# Plugin System Flow

```mermaid
graph TD
    Marketplace[Plugin Registry]
    Admin[Admin] -->|Install Plugin| Marketplace
    Marketplace -->|Download| LocalPlugins[Local Plugin Repo]
    Engine[Workflow Engine] -->|Load Tools| LocalPlugins
    LocalPlugins -->|Register| MCPServer[MCP Server]
```
