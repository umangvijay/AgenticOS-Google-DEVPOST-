"""
AgentOS — CSRF Protection

Double-submit cookie pattern.
A random CSRF token is set as a cookie and must be echoed
back in the X-CSRF-Token header on state-changing requests.
"""

import os
import hmac
import hashlib
import logging
from typing import Optional

from fastapi import Request, HTTPException, status, Response

logger = logging.getLogger(__name__)

CSRF_COOKIE_NAME = "agentos_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_TOKEN_LENGTH = 32

# Methods that require CSRF validation
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF (API-key or OAuth callback)
EXEMPT_PATHS = {
    "/api/v1/auth/google",      # OAuth callback (verified by state param)
    "/api/v1/auth/refresh",     # Uses refresh token in body
    "/health",
}


def generate_csrf_token() -> str:
    """Generate a cryptographically random CSRF token."""
    return os.urandom(CSRF_TOKEN_LENGTH).hex()


def set_csrf_cookie(response: Response, token: Optional[str] = None) -> str:
    """
    Set the CSRF cookie on a response.
    Returns the token value.
    """
    token = token or generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,      # Must be readable by JS to send in header
        samesite="lax",
        secure=False,        # Set to True in production with HTTPS
        max_age=3600 * 24,   # 24 hours
        path="/",
    )
    return token


def validate_csrf(request: Request) -> None:
    """
    Validate CSRF token on state-changing requests.
    
    Checks that the X-CSRF-Token header matches the csrf cookie.
    Raises 403 if validation fails.
    """
    # Skip safe methods
    if request.method not in UNSAFE_METHODS:
        return

    # Skip exempt paths
    path = request.url.path
    if path in EXEMPT_PATHS:
        return

    # Skip if no cookie was set (first request)
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token:
        # No CSRF cookie — could be first request or API client
        # For API clients using Bearer auth, CSRF is less critical
        # but we still enforce it for browser clients
        return

    # Get the header token
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing. Include X-CSRF-Token header.",
        )

    # Timing-safe comparison
    if not hmac.compare_digest(cookie_token, header_token):
        logger.warning(f"CSRF validation failed for {request.method} {path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch.",
        )
