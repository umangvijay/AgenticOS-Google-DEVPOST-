import re
from typing import List, Dict, Any
from backend.models.mcp_schemas import CachedToolDefinition, OperationAuthRequirement
from backend.mcp.builder.normalized_api_model import NormalizedAPIModel, NormalizedOperation

class SchemaGenerator:
    def _normalize_name(self, name: str) -> str:
        # alphanumeric and underscores only
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return name.strip('_')

    def generate_tool_schema(self, op: NormalizedOperation, mcp_id: str, mcp_version: str) -> CachedToolDefinition:
        from datetime import datetime, timezone
        
        # 1. Deterministic Naming
        tool_name = self._normalize_name(op.operation_id)
        
        # 2. Map Parameters
        properties = {}
        required = []
        
        for param in op.parameters:
            properties[param.name] = param.schema_
            if param.required:
                required.append(param.name)
                
        # 3. Map Request Body
        if op.request_body:
            # We assume application/json for now
            json_content = op.request_body.content.get("application/json")
            if json_content:
                schema = json_content.get("schema", {})
                
                # If the body is an object, we merge its properties into the tool schema
                # Because MCP tools accept a flat key-value argument map.
                if schema.get("type") == "object":
                    body_props = schema.get("properties", {})
                    for k, v in body_props.items():
                        properties[k] = v
                    if schema.get("required"):
                        required.extend(schema["required"])
                else:
                    # If it's a primitive or array, we map it as a single 'body' parameter
                    properties["request_body"] = schema
                    if op.request_body.required:
                        required.append("request_body")
                        
        input_schema = {
            "type": "object",
            "properties": properties
        }
        if required:
            input_schema["required"] = required
            
        # 4. Map Security Requirements
        auth_reqs = []
        for sec_dict in op.security_requirements:
            for scheme_name, scopes in sec_dict.items():
                auth_reqs.append(OperationAuthRequirement(
                    auth_scheme=scheme_name,
                    required_scopes=scopes
                ))
                
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        # Long expiration for dynamically built connectors, cache invalidation handled separately
        expires_at = now + timedelta(days=365)
        
        return CachedToolDefinition(
            tool_name=tool_name,
            description=op.summary or op.description or f"Invoke {op.operation_id}",
            input_schema=input_schema,
            mcp_id=mcp_id,
            mcp_version=mcp_version,
            discovered_at=now,
            expires_at=expires_at,
            auth_requirements=auth_reqs
        )

    def generate(self, model: NormalizedAPIModel, mcp_id: str, mcp_version: str) -> List[CachedToolDefinition]:
        tools = []
        for op in model.operations:
            tools.append(self.generate_tool_schema(op, mcp_id, mcp_version))
        return tools
