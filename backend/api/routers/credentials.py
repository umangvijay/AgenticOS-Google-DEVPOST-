"""
AgentOS — User Credentials Router

Named, vault-encrypted credentials the agents can use on the user's behalf:
site logins for the browser agent, SMTP settings for email, API keys for
integrations (e.g. Stripe).

POST   /api/v1/credentials          — Store/replace a named credential
GET    /api/v1/credentials          — List credential names (values are never returned)
DELETE /api/v1/credentials/{name}   — Delete a credential

Storage format: the values dict is JSON-encoded, encrypted with AES-256-GCM
via the SecretsVault, and stored under the key "cred:{name}".
"""

import json
import logging
import re
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser, require_not_viewer
from backend.security.secrets_vault import secrets_vault

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/credentials", tags=["credentials"])

CRED_PREFIX = "cred:"
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")


def _get_factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


class StoreCredentialRequest(BaseModel):
    name: str                    # e.g. "fluentedge", "smtp", "stripe"
    values: Dict[str, str]       # e.g. {"username": "...", "password": "..."} or {"api_key": "..."}


@router.post("", status_code=status.HTTP_201_CREATED)
async def store_credential(
    body: StoreCredentialRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Encrypt and store a named credential for the current user."""
    factory = _get_factory(request)

    if not NAME_PATTERN.match(body.name):
        raise HTTPException(
            status_code=400,
            detail="Credential name must be 1-64 chars: letters, digits, dot, dash, underscore",
        )
    if not body.values:
        raise HTTPException(status_code=400, detail="Credential values cannot be empty")
    if len(json.dumps(body.values)) > 16_000:
        raise HTTPException(status_code=400, detail="Credential payload too large")

    encrypted = secrets_vault.encrypt(json.dumps(body.values))
    await factory.secrets_repo.store_secret(user.user_id, f"{CRED_PREFIX}{body.name}", encrypted)

    await factory.audit_repo.log_event({
        "event_type": "CREDENTIAL_STORED",
        "actor_id": user.user_id, "actor_type": "USER",
        "resource_id": body.name,
        "details": {"fields": sorted(body.values.keys())},  # field names only, never values
    })

    return {"name": body.name, "fields": sorted(body.values.keys()), "stored": True}


@router.get("")
async def list_credentials(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List the user's credential names. Values are never returned."""
    factory = _get_factory(request)
    keys = await factory.secrets_repo.list_secret_keys(user.user_id)
    names = [k[len(CRED_PREFIX):] for k in keys if k.startswith(CRED_PREFIX)]
    return {"credentials": names, "count": len(names)}


@router.delete("/{name}")
async def delete_credential(
    name: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Delete a named credential."""
    factory = _get_factory(request)
    deleted = await factory.secrets_repo.delete_secret(user.user_id, f"{CRED_PREFIX}{name}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")

    await factory.audit_repo.log_event({
        "event_type": "CREDENTIAL_DELETED",
        "actor_id": user.user_id, "actor_type": "USER",
        "resource_id": name,
        "details": {},
    })
    return {"name": name, "deleted": True}


async def load_credential(secrets_repo, user_id: str, name: str) -> Dict[str, str]:
    """Resolve and decrypt a named credential for internal service use."""
    encrypted = await secrets_repo.get_secret(user_id, f"{CRED_PREFIX}{name}")
    if not encrypted:
        raise ValueError(f"No credential named '{name}' is stored")
    return json.loads(secrets_vault.decrypt(encrypted))
