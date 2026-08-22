import logging
from datetime import datetime, timezone
from backend.repositories.mcp_repository import MCPRepository
from backend.models.mcp_schemas import MCPHealthStatus, MCPTransportType
from backend.mcp.mcp_client import MCPClientManager

logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, mcp_repo: MCPRepository):
        self.mcp_repo = mcp_repo

    async def check_all(self):
        """Iterate all MCPs and check their health."""
        mcps = self.mcp_repo.list_mcps()
        for mcp in mcps:
            if not mcp.is_enabled:
                continue
                
            now = datetime.now(timezone.utc)
            try:
                # Two-level check: We use discover_tools which connects and initializes (Protocol Check)
                # This inherently does the connectivity check as well.
                tools = await MCPClientManager.discover_tools(mcp)
                
                # Update health
                self.mcp_repo.update_mcp_health(mcp.mcp_id, MCPHealthStatus.HEALTHY, now)
                
                # Automatically cache the discovered tools!
                self.mcp_repo.cache_tools(mcp.mcp_id, tools)
                logger.info(f"Health check passed for {mcp.mcp_id}. Discovered {len(tools)} tools.")
                
            except Exception as e:
                logger.warning(f"Health check failed for {mcp.mcp_id}: {e}")
                self.mcp_repo.update_mcp_health(mcp.mcp_id, MCPHealthStatus.UNHEALTHY, now)
