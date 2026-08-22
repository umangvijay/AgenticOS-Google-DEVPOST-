from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

class MemoryEntry(BaseModel):
    id: str = Field(description="Unique identifier for the memory entry")
    user_id: str = Field(description="User ID this memory belongs to")
    content: str = Field(description="The semantic text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional structured metadata")
    embedding: List[float] = Field(description="Vector embedding (max 2048 dimensions)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemorySearchResult(BaseModel):
    entry: MemoryEntry
    similarity_score: float = Field(description="Cosine similarity score (0 to 1)")
