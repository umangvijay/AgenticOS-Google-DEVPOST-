from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_NAME: str = "AgentOS"
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"
    
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_CLOUD_REGION: str = "us-central1"
    FIRESTORE_DATABASE_ID: str = "(default)"
    
    FIRESTORE_COLLECTION_USERS: str = "users"
    FIRESTORE_COLLECTION_WORKFLOWS: str = "workflows"
    FIRESTORE_COLLECTION_RUNS: str = "runs"
    FIRESTORE_COLLECTION_TASKS: str = "tasks"
    
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_API_KEY: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
