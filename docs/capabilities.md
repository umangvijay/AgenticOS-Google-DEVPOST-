# Capabilities

| Capability | How to use |
|---|---|
| Any-app MCP | Chat or Integrations: OpenAPI URL, HTTP description, or website URL |
| Browser actions | Chat + vault login; HITL pause on CAPTCHA/OTP/MFA |
| Email | Contact SMTP to the team (Gmail App Password); vault `smtp` or provider MCP for agents |
| Site health | Studio → Website health, or chat “check https://…” |
| Debug | Studio → Debug, or chat with the source and error |
| Generate site/app | Studio → Generate (compact / standard / full scale) |
| ATS resume | Resume page (PDF scan, notes, tailor, HTML download) |
| Memory | Stored per user; semantic search uses live embeddings |
| Context meter | Top bar — live token breakdown |
| Cloud host | Cloud Run + Secret Manager; see [deploy-gcp.md](deploy-gcp.md) |

## Generate scale

- **Compact** — small landing or utility (few files).
- **Standard** — medium multi-page site or complete local app (default).
- **Full** — large multi-module project (dozens of files, planned then filled in batches).

Generated files are stored per user and listed in Studio. Code is not executed on the server.

## MCP from chat (same as dashboard chips)

- OpenAPI: PokeAPI `openapi.yml` then list pokemon.
- HTTP, no spec: GitHub public events.
- Website: `example.com` homepage (CAPTCHA-free). Real portals: Vault name + Resume after challenge.
