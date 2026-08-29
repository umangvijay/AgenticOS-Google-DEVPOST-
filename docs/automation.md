# Automation agent

The automation agent is a **chat-first** workspace plus a DAG executor.

## Loop

1. **Intent** — the model interprets your goal (live Gemini call). Direct plans skip this hop for health checks, raw HTTP GETs, and MCP-build phrases the planner already understands.
2. **Plan** — a DAG of `core.*` nodes and OrchestratorAgent tasks, using your **current** tool catalog. If the goal is to create tools, the first node is `core.mcp_build` with method `url`, `prompt`, or `website`.
3. **Execute** — HTTP, health checks, email, or AI tasks that can call catalog tools, build missing integrations, browse the web, debug, generate projects, or write resumes.
4. **Recover** — retries for timeout/network/429; semantic recovery when enabled. CAPTCHA/OTP/MFA pause for a human instead of failing.

## Chat UI

The workspace is a message thread. SSE events appear as an action timeline. Task output is JSON from the real run. Suggestion chips on `/dashboard` are the three MCP paths (OpenAPI, HTTP without spec, website).

Follow-up messages pass `parent_run_id` / `thread_id` so the catalog from the previous build is reused.

## Browser work

For sites without an API, website MCP / `browse_website` drives Chromium: snapshot → model decides next click/type → domain-locked navigation. Credentials stay in the vault. Challenges pause (`WAITING_APPROVAL`) until you Resume in the **same** browser session.

## Scheduling

Schedules fire from cron locally. Cloud Scheduler is optional production. The same goal → plan → execute path runs unattended.

## What “working” means

A green chat turn means the engine completed (or paused for HITL) with live tool results — not a canned string. Unit tests cover method routing (`backend/tests/test_mcp_intent_routing.py`). Live checks live in `scripts/live_e2e.py` against `:8000` and `:3000`.
