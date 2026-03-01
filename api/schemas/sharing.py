"""Sharing schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel


class ShareRequest(BaseModel):
    scope: str = "org"  # "org" or "global"


class ShareReview(BaseModel):
    approve: bool
    reason: str = ""


class ShareRequestResponse(BaseModel):
    id: str
    song_title: str
    org_name: str
    requested_by: str
    created_at: str
