from google.cloud import firestore
from backend.models.schemas import WorkflowRun
from backend.repositories.workflow_repository import WorkflowRepository
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
