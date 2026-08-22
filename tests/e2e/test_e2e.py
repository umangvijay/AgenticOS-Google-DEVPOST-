import pytest
import os
from fastapi.testclient import TestClient
from backend.api.main import app
import backend.api.main as main_module
from backend.repositories.firestore_workflow_repository import FirestoreWorkflowRepository

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_real_firestore():
    # Only run if we are explicitly running e2e tests
    if not os.getenv("RUN_E2E_TESTS"):
        pytest.skip("Set RUN_E2E_TESTS=1 to run real Firestore integration test.")
        
    try:
        main_module.workflow_repo = FirestoreWorkflowRepository()
    except Exception:
        pytest.fail("Could not initialize real Firestore repository.")
        
    yield
    # We would normally clean up, but for the Phase 1 verification, observing the data is fine.

def test_real_firestore_e2e_flow():
    response = client.post("/api/v1/intent", json={"goal": "What time is it in UTC?"})
    assert response.status_code == 200
    data = response.json()
    
    run_id = data["run_id"]
    timeline_response = client.get(f"/api/v1/workflows/{run_id}")
    assert timeline_response.status_code == 200
