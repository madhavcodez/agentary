from __future__ import annotations

from uuid import UUID


async def check_project_access(user_id: UUID, project_id: UUID) -> bool:
    """Stub: Check if a user has access to a project. Will be expanded in Phase 6."""
    # For now, all authenticated users can access their own projects
    return True


async def check_admin(user_id: UUID) -> bool:
    """Stub: Check if a user is an admin."""
    return True


async def require_project_owner(user_id: UUID, project_id: UUID) -> bool:
    """Stub: Verify user owns the project."""
    return True
