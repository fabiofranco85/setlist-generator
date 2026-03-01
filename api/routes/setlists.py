"""Setlist generation, viewing, replacement, and derivation endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from library.config import GenerationConfig
from library.formatter import format_setlist_markdown
from library.generator import SetlistGenerator
from library.pdf_formatter import generate_setlist_pdf_bytes
from library.replacer import (
    derive_setlist,
    find_target_setlist,
    replace_song_in_setlist,
    select_replacement_song,
    validate_replacement_request,
)
from library.repositories import RepositoryContainer

from ..deps import get_repos, get_generation_config, require_role
from ..schemas.setlists import (
    DeriveRequest,
    GenerateRequest,
    ReplaceRequest,
    SetlistResponse,
)

router = APIRouter()


@router.post("/generate", response_model=SetlistResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def generate_setlist(
    data: GenerateRequest,
    repos: RepositoryContainer = Depends(get_repos),
    config: GenerationConfig = Depends(get_generation_config),
):
    """Generate a new setlist."""
    songs = await asyncio.to_thread(repos.songs.get_all)
    history = await asyncio.to_thread(repos.history.get_all)

    generator = SetlistGenerator(songs, history, config=config)

    # Use event type moments if specified
    moments_config = None
    if data.event_type and repos.event_types:
        et = await asyncio.to_thread(repos.event_types.get, data.event_type)
        if et:
            moments_config = et.moments

    setlist = await asyncio.to_thread(
        generator.generate,
        data.date,
        data.overrides,
        label=data.label,
        event_type=data.event_type,
        moments_config=moments_config,
    )

    # Save
    await asyncio.to_thread(repos.history.save, setlist)

    # Generate markdown output
    md = format_setlist_markdown(setlist, songs)
    await asyncio.to_thread(
        repos.output.save_markdown, setlist.date, md,
        setlist.label, setlist.event_type,
    )

    return SetlistResponse(
        date=setlist.date,
        moments=setlist.moments,
        label=setlist.label,
        event_type=setlist.event_type,
    )


@router.get("", response_model=list[SetlistResponse])
async def list_setlists(
    label: str | None = None,
    event_type: str | None = None,
    repos: RepositoryContainer = Depends(get_repos),
):
    """List setlists (filterable by label and event_type)."""
    all_history = await asyncio.to_thread(repos.history.get_all)

    results = []
    for entry in all_history:
        if label is not None and entry.get("label", "") != label:
            continue
        if event_type is not None and entry.get("event_type", "") != event_type:
            continue
        results.append(SetlistResponse(
            date=entry["date"],
            moments=entry["moments"],
            label=entry.get("label", ""),
            event_type=entry.get("event_type", ""),
        ))

    return results


@router.get("/{date}", response_model=SetlistResponse)
async def get_setlist(
    date: str,
    label: str = "",
    event_type: str = "",
    repos: RepositoryContainer = Depends(get_repos),
):
    """Get a specific setlist by date."""
    entry = await asyncio.to_thread(repos.history.get_by_date, date, label, event_type)
    if not entry:
        raise KeyError(f"Setlist for {date} not found")

    return SetlistResponse(
        date=entry["date"],
        moments=entry["moments"],
        label=entry.get("label", ""),
        event_type=entry.get("event_type", ""),
    )


@router.post("/{date}/replace", response_model=SetlistResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def replace_song(
    date: str,
    data: ReplaceRequest,
    label: str = "",
    event_type: str = "",
    repos: RepositoryContainer = Depends(get_repos),
    config: GenerationConfig = Depends(get_generation_config),
):
    """Replace a song in a setlist."""
    songs = await asyncio.to_thread(repos.songs.get_all)
    history = await asyncio.to_thread(repos.history.get_all)

    setlist_dict = find_target_setlist(history, date, label, event_type)
    validate_replacement_request(setlist_dict, data.moment, data.position, data.song, songs, config=config)

    replacement = await asyncio.to_thread(
        select_replacement_song,
        data.moment, setlist_dict, data.position, songs, history, data.song,
    )

    new_setlist = replace_song_in_setlist(
        setlist_dict, data.moment, data.position, replacement, songs, config=config,
    )

    await asyncio.to_thread(repos.history.update, date, new_setlist, label, event_type)

    return SetlistResponse(
        date=new_setlist["date"],
        moments=new_setlist["moments"],
        label=new_setlist.get("label", ""),
        event_type=new_setlist.get("event_type", ""),
    )


@router.post("/{date}/derive", response_model=SetlistResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def derive_setlist_endpoint(
    date: str,
    data: DeriveRequest,
    event_type: str = "",
    repos: RepositoryContainer = Depends(get_repos),
    config: GenerationConfig = Depends(get_generation_config),
):
    """Derive a labeled variant from an existing setlist."""
    songs = await asyncio.to_thread(repos.songs.get_all)
    history = await asyncio.to_thread(repos.history.get_all)

    base = find_target_setlist(history, date, event_type=event_type)

    derived = await asyncio.to_thread(
        derive_setlist, base, songs, history,
        data.replace_count, event_type, config,
    )

    # Set label and save
    derived["label"] = data.label
    if event_type:
        derived["event_type"] = event_type

    from library.models import Setlist
    setlist = Setlist(
        date=derived["date"],
        moments=derived["moments"],
        label=data.label,
        event_type=event_type,
    )
    await asyncio.to_thread(repos.history.save, setlist)

    return SetlistResponse(
        date=derived["date"],
        moments=derived["moments"],
        label=data.label,
        event_type=event_type,
    )


@router.get("/{date}/pdf")
async def download_pdf(
    date: str,
    label: str = "",
    event_type: str = "",
    repos: RepositoryContainer = Depends(get_repos),
):
    """Download a setlist as PDF."""
    entry = await asyncio.to_thread(repos.history.get_by_date, date, label, event_type)
    if not entry:
        raise KeyError(f"Setlist for {date} not found")

    songs = await asyncio.to_thread(repos.songs.get_all)
    from library.models import Setlist
    setlist = Setlist(
        date=entry["date"],
        moments=entry["moments"],
        label=entry.get("label", ""),
        event_type=entry.get("event_type", ""),
    )

    pdf_bytes = await asyncio.to_thread(generate_setlist_pdf_bytes, setlist, songs)

    filename = f"setlist-{date}"
    if label:
        filename += f"-{label}"
    filename += ".pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
