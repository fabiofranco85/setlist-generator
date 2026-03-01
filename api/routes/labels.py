"""Label management endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from library.labeler import relabel_setlist
from library.repositories import RepositoryContainer

from ..deps import get_repos, require_role
from ..schemas.setlists import SetlistResponse

router = APIRouter()


@router.post("", response_model=SetlistResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def add_label(
    date: str,
    label: str,
    event_type: str = "",
    repos: RepositoryContainer = Depends(get_repos),
):
    """Add a label to an existing setlist (creates a copy with the label)."""
    source = await asyncio.to_thread(repos.history.get_by_date, date, "", event_type)
    if not source:
        raise KeyError(f"Setlist for {date} not found")

    if await asyncio.to_thread(repos.history.exists, date, label, event_type):
        raise ValueError(f"Label '{label}' already exists for {date}")

    new_setlist = relabel_setlist(source, label)
    await asyncio.to_thread(repos.history.save, new_setlist)

    return SetlistResponse(
        date=new_setlist.date,
        moments=new_setlist.moments,
        label=new_setlist.label,
        event_type=new_setlist.event_type,
    )


@router.patch("/{label}", response_model=SetlistResponse, dependencies=[Depends(require_role("editor", "org_admin"))])
async def rename_label(
    label: str,
    new_label: str,
    date: str,
    event_type: str = "",
    repos: RepositoryContainer = Depends(get_repos),
):
    """Rename a label on a setlist."""
    source = await asyncio.to_thread(repos.history.get_by_date, date, label, event_type)
    if not source:
        raise KeyError(f"Setlist for {date} (label: {label}) not found")

    if await asyncio.to_thread(repos.history.exists, date, new_label, event_type):
        raise ValueError(f"Label '{new_label}' already exists for {date}")

    new_setlist = relabel_setlist(source, new_label)
    await asyncio.to_thread(repos.history.save, new_setlist)
    await asyncio.to_thread(repos.history.delete, date, label, event_type)

    return SetlistResponse(
        date=new_setlist.date,
        moments=new_setlist.moments,
        label=new_setlist.label,
        event_type=new_setlist.event_type,
    )


@router.delete("/{label}", dependencies=[Depends(require_role("editor", "org_admin"))])
async def remove_label(
    label: str,
    date: str,
    event_type: str = "",
    repos: RepositoryContainer = Depends(get_repos),
):
    """Remove a labeled setlist."""
    if not await asyncio.to_thread(repos.history.exists, date, label, event_type):
        raise KeyError(f"Setlist for {date} (label: {label}) not found")

    await asyncio.to_thread(repos.history.delete, date, label, event_type)
    repos.output.delete_outputs(date, label, event_type)

    return {"detail": f"Label '{label}' removed from {date}"}
