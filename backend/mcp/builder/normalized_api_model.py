from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ParameterModel(BaseModel):
    name: str
    in_: str = Field(alias="in")  # query, header, path, cookie
    description: Optional[str] = None
    required: bool = False
    schema_: Dict[str, Any] = Field(default_factory=dict, alias="schema")

class RequestBodyModel(BaseModel):
    description: Optional[str] = None
    required: bool = False
    content: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class ServerModel(BaseModel):
    url: str
    description: Optional[str] = None

class NormalizedOperation(BaseModel):
    operation_id: str
    http_method: str
    path: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[ParameterModel] = Field(default_factory=list)
    request_body: Optional[RequestBodyModel] = None
    security_requirements: List[Dict[str, List[str]]] = Field(default_factory=list)
    servers: List[ServerModel] = Field(default_factory=list)

class NormalizedAPIModel(BaseModel):
    info: Dict[str, Any]
    servers: List[ServerModel] = Field(default_factory=list)
    operations: List[NormalizedOperation] = Field(default_factory=list)
    security_schemes: Dict[str, Any] = Field(default_factory=dict)
