"""Per-request LLM key overrides so users can bring their own Gemini / Grok keys."""

from contextvars import ContextVar
from typing import Any, Dict, Optional

from backend.config.settings import settings

_user_gemini_key: ContextVar[Optional[str]] = ContextVar("user_gemini_key", default=None)
_user_grok_key: ContextVar[Optional[str]] = ContextVar("user_grok_key", default=None)


def set_user_gemini_key(key: Optional[str]) -> None:
    _user_gemini_key.set((key or "").strip() or None)


def get_user_gemini_key() -> Optional[str]:
    return _user_gemini_key.get()


def set_user_grok_key(key: Optional[str]) -> None:
    _user_grok_key.set((key or "").strip() or None)


def get_user_grok_key() -> Optional[str]:
    return _user_grok_key.get()


def effective_gemini_key() -> Optional[str]:
    return get_user_gemini_key() or settings.GEMINI_API_KEY


def effective_grok_key() -> Optional[str]:
    return get_user_grok_key() or settings.XAI_API_KEY


def gemini_adk_kwargs() -> Dict[str, Any]:
    """Client kwargs for ADK Gemini so BYOK vault keys reach planner/orchestrator."""
    key = effective_gemini_key()
    if key:
        return {"api_key": key}
    return {
        "vertexai": True,
        "project": settings.GOOGLE_CLOUD_PROJECT,
        "location": settings.GOOGLE_CLOUD_REGION,
    }


async def _load_named_key(secrets_repo, user_id: str, name: str, fields: tuple) -> Optional[str]:
    try:
        from backend.api.routers.credentials import load_credential
        cred = await load_credential(secrets_repo, user_id, name)
        for field in fields:
            val = cred.get(field)
            if isinstance(val, str) and val.strip():
                return val.strip()
    except Exception:
        return None
    return None


async def load_user_gemini_key(secrets_repo, user_id: str) -> Optional[str]:
    key = await _load_named_key(
        secrets_repo, user_id, "gemini", ("api_key", "key", "GEMINI_API_KEY")
    )
    set_user_gemini_key(key)
    return key


async def load_user_grok_key(secrets_repo, user_id: str) -> Optional[str]:
    key = await _load_named_key(
        secrets_repo, user_id, "grok", ("api_key", "key", "XAI_API_KEY", "GROK_API_KEY")
    )
    set_user_grok_key(key)
    return key


async def load_user_llm_keys(secrets_repo, user_id: str) -> None:
    """Load vault Gemini + Grok keys into this task's context. Safe to call with None repo."""
    if not secrets_repo or not user_id:
        set_user_gemini_key(None)
        set_user_grok_key(None)
        return
    await load_user_gemini_key(secrets_repo, user_id)
    await load_user_grok_key(secrets_repo, user_id)
