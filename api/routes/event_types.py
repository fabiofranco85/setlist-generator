"""Event type CRUD endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from library.event_type import EventType
from library.repositories import RepositoryContainer

from ..deps import get_repos, require_role
from ..schemas.event_types import EventTypeCreate, EventTypeResponse, EventTypeUpdate

router = APIRouter()


@router.get("", response_model=list[EventTypeResponse])
async def list_event_types(repos: RepositoryContainer = Depends(get_repos)):
    """List all event types for the organization."""
    if not repos.event_types:
        return []

    all_types = await asyncio.to_thread(repos.event_types.get_all)
    return [
        EventTypeResponse(
            slug=et.slug,
            name=et.name,
            description=et.description,
            moments=et.moments,
        )
        for et in all_types.values()
    ]


@router.get("/{slug}", response_model=EventTypeResponse)
async def get_event_type(slug: str, repos: RepositoryContainer = Depends(get_repos)):
    """Get a specific event type."""
    if not repos.event_types:
        raise KeyError(f"Event type '{slug}' not found")

    et = await asyncio.to_thread(repos.event_types.get, slug)
    if not et:
        raise KeyError(f"Event type '{slug}' not found")

    return EventTypeResponse(
        slug=et.slug,
        name=et.name,
        description=et.description,
        moments=et.moments,
    )


@router.post("", response_model=EventTypeResponse, dependencies=[Depends(require_role("org_admin"))])
async def create_event_type(data: EventTypeCreate, repos: RepositoryContainer = Depends(get_repos)):
    """Create a new event type."""
    if not repos.event_types:
        raise ValueError("Event types not supported by this backend")

    et = EventType(
        slug=data.slug,
        name=data.name,
        description=data.description,
        moments=data.moments if data.moments else {},
    )
    await asyncio.to_thread(repos.event_types.add, et)

    return EventTypeResponse(
        slug=et.slug,
        name=et.name,
        description=et.description,
        moments=et.moments,
    )


@router.patch("/{slug}", response_model=EventTypeResponse, dependencies=[Depends(require_role("org_admin"))])
async def update_event_type(slug: str, data: EventTypeUpdate, repos: RepositoryContainer = Depends(get_repos)):
    """Update an event type."""
    if not repos.event_types:
        raise ValueError("Event types not supported by this backend")

    kwargs = {}
    if data.name is not None:
        kwargs["name"] = data.name
    if data.description is not None:
        kwargs["description"] = data.description
    if data.moments is not None:
        kwargs["moments"] = data.moments

    await asyncio.to_thread(repos.event_types.update, slug, **kwargs)

    et = await asyncio.to_thread(repos.event_types.get, slug)
    return EventTypeResponse(
        slug=et.slug,
        name=et.name,
        description=et.description,
        moments=et.moments,
    )


@router.delete("/{slug}", dependencies=[Depends(require_role("org_admin"))])
async def delete_event_type(slug: str, repos: RepositoryContainer = Depends(get_repos)):
    """Delete an event type."""
    if not repos.event_types:
        raise ValueError("Event types not supported by this backend")

    await asyncio.to_thread(repos.event_types.remove, slug)
    return {"detail": f"Event type '{slug}' removed"}
