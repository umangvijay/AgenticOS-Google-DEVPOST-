from typing import Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging

logger = logging.getLogger("agentos_audit")

class AuditEvent(BaseModel):
    event_type: str
    user_id: str
    resource_id: str
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AuditRepository:
    def __init__(self):
        self._store = []
        
    def log_event(self, event: AuditEvent):
        self._store.append(event)
        # Also log to structured logging
        logger.info(f"AUDIT: {event.model_dump_json()}")
        
    def get_events_for_resource(self, resource_id: str):
        return [e for e in self._store if e.resource_id == resource_id]
        
audit_repo = AuditRepository()
