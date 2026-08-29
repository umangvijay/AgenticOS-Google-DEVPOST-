# MCP tool creation

If AgentOS does not already have tools for an application, it **creates them**, tests them, registers them, and then uses them.

## How it works

1. You provide an OpenAPI spec, an API docs URL, a natural-language description of an HTTP API, or a **website URL** with no public API.
2. The planner picks a factory method:
   - **`url`** — fetch OpenAPI/Swagger (SSRF-safe).
   - **`prompt`** — sketch or generate a small OpenAPI against a public HTTPS host (GitHub, Open-Meteo, PokeAPI, JSONPlaceholder, …).
   - **`website`** — plan Playwright tools on one origin. No hidden REST API is invented.
3. The factory generates tool schemas, probes a safe GET when the path is HTTP, and registers the MCP in your catalog.
4. Tools appear for every agent. Authenticated APIs attach a vault credential (`api_key` / token). Browser login uses `credential_name` from chat (`Log in with vault credential NAME`).
5. The next task in the same run (or the next message in the thread) can call the new tools. Follow-ups score the catalog instead of always calling tool `[0]`.

Payment APIs, CRMs, issue trackers, and internal HTTPS APIs all use the HTTP path. There is no per-vendor hardcoding beyond a few well-known public hosts used to sketch paths when you skip OpenAPI.

## In the product

- **Integrations → Create MCP** — OpenAPI URL, paste spec, website URL, or “I don’t see my app”. Poll live build logs.
- **Workspace chat**
  - OpenAPI: `Create MCP tools from https://…/openapi.json then list …`
  - HTTP API without a spec: `Build MCP tools for [app] so I can [list / get / create …]`
  - Website: vault login, then `Create MCP tools for https://…`, then `Log in with vault credential NAME and open home / use runOnSite`

Dashboard chips send the three live-safe examples (PokeAPI OpenAPI, GitHub events, example.com website).

## Trust

Specs from a URL start as `verified` when they parse cleanly. Prompt-generated specs are `pending_review`. Private/localhost/metadata hosts are blocked.

## Websites without an API

Integrations → Create → **Website**, or chat `Create MCP tools for https://example.com`. The factory plans Playwright tools (`runOnSite`, `login`, `openHome`, …) locked to that origin. That is UI automation, not a hidden REST API.

CAPTCHA, OTP, and MFA pause the run for you. AgentOS does not fill them. Use Vault + **Resume after challenge** for real logins (for example a learner portal). Live E2E uses `example.com` so it never hits CAPTCHA.

## After the build

`GET /api/v1/integrations` lists MCPs for the current user. Disable or delete from the Integrations UI. Circuit breakers open if a tool starts failing repeatedly.
