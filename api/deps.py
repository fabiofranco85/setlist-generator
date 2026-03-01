"""FastAPI dependency injection for repositories and config."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, HTTPException, status

from library.config import GenerationConfig
from library.repositories import get_repositories, RepositoryContainer

from .auth import get_current_user


async def get_org_id(x_org_id: str = Header(..., alias="X-Org-Id")) -> str:
    """Extract organization ID from request header."""
    if not x_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Org-Id header is required",
        )
    return x_org_id


async def get_repos(
    user: dict[str, Any] = Depends(get_current_user),
    org_id: str = Depends(get_org_id),
) -> RepositoryContainer:
    """Create per-request repositories with user auth and org context."""
    return get_repositories(
        backend="supabase",
        user_jwt=user["jwt"],
        org_id=org_id,
    )


async def get_generation_config(
    repos: RepositoryContainer = Depends(get_repos),
) -> GenerationConfig:
    """Load generation config from the repository (with org overrides)."""
    return GenerationConfig.from_config_repo(repos.config)


def require_role(*allowed_roles: str):
    """Create a dependency that checks user role against allowed roles.

    Usage:
        @router.post("/", dependencies=[Depends(require_role("editor", "org_admin"))])
    """

    async def _check_role(
        user: dict[str, Any] = Depends(get_current_user),
        org_id: str = Depends(get_org_id),
        repos: RepositoryContainer = Depends(get_repos),
    ) -> None:
        # Check if user is system admin (has all permissions)
        if hasattr(repos, "users") and repos.users:
            if repos.users.is_system_admin(user["id"]):
                return

        # Check org role
        if hasattr(repos, "users") and repos.users:
            role = repos.users.get_user_role(user["id"], org_id)
        else:
            role = None

        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(allowed_roles)}",
            )

    return _check_role


def require_system_admin():
    """Dependency that requires the user to be a system admin."""

    async def _check_admin(
        user: dict[str, Any] = Depends(get_current_user),
        repos: RepositoryContainer = Depends(get_repos),
    ) -> None:
        if hasattr(repos, "users") and repos.users:
            if repos.users.is_system_admin(user["id"]):
                return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System administrator access required",
        )

    return _check_admin
