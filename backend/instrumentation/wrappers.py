from typing import Dict, Any, List
import json
from backend.mcp.tool_router import ToolRouter, ToolRouterError
from backend.instrumentation.telemetry import get_tracer, get_meter, TelemetrySanitizer
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode

tracer = get_tracer()
meter = get_meter()

tool_call_counter = meter.create_counter(
    "tool.call.count",
    description="Number of tool calls executed"
)
tool_failure_counter = meter.create_counter(
    "tool.failure.count",
    description="Number of failed tool calls"
)

class InstrumentedToolRouter:
    """Wraps the ToolRouter to add OpenTelemetry spans and metrics without polluting the core logic."""
    def __init__(self, inner: ToolRouter):
        self._inner = inner

    async def get_tool_catalog(self) -> List[Dict[str, Any]]:
        return await self._inner.get_tool_catalog()

    async def execute_tool(self, agent_tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        # Create a span for the tool execution
        with tracer.start_as_current_span(
            name=f"tool.call:{agent_tool_name}",
            kind=trace.SpanKind.INTERNAL
        ) as span:
            
            # Record sanitized attributes
            span.set_attribute("tool.name", agent_tool_name)
            if context:
                span.set_attribute("workflow.id", context.get("workflow_id", ""))
                span.set_attribute("run.id", context.get("run_id", ""))
                span.set_attribute("task.id", context.get("task_id", ""))
                span.set_attribute("user.id", context.get("user_id", ""))
            
            sanitized_args = TelemetrySanitizer.sanitize(arguments)
            span.set_attribute("tool.arguments", json.dumps(sanitized_args))
            
            # Increment metric
            tool_call_counter.add(1, {"tool.name": agent_tool_name})
            
            try:
                result = await self._inner.execute_tool(agent_tool_name, arguments, context)
                
                # Sanitize and record result if it's small enough
                sanitized_result = TelemetrySanitizer.sanitize(result)
                if isinstance(sanitized_result, (str, dict, list)):
                    span.set_attribute("tool.result", json.dumps(sanitized_result)[:1000])
                    
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                # Increment failure metric
                tool_failure_counter.add(1, {
                    "tool.name": agent_tool_name,
                    "error.type": type(e).__name__
                })
                raise

workflow_success_counter = meter.create_counter(
    "workflow.success.count",
    description="Number of completed workflows"
)
workflow_failure_counter = meter.create_counter(
    "workflow.failure.count",
    description="Number of failed workflows"
)
task_duration_histogram = meter.create_histogram(
    "task.duration",
    description="Task execution duration in seconds",
    unit="s"
)

class InstrumentedWorkflowEngine:
    def __init__(self, inner):
        self._inner = inner

    async def evaluate_dag(self, run_id: str) -> None:
        with tracer.start_as_current_span(
            name="workflow.run",
            kind=trace.SpanKind.INTERNAL
        ) as span:
            span.set_attribute("run.id", run_id)
            
            try:
                await self._inner.evaluate_dag(run_id)
                
                # Check the run status to see if it completed or failed in this eval
                run = self._inner.repo.get_run(run_id)
                if run:
                    from backend.models.schemas import TaskStatus
                    if run.status == TaskStatus.COMPLETED:
                        workflow_success_counter.add(1)
                    elif run.status == TaskStatus.FAILED:
                        workflow_failure_counter.add(1)
                        
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def execute_task(self, run_id: str, task_id: str) -> None:
        import time
        start_time = time.time()
        
        with tracer.start_as_current_span(
            name="task.execute",
            kind=trace.SpanKind.INTERNAL
        ) as span:
            span.set_attribute("run.id", run_id)
            span.set_attribute("task.id", task_id)
            
            try:
                await self._inner.execute_task(run_id, task_id)
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                duration = time.time() - start_time
                task_duration_histogram.record(duration, {"task.id": task_id})

