"""
AgentOS — SQLite Memory Repository

Vector similarity via cosine distance in Python.
Fine for <10k memories per user. Cloud uses Firestore native vector search.
Strict per-user isolation — no cross-user retrieval, ever.
"""

import json
import math
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.repositories.base import BaseMemoryRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SQLiteMemoryRepository(BaseMemoryRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def store_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any],
        embedding: List[float],
    ) -> str:
        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self.db.execute(
            """
            INSERT INTO memories (id, user_id, content, memory_type, metadata, embedding, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                user_id,
                content,
                memory_type,
                json.dumps(metadata),
                json.dumps(embedding),
                now,
                now,
            ),
        )
        await self.db.commit()
        return memory_id

    async def search_memory(
        self,
        user_id: str,
        query_embedding: List[float],
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Full-table scan with Python cosine similarity.
        Acceptable for <10k rows per user in SQLite mode.
        In Firestore mode, native vector search handles this.
        """
        if memory_type:
            rows = await self.db.fetch_all(
                "SELECT * FROM memories WHERE user_id = ? AND memory_type = ?",
                (user_id, memory_type),
            )
        else:
            rows = await self.db.fetch_all(
                "SELECT * FROM memories WHERE user_id = ?",
                (user_id,),
            )

        scored = []
        for row in rows:
            embedding = json.loads(row["embedding"])
            score = _cosine_similarity(embedding, query_embedding)
            entry = {
                "id": row["id"],
                "user_id": row["user_id"],
                "content": row["content"],
                "memory_type": row["memory_type"],
                "metadata": json.loads(row.get("metadata", "{}")),
                "similarity_score": score,
                "created_at": row["created_at"],
            }
            scored.append(entry)

        # Sort by similarity descending
        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:limit]

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        conn = await self.db.connection()
        cursor = await conn.execute(
            "DELETE FROM memories WHERE id = ? AND user_id = ?",
            (memory_id, user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def update_memory(self, user_id: str, memory_id: str, content: str, embedding: List[float]) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()
        cursor = await conn.execute(
            """
            UPDATE memories
            SET content = ?, embedding = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (content, json.dumps(embedding), now, memory_id, user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
