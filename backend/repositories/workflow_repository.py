from abc import ABC, abstractmethod
from typing import Optional, List
from backend.models.schemas import WorkflowRun, Task, TaskStatus, WorkflowEvent
from backend.models.security import ApprovalRequest
from typing import AsyncGenerator

class WorkflowRepository(ABC):
    @abstractmethod
    def save_run(self, run: WorkflowRun) -> None:
        pass
        
    @abstractmethod
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        pass
        
    @abstractmethod
    def claim_task(self, run_id: str, task_id: str, lease_seconds: int) -> bool:
        pass
        
    @abstractmethod
    def update_task(self, run_id: str, task: Task, pending_approval: Optional[ApprovalRequest] = None) -> None:
        pass
        
    @abstractmethod
    def create_if_absent(self, run: WorkflowRun) -> bool:
        pass
        
    @abstractmethod
    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        pass
        
    @abstractmethod
    def list_pending_approvals(self, user_id: str) -> List[ApprovalRequest]:
        pass
        
    @abstractmethod
    def resolve_approval(self, approval_id: str, new_status: str, decision_by: str) -> bool:
        """Atomically transition a PENDING approval to APPROVED or REJECTED. Returns True if successful."""
        pass
        
    @abstractmethod
    def save_event(self, event: WorkflowEvent) -> None:
        pass
        
    @abstractmethod
    async def stream_events(self, run_id: str) -> AsyncGenerator[WorkflowEvent, None]:
        pass
        
class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self):
        self._store = {}
        self._approvals_store = {}
        self._events_store = {}
        self._event_queues = {}
        
    def save_run(self, run: WorkflowRun) -> None:
        self._store[run.run_id] = run
        
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self._store.get(run_id)
        
    def claim_task(self, run_id: str, task_id: str, lease_seconds: int) -> bool:
        from datetime import datetime, timedelta, timezone
        run = self.get_run(run_id)
        if not run: return False
        
        for t in run.tasks:
            if t.task_id == task_id:
                now = datetime.now(timezone.utc)
                if t.status == TaskStatus.PENDING or (t.status == TaskStatus.RUNNING and t.lease_expires_at and t.lease_expires_at < now) or t.status == TaskStatus.RETRYING:
                    t.status = TaskStatus.RUNNING
                    t.lease_started_at = now
                    t.lease_expires_at = now + timedelta(seconds=lease_seconds)
                    t.attempt += 1
                    return True
        return False
        
    def update_task(self, run_id: str, task: Task, pending_approval: Optional[ApprovalRequest] = None) -> None:
        run = self.get_run(run_id)
        if not run: return
        for i, t in enumerate(run.tasks):
            if t.task_id == task.task_id:
                run.tasks[i] = task
                break
                
        if pending_approval:
            self._approvals_store[pending_approval.approval_id] = pending_approval
                
    def create_if_absent(self, run: WorkflowRun) -> bool:
        if run.run_id in self._store:
            return False
        self._store[run.run_id] = run
        return True
        
    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._approvals_store.get(approval_id)
        
    def list_pending_approvals(self, user_id: str) -> List[ApprovalRequest]:
        from backend.models.security import ApprovalStatus
        return [
            a for a in self._approvals_store.values()
            if a.user_id == user_id and a.status == ApprovalStatus.PENDING
        ]
        
    def resolve_approval(self, approval_id: str, new_status: str, decision_by: str) -> bool:
        from backend.models.security import ApprovalStatus
        from datetime import datetime, timezone
        
        approval = self._approvals_store.get(approval_id)
        if not approval:
            return False
            
        # Atomic compare-and-set logic (in-memory implementation)
        if approval.status != ApprovalStatus.PENDING:
            return False
            
        approval.status = new_status
        approval.decision_by = decision_by
        approval.decision_at = datetime.now(timezone.utc)
        return True
        
    def save_event(self, event: WorkflowEvent) -> None:
        if event.run_id not in self._events_store:
            self._events_store[event.run_id] = []
        self._events_store[event.run_id].append(event)
        
        # Publish to any active streams
        if event.run_id in self._event_queues:
            import asyncio
            for q in self._event_queues[event.run_id]:
                asyncio.run_coroutine_threadsafe(q.put(event), asyncio.get_event_loop())
                
    async def stream_events(self, run_id: str) -> AsyncGenerator[WorkflowEvent, None]:
        import asyncio
        if run_id not in self._event_queues:
            self._event_queues[run_id] = []
            
        queue = asyncio.Queue()
        self._event_queues[run_id].append(queue)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._event_queues[run_id].remove(queue)
            if not self._event_queues[run_id]:
                del self._event_queues[run_id]
