"""
AgentOS — Secrets Vault

AES-256-GCM encryption for stored credentials.
Key derived via PBKDF2 from SECRETS_MASTER_KEY.

Same interface backed by Secret Manager once STORAGE_BACKEND=firestore.
Never log a secret. Never return one in an API response.
"""

import os
import base64
import logging
import hashlib
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# PBKDF2 parameters
KDF_ITERATIONS = 480_000  # OWASP 2024 recommendation for PBKDF2-SHA256
KDF_SALT_SIZE = 16        # 128-bit salt
NONCE_SIZE = 12           # 96-bit nonce for AES-GCM
KEY_SIZE = 32             # 256-bit key


class SecretsVault:
    """
    Encrypts and decrypts secrets using AES-256-GCM.
    
    The master key is derived from SECRETS_MASTER_KEY via PBKDF2.
    Each encrypted value includes: salt + nonce + ciphertext + tag.
    Everything is base64-encoded for storage in SQLite.
    
    Usage:
        vault = SecretsVault()
        vault.initialize()
        
        encrypted = vault.encrypt("my-api-key-value")
        decrypted = vault.decrypt(encrypted)
    """

    def __init__(self):
        self._master_key: Optional[str] = None
        self._initialized = False

    def initialize(self) -> None:
        """Load or auto-generate the master key."""
        self._master_key = settings.SECRETS_MASTER_KEY
        
        self.use_gcp = settings.STORAGE_BACKEND.lower() == "firestore"
        if self.use_gcp:
            from backend.security.gcp_secret_manager import GCPSecretManager
            self.gcp_client = GCPSecretManager()
            logger.info("SecretsVault configured to use GCP Secret Manager.")
        else:
            if not self._master_key:
                # Auto-generate on first run
                self._master_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
                logger.warning(
                    "SECRETS_MASTER_KEY not set. Auto-generated a key. "
                    "Add it to .env to persist across restarts: "
                    f"SECRETS_MASTER_KEY={self._master_key}"
                )

        self._initialized = True

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive a 256-bit encryption key from the master key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=KDF_ITERATIONS,
        )
        return kdf.derive(self._master_key.encode("utf-8"))

    def encrypt(self, plaintext: str, secret_id: str = None) -> str:
        """
        Encrypt a plaintext secret. If using GCP, uses secret_id to store it remotely.
        Otherwise returns a base64-encoded string containing:
        [salt (16 bytes)][nonce (12 bytes)][ciphertext + GCM tag]
        """
        self._ensure_initialized()

        if self.use_gcp and secret_id:
            self.gcp_client.set_secret(secret_id, plaintext)
            return f"gcp://{secret_id}"
            
        salt = os.urandom(KDF_SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        key = self._derive_key(salt)

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        # Pack: salt + nonce + ciphertext (includes 16-byte GCM tag)
        packed = salt + nonce + ciphertext
        return base64.urlsafe_b64encode(packed).decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted secret.
        
        Expects the base64 format from encrypt(), or a gcp:// URI.
        Raises ValueError on tampered/invalid data.
        """
        self._ensure_initialized()

        if encrypted.startswith("gcp://"):
            if not self.use_gcp:
                raise ValueError("Secret is stored in GCP but STORAGE_BACKEND != firestore")
            secret_id = encrypted[6:]
            return self.gcp_client.get_secret(secret_id)

        try:
            packed = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
        except Exception:
            raise ValueError("Invalid encrypted data format")

        if len(packed) < KDF_SALT_SIZE + NONCE_SIZE + 16:
            raise ValueError("Encrypted data too short")

        salt = packed[:KDF_SALT_SIZE]
        nonce = packed[KDF_SALT_SIZE:KDF_SALT_SIZE + NONCE_SIZE]
        ciphertext = packed[KDF_SALT_SIZE + NONCE_SIZE:]

        key = self._derive_key(salt)
        aesgcm = AESGCM(key)

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception:
            raise ValueError("Decryption failed — data may be tampered or wrong master key")

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError("SecretsVault not initialized. Call vault.initialize() first.")


# ── Singleton ─────────────────────────────────────────────────────
secrets_vault = SecretsVault()
