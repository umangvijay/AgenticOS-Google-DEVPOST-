import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.models.schemas import WorkflowRun, TaskStatus
from backend.models.evaluation import AgentEvaluationRecord
from backend.config.settings import settings
import logging

logger = logging.getLogger("evaluation_service")

class EvaluationService:
    def __init__(self, db_client=None):
        self.db = db_client # Firestore client injected here in prod
        self.evaluations: List[AgentEvaluationRecord] = [] # In-memory fallback
        
    def evaluate_run(self, run: WorkflowRun) -> AgentEvaluationRecord:
        """
        Evaluates a completed or failed workflow run and generates an evaluation record.
        """
        
        # Calculate overall success
        success = run.status == TaskStatus.COMPLETED
        
        # Aggregate metrics across tasks
        total_recovery_attempts = 0
        total_successful_recoveries = 0
        total_tool_calls = 0
        total_unknown_tools = 0
        total_schema_violations = 0
        
        latency_ms = 0.0
        
        for task in run.tasks:
            total_recovery_attempts += task.recovery_attempts
            # If the task recovered and ultimately succeeded or went back to pending
            if task.recovery_attempts > 0 and task.status == TaskStatus.COMPLETED:
                total_successful_recoveries += 1
                
            # These would ideally be fetched from the audit logs or traces
            # For demonstration, we'll infer them from error history if present
            for history in getattr(task, 'recovery_history', []):
                # Pseudo-logic to determine why it failed
                if "unknown tool" in str(history).lower():
                    total_unknown_tools += 1
                if "schema" in str(history).lower() or "validation" in str(history).lower():
                    total_schema_violations += 1
                    
            if task.started_at and task.completed_at:
                latency_ms += (task.completed_at - task.started_at).total_seconds() * 1000
                
        # Calculate rates
        unknown_rate = total_unknown_tools / max(total_recovery_attempts, 1)
        schema_violation_rate = total_schema_violations / max(total_recovery_attempts, 1)
        
        record = AgentEvaluationRecord(
            evaluation_id=str(uuid.uuid4()),
            run_id=run.run_id,
            workflow_id=run.workflow_id,
            agent_name="orchestrator", # Default, could be extracted per task
            model=settings.GEMINI_MODEL,
            task_type="workflow",
            success=success,
            recovery_attempts=total_recovery_attempts,
            successful_recoveries=total_successful_recoveries,
            tool_calls=total_tool_calls,
            unknown_tool_call_rate=unknown_rate,
            invalid_argument_rate=schema_violation_rate,
            tool_schema_violation_rate=schema_violation_rate,
            latency_ms=latency_ms,
            token_usage_input=0, # These would be extracted from OTel metrics
            token_usage_output=0,
            token_usage_total=0,
            evaluator_version="1.0.0",
            prompt_version="1.0.0"
        )
        
        self.save_evaluation(record)
        return record
        
    def save_evaluation(self, record: AgentEvaluationRecord):
        # Save to Firestore in production
        if self.db:
            try:
                self.db.collection("agent_evaluations").document(record.evaluation_id).set(record.model_dump(mode='json'))
            except Exception as e:
                logger.error(f"Failed to save evaluation to Firestore: {e}")
                
        self.evaluations.append(record)
        logger.info(f"Generated AgentEvaluationRecord for run {record.run_id}")
