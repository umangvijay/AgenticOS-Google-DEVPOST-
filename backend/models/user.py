"""
AgentOS — User Model

Pydantic model for user data with all auth-related fields.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(BaseModel):
    """Full user model for internal use. Never send password_hash to frontend."""
    id: str
    email: str
    name: str = ""
    password_hash: Optional[str] = None       # None for Google OAuth users
    auth_provider: AuthProvider = AuthProvider.LOCAL
    google_id: Optional[str] = None           # Google OAuth sub claim
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None        # ISO timestamp
    last_login: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "User":
        """Create User from database row dict."""
        return cls(**{k: v for k, v in data.items() if k in cls.model_fields})


class UserPublic(BaseModel):
    """User data safe to send to frontend. No password_hash, no lockout internals."""
    id: str
    email: str
    name: str
    auth_provider: str
    avatar_url: Optional[str] = None
    role: str
    is_active: bool = True
    created_at: str = ""

    @classmethod
    def from_user(cls, user: User) -> "UserPublic":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            auth_provider=user.auth_provider.value if isinstance(user.auth_provider, AuthProvider) else user.auth_provider,
            avatar_url=user.avatar_url,
            role=user.role.value if isinstance(user.role, UserRole) else user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "UserPublic":
        return cls(
            id=data["id"],
            email=data["email"],
            name=data.get("name", ""),
            auth_provider=data.get("auth_provider", "local"),
            avatar_url=data.get("avatar_url"),
            role=data.get("role", "user"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", ""),
        )


# ── API Request/Response Schemas ──────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    code: Optional[str] = None          # Authorization code (code flow)
    id_token: Optional[str] = None      # Direct id_token (implicit/popup)
    redirect_uri: Optional[str] = None  # For code exchange

class RefreshRequest(BaseModel):
    refresh_token: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
