# scripts/translate_po.py
import os, re, json, time, hashlib
from pathlib import Path
from dotenv import load_dotenv
import polib
from tqdm import tqdm

from openai import OpenAI

# ===== Настройки =====
MODEL = "gpt-4o-mini"   # бюджетная и качественная
SRC_LANG = "ru"          # исходные тексты на сайте
# =====================

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY не задан в .env")

client = OpenAI(api_key=api_key)

# ———— защита плейсхолдеров и тэгов ————
PLACEHOLDER_PATTERNS = [
    r"%\([^)]+\)s",    # Python формат: %(name)s
    r"%s", r"%d",      # Python формат: %s %d
    r"\{\{.*?\}\}",    # Django: {{ var }}
    r"\{%.*?%\}",      # Django: {% block %}
    r"<[^>]+>",        # HTML теги
    r"https?://\S+",   # ссылки
]
PLACEHOLDER_REGEX = re.compile("|".join(PLACEHOLDER_PATTERNS), flags=re.DOTALL)

def mask_placeholders(text: str):
    """Заменяем плейсхолдеры на маркеры, чтобы ИИ их не портил."""
    mapping = {}
    def _sub(m):
        token = f"§§PH{len(mapping)}§§"
        mapping[token] = m.group(0)
        return token
    masked = PLACEHOLDER_REGEX.sub(_sub, text)
    return masked, mapping

def unmask_placeholders(text: str, mapping: dict):
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text

# ———— простейший кэш на диск ————
CACHE_DIR = Path(".cache/i18n")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def cache_key(msgid: str, target_lang: str):
    h = hashlib.sha1((target_lang + "||" + msgid).encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{target_lang}_{h}.json"

def cache_get(msgid: str, target_lang: str):
    f = cache_key(msgid, target_lang)
    if f.exists():
        try:
            return json.loads(f.read_text("utf-8"))["translation"]
        except Exception:
            return None
    return None

def cache_set(msgid: str, target_lang: str, translation: str):
    f = cache_key(msgid, target_lang)
    f.write_text(json.dumps({"translation": translation}, ensure_ascii=False), "utf-8")

# ———— хелперы ————
def looks_like_code_or_empty(s: str) -> bool:
    s = s.strip()
    if not s:
        return True
    # короткие вещи типа "OK", "USD", "VIN", "API" — не переводим
    if len(s) <= 2 and s.isupper():
        return True
    return False

SYSTEM_PROMPT = (
    "You are a professional software localization translator for a Django website. "
    "Translate Russian → TARGET_LANG. Keep meaning, tone (business). "
    "VERY IMPORTANT RULES:\n"
    "1) Do NOT change placeholders or tags: %(name)s, %s, {{ var }}, {% tag %}, HTML like <a>...</a>.\n"
    "2) Preserve punctuation and numbers.\n"
    "3) Keep brand names and phone numbers as-is.\n"
    "4) If text is already language-neutral or too short (e.g. 'OK', 'VIN'), return as-is.\n"
    "5) Never add quotes around the result.\n"
)

def ask_ai(msgid: str, target_lang: str) -> str:
    """Запрос к ИИ с маскированием плейсхолдеров."""
    cached = cache_get(msgid, target_lang)
    if cached is not None:
        return cached

    masked, mapping = mask_placeholders(msgid)
    user_prompt = (
        f"TARGET_LANG={target_lang}\n"
        f"Original (RU):\n{masked}\n\n"
        "Return only the translated sentence (no comments)."
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.2,
    )
    out = resp.choices[0].message.content.strip()
    out = unmask_placeholders(out, mapping)
    cache_set(msgid, target_lang, out)
    return out

def translate_po(po_path: Path, target_lang: str):
    po = polib.pofile(str(po_path))
    changed = False

    for entry in tqdm(po.untranslated_entries() + [e for e in po if not e.translated() and e.msgstr]):
        msgid = entry.msgid

        # пропуск пустых/псевдокода
        if looks_like_code_or_empty(msgid):
            continue

        try:
            tr = ask_ai(msgid, target_lang)
            if tr and tr.strip() and tr.strip() != msgid.strip():
                entry.msgstr = tr
                changed = True
        except Exception as e:
            print(f"[WARN] fail on: {msgid[:80]}… -> {e}")
            time.sleep(1)

    if changed:
        po.save()
        print(f"Saved: {po_path}")
    else:
        print(f"No changes: {po_path}")

def main():
    project_root = Path(__file__).resolve().parents[1]
    locale_dir = project_root / "locale"

    targets = []
    # если хочешь строго две локали — раскомментируй:
    # targets = ["ky", "en"]

    # иначе собираем из папки locale:
    for lang_dir in locale_dir.glob("*"):
        if lang_dir.name == SRC_LANG:
            continue
        if (lang_dir / "LC_MESSAGES" / "django.po").exists():
            targets.append(lang_dir.name)

    if not targets:
        print("Не найдены целевые локали (кроме ru). Убедись, что запускал makemessages.")
        return

    for t in targets:
        po_file = locale_dir / t / "LC_MESSAGES" / "django.po"
        print(f"===> Translating {po_file} ({SRC_LANG} → {t})")
        translate_po(po_file, t)

if __name__ == "__main__":
    main()
