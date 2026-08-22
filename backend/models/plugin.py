from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone

class PluginLifecycleState(str, Enum):
    DISCOVERED = "DISCOVERED"
    INSTALLING = "INSTALLING"
    INSTALLED = "INSTALLED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    ENABLED = "ENABLED"
    DISABLING = "DISABLING"
    DISABLED = "DISABLED"
    UNINSTALLING = "UNINSTALLING"
    UNINSTALLED = "UNINSTALLED"
    FAILED = "FAILED"

class PluginScope(str, Enum):
    GLOBAL = "GLOBAL"
    TENANT = "TENANT"
    USER = "USER"

class PluginAgentDefinition(BaseModel):
    agent_id: str
    display_name: str
    instructions: str
    allowed_tools: List[str] = Field(default_factory=list)
    model_policy: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

class PluginManifest(BaseModel):
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    agentos_version: str # e.g. ">=1.0.0"
    requested_permissions: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    agents: List[PluginAgentDefinition] = Field(default_factory=list)
    scope: PluginScope = PluginScope.USER
    manifest_hash: str
    
class PluginRecord(BaseModel):
    id: str = Field(description="Unique ID for this plugin installation record")
    manifest: PluginManifest
    state: PluginLifecycleState
    installed_by: str
    installed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
