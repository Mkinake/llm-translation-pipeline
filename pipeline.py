from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Simple localization pipeline: English to French

import json
from pathlib import Path

INPUT_FILE = Path("input/en.json")
OUTPUT_FILE = Path("output/fr.json")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    source_data = json.load(f)

print("Loaded strings:", len(source_data))

##Glossary loading and application

import csv

def load_glossary(csv_path):
    glossary = {}
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



###Detect placeholders
import re

PLACEHOLDER_PATTERN = re.compile(r"\{[^}]+\}")

#### Mask function

def mask_placeholders(text):
    placeholders = PLACEHOLDER_PATTERN.findall(text)
    mapping = {}
    masked_text = text

    for index, placeholder in enumerate(placeholders, start=1):
        token = f"<VAR{index}>"
        mapping[token] = placeholder
        masked_text = masked_text.replace(placeholder, token)

    return masked_text, mapping

### Apply masking to all strings

masked_data = {}
placeholder_maps = {}

for key, value in source_data.items():
    masked_text, mapping = mask_placeholders(value)
    masked_data[key] = masked_text
    placeholder_maps[key] = mapping


print("\n--- MASKED DATA ---")
for k, v in masked_data.items():
    print(k, "=>", v)

###   LLM function

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
        model="gpt-4o-mini",   # fast & cost-effective
        messages=[
            {"role": "system", "content": "You translate software UI strings."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()




##Apply translation

translated_data = {}

for key, text in masked_data.items():
    translated_text = llm_translate(text)
    translated_text = apply_glossary(translated_text, GLOSSARY)
    translated_data[key] = translated_text


print("\n--- TRANSLATED DATA ---")
for k, v in translated_data.items():
    print(k, "=>", v)



#Placeholder extraction helper

def extract_placeholders(text):
    return set(re.findall(r"<VAR\d+>", text))

### Validate placeholders

for key in masked_data:
    source_vars = extract_placeholders(masked_data[key])
    target_vars = extract_placeholders(translated_data[key])

    if source_vars != target_vars:
        raise ValueError(
            f"❌ Placeholder mismatch in key '{key}': "
            f"{source_vars} vs {target_vars}"
        )
print("\n✅ QA PASSED — placeholders are safe")
    
#Restore Placeholders

def restore_placeholders(text, mapping):
    restored_text = text
    for token, original in mapping.items():
        restored_text = restored_text.replace(token, original)
    return restored_text


#Apply restore

final_data = {}

for key, translated_text in translated_data.items():
    final_data[key] = restore_placeholders(
        translated_text,
        placeholder_maps[key]
    )


print("\n--- FINAL DATA ---")
for k, v in final_data.items():
    print(k, "=>", v)

#Write Output File

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


output_file = OUTPUT_DIR / "fr.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)
print("\n🎉 Translation pipeline completed successfully!")
print("📁 Output file:", output_file)

