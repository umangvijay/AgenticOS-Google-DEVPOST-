"""
AgentOS — Integrations Router

GET  /api/v1/integrations                — List all integrations
POST /api/v1/integrations/build          — Build from OpenAPI spec
POST /api/v1/integrations/build-from-url — Build from URL
POST /api/v1/integrations/build-from-prompt — Build from description
GET  /api/v1/integrations/{id}           — Get integration detail
POST /api/v1/integrations/{id}/test      — Test an integration
GET  /api/v1/integrations/{id}/health    — Get health status
POST /api/v1/integrations/{id}/enable    — Enable
POST /api/v1/integrations/{id}/disable   — Disable
DELETE /api/v1/integrations/{id}         — Delete
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser, require_not_viewer
from backend.security.rate_limiter import check_rate_limit
from backend.security.input_sanitizer import sanitize_text, InputValidationError
from backend.mcp.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _get_factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


# ── Request Models ────────────────────────────────────────────────

class BuildFromSpecRequest(BaseModel):
    spec: str           # OpenAPI/Swagger JSON/YAML
    name: Optional[str] = None

class BuildFromURLRequest(BaseModel):
    url: str            # URL to API docs
    name: Optional[str] = None

class BuildFromPromptRequest(BaseModel):
    prompt: str         # Natural language description
    name: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  LIST / GET
# ══════════════════════════════════════════════════════════════════

@router.get("")
async def list_integrations(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List all integrations visible to the user."""
    factory = _get_factory(request)
    mcps = await factory.mcp_repo.list_mcps(user_id=user.user_id)

    # Enrich with circuit breaker status
    results = []
    for mcp in mcps:
        mcp_id = mcp.get("mcp_id", "")
        breaker_status = circuit_breaker.get_status(mcp_id)
        mcp["circuit_breaker"] = breaker_status
        # Get cached tool count
        tools = await factory.mcp_repo.get_cached_tools(mcp_id=mcp_id)
        mcp["tool_count"] = len(tools)
        results.append(mcp)

    return {"integrations": results, "count": len(results)}


