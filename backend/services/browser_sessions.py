"""In-process Playwright sessions kept alive while a human completes CAPTCHA/OTP/MFA."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    playwright: Any
    browser: Any
    context: Any
    page: Any
    allowed_domains: Set[str]
    secrets: Dict[str, str]
    goal: str
    history: List[str]
    steps: List[Dict[str, Any]]
    step_num: int
    max_steps: int
    challenge_type: str
    url: str
    headed: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


_SESSIONS: Dict[str, BrowserSession] = {}


def session_key(run_id: str, task_id: str) -> str:
    return f"{run_id}:{task_id}"


def get_session(run_id: str, task_id: str) -> Optional[BrowserSession]:
    return _SESSIONS.get(session_key(run_id, task_id))


def put_session(run_id: str, task_id: str, session: BrowserSession) -> None:
    _SESSIONS[session_key(run_id, task_id)] = session


async def close_session(run_id: str, task_id: str) -> None:
    key = session_key(run_id, task_id)
    session = _SESSIONS.pop(key, None)
    if not session:
        return
    for closer in (session.context.close, session.browser.close, session.playwright.stop):
        try:
            await closer()
        except Exception:
            logger.debug("browser session close ignored", exc_info=True)
