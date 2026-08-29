"""Deterministic plans for common goals so the workspace still runs when Gemini is unavailable."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence

from backend.models.schemas import TaskDefinition, WorkflowDefinition
from backend.engine.mcp_catalog import build_input_for_app, detect_named_apps

_URL = re.compile(r"https?://[^\s\"'<>]+", re.I)
_EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)

MCP_PHRASES = (
    "mcp", "openapi", "swagger", "build an mcp", "create mcp", "create a mcp",
    "make an mcp", "generate an mcp", "connector for", "an integration for",
    "build an integration", "create an integration", "integrate with", "connect to",
)
TOOL_PHRASES = (
    "create tools", "build tools", "make tools", "generate tools",
    "create a tool", "build a tool", "make a tool", "generate a tool",
)
_QUESTION_START = re.compile(
    r"^(and\s+)?(can you|could you|do you|would you|are you|what|how)\b",
    re.I,
)
_VAGUE_TARGET = re.compile(r"\b(any api|any app|any service|every api|all apis|anything)\b", re.I)
_FOR_TARGET = re.compile(
    r"\b(?:for|with|to)\s+(?:the\s+)?(?!any\b|every\b|all\b|some\b|me\b|us\b|it\b|this\b|that\b)([\w][\w .+\-]{1,48})",
    re.I,
)
BROWSE_WORDS = (
    "log in", "login", "sign in", "signin", "fill the form", "fill out",
    "click through", "browse", "on the website", "on this site", "on the site",
    "complete the", "do this on", "open the site", "human like", "human-like",
)
APP_WORDS = (
    "create a website", "build a website", "generate a website", "create a landing",
    "build a landing", "create an app", "build an app", "generate an app",
    "build me a", "scaffold", "multi-page", "generate a site",
)
USE_AFTER_MCP = (
    "so i can", "so that i", "then ", " and then",     "use them", "use those", "use it", "use the tool", "call the", "call one",
    "list my", "get my", "fetch ", "now ", "using it", "using them", "and call",
    "then call", "then use",
)
EMAIL_WORDS = (
    "email", "e-mail", "e mail", "send mail", "send an email", "write the email",
    "write an email", "draft an email", "mail it",
)


def _wants_browse(text: str, url: Optional[str] = None) -> bool:
    lowered = (text or "").lower()
    if any(w in lowered for w in BROWSE_WORDS):
        return True
    if url and (_is_login_url(url) or _is_spa_hash_url(url)):
        return True
    return False


def _is_login_url(url: str) -> bool:
    u = (url or "").lower()
    return any(p in u for p in ("/login", "/signin", "/sign-in", "/auth/", "/session", "/account/login"))


def _is_spa_hash_url(url: Optional[str]) -> bool:
    """True for in-app routes like https://host/#/home that only exist in the browser."""
    if not url:
        return False
    parsed = url.split("#", 1)
    if len(parsed) < 2:
        return False
    fragment = parsed[1].lstrip("/")
    return bool(fragment) and not fragment.lower().startswith(("http", "openapi", "swagger"))


def _is_spec_url(url: Optional[str], text: str = "") -> bool:
    if not url:
        return False
    lowered = (text or "").lower()
    u = url.lower()
    return bool(
        "openapi" in lowered
        or "swagger" in lowered
        or u.endswith((".json", ".yaml", ".yml"))
        or "/openapi" in u
        or "/swagger" in u
        or "/api-docs" in u
    )


def _wants_app(text: str) -> bool:
    lowered = (text or "").lower()
    return any(w in lowered for w in APP_WORDS)


def _wants_use_after_mcp(text: str) -> bool:
    lowered = (text or "").lower()
    return any(w in lowered for w in USE_AFTER_MCP)


def _prior_was_mcp(prior_goal: str) -> bool:
    return _wants_mcp(prior_goal or "", url=_url(prior_goal or ""))


