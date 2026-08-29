from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from backend.repositories.base import BaseWorkflowRepository
from backend.repositories.firestore.database import FirestoreDB
from backend.models.schemas import Task
from backend.models.security import ApprovalRequest


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


class FirestoreWorkflowRepository(BaseWorkflowRepository):
    """Firestore implementation of BaseWorkflowRepository."""

    async def _get_db(self):
        return await FirestoreDB.get_client()

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        doc = await db.collection("workflow_runs").document(run_id).get()
        if not doc.exists:
            return None
        return doc.to_dict() or {}

    async def save_run(self, run: Dict[str, Any]) -> None:
        db = await self._get_db()
        payload = _as_dict(run)
        run_id = payload.get("run_id")
        if not run_id:
            raise ValueError("Run dict must have 'run_id'")
        payload.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        await db.collection("workflow_runs").document(run_id).set(payload)

    async def list_runs(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        db = await self._get_db()
        query = (
            db.collection("workflow_runs")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(max(1, limit + max(0, offset)))
        )
        runs = []
        skipped = 0
        async for doc in query.stream():
            if skipped < offset:
                skipped += 1
                continue
            if len(runs) >= limit:
                break
            runs.append(doc.to_dict() or {})
        return runs

    async def update_run_status(self, run_id: str, status: str) -> None:
        db = await self._get_db()
        await db.collection("workflow_runs").document(run_id).update(
            {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def save_task(self, task_data: Dict[str, Any]) -> None:
        payload = _as_dict(task_data)
        run_id = payload.get("run_id")
        task_id = payload.get("task_id")
        if not run_id or not task_id:
            raise ValueError("Task dict must have 'run_id' and 'task_id'")
        await self.update_task(run_id, task_id, payload)

    async def get_task(self, run_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        run = await self.get_run(run_id)
        if not run:
            return None
        for task in run.get("tasks") or []:
            if isinstance(task, dict) and task.get("task_id") == task_id:
                return task
        return None

    async def update_task(self, run_id: str, task_id, updates=None, pending_approval=None) -> None:
        """ABC: (run_id, task_id, updates). Also accepts a Task as the second argument."""
        if isinstance(task_id, Task):
            task = task_id
            if isinstance(updates, ApprovalRequest):
                pending_approval = updates
            updates = task.model_dump(mode="json")
            task_id = task.task_id
        elif hasattr(task_id, "model_dump") and not isinstance(task_id, str):
            dumped = task_id.model_dump(mode="json")
            updates = dumped
            task_id = dumped.get("task_id")

        if not updates:
            return

        db = await self._get_db()
        doc_ref = db.collection("workflow_runs").document(run_id)

        @firestore.async_transactional
        async def update_in_transaction(transaction, ref):
            snapshot = await ref.get(transaction=transaction)
            if not snapshot.exists:
                return

            data = snapshot.to_dict() or {}
            tasks = list(data.get("tasks") or [])
            found = False
            for i, t in enumerate(tasks):
                if isinstance(t, dict) and t.get("task_id") == task_id:
                    merged = dict(t)
                    merged.update(_as_dict(updates))
                    merged["task_id"] = task_id
                    tasks[i] = merged
                    found = True
                    break
            if not found:
                payload = _as_dict(updates)
                payload["task_id"] = task_id
                payload.setdefault("run_id", run_id)
                tasks.append(payload)

            transaction.update(
                ref,
                {
                    "tasks": tasks,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            if pending_approval:
                approval = _as_dict(pending_approval)
                app_id = approval.get("approval_id")
                if app_id:
                    app_ref = db.collection("approvals").document(app_id)
                    transaction.set(app_ref, approval)

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

            data = snapshot.to_dict() or {}
            tasks = list(data.get("tasks") or [])

            for i, t in enumerate(tasks):
                if t.get("task_id") == task_id:
                    status = t.get("status")
                    if status not in ["PENDING", "RETRYING"]:
                        return False

                    now = datetime.now(timezone.utc)
                    t["status"] = "RUNNING"
                    t["lease_started_at"] = now.isoformat()
                    t["lease_expires_at"] = (now + timedelta(seconds=lease_seconds)).isoformat()
                    t["attempt"] = t.get("attempt", 0) + 1
                    tasks[i] = t
                    transaction.update(ref, {"tasks": tasks})
                    return True
            return False

        transaction = db.transaction()
        return await claim_in_transaction(transaction, doc_ref)

    async def create_if_absent(self, run_data: Dict[str, Any]) -> bool:
        payload = _as_dict(run_data)
        run_id = payload.get("run_id")
        if not run_id:
            raise ValueError("Run dict must have 'run_id'")
        db = await self._get_db()
        doc_ref = db.collection("workflow_runs").document(run_id)

        @firestore.async_transactional
        async def create_in_transaction(transaction, ref):
            snapshot = await ref.get(transaction=transaction)
            if snapshot.exists:
                return False
            now = datetime.now(timezone.utc).isoformat()
            payload.setdefault("created_at", now)
            payload.setdefault("updated_at", now)
            transaction.set(ref, payload)
            return True

        transaction = db.transaction()
        return await create_in_transaction(transaction, doc_ref)

    async def save_approval(self, approval_data: Dict[str, Any]) -> None:
        payload = _as_dict(approval_data)
        approval_id = payload.get("approval_id")
        if not approval_id:
            raise ValueError("Approval dict must have 'approval_id'")
        db = await self._get_db()
        await db.collection("approvals").document(approval_id).set(payload)

    async def get_events(self, run_id: str, after_event_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = await self._get_db()
        query = db.collection("events").where("run_id", "==", run_id).order_by("timestamp")

        events = []
        found_after = after_event_id is None

        async for doc in query.stream():
            data = doc.to_dict() or {}
            if not found_after:
                if data.get("event_id") == after_event_id:
                    found_after = True
                continue
            events.append(data)

        return events

    async def save_event(self, event: Any) -> None:
        db = await self._get_db()
        event_dict = _as_dict(event)
        event_id = event_dict.get("event_id")
        await db.collection("events").document(event_id).set(event_dict)

    async def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        doc = await db.collection("approvals").document(approval_id).get()
        if doc.exists:
            return doc.to_dict() or {}
        return None

    async def list_pending_approvals(self, user_id: str) -> List[Dict[str, Any]]:
        db = await self._get_db()
        query = db.collection("approvals").where("user_id", "==", user_id).where("status", "==", "PENDING")
        approvals = []
        async for doc in query.stream():
            approvals.append(doc.to_dict() or {})
        return approvals

    async def resolve_approval(self, approval_id: str, new_status: str, decision_by: str) -> bool:
        db = await self._get_db()
        doc_ref = db.collection("approvals").document(approval_id)

        @firestore.async_transactional
        async def resolve_in_transaction(transaction, ref):
            snapshot = await ref.get(transaction=transaction)
            if not snapshot.exists:
                return False

            data = snapshot.to_dict() or {}
            if data.get("status") != "PENDING":
                return False

            transaction.update(
                ref,
                {
                    "status": new_status,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "resolved_by": decision_by,
                },
            )
            return True

        transaction = db.transaction()
        return await resolve_in_transaction(transaction, doc_ref)
