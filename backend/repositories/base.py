"""
AgentOS — Repository Abstract Base Classes

One interface per domain. Nothing else in the codebase should know
which backend (SQLite, Firestore, in-memory) is active.

Every existing repository (InMemoryWorkflowRepository, FirestoreWorkflowRepository,
InMemoryMCPRepository, etc.) will be updated to extend these base classes.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
#  USER REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseUserRepository(ABC):
    """Manages user accounts, authentication state, and lockout."""

    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user. Returns user_id. Raises if email already exists."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email. Returns None if not found."""
        ...

    @abstractmethod
    async def get_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Google OAuth sub claim. Returns None if not found."""
        ...

    @abstractmethod
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user fields. Returns True if user existed and was updated."""
        ...

    @abstractmethod
    async def increment_failed_logins(self, user_id: str) -> int:
        """Increment failed login counter. Returns new count."""
        ...

    @abstractmethod
    async def reset_failed_logins(self, user_id: str) -> None:
        """Reset failed login counter and locked_until."""
        ...

    @abstractmethod
    async def set_lockout(self, user_id: str, locked_until: datetime) -> None:
        """Lock the account until the given timestamp."""
        ...

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user. Returns True if existed."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  WORKFLOW REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseWorkflowRepository(ABC):
    """
    Manages workflow runs, tasks, approvals, and events.
    Extends the existing WorkflowRepository interface to support user_id scoping.
    """

    @abstractmethod
    async def save_run(self, run_data: Dict[str, Any]) -> None:
        """Persist a workflow run."""
        ...

    @abstractmethod
    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a workflow run by ID."""
        ...

    @abstractmethod
    async def list_runs(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List workflow runs for a user, ordered by created_at descending."""
        ...

    @abstractmethod
    async def update_run_status(self, run_id: str, status: str) -> None:
        """Update the status of a workflow run."""
        ...

    @abstractmethod
    async def save_task(self, task_data: Dict[str, Any]) -> None:
        """Persist a task."""
        ...

    @abstractmethod
    async def get_task(self, run_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task within a run."""
        ...

    @abstractmethod
    async def update_task(self, run_id: str, task_id: str, updates: Dict[str, Any]) -> None:
        """Update task fields."""
        ...

    @abstractmethod
    async def claim_task(self, run_id: str, task_id: str, lease_seconds: int) -> bool:
        """
        Atomically claim a task for execution.
        Must use a transaction — never get-then-write.
        Returns True if claimed successfully.
        """
        ...

    @abstractmethod
    async def create_if_absent(self, run_data: Dict[str, Any]) -> bool:
        """
        Idempotent run creation. Returns True if created, False if already exists.
        Used to prevent duplicate runs from duplicate triggers.
        """
        ...

    # ── Approvals ────────────────────────────────────────────────

    @abstractmethod
    async def save_approval(self, approval_data: Dict[str, Any]) -> None:
        """Save an approval request."""
        ...

    @abstractmethod
    async def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Get an approval by ID."""
        ...

    @abstractmethod
    async def list_pending_approvals(self, user_id: str) -> List[Dict[str, Any]]:
        """List all pending approvals for a user."""
        ...

    @abstractmethod
    async def resolve_approval(self, approval_id: str, new_status: str, decision_by: str) -> bool:
        """
        Atomically transition a PENDING approval to APPROVED or REJECTED.
        Returns True if successful (was actually PENDING).
        """
        ...

    # ── Events (SSE Timeline) ────────────────────────────────────

    @abstractmethod
    async def save_event(self, event_data: Dict[str, Any]) -> None:
        """Save a workflow event for the SSE timeline."""
        ...

    @abstractmethod
    async def get_events(self, run_id: str, after_event_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get events for a run, optionally after a specific event_id.
        Used for SSE reconnection (poll with last_event_id cursor).
        """
        ...


# ═══════════════════════════════════════════════════════════════════
#  MCP REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseMCPRepository(ABC):
    """Manages MCP integrations, their tools, and health status."""

    @abstractmethod
    async def register_mcp(self, manifest_data: Dict[str, Any]) -> None:
        """Register or update an MCP manifest."""
        ...

    @abstractmethod
    async def get_mcp(self, mcp_id: str) -> Optional[Dict[str, Any]]:
        """Get an MCP manifest by ID."""
        ...

    @abstractmethod
    async def list_mcps(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all MCPs, optionally filtered by owner."""
        ...

    @abstractmethod
    async def update_mcp_health(self, mcp_id: str, status: str, timestamp: datetime) -> None:
        """Update health status."""
        ...

    @abstractmethod
    async def set_mcp_enabled(self, mcp_id: str, enabled: bool) -> None:
        """Enable or disable an MCP."""
        ...

    @abstractmethod
    async def update_mcp_state(self, mcp_id: str, state: str) -> None:
        """Update connector state (draft → pending-review → tested → active → disabled)."""
        ...

    @abstractmethod
    async def delete_mcp(self, mcp_id: str) -> bool:
        """Delete an MCP and its cached tools. Returns True if existed."""
        ...

    @abstractmethod
    async def cache_tools(self, mcp_id: str, tools: List[Dict[str, Any]]) -> None:
        """Cache discovered tool definitions for an MCP."""
        ...

    @abstractmethod
    async def get_cached_tools(self, mcp_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all cached tools, optionally filtered by mcp_id."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  MEMORY REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseMemoryRepository(ABC):
    """
    Manages semantic memory with vector embeddings.
    Strict per-user isolation — no cross-user retrieval, ever.
    """

    @abstractmethod
    async def store_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any],
        embedding: List[float]
    ) -> str:
        """
        Store a memory entry with its embedding vector.
        memory_type: 'profile' | 'workflow' | 'semantic'
        Returns the memory_id.
        """
        ...

    @abstractmethod
    async def search_memory(
        self,
        user_id: str,
        query_embedding: List[float],
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search memories by vector similarity. Cosine distance.
        Results include: id, content, metadata, similarity_score.
        Always scoped to user_id.
        """
        ...

    @abstractmethod
    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory. Returns True if existed."""
        ...

    @abstractmethod
    async def update_memory(self, user_id: str, memory_id: str, content: str, embedding: List[float]) -> bool:
        """Update content and re-embed a memory. Returns True if existed."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  SECRETS REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseSecretsRepository(ABC):
    """
    Stores encrypted credentials per user.
    The repository stores/retrieves ciphertext only.
    Encryption/decryption is done by the SecretsVault service.
    """

    @abstractmethod
    async def store_secret(self, user_id: str, key: str, encrypted_value: str) -> None:
        """Store an encrypted secret. Overwrites if key already exists for user."""
        ...

    @abstractmethod
    async def get_secret(self, user_id: str, key: str) -> Optional[str]:
        """Get an encrypted secret value. Returns None if not found."""
        ...

    @abstractmethod
    async def delete_secret(self, user_id: str, key: str) -> bool:
        """Delete a secret. Returns True if existed."""
        ...

    @abstractmethod
    async def list_secret_keys(self, user_id: str) -> List[str]:
        """List all secret key names for a user (never the values)."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  SCHEDULE REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseScheduleRepository(ABC):
    """Manages scheduled workflow triggers."""

    @abstractmethod
    async def create_schedule(self, schedule_data: Dict[str, Any]) -> None:
        """Create a new schedule."""
        ...

    @abstractmethod
    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID."""
        ...

    @abstractmethod
    async def list_schedules(self, user_id: str) -> List[Dict[str, Any]]:
        """List all schedules for a user."""
        ...

    @abstractmethod
    async def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> None:
        """Update schedule fields."""
        ...

    @abstractmethod
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule. Returns True if existed."""
        ...

    @abstractmethod
    async def record_execution(self, schedule_id: str, run_id: str, status: str) -> None:
        """Record that a schedule fired and produced a workflow run."""
        ...

    @abstractmethod
    async def get_execution_history(self, schedule_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent execution history for a schedule."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  IDEMPOTENCY REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseIdempotencyRepository(ABC):
    """
    Exactly-once execution ledger.
    Prevents duplicate tool calls in distributed/concurrent environments.
    """

    @abstractmethod
    async def atomic_insert(self, key: str, workflow_id: str, task_id: str) -> bool:
        """
        Atomically attempt to insert a 'running' lock.
        Returns True if successfully inserted (we own the lock).
        Returns False if the key already exists (another worker has it).
        """
        ...

    @abstractmethod
    async def get_record(self, key: str) -> Optional[Dict[str, Any]]:
        """Get an idempotency record by key. Returns status, result_payload, etc."""
        ...

    @abstractmethod
    async def commit_success(self, key: str, result_payload: str) -> None:
        """Mark an execution as completed with the result payload."""
        ...

    @abstractmethod
    async def commit_failure(self, key: str) -> None:
        """Mark an execution as failed, freeing the lock for retry."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  AUDIT REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseAuditRepository(ABC):
    """Append-only, integrity-checked audit log."""

    @abstractmethod
    async def log_event(self, event_data: Dict[str, Any]) -> None:
        """Append an audit event. Never log secrets or bearer tokens."""
        ...

    @abstractmethod
    async def get_events(self, resource_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit events for a resource."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  REFRESH TOKEN REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseRefreshTokenRepository(ABC):
    """Manages refresh token hashes for JWT rotation and logout."""

    @abstractmethod
    async def store_token(self, user_id: str, token_hash: str, expires_at: datetime) -> None:
        """Store a hashed refresh token."""
        ...

    @abstractmethod
    async def validate_and_consume(self, token_hash: str) -> Optional[str]:
        """
        Validate a refresh token hash exists and is not expired.
        Atomically delete it (single-use). Returns user_id if valid.
        """
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user (logout everywhere). Returns count."""
        ...

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Delete expired tokens. Returns count deleted."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  NOTIFICATION REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseNotificationRepository(ABC):
    """Manages in-app notifications."""

    @abstractmethod
    async def create_notification(self, notification_data: Dict[str, Any]) -> str:
        """Create a notification. Returns notification_id."""
        ...

    @abstractmethod
    async def list_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List notifications for a user."""
        ...

    @abstractmethod
    async def mark_read(self, notification_id: str) -> None:
        """Mark a single notification as read."""
        ...

    @abstractmethod
    async def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        ...

    @abstractmethod
    async def get_unread_count(self, user_id: str) -> int:
        """Get the unread notification count for a user."""
        ...


# ═══════════════════════════════════════════════════════════════════
#  SETTINGS REPOSITORY
# ═══════════════════════════════════════════════════════════════════

class BaseSettingsRepository(ABC):
    """Per-user settings (autonomy level, theme, preferences)."""

    @abstractmethod
    async def get_settings(self, user_id: str) -> Dict[str, Any]:
        """Get settings for a user. Returns defaults if none stored."""
        ...

    @abstractmethod
    async def update_settings(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Update (merge) settings for a user."""
        ...
