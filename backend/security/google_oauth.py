"""
AgentOS — Google OAuth Integration

Uses google-auth library directly (NOT Firebase).
Works identically in local and cloud modes.
Only needs a free OAuth Client ID (no billing required).

Flow:
  1. Frontend opens Google sign-in popup
  2. User authorizes → Google returns auth code
  3. Frontend sends code to our backend
  4. Backend exchanges code for id_token via Google
  5. Backend verifies id_token → extracts user info
  6. Find-or-create local user (auth_provider="google", no password hash)
  7. Issue our own JWT pair
"""

import logging
from typing import Optional, Dict, Any

import httpx
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Google's token endpoint
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(Exception):
    """Raised when Google OAuth flow fails."""
    pass


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, Any]:
    """
    Exchange an authorization code for Google tokens.
    Returns dict with id_token, access_token, etc.
    """
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise GoogleOAuthError(
            "Google OAuth not configured. Set GOOGLE_OAUTH_CLIENT_ID and "
            "GOOGLE_OAUTH_CLIENT_SECRET in .env"
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if response.status_code != 200:
        logger.error(f"Google token exchange failed: {response.text}")
        raise GoogleOAuthError(f"Token exchange failed: {response.status_code}")

    return response.json()


def verify_google_id_token(token: str) -> Dict[str, Any]:
    """
    Verify a Google id_token and extract user info.
    
    Returns dict with:
        sub: Google user ID
        email: User's email
        email_verified: bool
        name: Full name
        picture: Avatar URL
    
    Raises GoogleOAuthError if verification fails.
    """
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise GoogleOAuthError("GOOGLE_OAUTH_CLIENT_ID not configured")

    try:
        # google-auth handles:
        # - Fetching Google's public keys (cached)
        # - Verifying the RS256 signature
        # - Checking expiry, issuer, audience
        idinfo = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )

        # Verify the issuer
        if idinfo["iss"] not in ("accounts.google.com", "https://accounts.google.com"):
            raise GoogleOAuthError("Invalid issuer")

        # Verify email is verified
        if not idinfo.get("email_verified", False):
            raise GoogleOAuthError("Google email not verified")

        return {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name", ""),
            "avatar_url": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False),
        }

    except ValueError as e:
        logger.error(f"Google ID token verification failed: {e}")
        raise GoogleOAuthError(f"Invalid Google token: {e}")


def get_google_auth_url(redirect_uri: str, state: Optional[str] = None) -> str:
    """
    Generate the Google OAuth authorization URL.
    Frontend can use this or construct its own.
    """
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise GoogleOAuthError("GOOGLE_OAUTH_CLIENT_ID not configured")

    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
