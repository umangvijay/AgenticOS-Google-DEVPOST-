import pytest
from backend.models.schemas import WorkflowDefinition, TaskDefinition
from backend.engine.dag_validator import validate_dag, DAGValidationError

def test_valid_dag():
    wf = WorkflowDefinition(tasks=[
        TaskDefinition(task_id="A", agent="IntentAgent", dependencies=[]),
        TaskDefinition(task_id="B", agent="PlannerAgent", dependencies=["A"]),
        TaskDefinition(task_id="C", agent="OrchestratorAgent", dependencies=["B"])
    ])
    # Should not raise
    validate_dag(wf)

def test_cycle_rejected():
    wf = WorkflowDefinition(tasks=[
        TaskDefinition(task_id="A", agent="IntentAgent", dependencies=["C"]),
        TaskDefinition(task_id="B", agent="IntentAgent", dependencies=["A"]),
        TaskDefinition(task_id="C", agent="IntentAgent", dependencies=["B"])
    ])
    with pytest.raises(DAGValidationError, match="Cycle detected"):
        validate_dag(wf)

def test_duplicate_task_ids_rejected():
    wf = WorkflowDefinition(tasks=[
        TaskDefinition(task_id="A", agent="IntentAgent", dependencies=[]),
        TaskDefinition(task_id="A", agent="IntentAgent", dependencies=[])
    ])
    with pytest.raises(DAGValidationError, match="Duplicate task ID"):
        validate_dag(wf)

def test_unknown_dependency_rejected():
    wf = WorkflowDefinition(tasks=[
        TaskDefinition(task_id="A", agent="IntentAgent", dependencies=["UNKNOWN"])
    ])
    with pytest.raises(DAGValidationError, match="Unknown dependency"):
        validate_dag(wf)

def test_self_dependency_rejected():
    wf = WorkflowDefinition(tasks=[
        TaskDefinition(task_id="A", agent="IntentAgent", dependencies=["A"])
    ])
    with pytest.raises(DAGValidationError, match="Self-dependency detected"):
        validate_dag(wf)

def test_unknown_agent_rejected():
    wf = WorkflowDefinition(tasks=[
        TaskDefinition(task_id="A", agent="HackerAgent", dependencies=[])
    ])
    with pytest.raises(DAGValidationError, match="Unknown agent"):
        validate_dag(wf)

def test_invalid_timeout_rejected():
    wf = WorkflowDefinition(tasks=[
        TaskDefinition(task_id="A", agent="IntentAgent", dependencies=[], timeout_seconds=-5)
    ])
    with pytest.raises(DAGValidationError, match="Invalid timeout"):
        validate_dag(wf)
