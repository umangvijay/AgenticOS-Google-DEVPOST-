import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
import backend.api.main as main_module
from backend.models.schemas import TaskStatus, WorkflowRun
from backend.repositories.workflow_repository import InMemoryWorkflowRepository
from unittest.mock import patch, MagicMock

client = TestClient(app)

@pytest.fixture(autouse=True)
def inject_in_memory_repo():
    main_module.workflow_repo = InMemoryWorkflowRepository()
    yield
    main_module.workflow_repo = None

@patch('backend.api.main.InMemoryRunner')
def test_process_goal_success(mock_runner_class):
    # Setup mock events for Intent, Plan, Orchestrator
    mock_runner = MagicMock()
    
    # We just need it to not crash and return some output
    class MockEvent:
        def __init__(self, output):
            self.output = output
            
    class MockOutput:
        def __init__(self, data):
            self.data = data
        def model_dump(self):
            return self.data
            
    async def mock_run_debug(*args, **kwargs):
        return [MockEvent(MockOutput({"mocked": "data"}))]
        
    mock_runner.run_debug = mock_run_debug
    mock_runner_class.return_value = mock_runner
    
    response = client.post("/api/v1/intent", json={"goal": "Test goal"})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] == TaskStatus.COMPLETED
    
    # Test GET
    run_id = data["run_id"]
    get_response = client.get(f"/api/v1/workflows/{run_id}")
    assert get_response.status_code == 200
    assert len(get_response.json()["tasks"]) == 3
