"""
Public contact form. Persists every message and emails CONTACT_TO_EMAIL via SMTP first.
"""

import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config.settings import settings
from backend.security.rate_limiter import check_rate_limit, get_client_identifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INBOX_PATH = PROJECT_ROOT / "data" / "contact_inbox.json"
ENV_PATH = PROJECT_ROOT / ".env"


def _parse_dotenv(path: Path) -> dict:
    """Read CONTACT_/SMTP_/RESEND keys from .env on every send (no restart required)."""
    out: dict = {}
    if not path.exists():
        return out
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#") or "=" not in trimmed:
            continue
        key, val = trimmed.split("=", 1)
        key = key.strip()
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        if key.startswith("CONTACT_") or key.startswith("SMTP_") or key in ("RESEND_API_KEY",):
            out[key] = val
    return out


def _contact_cfg() -> dict:
    file_env = _parse_dotenv(ENV_PATH)
    def pick(*names: str, default: str = "") -> str:
        for name in names:
            if file_env.get(name):
                return str(file_env[name])
            if os.environ.get(name):
                return str(os.environ[name])
            attr = getattr(settings, name, None)
            if attr:
                return str(attr)
        return default
    username = pick("CONTACT_SMTP_USERNAME", "SMTP_USERNAME")
    # Gmail App Passwords are often copied with spaces: abcd efgh ijkl mnop
    password = pick("CONTACT_SMTP_PASSWORD", "SMTP_PASSWORD").replace(" ", "")
    host = pick("CONTACT_SMTP_HOST", "SMTP_HOST")
    if not host and "gmail.com" in username.lower():
        host = "smtp.gmail.com"
    port_raw = pick("CONTACT_SMTP_PORT", "SMTP_PORT", default="587") or "587"
    try:
        port = int(port_raw)
    except ValueError:
        port = 587
    return {
        "to": pick("CONTACT_TO_EMAIL", default="godumang35@gmail.com") or "godumang35@gmail.com",
        "from_addr": pick("CONTACT_FROM_EMAIL") or username,
        "username": username.strip(),
        "password": password.strip(),
        "host": host.strip(),
        "port": port,
        "resend": pick("RESEND_API_KEY").strip(),
        "webhook": pick("CONTACT_WEBHOOK_URL").strip(),
    }


class ContactRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    message: str = Field(min_length=1, max_length=8000)
    name: str = Field(default="", max_length=120)


def _contact_to() -> str:
    return _contact_cfg()["to"]


def _append_inbox(payload: dict) -> None:
    INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if INBOX_PATH.exists():
        try:
            existing = json.loads(INBOX_PATH.read_text())
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    existing.insert(0, payload)
    INBOX_PATH.write_text(json.dumps(existing[:500], indent=2))


def _smtp_error_reason(exc: Exception) -> str:
    name = type(exc).__name__
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "smtp_auth_failed"
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "smtp_recipient_refused"
    if isinstance(exc, (TimeoutError, smtplib.SMTPServerDisconnected)):
        return "smtp_timeout"
    return f"smtp_{name.lower()}"


def _send_smtp(subject: str, body: str, reply_to: str) -> Tuple[bool, Optional[str]]:
    cfg = _contact_cfg()
    username, password, host, port = cfg["username"], cfg["password"], cfg["host"], cfg["port"]
    if not (username and password):
        return False, "smtp_not_configured"
    if not host:
        return False, "smtp_host_missing"
    to_addr = cfg["to"]
    msg = EmailMessage()
    msg["From"] = cfg["from_addr"] or username
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Reply-To"] = reply_to
    msg.set_content(body)
    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.send_message(msg)
        logger.info("Contact SMTP delivered to %s", to_addr)
        return True, None
    except Exception as exc:
        logger.warning("SMTP contact delivery failed: %s", type(exc).__name__)
        return False, _smtp_error_reason(exc)


def _send_webhook(subject: str, body: str, reply_to: str, name: str) -> bool:
    url = _contact_cfg()["webhook"]
    if not url or not url.startswith("https://"):
        return False
    payload = json.dumps({
        "to": _contact_to(),
        "subject": subject,
        "text": body,
        "reply_to": reply_to,
        "name": name,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "AgentOS-contact/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 300
    except urllib.error.URLError as exc:
        logger.warning("Contact webhook failed: %s", type(exc).__name__)
        return False


def _send_resend(subject: str, body: str, reply_to: str) -> bool:
    cfg = _contact_cfg()
    api_key = cfg["resend"]
    if not api_key:
        return False
    from_addr = cfg["from_addr"] or "AgentOS <onboarding@resend.dev>"
    payload = json.dumps({
        "from": from_addr,
        "to": [_contact_to()],
        "reply_to": reply_to,
        "subject": subject,
        "text": body,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 300
    except urllib.error.URLError as exc:
        logger.warning("Resend delivery failed: %s", type(exc).__name__)
        return False


@router.post("")
async def submit_contact(body: ContactRequest, request: Request):
    check_rate_limit(get_client_identifier(request), "general")
    if "@" not in body.email or "." not in body.email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    to_addr = _contact_to()
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "name": body.name.strip(),
        "email": str(body.email),
        "message": body.message.strip(),
        "to": to_addr,
    }
    try:
        _append_inbox(record)
    except Exception as exc:
        logger.error("Failed to persist contact message: %s", exc)
        raise HTTPException(status_code=500, detail="Could not save your message.")

    subject = f"AgentOS contact from {body.email}"
    text = f"From: {body.name or '—'} <{body.email}>\n\n{body.message}"
    delivered = False
    via = None
    reason = None

    delivered, reason = _send_smtp(subject, text, str(body.email))
    if delivered:
        via = "smtp"
        reason = None
    else:
        if _send_resend(subject, text, str(body.email)):
            delivered = True
            via = "resend"
            reason = None
        elif _send_webhook(subject, text, str(body.email), body.name):
            delivered = True
            via = "webhook"
            reason = None

    if delivered:
        message = f"Message received and emailed to {to_addr}."
    else:
        hint = reason or "smtp_not_configured"
        message = (
            f"Message was saved, but email was not delivered ({hint}). "
            f"In the project root file .env set CONTACT_SMTP_PASSWORD to a Gmail App Password "
            f"(https://myaccount.google.com/apppasswords — 2-Step Verification must be on), "
            f"save the file, then send again. Mail goes to {to_addr}."
        )

    return {
        "ok": True,
        "saved": True,
        "delivered": delivered,
        "to": to_addr,
        "via": via,
        "reason": reason,
        "message": message,
    }


@router.get("/status")
async def contact_status():
    """Whether SMTP is configured. Never returns the password."""
    cfg = _contact_cfg()
    return {
        "to": cfg["to"],
        "smtp_configured": bool(cfg["username"] and cfg["password"]),
        "host": cfg["host"] or None,
        "setup": (
            "Open the project-root .env and set CONTACT_SMTP_PASSWORD to a Gmail App Password "
            "from https://myaccount.google.com/apppasswords"
        ),
    }
