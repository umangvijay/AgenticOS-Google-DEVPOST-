# AgentOS

**Tell it what you want. It builds the tools and does the work.**

AgentOS is an autonomous AI workspace: you give a high-level goal; a planner turns it into a DAG of tasks; if a required integration is missing, the MCP factory builds it (OpenAPI HTTP tools or origin-locked browser tools), tests it, registers it, and the orchestrator continues. Resume generation, self-healing retries, and an action timeline are features of that workspace — not the whole product.

Default local stack: **Next.js** (port 3000) + **FastAPI** (port 8000) + **SQLite**. Google Cloud (Firestore, Pub/Sub, Cloud Run) is an optional storage/runtime mode, not what you run on a laptop.

## What it can do

- **Dynamic MCP builder** — OpenAPI/docs URL, pasted spec, natural-language prompt, or a website with no API (Playwright tools on a locked origin). Not a hidden official API.
- **Autonomous orchestration** — planner = task decomposition. Core nodes (HTTP, health, chat) do not need a model; the orchestrator uses the live tool catalog.
- **Self-healing** — timeouts, network errors, and 429/quota are retried; semantic failures can recover. CAPTCHA/OTP/MFA are **not** retried as failures: the run **pauses** for you.
- **Human-in-the-loop challenges** — AgentOS never fills CAPTCHA, SMS OTP, or MFA. It opens a visible browser when it can, asks you to complete the check, then **Resume**.
- **Vault** — AES-256-GCM credentials; API never returns values after save.
- **Resume** — scan vs a job description, tailor from notes, HTML preview/download.
- **Action timeline** — workspace shows the events the agents actually emitted.
- **Contact** — SMTP (Gmail App Password) to `godumang35@gmail.com`.

## Quick start

```bash
cd "AgenticOS(Google DEVPOST)"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # add GEMINI_API_KEY and CONTACT_SMTP_PASSWORD
.venv/bin/python main.py
cd frontend && npm install && npm run dev
```

- App: http://localhost:3000
- API: http://127.0.0.1:8000
- OpenAPI: http://127.0.0.1:8000/docs

Contact mail: open the **project-root** `.env` (next to `README.md`) and set:

```
CONTACT_TO_EMAIL=godumang35@gmail.com
CONTACT_SMTP_HOST=smtp.gmail.com
CONTACT_SMTP_PORT=587
CONTACT_SMTP_USERNAME=godumang35@gmail.com
CONTACT_SMTP_PASSWORD=your-16-char-gmail-app-password
```

Create the App Password at [Google App Passwords](https://myaccount.google.com/apppasswords) (2-Step Verification must be on). Save `.env` and send again from `/contact`. The password is never committed.

## Documentation

- [Architecture](docs/architecture.md)
- [Security](docs/SECURITY.md)
- [MCP builder](docs/mcp-builder.md)
- [Automation](docs/automation.md)
- [User guide](docs/user-guide.md)
- [Diagrams](docs/diagrams/)
- In-app docs: http://localhost:3000/docs

## Security (summary)

| Control | Mechanism |
| --- | --- |
| Account passwords | bcrypt cost 12; optional HMAC `PASSWORD_PEPPER`; 5-fail / 15-min lockout |
| Vault secrets | AES-256-GCM, PBKDF2-SHA256 480k iterations |
| Sessions | JWT RS256, CSRF cookie, rate limits |
| HTTP tools | SSRF blocks on private/loopback hosts |
| Browser tools | Origin / registrable-domain lock; secrets as `{{secret:…}}` placeholders |
| Auth walls | HITL pause for CAPTCHA / OTP / MFA — no solving or bypass |

Argon2id is a future option for new password hashes; this tree keeps bcrypt so existing accounts still log in.

## Honest limits

- Website MCP is **UI automation**, not a reverse-engineered private API.
- Stripe live charges and other paid APIs need your own keys in the Vault.
- CAPTCHA, SMS OTP, and bank MFA require you. AgentOS will not complete them for you.
