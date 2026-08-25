"""
AgentOS — Role-Based Access Control (RBAC)

Roles: admin / user / viewer.
Resource-level checks — a user can only touch their own data.
"""

import logging
from enum import Enum
from typing import Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# ── Permission Matrix ─────────────────────────────────────────────
# Maps (role, resource_type, action) → allowed
# If not in the matrix, default is DENY.
PERMISSIONS = {
    # Admin can do everything
    (Role.ADMIN, "*", "*"): True,

    # User permissions
    (Role.USER, "workflow", "create"): True,
    (Role.USER, "workflow", "read"): True,
    (Role.USER, "workflow", "cancel"): True,
    (Role.USER, "workflow", "retry"): True,
    (Role.USER, "integration", "create"): True,
    (Role.USER, "integration", "read"): True,
    (Role.USER, "integration", "test"): True,
    (Role.USER, "integration", "enable"): True,
    (Role.USER, "integration", "disable"): True,
    (Role.USER, "resume", "create"): True,
    (Role.USER, "resume", "read"): True,
    (Role.USER, "resume", "tailor"): True,
    (Role.USER, "resume", "download"): True,
    (Role.USER, "schedule", "create"): True,
    (Role.USER, "schedule", "read"): True,
    (Role.USER, "schedule", "update"): True,
    (Role.USER, "schedule", "delete"): True,
    (Role.USER, "approval", "read"): True,
    (Role.USER, "approval", "decide"): True,
    (Role.USER, "settings", "read"): True,
    (Role.USER, "settings", "update"): True,
    (Role.USER, "notification", "read"): True,
    (Role.USER, "notification", "update"): True,
    (Role.USER, "memory", "read"): True,
    (Role.USER, "memory", "create"): True,
    (Role.USER, "memory", "delete"): True,
    (Role.USER, "secret", "create"): True,
    (Role.USER, "secret", "read"): True,
    (Role.USER, "secret", "delete"): True,
    (Role.USER, "profile", "read"): True,
    (Role.USER, "profile", "update"): True,

    # Viewer permissions (read-only)
    (Role.VIEWER, "workflow", "read"): True,
    (Role.VIEWER, "integration", "read"): True,
    (Role.VIEWER, "resume", "read"): True,
    (Role.VIEWER, "schedule", "read"): True,
    (Role.VIEWER, "approval", "read"): True,
    (Role.VIEWER, "settings", "read"): True,
    (Role.VIEWER, "notification", "read"): True,
    (Role.VIEWER, "profile", "read"): True,
}


def check_permission(role: str, resource_type: str, action: str) -> bool:
    """Check if a role has permission for an action on a resource type."""
    role_enum = Role(role) if isinstance(role, str) else role

    # Check admin wildcard first
    if PERMISSIONS.get((Role.ADMIN, "*", "*")) and role_enum == Role.ADMIN:
        return True

    return PERMISSIONS.get((role_enum, resource_type, action), False)


def require_permission(role: str, resource_type: str, action: str) -> None:
    """Raise 403 if the role doesn't have permission."""
    if not check_permission(role, resource_type, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {role} cannot {action} {resource_type}",
        )


def require_resource_owner(
    requesting_user_id: str,
    resource_owner_id: str,
    admin_role: Optional[str] = None,
) -> None:
    """
    Ensure the requesting user owns the resource.
    Admins bypass this check.
    """
    if admin_role == Role.ADMIN:
        return

    if requesting_user_id != resource_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you can only access your own resources",
        )
