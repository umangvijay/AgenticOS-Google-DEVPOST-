from google.cloud import firestore
from backend.models.schemas import WorkflowRun, Task, TaskStatus, WorkflowEvent
from backend.repositories.workflow_repository import WorkflowRepository
from backend.models.security import ApprovalRequest
from typing import AsyncGenerator
import asyncio
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class FirestoreWorkflowRepository(WorkflowRepository):
    def __init__(self):
        # The application must use REAL Firestore. No mock fallback.
        try:
            self.db = firestore.Client(
                project=settings.GOOGLE_CLOUD_PROJECT,
                database=settings.FIRESTORE_DATABASE_ID
            )
            self.collection = self.db.collection(settings.FIRESTORE_COLLECTION_WORKFLOWS)
        except Exception as e:
            logger.error("Failed to connect to Firestore. Ensure ADC is configured or GOOGLE_APPLICATION_CREDENTIALS is set.")
            raise e

    def save_run(self, run: WorkflowRun) -> None:
        self.collection.document(run.run_id).set(run.model_dump(mode='json'))
        
    def get_run(self, run_id: str) -> WorkflowRun | None:
        doc = self.collection.document(run_id).get()
        if doc.exists:
            return WorkflowRun(**doc.to_dict())
        return None
        
    def claim_task(self, run_id: str, task_id: str, lease_seconds: int) -> bool:
        from datetime import datetime, timedelta, timezone
        
        transaction = self.db.transaction()
        doc_ref = self.collection.document(run_id)
        
        @firestore.transactional
        def _claim(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
                
            run_data = snapshot.to_dict()
            tasks = run_data.get("tasks", [])
            
            claimed = False
            for t in tasks:
                if t.get("task_id") == task_id:
                    status = t.get("status")
                    lease_expires_str = t.get("lease_expires_at")
                    
                    now = datetime.now(timezone.utc)
                    
                    can_claim = False
                    if status in [TaskStatus.PENDING, TaskStatus.RETRYING]:
                        can_claim = True
                    elif status == TaskStatus.RUNNING and lease_expires_str:
                        # Check if stale
                        try:
                            # Firestore stores datetimes as google.api.core.datetime_helpers.DatetimeWithNanoseconds
                            # or ISO strings if we dumped it as JSON. We used `model_dump(mode='json')`, so it's a string.
                            if isinstance(lease_expires_str, str):
                                # Ensure it handles Z
                                lease_expires = datetime.fromisoformat(lease_expires_str.replace("Z", "+00:00"))
                            else:
                                lease_expires = lease_expires_str
                            
                            if lease_expires < now:
                                can_claim = True
                        except Exception as e:
                            logger.error(f"Error parsing lease_expires_at: {e}")
                            
                    if can_claim:
                        t["status"] = TaskStatus.RUNNING
                        t["lease_started_at"] = now.isoformat()
                        t["lease_expires_at"] = (now + timedelta(seconds=lease_seconds)).isoformat()
                        t["attempt"] = t.get("attempt", 0) + 1
                        claimed = True
                    break
                    
            if claimed:
                transaction.update(doc_ref, {"tasks": tasks})
                return True
            return False
            
        return _claim(transaction, doc_ref)
        
    def update_task(self, run_id: str, task: Task) -> None:
        transaction = self.db.transaction()
        doc_ref = self.collection.document(run_id)
        
        @firestore.transactional
        def _update(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return
                
            run_data = snapshot.to_dict()
            tasks = run_data.get("tasks", [])
            
            updated = False
            for i, t in enumerate(tasks):
                if t.get("task_id") == task.task_id:
                    tasks[i] = task.model_dump(mode='json')
                    updated = True
                    break
                    
            if updated:
                transaction.update(doc_ref, {"tasks": tasks})
                
        _update(transaction, doc_ref)
        
    def save_event(self, event: WorkflowEvent) -> None:
        # Save to events subcollection under the run document
        events_ref = self.collection.document(event.run_id).collection("events")
        events_ref.document(event.event_id).set(event.model_dump(mode='json'))
        
    async def stream_events(self, run_id: str) -> AsyncGenerator[WorkflowEvent, None]:
        events_ref = self.collection.document(run_id).collection("events")
        
        # We need a queue to bridge the Firestore callback with the async generator
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        
        def on_snapshot(col_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'ADDED':
                    doc = change.document
                    event = WorkflowEvent(**doc.to_dict())
                    loop.call_soon_threadsafe(queue.put_nowait, event)
                    
        # Watch the query, maybe ordered by timestamp, though on_snapshot returns all initially
        query = events_ref.order_by("timestamp")
        watch = query.on_snapshot(on_snapshot)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            watch.unsubscribe()

    def create_if_absent(self, run: WorkflowRun) -> bool:
        transaction = self.db.transaction()
        doc_ref = self.collection.document(run.run_id)
        
        @firestore.transactional
        def _create(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                return False
            transaction.set(doc_ref, run.model_dump(mode='json'))
            return True
            
        return _create(transaction, doc_ref)

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        doc = self.db.collection("approvals").document(approval_id).get()
        if doc.exists:
            return ApprovalRequest(**doc.to_dict())
        return None

    def list_pending_approvals(self, user_id: str) -> list[ApprovalRequest]:
        from backend.models.security import ApprovalStatus
        docs = self.db.collection("approvals").where(filter=firestore.FieldFilter("user_id", "==", user_id)).where(filter=firestore.FieldFilter("status", "==", ApprovalStatus.PENDING)).stream()
        return [ApprovalRequest(**doc.to_dict()) for doc in docs]

    def resolve_approval(self, approval_id: str, new_status: str, decision_by: str) -> bool:
        from backend.models.security import ApprovalStatus
        from datetime import datetime, timezone
        transaction = self.db.transaction()
        doc_ref = self.db.collection("approvals").document(approval_id)
        
        @firestore.transactional
        def _resolve(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
            data = snapshot.to_dict()
            if data.get("status") != ApprovalStatus.PENDING:
                return False
            transaction.update(doc_ref, {
                "status": new_status,
                "decision_by": decision_by,
                "decision_at": datetime.now(timezone.utc).isoformat()
            })
            return True
        return _resolve(transaction, doc_ref)