def _catalog_covers_goal(text: str, catalog: Optional[Sequence[Any]] = None) -> bool:
    """True when registered MCP tools already match what the user is asking to do."""
    if not catalog or not (text or "").strip():
        return False
    lowered = text.lower()
    compact_goal = re.sub(r"[^a-z0-9]", "", lowered)
    named = set(detect_named_apps(text))
    for raw in catalog:
        tool = raw if isinstance(raw, dict) else {}
        mcp_name = str(tool.get("mcp_name") or "")
        tname = str(tool.get("name") or "")
        desc = str(tool.get("description") or "")
        mcp_l = mcp_name.lower()
        if mcp_l and len(mcp_l) >= 4 and mcp_l in lowered:
            return True
        compact_mcp = re.sub(r"[^a-z0-9]", "", mcp_l)
        if compact_mcp and len(compact_mcp) >= 5 and compact_mcp in compact_goal:
            return True
        compact_tool = re.sub(r"[^a-z0-9]", "", tname.lower())
        if compact_tool and len(compact_tool) >= 6 and compact_tool in compact_goal:
            return True
        camel = re.sub(r"([a-z])([A-Z])", r"\1 \2", tname)
        words = [w for w in re.findall(r"[a-z][a-z0-9]+", camel.lower()) if len(w) > 3]
        if words and all(w in lowered for w in words):
            return True
        hay = f"{mcp_l} {tname.lower()} {desc.lower()}"
        if named and any(app in hay for app in named):
            return True
        if "pokemon" in lowered and "poke" in compact_mcp:
            return True
    return False


def _orchestrator_task(goal: str, timeout: int = 180, deps: Optional[List[str]] = None) -> TaskDefinition:
    return TaskDefinition(
        task_id="work-1",
        agent="OrchestratorAgent",
        dependencies=list(deps or []),
        input_data={"goal": goal},
        timeout_seconds=timeout,
    )


def _url(text: str) -> Optional[str]:
    m = _URL.search(text or "")
    if not m:
        return None
    return m.group(0).rstrip(").,;]")


def _has_concrete_mcp_target(text: str, url: Optional[str] = None) -> bool:
    if url:
        return True
    if detect_named_apps(text or ""):
        return True
    if _VAGUE_TARGET.search(text or ""):
        return False
    if _FOR_TARGET.search(text or ""):
        return True
    return False


def _wants_mcp(text: str, prior_goal: str = "", url: Optional[str] = None) -> bool:
    lowered = (text or "").lower()
    if not lowered:
        return False
    if detect_named_apps(prior_goal or "") and any(
        w in lowered
        for w in ("these", "those", "them", "the tool", "the mcp", "that mcp", "same ones", "same tools")
    ):
        return True
    spec_url = bool(
        url
        and (
            "openapi" in lowered
            or "swagger" in lowered
            or url.lower().endswith((".json", ".yaml", ".yml"))
            or "/openapi" in url.lower()
            or "/swagger" in url.lower()
        )
    )
    if spec_url:
        return True
    mentions_mcp = any(w in lowered for w in MCP_PHRASES)
    tools_phrase = any(w in lowered for w in TOOL_PHRASES)
    if not mentions_mcp and not tools_phrase:
        return False
    if _QUESTION_START.match(lowered.strip()) and not _has_concrete_mcp_target(text, url):
        return False
    if mentions_mcp:
        if _VAGUE_TARGET.search(lowered) and not _has_concrete_mcp_target(text, url):
            return False
        return True
    return _has_concrete_mcp_target(text, url)


def extract_emails(text: str) -> List[str]:
    seen = set()
    out: List[str] = []
    for match in _EMAIL.findall(text or ""):
        addr = match.lower()
        if addr in seen:
            continue
        seen.add(addr)
        out.append(match)
    return out


