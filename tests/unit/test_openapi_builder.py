import pytest
from pathlib import Path
from backend.mcp.builder.openapi_parser import OpenAPIParser, SSRFViolationError, OpenAPIParserError
from backend.mcp.builder.schema_generator import SchemaGenerator
from backend.mcp.builder.dynamic_builder import DynamicBuilder
from backend.repositories.in_memory_mcp_repository import InMemoryMCPRepository
from backend.models.mcp_schemas import ConnectorState

def test_parse_valid_petstore():
    parser = OpenAPIParser()
    path = Path(__file__).parent.parent / "fixtures" / "openapi" / "petstore.yaml"
    model = parser.parse_file(path)
    
    assert model.info["title"] == "Swagger Petstore"
    assert len(model.operations) == 3
    
    list_pets = next(op for op in model.operations if op.operation_id == "listPets")
    assert list_pets.http_method == "GET"
    assert len(list_pets.parameters) == 1
    assert list_pets.parameters[0].name == "limit"
    
    # Test $ref resolution mapping
    # createPets uses local requestBody
    create_pets = next(op for op in model.operations if op.operation_id == "createPets")
    assert create_pets.request_body is not None
    assert create_pets.security_requirements == [{'bearerAuth': []}]

def test_ssrf_protection_localhost():
    parser = OpenAPIParser()
    # It should block localhost URLs
    with pytest.raises(SSRFViolationError):
        parser._validate_ssrf("http://localhost:8080/api")
        
    with pytest.raises(SSRFViolationError):
        parser._validate_ssrf("https://127.0.0.1/api")

def test_remote_ref_rejection():
    parser = OpenAPIParser()
    with pytest.raises(OpenAPIParserError) as exc:
        parser._resolve_ref("https://example.com/schema.json")
    assert "Remote $refs are prohibited" in str(exc.value)

def test_schema_generator_naming():
    generator = SchemaGenerator()
    name = generator._normalize_name("get-pets/123@#")
    assert name == "get_pets_123" # stripped trailing _

def test_schema_generation():
    parser = OpenAPIParser()
    path = Path(__file__).parent.parent / "fixtures" / "openapi" / "petstore.yaml"
    model = parser.parse_file(path)
    
    gen = SchemaGenerator()
    tools = gen.generate(model, "test-mcp", "1.0.0")
    
    assert len(tools) == 3
    
    # Check createPets tool schema (requestBody mapped to properties)
    create_tool = next(t for t in tools if t.tool_name == "createPets")
    assert "name" in create_tool.input_schema["properties"]
    assert "name" in create_tool.input_schema["required"]
    assert create_tool.auth_requirements[0].auth_scheme == "bearerAuth"

def test_dynamic_builder_workflow():
    repo = InMemoryMCPRepository()
    builder = DynamicBuilder(repo)
    path = Path(__file__).parent.parent / "fixtures" / "openapi" / "petstore.yaml"
    
    manifest = builder.build_connector("petstore", "Petstore API", path)
    
    assert manifest.state == ConnectorState.PENDING_CREDENTIALS
    assert manifest.is_enabled is False
    assert manifest.spec_hash is not None
    assert manifest.endpoint == "http://127.0.0.1:8002/mcp"
    
    # Tool cache should be populated
    cached = repo.get_cached_tools("petstore")
    assert len(cached) == 3
    assert cached[0].tool_name in ["listPets", "createPets", "showPetById"]
