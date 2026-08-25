import logging
import os
from typing import Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)

class FirestoreDB:
    _instance: Optional[firestore.AsyncClient] = None

    @classmethod
    async def get_client(cls) -> firestore.AsyncClient:
        """Get or create the singleton AsyncClient."""
        if cls._instance is None:
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            if not project:
                logger.warning("GOOGLE_CLOUD_PROJECT not set, using default credentials.")
            
            # Note: We must use AsyncClient to maintain compatibility with FastAPI async routes
            cls._instance = firestore.AsyncClient(project=project)
            logger.info("Firestore AsyncClient initialized.")
        return cls._instance

    @classmethod
    async def close(cls):
        """Close the client."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            logger.info("Firestore AsyncClient closed.")
