from pydantic import BaseModel, Field
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

class MCPManifest(BaseModel):
    mcp_id: str
    name: str
    version: str
    endpoint: str
    transport: MCPTransportType
    auth: AuthMetadata
    scopes: List[str] = Field(default_factory=list)
    health: MCPHealthStatus = MCPHealthStatus.UNKNOWN
    health_updated_at: Optional[datetime] = None
    # Phase 4 Metadata
    state: ConnectorState = ConnectorState.DRAFT
    spec_hash: Optional[str] = None
    spec_version: Optional[str] = None
    source_uri: Optional[str] = None
    built_at: Optional[datetime] = None

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
    # Phase 10: Authoritative risk level from the Registry
    risk_level: RiskLevel = RiskLevel.CRITICAL

class ToolPolicyResult(BaseModel):
    allowed: bool
    reason: Optional[str] = None
