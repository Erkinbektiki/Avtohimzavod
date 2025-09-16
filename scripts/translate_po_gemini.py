# scripts/translate_po_gemini.py
import os
import re
import time
import json
from pathlib import Path

import polib
from dotenv import load_dotenv
from tqdm import tqdm

import google.generativeai as genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise SystemExit("GOOGLE_API_KEY не найден в .env")

MODEL_NAME = "gemini-1.5-flash"

GLOSSARY = {
    "раскоксовка": {"en": "decarbonization", "ky": "раскоксовка"},
    "диагностика мотора": {"en": "engine diagnostics", "ky": "мотор диагностикасы"},
    "детейлинг": {"en": "detailing", "ky": "детейлинг"},
    "Автохим завод": {"en": "Avto_Him_Zavod", "ky": "Avto_Him_Zavod"},
}

PLACEHOLDER_PATTERNS = [
    r"%\([^)]+\)[sd]",
    r"%s|%d",
    r"\{\{.*?\}\}",
    r"\{%.*?%\}",
    r"\{[^\}]+\}",
    r"<[^>]+>",
]

def build_system_prompt(target_lang: str) -> str:
    # НЕ f-строка! Просто собираем текст частями.
    parts = [
        "You are a professional software localization translator.",
        "Translate from Russian to " + target_lang.upper() + ".",
        "Rules:",
        "- Preserve placeholders and template tags unchanged (patterns like %(name)s, %s, {{ var }}, {% block %}, {foo}, <b>...</b>).",
        "- Keep punctuation, capitalization and placeholders positions.",
        "- Do not translate brand names (Avto_Him_Zavod).",
        "Use the glossary strictly if applicable:",
        json.dumps(GLOSSARY, ensure_ascii=False, indent=2),
        "Output only the translated text, no comments.",
    ]
    return "\n".join(parts)

def freeze_spans(text: str):
    frozen = []
    def repl(m):
        frozen.append(m.group(0))
        return f"[[[__KEEP_{len(frozen)-1}__]]]"
    pattern = re.compile("|".join(PLACEHOLDER_PATTERNS))
    protected = pattern.sub(repl, text)
    return protected, frozen

def unfreeze_spans(text: str, frozen):
    for i, chunk in enumerate(frozen):
        text = text.replace(f"[[[__KEEP_{i}__]]]", chunk)
    return text

def translate_strings(strings, target_lang: str):
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)

    out = []
    for s in tqdm(strings, desc=f"Translate → {target_lang}"):
        if not s.strip():
            out.append(s)
            continue
        protected, frozen = freeze_spans(s)
        prompt = build_system_prompt(target_lang) + "\n\nSOURCE:\n" + protected
        for attempt in range(3):
            try:
                resp = model.generate_content(prompt)
                t = resp.text.strip() if resp and hasattr(resp, "text") else ""
                t = unfreeze_spans(t, frozen)
                out.append(t or s)
                break
            except Exception:
                if attempt == 2:
                    out.append(s)
                else:
                    time.sleep(1.5 * (attempt + 1))
    return out

def translate_po(src_po_path: Path, target_lang_code: str):
    po = polib.pofile(str(src_po_path))
    pending_idx = []
    sources = []
    for idx, entry in enumerate(po):
        if entry.obsolete:
            continue
        if entry.msgid_plural:
            if not all(entry.msgstr_plural.values()):
                pack = f"[SINGULAR]: {entry.msgid}\n[PLURAL]: {entry.msgid_plural}"
                sources.append(pack)
                pending_idx.append(("plural", idx))
            continue
        if not entry.msgstr:
            sources.append(entry.msgid)
            pending_idx.append(("single", idx))

    if not sources:
        print(f"{src_po_path.name}: нечего переводить")
        return

    translated = translate_strings(sources, target_lang_code)

    t_i = 0
    for kind, idx in pending_idx:
        entry = po[idx]
        text = translated[t_i]
        t_i += 1
        if kind == "single":
            entry.msgstr = text
        else:
            sing = re.search(r"\[SINGULAR\]:\s*(.+)", text, flags=re.S)
            plur = re.search(r"\[PLURAL\]:\s*(.+)", text, flags=re.S)
            s_val = (sing.group(1).strip() if sing else "").strip()
            p_val = (plur.group(1).strip() if plur else "").strip()
            entry.msgstr_plural[0] = s_val
            entry.msgstr_plural[1] = p_val or s_val

    po.save(str(src_po_path))
    print(f"✔ Saved: {src_po_path}")

if __name__ == "__main__":
    base = Path("locale")
    targets = [
        base / "en" / "LC_MESSAGES" / "django.po",
        base / "ky" / "LC_MESSAGES" / "django.po",
    ]
    for po_path in targets:
        if po_path.exists():
            lang = po_path.parts[-3]
            translate_po(po_path, lang)
        else:
            print(f"skip: {po_path} (нет файла)")
