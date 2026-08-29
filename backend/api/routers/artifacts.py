"""
AgentOS — Generated artifacts API

GET  /api/v1/artifacts                 — List this user's generated websites/apps
GET  /api/v1/artifacts/{id}            — Artifact metadata
GET  /api/v1/artifacts/{id}/files/{path} — Serve a generated file
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from backend.api.dependencies.auth import AuthenticatedUser, get_current_user
from backend.services.artifact_builder import ArtifactError, list_artifacts, load_artifact, read_artifact_file

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("")
async def list_user_artifacts(user: AuthenticatedUser = Depends(get_current_user)):
    items = list_artifacts(user.user_id)
    return {"artifacts": items, "count": len(items)}


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    try:
        return load_artifact(user.user_id, artifact_id)
    except ArtifactError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{artifact_id}/files/{file_path:path}")
async def get_artifact_file(
    artifact_id: str,
    file_path: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        path = read_artifact_file(user.user_id, artifact_id, file_path)
    except ArtifactError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return FileResponse(path)
