from django import template
from urllib.parse import urlencode, quote
import re

register = template.Library()

@register.filter
def pretty_phone(e164: str) -> str:
    if not e164:
        return ""
    return re.sub(r"^\+996(\d{3})(\d{3})(\d{3})$", r"+996 \1 \2 \3", e164)

@register.simple_tag
def wa_link(e164: str, text: str = "") -> str:
    """
    wa.me/<digits>?text=...
    - e164: "+996770123456"
    - text: произвольный текст (URL-энкодится)
    """
    if not e164:
        return "#"
    digits = re.sub(r"\D", "", e164)  # оставить только цифры
    q = f"?text={quote(text)}" if text else ""
    return f"https://wa.me/{digits}{q}"
