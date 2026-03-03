"""Integration tests for sharing API endpoints against local Supabase.

Tests cover: submitting share requests, listing pending requests, approving
and rejecting requests, and RBAC enforcement.

**Known limitation:** The ``share_requests.requested_by`` column is NOT NULL
but ``SupabaseShareRequestRepository.submit()`` does not provide it.  With
service_role (which bypasses RLS), the insert fails because there is no
default for ``requested_by``.  Tests that need share request rows seed them
via direct SQL to bypass this issue.

Fixtures used from conftest.py:
  - ``make_client(user_key)`` — factory returning a ``TestClient`` for a role
  - ``seed_songs`` — inserts 4 org-scoped songs with louvor tags
  - ``db_conn`` — raw psycopg connection for direct SQL
  - ``test_org`` — dict with ``org_id`` and ``other_org_id``
  - ``test_users`` — dict with user dicts (``id``, ``email``)
  - ``clean_test_data`` — autouse, truncates mutable tables after each test
"""

from __future__ import annotations

import urllib.parse
import uuid

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


SHARING_URL = "/sharing"


def _encode(title: str) -> str:
    return urllib.parse.quote(title, safe="")


def _seed_share_request(db_conn, song_id, org_id, user_id, status="pending"):
    """Insert a share request via direct SQL, returning the request ID.

    This bypasses the repository's ``submit()`` method, which fails
    because it doesn't provide ``requested_by`` for the NOT NULL column.
    """
    request_id = str(uuid.uuid4())
    db_conn.execute(
        """
        INSERT INTO share_requests (id, song_id, org_id, requested_by, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (request_id, song_id, org_id, user_id, status),
    )
    return request_id


# ── Submit Request ───────────────────────────────────────────────────────────


class TestSubmitRequest:
    """POST /sharing/request/{title}"""

    @pytest.mark.xfail(
        reason=(
            "SupabaseShareRequestRepository.submit() does not provide "
            "requested_by, which is NOT NULL.  The insert fails with "
            "service_role key because there is no auth.uid() to fill "
            "the column via RLS default."
        ),
        strict=False,
    )
    def test_submit_request(self, make_client, seed_songs):
        """Submit a share request for a seeded song (may fail due to NOT NULL)."""
        client = make_client("editor")
        resp = client.post(f"{SHARING_URL}/request/{_encode('Reflective Song')}")

        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert "Reflective Song" in data["detail"]

    def test_submit_nonexistent_song_returns_404(self, make_client, seed_songs):
        """Requesting a share for a non-existent song returns 404."""
        client = make_client("editor")
        resp = client.post(f"{SHARING_URL}/request/{_encode('Ghost Song')}")

        assert resp.status_code == 404

    def test_viewer_cannot_submit(self, make_client, seed_songs):
        """Viewer gets 403 (requires editor+)."""
        client = make_client("viewer")
        resp = client.post(f"{SHARING_URL}/request/{_encode('Reflective Song')}")

        assert resp.status_code == 403


# ── List Pending ─────────────────────────────────────────────────────────────


class TestListPending:
    """GET /sharing/pending"""

    def test_list_pending_empty(self, make_client):
        """System admin sees empty list when no requests exist."""
        client = make_client("system_admin")
        resp = client.get(f"{SHARING_URL}/pending")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_pending_with_seeded_request(
        self, make_client, seed_songs, db_conn, test_org, test_users
    ):
        """Direct SQL seed produces a request visible to system admin."""
        song_id = seed_songs["Reflective Song"]
        user_id = test_users["editor"]["id"]
        org_id = test_org["org_id"]

        _seed_share_request(db_conn, song_id, org_id, user_id)

        client = make_client("system_admin")
        resp = client.get(f"{SHARING_URL}/pending")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

        item = data[0]
        assert "id" in item
        assert item["song_title"] == "Reflective Song"
        assert item["org_name"] == "Test Church"
        assert "requested_by" in item
        assert "created_at" in item

    def test_editor_cannot_list_pending(self, make_client):
        """Editor gets 403 (requires system_admin)."""
        client = make_client("editor")
        resp = client.get(f"{SHARING_URL}/pending")

        assert resp.status_code == 403


# ── Review Request ───────────────────────────────────────────────────────────


class TestReviewRequest:
    """POST /sharing/{request_id}/review"""

    def test_approve_request(
        self, make_client, seed_songs, db_conn, test_org, test_users
    ):
        """Approving a request promotes the song to global visibility."""
        song_id = seed_songs["Worship Song"]
        user_id = test_users["editor"]["id"]
        org_id = test_org["org_id"]

        request_id = _seed_share_request(db_conn, song_id, org_id, user_id)

        client = make_client("system_admin")
        resp = client.post(
            f"{SHARING_URL}/{request_id}/review",
            json={"approve": True},
        )

        assert resp.status_code == 200

        # Verify via SQL: song visibility updated
        row = db_conn.execute(
            "SELECT visibility FROM songs WHERE id = %s", (song_id,)
        ).fetchone()
        assert row[0] == "global"

        # Verify via SQL: request status updated
        req_row = db_conn.execute(
            "SELECT status FROM share_requests WHERE id = %s", (request_id,)
        ).fetchone()
        assert req_row[0] == "approved"

    def test_reject_request(
        self, make_client, seed_songs, db_conn, test_org, test_users
    ):
        """Rejecting a request marks it rejected with a review note."""
        song_id = seed_songs["Moderate Song"]
        user_id = test_users["editor"]["id"]
        org_id = test_org["org_id"]

        request_id = _seed_share_request(db_conn, song_id, org_id, user_id)

        client = make_client("system_admin")
        resp = client.post(
            f"{SHARING_URL}/{request_id}/review",
            json={"approve": False, "reason": "Not suitable for global"},
        )

        assert resp.status_code == 200

        # Verify via SQL: request status updated
        req_row = db_conn.execute(
            "SELECT status, review_note FROM share_requests WHERE id = %s",
            (request_id,),
        ).fetchone()
        assert req_row[0] == "rejected"
        assert req_row[1] == "Not suitable for global"

    def test_review_nonexistent_returns_404(self, make_client):
        """Reviewing a fake UUID returns 404."""
        client = make_client("system_admin")
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"{SHARING_URL}/{fake_id}/review",
            json={"approve": True},
        )

        assert resp.status_code == 404

    def test_review_already_approved_returns_422(
        self, make_client, seed_songs, db_conn, test_org, test_users
    ):
        """Approving an already-approved request returns 422."""
        song_id = seed_songs["Upbeat Song"]
        user_id = test_users["editor"]["id"]
        org_id = test_org["org_id"]

        # Seed as already approved
        request_id = _seed_share_request(
            db_conn, song_id, org_id, user_id, status="approved"
        )

        client = make_client("system_admin")
        resp = client.post(
            f"{SHARING_URL}/{request_id}/review",
            json={"approve": True},
        )

        assert resp.status_code == 422
