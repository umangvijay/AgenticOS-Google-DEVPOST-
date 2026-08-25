"""
AgentOS — Password Security

bcrypt hashing with policy enforcement and lockout.
Policy: 8+ chars, upper/lower/digit/special.
Common password rejection. Lockout: 5 failures → 15 min.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

import bcrypt

logger = logging.getLogger(__name__)

# ── Policy constants ──────────────────────────────────────────────
MIN_LENGTH = 8
MAX_LENGTH = 72  # bcrypt's native limit
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Top 100 most common passwords (subset for fast rejection)
COMMON_PASSWORDS = frozenset({
    "password", "123456", "12345678", "qwerty", "abc123", "monkey",
    "1234567", "letmein", "trustno1", "dragon", "baseball", "iloveyou",
    "master", "sunshine", "ashley", "bailey", "passw0rd", "shadow",
    "123456789", "1234567890", "password1", "password123", "admin",
    "welcome", "football", "charlie", "donald", "login", "princess",
    "starwars", "solo", "qwerty123", "welcome1", "hello", "charlie1",
})


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with auto-generated salt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash. Timing-safe."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password meets policy requirements.
    Returns (is_valid, error_message).
    """
    if len(password) < MIN_LENGTH:
        return False, f"Password must be at least {MIN_LENGTH} characters"

    if len(password) > MAX_LENGTH:
        return False, f"Password must be at most {MAX_LENGTH} characters"

    if password.lower() in COMMON_PASSWORDS:
        return False, "This password is too common. Choose a stronger one."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False, "Password must contain at least one special character"

    return True, None


def check_lockout(failed_attempts: int, locked_until: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Check if an account is locked out.
    Returns (is_locked, reason_message).
    """
    if locked_until:
        lock_time = datetime.fromisoformat(locked_until)
        now = datetime.now(timezone.utc)
        if now < lock_time:
            remaining = (lock_time - now).seconds // 60
            return True, f"Account locked. Try again in {remaining + 1} minute(s)."

    return False, None


def should_lock_account(failed_attempts: int) -> bool:
    """Check if the account should be locked after this failed attempt."""
    return failed_attempts >= MAX_FAILED_ATTEMPTS


def get_lockout_until() -> datetime:
    """Get the lockout expiry timestamp."""
    return datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
