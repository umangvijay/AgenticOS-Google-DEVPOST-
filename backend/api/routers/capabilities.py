"""
Direct capability endpoints so any of these jobs can run without waiting on the planner.

POST /api/v1/capabilities/site-health
POST /api/v1/capabilities/debug
POST /api/v1/capabilities/generate
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.api.dependencies.auth import AuthenticatedUser, require_not_viewer
from backend.security.rate_limiter import check_rate_limit

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


class SiteHealthRequest(BaseModel):
    url: str


class DebugRequest(BaseModel):
    source: str
    language: str = "python"
    error_message: str = ""
    goal: str = ""


class GenerateRequest(BaseModel):
    brief: str
    kind: str = "website"
    name: str = ""
    scale: str = "standard"


async def _apply_user_key(request, user_id: str) -> None:
    factory = getattr(request.app.state, "factory", None)
    if factory:
        from backend.services.llm_context import load_user_llm_keys
        await load_user_llm_keys(factory.secrets_repo, user_id)


@router.post("/site-health")
async def site_health(body: SiteHealthRequest, request: Request, user: AuthenticatedUser = Depends(require_not_viewer)):
    check_rate_limit(f"user:{user.user_id}", "general")
    try:
        from backend.services.website_health import check_website
        return await check_website(body.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/debug")
async def debug(body: DebugRequest, request: Request, user: AuthenticatedUser = Depends(require_not_viewer)):
    check_rate_limit(f"user:{user.user_id}", "general")
    await _apply_user_key(request, user.user_id)
    try:
        from backend.services.code_debugger import debug_code
        return await debug_code(body.source, body.language, body.error_message, body.goal)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ping")
async def ping_gemini(request: Request, user: AuthenticatedUser = Depends(require_not_viewer)):
    """Cheap check that the shared or vault Gemini key can complete a request."""
    check_rate_limit(f"user:{user.user_id}", "general")
    await _apply_user_key(request, user.user_id)
    try:
        from backend.services import gemini_client
        from backend.services.llm_context import get_user_gemini_key
        reply = await gemini_client.generate_text("Reply with exactly: PONG")
        return {
            "ok": "PONG" in (reply or "").upper(),
            "reply": (reply or "")[:80],
            "using_user_key": bool(get_user_gemini_key()),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate")
async def generate(body: GenerateRequest, request: Request, user: AuthenticatedUser = Depends(require_not_viewer)):
    check_rate_limit(f"user:{user.user_id}", "general")
    await _apply_user_key(request, user.user_id)
    try:
        from backend.services.artifact_builder import generate_project
        return await generate_project(user.user_id, body.brief, kind=body.kind, name=body.name, scale=body.scale)
    except Exception as e:
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota exhausted" in msg.lower() or "UNAUTHENTICATED" in msg:
            raise HTTPException(
                status_code=429,
                detail="Gemini quota is exhausted. Add your own Gemini key or an xAI Grok key in Settings to generate a website or app.",
            )
        raise HTTPException(status_code=400, detail=msg)
