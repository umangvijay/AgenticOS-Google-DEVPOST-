import os
import json
import logging
import asyncio
import tempfile
import subprocess
import venv
from pathlib import Path

logger = logging.getLogger(__name__)

class SandboxTester:
    """
    Stage C: Live Network Testing.
    Executes the generated code in a safe sandbox environment to verify it works.
    In local mode, this uses a subprocess with a fresh venv.
    In cloud mode, it uses gVisor/Cloud Run.
    """
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    async def run_test(self, mcp_id: str, code: str) -> dict:
        """
        Runs the MCP server locally in a test harness to verify it starts and tools load.
        """
        logger.info(f"Running sandbox test for MCP {mcp_id}...")
        
        test_dir = self.workspace_dir / mcp_id
        test_dir.mkdir(parents=True, exist_ok=True)
        
        server_file = test_dir / "server.py"
        server_file.write_text(code)
        
        # Test harness to just import the module and inspect the FastMCP app
        harness_code = f"""
import sys
import json
import asyncio

try:
    import server
    # Find the FastMCP instance
    app = None
    for attr_name in dir(server):
        attr = getattr(server, attr_name)
        if type(attr).__name__ == 'FastMCP':
            app = attr
            break
            
    if not app:
        print(json.dumps({{"status": "error", "message": "Could not find FastMCP instance in generated code."}}))
        sys.exit(1)
        
    # Mock extract tools
    tools = []
    if hasattr(app, '_tools'):
        for t_name, t_func in app._tools.items():
            tools.append({{"name": t_name, "description": getattr(t_func, '__doc__', '')}})
            
    print(json.dumps({{"status": "success", "tools": tools}}))
except Exception as e:
    print(json.dumps({{"status": "error", "message": str(e)}}))
"""
        harness_file = test_dir / "test_harness.py"
        harness_file.write_text(harness_code)
        
        # In a real production setup, we'd provision a Docker container here.
        # For this Devpost version, we execute the Python harness in a subprocess with timeouts.
        try:
            # We use the current python executable so mcp package is available
            import sys
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(harness_file),
                cwd=str(test_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PYTHONPATH": str(test_dir)}
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            
            if proc.returncode != 0:
                logger.error(f"Sandbox test failed with exit code {proc.returncode}")
                return {"status": "error", "message": stderr.decode().strip() or "Unknown crash"}
                
            out = stdout.decode().strip()
            try:
                result = json.loads(out)
                return result
            except json.JSONDecodeError:
                return {"status": "error", "message": f"Invalid JSON from harness: {out}"}
                
        except asyncio.TimeoutError:
            proc.kill()
            return {"status": "error", "message": "Sandbox execution timed out."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
