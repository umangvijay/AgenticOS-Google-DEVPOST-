"""Execute registered OpenAPI tools as real HTTP calls. No synthetic responses."""

import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

from backend.mcp.builder.openapi_parser import OpenAPIParser, SSRFViolationError
from backend.security.secrets_vault import secrets_vault

logger = logging.getLogger(__name__)


async def resolve_secret(user_id: str, credential_ref: Optional[str], secrets_repo=None) -> Optional[str]:
    if not credential_ref or not secrets_repo:
        return None
    encrypted = await secrets_repo.get_secret(user_id, credential_ref)
    if not encrypted:
        return None
    decrypted = secrets_vault.decrypt(encrypted)
    # Named credentials (cred:*) store a JSON dict; extract the token field.
    if decrypted.lstrip().startswith("{"):
        try:
            values = json.loads(decrypted)
            if isinstance(values, dict):
                for field in ("api_key", "token", "access_token", "secret_key", "password"):
                    if values.get(field):
                        return str(values[field])
                if len(values) == 1:
                    return str(next(iter(values.values())))
        except (ValueError, TypeError):
            pass
    return decrypted


async def execute_openapi_tool(
    manifest: Dict[str, Any],
    tool: Dict[str, Any],
    arguments: Dict[str, Any],
    *,
    user_id: str = "system",
    secrets_repo=None,
    run_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    operation = tool.get("operation") or {}
    if not operation:
        raise ValueError(f"Tool {tool.get('tool_name')} has no stored OpenAPI operation")
    if operation.get("kind") == "browser":
        from backend.mcp.website_mcp import execute_browser_tool
        return await execute_browser_tool(
            tool, arguments, user_id=user_id, secrets_repo=secrets_repo,
            run_id=run_id, task_id=task_id,
        )

    parser = OpenAPIParser()
    servers = operation.get("servers") or []
    base_url = servers[0]["url"] if servers and isinstance(servers[0], dict) else (servers[0] if servers else "")
    if not base_url:
        raise ValueError("OpenAPI operation has no server URL")
    parser._validate_ssrf(base_url)

    path = operation.get("path") or ""
    query_params: Dict[str, Any] = {}
    headers: Dict[str, str] = {}
    json_body = None
    arguments = arguments or {}

    for param in operation.get("parameters") or []:
        name = param.get("name")
        val = arguments.get(name)
        if val is None:
            if param.get("required"):
                raise ValueError(f"Missing required parameter: {name}")
            continue
        loc = param.get("in", "query")
        if loc == "path":
            path = path.replace(f"{{{name}}}", str(val))
        elif loc == "header":
            headers[name] = str(val)
        else:
            query_params[name] = val

    param_names = {p.get("name") for p in (operation.get("parameters") or [])}
    extra = {k: v for k, v in arguments.items() if k not in param_names}
    if extra:
        json_body = extra.get("request_body") if "request_body" in extra and len(extra) == 1 else extra

    auth = manifest.get("auth") or {}
    if isinstance(auth, str):
        auth = json.loads(auth)
    credential_ref = auth.get("credential_ref")
    secret = await resolve_secret(user_id, credential_ref, secrets_repo)
    if secret:
        auth_type = str(auth.get("type") or "API_KEY").upper()
        if auth_type in ("OAUTH2", "OAUTH", "API_KEY", "NONE"):
            headers.setdefault("Authorization", f"Bearer {secret}")

    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/")) if not path.startswith("http") else path
    if not path.startswith("http"):
        url = base_url.rstrip("/") + (path if path.startswith("/") else "/" + path)
    parser._validate_ssrf(url)

    method = (operation.get("http_method") or "GET").upper()
    async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                params=query_params,
                headers=headers,
                json=json_body,
            )
        except SSRFViolationError:
            raise
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e), "url": url, "method": method}

        if response.status_code in (301, 302, 307, 308):
            loc = response.headers.get("Location", "")
            parser._validate_ssrf(loc)
            raise RuntimeError(f"Redirect blocked for security: {loc}")

        body: Any
        try:
            body = response.json()
        except Exception:
            body = response.text

        if response.is_error:
            return {
                "ok": False,
                "status": response.status_code,
                "url": url,
                "method": method,
                "body": body,
            }
        return {
            "ok": True,
            "status": response.status_code,
            "url": url,
            "method": method,
            "body": body,
        }
