"""
AgentOS — Auth Dependencies (PRODUCTION)

RS256 JWT verification. No hardcoded tokens. No "test_token" bypass.
User identity comes from authenticated JWT, NEVER from request body.

Usage in routers:
    @router.get("/me")
    async def get_me(user: AuthenticatedUser = Depends(get_current_user)):
        return user
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from backend.security.jwt_manager import jwt_manager
from backend.security.rbac import Role

logger = logging.getLogger(__name__)

# ── Security scheme ───────────────────────────────────────────────
# auto_error=False so we can provide better error messages
security_scheme = HTTPBearer(auto_error=False)


# ── Authenticated User ───────────────────────────────────────────
@dataclass
class AuthenticatedUser:
    """
    Extracted from a verified JWT. Available in every protected route.
    No database lookup needed for basic auth checks.
    """
    user_id: str
    email: str
    name: str
    role: str
    auth_provider: str

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_viewer(self) -> bool:
        return self.role == Role.VIEWER


# ── Dependencies ──────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> AuthenticatedUser:
    """
    Verify the JWT access token and return the authenticated user.
    
    Validates:
    - Token is present
    - RS256 signature is valid (using public key)
    - Token is not expired
    - Issuer and audience match
    - Token type is 'access'
    
    Returns AuthenticatedUser with claims from the token.
    Raises 401 on any failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        claims = jwt_manager.verify_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Use /api/v1/auth/refresh to get a new one.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user identity from verified claims
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
        )

    return AuthenticatedUser(
        user_id=user_id,
        email=claims.get("email", ""),
        name=claims.get("name", ""),
        role=claims.get("role", "user"),
        auth_provider=claims.get("auth_provider", "local"),
    )


async def get_current_user_id(
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """Convenience dependency that returns just the user_id string."""
    return user.user_id


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require admin role. Returns user if admin, raises 403 otherwise."""
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


async def require_not_viewer(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require at least 'user' role (not 'viewer'). For write operations."""
    if user.is_viewer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required. Viewer role cannot perform this action.",
        )
    return user
