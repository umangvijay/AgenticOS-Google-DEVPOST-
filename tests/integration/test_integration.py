import pytest
import os
from fastapi.testclient import TestClient
from backend.api.main import app
import backend.api.main as main_module
from backend.models.schemas import TaskStatus
from backend.repositories.workflow_repository import InMemoryWorkflowRepository

client = TestClient(app)

@pytest.fixture(autouse=True)
def inject_in_memory_repo():
    main_module.workflow_repo = InMemoryWorkflowRepository()
    yield
    main_module.workflow_repo = None

# This integration test uses the real ADK agents but intercepts Firestore.
# Requires GEMINI_API_KEY or ADC for vertex to succeed.
@pytest.mark.asyncio
def test_workflow_integration_with_real_llm():
    # Only run if a key or environment variable implies we can authenticate
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip("Skipping real LLM integration test because credentials are not explicitly set.")
        
    response = client.post("/api/v1/intent", json={"goal": "What time is it in UTC?"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == TaskStatus.COMPLETED
    run_id = data["run_id"]
    
    timeline_response = client.get(f"/api/v1/workflows/{run_id}")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    
    assert len(timeline["tasks"]) == 3
