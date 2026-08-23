from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging
from enum import Enum
import os
import json

try:
    from google.cloud import logging as cloud_logging
    cloud_logger_client = cloud_logging.Client()
    cloud_logger = cloud_logger_client.logger("agentic-os-audit")
except (ImportError, Exception) as e:
    cloud_logger = None

logger = logging.getLogger("agentos_audit")

class ActorType(str, Enum):
    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    WORKER = "WORKER"
    RECOVERY_AGENT = "RECOVERY_AGENT"
    SCHEDULER = "SCHEDULER"

class AuditEvent(BaseModel):
    event_type: str
    actor_id: str
    actor_type: ActorType
    resource_id: str
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    task_id: Optional[str] = None
    trace_id: Optional[str] = None
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AuditRepository:
    def __init__(self):
        self._store = []
        
    def log_event(self, event: AuditEvent):
        # Local memory store for quick querying in tests
        self._store.append(event)
        
        payload = event.model_dump(mode='json')
        
        # Log to Cloud Logging (immutable audit sink)
        if cloud_logger:
            try:
                cloud_logger.log_struct(
                    payload,
                    severity="INFO",
                    labels={"event_type": event.event_type}
                )
            except Exception as e:
                logger.error(f"Failed to write to Cloud Logging: {e}")
        
        # Fallback structured logging
        logger.info(f"AUDIT: {json.dumps(payload)}")
        
    def get_events_for_resource(self, resource_id: str):
        return [e for e in self._store if e.resource_id == resource_id]
        
audit_repo = AuditRepository()
