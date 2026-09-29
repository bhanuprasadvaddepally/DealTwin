# DealTwin

DealTwin is a client conversation workspace prototype. It keeps client notes and outcomes connected to past conversations so sales teams can prepare for the next call with more context.

## What it does

- Create and switch between client workspaces.
- Save meeting notes, calls, emails, and transcripts, then search past conversations.
- Ask for client-specific coaching grounded in remembered notes.
- Review follow-up risks and the people involved in a client relationship.
- Check a proposed next step for possible benefits, risks, and alternatives.
- Record what happened and compare a general answer with one informed by client history.

DealTwin uses Hindsight for long-term memory and evidence-based responses. SQLite stores workspace metadata. Recommendations are guidance, not guaranteed predictions; follow-up and stakeholder analysis are heuristic prototype features.

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

