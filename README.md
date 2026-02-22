# 🚀 LLM-Based Incremental Localization Pipeline (CI/CD)

This project demonstrates a production-style **LLM-powered localization pipeline** using:

- 🤖 OpenAI for translation
- 📚 CSV glossary enforcement
- 🧠 Placeholder protection & QA
- 🔄 Incremental (delta-based) translation logic
- ⚙️ GitHub Actions for automated CI/CD

The system translates **only new or modified source strings**, not the entire file — making it efficient, deterministic, and cost-optimized.

---

# 📂 Project Structure
├── pipeline.py
├── glossary.csv
├── input/
│ └── en.json
├── output/
│ └── fr.json
└── .github/
└── workflows/
└── translate.yml

---

# 🧠 How It Works

## 1️⃣ Source File

`input/en.json`

Any update and new content will trigger in the source file will transalte the CI/CD pipeline.

**FULL WORKFLOW**
Edit input/en.json
       ↓
git add input/en.json
       ↓
git commit -m "Update login text"
       ↓
git push
       ↓
GitHub Actions runs
       ↓
pipeline.py executes
       ↓
output/fr.json updated
       ↓
Bot commits changes
