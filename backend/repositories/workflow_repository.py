from abc import ABC, abstractmethod
from typing import Optional
from backend.models.schemas import WorkflowRun

class WorkflowRepository(ABC):
    @abstractmethod
    def save_run(self, run: WorkflowRun) -> None:
        pass
        
    @abstractmethod
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        pass

class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self):
        self._store = {}
        
    def save_run(self, run: WorkflowRun) -> None:
        self._store[run.run_id] = run
        
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self._store.get(run_id)
