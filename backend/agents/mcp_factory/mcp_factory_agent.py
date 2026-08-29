import hashlib
import json
import logging
from typing import Any, Dict, Optional

import httpx

from urllib.parse import urljoin, urlparse

from backend.agents.mcp_factory.code_generator import CodeGenerator
from backend.agents.mcp_factory.tool_registry_manager import ToolRegistryManager
from backend.engine.mcp_catalog import detect_named_apps, resolve_named_spec, sketch_openapi_from_prompt
from backend.mcp.builder.openapi_parser import OpenAPIParser, OpenAPIParserError, SSRFViolationError
from backend.mcp.builder.schema_generator import SchemaGenerator
from backend.mcp.openapi_executor import execute_openapi_tool
from backend.mcp.website_mcp import (
    default_start_url,
    looks_like_website_without_api,
    origin_from_url,
    plan_website_connector,
    tools_from_plan,
    website_mcp_id,
)
from backend.services import gemini_client
from backend.services.gemini_client import GeminiQuotaExceeded, is_quota_error

logger = logging.getLogger(__name__)


class MCPFactoryAgent:
    def __init__(self, mcp_repo, secrets_repo=None):
        self.mcp_repo = mcp_repo
        self.secrets_repo = secrets_repo
        self.code_gen = CodeGenerator()
        self.registry = ToolRegistryManager(mcp_repo)
        self.parser = OpenAPIParser()
        self.schema_gen = SchemaGenerator()

    async def _log(self, build_id: Optional[str], message: str, logs: list) -> None:
        logs.append(message)
        logger.info("[mcp-factory] %s", message)
        if build_id:
            await self.mcp_repo.update_build(build_id, {"logs": logs, "stage": logs[-1][:80]})

    async def run_build(
        self,
        *,
        user_id: str,
        method: str,
        source: str,
        name: str = "",
        build_id: Optional[str] = None,
        auth_type: str = "API_KEY",
    ) -> Dict[str, Any]:
        logs: list = []
        try:
            if build_id:
                await self.mcp_repo.update_build(build_id, {"status": "running", "stage": "fetching"})
            await self._log(build_id, "Starting MCP factory", logs)
            if method == "website" or (
                method in ("prompt", "url")
                and looks_like_website_without_api(source, url=source if str(source).startswith("http") else None)
            ):
                return await self._build_website(user_id=user_id, source=source, name=name, build_id=build_id, logs=logs)

            spec_text, source_uri = await self._ingest(method, source, logs, build_id, name=name)
            await self._log(build_id, "Parsing OpenAPI specification", logs)
            model = self.parser.parse_text(spec_text)
            if not model.operations:
                raise ValueError("No HTTP operations found in the specification")
            if not model.servers:
                for op in model.operations:
                    if op.servers:
                        model.servers = list(op.servers)
                        break
            if not model.servers:
                raise ValueError("OpenAPI spec has no HTTPS servers")
            self._resolve_relative_servers(model, source_uri)

            spec_hash = hashlib.sha256(spec_text.encode("utf-8")).hexdigest()
            spec_version = str(model.info.get("version") or "1.0.0")
            display_name = name or model.info.get("title") or "Custom Integration"
            mcp_id = hashlib.sha256(f"{user_id}:{spec_hash}".encode("utf-8")).hexdigest()[:16]

            await self._log(build_id, f"Generating tool schemas ({min(len(model.operations), 80)} ops)", logs)
            tools = self.schema_gen.generate(model, mcp_id, spec_version)
            if not tools:
                raise ValueError("Schema generator produced no tools")

            await self._log(build_id, "Validating generated tool metadata", logs)
            for t in tools:
                if not t.operation or not (t.operation.get("servers") or t.operation.get("path")):
                    raise ValueError(f"Tool {t.tool_name} is missing operation metadata")

            await self._log(build_id, "Running live sandbox probe", logs)
            probe = await self._probe(tools[0].model_dump(mode="json"), model)
            await self._log(build_id, f"Probe result: {probe.get('status', probe)}", logs)

            trust_tier = "verified" if method in ("url", "spec", "openapi") else "pending_review"
            auto_enable = True

            await self._log(build_id, "Registering MCP in the catalog", logs)
            mcp_id = await self.registry.register_mcp(
                display_name,
                f"Auto-generated from {method}",
                tools,
                owner=user_id,
                trust_tier=trust_tier,
                source_type=method,
                source_uri=source_uri,
                spec_json=spec_text,
                spec_hash=spec_hash,
                spec_version=spec_version,
                auth={"type": auth_type},
                is_enabled=auto_enable,
                mcp_id=mcp_id,
            )

            tool_summaries = [{"name": t.tool_name, "description": t.description} for t in tools]
            names = ", ".join(t["name"] for t in tool_summaries[:16] if t.get("name"))
            msg = (
                f"Built {display_name} with {len(tools)} tool{'s' if len(tools) != 1 else ''}"
                + (f": {names}." if names else ".")
                + f"\nmcp_id: {mcp_id}. Store the API key in Vault to call these tools live."
            )
            result = {
                "status": "success",
                "message": msg,
                "reply": msg,
                "mcp_id": mcp_id,
                "name": display_name,
                "tools": tool_summaries,
                "trust_tier": trust_tier,
            }
            if build_id:
                await self.mcp_repo.update_build(build_id, {
                    "status": "success",
                    "stage": "registered",
                    "mcp_id": mcp_id,
                    "tools": tool_summaries,
                    "logs": logs,
                    "error": None,
                })
            return result
        except Exception as e:
            logger.exception("MCP build failed")
            if build_id:
                await self.mcp_repo.update_build(build_id, {
                    "status": "error",
                    "stage": "failed",
                    "error": str(e),
                    "logs": logs + [f"FAILED: {e}"],
                })
            return {"status": "error", "message": str(e)}

    async def _build_website(
        self,
        *,
        user_id: str,
        source: str,
        name: str,
        build_id: Optional[str],
        logs: list,
    ) -> Dict[str, Any]:
        start = default_start_url(source, "https://example.com")
        if "example.com" in start and "http" not in (source or "").lower():
            raise ValueError("Name the website URL so tools can open it in the browser.")
        origin = origin_from_url(start)
        await self._log(build_id, f"No OpenAPI — building browser tools for {origin}", logs)
        plan = await plan_website_connector(source, origin, start)
        display = name or str(plan.get("name") or urlparse(origin).hostname)
        mcp_id = website_mcp_id(user_id, origin)
        tools = tools_from_plan(mcp_id, origin, start, plan)
        await self._log(build_id, f"Registering {len(tools)} browser tools", logs)
        spec = json.dumps({"origin": origin, "start_url": start, "plan": plan}, default=str)
        spec_hash = hashlib.sha256(spec.encode("utf-8")).hexdigest()
        mcp_id = await self.registry.register_mcp(
            display,
            f"Browser tools for {origin} (no OpenAPI — Playwright)",
            tools,
            owner=user_id,
            trust_tier="pending_review",
            source_type="website",
            source_uri=start,
            spec_json=spec,
            spec_hash=spec_hash,
            spec_version="1.0.0",
            auth={"type": "NONE"},
            is_enabled=True,
            mcp_id=mcp_id,
        )
        summaries = [{"name": t.tool_name, "description": t.description} for t in tools]
        names = ", ".join(t["name"] for t in summaries[:16])
        msg = (
            f"Built {display} with {len(tools)} browser tool{'s' if len(tools) != 1 else ''}: {names}. "
            f"These run a real browser on {origin} (not a REST API). "
            "Store a Vault login (username/email + password) and pass credential_name when a tool needs sign-in."
        )
        result = {
            "status": "success",
            "message": msg,
            "reply": msg,
            "mcp_id": mcp_id,
            "name": display,
            "tools": summaries,
            "trust_tier": "pending_review",
            "kind": "website",
        }
        if build_id:
            await self.mcp_repo.update_build(build_id, {
                "status": "success",
                "stage": "registered",
                "mcp_id": mcp_id,
                "tools": summaries,
                "logs": logs,
                "error": None,
            })
        return result

    async def build_from_url(self, url: str, name: str = "API Integration", user_id: str = "system") -> Dict[str, Any]:
        return await self.run_build(user_id=user_id, method="url", source=url, name=name)

    async def build_from_prompt(self, prompt: str, name: str = "Custom Integration", user_id: str = "system") -> Dict[str, Any]:
        return await self.run_build(user_id=user_id, method="prompt", source=prompt, name=name)

    async def build_from_spec(self, spec: str, name: str = "API Integration", user_id: str = "system") -> Dict[str, Any]:
        return await self.run_build(user_id=user_id, method="spec", source=spec, name=name)

    @staticmethod
    def _resolve_relative_servers(model, source_uri: Optional[str]) -> None:
        """OpenAPI allows relative server URLs; resolve them against the spec's own URL."""
        from urllib.parse import urljoin

        def fix(servers):
            for server in servers:
                if server.url.startswith(("http://", "https://")):
                    continue
                if source_uri:
                    server.url = urljoin(source_uri, server.url)
                else:
                    raise ValueError(
                        f"Spec uses relative server URL '{server.url}' but no source URL is known"
                    )

        fix(model.servers)
        for op in model.operations:
            fix(op.servers)

    async def _fetch_text(self, url: str) -> str:
        self.parser._validate_ssrf(url)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
        if len(content) > 400_000:
            content = content[:400_000]
        return content

    def _parse_or_none(self, content: str):
        try:
            self.parser.parse_text(content)
            return content
        except Exception:
            return None

    async def _try_well_known_specs(self, source: str, logs: list, build_id: Optional[str]) -> Optional[tuple]:
        parsed = urlparse(source)
        if not parsed.scheme or not parsed.netloc:
            return None
        base = f"{parsed.scheme}://{parsed.netloc}"
        candidates = []
        for path in (
            "/openapi.json",
            "/openapi.yaml",
            "/swagger.json",
            "/swagger.yaml",
            "/v3/api-docs",
            "/api-docs",
            "/api/openapi.json",
        ):
            url = urljoin(base + "/", path.lstrip("/"))
            if url.rstrip("/") != source.rstrip("/"):
                candidates.append(url)
        for url in candidates:
            try:
                await self._log(build_id, f"Trying spec at {url}", logs)
                content = await self._fetch_text(url)
                if self._parse_or_none(content):
                    return content, url
            except Exception:
                continue
        return None

    async def _spec_from_prompt(self, source: str, logs: list, build_id: Optional[str]) -> str:
        prompt = (
            "You convert a natural-language description of ANY application or HTTP API "
            "into a compact OpenAPI 3.0 JSON object. Named apps (GitHub, Slack, Notion, "
            "Stripe, Gmail, Shopify, HubSpot, Jira, etc.) must use their official public HTTPS base URL. "
            "Include only the operations needed for the request, typically 4–12. "
            "Each path operation needs operationId, summary, and responses. "
            "servers must be a non-empty array of https URLs. No localhost, metadata, or invented hosts.\n\n"
            "Return JSON only with keys: openapi, info, servers, paths.\n\nDescription:\n" + source
        )
        spec = await gemini_client.generate_json(prompt)
        if isinstance(spec, dict):
            spec = json.dumps(spec)
        return spec

    async def _ingest(self, method: str, source: str, logs: list, build_id: Optional[str], name: str = "") -> tuple:
        if method in ("spec", "openapi"):
            return source, None
        if method == "prompt":
            await self._log(build_id, "Asking the model to produce an OpenAPI 3 spec for this app", logs)
            last_error: Optional[Exception] = None
            for attempt in range(2):
                try:
                    spec = await self._spec_from_prompt(source, logs, build_id)
                    if self._parse_or_none(spec):
                        return spec, None
                    last_error = ValueError("Model spec did not parse as OpenAPI 3")
                    await self._log(build_id, "Model spec was invalid; retrying once", logs)
                    source = source + "\n\nThe previous JSON was invalid OpenAPI 3. Return a simpler valid spec."
                except (GeminiQuotaExceeded, Exception) as e:
                    last_error = e
                    if not (isinstance(e, GeminiQuotaExceeded) or is_quota_error(e)):
                        if attempt == 0:
                            await self._log(build_id, f"Model spec failed ({e}); retrying", logs)
                            continue
                        break
                    break
            named = resolve_named_spec(name) if name else None
            if named is None and len(detect_named_apps(source or "")) == 1:
                named = resolve_named_spec(source or "")
            if named:
                spec_text, display, _auth = named
                await self._log(
                    build_id,
                    f"Model unavailable or invalid spec; using bundled OpenAPI for {display}",
                    logs,
                )
                if spec_text.startswith("http"):
                    return await self._fetch_text(spec_text), spec_text
                return spec_text, None
            sketched = sketch_openapi_from_prompt(source or "")
            if sketched and self._parse_or_none(sketched):
                await self._log(
                    build_id,
                    "Model unavailable; sketched OpenAPI from the request (operations come from your wording)",
                    logs,
                )
                return sketched, None
            if last_error and (isinstance(last_error, GeminiQuotaExceeded) or is_quota_error(last_error)):
                raise ValueError(
                    "The model could not build this MCP (quota). Add a Gemini key in Settings, "
                    "or paste an OpenAPI URL."
                ) from last_error
            raise ValueError(
                "The model could not produce a valid OpenAPI spec for that app. "
                "Paste an OpenAPI URL or a shorter description of the HTTP API."
            ) from last_error
        if method == "url":
            await self._log(build_id, f"Fetching {source}", logs)
            content = await self._fetch_text(source)
            parsed = self._parse_or_none(content)
            if parsed:
                return parsed, source
            found = await self._try_well_known_specs(source, logs, build_id)
            if found:
                return found
            await self._log(build_id, "Fetched docs are not a raw spec; extracting OpenAPI with Gemini", logs)
            try:
                spec = await gemini_client.generate_json(
                    "This page is documentation or a website for an application. Extract or construct "
                    "a valid OpenAPI 3.0 JSON object covering the HTTP API a client would call. "
                    "Use only https servers from the docs. Return JSON only.\n\n" + content[:80000]
                )
                if isinstance(spec, dict):
                    spec = json.dumps(spec)
                return spec, source
            except (GeminiQuotaExceeded, Exception) as e:
                if not (isinstance(e, GeminiQuotaExceeded) or is_quota_error(e)):
                    raise
                sketched = sketch_openapi_from_prompt(source or "")
                if sketched and self._parse_or_none(sketched):
                    await self._log(build_id, "Gemini unavailable; sketched OpenAPI from the URL and description", logs)
                    return sketched, source
                raise ValueError(
                    "This URL is not an OpenAPI spec and Gemini is unavailable. "
                    "Paste an OpenAPI JSON/YAML URL or a description of the HTTP API."
                ) from e
        raise ValueError(f"Unknown ingest method: {method}")

    async def _probe(self, tool: Dict[str, Any], model) -> Dict[str, Any]:
        """Live list/schema check. Optional GET with no required params hits the real API."""
        op = tool.get("operation") or {}
        if op.get("http_method") != "GET":
            return {"status": "skipped", "reason": "first tool is not GET"}
        required = (tool.get("input_schema") or {}).get("required") or []
        if required:
            return {"status": "skipped", "reason": "tool requires arguments"}
        fake_manifest = {"auth": {"type": "NONE"}}
        try:
            result = await execute_openapi_tool(fake_manifest, tool, {}, user_id="system")
            return {"status": "probed", "ok": result.get("ok"), "http_status": result.get("status")}
        except SSRFViolationError as e:
            raise
        except Exception as e:
            return {"status": "probe_error", "error": str(e)}
