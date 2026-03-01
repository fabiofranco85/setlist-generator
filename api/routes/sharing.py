"""Song sharing workflow endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from library.repositories import RepositoryContainer

from ..deps import get_repos, require_role, require_system_admin
from ..schemas.sharing import ShareReview, ShareRequestResponse

router = APIRouter()


@router.post("/request/{title}", dependencies=[Depends(require_role("editor", "org_admin"))])
async def request_global_share(title: str, repos: RepositoryContainer = Depends(get_repos)):
    """Submit a request to promote a song to global visibility."""
    if not hasattr(repos, "share_requests") or not repos.share_requests:
        raise ValueError("Share requests not supported by this backend")

    request_id = await asyncio.to_thread(repos.share_requests.submit, title)
    return {"request_id": request_id, "detail": f"Share request submitted for '{title}'"}


@router.get("/pending", response_model=list[ShareRequestResponse], dependencies=[Depends(require_system_admin())])
async def list_pending(repos: RepositoryContainer = Depends(get_repos)):
    """List all pending share requests (system admin only)."""
    if not hasattr(repos, "share_requests") or not repos.share_requests:
        return []

    requests = await asyncio.to_thread(repos.share_requests.list_pending)
    return [
        ShareRequestResponse(**r)
        for r in requests
    ]


@router.post("/{request_id}/review", dependencies=[Depends(require_system_admin())])
async def review_request(
    request_id: str,
    data: ShareReview,
    repos: RepositoryContainer = Depends(get_repos),
):
    """Approve or reject a share request (system admin only)."""
    if not hasattr(repos, "share_requests") or not repos.share_requests:
        raise ValueError("Share requests not supported by this backend")

    if data.approve:
        await asyncio.to_thread(repos.share_requests.approve, request_id)
        return {"detail": f"Share request {request_id} approved"}
    else:
        await asyncio.to_thread(repos.share_requests.reject, request_id, data.reason)
        return {"detail": f"Share request {request_id} rejected"}
