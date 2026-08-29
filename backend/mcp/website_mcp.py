"""Website MCP: tools for apps that have no public OpenAPI.

Each tool drives Playwright on a locked origin. The model proposes named
actions; execution is always a real browser session, never a fake HTTP API.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from backend.models.mcp_schemas import CachedToolDefinition
from backend.models.security import RiskLevel
from backend.services import gemini_client
from backend.services.web_agent import WebAgent, WebAgentError, _registrable_domain
from backend.services.auth_challenges import ChallengePause

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_]")
_URL = re.compile(r"https?://[^\s\"'<>]+", re.I)


def origin_from_url(url: str) -> str:
    parsed = urlparse(url if "://" in (url or "") else f"https://{url}")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"Not a usable website URL: {url}")
    return f"{parsed.scheme}://{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")


def default_start_url(source: str, origin: str) -> str:
    found = _URL.search(source or "")
    if found:
        return found.group(0).rstrip(").,;]")
    return origin.rstrip("/") + "/"


_WEBSITE_PHRASES = (
    "this website", "this site", "web app", "login page", "learner portal",
    "no openapi", "no open api", "no public api", "without an api", "without api",
    "browser tools", "browser mcp", "website mcp", "playwright",
)
_API_HOST_FRAGMENTS = (
    "pokeapi.", "open-meteo.", "openmeteo.", "httpbin.", "jsonplaceholder.",
    "googleapis.com", "api.github.com", "api.gitlab.com", "api.stripe.com",
)
_API_PATH_FRAGMENTS = ("/api/", "/v1/", "/v2/", "/v3/", "/rest/", "/graphql")


def looks_like_http_api_url(url: str) -> bool:
    """True when the URL is a REST/OpenAPI host, not a human website."""
    parsed = urlparse(url if "://" in (url or "") else f"https://{url}")
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if not host:
        return False
    if host.startswith("api.") or host.startswith("openapi."):
        return True
    if any(frag in host for frag in _API_HOST_FRAGMENTS):
        return True
    if any(frag in path for frag in _API_PATH_FRAGMENTS):
        return True
    return False


def looks_like_website_without_api(source: str, url: Optional[str] = None) -> bool:
    """True when the user wants origin-locked browser tools, not HTTP MCP tools."""
    text = source or ""
    lowered = text.lower()
    if "openapi" in lowered or "swagger" in lowered:
        return False
    target = url or ""
    if not target:
        found = _URL.search(text)
        target = found.group(0) if found else ""
    if target:
        u = target.lower()
        if u.endswith((".json", ".yaml", ".yml")) or "/openapi" in u or "/swagger" in u or "/api-docs" in u:
            return False
        if looks_like_http_api_url(target):
            return False
        fragment = target.split("#", 1)[1] if "#" in target else ""
        if fragment.strip("/"):
            return True
        if any(p in u for p in ("/login", "/signin", "/sign-in", "/auth/")):
            return True
    if any(w in lowered for w in _WEBSITE_PHRASES):
        return True
    if re.search(r"\b(rest|http api|endpoints?)\b", lowered) and "website" not in lowered:
        return False
    if target and not looks_like_http_api_url(target):
        if any(w in lowered for w in ("create tools", "build tools", "make tools", "mcp", "integration", "connector")):
            return True
        stripped = lowered.strip()
        if stripped.startswith("http"):
            return True
    return False


def _tool_name(raw: str, fallback: str) -> str:
    name = _SAFE_NAME.sub("", (raw or "").strip()) or fallback
    if name[0].isdigit():
        name = "t" + name
    return name[:48]


def _same_origin(candidate: str, origin: str) -> str:
    parsed = urlparse(candidate)
    origin_p = urlparse(origin)
    if not parsed.scheme:
        candidate = urljoin(origin.rstrip("/") + "/", candidate.lstrip("/"))
        parsed = urlparse(candidate)
    if _registrable_domain(parsed.hostname or "") != _registrable_domain(origin_p.hostname or ""):
        return origin
    return candidate


def _fallback_plan(origin: str, start_url: str, source: str) -> Dict[str, Any]:
    login = start_url if "/login" in start_url.lower() else origin.rstrip("/") + "/#/user/login"
    home = start_url if "/home" in start_url.lower() or start_url.rstrip("/").endswith(origin) else origin.rstrip("/") + "/#/home"
    if "/login" not in start_url.lower() and "#" in start_url:
        home = start_url
    return {
        "name": urlparse(origin).hostname or "website",
        "origin": origin,
        "tools": [
            {
                "name": "runOnSite",
                "description": f"Do any task on {origin} in a real browser (read, click, fill, navigate).",
                "start_url": start_url,
                "goal_template": "Complete the user's task on this website.",
                "needs_login": False,
            },
            {
                "name": "login",
                "description": f"Log in on {origin} using a Vault credential (username/email + password).",
                "start_url": login,
                "goal_template": "Log in with the stored site credential. Stop clearly if CAPTCHA or MFA blocks you.",
                "needs_login": True,
            },
            {
                "name": "openHome",
                "description": f"Open the main/home screen of {origin} and summarize what is visible.",
                "start_url": home,
                "goal_template": "Open the home page and describe the main actions available.",
                "needs_login": False,
            },
        ],
    }


async def plan_website_connector(source: str, origin: str, start_url: str) -> Dict[str, Any]:
    prompt = f"""You design browser tools for a website that has NO public OpenAPI.
