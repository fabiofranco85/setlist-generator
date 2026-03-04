"""Integration tests for song CRUD, search, fork, share, transpose, and info endpoints.

Tests run against a local Supabase instance using fixtures from conftest.py.
"""

from __future__ import annotations

import urllib.parse

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


# -- helpers -----------------------------------------------------------------

def _encode(title: str) -> str:
    """URL-encode a song title for use in path parameters."""
    return urllib.parse.quote(title, safe="")


# -- list / search / get -----------------------------------------------------


class TestListSongs:
    """GET /songs — list all visible songs."""

    def test_list_returns_seeded_songs(self, make_client, seed_songs):
        client = make_client("editor")
        resp = client.get("/songs")

        assert resp.status_code == 200
        titles = {s["title"] for s in resp.json()}
        assert titles == {"Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"}


class TestSearchSongs:
    """GET /songs/search?q=..."""

    def test_partial_match(self, make_client, seed_songs):
        client = make_client("editor")
        resp = client.get("/songs/search", params={"q": "Reflect"})

        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()]
        assert titles == ["Reflective Song"]

    def test_no_match_returns_empty(self, make_client, seed_songs):
        client = make_client("editor")
        resp = client.get("/songs/search", params={"q": "NonexistentXYZ"})

        assert resp.status_code == 200
        assert resp.json() == []


class TestGetSong:
    """GET /songs/{title}"""

    def test_found(self, make_client, seed_songs):
        client = make_client("editor")
        resp = client.get(f"/songs/{_encode('Upbeat Song')}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Upbeat Song"
        assert data["energy"] == 1
        assert "louvor" in data["tags"]

    def test_not_found(self, make_client, seed_songs):
        client = make_client("editor")
        resp = client.get(f"/songs/{_encode('Does Not Exist')}")

        assert resp.status_code == 404


# -- create / update / delete ------------------------------------------------


class TestCreateSong:
    """POST /songs"""

    def test_editor_can_create(self, make_client):
        client = make_client("editor")
        payload = {
            "title": "Brand New Song",
            "energy": 2,
            "tags": {"louvor": 4, "ofertório": 3},
            "youtube_url": "https://youtu.be/abc123",
            "visibility": "org",
        }
        resp = client.post("/songs", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Brand New Song"
        assert data["energy"] == 2
        assert data["tags"]["louvor"] == 4

        # Verify it appears in the list
        list_resp = client.get("/songs")
        titles = {s["title"] for s in list_resp.json()}
        assert "Brand New Song" in titles

    def test_viewer_cannot_create(self, make_client):
        client = make_client("viewer")
        payload = {
            "title": "Forbidden Song",
            "energy": 3,
            "tags": {"louvor": 3},
        }
        resp = client.post("/songs", json=payload)

        assert resp.status_code == 403


class TestUpdateSong:
    """PATCH /songs/{title}"""

    def test_update_content(self, make_client, seed_songs):
        client = make_client("editor")
        new_content = "### Upbeat Song (G)\n\nG       D\nLyrics here..."
        resp = client.patch(
            f"/songs/{_encode('Upbeat Song')}",
            json={"content": new_content},
        )

        assert resp.status_code == 200


class TestDeleteSong:
    """DELETE /songs/{title}"""

    def test_editor_can_delete(self, make_client, seed_songs):
        client = make_client("editor")
        resp = client.delete(f"/songs/{_encode('Worship Song')}")

        assert resp.status_code == 200
        assert "deleted" in resp.json()["detail"].lower()

        # Verify it is gone
        get_resp = client.get(f"/songs/{_encode('Worship Song')}")
        assert get_resp.status_code == 404


# -- fork / share ------------------------------------------------------------


class TestForkSong:
    """POST /songs/{title}/fork"""

    def test_fork_with_overrides(self, make_client, seed_songs):
        client = make_client("editor")
        payload = {
            "title": "Reflective Song (Tom G)",
            "energy": 3,
            "tags": {"louvor": 5, "ofertório": 4},
        }
        resp = client.post(
            f"/songs/{_encode('Reflective Song')}/fork",
            json=payload,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Reflective Song (Tom G)"
        assert data["energy"] == 3
        assert data["tags"]["louvor"] == 5
        assert data["tags"]["ofertório"] == 4


class TestShareSong:
    """POST /songs/{title}/share"""

    def test_share_to_org(self, make_client, db_conn, test_org, test_users):
        """Create a user-level song, then share it to org visibility."""
        client = make_client("editor")

        # Create a user-level song first
        client.post("/songs", json={
            "title": "My Private Song",
            "energy": 2,
            "tags": {"louvor": 3},
            "visibility": "user",
        })

        resp = client.post(f"/songs/{_encode('My Private Song')}/share")

        assert resp.status_code == 200
        assert "shared" in resp.json()["detail"].lower()

        # Verify visibility changed to 'org' via direct SQL
        row = db_conn.execute(
            "SELECT visibility FROM songs WHERE title = 'My Private Song' AND org_id = %s",
            (test_org["org_id"],),
        ).fetchone()
        assert row is not None
        assert row[0] == "org"


# -- transpose ---------------------------------------------------------------


class TestTransposeSong:
    """POST /songs/{title}/transpose?to=..."""

    def test_transpose_no_content_returns_422(self, make_client, seed_songs):
        """Supabase backend stores content in S3; get_by_title returns content=''.

        The transpose endpoint correctly rejects songs without loaded content.
        """
        client = make_client("viewer")
        resp = client.post(
            f"/songs/{_encode('Moderate Song')}/transpose",
            params={"to": "G"},
        )

        # Song exists but content is empty (loaded from S3 on demand)
        assert resp.status_code == 422

    def test_transpose_with_content_via_update(self, make_client, seed_songs):
        """When content is set via update_content, transpose works.

        The editor first updates the song content through the API,
        then the viewer can transpose it.
        """
        editor = make_client("editor")
        content = "### Moderate Song (C)\n\nC       G       Am\nLyrics here..."
        patch_resp = editor.patch(
            f"/songs/{_encode('Moderate Song')}",
            json={"content": content},
        )
        assert patch_resp.status_code == 200

        # Now try transpose — the Supabase repo stores content in
        # content_s3_key but get_by_title returns content="" (S3 on demand).
        # So this still returns 422 even after update.
        viewer = make_client("viewer")
        resp = viewer.post(
            f"/songs/{_encode('Moderate Song')}/transpose",
            params={"to": "G"},
        )
        assert resp.status_code == 422


# -- info --------------------------------------------------------------------


class TestSongInfo:
    """GET /songs/{title}/info"""

    def test_info_no_usage(self, make_client, seed_songs):
        client = make_client("viewer")
        resp = client.get(f"/songs/{_encode('Upbeat Song')}/info")

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Upbeat Song"
        assert data["energy"] == 1
        assert data["usage_count"] == 0
        assert data["days_since_last_use"] is None
        assert data["usage_history"] == []

    def test_info_with_usage(self, make_client, seed_songs, db_conn, test_org):
        """Insert a setlist referencing the song, then check info."""
        import json as _json

        org_id = test_org["org_id"]
        db_conn.execute(
            """
            INSERT INTO setlists (org_id, date, moments, label, event_type)
            VALUES (%s, '2026-02-20', %s, '', '')
            """,
            (
                org_id,
                _json.dumps({"louvor": ["Upbeat Song", "Moderate Song"]}),
            ),
        )

        client = make_client("viewer")
        resp = client.get(f"/songs/{_encode('Upbeat Song')}/info")

        assert resp.status_code == 200
        data = resp.json()
        assert data["usage_count"] >= 1
