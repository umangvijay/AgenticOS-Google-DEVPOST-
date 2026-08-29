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
    url: str            # URL to API docs or a website
    name: Optional[str] = None
    method: Optional[str] = None  # url | website

class BuildFromPromptRequest(BaseModel):
    prompt: str         # Natural language description
    name: Optional[str] = None

class BuildFromWebsiteRequest(BaseModel):
    url: str
    name: Optional[str] = None
    notes: Optional[str] = None


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
#  BUILD (MCP Factory) — async jobs with persisted stages
# ══════════════════════════════════════════════════════════════════

async def _start_build(factory, user_id: str, method: str, source: str, name: Optional[str]) -> dict:
    """Create an mcp_builds record and run the factory pipeline in the background."""
    import asyncio
    import uuid

    from backend.agents.mcp_factory.mcp_factory_agent import MCPFactoryAgent

    build_id = str(uuid.uuid4())
    await factory.mcp_repo.create_build({
        "build_id": build_id,
        "user_id": user_id,
        "name": name or "",
        "method": method,
        "source": source[:2000],
        "status": "queued",
        "stage": "queued",
    })

    factory_agent = MCPFactoryAgent(factory.mcp_repo, secrets_repo=factory.secrets_repo)

    async def _run():
        try:
            from backend.services.llm_context import load_user_llm_keys
            await load_user_llm_keys(factory.secrets_repo, user_id)
            await factory_agent.run_build(
                user_id=user_id, method=method, source=source,
                name=name or "", build_id=build_id,
            )
        except Exception:
            logger.exception("Background MCP build %s crashed", build_id)
            try:
                await factory.mcp_repo.update_build(build_id, {"status": "error", "stage": "failed", "error": "Internal build crash"})
            except Exception:
                pass

    asyncio.create_task(_run())
    return {
        "build_id": build_id,
        "status": "queued",
        "message": "MCP Factory build started. Poll /integrations/builds/{build_id} for progress.",
    }


