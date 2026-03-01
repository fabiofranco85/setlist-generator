"""Song schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SongCreate(BaseModel):
    title: str
    energy: float = Field(ge=1, le=4)
    tags: dict[str, int] = Field(default_factory=dict)
    youtube_url: str = ""
    content: str = ""
    visibility: str = Field(default="user", pattern="^(global|org|user)$")
    event_types: list[str] = Field(default_factory=list)


class SongUpdate(BaseModel):
    energy: float | None = Field(default=None, ge=1, le=4)
    tags: dict[str, int] | None = None
    youtube_url: str | None = None
    content: str | None = None
    event_types: list[str] | None = None


class SongResponse(BaseModel):
    title: str
    energy: float
    tags: dict[str, int]
    youtube_url: str = ""
    content: str = ""
    event_types: list[str] = Field(default_factory=list)


class SongFork(BaseModel):
    title: str | None = None
    energy: float | None = Field(default=None, ge=1, le=4)
    tags: dict[str, int] | None = None


class SongSearch(BaseModel):
    q: str = Field(min_length=1)