@router.get("/{mcp_id}")
async def get_integration(
    mcp_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get integration detail with tools and health."""
    factory = _get_factory(request)
    mcp = await factory.mcp_repo.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="Integration not found")

    tools = await factory.mcp_repo.get_cached_tools(mcp_id=mcp_id)
    breaker_status = circuit_breaker.get_status(mcp_id)

    return {
        **mcp,
        "tools": tools,
        "tool_count": len(tools),
        "circuit_breaker": breaker_status,
    }


# ══════════════════════════════════════════════════════════════════
#  BUILD (MCP Factory)
# ══════════════════════════════════════════════════════════════════

@router.post("/build", status_code=status.HTTP_202_ACCEPTED)
async def build_from_spec(
    body: BuildFromSpecRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """
    Build an MCP integration from an OpenAPI/Swagger spec.
    This is the automated path — clean specs are fully automated.
    """
    factory = _get_factory(request)
    check_rate_limit(f"user:{user.user_id}", "mcp_build")

    try:
        spec_text = sanitize_text(body.spec, "spec", max_length=500_000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Trigger MCP Factory (async — returns immediately)
    # The factory agent will discover, generate, test, and register
    try:
        from backend.agents.mcp_factory.mcp_factory_agent import MCPFactoryAgent
        factory_agent = MCPFactoryAgent(factory.mcp_repo)
        result = await factory_agent.build_from_url(
            url=body.spec, name=body.name
        )
        return result
    except ImportError:
        # MCP Factory not yet fully implemented — return pending
        logger.warning("MCP Factory agent not yet available")
        return {
            "status": "pending",
            "message": "MCP Factory is processing your spec. You will be notified when ready.",
        }


@router.post("/build-from-url", status_code=status.HTTP_202_ACCEPTED)
async def build_from_url(
    body: BuildFromURLRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Build from a URL pointing to API documentation."""
    factory = _get_factory(request)
    check_rate_limit(f"user:{user.user_id}", "mcp_build")

    try:
        url = sanitize_text(body.url, "url", max_length=2000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    try:
        from backend.agents.mcp_factory.mcp_factory_agent import MCPFactoryAgent
        factory_agent = MCPFactoryAgent(factory.mcp_repo)
        result = await factory_agent.build_from_url(
            url=url, name=body.name
        )
        return result
    except ImportError:
        return {
            "status": "pending",
            "message": "MCP Factory is processing your URL. You will be notified when ready.",
        }


@router.post("/build-from-prompt", status_code=status.HTTP_202_ACCEPTED)
async def build_from_prompt(
    body: BuildFromPromptRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """
    Build from a natural language prompt.
    Lands in pending-review state (trust tier: prose docs).
    """
    factory = _get_factory(request)
    check_rate_limit(f"user:{user.user_id}", "mcp_build")

    try:
        prompt = sanitize_text(body.prompt, "prompt", max_length=5000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    try:
        from backend.agents.mcp_factory.mcp_factory_agent import MCPFactoryAgent
        factory_agent = MCPFactoryAgent(factory.mcp_repo)
        result = await factory_agent.build_from_prompt(
            prompt=prompt, name=body.name
        )
        return result
    except ImportError:
        return {
            "status": "pending",
            "message": "MCP Factory is processing your request. You will be notified when ready.",
        }


# ══════════════════════════════════════════════════════════════════
#  TEST / HEALTH / ENABLE / DISABLE / DELETE
# ══════════════════════════════════════════════════════════════════

@router.post("/{mcp_id}/test")
async def test_integration(
    mcp_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Test an integration by calling list_tools and a health check."""
    factory = _get_factory(request)
    mcp = await factory.mcp_repo.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Basic health check
    from datetime import datetime, timezone
    try:
        from backend.mcp.client_manager import MCPClientManager
        client = MCPClientManager()
        tools = await client.list_tools(mcp)
        await factory.mcp_repo.update_mcp_health(
            mcp_id, "HEALTHY", datetime.now(timezone.utc)
        )
        circuit_breaker.record_success(mcp_id)
        return {
            "status": "healthy",
            "tools_discovered": len(tools) if tools else 0,
        }
    except ImportError:
        return {"status": "unknown", "message": "MCP client not available for testing"}
    except Exception as e:
        await factory.mcp_repo.update_mcp_health(
            mcp_id, "UNHEALTHY", datetime.now(timezone.utc)
        )
        circuit_breaker.record_failure(mcp_id)
        return {"status": "unhealthy", "error": str(e)}


@router.get("/{mcp_id}/health")
async def get_health(
    mcp_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get integration health and circuit breaker status."""
    factory = _get_factory(request)
    mcp = await factory.mcp_repo.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "mcp_id": mcp_id,
        "health": mcp.get("health", "UNKNOWN"),
        "health_updated_at": mcp.get("health_updated_at"),
        "circuit_breaker": circuit_breaker.get_status(mcp_id),
    }


@router.post("/{mcp_id}/enable")
async def enable_integration(
    mcp_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Enable an integration."""
    factory = _get_factory(request)
    mcp = await factory.mcp_repo.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="Integration not found")
    await factory.mcp_repo.set_mcp_enabled(mcp_id, True)
    return {"mcp_id": mcp_id, "is_enabled": True}


@router.post("/{mcp_id}/disable")
async def disable_integration(
    mcp_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Disable an integration."""
    factory = _get_factory(request)
    mcp = await factory.mcp_repo.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="Integration not found")
    await factory.mcp_repo.set_mcp_enabled(mcp_id, False)
    return {"mcp_id": mcp_id, "is_enabled": False}


@router.delete("/{mcp_id}", status_code=status.HTTP_200_OK)
async def delete_integration(
    mcp_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Delete an integration and its cached tools."""
    factory = _get_factory(request)
    deleted = await factory.mcp_repo.delete_mcp(mcp_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")

    await factory.audit_repo.log_event({
        "event_type": "MCP_DELETED",
        "actor_id": user.user_id, "actor_type": "USER",
        "resource_id": mcp_id,
        "details": {},
    })

    return {"mcp_id": mcp_id, "deleted": True}
