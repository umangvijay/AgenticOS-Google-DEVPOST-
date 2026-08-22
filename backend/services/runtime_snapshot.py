from typing import Dict, List, Set, Any
from backend.models.plugin import PluginManifest, PluginRecord, PluginLifecycleState

class PluginPolicy:
    def __init__(self):
        # A static map of valid permissions the system allows plugins to request
        self.ALLOWED_CAPABILITIES = {
            "memory.read",
            "memory.write",
            "mcp.calculator.use",
            "resume.read",
            "tool.web_search"
        }
        
    def is_allowed(self, requested_permissions: List[str]) -> bool:
        """
        Check if all requested permissions are recognized by the system.
        """
        for req in requested_permissions:
            if req not in self.ALLOWED_CAPABILITIES:
                return False
        return True
        
    def filter_allowed_tools(self, plugin: PluginManifest) -> List[str]:
        """
        Filters the requested tools to only those the plugin has permission to use.
        This provides a secondary security barrier.
        """
        allowed = []
        for tool in plugin.required_tools:
            # Map tool to required capability
            if tool.startswith("calculator.") and "mcp.calculator.use" in plugin.requested_permissions:
                allowed.append(tool)
            elif tool == "search_memory" and "memory.read" in plugin.requested_permissions:
                allowed.append(tool)
            elif tool == "store_memory" and "memory.write" in plugin.requested_permissions:
                allowed.append(tool)
            # Add other tool mappings here...
        return allowed

class RuntimeSnapshot:
    def __init__(self, version: int, active_plugins: List[PluginRecord]):
        self.version = version
        # We store immutable copies of the manifestations
        self.active_plugins = [r.model_copy(deep=True) for r in active_plugins]
        
    def get_plugin_agent_definitions(self) -> List[Any]:
        # Returns all valid PluginAgentDefinitions across all enabled plugins
        agents = []
        for plugin_record in self.active_plugins:
            agents.extend(plugin_record.manifest.agents)
        return agents

class RuntimeSnapshotRegistry:
    def __init__(self):
        self._current_version = 0
        self._snapshots: Dict[int, RuntimeSnapshot] = {}
        # Start with base snapshot
        self.build_snapshot([])
        
    def build_snapshot(self, enabled_plugins: List[PluginRecord]) -> RuntimeSnapshot:
        """
        Atomically swaps the runtime to a new version.
        """
        self._current_version += 1
        snapshot = RuntimeSnapshot(self._current_version, enabled_plugins)
        self._snapshots[self._current_version] = snapshot
        return snapshot
        
    def get_snapshot(self, version: int = None) -> RuntimeSnapshot:
        """
        Get a specific snapshot, or the latest if version is None.
        New workflows call get_snapshot() without version to bind to the latest.
        """
        if version is None:
            version = self._current_version
        return self._snapshots.get(version)
