"""Song library merging and share validation for multi-tenant SaaS.

This module provides pure functions for combining songs from different
visibility scopes (global, org, user) and validating share operations.
"""

from __future__ import annotations

from .models import Song


def merge_effective_library(
    global_songs: dict[str, Song],
    org_songs: dict[str, Song],
    user_songs: dict[str, Song],
) -> dict[str, Song]:
    """Merge songs from all visibility scopes into a single library.

    Higher-scope songs are overridden by lower-scope songs with the same title:
    global < org < user (user songs take priority).

    Args:
        global_songs: Songs visible to all organizations
        org_songs: Songs visible within the current organization
        user_songs: Songs owned by the current user

    Returns:
        Merged dictionary mapping song titles to Song objects
    """
    merged = {}
    merged.update(global_songs)
    merged.update(org_songs)
    merged.update(user_songs)
    return merged


VALID_SCOPES = ("user", "org", "global")
SCOPE_ORDER = {scope: i for i, scope in enumerate(VALID_SCOPES)}


def validate_share_request(
    song: Song,
    from_scope: str,
    to_scope: str,
) -> None:
    """Validate that a share operation is valid.

    Share operations move a song to a wider visibility scope:
    user -> org -> global. Narrowing is not supported.

    Args:
        song: The song being shared
        from_scope: Current visibility scope
        to_scope: Target visibility scope

    Raises:
        ValueError: If the share operation is invalid
    """
    if from_scope not in VALID_SCOPES:
        raise ValueError(f"Invalid source scope '{from_scope}'. Valid: {', '.join(VALID_SCOPES)}")

    if to_scope not in VALID_SCOPES:
        raise ValueError(f"Invalid target scope '{to_scope}'. Valid: {', '.join(VALID_SCOPES)}")

    if SCOPE_ORDER[to_scope] <= SCOPE_ORDER[from_scope]:
        raise ValueError(
            f"Cannot share from '{from_scope}' to '{to_scope}'. "
            f"Songs can only be promoted to wider visibility."
        )

    if from_scope == to_scope:
        raise ValueError(f"Song '{song.title}' is already at '{from_scope}' scope.")
