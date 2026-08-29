"""
AgentOS — Memory Router

POST /api/v1/memory             — Add a memory entry
GET  /api/v1/memory             — List memory entries
POST /api/v1/memory/search      — Semantic search
DELETE /api/v1/memory/{id}      — Delete a memory entry
"""

import asyncio
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

    embedding = None
    try:
        from backend.services.embedding_service import GoogleCloudEmbeddingService
        embedding = await asyncio.to_thread(GoogleCloudEmbeddingService().embed_text, content)
    except Exception as e:
        logger.exception("Embedding generation failed")
        raise HTTPException(status_code=500, detail=f"Embedding service unavailable: {e}") from e

    metadata = dict(body.metadata or {})
    if body.tags:
        metadata["tags"] = body.tags
    memory_id = await factory.memory_repo.store_memory(
        user_id=user.user_id,
        content=content,
        memory_type=body.memory_type,
        metadata=metadata,
        embedding=embedding or [],
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
    lister = getattr(factory.memory_repo, "list_memories", None)
    if not callable(lister):
        raise HTTPException(
            status_code=500,
            detail="Memory listing is not available on this storage backend.",
        )
    try:
        memories = await lister(
            user_id=user.user_id,
            memory_type=memory_type,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.exception("list_memories failed")
        raise HTTPException(status_code=500, detail=f"Could not list memories: {e}") from e
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

    query_embedding = None
    try:
        from backend.services.embedding_service import GoogleCloudEmbeddingService
        query_embedding = await asyncio.to_thread(GoogleCloudEmbeddingService().embed_text, query)
    except Exception as e:
        logger.exception("Query embedding failed")
        raise HTTPException(status_code=500, detail=f"Embedding service unavailable: {e}") from e

    results = await factory.memory_repo.search_memory(
        user_id=user.user_id,
        query_embedding=query_embedding,
        memory_type=body.memory_type,
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
    deleted = await factory.memory_repo.delete_memory(user.user_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return {"memory_id": memory_id, "deleted": True}
