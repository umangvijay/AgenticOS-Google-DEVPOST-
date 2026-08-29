"""
AgentOS — Centralized Configuration

Dual-mode: local (SQLite) and cloud (Firestore).
Model selection is config, not a constant buried in code.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "AgentOS"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"

    FRONTEND_BASE_URL: str = "http://localhost:3000"
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # ── Storage Backend ──────────────────────────────────────────
    # "sqlite" for local development, "firestore" for Google Cloud.
    # This ONE setting controls which repository implementations load.
    STORAGE_BACKEND: str = "sqlite"
    SQLITE_DB_PATH: str = "data/agentos.db"

    # ── Google Cloud (Optional — only needed when STORAGE_BACKEND=firestore) ─
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_CLOUD_REGION: str = "us-central1"
    FIRESTORE_DATABASE_ID: str = "(default)"

    FIRESTORE_COLLECTION_USERS: str = "users"
    FIRESTORE_COLLECTION_WORKFLOWS: str = "workflows"
    FIRESTORE_COLLECTION_RUNS: str = "runs"
    FIRESTORE_COLLECTION_TASKS: str = "tasks"

    # ── Gemini AI ────────────────────────────────────────────────
    # Per spec: gemini-3.5-flash as default everywhere.
    # gemini-3.1-pro only for tasks needing deeper reasoning.
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2-preview"
    GEMINI_API_KEY: Optional[str] = None

    # ── xAI Grok (fallback when Gemini quota/key fails) ──────────
    XAI_API_KEY: Optional[str] = None
    GROK_MODEL: str = "grok-4-fast"

    # ── Authentication — JWT (RS256) ─────────────────────────────
    # Auto-generated on first run if missing.
    JWT_PRIVATE_KEY_PATH: str = "backend/security/keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "backend/security/keys/public.pem"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "agentos"
    JWT_AUDIENCE: str = "agentos-api"

    # ── Authentication — Google OAuth ────────────────────────────
    # Get from: https://console.cloud.google.com/apis/credentials
    # Create OAuth 2.0 Client ID (Web application). Free, no billing needed.
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None

    # ── Security — Secrets Vault ─────────────────────────────────
    # Master key for AES-256-GCM encryption of stored credentials.
    # Auto-generated on first run if empty.
    SECRETS_MASTER_KEY: Optional[str] = None
    # Optional HMAC pepper mixed into passwords before bcrypt. Leave empty
    # to keep existing hashes working; set a long random value for new installs.
    PASSWORD_PEPPER: Optional[str] = None

    # ── Contact form (SMTP to the founding team) ─────────────────
    CONTACT_TO_EMAIL: str = "godumang35@gmail.com"
    CONTACT_FROM_EMAIL: Optional[str] = None
    CONTACT_SMTP_HOST: Optional[str] = None
    CONTACT_SMTP_PORT: int = 587
    CONTACT_SMTP_USERNAME: Optional[str] = None
    CONTACT_SMTP_PASSWORD: Optional[str] = None
    CONTACT_WEBHOOK_URL: Optional[str] = None
    RESEND_API_KEY: Optional[str] = None

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_AUTH: int = 20         # per minute on auth endpoints
    RATE_LIMIT_WORKFLOW: int = 30     # per minute on workflow creation
    RATE_LIMIT_MCP_BUILD: int = 10    # per minute on MCP builder
    RATE_LIMIT_GENERAL: int = 60      # per minute general

    # ── Token Budgets ────────────────────────────────────────────
    DEFAULT_DAILY_TOKEN_LIMIT: int = 1_000_000  # per user per day
    RESEARCH_MAX_HOPS: int = 10                 # max hops for research agent

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
