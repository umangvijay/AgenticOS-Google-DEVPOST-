import inspect
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.models.schemas import Task, WorkflowRun, WorkflowEvent


async def maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


def _parse_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def dict_to_task(data: Dict[str, Any], run: Optional[Dict[str, Any]] = None) -> Task:
    payload = dict(data)
    for key in ("started_at", "completed_at", "lease_started_at", "lease_expires_at"):
        if key in payload:
            payload[key] = _parse_dt(payload.get(key))
    payload.setdefault("workflow_id", (run or {}).get("workflow_id", "default_workflow"))
    payload.setdefault("run_id", (run or {}).get("run_id", payload.get("run_id", "")))
    payload.setdefault("user_id", (run or {}).get("user_id", "default_user"))
    payload.setdefault("agent", payload.get("agent") or "OrchestratorAgent")
    payload.setdefault("input_data", payload.get("input_data") or {})
    if isinstance(payload["input_data"], str):
        import json
        payload["input_data"] = json.loads(payload["input_data"] or "{}")
    if isinstance(payload.get("output_data"), str):
        import json
        payload["output_data"] = json.loads(payload["output_data"] or "null")
    if isinstance(payload.get("dependencies"), str):
        import json
        payload["dependencies"] = json.loads(payload["dependencies"] or "[]")
    allowed = set(Task.model_fields)
    return Task(**{k: v for k, v in payload.items() if k in allowed})


def dict_to_run(data: Dict[str, Any]) -> WorkflowRun:
    tasks = [dict_to_task(t, data) for t in (data.get("tasks") or [])]
    created = _parse_dt(data.get("created_at")) or datetime.now(timezone.utc)
    return WorkflowRun(
        run_id=data["run_id"],
        workflow_id=data.get("workflow_id", "default_workflow"),
        user_id=data.get("user_id", "default_user"),
        goal=data.get("goal", ""),
        status=data.get("status", "PENDING"),
        tasks=tasks,
        created_at=created,
    )


def task_updates(task: Task) -> Dict[str, Any]:
    dump = task.model_dump(mode="json")
    dump.pop("task_id", None)
    dump.pop("run_id", None)
    return dump


async def load_run(repo, run_id: str) -> Optional[WorkflowRun]:
    data = await maybe_await(repo.get_run(run_id))
    if data is None:
        return None
    if isinstance(data, WorkflowRun):
        return data
    return dict_to_run(data)


async def persist_task(repo, run_id: str, task: Task) -> None:
    try:
        result = repo.update_task(run_id, task.task_id, task_updates(task))
        await maybe_await(result)
    except TypeError:
        result = repo.update_task(run_id, task)
        await maybe_await(result)


async def persist_run(repo, run: WorkflowRun) -> None:
    dump = run.model_dump(mode="json")
    dump["tasks"] = [t.model_dump(mode="json") for t in run.tasks]
    await maybe_await(repo.save_run(dump))


async def persist_event(repo, event: WorkflowEvent) -> None:
    dump = event.model_dump(mode="json")
    await maybe_await(repo.save_event(dump))
