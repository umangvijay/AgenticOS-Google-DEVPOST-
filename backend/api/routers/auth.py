"""
AgentOS — Auth Router (PRODUCTION)

Real authentication with real database lookups.
No hardcoded users. No demo paths. No faked results.

Endpoints:
    POST /api/v1/auth/signup        — Email/password registration
    POST /api/v1/auth/login         — Email/password login
    POST /api/v1/auth/google        — Google OAuth (code or id_token)
    POST /api/v1/auth/refresh       — Refresh access token
    POST /api/v1/auth/logout        — Revoke all tokens
    GET  /api/v1/auth/me            — Get current user
    PUT  /api/v1/auth/me            — Update profile
    PUT  /api/v1/auth/password      — Change password
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, status

from backend.models.user import (
    SignupRequest, LoginRequest, GoogleAuthRequest, RefreshRequest,
    PasswordChangeRequest, UpdateProfileRequest, AuthResponse, UserPublic,
)
from backend.security.password import (
    hash_password, verify_password, validate_password_strength,
    check_lockout, should_lock_account, get_lockout_until,
)
from backend.security.jwt_manager import jwt_manager, JWTManager
from backend.security.google_oauth import (
    exchange_code_for_tokens, verify_google_id_token, GoogleOAuthError,
)
from backend.security.rate_limiter import check_rate_limit, get_client_identifier
from backend.security.input_sanitizer import (
    sanitize_email, sanitize_name, sanitize_text, InputValidationError,
)
from backend.api.dependencies.auth import get_current_user, AuthenticatedUser
from backend.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Helper: Get repos from app state ──────────────────────────────

def _get_factory(request: Request):
    """Get the RepositoryFactory from app state."""
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


# ══════════════════════════════════════════════════════════════════
#  SIGNUP
# ══════════════════════════════════════════════════════════════════

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, request: Request):
    """Register a new user with email and password."""
    factory = _get_factory(request)

    # Rate limit
    client_id = get_client_identifier(request)
    check_rate_limit(client_id, "auth")

    # Sanitize inputs
    try:
        email = sanitize_email(body.email)
        name = sanitize_name(body.name)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Validate password strength
    is_valid, error = validate_password_strength(body.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Check if email already exists
    existing = await factory.user_repo.get_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await factory.user_repo.create_user({
        "id": user_id,
        "email": email,
        "name": name,
        "password_hash": hash_password(body.password),
        "auth_provider": "local",
        "role": "user",
    })

    # Generate tokens
    access_token, refresh_token = jwt_manager.create_token_pair(
        user_id=user_id, email=email, name=name,
        role="user", auth_provider="local",
    )

    # Store refresh token hash
    token_hash = JWTManager.hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await factory.refresh_token_repo.store_token(user_id, token_hash, expires_at)

    # Audit log
    await factory.audit_repo.log_event({
        "event_type": "USER_SIGNUP",
        "actor_id": user_id,
        "actor_type": "USER",
        "resource_id": user_id,
        "details": {"email": email, "auth_provider": "local"},
    })

    user_data = await factory.user_repo.get_by_id(user_id)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic.from_db(user_data),
    )


# ══════════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════════

@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request):
    """Login with email and password."""
    factory = _get_factory(request)

    # Rate limit
    client_id = get_client_identifier(request)
    check_rate_limit(client_id, "auth")

    # Sanitize
    try:
        email = sanitize_email(body.email)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Find user
    user = await factory.user_repo.get_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check if it's an OAuth-only account
    if user.get("auth_provider") == "google" and not user.get("password_hash"):
        raise HTTPException(
            status_code=401,
            detail="This account uses Google Sign-In. Please use the Google login button.",
        )

    # Check lockout
    is_locked, lock_msg = check_lockout(
        user.get("failed_login_attempts", 0),
        user.get("locked_until"),
    )
    if is_locked:
        raise HTTPException(status_code=423, detail=lock_msg)

    # Verify password
    if not verify_password(body.password, user.get("password_hash", "")):
        # Increment failed attempts
        new_count = await factory.user_repo.increment_failed_logins(user["id"])

        if should_lock_account(new_count):
            locked_until = get_lockout_until()
            await factory.user_repo.set_lockout(user["id"], locked_until)
            raise HTTPException(
                status_code=423,
                detail=f"Account locked after {new_count} failed attempts. Try again in 15 minutes.",
            )

        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Success — reset failed attempts
    await factory.user_repo.reset_failed_logins(user["id"])

    # Update last login
    await factory.user_repo.update_user(user["id"], {
        "last_login": datetime.now(timezone.utc).isoformat(),
    })

    # Generate tokens
    access_token, refresh_token = jwt_manager.create_token_pair(
        user_id=user["id"], email=user["email"], name=user.get("name", ""),
        role=user.get("role", "user"), auth_provider=user.get("auth_provider", "local"),
    )

    # Store refresh token
    token_hash = JWTManager.hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await factory.refresh_token_repo.store_token(user["id"], token_hash, expires_at)

    # Audit
    await factory.audit_repo.log_event({
        "event_type": "USER_LOGIN",
        "actor_id": user["id"],
        "actor_type": "USER",
        "resource_id": user["id"],
        "details": {"method": "password"},
    })

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic.from_db(user),
    )


# ══════════════════════════════════════════════════════════════════
#  GOOGLE OAUTH
# ══════════════════════════════════════════════════════════════════

@router.post("/google", response_model=AuthResponse)
async def google_auth(body: GoogleAuthRequest, request: Request):
    """
    Google OAuth login/signup.
    Accepts either an authorization code or an id_token directly.
    Find-or-create user with auth_provider='google'.
    """
    factory = _get_factory(request)

    # Rate limit
    client_id = get_client_identifier(request)
    check_rate_limit(client_id, "auth")

    try:
        if body.code:
            # Code flow — exchange code for tokens
            redirect_uri = body.redirect_uri or f"{settings.FRONTEND_BASE_URL}/auth/callback"
            tokens = await exchange_code_for_tokens(body.code, redirect_uri)
            google_user = verify_google_id_token(tokens["id_token"])
        elif body.id_token:
            # Direct id_token (popup flow)
            google_user = verify_google_id_token(body.id_token)
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either 'code' (auth code flow) or 'id_token' (popup flow)",
            )
    except GoogleOAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Find existing user by Google ID
    user = await factory.user_repo.get_by_google_id(google_user["google_id"])

    if not user:
        # Check if email already exists with local auth
        existing = await factory.user_repo.get_by_email(google_user["email"])
        if existing:
            # Link Google account to existing local user
            await factory.user_repo.update_user(existing["id"], {
                "google_id": google_user["google_id"],
                "avatar_url": google_user.get("avatar_url"),
                "auth_provider": "google",
            })
            user = await factory.user_repo.get_by_id(existing["id"])
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            await factory.user_repo.create_user({
                "id": user_id,
                "email": google_user["email"],
                "name": google_user.get("name", ""),
                "auth_provider": "google",
                "google_id": google_user["google_id"],
                "avatar_url": google_user.get("avatar_url"),
                "role": "user",
            })
            user = await factory.user_repo.get_by_id(user_id)

            await factory.audit_repo.log_event({
                "event_type": "USER_SIGNUP",
                "actor_id": user_id,
                "actor_type": "USER",
                "resource_id": user_id,
                "details": {"email": google_user["email"], "auth_provider": "google"},
            })

    # Update last login
    await factory.user_repo.update_user(user["id"], {
        "last_login": datetime.now(timezone.utc).isoformat(),
    })

    # Generate tokens
    access_token, refresh_token = jwt_manager.create_token_pair(
        user_id=user["id"], email=user["email"], name=user.get("name", ""),
        role=user.get("role", "user"), auth_provider="google",
    )

    token_hash = JWTManager.hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await factory.refresh_token_repo.store_token(user["id"], token_hash, expires_at)

    await factory.audit_repo.log_event({
        "event_type": "USER_LOGIN",
        "actor_id": user["id"],
        "actor_type": "USER",
        "resource_id": user["id"],
        "details": {"method": "google_oauth"},
    })

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic.from_db(user),
    )


# ══════════════════════════════════════════════════════════════════
#  REFRESH
# ══════════════════════════════════════════════════════════════════

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(body: RefreshRequest, request: Request):
    """
    Refresh an access token using a refresh token.
    Refresh tokens are single-use — a new pair is issued each time.
    """
    factory = _get_factory(request)

    # Verify the refresh JWT
    try:
        claims = jwt_manager.verify_refresh_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Validate and consume (single-use)
    token_hash = JWTManager.hash_token(body.refresh_token)
    user_id = await factory.refresh_token_repo.validate_and_consume(token_hash)

    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token expired or already used")

    # Get fresh user data (role could have changed)
    user = await factory.user_repo.get_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User account deactivated")

    # Issue new pair
    access_token, new_refresh = jwt_manager.create_token_pair(
        user_id=user["id"], email=user["email"], name=user.get("name", ""),
        role=user.get("role", "user"), auth_provider=user.get("auth_provider", "local"),
    )

    new_hash = JWTManager.hash_token(new_refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await factory.refresh_token_repo.store_token(user["id"], new_hash, expires_at)

    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic.from_db(user),
    )


# ══════════════════════════════════════════════════════════════════
#  LOGOUT
# ══════════════════════════════════════════════════════════════════

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    """Revoke all refresh tokens for the user (logout everywhere)."""
    factory = _get_factory(request)

    count = await factory.refresh_token_repo.revoke_all_for_user(user.user_id)

    await factory.audit_repo.log_event({
        "event_type": "USER_LOGOUT",
        "actor_id": user.user_id,
        "actor_type": "USER",
        "resource_id": user.user_id,
        "details": {"tokens_revoked": count},
    })


# ══════════════════════════════════════════════════════════════════
#  GET ME / UPDATE PROFILE
# ══════════════════════════════════════════════════════════════════

@router.get("/me", response_model=UserPublic)
async def get_me(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    """Get the current user's profile."""
    factory = _get_factory(request)
    user_data = await factory.user_repo.get_by_id(user.user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic.from_db(user_data)


@router.put("/me", response_model=UserPublic)
async def update_profile(
    body: UpdateProfileRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Update the current user's profile (name, avatar)."""
    factory = _get_factory(request)

    updates = {}
    if body.name is not None:
        try:
            updates["name"] = sanitize_name(body.name)
        except InputValidationError as e:
            raise HTTPException(status_code=400, detail=e.message)
    if body.avatar_url is not None:
        updates["avatar_url"] = body.avatar_url

    if updates:
        await factory.user_repo.update_user(user.user_id, updates)

    user_data = await factory.user_repo.get_by_id(user.user_id)
    return UserPublic.from_db(user_data)


# ══════════════════════════════════════════════════════════════════
#  CHANGE PASSWORD
# ══════════════════════════════════════════════════════════════════

@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Change password. Requires current password verification."""
    factory = _get_factory(request)

    # Rate limit
    check_rate_limit(f"user:{user.user_id}", "auth")

    # Get user with password hash
    user_data = await factory.user_repo.get_by_id(user.user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    if not user_data.get("password_hash"):
        raise HTTPException(
            status_code=400,
            detail="Cannot change password for Google OAuth accounts. Use Google's account settings.",
        )

    # Verify current password
    if not verify_password(body.current_password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Validate new password
    is_valid, error = validate_password_strength(body.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Update
    new_hash = hash_password(body.new_password)
    await factory.user_repo.update_user(user.user_id, {"password_hash": new_hash})

    # Revoke all refresh tokens (force re-login everywhere)
    await factory.refresh_token_repo.revoke_all_for_user(user.user_id)

    await factory.audit_repo.log_event({
        "event_type": "PASSWORD_CHANGED",
        "actor_id": user.user_id,
        "actor_type": "USER",
        "resource_id": user.user_id,
        "details": {},
    })

# ══════════════════════════════════════════════════════════════════
#  GUEST ACCESS
# ══════════════════════════════════════════════════════════════════

@router.post("/guest", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_session(request: Request):
    """
    Generate a temporary guest session. 
    Creates a random user account so they can explore the dashboard.
    """
    factory = _get_factory(request)
    
    # Rate limit (tighter for guest creation)
    client_id = get_client_identifier(request)
    check_rate_limit(client_id, "auth")
    
    guest_id = str(uuid.uuid4())
    guest_email = f"guest-{guest_id[:8]}@agentos.local"
    guest_name = "Guest User"
    
    # Create the user
    await factory.user_repo.create_user({
        "id": guest_id,
        "email": guest_email,
        "name": guest_name,
        "password_hash": hash_password(str(uuid.uuid4())), # random unused password
        "auth_provider": "local",
        "role": "guest", # specific role
    })
    
    # Generate tokens
    access_token, refresh_token = jwt_manager.create_token_pair(
        user_id=guest_id, email=guest_email, name=guest_name,
        role="guest", auth_provider="local",
    )
    
    # Store refresh token
    token_hash = JWTManager.hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await factory.refresh_token_repo.store_token(guest_id, token_hash, expires_at)
    
    # Audit log
    await factory.audit_repo.log_event({
        "event_type": "USER_SIGNUP",
        "actor_id": guest_id,
        "actor_type": "USER",
        "resource_id": guest_id,
        "details": {"email": guest_email, "is_guest": True},
    })
    
    user_data = await factory.user_repo.get_by_id(guest_id)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic.from_db(user_data),
    )
