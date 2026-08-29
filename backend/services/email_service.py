"""
AgentOS — Email Service

Sends real email on the user's behalf via their own SMTP account
(e.g. Gmail with an app password). SMTP settings are stored as a
vault-encrypted credential named "smtp" with fields:

    host      — e.g. "smtp.gmail.com"
    port      — e.g. "587" (STARTTLS) or "465" (SSL)
    username  — SMTP login
    password  — SMTP password / app password
    from_email (optional) — defaults to username

Used by the orchestrator's send_email tool and the core.email DAG node.
"""

import asyncio
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SMTP_CREDENTIAL_NAME = "smtp"


class EmailError(Exception):
    pass


def _send_sync(
    smtp_cfg: Dict[str, str], to: List[str], subject: str,
    body: str, html: bool, from_email: str, from_name: Optional[str],
) -> None:
    host = smtp_cfg["host"]
    port = int(smtp_cfg.get("port", 587))
    username = smtp_cfg["username"]
    password = smtp_cfg["password"]

    msg = EmailMessage()
    msg["From"] = formataddr((from_name, from_email)) if from_name else from_email
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    if html:
        msg.set_content("This email requires an HTML-capable client.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.send_message(msg)


async def send_email(
    secrets_repo,
    user_id: str,
    to: List[str] | str,
    subject: str,
    body: str,
    html: bool = False,
    from_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an email using the user's stored SMTP credential."""
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        raise EmailError("No recipients provided")
    for addr in recipients:
        if not EMAIL_PATTERN.match(addr):
            raise EmailError(f"Invalid recipient address: {addr}")
    if not subject.strip():
        raise EmailError("Subject cannot be empty")

    from backend.api.routers.credentials import load_credential
    try:
        smtp_cfg = await load_credential(secrets_repo, user_id, SMTP_CREDENTIAL_NAME)
    except ValueError:
        raise EmailError(
            "No SMTP credential configured. Store one via POST /api/v1/credentials "
            'with name "smtp" and fields: host, port, username, password.'
        )

    missing = [f for f in ("host", "username", "password") if not smtp_cfg.get(f)]
    if missing:
        raise EmailError(f"SMTP credential is missing fields: {', '.join(missing)}")

    from_email = smtp_cfg.get("from_email") or smtp_cfg["username"]

    await asyncio.to_thread(
        _send_sync, smtp_cfg, recipients, subject, body, html, from_email, from_name
    )
    logger.info("Email sent to %d recipient(s) for user %s", len(recipients), user_id)

    return {
        "sent": True,
        "to": recipients,
        "subject": subject,
        "from": from_email,
    }
