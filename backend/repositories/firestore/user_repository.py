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
            data = doc.to_dict() or {}
            data.setdefault("id", user_id)
            return data
        return None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        col = await self._get_collection()
        docs = col.where("email", "==", email).limit(1).stream()
        async for doc in docs:
            return doc.to_dict()
        return None

    async def create_user(self, user_data: Dict[str, Any]) -> str:
        return await self.create(user_data)

    async def create(self, user: Dict[str, Any]) -> str:
        col = await self._get_collection()
        user_id = user.get("id")
        if not user_id:
            raise ValueError("User dict must have 'id'")
        payload = dict(user)
        payload["id"] = user_id
        payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        payload.setdefault("failed_login_attempts", 0)
        payload.setdefault("is_active", True)
        await col.document(user_id).set(payload)
        return user_id

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        return await self.update(user_id, updates)

    async def increment_failed_logins(self, user_id: str) -> int:
        user = await self.get_by_id(user_id) or {}
        count = int(user.get("failed_login_attempts") or 0) + 1
        await self.update(user_id, {"failed_login_attempts": count})
        return count

    async def reset_failed_logins(self, user_id: str) -> None:
        await self.update(user_id, {"failed_login_attempts": 0, "locked_until": None})

    async def set_lockout(self, user_id: str, locked_until: datetime) -> None:
        value = locked_until.isoformat() if hasattr(locked_until, "isoformat") else str(locked_until)
        await self.update(user_id, {"locked_until": value})

    async def delete_user(self, user_id: str) -> bool:
        col = await self._get_collection()
        ref = col.document(user_id)
        snap = await ref.get()
        if not snap.exists:
            return False
        await ref.delete()
        return True

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