@router.post("/build", status_code=status.HTTP_202_ACCEPTED)
async def build_from_spec(
    body: BuildFromSpecRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Build an MCP integration from a raw OpenAPI/Swagger spec (JSON or YAML)."""
    factory = _get_factory(request)
    check_rate_limit(f"user:{user.user_id}", "mcp_build")

    try:
        spec_text = sanitize_text(body.spec, "spec", max_length=500_000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return await _start_build(factory, user.user_id, "spec", spec_text, body.name)


@router.post("/build-from-url", status_code=status.HTTP_202_ACCEPTED)
async def build_from_url(
    body: BuildFromURLRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Build from a URL pointing to an OpenAPI spec or API documentation."""
    factory = _get_factory(request)
    check_rate_limit(f"user:{user.user_id}", "mcp_build")

    try:
        url = sanitize_text(body.url, "url", max_length=2000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return await _start_build(factory, user.user_id, body.method or "url", url, body.name)


@router.post("/build-from-website", status_code=status.HTTP_202_ACCEPTED)
async def build_from_website(
    body: BuildFromWebsiteRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Build a Playwright website MCP for an app with no public API."""
    factory = _get_factory(request)
    check_rate_limit(f"user:{user.user_id}", "mcp_build")
    try:
        url = sanitize_text(body.url, "url", max_length=2000)
        notes = sanitize_text(body.notes or "", "notes", max_length=4000) if body.notes else ""
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    source = f"{url}\n{notes}".strip()
    return await _start_build(factory, user.user_id, "website", source, body.name)


@router.post("/build-from-prompt", status_code=status.HTTP_202_ACCEPTED)
async def build_from_prompt(
    body: BuildFromPromptRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Build from a natural language description (lands in pending-review trust tier)."""
    factory = _get_factory(request)
    check_rate_limit(f"user:{user.user_id}", "mcp_build")

    try:
        prompt = sanitize_text(body.prompt, "prompt", max_length=5000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return await _start_build(factory, user.user_id, "prompt", prompt, body.name)


@router.get("/builds/{build_id}")
async def get_build_status(
    build_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Poll the status, stage, and logs of an MCP factory build."""
    factory = _get_factory(request)
    build = await factory.mcp_repo.get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    if build.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")
    return build


# ══════════════════════════════════════════════════════════════════
#  TEST / HEALTH / ENABLE / DISABLE / DELETE
# ══════════════════════════════════════════════════════════════════

@router.post("/{mcp_id}/test")
async def test_integration(
    mcp_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Test an integration: validate cached tools and run a safe live GET probe if possible."""
    factory = _get_factory(request)
    mcp = await factory.mcp_repo.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="Integration not found")

    from datetime import datetime, timezone
    tools = await factory.mcp_repo.get_cached_tools(mcp_id=mcp_id)
    transport = str(mcp.get("transport") or "internal")

    try:
        if transport == "internal":
            if not tools:
                raise ValueError("No tools registered for this integration")
            # Live probe: first GET tool with no required arguments
            probe = {"status": "skipped", "reason": "no parameterless GET tool"}
            for tool in tools:
                op = tool.get("operation") or {}
                required = (tool.get("input_schema") or {}).get("required") or []
                if op.get("http_method") == "GET" and not required:
                    from backend.mcp.openapi_executor import execute_openapi_tool
                    result = await execute_openapi_tool(
                        mcp, tool, {}, user_id=user.user_id, secrets_repo=factory.secrets_repo,
                    )
                    probe = {"status": "probed", "ok": result.get("ok"), "http_status": result.get("status")}
                    break
            healthy = probe.get("status") == "skipped" or probe.get("ok") is not False
            await factory.mcp_repo.update_mcp_health(
                mcp_id, "HEALTHY" if healthy else "UNHEALTHY", datetime.now(timezone.utc)
            )
            (circuit_breaker.record_success if healthy else circuit_breaker.record_failure)(mcp_id)
            return {
                "status": "healthy" if healthy else "unhealthy",
                "tools_discovered": len(tools),
                "probe": probe,
            }

        # Remote MCP server (streamable HTTP / stdio)
        from backend.mcp.mcp_client import MCPClientManager
        discovered = await MCPClientManager.list_tools(mcp)
        await factory.mcp_repo.update_mcp_health(mcp_id, "HEALTHY", datetime.now(timezone.utc))
        circuit_breaker.record_success(mcp_id)
        return {"status": "healthy", "tools_discovered": len(discovered) if discovered else 0}
    except Exception as e:
        await factory.mcp_repo.update_mcp_health(
            mcp_id, "UNHEALTHY", datetime.now(timezone.utc)
        )
        circuit_breaker.record_failure(mcp_id)
        return {"status": "unhealthy", "error": str(e)}


# ══════════════════════════════════════════════════════════════════
#  CREDENTIALS
# ══════════════════════════════════════════════════════════════════

class CredentialsRequest(BaseModel):
    api_key: str
    auth_type: Optional[str] = "API_KEY"   # API_KEY | OAUTH2 | BASIC


@router.post("/{mcp_id}/credentials")
async def set_credentials(
    mcp_id: str, body: CredentialsRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Store an encrypted credential for this integration and link it via credential_ref."""
    factory = _get_factory(request)
    mcp = await factory.mcp_repo.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="Integration not found")
    if mcp.get("owner") not in (user.user_id, "system") and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        api_key = sanitize_text(body.api_key, "api_key", max_length=4000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    from backend.security.secrets_vault import secrets_vault
    credential_ref = f"mcp:{mcp_id}:api_key"
    encrypted = secrets_vault.encrypt(api_key)
    await factory.secrets_repo.store_secret(user.user_id, credential_ref, encrypted)

    auth = mcp.get("auth") or {}
    if isinstance(auth, str):
        import json as _json
        auth = _json.loads(auth)
    auth["type"] = (body.auth_type or "API_KEY").upper()
    auth["credential_ref"] = credential_ref
    await factory.mcp_repo.update_mcp_auth(mcp_id, auth)

    await factory.audit_repo.log_event({
        "event_type": "MCP_CREDENTIALS_SET",
        "actor_id": user.user_id, "actor_type": "USER",
        "resource_id": mcp_id,
        "details": {"auth_type": auth["type"]},
    })

    return {"mcp_id": mcp_id, "credential_ref": credential_ref, "auth_type": auth["type"]}


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
