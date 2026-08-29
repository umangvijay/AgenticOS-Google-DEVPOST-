import logging
from typing import Dict, Any, List, Optional

from backend.repositories.mcp_repository import MCPRepository
from backend.mcp.tool_policy import ToolPolicy
from backend.mcp.mcp_client import MCPClientManager
from backend.mcp.openapi_executor import execute_openapi_tool
from backend.services.approvals_engine import ApprovalsEngine, ApprovalRequiredException
from backend.models.security import AutonomyLevel, RiskLevel
from backend.mcp.circuit_breaker import circuit_breaker
from backend.engine.idempotency_guard import IdempotencyGuard
from backend.models.mcp_schemas import CachedToolDefinition, MCPManifest, MCPHealthStatus, AuthMetadata, AuthType, MCPTransportType

logger = logging.getLogger(__name__)


class ToolRouterError(Exception):
    pass


def _as_manifest(mcp: Any) -> MCPManifest:
    if isinstance(mcp, MCPManifest):
        return mcp
    data = dict(mcp)
    auth = data.get("auth") or {}
    if isinstance(auth, str):
        import json
        try:
            auth = json.loads(auth)
        except Exception:
            auth = {"type": auth}
    data["auth"] = AuthMetadata(**auth) if isinstance(auth, dict) else AuthMetadata()
    if isinstance(data.get("transport"), str):
        try:
            data["transport"] = MCPTransportType(data["transport"])
        except ValueError:
            data["transport"] = MCPTransportType.INTERNAL
    return MCPManifest(**{k: v for k, v in data.items() if k in MCPManifest.model_fields})


def _as_tool(t: Any) -> CachedToolDefinition:
    if isinstance(t, CachedToolDefinition):
        return t
    data = dict(t)
    data.setdefault("tool_name", data.get("name") or "unknown")
    data.setdefault("mcp_version", "1.0.0")
    data.setdefault("input_schema", data.get("inputSchema") or {})
    from datetime import datetime, timezone
    data.setdefault("discovered_at", datetime.now(timezone.utc))
    data.setdefault("expires_at", datetime.now(timezone.utc))
    if "risk_level" in data and not isinstance(data["risk_level"], RiskLevel):
        try:
            data["risk_level"] = RiskLevel(int(data["risk_level"]))
        except Exception:
            data["risk_level"] = RiskLevel.CRITICAL
    return CachedToolDefinition(**{k: v for k, v in data.items() if k in CachedToolDefinition.model_fields})