Do not invent REST paths. Each tool is a named job a person would do in the UI.

ORIGIN (must not change): {origin}
DEFAULT START URL: {start_url}
USER REQUEST:
{source[:8000]}

Return JSON only:
{{
  "name": "short-kebab-name",
  "tools": [
    {{
      "name": "camelCaseName",
      "description": "what this tool does on the site",
      "start_url": "https://... full URL on the same origin, hash routes allowed",
      "goal_template": "instructions the browser agent should follow",
      "needs_login": false
    }}
  ]
}}
Always include runOnSite (free-text goal on the site). Include login if the site has a sign-in page.
3 to 8 tools. start_url must stay on {origin}.
"""
    try:
        payload = await gemini_client.generate_json(prompt)
        if isinstance(payload, dict) and payload.get("tools"):
            payload.setdefault("name", urlparse(origin).hostname)
            payload["origin"] = origin
            return payload
    except Exception as exc:
        logger.warning("Website MCP plan fell back to defaults: %s", exc)
    return _fallback_plan(origin, start_url, source)


def tools_from_plan(mcp_id: str, origin: str, start_url: str, plan: Dict[str, Any]) -> List[CachedToolDefinition]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=365)
    seen = set()
    out: List[CachedToolDefinition] = []
    raw_tools = list(plan.get("tools") or [])
    names = {str(t.get("name") or "").lower() for t in raw_tools if isinstance(t, dict)}
    if "runonsite" not in names:
        raw_tools.insert(0, _fallback_plan(origin, start_url, "")["tools"][0])

    for item in raw_tools[:10]:
        if not isinstance(item, dict):
            continue
        name = _tool_name(str(item.get("name") or ""), "siteTool")
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        needs_login = bool(item.get("needs_login"))
        start = _same_origin(str(item.get("start_url") or start_url), origin)
        props: Dict[str, Any] = {
            "goal": {"type": "string", "description": "What to do on the site. Overrides the default goal if set."},
            "credential_name": {"type": "string", "description": "Vault record name with username/email and password."},
            "start_url": {"type": "string", "description": "Optional page to open first (same site only)."},
        }
        required = ["credential_name"] if needs_login else []
        out.append(
            CachedToolDefinition(
                tool_name=name,
                description=str(item.get("description") or f"Work on {origin}"),
                input_schema={"type": "object", "properties": props, "required": required},
                mcp_id=mcp_id,
                mcp_version="1.0.0",
                discovered_at=now,
                expires_at=expires,
                risk_level=RiskLevel.MEDIUM if needs_login else RiskLevel.LOW,
                operation={
                    "kind": "browser",
                    "origin": origin,
                    "start_url": start,
                    "goal_template": str(item.get("goal_template") or f"Use {name} on {origin}."),
                    "needs_login": needs_login,
                },
            )
        )
    if not out:
        raise ValueError("Website MCP produced no tools")
    return out


async def execute_browser_tool(
    tool: Dict[str, Any],
    arguments: Dict[str, Any],
    *,
    user_id: str,
    secrets_repo=None,
    run_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    operation = tool.get("operation") or {}
    origin = str(operation.get("origin") or "")
    if not origin:
        raise ValueError("Browser tool is missing origin")
    args = arguments or {}
    start = str(args.get("start_url") or operation.get("start_url") or origin)
    start = _same_origin(start, origin)
    goal = str(args.get("goal") or operation.get("goal_template") or "Complete the user's task on this website.")
    cred = str(args.get("credential_name") or "").strip()
    if operation.get("needs_login") and not cred:
        return {
            "ok": False,
            "error": (
                "This tool needs a Vault login. Store username/email and password under a short name "
                "(Dashboard → Vault), then pass credential_name."
            ),
        }
    try:
        agent = WebAgent(secrets_repo=secrets_repo)
        outcome = await agent.run(
            goal=goal,
            start_url=start,
            user_id=user_id,
            credential_name=cred or None,
            max_steps=40,
            run_id=run_id,
            task_id=task_id,
        )
        return {"ok": bool(outcome.get("success")), **outcome}
    except ChallengePause:
        raise
    except WebAgentError as exc:
        return {"ok": False, "error": str(exc)}


def website_mcp_id(user_id: str, origin: str) -> str:
    return hashlib.sha256(f"{user_id}:website:{origin}".encode("utf-8")).hexdigest()[:16]
