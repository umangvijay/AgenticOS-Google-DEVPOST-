import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Union
from backend.repositories.mcp_repository import MCPRepository
from backend.models.mcp_schemas import MCPManifest, MCPTransportType, AuthMetadata, AuthType, ConnectorState
from backend.mcp.builder.openapi_parser import OpenAPIParser
from backend.mcp.builder.schema_generator import SchemaGenerator

class DynamicBuilder:
    def __init__(self, mcp_repo: MCPRepository):
        self.mcp_repo = mcp_repo
        self.parser = OpenAPIParser()
        self.schema_gen = SchemaGenerator()

    def build_connector(self, mcp_id: str, name: str, source_uri: Union[str, Path]) -> MCPManifest:
        # 1. Parse and Validate OpenAPI Spec
        normalized_api = self.parser.parse_file(source_uri)
        
        # 2. Compute fingerprint/hash
        spec_hash = hashlib.sha256(json.dumps(self.parser.raw_spec, sort_keys=True).encode()).hexdigest()
        
        # 3. Check if existing version matches
        existing = self.mcp_repo.get_mcp(mcp_id)
        if existing and existing.spec_hash == spec_hash:
            # Idempotent return
            return existing
            
        spec_version = normalized_api.info.get("version", "1.0.0")
        
        # 4. Create the manifest referencing the Proxy Server
        # The endpoint for all dynamic builders points to the central Proxy Service
        # We will assume it runs on a known local/internal path, e.g., http://proxy:8000
        # The proxy itself uses the mcp_id to fetch the specific API definition from the repo
        proxy_endpoint = "http://127.0.0.1:8002/mcp/sse" # Proxy server address
        
        manifest = MCPManifest(
            mcp_id=mcp_id,
            name=name,
            version=spec_version,
            endpoint=proxy_endpoint,
            transport=MCPTransportType.STREAMABLE_HTTP,
            auth=AuthMetadata(type=AuthType.NONE), # User will inject credential_ref later
            state=ConnectorState.PENDING_CREDENTIALS, # Secure by default
            is_enabled=False,
            spec_hash=spec_hash,
            spec_version=spec_version,
            source_uri=str(source_uri),
            built_at=datetime.now(timezone.utc)
        )
        
        # 5. Generate and Cache Tools
        tools = self.schema_gen.generate(normalized_api, mcp_id, spec_version)
        
        # 6. Save State
        self.mcp_repo.register_mcp(manifest)
        self.mcp_repo.cache_tools(mcp_id, tools)
        
        return manifest
