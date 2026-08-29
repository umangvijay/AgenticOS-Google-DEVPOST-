"""
AgentOS — Website / endpoint health checker.

Live HTTPS probe of any public site: DNS, TLS, latency, status, redirects,
security headers, and HTML title. Used by the orchestrator and core.health.
Never targets private/loopback/metadata hosts.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
SECURITY_HEADERS = (
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
)


class HealthCheckError(Exception):
    pass


def _is_private_host(host: str) -> bool:
    if not host:
        return True
    lowered = host.lower().rstrip(".")
    if lowered in ("localhost", "metadata.google.internal") or lowered.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def assert_public_https_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HealthCheckError(f"Invalid URL: {url}")
    host = parsed.hostname
    if _is_private_host(host):
        raise HealthCheckError("Refusing to probe private/internal hosts")
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip_str = info[4][0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HealthCheckError(f"Host {host} resolves to a blocked address")
    except socket.gaierror as e:
        raise HealthCheckError(f"DNS lookup failed for {host}: {e}") from e
    return host


def _tls_info(host: str, port: int = 443) -> Dict[str, Any]:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                not_after = cert.get("notAfter")
                expires = None
                days_left = None
                if not_after:
                    expires_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                    expires = expires_dt.isoformat()
                    days_left = (expires_dt - datetime.now(timezone.utc)).days
                subject = dict(x[0] for x in cert.get("subject", ()))
                return {
                    "ok": True,
                    "tls_version": ssock.version(),
                    "subject_cn": subject.get("commonName"),
                    "expires_at": expires,
                    "days_until_expiry": days_left,
                }
    except Exception as e:
        return {"ok": False, "error": str(e).split("\n")[0][:200]}


def _grade(status_code: Optional[int], latency_ms: Optional[float], tls: Dict[str, Any], missing_headers: List[str]) -> str:
    if status_code is None:
        return "down"
    if status_code >= 500:
        return "unhealthy"
    if status_code >= 400:
        return "degraded"
    if latency_ms is not None and latency_ms > 3000:
        return "slow"
    if not tls.get("ok"):
        return "tls_issue"
    if missing_headers:
        return "ok_with_warnings"
    return "healthy"


async def check_website(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    """Probe a public website and return a structured health report."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    host = assert_public_https_url(url)

    started = time.perf_counter()
    status_code: Optional[int] = None
    final_url = url
    redirects: List[str] = []
    headers: Dict[str, str] = {}
    title = None
    body_bytes = 0
    error: Optional[str] = None

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=8) as client:
            resp = await client.get(url, headers={"User-Agent": "AgentOS-HealthCheck/1.0"})
            status_code = resp.status_code
            final_url = str(resp.url)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body_bytes = len(resp.content or b"")
            redirects = [str(r.url) for r in resp.history]
            if "text/html" in (headers.get("content-type") or ""):
                match = TITLE_RE.search(resp.text[:80_000] if resp.text else "")
                if match:
                    title = re.sub(r"\s+", " ", match.group(1)).strip()[:200]
    except Exception as e:
        error = str(e).split("\n")[0][:300]

    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    tls = _tls_info(host) if urlparse(url).scheme == "https" or urlparse(final_url).scheme == "https" else {"ok": None}
    present = [h for h in SECURITY_HEADERS if h in headers]
    missing = [h for h in SECURITY_HEADERS if h not in headers]
    grade = _grade(status_code, latency_ms, tls, missing)

    report = {
        "url": url,
        "final_url": final_url,
        "host": host,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "grade": grade,
        "title": title,
        "bytes": body_bytes,
        "redirects": redirects,
        "tls": tls,
        "security_headers": {"present": present, "missing": missing},
        "error": error,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Website health %s grade=%s status=%s latency=%sms", host, grade, status_code, latency_ms)
    return report
