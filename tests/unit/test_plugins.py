import pytest
import hashlib
import json
from backend.models.plugin import PluginManifest, PluginAgentDefinition, PluginLifecycleState
from backend.services.runtime_snapshot import RuntimeSnapshotRegistry, PluginPolicy
from backend.services.plugin_registry_service import PluginRegistryService, PluginValidator
from backend.repositories.plugin_repository import InMemoryPluginRepository

def test_plugin_validation_and_permissions():
    policy = PluginPolicy()
    validator = PluginValidator(policy)
    
    # Valid manifest
    manifest_dict = {
        "plugin_id": "com.example.plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "Test",
        "author": "Me",
        "agentos_version": "1.0.0",
        "requested_permissions": ["memory.read"],
        "required_tools": ["search_memory"],
        "agents": [
            {
                "agent_id": "test_agent",
                "display_name": "Test Agent",
                "instructions": "Be helpful",
                "allowed_tools": ["search_memory"]
            }
        ],
        "scope": "USER",
        "manifest_hash": ""
    }
    
    manifest = PluginManifest.model_validate(manifest_dict)
    computed_hash = hashlib.sha256(manifest.model_dump_json(exclude={"manifest_hash"}, exclude_none=True).encode('utf-8')).hexdigest()
    manifest.manifest_hash = computed_hash
    raw_payload_hashed = manifest.model_dump_json()
    
    # Should pass
    assert validator.validate_manifest(manifest, raw_payload_hashed) == True
    
    # Test unallowed permission
    manifest_dict["requested_permissions"] = ["admin.root"]
    manifest = PluginManifest.model_validate(manifest_dict)
    computed_hash = hashlib.sha256(manifest.model_dump_json(exclude={"manifest_hash"}, exclude_none=True).encode('utf-8')).hexdigest()
    manifest.manifest_hash = computed_hash
    raw_payload_hashed = manifest.model_dump_json()
    
    with pytest.raises(ValueError, match="Manifest requests unsupported or forbidden permissions."):
        validator.validate_manifest(manifest, raw_payload_hashed)
        
    # Test version failure
    manifest_dict["requested_permissions"] = ["memory.read"]
    manifest_dict["agentos_version"] = "2.0.0"
    manifest = PluginManifest.model_validate(manifest_dict)
    computed_hash = hashlib.sha256(manifest.model_dump_json(exclude={"manifest_hash"}, exclude_none=True).encode('utf-8')).hexdigest()
    manifest.manifest_hash = computed_hash
    raw_payload_hashed = manifest.model_dump_json()
    
    with pytest.raises(ValueError, match="Incompatible AgentOS version"):
        validator.validate_manifest(manifest, raw_payload_hashed)

def test_hot_swapping_snapshots():
    repo = InMemoryPluginRepository()
    snapshot_registry = RuntimeSnapshotRegistry()
    service = PluginRegistryService(repo, snapshot_registry)
    
    manifest_dict = {
        "plugin_id": "com.example.swap",
        "name": "Swap Plugin",
        "version": "1.0.0",
        "description": "Test",
        "author": "Me",
        "agentos_version": "1.0.0",
        "requested_permissions": [],
        "required_tools": [],
        "agents": [],
        "scope": "GLOBAL",
        "manifest_hash": ""
    }
    
    manifest = PluginManifest.model_validate(manifest_dict)
    computed_hash = hashlib.sha256(manifest.model_dump_json(exclude={"manifest_hash"}, exclude_none=True).encode('utf-8')).hexdigest()
    manifest.manifest_hash = computed_hash
    raw_payload_hashed = manifest.model_dump_json()
    
    # Base snapshot
    base_snapshot = snapshot_registry.get_snapshot()
    assert base_snapshot.version == 1
    assert len(base_snapshot.active_plugins) == 0
    
    # Install
    record = service.install_plugin(raw_payload_hashed, "user1")
    assert record.state == PluginLifecycleState.INSTALLED
    
    # Enable should bump snapshot
    service.enable_plugin(record.id, "user1")
    
    new_snapshot = snapshot_registry.get_snapshot()
    assert new_snapshot.version == 2
    assert len(new_snapshot.active_plugins) == 1
    
    # Existing workflows using base_snapshot still see 0 plugins
    assert len(base_snapshot.active_plugins) == 0
    
    # Disable should bump snapshot again
    service.disable_plugin(record.id, "user1")
    final_snapshot = snapshot_registry.get_snapshot()
    assert final_snapshot.version == 3
    assert len(final_snapshot.active_plugins) == 0
    
    # Version 2 should still have the plugin
    assert len(snapshot_registry.get_snapshot(2).active_plugins) == 1
