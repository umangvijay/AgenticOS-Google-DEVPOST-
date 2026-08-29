# MCP runtime (in-process catalog)

AgentOS does not spawn a separate MCP stdio server per user. The factory registers tools in the SQLite/Firestore catalog; the orchestrator calls them through the in-process tool router.

```mermaid
graph LR
    Chat[Workspace chat] --> Plan[Planner]
    Plan --> Build[core.mcp_build]
    Build --> Factory[MCP factory]
    Factory --> HTTP[HTTP tools]
    Factory --> Browser[Website Playwright tools]
    HTTP --> Catalog[User catalog]
    Browser --> Catalog
    Catalog --> Orch[Orchestrator]
    Orch --> Live[Live GET or headed/headless browser]
```

External MCP servers (JSON-RPC over stdio) remain a possible future adapter, not the local path.
