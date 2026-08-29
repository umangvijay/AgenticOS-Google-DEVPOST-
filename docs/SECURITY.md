# Security

AgentOS is built to hold logins and API keys. The controls below are what the running code does — not a future wish list.

## Account passwords

- **bcrypt** with cost **12**.
- bcrypt’s 72-byte limit is enforced.
- Policy: length 8–72, upper, lower, digit, special; common-password denylist.
- Lockout: **5** failed logins → **15** minutes.
- Optional **HMAC-SHA256 pepper** (`PASSWORD_PEPPER`) mixed in before bcrypt. Verify tries peppered material first, then legacy unpeppered hashes so existing users keep working.
- **Argon2id** is a documented future option for *new* hashes; it is not enabled in this pass because it would invalidate current bcrypt rows.

## Vault (API keys, site logins, SMTP)

- **AES-256-GCM** authenticated encryption.
- Data-encryption key from **PBKDF2-HMAC-SHA256**, **480,000** iterations (OWASP 2024) over `SECRETS_MASTER_KEY`.
- REST list returns **names only**. Values are never returned after save.
- Agents receive `{{secret:field}}` placeholders. Substitution happens at keystroke / HTTP header time.

## Sessions and API

- JWT **RS256** (keys auto-generated under `backend/security/keys/`).
- CSRF token cookie + header on mutating requests.
- Rate limits on auth, workflow create, MCP build, contact, general.
- CORS allowlist from settings.

## Tool and browser safety

- OpenAPI executor **SSRF** checks: no private, loopback, or link-local targets.
- Website MCP is locked to the start URL’s registrable domain.
- Playwright refuses private hosts.
- Circuit breaker per MCP after repeated failures.

## Human-in-the-loop (CAPTCHA / OTP / MFA)

AgentOS **does not** solve CAPTCHA, intercept SMS, or bypass MFA.

When a page looks like a challenge, the workflow status becomes `WAITING_APPROVAL`. A headed browser is opened when the environment allows it. You complete the check, then **Resume**. Completing the challenge in a *different* browser than the agent’s session will not continue that session.

## Contact SMTP

STARTTLS (port 587) or SMTPS (465). The App Password is never logged. Failures return a reason code such as `smtp_not_configured` or `smtp_auth_failed`.

## What we will not do

- Fill or defeat CAPTCHA / OTP / MFA.
- Invent a private API for a website that has none.
- Return vault secrets to the UI.
