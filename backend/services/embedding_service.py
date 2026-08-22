from abc import ABC, abstractmethod
from typing import List
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

class MockEmbeddingService(EmbeddingService):
    def embed_text(self, text: str) -> List[float]:
        # Return a mock 768-dimensional embedding
        return [0.1] * 768

class GoogleCloudEmbeddingService(EmbeddingService):
    def __init__(self):
        from google import genai
        
        # Initialize client according to ADK settings structure
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = genai.Client(
                vertexai=True, 
                project=settings.GOOGLE_CLOUD_PROJECT, 
                location=settings.GOOGLE_CLOUD_REGION
            )
            
    def embed_text(self, text: str) -> List[float]:
        try:
            response = self.client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text
            )
            # Depending on genai SDK version, the structure varies.
            # Usually response.embeddings[0].values
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
