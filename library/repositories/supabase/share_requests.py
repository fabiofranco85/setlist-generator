"""Supabase share request repository for song sharing workflow."""

from __future__ import annotations

from typing import Any


class SupabaseShareRequestRepository:
    """Repository for managing song share requests via Supabase.

    Share requests flow: editor submits -> system admin reviews -> approve/reject.
    """

    def __init__(self, client: Any, org_id: str):
        self._client = client
        self._org_id = org_id

    def submit(self, song_title: str) -> str:
        """Submit a share request for global visibility.

        The actual song lookup (title -> UUID) is handled by the song repository.
        This method creates the request record assuming the song_id is resolved upstream.
        """
        # Look up song UUID by title
        song_response = (
            self._client.table("songs")
            .select("id")
            .eq("title", song_title)
            .eq("org_id", self._org_id)
            .limit(1)
            .execute()
        )

        if not song_response.data:
            raise KeyError(f"Song '{song_title}' not found in current org")

        song_id = song_response.data[0]["id"]

        response = self._client.table("share_requests").insert({
            "song_id": song_id,
            "org_id": self._org_id,
        }).execute()

        return response.data[0]["id"]

    def list_pending(self) -> list[dict]:
        """List all pending share requests (system admin view)."""
        response = (
            self._client.table("share_requests")
            .select("id, song_id, org_id, requested_by, created_at, "
                    "songs(title), orgs(name)")
            .eq("status", "pending")
            .order("created_at")
            .execute()
        )

        results = []
        for row in response.data:
            song_info = row.get("songs") or {}
            org_info = row.get("orgs") or {}
            results.append({
                "id": row["id"],
                "song_title": song_info.get("title", ""),
                "org_name": org_info.get("name", ""),
                "requested_by": row["requested_by"],
                "created_at": row["created_at"],
            })
        return results

    def approve(self, request_id: str) -> None:
        """Approve a share request, promoting the song to global."""
        # Get the request
        req_response = (
            self._client.table("share_requests")
            .select("id, song_id, status")
            .eq("id", request_id)
            .execute()
        )

        if not req_response.data:
            raise KeyError(f"Share request '{request_id}' not found")

        request = req_response.data[0]
        if request["status"] != "pending":
            raise ValueError(f"Share request is '{request['status']}', not 'pending'")

        # Update song to global visibility + active status
        self._client.table("songs").update({
            "visibility": "global",
            "status": "active",
        }).eq("id", request["song_id"]).execute()

        # Update request status
        self._client.table("share_requests").update({
            "status": "approved",
            "reviewed_at": "now()",
        }).eq("id", request_id).execute()

    def reject(self, request_id: str, reason: str) -> None:
        """Reject a share request."""
        req_response = (
            self._client.table("share_requests")
            .select("id, song_id, status")
            .eq("id", request_id)
            .execute()
        )

        if not req_response.data:
            raise KeyError(f"Share request '{request_id}' not found")

        request = req_response.data[0]
        if request["status"] != "pending":
            raise ValueError(f"Share request is '{request['status']}', not 'pending'")

        # Update song back to active (from pending_review)
        self._client.table("songs").update({
            "status": "rejected",
        }).eq("id", request["song_id"]).execute()

        # Update request status
        self._client.table("share_requests").update({
            "status": "rejected",
            "review_note": reason,
            "reviewed_at": "now()",
        }).eq("id", request_id).execute()
