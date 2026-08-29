# Security

AgentOS is built to hold logins and API keys. The controls below are what the running code does — not a future wish list.

## Account passwords

- **bcrypt** with cost **12**.
- bcrypt’s 72-byte limit is enforced.
- Policy: length 8–72, upper, lower, digit, special; common-password denylist.
- Lockout: **5** failed logins → **15** minutes.
- Optional **HMAC-SHA256 pepper** (`PASSWORD_PEPPER`) mixed in before bcrypt. Verify tries peppered material first, then legacy unpeppered hashes so existing users keep working.
- **Argon2id** is a documented future option for *new* hashes; it is not enabled in this pass because it would invalidate current bcrypt rows.

## Vault (API keys, site logins)

- **AES-256-GCM** authenticated encryption.
- Data-encryption key from **PBKDF2-HMAC-SHA256**, **480,000** iterations (OWASP 2024) over `SECRETS_MASTER_KEY`.
- REST list returns **names only**. Values are never returned after save.
- Agents receive `{{secret:field}}` placeholders. Substitution happens at keystroke / HTTP header time, not in the model prompt.

The vault is for *agent* site/API secrets (for example a portal named `bharatenglish`). It is not a substitute for the contact-form SMTP App Password in `.env`.

## Sessions and API

- JWT **RS256** (keys auto-generated under `backend/security/keys/`, gitignored).
- CSRF token cookie + header on mutating requests.
- Rate limits on auth, workflow create, MCP build, contact, general.
- CORS allowlist from settings.

## Tool and browser safety

- OpenAPI executor **SSRF** checks: no private, loopback, or link-local targets.
- Website MCP is locked to the start URL’s **registrable domain**.
- Playwright refuses private hosts.
- Circuit breaker per MCP after repeated failures.

## Human-in-the-loop (CAPTCHA / OTP / MFA)

AgentOS **does not** solve CAPTCHA, intercept SMS, or bypass MFA.

When a page looks like a challenge, the workflow status becomes `WAITING_APPROVAL`. A headed browser is opened when the environment allows it. You complete the check, then **Resume**. Completing the challenge in a *different* browser than the agent’s session will not continue that session.

## Contact SMTP and Gmail

STARTTLS (port 587) or SMTPS (465). Failures return a reason code such as `smtp_not_configured` or `smtp_auth_failed`. The password is never logged and never returned by `GET /api/v1/contact/status`.

**Do not put your Google mailbox password in `.env`.** Gmail SMTP does not accept it, and that password unlocks Drive, Mail, and account recovery.

Use a **Gmail App Password** only:

1. Enable [2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification).
2. Create an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Set `CONTACT_SMTP_PASSWORD` in the **project-root** `.env`. Spaces are stripped. Save and send again — the contact router re-reads `.env` on each send.

`.env` is listed in `.gitignore`. It is not in GitHub. Do not paste it into chat, Dockerfiles, or Cloud Build substitutions.

On Google Cloud, store `CONTACT_SMTP_PASSWORD` in **Secret Manager** and mount it as a Cloud Run env var. Do not copy `.env` into the container image.

## Secrets on disk vs in git vs in GCP

| Secret | Local | Git | Cloud Run |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | `.env` | never | Secret Manager |
| `CONTACT_SMTP_PASSWORD` | `.env` (App Password) | never | Secret Manager |
| `SECRETS_MASTER_KEY` | auto or `.env` | never | Secret Manager (must be stable or vault ciphertext is unreadable) |
| `PASSWORD_PEPPER` | optional `.env` | never | Secret Manager |
| Vault site passwords | encrypted in SQLite / Firestore | never (ciphertext only) | same stores |
| JWT PEM files | `backend/security/keys/` | gitignored | persist via Secret Manager or they rotate per new instance |

## What we will not do

- Fill or defeat CAPTCHA / OTP / MFA.
- Invent a private API for a website that has none.
- Return vault secrets to the UI.
- Commit `.env`, App Passwords, or service-account JSON.
