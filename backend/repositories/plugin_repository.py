from abc import ABC, abstractmethod
from typing import List, Optional
from backend.models.plugin import PluginRecord
from datetime import datetime, timezone

class PluginRepository(ABC):
    @abstractmethod
    def save(self, record: PluginRecord) -> None:
        pass
        
    @abstractmethod
    def get_by_id(self, record_id: str) -> Optional[PluginRecord]:
        pass
        
    @abstractmethod
    def list_all(self, user_id: str = None) -> List[PluginRecord]:
        pass

class InMemoryPluginRepository(PluginRepository):
    def __init__(self):
        self._store = {}
        
    def save(self, record: PluginRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        self._store[record.id] = record
        
    def get_by_id(self, record_id: str) -> Optional[PluginRecord]:
        return self._store.get(record_id)
        
    def list_all(self, user_id: str = None) -> List[PluginRecord]:
        # For simplicity, if user_id is provided, we filter by it or global
        # Scope enforcement is largely handled by policy, but we can do basic filtering here
        results = []
        for r in self._store.values():
            if user_id and r.manifest.scope.value == "USER" and r.installed_by != user_id:
                continue
            results.append(r)
        return results

class FirestorePluginRepository(PluginRepository):
    def __init__(self, db_client):
        self.db = db_client
        self.collection_name = "plugins"
        
    def save(self, record: PluginRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        doc_ref = self.db.collection(self.collection_name).document(record.id)
        # We store the raw dict
        doc_ref.set(record.model_dump(mode="json"))
        
    def get_by_id(self, record_id: str) -> Optional[PluginRecord]:
        doc = self.db.collection(self.collection_name).document(record_id).get()
        if not doc.exists:
            return None
        return PluginRecord.model_validate(doc.to_dict())
        
    def list_all(self, user_id: str = None) -> List[PluginRecord]:
        collection = self.db.collection(self.collection_name)
        docs = collection.stream()
        results = []
        for doc in docs:
            r = PluginRecord.model_validate(doc.to_dict())
            if user_id and r.manifest.scope.value == "USER" and r.installed_by != user_id:
                continue
            results.append(r)
        return results
