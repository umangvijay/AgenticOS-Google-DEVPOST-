import logging
from typing import Dict, Any, List, Optional
from backend.repositories.mcp_repository import MCPRepository
from backend.mcp.tool_policy import ToolPolicy
from backend.mcp.mcp_client import MCPClientManager
from backend.services.approvals_engine import ApprovalsEngine, ApprovalRequiredException
from backend.models.security import AutonomyLevel
from backend.mcp.circuit_breaker import circuit_breaker
from backend.engine.idempotency_guard import IdempotencyGuard

logger = logging.getLogger(__name__)

class ToolRouterError(Exception):
    pass

class ToolRouter:
    def __init__(self, mcp_repo: MCPRepository, policy: ToolPolicy, approvals_engine: Optional[ApprovalsEngine] = None, idempotency_repo=None):
        self.mcp_repo = mcp_repo
        self.policy = policy
        self.approvals_engine = approvals_engine
        self.idempotency_guard = IdempotencyGuard(idempotency_repo) if idempotency_repo else None

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

    async def execute_tool(self, agent_tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
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

        # 3.5. Evaluate Risk & Approvals (Phase 10)
        context = context or {}
        if self.approvals_engine:
            autonomy_level = context.get("autonomy_level", AutonomyLevel.L0_MANUAL)
            if self.approvals_engine.requires_approval(autonomy_level, tool.risk_level):
                # Is there a pre-approved request passed in context?
                approved_request = context.get("approved_request")
                if approved_request:
                    self.approvals_engine.validate_approval_for_execution(approved_request, arguments)
                    logger.info(f"Execution authorized by approval {approved_request.approval_id}")
                else:
                    # Request an approval
                    pending_approval = self.approvals_engine.create_approval_request(
                        user_id=context.get("user_id", "system"),
                        tool_name=tool_name,
                        tool_version=tool.mcp_version,
                        risk_level=tool.risk_level,
                        autonomy_level=autonomy_level,
                        arguments=arguments,
                        workflow_id=context.get("workflow_id", "unknown"),
                        run_id=context.get("run_id", "unknown"),
                        task_id=context.get("task_id", "unknown")
                    )
                    raise ApprovalRequiredException("Human approval is required for this action.", pending_approval)

        # 4. Execute via MCP Client
        try:
            logger.info(f"ToolRouter executing {tool_name} on {mcp_id}")
            
            # Inject trace context
            from opentelemetry.propagate import inject
            trace_headers = {}
            inject(trace_headers)
            
            result = await MCPClientManager.call_tool(mcp, tool_name, arguments, extra_headers=trace_headers)
            return result
        except Exception as e:
            logger.error(f"MCP execution failed: {e}")
            raise ToolRouterError(f"MCP execution failed: {e}")

    async def execute_tool_safe(self, agent_tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Safe execution wrapper that integrates the Circuit Breaker and Idempotency Guard.
        """
        if "__" not in agent_tool_name:
            raise ToolRouterError(f"Invalid tool name format: {agent_tool_name}")
            
        mcp_id, tool_name = agent_tool_name.split("__", 1)
        
        # 1. Circuit Breaker Check
        if circuit_breaker.get_status(mcp_id) == "OPEN":
            raise ToolRouterError("BLOCKED_UPSTREAM_OUTAGE")

        async def _execute():
            # Perform actual execution logic including approvals
            return await self.execute_tool(agent_tool_name, arguments, context)

        # 2. Idempotency Check & Execution
        workflow_id = context.get("workflow_id", "unknown") if context else "unknown"
        task_id = context.get("task_id", "unknown") if context else "unknown"

        try:
            if self.idempotency_guard and workflow_id != "unknown" and task_id != "unknown":
                result = await self.idempotency_guard.execute_once(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    tool_name=agent_tool_name,
                    arguments=arguments,
                    execute_fn=_execute
                )
                
                if result.blocked:
                    raise ToolRouterError(f"Idempotency blocked execution: {result.reason}")
                
                output = result.result
            else:
                # Fallback if no idempotency repo or context
                output = await _execute()

            # 3. Record success to circuit breaker
            circuit_breaker.record_success(mcp_id)
            return output
        except Exception as e:
            circuit_breaker.record_failure(mcp_id)
            raise

