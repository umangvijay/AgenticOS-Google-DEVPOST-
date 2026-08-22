from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone
from backend.models.schedule import Schedule, ScheduleStatus

class ScheduleRepository(ABC):
    @abstractmethod
    def create_schedule(self, schedule: Schedule) -> None:
        pass
        
    @abstractmethod
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        pass
        
    @abstractmethod
    def list_schedules(self, user_id: str) -> List[Schedule]:
        pass
        
    @abstractmethod
    def update_schedule(self, schedule: Schedule) -> None:
        pass
        
    @abstractmethod
    def delete_schedule(self, schedule_id: str) -> None:
        pass

class InMemoryScheduleRepository(ScheduleRepository):
    def __init__(self):
        self._store = {}
        
    def create_schedule(self, schedule: Schedule) -> None:
        self._store[schedule.schedule_id] = schedule
        
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return self._store.get(schedule_id)
        
    def list_schedules(self, user_id: str) -> List[Schedule]:
        return [s for s in self._store.values() if s.user_id == user_id]
        
    def update_schedule(self, schedule: Schedule) -> None:
        if schedule.schedule_id in self._store:
            schedule.updated_at = datetime.now(timezone.utc)
            self._store[schedule.schedule_id] = schedule
            
    def delete_schedule(self, schedule_id: str) -> None:
        self._store.pop(schedule_id, None)
