from typing import Optional, Dict, Any, List
from google.cloud import firestore
from backend.repositories.base import BaseUserRepository
from backend.repositories.firestore.database import FirestoreDB
from datetime import datetime, timezone

class FirestoreUserRepository(BaseUserRepository):
    """Firestore implementation of BaseUserRepository."""

    def __init__(self):
        self.collection_name = "users"

    async def _get_collection(self):
        db = await FirestoreDB.get_client()
        return db.collection(self.collection_name)

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        col = await self._get_collection()
        doc = await col.document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        col = await self._get_collection()
        docs = col.where("email", "==", email).limit(1).stream()
        async for doc in docs:
            return doc.to_dict()
        return None

    async def create(self, user: Dict[str, Any]) -> str:
        col = await self._get_collection()
        user_id = user.get("id")
        if not user_id:
            raise ValueError("User dict must have 'id'")
        
        # Ensure timestamp
        if "created_at" not in user:
            user["created_at"] = datetime.now(timezone.utc).isoformat()
            
        await col.document(user_id).set(user)
        return user_id

    async def update(self, user_id: str, updates: Dict[str, Any]) -> bool:
        col = await self._get_collection()
        doc_ref = col.document(user_id)
        if "updated_at" not in updates:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
        try:
            await doc_ref.update(updates)
            return True
        except Exception:
            return False

    async def get_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        col = await self._get_collection()
        docs = col.where("google_id", "==", google_id).limit(1).stream()
        async for doc in docs:
            return doc.to_dict()
        return None
