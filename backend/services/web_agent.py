"""
AgentOS — Web Agent (browser automation)

Performs human-like work in a real browser on the user's behalf:
log in to a site with stored credentials, click through pages, fill
forms, complete tasks, and extract results.

How it works (observe → decide → act loop):
  1. Open the start URL in headless Chromium (Playwright).
  2. Snapshot the page: URL, title, visible text, interactive elements.
  3. Ask Gemini for the next action as strict JSON.
  4. Execute the action (click / type / select / navigate / scroll / wait / done).
  5. Repeat until the model reports "done" or max_steps is reached.

Security model:
  - Credentials come from the user's encrypted vault. The LLM only ever
    sees placeholder tokens like {{secret:password}}; the real value is
    substituted at keystroke time and never appears in prompts, logs,
    or step history.
  - Navigation is confined to the start URL's registered domain (plus
    any extra domains the caller allows). Private/loopback hosts are
    always blocked.
  - Every action is recorded in an audit trail returned with the result.
"""

import asyncio
import ipaddress
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from backend.services import gemini_client
from backend.services.auth_challenges import ChallengePause, challenge_user_message, classify_auth_challenge
from backend.services.browser_sessions import BrowserSession, close_session, get_session, put_session

logger = logging.getLogger(__name__)

MAX_ELEMENTS = 120
MAX_PAGE_TEXT = 3500
ACTION_TIMEOUT_MS = 20_000
SECRET_TOKEN = re.compile(r"\{\{secret:([a-zA-Z0-9_.-]+)\}\}")

# JS snippet: tag visible interactive elements with a stable index attribute
# and return a compact description of each.
_SNAPSHOT_JS = """
() => {
  const selector = 'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [onclick]';
  const els = Array.from(document.querySelectorAll(selector));
  const out = [];
  let idx = 0;
  for (const el of els) {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    if (rect.width < 2 || rect.height < 2) continue;
    if (style.display === 'none' || style.visibility === 'hidden') continue;
    el.setAttribute('data-agentos-idx', String(idx));
    const text = (el.innerText || el.value || '').trim().slice(0, 80);
    out.push({
      idx: idx,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || undefined,
      text: text || undefined,
      placeholder: el.getAttribute('placeholder') || undefined,
      name: el.getAttribute('name') || undefined,
      aria: el.getAttribute('aria-label') || undefined,
      href: el.tagName === 'A' ? (el.getAttribute('href') || '').slice(0, 120) : undefined,
    });
    idx += 1;
    if (idx >= %(max_elements)d) break;
  }
  return out;
}
""" % {"max_elements": MAX_ELEMENTS}

_IFRAMES_JS = """
() => Array.from(document.querySelectorAll('iframe'))
  .map((el) => (el.src || el.getAttribute('src') || el.title || el.id || '').slice(0, 200))
  .filter(Boolean)
"""


def _registrable_domain(host: str) -> str:
    """Approximate registrable domain: last two labels (three for known ccTLD SLDs)."""
    host = (host or "").lower().rstrip(".")
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    second_level = {"co", "com", "net", "org", "gov", "edu", "ac"}
    if parts[-2] in second_level and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _is_private_host(host: str) -> bool:
    if not host:
        return True
    lowered = host.lower()
    if lowered in ("localhost", "metadata.google.internal") or lowered.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


class WebAgentError(Exception):
    pass


