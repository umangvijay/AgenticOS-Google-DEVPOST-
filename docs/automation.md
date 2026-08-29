# Automation agent

The automation agent is a **chat-first** workspace plus a DAG executor.

## Loop

1. **Intent** — the model interprets your goal (live Gemini call).
2. **Plan** — a DAG of `core.*` nodes and OrchestratorAgent tasks, using your **current** tool catalog.
3. **Execute** — HTTP, health checks, email, or AI tasks that can call catalog tools, build missing integrations, browse the web, debug, generate projects, or write resumes.
4. **Recover** — retries for timeout/network/429; semantic recovery when enabled. CAPTCHA/OTP/MFA pause for a human instead of failing.

## Chat UI

The workspace is a message thread. SSE events appear as an action timeline. Task output is JSON from the real run.

## Browser work

For sites without an API, website MCP / `browse_website` drives Chromium: snapshot → model decides next click/type → domain-locked navigation. Credentials stay in the vault. Challenges pause (`WAITING_APPROVAL`) until you Resume.

## Scheduling

Schedules fire from cron locally. Cloud Scheduler is optional production. The same goal → plan → execute path runs unattended.
