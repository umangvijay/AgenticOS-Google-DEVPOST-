from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from backend.models.memory import MemoryEntry, MemorySearchResult
import uuid
import math
from datetime import datetime, timezone

class MemoryRepository(ABC):
    @abstractmethod
    def store_memory(self, user_id: str, content: str, metadata: Dict[str, Any], embedding: List[float]) -> str:
        pass
        
    @abstractmethod
    def search_memory(self, user_id: str, query_embedding: List[float], limit: int = 5) -> List[MemorySearchResult]:
        pass

class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self):
        self._store: List[MemoryEntry] = []
        
    def store_memory(self, user_id: str, content: str, metadata: Dict[str, Any], embedding: List[float]) -> str:
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=content,
            metadata=metadata,
            embedding=embedding
        )
        self._store.append(entry)
        return entry.id
        
    def search_memory(self, user_id: str, query_embedding: List[float], limit: int = 5) -> List[MemorySearchResult]:
        results = []
        for entry in self._store:
            if entry.user_id != user_id:
                continue
            
            # Compute cosine similarity
            dot_product = sum(a * b for a, b in zip(entry.embedding, query_embedding))
            norm_a = math.sqrt(sum(a * a for a in entry.embedding))
            norm_b = math.sqrt(sum(b * b for b in query_embedding))
            
            if norm_a == 0 or norm_b == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (norm_a * norm_b)
                
            results.append(MemorySearchResult(entry=entry, similarity_score=similarity))
            
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]

# Firestore implementation requires the vector search preview features
class FirestoreMemoryRepository(MemoryRepository):
    def __init__(self, db_client):
        # db_client is the google-cloud-firestore client
        self.db = db_client
        self.collection_name = "memory"
        
    def store_memory(self, user_id: str, content: str, metadata: Dict[str, Any], embedding: List[float]) -> str:
        from google.cloud.firestore_v1.vector import Vector
        
        doc_id = str(uuid.uuid4())
        doc_ref = self.db.collection(self.collection_name).document(doc_id)
        
        doc_ref.set({
            "user_id": user_id,
            "content": content,
            "metadata": metadata,
            "embedding": Vector(embedding),
            "created_at": datetime.now(timezone.utc)
        })
        
        return doc_id
        
    def search_memory(self, user_id: str, query_embedding: List[float], limit: int = 5) -> List[MemorySearchResult]:
        from google.cloud.firestore_v1.vector import Vector
        from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
        
        collection = self.db.collection(self.collection_name)
        
        # We filter by user_id, then order by cosine distance
        query = collection.where("user_id", "==", user_id).find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
        )
        
        docs = query.stream()
        
        results = []
        for doc in docs:
            data = doc.to_dict()
            # Firestore distance might be returned differently, but for now we mock the score
            entry = MemoryEntry(
                id=doc.id,
                user_id=data["user_id"],
                content=data["content"],
                metadata=data.get("metadata", {}),
                embedding=list(data["embedding"]),
                created_at=data["created_at"]
            )
            # Find nearest doesn't always yield the score in the document directly without get_alias
            results.append(MemorySearchResult(entry=entry, similarity_score=1.0)) # TODO: extract exact distance
            
        return results
