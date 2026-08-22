import logging
from typing import Dict, Any, List, Optional
from backend.repositories.mcp_repository import MCPRepository
from backend.mcp.tool_policy import ToolPolicy
from backend.mcp.mcp_client import MCPClientManager

logger = logging.getLogger(__name__)

class ToolRouterError(Exception):
    pass

class ToolRouter:
    def __init__(self, mcp_repo: MCPRepository, policy: ToolPolicy):
        self.mcp_repo = mcp_repo
        self.policy = policy

    async def get_tool_catalog(self) -> List[Dict[str, Any]]:
        """Returns the list of tools that the agent is allowed to use."""
        tools = self.mcp_repo.get_cached_tools()
        catalog = []
        for t in tools:
            mcp = self.mcp_repo.get_mcp(t.mcp_id)
            if not mcp:
                continue
                
            policy_result = self.policy.is_allowed(t, mcp)
            if policy_result.allowed:
                catalog.append({
                    "name": t.tool_name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                    # We inject an internal mapping reference if needed, 
                    # but tool_name should be unique or prefixed by mcp_id.
                    # For Phase 3, we prepend mcp_id to tool_name to ensure uniqueness.
                    "agent_tool_name": f"{t.mcp_id}__{t.tool_name}"
                })
        return catalog

    async def execute_tool(self, agent_tool_name: str, arguments: Dict[str, Any]) -> Any:
        """The absolute and ONLY execution boundary for external tools."""
        if "__" not in agent_tool_name:
            raise ToolRouterError(f"Invalid tool name format: {agent_tool_name}")
            
        mcp_id, tool_name = agent_tool_name.split("__", 1)
        
        # 1. Resolve MCP
        mcp = self.mcp_repo.get_mcp(mcp_id)
        if not mcp:
            raise ToolRouterError(f"Unknown MCP Server: {mcp_id}")

        # 2. Resolve Tool in Catalog
        cached_tools = self.mcp_repo.get_cached_tools(mcp_id)
        tool = next((t for t in cached_tools if t.tool_name == tool_name), None)
        if not tool:
            raise ToolRouterError(f"Unknown tool '{tool_name}' on MCP '{mcp_id}'")

        # 3. Enforce Policy
        policy_result = self.policy.is_allowed(tool, mcp)
        if not policy_result.allowed:
            raise ToolRouterError(f"Policy Denied: {policy_result.reason}")

        # 4. Execute via MCP Client
        try:
            logger.info(f"ToolRouter executing {tool_name} on {mcp_id}")
            result = await MCPClientManager.call_tool(mcp, tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"MCP execution failed: {e}")
            raise ToolRouterError(f"MCP execution failed: {e}")
