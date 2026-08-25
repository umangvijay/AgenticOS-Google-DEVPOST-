"""
AgentOS — SQLite Database Manager

Async SQLite via aiosqlite. WAL mode for concurrent reads.
Schema migration on startup (create tables if not exist).
Database file at data/agentos.db, auto-created.
"""

import os
import logging
import aiosqlite
from pathlib import Path
from typing import Optional

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  SCHEMA — All tables per spec
# ═══════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
-- ── Users ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    password_hash TEXT,                  -- NULL for Google OAuth users
    auth_provider TEXT NOT NULL DEFAULT 'local',  -- 'local' | 'google'
    google_id TEXT UNIQUE,               -- Google OAuth sub claim
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'user',    -- 'admin' | 'user' | 'viewer'
    is_active INTEGER NOT NULL DEFAULT 1,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,                   -- ISO timestamp
    last_login TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

-- ── User Settings ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    settings_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

-- ── Refresh Tokens ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at);

-- ── Workflows ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL DEFAULT 'default_workflow',
    user_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_user ON workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON workflow_runs(status);

-- ── Tasks ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES workflow_runs(run_id) ON DELETE CASCADE,
    workflow_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    tool TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    input_data TEXT NOT NULL DEFAULT '{}',   -- JSON
    output_data TEXT,                         -- JSON
    dependencies TEXT NOT NULL DEFAULT '[]',  -- JSON array
    started_at TEXT,
    completed_at TEXT,
    lease_started_at TEXT,
    lease_expires_at TEXT,
    attempt INTEGER NOT NULL DEFAULT 0,
    timeout_seconds INTEGER NOT NULL DEFAULT 60,
    max_retries INTEGER NOT NULL DEFAULT 3,
    recovery_enabled INTEGER NOT NULL DEFAULT 0,
    max_recoveries INTEGER NOT NULL DEFAULT 3,
    max_total_attempts INTEGER NOT NULL DEFAULT 5,
    recovery_attempts INTEGER NOT NULL DEFAULT 0,
    original_input TEXT,                      -- JSON
    recovery_history TEXT DEFAULT '[]',       -- JSON array
    error TEXT,
    error_type TEXT,
    trace_id TEXT,
    PRIMARY KEY (run_id, task_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- ── Events (SSE Timeline) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    task_id TEXT,
    status TEXT,
    summary TEXT NOT NULL,
    sanitized_metadata TEXT NOT NULL DEFAULT '{}',  -- JSON
    sequence INTEGER                                 -- Auto-increment for ordering
);

CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);

-- ── Approvals ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    risk_level INTEGER NOT NULL,
    autonomy_level INTEGER NOT NULL,
    arguments TEXT NOT NULL DEFAULT '{}',    -- JSON
    arguments_hash TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    requested_by TEXT NOT NULL DEFAULT 'system',
    status TEXT NOT NULL DEFAULT 'PENDING',
    decision_by TEXT,
    decision_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_approvals_user_status ON approvals(user_id, status);

-- ── MCP Integrations ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mcps (
    mcp_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    transport TEXT NOT NULL,
    auth_json TEXT NOT NULL DEFAULT '{}',    -- JSON AuthMetadata
    scopes TEXT NOT NULL DEFAULT '[]',       -- JSON array
    health TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_updated_at TEXT,
    state TEXT NOT NULL DEFAULT 'DRAFT',     -- ConnectorState
    spec_hash TEXT,
    spec_version TEXT,
    source_uri TEXT,
    built_at TEXT,
    owner TEXT NOT NULL DEFAULT 'system',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mcps_owner ON mcps(owner);

-- ── MCP Tool Cache ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mcp_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    description TEXT NOT NULL,
    input_schema TEXT NOT NULL,              -- JSON
    mcp_id TEXT NOT NULL REFERENCES mcps(mcp_id) ON DELETE CASCADE,
    mcp_version TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    auth_requirements TEXT NOT NULL DEFAULT '[]',  -- JSON
    risk_level INTEGER NOT NULL DEFAULT 4          -- RiskLevel.CRITICAL
);

CREATE INDEX IF NOT EXISTS idx_mcp_tools_mcp ON mcp_tools(mcp_id);

-- ── Memories (Vector Store) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'semantic',  -- 'profile' | 'workflow' | 'semantic'
    metadata TEXT NOT NULL DEFAULT '{}',            -- JSON
    embedding TEXT NOT NULL,                        -- JSON array of floats
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, memory_type);

