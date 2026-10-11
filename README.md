# DealTwin 🤖
### AI Sales Agent with Memory

DealTwin is an AI-powered sales agent that uses **Hindsight memory** to remember and recall important information throughout the sales deal cycle.

## 💡 Problem
Sales teams often lose track of customer conversations, pricing concerns, stakeholder priorities, competitor mentions, and follow-up commitments. Reviewing scattered notes takes time and can lead to missed opportunities.

## 🚀 Solution
DealTwin maintains deal context across interactions and helps sales teams make informed decisions using past conversations and outcomes.

## ✨ Key Features
- 🧠 Remembers customer conversations and objections
- 👥 Tracks stakeholder priorities and competitor mentions
- ⏰ Identifies overdue commitments and follow-ups
- ⚠️ Detects potential deal risks
- 🎯 Suggests the next best action
- 📈 Uses past deal context to support better recommendations

## 🛠️ Technology
- **Hindsight** — Persistent memory
- **AI Agent** — Context-aware sales recommendations

## 🔗 Project Links
- **GitHub:** https://github.com/bhanuprasadvaddepally/DealTwin
- **Demo Video:** Add your demo link here

## 🏆 About
Built as part of **HackWithHyderabad 3.0**, organized by Hack With India in collaboration with Devnovate.

Our goal is simple: **Less time searching through notes, more time making smarter sales decisions.**

## Run locally

Prerequisites: Python, Node.js/npm, and access to a Hindsight server.

1. Configure Hindsight in `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set `HINDSIGHT_BASE_URL`, `HINDSIGHT_BANK_ID`, and, if required by your server, `HINDSIGHT_API_KEY`. The example file uses a hosted Hindsight URL; replace its placeholder API key with a valid key. Keep real credentials out of source control.

2. Start the backend from the repository root:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --app-dir backend --reload --port 8000
   ```

3. In a second terminal, start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Open <http://localhost:5173>. Use **Load sample client** to populate the Acme example workspace. Vite forwards API requests to the backend.

The backend reads its settings from environment variables or `.env`. Defaults and available settings are defined in `backend/app/config.py`; SQLite uses `data/dealtwin.db` by default.

## Checks

Run from the repository root unless noted:

```powershell
pytest backend/tests
ruff check backend
cd frontend
npm run lint
npm run build
```

