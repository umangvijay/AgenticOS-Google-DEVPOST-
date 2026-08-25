"""
AgentOS — JWT Manager (RS256)

Asymmetric RSA-256 signing. Auto-generates keypair on first run.
Access tokens: 15 min. Refresh tokens: 7 days, single-use with rotation.
"""

import os
import hashlib
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────
ALGORITHM = "RS256"
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class JWTManager:
    """
    RS256 JWT manager with auto-generated RSA keypair.
    
    Usage:
        jwt_mgr = JWTManager()
        jwt_mgr.initialize()
        
        access, refresh = jwt_mgr.create_token_pair(user_id, email, name, role)
        claims = jwt_mgr.verify_access_token(access)
    """

    def __init__(self):
        self._private_key: Optional[bytes] = None
        self._public_key: Optional[bytes] = None
        self._initialized = False

    def initialize(self) -> None:
        """Load or generate RSA keypair."""
        priv_path = Path(settings.JWT_PRIVATE_KEY_PATH)
        pub_path = Path(settings.JWT_PUBLIC_KEY_PATH)

        if priv_path.exists() and pub_path.exists():
            self._private_key = priv_path.read_bytes()
            self._public_key = pub_path.read_bytes()
            logger.info("JWT keys loaded from disk")
        else:
            self._generate_keypair(priv_path, pub_path)
            logger.info("JWT RSA keypair generated")

        self._initialized = True

    def _generate_keypair(self, priv_path: Path, pub_path: Path) -> None:
        """Generate a new RSA-2048 keypair and save to disk."""
        # Create directory
        priv_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )

        # Serialize private key (unencrypted PEM — in production use KMS)
        self._private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Serialize public key
        self._public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Write to disk
        priv_path.write_bytes(self._private_key)
        pub_path.write_bytes(self._public_key)

        # Restrict private key permissions
        os.chmod(str(priv_path), 0o600)

    # ── Token Creation ────────────────────────────────────────────

    def create_token_pair(
        self,
        user_id: str,
        email: str,
        name: str,
        role: str,
        auth_provider: str = "local",
    ) -> Tuple[str, str]:
        """
        Create an access + refresh token pair.
        Returns (access_token, refresh_token).
        """
        self._ensure_initialized()

        now = datetime.now(timezone.utc)
        jti_access = str(uuid.uuid4())
        jti_refresh = str(uuid.uuid4())

        # Access token (15 min)
        access_payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "role": role,
            "auth_provider": auth_provider,
            "type": TOKEN_TYPE_ACCESS,
            "jti": jti_access,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        }

        # Refresh token (7 days)
        refresh_payload = {
            "sub": user_id,
            "type": TOKEN_TYPE_REFRESH,
            "jti": jti_refresh,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": now,
            "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        }

        access_token = jwt.encode(access_payload, self._private_key, algorithm=ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, self._private_key, algorithm=ALGORITHM)

        return access_token, refresh_token

    # ── Token Verification ────────────────────────────────────────

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verify an access token. Returns claims dict.
        Raises jwt.InvalidTokenError on any failure.
        """
        self._ensure_initialized()

        claims = jwt.decode(
            token,
            self._public_key,
            algorithms=[ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )

        if claims.get("type") != TOKEN_TYPE_ACCESS:
            raise jwt.InvalidTokenError("Not an access token")

        return claims

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a refresh token. Returns claims dict.
        The caller must also check it against the refresh token store (single-use).
        """
        self._ensure_initialized()

        claims = jwt.decode(
            token,
            self._public_key,
            algorithms=[ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )

        if claims.get("type") != TOKEN_TYPE_REFRESH:
            raise jwt.InvalidTokenError("Not a refresh token")

        return claims

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage (refresh tokens stored as hashes)."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError("JWTManager not initialized. Call jwt_mgr.initialize() first.")


# ── Singleton ─────────────────────────────────────────────────────
jwt_manager = JWTManager()
