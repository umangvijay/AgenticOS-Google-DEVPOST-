# AgentOS user guide

AgentOS is an autonomous workspace: you describe a goal in plain language, and it **plans**, **builds any missing app tools**, and **executes** against live systems. Inputs and outputs are real-time — not canned demos.

## What you can ask

- Connect or create tools for **any app with an HTTP API** (from OpenAPI, docs URL, or a description).
- Work in a real browser on a site (login with stored credentials, click, fill forms, extract results). CAPTCHA/OTP/MFA: you complete them, then Resume.
- Send a message on Contact (SMTP to the team) or send email via a vault SMTP credential / provider MCP.
- Check website/API health (DNS, TLS, latency, status, headers).
- Debug source code (syntax + diagnosis; submitted code is not executed).
- Generate a **medium or large** website or local app as downloadable files.
- Create and score **ATS-ready resumes** from notes or a PDF.

## Chat workspace

Open **New chat** after sign-in. Type a goal and press Enter. Show graph for the DAG, **Show timeline** for autonomous actions, **Resume after challenge** when a security check appears.

Nothing in that thread is pre-written. The planner, tool catalog, and task outputs come from the live backend.

## Vault

Store encrypted credentials (site logins, `smtp`, API keys). Field values are never returned by the API. Browser automation injects them as `{{secret:field}}` placeholders so the model never sees the secret.

## Context usage

The meter in the top bar shows how much of the 256K context window is occupied **right now**: system prompt, tool definitions, MCP tools, subagents, last conversation, and memory. Counts are estimated from your live catalog and last run.

## Guest vs signed-in

**Get started for free** provisions a guest JWT and opens `/dashboard`. Guests can build MCPs and run health checks. Sign in to keep a named account.

## Direct health runs

If your goal is to check the health of a URL, the backend skips the Gemini planner and runs `core.health` immediately — so that chip still works when model quota is exhausted.


In Settings, set autonomy 0–3. Semi-autonomous (2) auto-runs low/medium risk tools and asks you before high-risk ones. See [SECURITY.md](SECURITY.md) for bcrypt, vault encryption, CSRF, SSRF, and HITL.
