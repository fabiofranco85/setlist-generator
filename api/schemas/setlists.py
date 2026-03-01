"""Setlist schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    overrides: dict[str, list[str]] | None = None
    label: str = ""
    event_type: str = ""
    include_pdf: bool = False


class SetlistResponse(BaseModel):
    date: str
    moments: dict[str, list[str]]
    label: str = ""
    event_type: str = ""


class ReplaceRequest(BaseModel):
    moment: str
    position: int = Field(ge=0)
    song: str | None = None  # None = auto-select


class DeriveRequest(BaseModel):
    label: str
    replace_count: int | None = None  # None = random


class SetlistListParams(BaseModel):
    label: str | None = None
    event_type: str | None = None
