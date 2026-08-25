import json
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from backend.repositories.base import BaseMemoryRepository
from backend.repositories.firestore.database import FirestoreDB

class FirestoreMemoryRepository(BaseMemoryRepository):
    """Firestore implementation using native Vector Search capabilities."""

    async def _get_db(self):
        return await FirestoreDB.get_client()

    async def add_memory(self, memory_id: str, user_id: str, content: str, embedding: List[float], metadata: Dict[str, Any] = None) -> None:
        db = await self._get_db()
        doc_ref = db.collection("memories").document(memory_id)
        
        data = {
            "memory_id": memory_id,
            "user_id": user_id,
            "content": content,
            "embedding": Vector(embedding), # Firestore native Vector object
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await doc_ref.set(data)

    async def search_memory(self, user_id: str, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        db = await self._get_db()
        
        # Firestore Vector Search syntax
        # We need to filter by user_id to enforce strict isolation!
        # Requires creating a composite index in Firestore manually:
        # Collection: memories
        # Fields: user_id ASC, embedding VECTOR
        query = db.collection("memories").where("user_id", "==", user_id)
        
        # Find Nearest Neighbors
        # Using cosine distance.
        vector_query = query.find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_embedding),
            distance_measure=firestore.DistanceMeasure.COSINE,
            limit=limit,
            distance_result_field="vector_distance"
        )
        
        results = []
        async for doc in vector_query.stream():
            data = doc.to_dict()
            # Convert Vector back to list if needed, or leave out
            data.pop("embedding", None) 
            results.append(data)
            
        return results

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        db = await self._get_db()
        doc_ref = db.collection("memories").document(memory_id)
        
        doc = await doc_ref.get()
        if not doc.exists:
            return False
            
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            return False
            
        await doc_ref.delete()
        return True

    async def get_memories_by_category(self, user_id: str, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        db = await self._get_db()
        query = db.collection("memories")\
                  .where("user_id", "==", user_id)\
                  .where("metadata.category", "==", category)\
                  .order_by("created_at", direction=firestore.Query.DESCENDING)\
                  .limit(limit)
                  
        results = []
        async for doc in query.stream():
            data = doc.to_dict()
            data.pop("embedding", None)
            results.append(data)
            
        return results
