"""Supabase repository backend for multi-tenant SaaS deployments.

Requires: supabase>=2.0 (install via `uv sync --group saas`)

Usage:
    repos = SupabaseRepositoryContainer.create(
        supabase_url="https://xxx.supabase.co",
        supabase_key="service-role-key",
        user_jwt="user-jwt-token",
        org_id="org-uuid",
    )
"""

from .client import create_supabase_client
from .songs import SupabaseSongRepository
from .history import SupabaseHistoryRepository
from .config import SupabaseConfigRepository
from .event_types import SupabaseEventTypeRepository
from .users import SupabaseUserRepository
from .share_requests import SupabaseShareRequestRepository

from ..factory import SaaSRepositoryContainer

from ...repositories.filesystem import FilesystemOutputRepository

from pathlib import Path


class SupabaseRepositoryContainer:
    """Factory for creating all Supabase-backed repositories."""

    @classmethod
    def create(
        cls,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        user_jwt: str | None = None,
        org_id: str | None = None,
        base_path: Path | None = None,
        **kwargs,
    ) -> SaaSRepositoryContainer:
        """Create a SaaS repository container with Supabase backend.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key
            user_jwt: User's JWT token for RLS
            org_id: Organization UUID for org-scoped queries
            base_path: Base path for filesystem output (default: cwd)
        """
        import os

        url = supabase_url or os.environ["SUPABASE_URL"]
        key = supabase_key or os.environ["SUPABASE_KEY"]
        jwt = user_jwt or os.environ.get("SUPABASE_USER_JWT", "")
        oid = org_id or os.environ.get("SUPABASE_ORG_ID", "")

        client = create_supabase_client(url, key, jwt, oid)

        # Output always uses filesystem
        fs_base = base_path or Path.cwd()

        return SaaSRepositoryContainer(
            songs=SupabaseSongRepository(client, oid),
            history=SupabaseHistoryRepository(client, oid),
            config=SupabaseConfigRepository(client, oid),
            output=FilesystemOutputRepository(fs_base),
            event_types=SupabaseEventTypeRepository(client, oid),
            users=SupabaseUserRepository(client),
            share_requests=SupabaseShareRequestRepository(client, oid),
        )


__all__ = [
    "SupabaseRepositoryContainer",
    "SupabaseSongRepository",
    "SupabaseHistoryRepository",
    "SupabaseConfigRepository",
    "SupabaseEventTypeRepository",
    "SupabaseUserRepository",
    "SupabaseShareRequestRepository",
    "create_supabase_client",
]
