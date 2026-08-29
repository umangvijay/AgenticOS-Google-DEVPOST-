# AgentOS

**Tell it what you want. It builds the tools and does the work.**

AgentOS is an autonomous AI workspace. You give a high-level goal. A planner turns it into a DAG of tasks. If a required integration is missing, the MCP factory builds it — HTTP tools from an OpenAPI spec, HTTP tools sketched from a description when there is no spec, or origin-locked browser tools when the target is a website with no public API. The factory probes the tools, registers them, and the orchestrator continues in the same run (or the next message in the thread).

Resume generation, self-healing retries, a vault, and an action timeline are features of that workspace — not the whole product.

**Local default:** Next.js on port 3000, FastAPI on port 8000, SQLite. Google Cloud (Cloud Run, Secret Manager, optional Firestore) is how you *host* it, not what you need on a laptop.

Source: [github.com/umangvijay/AgenticOS-Google-DEVPOST-](https://github.com/umangvijay/AgenticOS-Google-DEVPOST-)

## What it can do

- **Dynamic MCP builder** — OpenAPI URL, pasted spec, natural-language prompt for any HTTP API, or a website with no API (Playwright tools on a locked origin). Not a reverse-engineered private API.
- **Autonomous orchestration** — planner = task decomposition. Core nodes (HTTP, health, chat) do not need a model. The orchestrator uses the live tool catalog.
- **Self-healing** — timeouts, network errors, and 429/quota are retried. CAPTCHA / OTP / MFA are **not** retried as failures: the run **pauses** for you.
- **Human-in-the-loop challenges** — AgentOS never fills CAPTCHA, SMS OTP, or MFA. It opens a visible browser when it can, you complete the check, then **Resume**.
- **Vault** — AES-256-GCM credentials. The API never returns values after save.
- **Resume** — scan vs a job description, tailor from notes, HTML preview/download.
- **Action timeline** — workspace shows the events the agents actually emitted.
- **Contact** — SMTP with a **Gmail App Password** (not your Gmail login password) to `godumang35@gmail.com`.

## How MCP tools work from chat

Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard). Chips under the composer send these same goals. The same three tabs exist on **Integrations → Create**.

| You have | You type in chat | What gets built |
| --- | --- | --- |
| OpenAPI URL | `Create MCP tools from https://…/openapi.json then list …` | HTTP tools from the spec, live-probed, then called |
| HTTP API, no spec | `Build MCP tools for [app] so I can [list / get / create …]` | HTTP tools against the public API (GitHub, Open-Meteo, PokeAPI, …) |
| Website, no API | Vault → save e.g. `bharatenglish` (username/email + password). Then `Create MCP tools for https://…`. Then `Log in with vault credential bharatenglish and open home / use runOnSite …` | Origin-locked browser tools (`runOnSite`, `login`, …). CAPTCHA/OTP/MFA pause for you. |

Follow-up messages in the same thread reuse the catalog. Vault lists **names only** after save.

## Quick start (laptop)

```bash
cd "AgenticOS(Google DEVPOST)"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # add GEMINI_API_KEY; optional CONTACT_SMTP_PASSWORD
.venv/bin/python main.py
cd frontend && npm install && npm run dev
```

- App: http://localhost:3000
- API: http://127.0.0.1:8000
- OpenAPI: http://127.0.0.1:8000/docs

`main.py` starts FastAPI and can start the Next.js app. Do not kill whatever is already listening on 3000/8000 if the health check is green.

### Contact mail (Gmail App Password — never your login password)

Gmail **will reject** your normal mailbox password for SMTP. Putting that password in `.env` is also unsafe: it unlocks the whole Google account.

1. Turn on [2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification).
2. Create a 16-character [App Password](https://myaccount.google.com/apppasswords).
3. Put it only in the **project-root** `.env` (next to this README):

```
CONTACT_TO_EMAIL=godumang35@gmail.com
CONTACT_SMTP_HOST=smtp.gmail.com
CONTACT_SMTP_PORT=587
CONTACT_SMTP_USERNAME=godumang35@gmail.com
CONTACT_SMTP_PASSWORD=your-16-char-app-password
```

Spaces in the App Password are stripped. `.env` is gitignored and is **never** committed. Save the file and send again from `/contact` — no restart required. On Google Cloud, store the same value in Secret Manager, not in the image.

## Deploy on Google Cloud (~$150 credits)

See **[docs/deploy-gcp.md](docs/deploy-gcp.md)** for the full path (billing, Secret Manager, Cloud Run, optional Terraform).

Short version:

- Use **Cloud Run** (scale to zero) so idle time does not burn the credit grant.
- Put `GEMINI_API_KEY`, `CONTACT_SMTP_PASSWORD`, and `SECRETS_MASTER_KEY` in **Secret Manager**. Never bake `.env` into Docker.
- Laptop SQLite is ephemeral on Cloud Run. For durable users/runs, set `STORAGE_BACKEND=firestore`.
- Keep Cloud Run **min instances = 0**. An always-on worker will drain credits.

This repo is not deployed to your GCP project until **you** run those commands while logged in (`gcloud auth login`).

## Documentation

- [Architecture](docs/architecture.md)
- [Security](docs/SECURITY.md)
- [MCP builder](docs/mcp-builder.md)
- [Automation](docs/automation.md)
- [User guide](docs/user-guide.md)
- [Google Cloud deploy](docs/deploy-gcp.md)
- [Environment setup](docs/environment-setup.md)
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
| Contact SMTP | Gmail App Password in gitignored `.env` or Secret Manager — never the mailbox password |
| Cloud secrets | Secret Manager on Cloud Run; `.env` is not in git |

Argon2id is a future option for *new* password hashes; this tree keeps bcrypt so existing accounts still log in.

## Honest limits

- Website MCP is **UI automation**, not a hidden official API.
- Stripe live charges and other paid APIs need your own keys in the Vault.
- CAPTCHA, SMS OTP, and bank MFA require you. AgentOS will not complete them for you.
- Contact mail does not send until `CONTACT_SMTP_PASSWORD` is a valid App Password.
- Cloud Run with SQLite loses data when instances recycle. Use Firestore for production persistence.
