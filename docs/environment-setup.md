# Environment setup

Local AgentOS is Python 3.11+, Node 18+, Playwright Chromium, and a project-root `.env`. Google Cloud CLI is only required if you deploy.

## Local

```bash
cd "AgenticOS(Google DEVPOST)"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Edit .env: GEMINI_API_KEY=...
# Optional: CONTACT_SMTP_PASSWORD=16-char Gmail App Password (not your mailbox password)
.venv/bin/python main.py
```

In another terminal:

```bash
cd frontend && npm install && npm run dev
```

Confirm:

- http://127.0.0.1:8000/health → `"status": "healthy"`, `"storage": "sqlite"`
- http://localhost:3000 → 200

If those ports are already serving AgentOS, leave them running.

## `.env` rules

- File lives next to `README.md`. FastAPI and Next.js both read it.
- Never commit it (`.gitignore`).
- `CONTACT_SMTP_PASSWORD` must be a [Gmail App Password](https://myaccount.google.com/apppasswords), not the Google account password.
- `GET /api/v1/contact/status` reports `smtp_configured` without returning the secret.

## Google Cloud (optional)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Then follow [deploy-gcp.md](deploy-gcp.md). Do not put `.env` in Cloud Build. Use Secret Manager.

Docker Desktop is required only if you build images locally instead of `gcloud run deploy --source`.

## Tests

```bash
.venv/bin/python -m pytest backend/tests/test_mcp_intent_routing.py -q
.venv/bin/python scripts/live_e2e.py   # needs :8000 and :3000 up
```
