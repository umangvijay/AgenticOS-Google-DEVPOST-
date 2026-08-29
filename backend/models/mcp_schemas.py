from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum
from backend.models.security import RiskLevel

class AuthType(str, Enum):
    NONE = "NONE"
    OAUTH2 = "OAUTH2"
    API_KEY = "API_KEY"
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"

class AuthMetadata(BaseModel):
    type: AuthType = AuthType.NONE
    credential_ref: Optional[str] = Field(None, description="Reference to Secret Manager or Config")

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_auth_type(cls, value):
        if value is None or value == "":
            return AuthType.NONE
        raw = str(value).upper().replace(" ", "_")
        aliases = {
            "OAUTH": AuthType.OAUTH2,
            "OAUTH2": AuthType.OAUTH2,
            "BASIC": AuthType.API_KEY,
            "BEARER": AuthType.API_KEY,
            "APIKEY": AuthType.API_KEY,
            "API_KEY": AuthType.API_KEY,
            "NONE": AuthType.NONE,
            "SERVICE_ACCOUNT": AuthType.SERVICE_ACCOUNT,
        }
        return aliases.get(raw, value)

class ConnectorState(str, Enum):
    DRAFT = "DRAFT"
    PENDING_CREDENTIALS = "PENDING_CREDENTIALS"
    VALIDATING = "VALIDATING"
    HEALTHY = "HEALTHY"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    FAILED = "FAILED"

class MCPHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"

class MCPTransportType(str, Enum):
    STREAMABLE_HTTP = "streamable_http"
    STDIO = "stdio"
    INTERNAL = "internal"

class MCPManifest(BaseModel):
    mcp_id: str
    name: str
    version: str
    endpoint: str
    transport: MCPTransportType
    auth: AuthMetadata = Field(default_factory=AuthMetadata)
    scopes: List[str] = Field(default_factory=list)
    health: MCPHealthStatus = MCPHealthStatus.UNKNOWN
    health_updated_at: Optional[datetime] = None
    state: ConnectorState = ConnectorState.DRAFT
    spec_hash: Optional[str] = None
    spec_version: Optional[str] = None
    source_uri: Optional[str] = None
    built_at: Optional[datetime] = None
    description: str = ""
    trust_tier: str = "pending_review"
    source_type: str = "openapi"
    spec_json: Optional[str] = None
    owner: str = "system"
    is_enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OperationAuthRequirement(BaseModel):
    auth_scheme: str
    required_scopes: List[str] = Field(default_factory=list)

class CachedToolDefinition(BaseModel):
    tool_name: str
    description: str
    input_schema: Dict[str, Any]
    mcp_id: str
    mcp_version: str
    discovered_at: datetime
    expires_at: datetime
    # Phase 4: Operation-level auth binding
    auth_requirements: List[OperationAuthRequirement] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.CRITICAL
    operation: Optional[Dict[str, Any]] = None

class ToolPolicyResult(BaseModel):
    allowed: bool
    reason: Optional[str] = None
