# core/tele_notify.py
from __future__ import annotations
import json
import threading
import requests
from django.conf import settings


def _send_telegram_message(text: str, parse_mode: str | None = "HTML") -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return  # молча выходим, чтобы не падать в dev, если не настроено

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.RequestException:
        # в продакшене можно логировать
        pass


def notify_lead(data: dict) -> None:
    """
    data ожидается вида:
    {
      "name": "...",
      "phone_e164": "+996...",
      "service": "Раскоксовка",    # опционально
      "comment": "текст",          # опционально
      "utm_source": "...",         # опционально
      "utm_medium": "...",
      "utm_campaign": "..."
    }
    """
    # Собираем человеческое сообщение
    lines = ["<b>Новая заявка с сайта</b>"]
    if v := data.get("name"):
        lines.append(f"👤 Имя: {v}")
    if v := data.get("phone_e164"):
        lines.append(f"📞 Телефон: <code>{v}</code>")
    if v := data.get("service"):
        lines.append(f"🛠 Услуга: {v}")
    if v := data.get("comment"):
        lines.append(f"📝 Комментарий: {v}")

    # UTM-метки если есть
    utm_parts = []
    for k in ("utm_source", "utm_medium", "utm_campaign"):
        if data.get(k):
            utm_parts.append(f"{k}={data[k]}")
    if utm_parts:
        lines.append("🔗 UTM: " + ", ".join(utm_parts))

    text = "\n".join(lines)

    # Отправим в отдельном потоке, чтобы не блокировать ответ пользователю
    threading.Thread(target=_send_telegram_message, args=(text,), daemon=True).start()
