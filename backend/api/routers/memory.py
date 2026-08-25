"""
AgentOS — Memory Router

POST /api/v1/memory             — Add a memory entry
GET  /api/v1/memory             — List memory entries
POST /api/v1/memory/search      — Semantic search
DELETE /api/v1/memory/{id}      — Delete a memory entry
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel
from typing import Optional, List

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser, require_not_viewer
from backend.security.input_sanitizer import sanitize_text, InputValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


def _get_factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


class AddMemoryRequest(BaseModel):
    content: str
    memory_type: str = "semantic"   # "profile" | "workflow" | "semantic"
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None

class SearchMemoryRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    limit: int = 10


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_memory(
    body: AddMemoryRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Add a memory entry with optional embedding."""
    factory = _get_factory(request)

    try:
        content = sanitize_text(body.content, "content", max_length=10_000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Generate embedding using Gemini
    embedding = None
    try:
        from google import genai
        from backend.config.settings import settings
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        embed_result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=content,
        )
        if embed_result and embed_result.embeddings:
            embedding = embed_result.embeddings[0].values
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")

    memory_id = await factory.memory_repo.add_memory(
        user_id=user.user_id,
        content=content,
        embedding=embedding,
        memory_type=body.memory_type,
        tags=body.tags,
        metadata=body.metadata,
    )

    return {"memory_id": memory_id, "embedded": embedding is not None}


@router.get("")
async def list_memories(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    memory_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List memory entries for the current user."""
    factory = _get_factory(request)
    memories = await factory.memory_repo.list_memories(
        user_id=user.user_id,
        memory_type=memory_type,
        limit=limit,
        offset=offset,
    )
    return {"memories": memories, "count": len(memories)}


@router.post("/search")
async def search_memory(
    body: SearchMemoryRequest, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Semantic search over memory using embeddings."""
    factory = _get_factory(request)

    try:
        query = sanitize_text(body.query, "query", max_length=2000)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Generate query embedding
    query_embedding = None
    try:
        from google import genai
        from backend.config.settings import settings
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        embed_result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=query,
        )
        if embed_result and embed_result.embeddings:
            query_embedding = embed_result.embeddings[0].values
    except Exception as e:
        logger.warning(f"Query embedding failed: {e}")
        raise HTTPException(status_code=500, detail="Embedding service unavailable")

    results = await factory.memory_repo.search_similar(
        user_id=user.user_id,
        query_embedding=query_embedding,
        limit=body.limit,
    )

    return {"results": results, "count": len(results)}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Delete a memory entry."""
    factory = _get_factory(request)
    deleted = await factory.memory_repo.delete_memory(memory_id, user.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return {"memory_id": memory_id, "deleted": True}