class WebAgent:
    """LLM-driven browser automation with vault-backed credential injection."""

    def __init__(self, secrets_repo=None):
        self.secrets_repo = secrets_repo

    async def run(
        self,
        goal: str,
        start_url: str,
        user_id: Optional[str] = None,
        credential_name: Optional[str] = None,
        max_steps: int = 50,
        extra_allowed_domains: Optional[List[str]] = None,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a browsing task. Returns {success, result, steps, final_url}."""
        parsed = urlparse(start_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise WebAgentError(f"Invalid start URL: {start_url}")
        if _is_private_host(parsed.hostname):
            raise WebAgentError("Refusing to browse private/internal hosts")

        allowed_domains = {_registrable_domain(parsed.hostname)}
        for domain in extra_allowed_domains or []:
            allowed_domains.add(_registrable_domain(domain))

        secrets: Dict[str, str] = {}
        if credential_name:
            if not (self.secrets_repo and user_id):
                raise WebAgentError("Credential requested but no secrets store available")
            from backend.api.routers.credentials import load_credential
            secrets = await load_credential(self.secrets_repo, user_id, credential_name)

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise WebAgentError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        existing = get_session(run_id or "", task_id or "") if (run_id and task_id) else None
        owns_browser = existing is None
        pw = browser = context = page = None
        steps: List[Dict[str, Any]] = list(existing.steps) if existing else []
        history: List[str] = list(existing.history) if existing else []
        start_step = (existing.step_num + 1) if existing else 1
        result: Optional[str] = None
        success = False
        final_url = start_url
        paused = False

        try:
            if existing:
                pw, browser, context, page = existing.playwright, existing.browser, existing.context, existing.page
                allowed_domains = existing.allowed_domains or allowed_domains
                secrets = existing.secrets or secrets
                goal = existing.goal or goal
                max_steps = existing.max_steps or max_steps
                history.append("Resumed after human completed the security challenge")
            else:
                pw = await async_playwright().start()
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    accept_downloads=False,
                )
                page = await context.new_page()
                page.set_default_timeout(ACTION_TIMEOUT_MS)
                await page.goto(start_url, wait_until="domcontentloaded", timeout=ACTION_TIMEOUT_MS)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                if "#" in (start_url or ""):
                    await asyncio.sleep(1.5)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                history.append(f"Opened {start_url}")

            for step_num in range(start_step, max_steps + 1):
                snapshot = await self._snapshot(page)
                challenge = classify_auth_challenge(snapshot)
                if challenge:
                    page, browser, context, headed = await self._open_headed_for_human(
                        pw, page, browser, context
                    )
                    if run_id and task_id:
                        put_session(run_id, task_id, BrowserSession(
                            playwright=pw,
                            browser=browser,
                            context=context,
                            page=page,
                            allowed_domains=allowed_domains,
                            secrets=secrets,
                            goal=goal,
                            history=history,
                            steps=steps,
                            step_num=step_num,
                            max_steps=max_steps,
                            challenge_type=challenge,
                            url=snapshot["url"],
                            headed=headed,
                        ))
                        paused = True
                    raise ChallengePause(
                        challenge,
                        snapshot["url"],
                        challenge_user_message(challenge, snapshot["url"]),
                    )

                decision = await self._decide(goal, snapshot, history, secrets, step_num, max_steps)
                action = str(decision.get("action", "")).lower()
                safe_desc = self._safe_description(decision)
                steps.append({"step": step_num, "url": snapshot["url"], "action": safe_desc})
                logger.info("WebAgent step %d: %s", step_num, safe_desc)

                if action == "done":
                    result = str(decision.get("result", ""))
                    success = bool(decision.get("success", True))
                    break

                try:
                    await self._execute(page, decision, secrets, allowed_domains)
                    history.append(f"Step {step_num}: {safe_desc} — ok")
                except ChallengePause:
                    raise
                except Exception as e:
                    err = str(e).split("\n")[0][:200]
                    history.append(f"Step {step_num}: {safe_desc} — FAILED: {err}")
                    steps[-1]["error"] = err

                history = history[-14:]

            final_url = page.url if page else start_url
            if result is None:
                result = "Reached the maximum number of steps before the goal was confirmed complete."
        except ChallengePause:
            raise
        finally:
            if owns_browser and not paused:
                if run_id and task_id:
                    await close_session(run_id, task_id)
                else:
                    for closer in (
                        (context.close if context else None),
                        (browser.close if browser else None),
                        (pw.stop if pw else None),
                    ):
                        if closer is None:
                            continue
                        try:
                            await closer()
                        except Exception:
                            pass
            elif existing and not paused and run_id and task_id:
                await close_session(run_id, task_id)

        return {
            "success": success,
            "result": result,
            "steps": steps,
            "steps_taken": len(steps),
            "final_url": final_url,
        }

    async def _open_headed_for_human(self, pw, page, browser, context):
        """Switch to a visible Chromium window so the user can complete the challenge."""
        current = page.url
        try:
            headed_browser = await pw.chromium.launch(headless=False)
            headed_context = await headed_browser.new_context(
                viewport={"width": 1280, "height": 900},
                accept_downloads=False,
            )
            headed_page = await headed_context.new_page()
            headed_page.set_default_timeout(ACTION_TIMEOUT_MS)
            await headed_page.goto(current, wait_until="domcontentloaded", timeout=ACTION_TIMEOUT_MS)
            try:
                await context.close()
                await browser.close()
            except Exception:
                pass
            return headed_page, headed_browser, headed_context, True
        except Exception as exc:
            logger.warning("Could not open a headed browser for HITL: %s", exc)
            return page, browser, context, False

    # ── Observe ───────────────────────────────────────────────────

    async def _snapshot(self, page) -> Dict[str, Any]:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=ACTION_TIMEOUT_MS)
        except Exception:
            pass
        elements = await page.evaluate(_SNAPSHOT_JS)
        try:
            text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        except Exception:
            text = ""
        iframes: List[str] = []
        try:
            iframes = await page.evaluate(_IFRAMES_JS)
        except Exception:
            iframes = []
        return {
            "url": page.url,
            "title": await page.title(),
            "text": re.sub(r"\n{3,}", "\n\n", text or "").strip()[:MAX_PAGE_TEXT],
            "elements": elements,
            "iframes": iframes if isinstance(iframes, list) else [],
        }

    # ── Decide ────────────────────────────────────────────────────

    async def _decide(
        self, goal: str, snapshot: Dict[str, Any], history: List[str],
        secrets: Dict[str, str], step_num: int, max_steps: int,
    ) -> Dict[str, Any]:
        lines = []
        for el in snapshot["elements"]:
            attrs = []
            for key in ("type", "name", "placeholder", "aria", "href"):
                if el.get(key):
                    attrs.append(f'{key}="{el[key]}"')
            label = el.get("text") or ""
            lines.append(f"[{el['idx']}] <{el['tag']} {' '.join(attrs)}> {label}".strip())
        elements_desc = "\n".join(lines) or "(no interactive elements found)"

        secret_tokens = (
            ", ".join(f"{{{{secret:{k}}}}}" for k in secrets.keys())
            if secrets else "(none provided)"
        )

        prompt = f"""You are a precise browser automation agent completing a task for a user.

GOAL: {goal}

STEP {step_num} of {max_steps}. Current page:
URL: {snapshot['url']}
TITLE: {snapshot['title']}

PAGE TEXT (truncated):
{snapshot['text']}

INTERACTIVE ELEMENTS (use idx to reference them):
{elements_desc}

RECENT ACTIONS:
{chr(10).join(history) or '(none)'}

AVAILABLE SECRET PLACEHOLDERS (use them verbatim in "text"; the real value is injected for you and you must NEVER guess or invent credentials):
{secret_tokens}

Reply with ONE action as strict JSON, using exactly one of these shapes:
{{"action":"click","index":<int>,"reasoning":"..."}}
{{"action":"type","index":<int>,"text":"<text or {{{{secret:field}}}}>","submit":<bool>,"reasoning":"..."}}
{{"action":"select","index":<int>,"value":"<option value or label>","reasoning":"..."}}
{{"action":"navigate","url":"<absolute url on the same site>","reasoning":"..."}}
{{"action":"scroll","direction":"down|up","reasoning":"..."}}
{{"action":"wait","seconds":<int 1-10>,"reasoning":"..."}}
{{"action":"done","success":<bool>,"result":"<detailed summary of what was accomplished and any extracted information>","reasoning":"..."}}

Rules:
- Work strictly toward the GOAL. When it is fully accomplished, use "done" with success=true and include extracted data in "result".
- If the page is 404, an error, has no login/form matching the GOAL, or cannot be completed, immediately use "done" with success=false and explain. Do not wander for extra steps.
- NEVER fill CAPTCHA, OTP, SMS codes, authenticator codes, or MFA prompts. If you see one, use done with success=false saying a human must complete it.
- If a previous action FAILED, try a different element or approach instead of repeating it."""

        try:
            decision = await gemini_client.generate_json(prompt)
        except Exception as e:
            logger.warning("WebAgent model decide failed: %s", e)
            return {
                "action": "done",
                "success": False,
                "result": (
                    "Could not continue in the browser because the model is unavailable "
                    f"({str(e).splitlines()[0][:180]}). Add a Gemini or Grok key in Settings, or try again shortly."
                ),
                "reasoning": "model_unavailable",
            }
        if not isinstance(decision, dict) or "action" not in decision:
            raise WebAgentError(f"Model returned invalid action: {decision}")
        return decision

    # ── Act ───────────────────────────────────────────────────────

    async def _execute(
        self, page, decision: Dict[str, Any], secrets: Dict[str, str], allowed_domains: set,
    ) -> None:
        action = str(decision.get("action", "")).lower()

        if action == "click":
            locator = page.locator(f'[data-agentos-idx="{int(decision["index"])}"]')
            await locator.click(timeout=ACTION_TIMEOUT_MS)
            await self._settle(page)

        elif action == "type":
            locator = page.locator(f'[data-agentos-idx="{int(decision["index"])}"]')
            text = self._substitute_secrets(str(decision.get("text", "")), secrets)
            await locator.fill(text, timeout=ACTION_TIMEOUT_MS)
            if decision.get("submit"):
                await locator.press("Enter")
                await self._settle(page)

        elif action == "select":
            locator = page.locator(f'[data-agentos-idx="{int(decision["index"])}"]')
            value = str(decision.get("value", ""))
            try:
                await locator.select_option(value=value, timeout=ACTION_TIMEOUT_MS)
            except Exception:
                await locator.select_option(label=value, timeout=ACTION_TIMEOUT_MS)

        elif action == "navigate":
            url = str(decision.get("url", ""))
            self._check_domain(url, allowed_domains)
            await page.goto(url, wait_until="domcontentloaded")

        elif action == "scroll":
            delta = 700 if str(decision.get("direction", "down")) == "down" else -700
            await page.mouse.wheel(0, delta)
            await asyncio.sleep(0.5)

        elif action == "wait":
            seconds = min(max(int(decision.get("seconds", 2)), 1), 10)
            await asyncio.sleep(seconds)

        else:
            raise WebAgentError(f"Unknown action: {action}")

        # Post-action domain guard: if a click/redirect escaped the allowed
        # domains, back out immediately.
        host = urlparse(page.url).hostname or ""
        if page.url.startswith("http") and _registrable_domain(host) not in allowed_domains:
            escaped = page.url
            try:
                await page.go_back(wait_until="domcontentloaded")
            except Exception:
                pass
            raise WebAgentError(f"Blocked navigation to off-site URL: {escaped[:120]}")

    async def _settle(self, page) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            await asyncio.sleep(1.0)

    @staticmethod
    def _substitute_secrets(text: str, secrets: Dict[str, str]) -> str:
        def repl(match):
            key = match.group(1)
            if key not in secrets:
                raise WebAgentError(f"Unknown secret placeholder: {key}")
            return str(secrets[key])
        return SECRET_TOKEN.sub(repl, text)

    @staticmethod
    def _safe_description(decision: Dict[str, Any]) -> str:
        """Human-readable action description that never leaks secret values."""
        action = str(decision.get("action", "?")).lower()
        if action == "click":
            return f"click element [{decision.get('index')}]"
        if action == "type":
            text = str(decision.get("text", ""))
            shown = text if SECRET_TOKEN.search(text) else (text[:60] or "(empty)")
            return f"type into element [{decision.get('index')}]: {shown}"
        if action == "select":
            return f"select '{decision.get('value')}' in element [{decision.get('index')}]"
        if action == "navigate":
            return f"navigate to {str(decision.get('url', ''))[:120]}"
        if action == "scroll":
            return f"scroll {decision.get('direction', 'down')}"
        if action == "wait":
            return f"wait {decision.get('seconds', 2)}s"
        if action == "done":
            return f"done (success={decision.get('success', True)})"
        return action
