from abc import ABC, abstractmethod
from typing import Optional
from backend.models.schemas import WorkflowRun, Task, TaskStatus

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
    def update_task(self, run_id: str, task: Task) -> None:
        pass
        
class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self):
        self._store = {}
        
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
        
    def update_task(self, run_id: str, task: Task) -> None:
        run = self.get_run(run_id)
        if not run: return
        for i, t in enumerate(run.tasks):
            if t.task_id == task.task_id:
                run.tasks[i] = task
                break
