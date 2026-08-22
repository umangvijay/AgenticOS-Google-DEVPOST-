from typing import List, Optional, Dict
from datetime import datetime, timezone
from backend.models.mcp_schemas import MCPManifest, CachedToolDefinition, MCPHealthStatus
from backend.repositories.mcp_repository import MCPRepository

class InMemoryMCPRepository(MCPRepository):
    def __init__(self):
        self._mcps: Dict[str, MCPManifest] = {}
        self._tools: Dict[str, CachedToolDefinition] = {}

    def register_mcp(self, manifest: MCPManifest) -> None:
        self._mcps[manifest.mcp_id] = manifest

    def get_mcp(self, mcp_id: str) -> Optional[MCPManifest]:
        return self._mcps.get(mcp_id)

    def list_mcps(self) -> List[MCPManifest]:
        return list(self._mcps.values())

    def update_mcp_health(self, mcp_id: str, status: MCPHealthStatus, timestamp: datetime) -> None:
        mcp = self.get_mcp(mcp_id)
        if mcp:
            mcp.health = status
            mcp.health_updated_at = timestamp
            mcp.updated_at = datetime.now(timezone.utc)

    def set_mcp_enabled(self, mcp_id: str, enabled: bool) -> None:
        mcp = self.get_mcp(mcp_id)
        if mcp:
            mcp.is_enabled = enabled
            mcp.updated_at = datetime.now(timezone.utc)

    def cache_tools(self, mcp_id: str, tools: List[CachedToolDefinition]) -> None:
        # Remove old tools for this MCP
        keys_to_delete = [k for k, v in self._tools.items() if v.mcp_id == mcp_id]
        for k in keys_to_delete:
            del self._tools[k]
            
        for tool in tools:
            self._tools[f"{mcp_id}:{tool.tool_name}"] = tool

    def get_cached_tools(self, mcp_id: Optional[str] = None) -> List[CachedToolDefinition]:
        now = datetime.now(timezone.utc)
        result = []
        for tool in self._tools.values():
            # Exclude expired tools
            if tool.expires_at > now:
                if mcp_id is None or tool.mcp_id == mcp_id:
                    result.append(tool)
        return result
