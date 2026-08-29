"""Detect CAPTCHA / OTP / MFA pages. AgentOS never solves these — it pauses for a human."""

from __future__ import annotations

from typing import Any, Dict, Optional

CAPTCHA_HINTS = (
    "captcha", "recaptcha", "h-captcha", "hcaptcha", "cf-turnstile", "turnstile",
    "verify you are human", "i'm not a robot", "im not a robot", "are you a robot",
    "complete the security check", "checking your browser", "challenge-platform",
    "cloudflare", "access denied", "attention required", "why do i have to complete",
)
OTP_HINTS = (
    "one-time password", "one time password", "one-time code", "one time code",
    "verification code", "enter the code we sent", "enter the 6-digit",
    "6-digit code", "otp", "sms code", "texted a code",
)
MFA_HINTS = (
    "two-factor", "two factor", "2-factor", "2fa", "mfa", "multi-factor",
    "multifactor", "authenticator app", "authentication app", "totp",
    "enter the code from your authenticator",
)


class ChallengePause(Exception):
    """Raised when the browser hit a human-only auth challenge. Do not fill or bypass it."""

    def __init__(self, challenge_type: str, url: str, message: str):
        super().__init__(message)
        self.challenge_type = challenge_type
        self.url = url
        self.message = message


def classify_auth_challenge(snapshot: Dict[str, Any]) -> Optional[str]:
    """Return 'captcha' | 'otp' | 'mfa' when the page is a human verification step."""
    text = str(snapshot.get("text") or "").lower()
    title = str(snapshot.get("title") or "").lower()
    url = str(snapshot.get("url") or "").lower()
    iframes = " ".join(str(x) for x in (snapshot.get("iframes") or [])).lower()
    blob = f"{text}\n{title}\n{url}\n{iframes}"
    for hint in CAPTCHA_HINTS:
        if hint in blob:
            return "captcha"
    for hint in MFA_HINTS:
        if hint in blob:
            return "mfa"
    for hint in OTP_HINTS:
        if hint in blob:
            return "otp"
    elements = snapshot.get("elements") or []
    joined = " ".join(
        str(el.get("name") or "") + " " + str(el.get("placeholder") or "") + " " + str(el.get("aria") or "")
        for el in elements if isinstance(el, dict)
    ).lower()
    if "otp" in joined or "one-time" in joined or "verification code" in joined:
        return "otp"
    if "authenticator" in joined or "totp" in joined:
        return "mfa"
    return None


def challenge_user_message(challenge_type: str, url: str) -> str:
    label = {"captcha": "CAPTCHA", "otp": "one-time passcode (OTP)", "mfa": "multi-factor authentication"}.get(
        challenge_type, "security check"
    )
    return (
        f"AgentOS paused: this page needs you to complete a {label}. "
        "Finish it in the open browser window, then click Resume in the workspace. "
        f"AgentOS will not fill or bypass {label}. Current URL: {url}"
    )