-- ── Secrets (Encrypted Vault) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS secrets (
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,           -- AES-256-GCM ciphertext (base64)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

-- ── Resumes ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resumes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Master Resume',
    is_master INTEGER NOT NULL DEFAULT 0,
    schema_json TEXT NOT NULL DEFAULT '{}',  -- JSON canonical schema
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id);

CREATE TABLE IF NOT EXISTS resume_versions (
    id TEXT PRIMARY KEY,
    resume_id TEXT NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    job_description TEXT,
    tailored_schema TEXT NOT NULL DEFAULT '{}',  -- JSON
    ats_score REAL,
    ats_breakdown TEXT,                          -- JSON scoring details
    format TEXT NOT NULL DEFAULT 'pdf',
    file_path TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resume_versions_resume ON resume_versions(resume_id);

-- ── Schedules ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    goal TEXT NOT NULL,
    cron_expression TEXT,
    schedule_type TEXT NOT NULL DEFAULT 'one_time',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    status TEXT NOT NULL DEFAULT 'active',
    next_run_at TEXT,
    last_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schedules_user ON schedules(user_id);

CREATE TABLE IF NOT EXISTS schedule_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id TEXT NOT NULL REFERENCES schedules(schedule_id) ON DELETE CASCADE,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    triggered_at TEXT NOT NULL
);

-- ── Plugins ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS plugins (
    id TEXT PRIMARY KEY,
    manifest_json TEXT NOT NULL,             -- JSON PluginManifest
    state TEXT NOT NULL DEFAULT 'installed',
    installed_by TEXT,
    installed_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- ── Audit Log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    workflow_id TEXT,
    run_id TEXT,
    task_id TEXT,
    trace_id TEXT,
    details TEXT NOT NULL DEFAULT '{}',      -- JSON
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_id);

-- ── Notifications ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',     -- JSON (e.g. workflow_id, approval_id)
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);

-- ── Idempotency Ledger ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS idempotency_ledger (
    idempotency_key TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',  -- 'running' | 'completed' | 'failed'
    result_payload TEXT,                     -- JSON cache of successful output
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


# ═══════════════════════════════════════════════════════════════════
#  DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════════

class DatabaseManager:
    """
    Async SQLite connection manager.
    
    Usage:
        db = DatabaseManager()
        await db.initialize()
        
        async with db.connection() as conn:
            cursor = await conn.execute("SELECT ...")
            rows = await cursor.fetchall()
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Create the database directory, open connection, enable WAL, run migrations."""
        # Ensure data directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        # Open connection
        self._connection = await aiosqlite.connect(self.db_path)

        # Enable WAL mode for better concurrent read performance
        await self._connection.execute("PRAGMA journal_mode=WAL")
        # Enable foreign keys
        await self._connection.execute("PRAGMA foreign_keys=ON")
        # Row factory to return dicts
        self._connection.row_factory = aiosqlite.Row

        # Run schema migration
        await self._run_migrations()

        logger.info(f"SQLite database initialized at {self.db_path}")

    async def _run_migrations(self) -> None:
        """Create all tables if they don't exist. Idempotent."""
        await self._connection.executescript(SCHEMA_SQL)
        await self._connection.commit()
        logger.info("Database schema migration complete")

    async def connection(self) -> aiosqlite.Connection:
        """Get the database connection. Raises if not initialized."""
        if self._connection is None:
            raise RuntimeError(
                "Database not initialized. Call await db.initialize() first."
            )
        return self._connection

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a single SQL statement."""
        conn = await self.connection()
        return await conn.execute(sql, params)

    async def execute_insert(self, sql: str, params: tuple = ()) -> Optional[int]:
        """Execute an INSERT and return lastrowid."""
        conn = await self.connection()
        cursor = await conn.execute(sql, params)
        await conn.commit()
        return cursor.lastrowid

    async def execute_many(self, sql: str, params_list: list) -> None:
        """Execute a statement with multiple parameter sets."""
        conn = await self.connection()
        await conn.executemany(sql, params_list)
        await conn.commit()

    async def fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Fetch a single row as a dict."""
        conn = await self.connection()
        cursor = await conn.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetch_all(self, sql: str, params: tuple = ()) -> list:
        """Fetch all rows as a list of dicts."""
        conn = await self.connection()
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        """Commit the current transaction."""
        conn = await self.connection()
        await conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("SQLite database connection closed")


# ── Singleton instance ────────────────────────────────────────────
# Created once, shared across the app via the repository factory.
db_manager = DatabaseManager()
