"""Supabase user and membership repository."""

from __future__ import annotations

from typing import Any


class SupabaseUserRepository:
    """User and organization membership management via Supabase."""

    def __init__(self, client: Any):
        self._client = client

    def get_user_orgs(self, user_id: str) -> list[dict]:
        """Get all organizations a user belongs to."""
        response = (
            self._client.table("memberships")
            .select("org_id, role, orgs(name, slug)")
            .eq("user_id", user_id)
            .execute()
        )

        results = []
        for row in response.data:
            org = row.get("orgs") or {}
            results.append({
                "org_id": row["org_id"],
                "org_name": org.get("name", ""),
                "org_slug": org.get("slug", ""),
                "role": row["role"],
            })
        return results

    def get_org_members(self, org_id: str) -> list[dict]:
        """Get all members of an organization."""
        response = (
            self._client.table("memberships")
            .select("user_id, role")
            .eq("org_id", org_id)
            .execute()
        )

        return [
            {"user_id": row["user_id"], "role": row["role"]}
            for row in response.data
        ]

    def get_user_role(self, user_id: str, org_id: str) -> str | None:
        """Get a user's role in an organization."""
        response = (
            self._client.table("memberships")
            .select("role")
            .eq("user_id", user_id)
            .eq("org_id", org_id)
            .execute()
        )

        if not response.data:
            return None
        return response.data[0]["role"]

    def is_system_admin(self, user_id: str) -> bool:
        """Check if a user is a system administrator."""
        response = (
            self._client.table("system_admins")
            .select("user_id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return (response.count or 0) > 0
