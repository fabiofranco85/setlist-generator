"""Song CRUD, fork, search, and share endpoints."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query

from library.models import Song
from library.selector import get_days_since_last_use, get_song_usage_history
from library.transposer import (
    calculate_semitones,
    resolve_target_key,
    should_use_flats,
    transpose_content,
)

from ..deps import get_repos, get_current_user, require_role
from ..schemas.songs import SongCreate, SongFork, SongResponse, SongUpdate

router = APIRouter()


@router.get("", response_model=list[SongResponse])
async def list_songs(repos=Depends(get_repos)):
    """List all songs in the effective library."""
    songs = await asyncio.to_thread(repos.songs.get_all)
    return [
        SongResponse(
            title=s.title,
            energy=s.energy,
            tags=s.tags,
            youtube_url=s.youtube_url,
            event_types=s.event_types,
        )
        for s in songs.values()
    ]


@router.get("/search", response_model=list[SongResponse])
async def search_songs(q: str = Query(min_length=1), repos=Depends(get_repos)):
    """Search songs by title."""
    results = await asyncio.to_thread(repos.songs.search, q)
    return [
        SongResponse(
            title=s.title,
            energy=s.energy,
            tags=s.tags,
            youtube_url=s.youtube_url,
            event_types=s.event_types,
        )
        for s in results
    ]


@router.get("/{title}", response_model=SongResponse)
async def get_song(title: str, repos=Depends(get_repos)):
    """Get song details including chords."""
    song = await asyncio.to_thread(repos.songs.get_by_title, title)
    if not song:
        raise KeyError(f"Song '{title}' not found")
    return SongResponse(
        title=song.title,
        energy=song.energy,
        tags=song.tags,
        youtube_url=song.youtube_url,
        content=song.content,
        event_types=song.event_types,
    )


@router.post("", response_model=SongResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def create_song(data: SongCreate, repos=Depends(get_repos)):
    """Create a new song."""
    song = Song(
        title=data.title,
        tags=data.tags,
        energy=data.energy,
        content=data.content,
        youtube_url=data.youtube_url,
        event_types=data.event_types,
    )

    if hasattr(repos.songs, "create"):
        await asyncio.to_thread(repos.songs.create, song, data.visibility)
    else:
        raise ValueError("Song creation not supported by this backend")

    return SongResponse(
        title=song.title,
        energy=song.energy,
        tags=song.tags,
        youtube_url=song.youtube_url,
        content=song.content,
        event_types=song.event_types,
    )


@router.patch("/{title}", response_model=SongResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def update_song(title: str, data: SongUpdate, repos=Depends(get_repos)):
    """Update song fields."""
    song = await asyncio.to_thread(repos.songs.get_by_title, title)
    if not song:
        raise KeyError(f"Song '{title}' not found")

    if data.content is not None:
        await asyncio.to_thread(repos.songs.update_content, title, data.content)
        song = await asyncio.to_thread(repos.songs.get_by_title, title)

    return SongResponse(
        title=song.title,
        energy=song.energy,
        tags=song.tags,
        youtube_url=song.youtube_url,
        content=song.content,
        event_types=song.event_types,
    )


@router.delete("/{title}", dependencies=[Depends(require_role("editor", "org_admin"))])
async def delete_song(title: str, repos=Depends(get_repos)):
    """Delete a song."""
    if hasattr(repos.songs, "delete"):
        await asyncio.to_thread(repos.songs.delete, title)
    else:
        raise ValueError("Song deletion not supported by this backend")
    return {"detail": f"Song '{title}' deleted"}


@router.post("/{title}/fork", response_model=SongResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def fork_song(title: str, data: SongFork, repos=Depends(get_repos)):
    """Fork an existing song with modifications."""
    if not hasattr(repos.songs, "fork"):
        raise ValueError("Song forking not supported by this backend")

    overrides: dict[str, Any] = {}
    if data.title:
        overrides["title"] = data.title
    if data.energy is not None:
        overrides["energy"] = data.energy
    if data.tags is not None:
        overrides["tags"] = data.tags

    new_title = await asyncio.to_thread(repos.songs.fork, title, overrides)
    song = await asyncio.to_thread(repos.songs.get_by_title, new_title)

    return SongResponse(
        title=song.title,
        energy=song.energy,
        tags=song.tags,
        youtube_url=song.youtube_url,
        event_types=song.event_types,
    )


@router.post("/{title}/share", dependencies=[Depends(require_role("editor", "org_admin"))])
async def share_song(title: str, repos=Depends(get_repos)):
    """Share a user-level song to org visibility."""
    if hasattr(repos.songs, "share_to_org"):
        await asyncio.to_thread(repos.songs.share_to_org, title)
    else:
        raise ValueError("Song sharing not supported by this backend")
    return {"detail": f"Song '{title}' shared to organization"}


@router.post("/{title}/transpose")
async def transpose_song(
    title: str,
    to: str = Query(..., description="Target key"),
    repos=Depends(get_repos),
):
    """Preview a song transposed to a different key."""
    song = await asyncio.to_thread(repos.songs.get_by_title, title)
    if not song:
        raise KeyError(f"Song '{title}' not found")
    if not song.content:
        raise ValueError(f"Song '{title}' has no chord content")

    # Extract current key from content header
    first_line = song.content.split("\n")[0]
    current_key = ""
    if "(" in first_line and ")" in first_line:
        start = first_line.rfind("(")
        end = first_line.rfind(")")
        current_key = first_line[start + 1 : end].strip()

    if not current_key:
        raise ValueError(f"Cannot determine current key for '{title}'")

    effective_key = resolve_target_key(current_key, to)
    semitones = calculate_semitones(current_key, effective_key)
    use_flats = should_use_flats(effective_key)
    transposed = transpose_content(song.content, semitones, use_flats)

    return {
        "title": title,
        "original_key": current_key,
        "target_key": effective_key,
        "content": transposed,
    }


@router.get("/{title}/info")
async def song_info(title: str, repos=Depends(get_repos)):
    """Get song statistics and usage history."""
    song = await asyncio.to_thread(repos.songs.get_by_title, title)
    if not song:
        raise KeyError(f"Song '{title}' not found")

    history = await asyncio.to_thread(repos.history.get_all)
    usage = get_song_usage_history(title, history)
    days = get_days_since_last_use(title, history)

    return {
        "title": song.title,
        "energy": song.energy,
        "tags": song.tags,
        "youtube_url": song.youtube_url,
        "event_types": song.event_types,
        "usage_count": len(usage),
        "days_since_last_use": days,
        "usage_history": usage,
    }
