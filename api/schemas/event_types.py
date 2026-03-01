"""Event type schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EventTypeCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1)
    description: str = ""
    moments: dict[str, int] = Field(default_factory=dict)


class EventTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    moments: dict[str, int] | None = None


class EventTypeResponse(BaseModel):
    slug: str
    name: str
    description: str = ""
    moments: dict[str, int]
