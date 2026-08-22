from abc import ABC, abstractmethod
from typing import Dict, Any
from backend.models.resume import Resume
import json

class ResumeIngestionService(ABC):
    @abstractmethod
    def ingest(self, source: Any) -> Resume:
        """Parse a source format into a structured Resume object."""
        pass

class StructuredResumeIngestion(ResumeIngestionService):
    def ingest(self, source: str) -> Resume:
        """
        Parses a strictly structured JSON string into a Resume object.
        Used for Phase 8 as the initial ingestion mechanism.
        """
        try:
            return Resume.model_validate_json(source)
        except Exception as e:
            raise ValueError(f"Failed to ingest JSON resume: {e}")