def _mcp_tasks(text: str, url: Optional[str], prior_goal: str = "") -> List[TaskDefinition]:
    haystack = "\n".join(p for p in (text, prior_goal) if p).strip()
    lowered = (text or "").lower()
    spec_url = bool(
        url and (
            "openapi" in lowered
            or "swagger" in lowered
            or url.lower().endswith((".json", ".yaml", ".yml"))
            or "/openapi" in url.lower()
            or "/swagger" in url.lower()
        )
    )
    website = bool(url and not spec_url and (_is_spa_hash_url(url) or _is_login_url(url)))
    if not website:
        from backend.mcp.website_mcp import looks_like_website_without_api
        website = looks_like_website_without_api(haystack, url)
    method = "url" if spec_url else ("website" if website else "prompt")
    source = url if method == "url" and url else haystack
    apps = detect_named_apps(haystack) if method == "prompt" else []
    if len(apps) > 1:
        tasks: List[TaskDefinition] = []
        for i, app_id in enumerate(apps, 1):
            payload = build_input_for_app(app_id) or {}
            display = payload.get("name") or app_id
            tasks.append(
                TaskDefinition(
                    task_id=f"mcp-{i}",
                    agent="core.mcp_build",
                    tool="mcp_build",
                    input_data={
                        "method": "prompt",
                        "source": f"{haystack}\n\nBuild tools only for {display}.",
                        "name": display,
                        "auth_type": payload.get("auth_type") or "API_KEY",
                    },
                    timeout_seconds=180,
                )
            )
        return tasks
    return [
        TaskDefinition(
            task_id="mcp-1",
            agent="core.mcp_build",
            tool="mcp_build",
            input_data={
                "method": method,
                "source": source,
                "name": "",
                "auth_type": "NONE" if method == "website" else "API_KEY",
            },
            timeout_seconds=180,
        )
    ]


def _email_tasks(goal: str, mcp_task_id: Optional[str] = None) -> List[TaskDefinition]:
    recipients = extract_emails(goal)
    deps = [mcp_task_id] if mcp_task_id else []
    prompt = (
        "Write a complete professional email that matches the user's request. "
        "Include To, Subject, and Body. Do not invent that mail was already sent.\n\n"
        f"User request:\n{goal.strip()}"
    )
    if mcp_task_id:
        prompt += (
            f"\n\nThe MCP build finished with this result:\n{{{{ tasks.{mcp_task_id}.output.message }}}}\n"
            "Mention the real tool names from that result."
        )
    tasks = [
        TaskDefinition(
            task_id="mail-draft",
            agent="core.chat",
            dependencies=list(deps),
            input_data={"prompt": prompt},
            timeout_seconds=45,
        )
    ]
    if recipients:
        tasks.append(
            TaskDefinition(
                task_id="mail-send",
                agent="core.email",
                dependencies=["mail-draft"],
                input_data={
                    "to": recipients[0],
                    "subject": "AgentOS update",
                    "body": "{{ tasks.mail-draft.output.reply }}",
                },
                timeout_seconds=45,
            )
        )
    return tasks


