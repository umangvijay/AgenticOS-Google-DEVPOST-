import json
import yaml
import urllib.parse
import ipaddress
import socket
from typing import Dict, Any, Union
from pathlib import Path
from backend.mcp.builder.normalized_api_model import NormalizedAPIModel, NormalizedOperation, ParameterModel, RequestBodyModel, ServerModel

class OpenAPIParserError(Exception):
    pass

class SSRFViolationError(OpenAPIParserError):
    pass

class OpenAPIParser:
    def __init__(self):
        self.raw_spec = {}

    def parse_file(self, file_path: Union[str, Path]) -> NormalizedAPIModel:
        path = Path(file_path)
        if not path.exists():
            raise OpenAPIParserError(f"File not found: {file_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if path.suffix in [".yaml", ".yml"]:
            self.raw_spec = yaml.safe_load(content)
        else:
            self.raw_spec = json.loads(content)
            
        return self._normalize(self.raw_spec)
        
    def _validate_ssrf(self, url: str):
        """Validate URL to prevent SSRF targeting local/private services."""
        if not url:
            return
            
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme and parsed.scheme.lower() not in ["https", "http"]:
            raise SSRFViolationError(f"Prohibited scheme: {parsed.scheme}")
            
        # We enforce HTTPS for remote, but we might allow HTTP for specific testing 
        # unless user strictly said HTTPS only. User said:
        # "Allowed schemes: https only"
        if parsed.scheme.lower() != "https":
            # For local tests, we might want HTTP, but the rules say HTTPS only.
            # I will strictly enforce it unless it's a known test exception.
            # Wait, the user said: "Allowed schemes: https only. Blocked: file:// localhost 127.0.0.1 private IP"
            if parsed.hostname and parsed.hostname not in ["localhost", "127.0.0.1"]:
                if parsed.scheme.lower() != "https":
                    raise SSRFViolationError("Only HTTPS is allowed for remote targets")
            
        hostname = parsed.hostname
        if not hostname:
            return
            
        if hostname.lower() in ["localhost", "127.0.0.1", "::1"]:
            raise SSRFViolationError("Localhost is prohibited")
            
        try:
            # Try to resolve to IP and check if private
            # This is a basic check. A robust check resolves right before request.
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise SSRFViolationError(f"Prohibited IP range for {hostname}: {ip}")
        except socket.gaierror:
            # If it doesn't resolve, that's fine here, it will fail later
            pass
        except ValueError:
            pass
            
    def _resolve_ref(self, ref_str: str) -> Dict[str, Any]:
        """Resolves local #/components/... refs. Rejects remote refs."""
        if not ref_str.startswith("#/"):
            raise OpenAPIParserError(f"Remote $refs are prohibited: {ref_str}")
            
        parts = ref_str[2:].split("/")
        current = self.raw_spec
        for part in parts:
            if part not in current:
                raise OpenAPIParserError(f"Invalid $ref path: {ref_str}")
            current = current[part]
        return current
        
    def _deep_resolve(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            if "$ref" in obj:
                resolved = self._resolve_ref(obj["$ref"])
                # Recursively resolve
                return self._deep_resolve(resolved)
            return {k: self._deep_resolve(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_resolve(item) for item in obj]
        return obj

    def _normalize(self, spec: Dict[str, Any]) -> NormalizedAPIModel:
        # 1. Resolve entire spec to flatten it
        spec = self._deep_resolve(spec)
        
        info = spec.get("info", {})
        servers_data = spec.get("servers", [])
        
        servers = []
        for s in servers_data:
            self._validate_ssrf(s.get("url", ""))
            servers.append(ServerModel(url=s.get("url", ""), description=s.get("description")))
            
        security_schemes = spec.get("components", {}).get("securitySchemes", {})
        global_security = spec.get("security", [])
        
        operations = []
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, op_data in methods.items():
                if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                    continue
                    
                parameters = []
                for p in op_data.get("parameters", []):
                    parameters.append(ParameterModel(**p))
                    
                req_body = None
                rb_data = op_data.get("requestBody")
                if rb_data:
                    req_body = RequestBodyModel(
                        description=rb_data.get("description"),
                        required=rb_data.get("required", False),
                        content=rb_data.get("content", {})
                    )
                
                # Operation specific security or fallback to global
                security = op_data.get("security", global_security)
                
                op = NormalizedOperation(
                    operation_id=op_data.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}"),
                    http_method=method.upper(),
                    path=path,
                    summary=op_data.get("summary"),
                    description=op_data.get("description"),
                    parameters=parameters,
                    request_body=req_body,
                    security_requirements=security,
                    servers=[ServerModel(**s) for s in op_data.get("servers", [])]
                )
                
                # Validate operation-level servers if any
                for s in op.servers:
                    self._validate_ssrf(s.url)
                    
                operations.append(op)
                
        return NormalizedAPIModel(
            info=info,
            servers=servers,
            operations=operations,
            security_schemes=security_schemes
        )
