import re
import os

with open("backend/engine/engine.py", "r") as f:
    content = f.read()

# Add httpx and re to imports
if "import httpx" not in content:
    content = content.replace("import asyncio", "import asyncio\nimport httpx\nimport re\nimport json")

target = '                span.set_attribute("task.tool", str(task.tool))'

replacement = """                span.set_attribute("task.tool", str(task.tool))

                # 1. Variable Interpolation Pipeline
                def interpolate(val):
                    if isinstance(val, dict):
                        return {k: interpolate(v) for k, v in val.items()}
                    elif isinstance(val, list):
                        return [interpolate(v) for v in val]
                    elif isinstance(val, str):
                        pattern = r"\\{\\{\\s*(.*?)\\s*\\}\\}"
                        def replacer(match):
                            expr = match.group(1)
                            parts = expr.split('.')
                            if len(parts) >= 3 and parts[0] == 'tasks':
                                target_task_id = parts[1]
                                target_task = next((t for t in run.tasks if t.task_id == target_task_id), None)
                                if target_task and target_task.output_data:
                                    curr = target_task.output_data
                                    start_idx = 3 if parts[2] == 'output' else 2
                                    for p in parts[start_idx:]:
                                        if isinstance(curr, dict) and p in curr:
                                            curr = curr[p]
                                        else:
                                            return ""
                                    return str(curr) if not isinstance(curr, (dict, list)) else json.dumps(curr)
                            return match.group(0)
                        return re.sub(pattern, replacer, val)
                    return val
                
                interpolated_input = interpolate(task.input_data)
                
                # 2. Hybrid Execution: Core Deterministic Nodes
                if task.agent.startswith("core."):
                    async def _run_core():
                        if task.agent == "core.http":
                            url = interpolated_input.get("url", "")
                            method = interpolated_input.get("method", "GET").upper()
                            headers = interpolated_input.get("headers", {})
                            body = interpolated_input.get("body", None)
                            async with httpx.AsyncClient() as client:
                                req_kwargs = {"headers": headers}
                                if body and method in ["POST", "PUT", "PATCH"]:
                                    req_kwargs["json"] = body if isinstance(body, dict) else json.loads(body)
                                resp = await client.request(method, url, **req_kwargs)
                                try:
                                    return resp.json()
                                except:
                                    return {"text": resp.text, "status": resp.status_code}
                        elif task.agent == "core.set":
                            return interpolated_input.get("fields", {})
                        elif task.agent == "core.if":
                            condition = str(interpolated_input.get("condition", "False"))
                            # Safe boolean evaluation for demo
                            is_true = condition.lower() in ['true', '1', 'yes']
                            if not is_true:
                                task.status = TaskStatus.SKIPPED
                            return {"matched": is_true}
                        return {"error": f"Unknown core node: {task.agent}"}
                        
                    result = await asyncio.wait_for(_run_core(), timeout=task.timeout_seconds)
                else:"""

if "# 1. Variable Interpolation Pipeline" not in content:
    content = content.replace(target, replacement)
    
    # We also need to indent the else block closing. We will just find the corresponding lines and indent them.
    # Instead of manual regex indenting, let's just do a string replacement for the execution chunk.
    old_block = """                # Execute with timeout
                async def _run_agent():"""
    new_block = """                # Execute AI Agent with timeout
                    async def _run_agent():"""
    content = content.replace(old_block, new_block)
    
    # Find `result = await asyncio.wait_for(_run_agent(), timeout=task.timeout_seconds)` and indent it
    content = content.replace(
        "                result = await asyncio.wait_for(_run_agent(), timeout=task.timeout_seconds)",
        "                    result = await asyncio.wait_for(_run_agent(), timeout=task.timeout_seconds)"
    )

with open("backend/engine/engine.py", "w") as f:
    f.write(content)
