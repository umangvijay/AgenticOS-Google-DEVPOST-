"""
AgentOS — Repository Factory

The ONE place that picks implementations based on STORAGE_BACKEND.
Nothing else in the codebase should import concrete repository classes directly.

Usage:
    from backend.repositories.factory import RepositoryFactory
    
    factory = RepositoryFactory()
    await factory.initialize()
    
    user_repo = factory.user_repo
    workflow_repo = factory.workflow_repo
    ...
"""

import logging
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class RepositoryFactory:
    """
    Creates and holds all repository instances.
    
    STORAGE_BACKEND='sqlite'    → SQLite implementations (local dev)
    STORAGE_BACKEND='firestore' → Firestore implementations (Google Cloud)
    """

    def __init__(self):
        self._initialized = False

        # All repository instances — populated by initialize()
        self.user_repo = None
        self.workflow_repo = None
        self.mcp_repo = None
        self.memory_repo = None
        self.secrets_repo = None
        self.schedule_repo = None
        self.refresh_token_repo = None
        self.notification_repo = None
        self.settings_repo = None
        self.idempotency_repo = None
        self.audit_repo = None

        # Infrastructure
        self.message_bus = None
        self.db_manager = None  # Only for SQLite

    async def initialize(self) -> None:
        """Initialize all repositories based on STORAGE_BACKEND config."""
        backend = settings.STORAGE_BACKEND.lower()
        logger.info(f"Initializing repositories with backend: {backend}")

        if backend == "firestore":
            from backend.repositories.firestore.database import FirestoreDB
            # We don't necessarily need to "init" Firestore like SQLite,
            # but we can call get_client to ensure it connects.
            await FirestoreDB.get_client()
            
            from backend.repositories.firestore.user_repository import FirestoreUserRepository
            from backend.repositories.firestore.workflow_repository import FirestoreWorkflowRepository
            from backend.repositories.firestore.mcp_repository import FirestoreMCPRepository
            from backend.repositories.firestore.idempotency_repository import FirestoreIdempotencyRepository
            from backend.repositories.firestore.memory_repository import FirestoreMemoryRepository
            
            self.user_repo = FirestoreUserRepository()
            self.workflow_repo = FirestoreWorkflowRepository()
            self.mcp_repo = FirestoreMCPRepository()
            self.idempotency_repo = FirestoreIdempotencyRepository()
            self.memory_repo = FirestoreMemoryRepository()
            
        elif backend == "sqlite":
            await self._init_sqlite()
        else:
            raise ValueError(
                f"Unknown STORAGE_BACKEND: '{backend}'. Must be 'sqlite' or 'firestore'."
            )

        self._initialized = True
        logger.info(f"All repositories initialized ({backend})")

    async def _init_sqlite(self) -> None:
        """Initialize SQLite repositories."""
        from backend.repositories.sqlite.database import DatabaseManager
        from backend.repositories.sqlite.user_repository import SQLiteUserRepository
        from backend.repositories.sqlite.workflow_repository import SQLiteWorkflowRepository
        from backend.repositories.sqlite.mcp_repository import SQLiteMCPRepository
        from backend.repositories.sqlite.memory_repository import SQLiteMemoryRepository
        from backend.repositories.sqlite.secrets_repository import SQLiteSecretsRepository
        from backend.repositories.sqlite.schedule_repository import SQLiteScheduleRepository
        from backend.repositories.sqlite.refresh_token_repository import SQLiteRefreshTokenRepository
        from backend.repositories.sqlite.notification_repository import SQLiteNotificationRepository
        from backend.repositories.sqlite.settings_repository import SQLiteSettingsRepository
        from backend.repositories.sqlite.idempotency_repository import SQLiteIdempotencyRepository
        from backend.repositories.sqlite.audit_repository import SQLiteAuditRepository
        from backend.repositories.in_memory_message_bus import InMemoryMessageBus

        # Initialize the database
        self.db_manager = DatabaseManager(settings.SQLITE_DB_PATH)
        await self.db_manager.initialize()

        # Create all repository instances with the shared db manager
        self.user_repo = SQLiteUserRepository(self.db_manager)
        self.workflow_repo = SQLiteWorkflowRepository(self.db_manager)
        self.mcp_repo = SQLiteMCPRepository(self.db_manager)
        self.memory_repo = SQLiteMemoryRepository(self.db_manager)
        self.secrets_repo = SQLiteSecretsRepository(self.db_manager)
        self.schedule_repo = SQLiteScheduleRepository(self.db_manager)
        self.refresh_token_repo = SQLiteRefreshTokenRepository(self.db_manager)
        self.notification_repo = SQLiteNotificationRepository(self.db_manager)
        self.settings_repo = SQLiteSettingsRepository(self.db_manager)
        self.idempotency_repo = SQLiteIdempotencyRepository(self.db_manager)
        self.audit_repo = SQLiteAuditRepository(self.db_manager)

        # In-process message bus for local mode
        self.message_bus = InMemoryMessageBus()

    async def _init_firestore(self) -> None:
        """Initialize Firestore repositories. Stage 3."""
        # Validate required config
        if not settings.GOOGLE_CLOUD_PROJECT:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT must be set when STORAGE_BACKEND=firestore"
            )

        from backend.repositories.firestore.database import FirestoreDB
        await FirestoreDB.get_client()
        
        from backend.repositories.firestore.user_repository import FirestoreUserRepository
        from backend.repositories.firestore.workflow_repository import FirestoreWorkflowRepository
        from backend.repositories.firestore.mcp_repository import FirestoreMCPRepository
        from backend.repositories.firestore.idempotency_repository import FirestoreIdempotencyRepository
        from backend.repositories.firestore.memory_repository import FirestoreMemoryRepository
        from backend.repositories.pubsub_message_bus import PubSubMessageBus
        from backend.repositories.in_memory_message_bus import InMemoryMessageBus
        
        self.user_repo = FirestoreUserRepository()
        self.workflow_repo = FirestoreWorkflowRepository()
        self.mcp_repo = FirestoreMCPRepository()
        self.idempotency_repo = FirestoreIdempotencyRepository()
        self.memory_repo = FirestoreMemoryRepository()

        # TODO: Implement other repositories for Firestore 
        # self.secrets_repo = SecretManagerSecretsRepository()
        # self.schedule_repo = FirestoreScheduleRepository()
        # self.refresh_token_repo = FirestoreRefreshTokenRepository()
        # self.notification_repo = FirestoreNotificationRepository()
        # self.settings_repo = FirestoreSettingsRepository()
        # self.audit_repo = FirestoreAuditRepository()

        # Pub/Sub message bus for cloud mode
        try:
            self.message_bus = PubSubMessageBus()
        except Exception:
            logger.warning("Pub/Sub unavailable, falling back to in-memory bus")
            self.message_bus = InMemoryMessageBus()

        logger.info("Firestore repositories initialized")

    async def shutdown(self) -> None:
        """Clean shutdown of all resources."""
        if self.db_manager:
            await self.db_manager.close()
        self._initialized = False
        logger.info("Repository factory shut down")

    def ensure_initialized(self) -> None:
        """Raise if not initialized. Call in health checks."""
        if not self._initialized:
            raise RuntimeError("RepositoryFactory not initialized. Call await factory.initialize() first.")
