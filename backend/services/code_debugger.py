"""
AgentOS — Code debugger.

Analyzes real source (and optional error/stack) with a syntax check for
Python plus a Gemini diagnosis. Does not execute untrusted code.
"""

from __future__ import annotations

import ast
import logging
from typing import Any, Dict, Optional

from backend.services import gemini_client

logger = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 40_000


class DebugError(Exception):
    pass


def _python_syntax(source: str) -> Dict[str, Any]:
    try:
        ast.parse(source)
        return {"ok": True, "language": "python"}
    except SyntaxError as e:
        return {
            "ok": False,
            "language": "python",
            "line": e.lineno,
            "offset": e.offset,
            "message": e.msg,
            "text": (e.text or "").strip()[:200],
        }


async def debug_code(
    source: str,
    language: str = "python",
    error_message: str = "",
    goal: str = "",
) -> Dict[str, Any]:
    if not (source or "").strip():
        raise DebugError("No source code provided")
    source = source[:MAX_SOURCE_CHARS]
    language = (language or "unknown").lower().strip()

    syntax: Optional[Dict[str, Any]] = None
    if language in ("python", "py"):
        syntax = _python_syntax(source)

    prompt = f"""You are a senior software debugger. Diagnose the issue and propose a concrete fix.
Do not invent files that were not provided. Do not ask to run the code if a static diagnosis is possible.

LANGUAGE: {language}
USER GOAL (optional): {goal or "(none)"}
REPORTED ERROR / STACK (optional):
{error_message or "(none)"}

SOURCE:
```{language}
{source}
```

Return JSON with keys:
- "summary": one-paragraph diagnosis
- "root_cause": short root cause
- "severity": one of "syntax", "logic", "runtime", "security", "style", "unknown"
- "issues": array of {{"line": int or null, "message": str, "fix": str}}
- "fixed_source": the corrected full source if a fix is clear, else null
- "tests_to_run": array of strings describing how the user should verify
"""
    analysis = None
    try:
        analysis = await gemini_client.generate_json(prompt)
        if not isinstance(analysis, dict):
            raise DebugError("Model returned an invalid debug report")
    except Exception as e:
        from backend.services.gemini_client import GeminiQuotaExceeded, is_quota_error
        if not (isinstance(e, GeminiQuotaExceeded) or is_quota_error(e)):
            raise
        issues = []
        if syntax and not syntax.get("ok"):
            issues.append({
                "line": syntax.get("line"),
                "message": syntax.get("message") or "Syntax error",
                "fix": "Correct the syntax on the reported line.",
            })
        analysis = {
            "summary": (
                "Gemini is unavailable, so this is a local static check only. "
                + ("Python did not parse: " + str(syntax.get("message")) if syntax and not syntax.get("ok") else "No syntax error detected in the provided source.")
            ),
            "root_cause": (syntax or {}).get("message") or "No local syntax error; LLM diagnosis skipped because Gemini quota is exhausted.",
            "severity": "syntax" if syntax and not syntax.get("ok") else "unknown",
            "issues": issues,
            "fixed_source": None,
            "tests_to_run": ["Re-run after adding a Gemini key in Settings for a full diagnosis."],
            "gemini": "skipped_quota",
        }

    return {
        "language": language,
        "syntax": syntax,
        "analysis": analysis,
    }
