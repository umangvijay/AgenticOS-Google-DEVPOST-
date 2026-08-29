from backend.models.mcp_schemas import MCPManifest, CachedToolDefinition, ToolPolicyResult, MCPHealthStatus

class ToolPolicy:
    def is_allowed(self, tool: CachedToolDefinition, mcp: MCPManifest, context: dict = None) -> ToolPolicyResult:
        if not mcp.is_enabled:
            return ToolPolicyResult(allowed=False, reason="MCP is disabled")

        # Health is informational — intermittent upstream 5xx should not block catalog or execution.
        if tool.mcp_id != mcp.mcp_id:
            return ToolPolicyResult(allowed=False, reason="Tool does not belong to this MCP")

        return ToolPolicyResult(allowed=True)
