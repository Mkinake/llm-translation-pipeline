"""
LLM-based Localization Pipeline (Incremental CI/CD)

Behavior:
- Loads en.json (source)
- Loads existing fr.json (if any)
- Translates ONLY new or changed keys
- Preserves existing translations
- Enforces glossary
- Protects placeholders
- Writes merged fr.json
"""

# ================================
# 1. Setup & Imports
# ================================

from openai import OpenAI
import os
import json
import csv
import re
from pathlib import Path

# OpenAI client (API key comes from environment variable)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# File paths
INPUT_FILE = Path("input/en.json")
OUTPUT_FILE = Path("output/fr.json")

# ================================
# 2. Load Source (en.json)
# ================================

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    source_data = json.load(f)

print("Loaded strings:", len(source_data))

# ================================
# 3. Load Existing Target (fr.json)
#    This enables incremental CI/CD
# ================================

def load_existing_translation(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

existing_fr = load_existing_translation(OUTPUT_FILE)

# ================================
# 4. Glossary (CSV-based terminology)
# ================================

def load_glossary(csv_path):
    glossary = {}
    if not Path(csv_path).exists():
        return glossary

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            glossary[row["source"]] = row["target"]
    return glossary

GLOSSARY = load_glossary("glossary.csv")

def apply_glossary(text, glossary):
    for source, target in glossary.items():
        text = text.replace(source, target)
    return text

# ================================
# 5. Placeholder Handling
# ================================

PLACEHOLDER_PATTERN = re.compile(r"\{[^}]+\}")

def mask_placeholders(text):
    placeholders = PLACEHOLDER_PATTERN.findall(text)
    mapping = {}
    masked_text = text

    for index, placeholder in enumerate(placeholders, start=1):
        token = f"<VAR{index}>"
        mapping[token] = placeholder
        masked_text = masked_text.replace(placeholder, token)

    return masked_text, mapping

def restore_placeholders(text, mapping):
    restored_text = text
    for token, original in mapping.items():
        restored_text = restored_text.replace(token, original)
    return restored_text

def extract_placeholders(text):
    return set(re.findall(r"<VAR\d+>", text))

# ================================
# 6. Decide WHAT needs translation
#    (Incremental / Delta logic)
# ================================

def get_keys_to_translate(source_en, existing_fr):
    """
    A key needs translation if:
    - It does not exist in fr.json
    - OR the English text has changed since last run
    """
    keys_to_translate = {}

    for key, en_text in source_en.items():
        source_marker = f"__source__:{key}"

        # New key
        if key not in existing_fr:
            keys_to_translate[key] = en_text

        # Changed English text
        elif existing_fr.get(source_marker) != en_text:
            keys_to_translate[key] = en_text

    return keys_to_translate

keys_to_translate = get_keys_to_translate(source_data, existing_fr)

print("Keys to translate:", list(keys_to_translate.keys()))

# ================================
# 7. LLM Translation Function
# ================================

def llm_translate(text, source_lang="en", target_lang="fr-FR"):
    prompt = f"""
You are a professional localization engine.

Rules:
- Translate from {source_lang} to {target_lang}
- Preserve placeholders like <VAR1>, <VAR2> exactly
- Do NOT add explanations
- Output only the translated text

Text:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You translate software UI strings."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()

# ================================
# 8. Translate ONLY delta keys
# ================================

for key, en_text in keys_to_translate.items():
    # 1. Mask source
    masked_text, mapping = mask_placeholders(en_text)

    # 2. Translate (masked)
    masked_translation = llm_translate(masked_text)
    masked_translation = apply_glossary(masked_translation, GLOSSARY)

    # 3. QA — validate masked placeholders
    src_vars = extract_placeholders(masked_text)
    tgt_vars = extract_placeholders(masked_translation)

    if src_vars != tgt_vars:
        raise ValueError(f"❌ Placeholder mismatch in key '{key}'")

    # 4. Restore placeholders ONLY after QA
    final_text = restore_placeholders(masked_translation, mapping)

    # 5. Save result + source snapshot
    existing_fr[key] = final_text
    existing_fr[f"__source__:{key}"] = en_text

print("✅ QA PASSED — placeholders are safe")

# ================================
# 10. Write Output (merged fr.json)
# ================================

OUTPUT_FILE.parent.mkdir(exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(existing_fr, f, ensure_ascii=False, indent=2)

print("🎉 Translation pipeline completed successfully!")
print("📁 Output file:", OUTPUT_FILE)
