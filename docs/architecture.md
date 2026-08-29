# Architecture

AgentOS is a local-first autonomous workspace. The laptop default is SQLite + an in-process worker. Firestore / Pub/Sub / Cloud Run remain optional when `STORAGE_BACKEND=firestore`.

## Tagline

Tell it what you want. It builds the tools and does the work.

## Runtime

```
Browser (Next.js :3000)
        │  REST + SSE + cookies
        ▼
FastAPI (:8000)
  auth, contact SMTP, credentials vault, MCP registry,
  workflows, resume, studio, approvals
        │
        ▼
Workflow engine (DAG)
  Intent → Planner (task decomposition) → execute
        │
        ├── core.http / core.health / core.chat / core.mcp_build
        ├── Orchestrator + MCP tool catalog
        └── WebAgent (Playwright, origin-locked)
```

Planner **is** the decomposer. There is no third LLM hop named Decomposer.

## Dynamic MCP

1. Discover: does a registered tool match the goal?
2. If yes → use it.
3. If no → MCP factory:
   - **HTTP:** OpenAPI / docs URL / pasted spec / prompt → tool schemas → live probe → register.
   - **Website (no API):** origin + Playwright tools (`runOnSite`, `login`, `openHome`, …). UI automation only.

## Data stores (local)

| Store | Path / table |
| --- | --- |
| SQLite | `data/agentos.db` — users, runs, tasks, events, MCP registry, schedules |
| Vault ciphertext | secrets table, AES-256-GCM |
| Contact inbox | `data/contact_inbox.json` plus SMTP to `CONTACT_TO_EMAIL` |
| JWT keys | `backend/security/keys/*.pem` |

## Data flow

```mermaid
flowchart LR
  user[UserGoal] --> api[FastAPI]
  api --> sqlite[(SQLite)]
  api --> planner[PlannerDAG]
  planner --> catalog[MCPCatalog]
  catalog -->|miss| factory[MCPFactory]
  factory --> httpTools[HTTPTools]
  factory --> browserTools[WebsiteBrowserTools]
  httpTools --> exec[Executor]
  browserTools --> exec
  catalog -->|hit| exec
  exec --> events[SSETimeline]
  events --> ui[Workspace]
  exec -->|CAPTCHA_OTP_MFA| hitl[PauseHITL]
  hitl --> ui
```

## Self-healing

Retryable: timeouts, network, 429/quota. Semantic errors can enter RECOVERING when `recovery_enabled` (default on new tasks). Not retried: SSRF, 401/403, CAPTCHA/OTP/MFA (those pause).

## Optional cloud mode

Diagrams under `docs/diagrams/14-terraform-gcp.md` and Pub/Sub worker notes describe **optional** GCP. They are not the local architecture.
