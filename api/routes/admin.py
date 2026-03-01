"""System admin endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from library.repositories import RepositoryContainer

from ..deps import get_repos, require_system_admin

router = APIRouter()


@router.get("/songs/global", dependencies=[Depends(require_system_admin())])
async def list_global_songs(repos: RepositoryContainer = Depends(get_repos)):
    """List all global songs (system admin view)."""
    songs = await asyncio.to_thread(repos.songs.get_all)
    return [
        {"title": s.title, "energy": s.energy, "tags": s.tags}
        for s in songs.values()
    ]
