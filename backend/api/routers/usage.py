"""
AgentOS — Context / token usage

GET /api/v1/usage/context

Live breakdown of how much of the model's context window is occupied
for this user right now: system instruction, registered tools, recent
conversation, and memory. Values are estimated from real catalog/run/memory
bytes (~4 characters per token).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies.auth import AuthenticatedUser, get_current_user
from backend.config.settings import settings
from backend.agents.planner.planner_agent import CORE_NODES_DOC

router = APIRouter(prefix="/usage", tags=["usage"])

CONTEXT_WINDOW = 256_000  # product context budget shown in the UI
CHARS_PER_TOKEN = 4


def _tokens(text: str) -> int:
    if not text:
        return 0
    return max(0, (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN)


def _get_factory(request: Request):
    return getattr(request.app.state, "factory", None)


def _run_blob(run: Dict[str, Any]) -> str:
    parts = [str(run.get("goal") or "")]
    for task in run.get("tasks") or []:
        parts.append(str(task.get("task_id") or ""))
        parts.append(json.dumps(task.get("output_data") or {}, default=str)[:4000])
        parts.append(str(task.get("error") or ""))
    return "\n".join(parts)


@router.get("/context")
async def get_context_usage(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    factory = _get_factory(request)
    tool_router = getattr(request.app.state, "tool_router", None)

    catalog: List[Any] = []
    if tool_router:
        try:
            catalog = await tool_router.get_tool_catalog(user.user_id) or []
        except Exception:
            catalog = []

    system_prompt = (
        "You are the Orchestrator Agent. Execute the given task using the best available capability. "
        "Build missing integrations, browse websites, send mail, check site health, debug code, "
        "generate projects, and create ATS resumes."
    )
    tool_blob = json.dumps(catalog, default=str)
    core_tools = (
        "call_external_tool build_integration browse_website send_email list_stored_credentials "
        "check_website_health debug_code generate_project create_resume analyze_resume_ats tailor_resume"
    )

    conversation = ""
    daily_used = 0
    today = datetime.now(timezone.utc).date().isoformat()
    if factory:
        try:
            runs = await factory.workflow_repo.list_runs(user.user_id, limit=12, offset=0)
            blobs = []
            for run in runs[:8]:
                blob = _run_blob(run)
                blobs.append(blob)
                created = str(run.get("created_at") or "")
                if created.startswith(today):
                    daily_used += _tokens(blob)
            conversation = "\n\n".join(blobs)
        except Exception:
            conversation = ""

    memory_blob = ""
    daily_limit = settings.DEFAULT_DAILY_TOKEN_LIMIT
    model = settings.GEMINI_MODEL
    if factory:
        try:
            memories = await factory.memory_repo.list_memories(user.user_id, limit=8)
            if memories:
                memory_blob = "\n".join(str(m.get("content") or "") for m in memories)
        except Exception:
            memory_blob = ""
        try:
            user_settings = await factory.settings_repo.get_settings(user.user_id)
            if user_settings:
                if user_settings.get("daily_token_limit"):
                    daily_limit = int(user_settings["daily_token_limit"])
                if user_settings.get("default_model"):
                    model = str(user_settings["default_model"])
        except Exception:
            pass

    categories = [
        {"id": "system", "label": "System prompt", "tokens": _tokens(system_prompt)},
        {"id": "tools", "label": "Tool definitions", "tokens": _tokens(tool_blob) + _tokens(core_tools)},
        {"id": "mcp", "label": "MCP & dynamic tools", "tokens": _tokens(json.dumps([t.get("name") for t in catalog], default=str))},
        {"id": "subagents", "label": "Subagent definitions", "tokens": _tokens(CORE_NODES_DOC)},
        {"id": "conversation", "label": "Conversation", "tokens": _tokens(conversation)},
        {"id": "memory", "label": "Memory", "tokens": _tokens(memory_blob)},
    ]
    used = sum(c["tokens"] for c in categories)
    remaining = max(0, CONTEXT_WINDOW - used)
    pct = min(100.0, round(100.0 * used / CONTEXT_WINDOW, 1)) if CONTEXT_WINDOW else 0
    daily_remaining = max(0, daily_limit - daily_used)

    return {
        "window_tokens": CONTEXT_WINDOW,
        "used_tokens": used,
        "remaining_tokens": remaining,
        "percent": pct,
        "daily_limit": daily_limit,
        "daily_used": daily_used,
        "daily_remaining": daily_remaining,
        "model": model,
        "tool_count": len(catalog),
        "categories": categories,
    }