class ToolRouter:
    def __init__(self, mcp_repo: MCPRepository, policy: ToolPolicy, approvals_engine: Optional[ApprovalsEngine] = None, idempotency_repo=None, secrets_repo=None):
        self.mcp_repo = mcp_repo
        self.policy = policy
        self.approvals_engine = approvals_engine
        self.idempotency_guard = IdempotencyGuard(idempotency_repo) if idempotency_repo else None
        self.secrets_repo = secrets_repo

    async def get_tool_catalog(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        tools = await self.mcp_repo.get_cached_tools()
        catalog = []
        for raw in tools:
            try:
                tool = _as_tool(raw)
                mcp_raw = await self.mcp_repo.get_mcp(tool.mcp_id)
                if not mcp_raw:
                    continue
                mcp = _as_manifest(mcp_raw)
                if user_id and mcp.owner not in (user_id, "system"):
                    continue
                if not mcp.is_enabled:
                    continue
                policy_result = self.policy.is_allowed(tool, mcp)
                if policy_result.allowed:
                    catalog.append({
                        "name": tool.tool_name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                        "agent_tool_name": f"{tool.mcp_id}__{tool.tool_name}",
                        "mcp_id": tool.mcp_id,
                        "mcp_name": mcp.name,
                    })
            except Exception:
                logger.exception("Skipping invalid catalog tool")
                continue
        return catalog

    async def execute_tool(self, agent_tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        if "__" not in agent_tool_name:
            raise ToolRouterError(f"Invalid tool name format: {agent_tool_name}")

        mcp_id, tool_name = agent_tool_name.split("__", 1)
        mcp_raw = await self.mcp_repo.get_mcp(mcp_id)
        if not mcp_raw:
            raise ToolRouterError(f"Unknown MCP Server: {mcp_id}")
        mcp = _as_manifest(mcp_raw)

        cached_tools = await self.mcp_repo.get_cached_tools(mcp_id)
        raw_tool = next((t for t in cached_tools if (t.get("tool_name") if isinstance(t, dict) else t.tool_name) == tool_name), None)
        if not raw_tool:
            raise ToolRouterError(f"Unknown tool '{tool_name}' on MCP '{mcp_id}'")
        tool = _as_tool(raw_tool)

        policy_result = self.policy.is_allowed(tool, mcp)
        if not policy_result.allowed:
            raise ToolRouterError(f"Policy Denied: {policy_result.reason}")

        context = context or {}
        if self.approvals_engine:
            autonomy_level = context.get("autonomy_level", AutonomyLevel.L0_MANUAL)
            if self.approvals_engine.requires_approval(autonomy_level, tool.risk_level):
                approved_request = context.get("approved_request")
                if approved_request:
                    if isinstance(approved_request, dict):
                        from backend.models.security import ApprovalRequest
                        approved_request = ApprovalRequest(**approved_request)
                    self.approvals_engine.validate_approval_for_execution(approved_request, arguments)
                else:
                    pending_approval = self.approvals_engine.create_approval_request(
                        user_id=context.get("user_id", "system"),
                        tool_name=tool_name,
                        tool_version=tool.mcp_version,
                        risk_level=tool.risk_level,
                        autonomy_level=autonomy_level,
                        arguments=arguments,
                        workflow_id=context.get("workflow_id", "unknown"),
                        run_id=context.get("run_id", "unknown"),
                        task_id=context.get("task_id", "unknown"),
                    )
                    raise ApprovalRequiredException("Human approval is required for this action.", pending_approval)

        transport = mcp.transport.value if hasattr(mcp.transport, "value") else str(mcp.transport)
        if transport == "internal" or (isinstance(raw_tool, dict) and raw_tool.get("operation")):
            try:
                return await execute_openapi_tool(
                    mcp.model_dump(mode="json"),
                    raw_tool if isinstance(raw_tool, dict) else tool.model_dump(mode="json"),
                    arguments,
                    user_id=context.get("user_id", "system"),
                    secrets_repo=self.secrets_repo,
                    run_id=context.get("run_id"),
                    task_id=context.get("task_id"),
                )
            except Exception as pause:
                from backend.services.auth_challenges import ChallengePause
                if not isinstance(pause, ChallengePause):
                    raise
                engine = self.approvals_engine or ApprovalsEngine()
                pending_approval = engine.create_approval_request(
                    user_id=context.get("user_id", "system"),
                    tool_name=tool_name,
                    tool_version=tool.mcp_version,
                    risk_level=RiskLevel.HIGH,
                    autonomy_level=context.get("autonomy_level", AutonomyLevel.L2_SEMI_AUTONOMOUS),
                    arguments={
                        **(arguments or {}),
                        "_challenge_type": pause.challenge_type,
                        "_challenge_url": pause.url,
                    },
                    workflow_id=context.get("workflow_id", "unknown"),
                    run_id=context.get("run_id", "unknown"),
                    task_id=context.get("task_id", "unknown"),
                )
                raise ApprovalRequiredException(pause.message, pending_approval) from pause

        try:
            from opentelemetry.propagate import inject
            trace_headers = {}
            inject(trace_headers)
            return await MCPClientManager.call_tool(mcp, tool_name, arguments, extra_headers=trace_headers)
        except Exception as e:
            logger.error("MCP execution failed: %s", e)
            raise ToolRouterError(f"MCP execution failed: {e}")

    async def execute_tool_safe(self, agent_tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        if "__" not in agent_tool_name:
            raise ToolRouterError(f"Invalid tool name format: {agent_tool_name}")
        mcp_id, _tool_name = agent_tool_name.split("__", 1)
        status = circuit_breaker.get_status(mcp_id)
        if status.get("state") == "OPEN":
            raise ToolRouterError("BLOCKED_UPSTREAM_OUTAGE")

        async def _execute():
            return await self.execute_tool(agent_tool_name, arguments, context)

        workflow_id = context.get("workflow_id", "unknown") if context else "unknown"
        task_id = context.get("task_id", "unknown") if context else "unknown"

        try:
            if self.idempotency_guard and workflow_id != "unknown" and task_id != "unknown":
                result = await self.idempotency_guard.execute_once(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    tool_name=agent_tool_name,
                    arguments=arguments,
                    execute_fn=_execute,
                )
                if result.blocked:
                    raise ToolRouterError(f"Idempotency blocked execution: {result.reason}")
                output = result.result
            else:
                output = await _execute()
            circuit_breaker.record_success(mcp_id)
            return output
        except ApprovalRequiredException:
            raise
        except Exception:
            circuit_breaker.record_failure(mcp_id)
            raise
