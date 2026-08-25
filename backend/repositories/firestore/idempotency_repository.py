from typing import Optional, Any
from datetime import datetime, timezone
from google.cloud import firestore
from backend.repositories.base import BaseIdempotencyRepository
from backend.repositories.firestore.database import FirestoreDB

class FirestoreIdempotencyRepository(BaseIdempotencyRepository):
    """Firestore implementation of Idempotency Ledger with true transactional locks."""

    async def _get_db(self):
        return await FirestoreDB.get_client()

    async def claim_execution(self, idempotency_key: str, workflow_id: str, task_id: str) -> Optional[Any]:
        """
        Attempts to atomically claim execution.
        Returns None if claimed successfully (i.e., we are the first worker).
        If already running, raises ValueError("already_running").
        If already completed, returns the cached result_payload.
        """
        db = await self._get_db()
        doc_ref = db.collection("idempotency_ledger").document(idempotency_key)
        
        @firestore.async_transactional
        async def claim_in_transaction(transaction, ref):
            snapshot = await ref.get(transaction=transaction)
            if snapshot.exists:
                data = snapshot.to_dict()
                if data.get("status") == "completed":
                    return data.get("result_payload")
                elif data.get("status") == "running":
                    raise ValueError("already_running")
                # If failed, we can claim it again
            
            # Not exists or failed, we claim it
            transaction.set(ref, {
                "idempotency_key": idempotency_key,
                "workflow_id": workflow_id,
                "task_id": task_id,
                "status": "running",
                "result_payload": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            return None # Claimed successfully

        transaction = db.transaction()
        return await claim_in_transaction(transaction, doc_ref)

    async def mark_completed(self, idempotency_key: str, result_payload: Any) -> None:
        db = await self._get_db()
        doc_ref = db.collection("idempotency_ledger").document(idempotency_key)
        await doc_ref.update({
            "status": "completed",
            "result_payload": result_payload,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

    async def mark_failed(self, idempotency_key: str) -> None:
        db = await self._get_db()
        doc_ref = db.collection("idempotency_ledger").document(idempotency_key)
        await doc_ref.update({
            "status": "failed",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
