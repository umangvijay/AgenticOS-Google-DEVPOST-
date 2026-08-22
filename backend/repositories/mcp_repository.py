from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from backend.models.mcp_schemas import MCPManifest, CachedToolDefinition, MCPHealthStatus

class MCPRepository(ABC):
    @abstractmethod
    def register_mcp(self, manifest: MCPManifest) -> None:
        pass

    @abstractmethod
    def get_mcp(self, mcp_id: str) -> Optional[MCPManifest]:
        pass

    @abstractmethod
    def list_mcps(self) -> List[MCPManifest]:
        pass

    @abstractmethod
    def update_mcp_health(self, mcp_id: str, status: MCPHealthStatus, timestamp: datetime) -> None:
        pass
        
    @abstractmethod
    def set_mcp_enabled(self, mcp_id: str, enabled: bool) -> None:
        pass

    @abstractmethod
    def cache_tools(self, mcp_id: str, tools: List[CachedToolDefinition]) -> None:
        pass
        
    @abstractmethod
    def get_cached_tools(self, mcp_id: Optional[str] = None) -> List[CachedToolDefinition]:
        """Get all cached tools, optionally filtered by mcp_id"""
        pass
