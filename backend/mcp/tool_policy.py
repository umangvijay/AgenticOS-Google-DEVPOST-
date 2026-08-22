from backend.models.mcp_schemas import MCPManifest, CachedToolDefinition, ToolPolicyResult, MCPHealthStatus

class ToolPolicy:
    def is_allowed(self, tool: CachedToolDefinition, mcp: MCPManifest, context: dict = None) -> ToolPolicyResult:
        if not mcp.is_enabled:
            return ToolPolicyResult(allowed=False, reason="MCP is disabled")
            
        if mcp.health == MCPHealthStatus.UNHEALTHY:
            return ToolPolicyResult(allowed=False, reason="MCP is unhealthy")
            
        # Simplified Scope Policy for Phase 3
        # E.g. tools might require specific scopes. If we assume the tool_name itself 
        # or a top-level domain represents the scope, we can check it.
        # For Phase 3, we just check if the tool is registered to the MCP
        if tool.mcp_id != mcp.mcp_id:
            return ToolPolicyResult(allowed=False, reason="Tool does not belong to this MCP")
            
        return ToolPolicyResult(allowed=True)
