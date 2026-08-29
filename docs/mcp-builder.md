# MCP tool creation

If AgentOS does not already have tools for an application, it **creates them**, tests them, registers them, and then uses them.

## How it works

1. You provide an OpenAPI spec, an API docs URL, or a natural-language description of **any** app/API.
2. The MCP factory normalizes the spec (SSRF-safe fetch), generates tool schemas, probes a safe GET when possible, and registers the tools in your catalog.
3. Tools appear for every agent. Authenticated APIs attach a vault credential (`api_key` / token).
4. The next task in the same run can call the new tools.

Payment APIs, CRMs, issue trackers, and internal HTTPS APIs all use this same path. There is no per-vendor hardcoding.

## In the product

- **Integrations → Create MCP** — URL, prompt, or raw spec. Poll live build logs.
- **Workspace chat** — “Build tools for this API and then list X” lets the orchestrator call `build_integration` mid-run.

## Trust

Specs from a URL start as `verified` when they parse cleanly. Prompt-generated specs are `pending_review`. Private/localhost/metadata hosts are blocked.

## Websites without an API

Integrations → Create → **Website**, or chat “Create MCP tools for https://example.com”. The factory plans Playwright tools (`runOnSite`, `login`, …) locked to that origin. That is UI automation, not a hidden REST API.

CAPTCHA, OTP, and MFA pause the run for you. AgentOS does not fill them.
