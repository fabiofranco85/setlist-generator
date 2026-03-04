"""RBAC integration tests for the Songbook API.

Tests role-based access control against a local Supabase instance.  Each test
verifies that a specific role is allowed or denied access to an endpoint.

Fixtures used from conftest.py:
  - ``make_client(user_key)`` — factory returning a ``TestClient`` for a role
  - ``seed_songs`` — inserts 4 org-scoped songs with louvor tags
  - ``test_org`` — dict with ``org_id`` and ``other_org_id``
  - ``test_users`` — dict with user dicts (``id``, ``email``)
  - ``clean_test_data`` — autouse, truncates mutable tables after each test
  - ``db_conn`` — raw psycopg connection for direct SQL
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


# ── helpers ────────────────────────────────────────────────────────────────

SONG_CREATE_BODY = {
    "title": "RBAC Test Song",
    "energy": 2,
    "tags": {"louvor": 3},
}

GENERATE_BODY = {
    "date": "2026-06-01",
}

EVENT_TYPE_CREATE_BODY = {
    "slug": "test-type",
    "name": "Test Type",
    "moments": {"louvor": 2},
}


# ── 1. Viewer can list songs ──────────────────────────────────────────────


def test_viewer_can_list_songs(make_client, seed_songs):
    """Viewer role has read access to the songs endpoint."""
    client = make_client("viewer")
    resp = client.get("/songs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4  # seed_songs inserts 4


# ── 2. Viewer cannot create song ──────────────────────────────────────────


def test_viewer_cannot_create_song(make_client):
    """Viewer role is denied write access (POST /songs requires editor+)."""
    client = make_client("viewer")
    resp = client.post("/songs", json=SONG_CREATE_BODY)
    assert resp.status_code == 403


# ── 3. Viewer cannot generate setlist ─────────────────────────────────────


def test_viewer_cannot_generate_setlist(make_client, seed_songs):
    """Viewer role is denied setlist generation (requires editor+)."""
    client = make_client("viewer")
    resp = client.post("/setlists/generate", json=GENERATE_BODY)
    assert resp.status_code == 403


# ── 4. Editor can create song ─────────────────────────────────────────────


def test_editor_can_create_song(make_client):
    """Editor role has write access to create songs."""
    client = make_client("editor")
    resp = client.post("/songs", json=SONG_CREATE_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == SONG_CREATE_BODY["title"]
    assert data["energy"] == SONG_CREATE_BODY["energy"]


# ── 5. Editor cannot create event type ────────────────────────────────────


def test_editor_cannot_create_event_type(make_client):
    """Editor role is denied event type management (requires org_admin)."""
    client = make_client("editor")
    resp = client.post("/event-types", json=EVENT_TYPE_CREATE_BODY)
    assert resp.status_code == 403


# ── 6. Org admin can create event type ────────────────────────────────────


def test_org_admin_can_create_event_type(make_client):
    """Org admin role can manage event types."""
    client = make_client("org_admin")
    resp = client.post("/event-types", json=EVENT_TYPE_CREATE_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == EVENT_TYPE_CREATE_BODY["slug"]
    assert data["name"] == EVENT_TYPE_CREATE_BODY["name"]
    assert data["moments"] == EVENT_TYPE_CREATE_BODY["moments"]


# ── 7. System admin can access admin endpoint ─────────────────────────────


def test_system_admin_can_access_admin_songs(make_client, seed_songs):
    """System admin can access /admin/songs/global (requires system_admin)."""
    client = make_client("system_admin")
    resp = client.get("/admin/songs/global")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── 8. Editor cannot access admin endpoint ────────────────────────────────


def test_editor_cannot_access_admin_songs(make_client):
    """Editor role is denied access to admin endpoints."""
    client = make_client("editor")
    resp = client.get("/admin/songs/global")
    assert resp.status_code == 403


# ── 9. System admin bypasses role checks ──────────────────────────────────


def test_system_admin_bypasses_role_checks(make_client):
    """System admin can create songs even though the check is for editor/org_admin.

    The ``require_role`` dependency short-circuits for system admins by
    checking ``repos.users.is_system_admin()`` before the role comparison.
    """
    client = make_client("system_admin")
    body = {
        "title": "SysAdmin Song",
        "energy": 3,
        "tags": {"louvor": 4},
    }
    resp = client.post("/songs", json=body)
    assert resp.status_code == 200
    assert resp.json()["title"] == "SysAdmin Song"


# ── 10. Other org user cannot see primary org's songs ─────────────────────


@pytest.mark.xfail(
    reason=(
        "Org isolation relies on Supabase RLS (current_setting('app.org_id')). "
        "Tests use service_role key which bypasses RLS, so org-scoped filtering "
        "does not apply. True org isolation tests require JWT-based auth or "
        "a PostgREST configuration that sets app.org_id from a custom header."
    ),
    strict=True,
)
def test_other_org_user_cannot_see_primary_org_songs(
    make_client, seed_songs, test_org
):
    """Editor in another org sees no songs when scoped to the primary org.

    Songs are created with ``visibility='org'`` in the primary org.  The
    ``other_org_user`` is an editor in a *different* org.  When we
    explicitly pass the primary ``org_id``, data isolation via the
    repository layer should return an empty list because the user has no
    membership in the primary org.

    NOTE: This test is expected to fail because service_role bypasses RLS.
    The SupabaseSongRepository.get_effective_library() relies on RLS for
    org filtering — it does not add an explicit ``.eq("org_id", ...)``
    clause.  With service_role, all active songs are returned regardless
    of org.
    """
    client = make_client("other_org_user", org_id=test_org["org_id"])
    resp = client.get("/songs")
    assert resp.status_code == 200
    data = resp.json()
    # other_org_user should not see primary org's org-scoped songs
    assert len(data) == 0
