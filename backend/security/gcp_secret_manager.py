import logging
import os
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class GCPSecretManager:
    """Wrapper for Google Cloud Secret Manager."""

    def __init__(self):
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.client = None
        if self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
                logger.info(f"GCPSecretManager initialized for project {self.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize SecretManager: {e}")
        else:
            logger.warning("GOOGLE_CLOUD_PROJECT not set, GCPSecretManager disabled.")

    def _get_secret_path(self, secret_id: str) -> str:
        return f"projects/{self.project_id}/secrets/{secret_id}"

    def get_secret(self, secret_id: str) -> str:
        if not self.client:
            raise RuntimeError("GCPSecretManager is not initialized.")
            
        name = f"{self._get_secret_path(secret_id)}/versions/latest"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    def set_secret(self, secret_id: str, payload: str) -> None:
        if not self.client:
            raise RuntimeError("GCPSecretManager is not initialized.")
            
        parent = f"projects/{self.project_id}"
        
        # Check if secret exists
        try:
            self.client.get_secret(request={"name": self._get_secret_path(secret_id)})
        except Exception:
            # Create the secret if it doesn't exist
            self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

        # Add a new version
        self.client.add_secret_version(
            request={
                "parent": self._get_secret_path(secret_id),
                "payload": {"data": payload.encode("UTF-8")},
            }
        )

    def delete_secret(self, secret_id: str) -> None:
        if not self.client:
            raise RuntimeError("GCPSecretManager is not initialized.")
            
        try:
            self.client.delete_secret(request={"name": self._get_secret_path(secret_id)})
        except Exception as e:
            logger.warning(f"Failed to delete secret {secret_id}: {e}")
