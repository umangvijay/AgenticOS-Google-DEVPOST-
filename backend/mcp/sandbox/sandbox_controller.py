import os
import shlex
from typing import List, Dict, Tuple
from backend.models.mcp_schemas import MCPManifest
from backend.mcp.sandbox.audit_logger import audit_logger

class SandboxController:
    """
    Transforms execution parameters into secure, isolated sandbox executions.
    """
    
    @classmethod
    def apply_docker_sandbox(
        cls, 
        manifest: MCPManifest, 
        command: str, 
        args: List[str], 
        timeout: int = 15,
        memory_limit: str = "128m",
        cpus: str = "0.5",
        env_vars: Dict[str, str] = None
    ) -> Tuple[str, List[str]]:
        """
        Takes a raw command (e.g. `python script.py`) and wraps it in a 
        secure Docker container.
        """
        
        # Base docker constraints
        # -i: Interactive (needed for stdio)
        # --rm: Ephemeral, delete container after exit
        # --network none: Absolute network isolation
        # --read-only: Root filesystem is read-only
        # --security-opt=no-new-privileges: Prevent privilege escalation
        # --user nobody: Execute as unprivileged user
        
        # We need a base image that has python. In reality, MCP connectors might need specific images.
        # For tests, we use a standard python image. 
        # But wait! If we run `python script.py`, the script MUST be mounted inside the container!
        # If `command` is an absolute path to a local script, we must mount its directory.
        
        docker_args = [
            "run",
            "-i",
            "--rm",
            "--network=none",
            "--read-only",
            "--security-opt=no-new-privileges",
            "--user", "nobody",
            f"--memory={memory_limit}",
            f"--cpus={cpus}",
        ]
        
        # To avoid mounting the entire host filesystem and allowing escapes, we mount ONLY the parent dir of the script, 
        # and mount it read-only.
        # If the command is just `python`, and args[0] is the script:
        script_path = None
        if command.endswith("python") and args:
            script_path = args[0]
        elif os.path.exists(command):
            script_path = command
            
        if script_path and os.path.exists(script_path):
            script_dir = os.path.abspath(os.path.dirname(script_path))
            # Mount it at /app as read-only
            docker_args.append(f"-v")
            docker_args.append(f"{script_dir}:/app:ro")
            
            # Set working dir
            docker_args.append("-w")
            docker_args.append("/app")
            
            # Reconstruct the command inside container
            if command.endswith("python"):
                command = "python3" # Explicitly use python3 inside container
                args.insert(0, "-u")
                args[1] = os.path.basename(script_path)
            else:
                command = f"/app/{os.path.basename(script_path)}"
                
        # Inject isolated environment variables
        # We DO NOT pass host environments. 
        if env_vars:
            for k, v in env_vars.items():
                docker_args.append("-e")
                docker_args.append(f"{k}={v}")
                
        # Determine image
        # For a true sandbox, we use a lightweight restricted python image
        image = "python:3.11-alpine"
        docker_args.append(image)
        
        # Append the actual execution command
        docker_args.append(command)
        docker_args.extend(args)
        
        audit_logger.log_sandbox_execution(manifest.mcp_id, "unknown", f"docker {' '.join(docker_args)}")
        
        return "docker", docker_args
