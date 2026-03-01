"""Supabase client initialization with per-request auth and org context.

Each API request gets its own client instance configured with:
1. The user's JWT token (for RLS enforcement)
2. The organization UUID (set as app.org_id for org-scoped RLS)
"""

from __future__ import annotations

from typing import Any


def create_supabase_client(
    url: str,
    key: str,
    user_jwt: str = "",
    org_id: str = "",
) -> Any:
    """Create a Supabase client configured for a specific user and org.

    Args:
        url: Supabase project URL
        key: Supabase service role key (or anon key)
        user_jwt: User's JWT token for RLS enforcement
        org_id: Organization UUID for org-scoped RLS policies

    Returns:
        Configured Supabase client instance
    """
    from supabase import create_client, ClientOptions

    headers = {}
    if user_jwt:
        headers["Authorization"] = f"Bearer {user_jwt}"
    if org_id:
        # Custom header consumed by edge function or PostgREST config
        # to set app.org_id via: SET LOCAL app.org_id = '<uuid>'
        headers["x-org-id"] = org_id

    options = ClientOptions(headers=headers)
    client = create_client(url, key, options)

    return client


def set_org_context(client: Any, org_id: str) -> None:
    """Set the organization context on a Supabase connection.

    This executes SET LOCAL app.org_id for RLS policies that
    reference current_setting('app.org_id', true).

    Args:
        client: Supabase client instance
        org_id: Organization UUID
    """
    if org_id:
        client.rpc("set_org_context", {"p_org_id": org_id}).execute()
