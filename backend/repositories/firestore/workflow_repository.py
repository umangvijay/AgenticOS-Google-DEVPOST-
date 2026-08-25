import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from google.cloud import firestore
from backend.repositories.base import BaseWorkflowRepository
from backend.repositories.firestore.database import FirestoreDB
from backend.models.schemas import Task, WorkflowRun, WorkflowEvent
from backend.models.security import ApprovalRequest

class FirestoreWorkflowRepository(BaseWorkflowRepository):
    """Firestore implementation of BaseWorkflowRepository."""

    async def _get_db(self):
        return await FirestoreDB.get_client()

    async def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        db = await self._get_db()
        doc = await db.collection("workflow_runs").document(run_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        
        # Firestore returns naive datetime objects if not careful, but Pydantic handles parsing
        # Tasks are stored as a list of dicts within the run
        return WorkflowRun(**data)

    async def save_run(self, run: Dict[str, Any]) -> None:
        db = await self._get_db()
        run_id = run.get("run_id")
        if not run_id:
            raise ValueError("Run dict must have 'run_id'")
        await db.collection("workflow_runs").document(run_id).set(run)

    async def list_runs(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        # Note: Firestore offset requires cursor or is inefficient with skip, 
        # but for simple implementations we can use standard limit/offset if supported,
        # or we just fetch and slice. Here we'll just fetch limit.
        db = await self._get_db()
        query = db.collection("workflow_runs").where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        runs = []
        async for doc in query.stream():
            runs.append(doc.to_dict())
        return runs

    async def update_task(self, run_id: str, task: Task, pending_approval: Optional[ApprovalRequest] = None) -> None:
        db = await self._get_db()
        doc_ref = db.collection("workflow_runs").document(run_id)
        
        @firestore.async_transactional
        async def update_in_transaction(transaction, ref):
            snapshot = await ref.get(transaction=transaction)
            if not snapshot.exists:
                return
                
            data = snapshot.to_dict()
            tasks = data.get("tasks", [])
            
            for i, t in enumerate(tasks):
                if t.get("task_id") == task.task_id:
                    # Update task in array
                    tasks[i] = task.model_dump(mode="json")
                    break
                    
            transaction.update(ref, {"tasks": tasks})
            
            if pending_approval:
                app_ref = db.collection("approvals").document(pending_approval.approval_id)
                transaction.set(app_ref, pending_approval.model_dump(mode="json"))

        transaction = db.transaction()
        await update_in_transaction(transaction, doc_ref)

    async def claim_task(self, run_id: str, task_id: str, lease_seconds: int = 60) -> bool:
        """Atomic claim of a task using Firestore transaction."""
        db = await self._get_db()
        doc_ref = db.collection("workflow_runs").document(run_id)
        
        @firestore.async_transactional
        async def claim_in_transaction(transaction, ref):
            snapshot = await ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
                
            data = snapshot.to_dict()
            tasks = data.get("tasks", [])
            
            for i, t in enumerate(tasks):
                if t.get("task_id") == task_id:
                    status = t.get("status")
                    if status not in ["PENDING", "RETRYING"]:
                        return False
                        
                    t["status"] = "RUNNING"
                    now = datetime.now(timezone.utc)
                    t["lease_started_at"] = now.isoformat()
                    # Cannot strictly compute expires_at easily here, but we can set attempt
                    t["attempt"] = t.get("attempt", 0) + 1
                    
                    tasks[i] = t
                    transaction.update(ref, {"tasks": tasks})
                    return True
            return False

        transaction = db.transaction()
        return await claim_in_transaction(transaction, doc_ref)

    async def get_events(self, run_id: str, after_event_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = await self._get_db()
        # Simplistic approach: get all and filter in-memory for after_event_id, 
        # or use standard order_by.
        query = db.collection("events").where("run_id", "==", run_id).order_by("timestamp")
        
        events = []
        found_after = after_event_id is None
        
        async for doc in query.stream():
            data = doc.to_dict()
            if not found_after:
                if data.get("event_id") == after_event_id:
                    found_after = True
                continue
            events.append(data)
            
        return events

    async def save_event(self, event: Any) -> None:
        db = await self._get_db()
        if isinstance(event, dict):
            event_dict = event
        else:
            event_dict = event.model_dump(mode="json")
            
        event_id = event_dict.get("event_id")
        await db.collection("events").document(event_id).set(event_dict)

    async def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        db = await self._get_db()
        doc = await db.collection("approvals").document(approval_id).get()
        if doc.exists:
            return ApprovalRequest(**doc.to_dict())
        return None

    async def list_pending_approvals(self, user_id: str) -> List[ApprovalRequest]:
        db = await self._get_db()
        query = db.collection("approvals").where("user_id", "==", user_id).where("status", "==", "PENDING")
        approvals = []
        async for doc in query.stream():
            approvals.append(ApprovalRequest(**doc.to_dict()))
        return approvals

    async def resolve_approval(self, approval_id: str, status: str, user_id: str) -> bool:
        db = await self._get_db()
        doc_ref = db.collection("approvals").document(approval_id)
        
        @firestore.async_transactional
        async def resolve_in_transaction(transaction, ref):
            snapshot = await ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
                
            data = snapshot.to_dict()
            if data.get("status") != "PENDING":
                return False
                
            transaction.update(ref, {
                "status": status,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "resolved_by": user_id
            })
            return True

        transaction = db.transaction()
        return await resolve_in_transaction(transaction, doc_ref)
