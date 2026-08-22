import pytest
import os
import asyncio
from pathlib import Path
from backend.models.mcp_schemas import MCPManifest, MCPTransportType, AuthMetadata, AuthType
from backend.mcp.mcp_client import MCPClientManager

@pytest.fixture
def adversarial_manifest():
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "adversarial", "adversarial_mcp.py"))
    return MCPManifest(
        mcp_id="evil-mcp",
        name="Adversarial MCP",
        version="1.0.0",
        endpoint=f"python '{script_path}'",
        transport=MCPTransportType.STDIO,
        auth=AuthMetadata(type=AuthType.NONE),
        is_enabled=True
    )

@pytest.mark.asyncio
async def test_sandbox_network_blocked(adversarial_manifest):
    # Test network isolation directly
    import asyncio
    from backend.mcp.sandbox.sandbox_controller import SandboxController
    
    script = """
import urllib.request
try:
    urllib.request.urlopen("http://example.com", timeout=2)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {str(e)}")
"""
    with open("tests/fixtures/adversarial/adv_net.py", "w") as f:
        f.write(script)
        
    adversarial_manifest.endpoint = "python tests/fixtures/adversarial/adv_net.py"
    
    cmd, args = SandboxController.apply_docker_sandbox(adversarial_manifest, "python", ["tests/fixtures/adversarial/adv_net.py"])
    proc = await asyncio.create_subprocess_exec(
        cmd, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode()
    
    assert "FAILED" in out
    assert "SUCCESS" not in out

@pytest.mark.asyncio
async def test_sandbox_fs_blocked(adversarial_manifest):
    import asyncio
    from backend.mcp.sandbox.sandbox_controller import SandboxController
    
    script = """
try:
    with open("/etc/shadow", "r") as f:
        print("SUCCESS")
except Exception as e:
    print(f"FAILED: {str(e)}")
"""
    with open("tests/fixtures/adversarial/adv_fs.py", "w") as f:
        f.write(script)
        
    adversarial_manifest.endpoint = "python tests/fixtures/adversarial/adv_fs.py"
    cmd, args = SandboxController.apply_docker_sandbox(adversarial_manifest, "python", ["tests/fixtures/adversarial/adv_fs.py"])
    proc = await asyncio.create_subprocess_exec(
        cmd, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode()
    
    assert "FAILED" in out
    assert "SUCCESS" not in out

@pytest.mark.asyncio
async def test_sandbox_oom_killed(adversarial_manifest):
    import asyncio
    from backend.mcp.sandbox.sandbox_controller import SandboxController
    
    script = """
arr = []
try:
    while True:
        arr.append("A" * 1024 * 1024 * 10) # 10MB chunks
except MemoryError:
    print("FAILED: MemoryError caught")
print("ALIVE")
"""
    with open("tests/fixtures/adversarial/adv_oom.py", "w") as f:
        f.write(script)
        
    adversarial_manifest.endpoint = "python tests/fixtures/adversarial/adv_oom.py"
    cmd, args = SandboxController.apply_docker_sandbox(adversarial_manifest, "python", ["tests/fixtures/adversarial/adv_oom.py"])
    proc = await asyncio.create_subprocess_exec(
        cmd, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    # Docker kills the process due to OOM
    # Non-zero exit code and ALIVE is not printed
    assert proc.returncode != 0
    assert "ALIVE" not in stdout.decode()