def plan_from_goal(goal: str, prior_goal: str = "", catalog: Optional[Sequence[Any]] = None) -> Optional[WorkflowDefinition]:
    text = (goal or "").strip()
    if not text:
        return None
    lowered = text.lower().strip(" ?.!")
    url = _url(text)
    haystack = f"{text}\n{prior_goal or ''}"

    help_phrases = (
        "what can you do", "what do you do", "help", "who are you",
        "what are you", "capabilities", "what can u do", "how does this work",
        "what can agentos do",
    )
    greetings = ("hi", "hello", "hey", "yo", "sup", "good morning", "good evening")

    if lowered in greetings or lowered.startswith("hi ") or lowered.startswith("hello "):
        return WorkflowDefinition(tasks=[
            TaskDefinition(
                task_id="chat-1",
                agent="core.chat",
                input_data={"prompt": text},
                timeout_seconds=25,
            ),
        ])

    if any(p in lowered for p in help_phrases) or lowered in ("help", "?"):
        return WorkflowDefinition(tasks=[
            TaskDefinition(
                task_id="chat-1",
                agent="core.chat",
                input_data={"prompt": text},
                timeout_seconds=25,
            ),
        ])

    health_words = ("health", "uptime", "status code", "is it up", "site health", "check the health")
    http_words = ("fetch", "get ", "http get", "call ", "request ")
    wants_mcp = _wants_mcp(text, prior_goal=prior_goal, url=url)
    wants_email = any(w in lowered for w in EMAIL_WORDS)

    if _prior_was_mcp(prior_goal):
        prior_apps = set(detect_named_apps(prior_goal))
        new_apps = [a for a in detect_named_apps(text) if a not in prior_apps]
        reuse_existing = any(
            w in lowered
            for w in (
                "these", "those", "them", "the tool", "the mcp", "that mcp",
                "same ones", "same tools", "use it", "call it", "call them",
            )
        ) or _wants_use_after_mcp(text)
        prior_url = _url(prior_goal)
        new_url = bool(url and url != prior_url)
        if reuse_existing and not new_apps and not new_url:
            return WorkflowDefinition(tasks=[_orchestrator_task(text, timeout=180)])

    if url and any(w in lowered for w in health_words) and not wants_mcp and not _wants_browse(text, url):
        return WorkflowDefinition(tasks=[
            TaskDefinition(task_id="health-1", agent="core.health", input_data={"url": url}, timeout_seconds=45),
        ])

    if wants_mcp:
        tasks = _mcp_tasks(text, url, prior_goal)
        mcp_ids = [t.task_id for t in tasks]
        if _wants_use_after_mcp(text) or any(w in lowered for w in BROWSE_WORDS) or _wants_app(text):
            timeout = 300 if any(w in lowered for w in BROWSE_WORDS) else 180
            tasks.append(_orchestrator_task(text, timeout=timeout, deps=mcp_ids))
        elif wants_email and mcp_ids:
            extra = _email_tasks(haystack, mcp_task_id=mcp_ids[-1])
            extra[0].dependencies = list(mcp_ids)
            tasks.extend(extra)
        return WorkflowDefinition(tasks=tasks)

    if _wants_browse(text, url):
        return WorkflowDefinition(tasks=[_orchestrator_task(text, timeout=300)])

    if _wants_app(text):
        return WorkflowDefinition(tasks=[_orchestrator_task(text, timeout=240)])

    if _prior_was_mcp(prior_goal) and not _QUESTION_START.match(lowered.strip()) and len(text) > 12:
        return WorkflowDefinition(tasks=[_orchestrator_task(text, timeout=180)])

    if _catalog_covers_goal(text, catalog) and not wants_email:
        return WorkflowDefinition(tasks=[_orchestrator_task(text, timeout=180)])

    if wants_email:
        return WorkflowDefinition(tasks=_email_tasks(text))

    if url and _is_login_url(url):
        return WorkflowDefinition(tasks=[_orchestrator_task(text, timeout=300)])

    if url and (any(w in lowered for w in http_words) or lowered.startswith("http")):
        return WorkflowDefinition(tasks=[
            TaskDefinition(
                task_id="http-1",
                agent="core.http",
                input_data={"url": url, "method": "GET"},
                timeout_seconds=45,
            ),
        ])

    if url:
        return WorkflowDefinition(tasks=[
            TaskDefinition(task_id="http-1", agent="core.http", input_data={"url": url, "method": "GET"}, timeout_seconds=45),
        ])

    # Short conversational asks should not wait on the full planner.
    if len(text) < 240 and not url:
        return WorkflowDefinition(tasks=[
            TaskDefinition(
                task_id="chat-1",
                agent="core.chat",
                input_data={"prompt": text},
                timeout_seconds=25,
            ),
        ])

    return None
