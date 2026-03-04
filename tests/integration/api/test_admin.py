"""Integration tests for admin API endpoints against local Supabase.

Tests cover: listing global songs, response shape, empty state, and
visibility of newly created songs.

Fixtures used from conftest.py:
  - ``make_client(user_key)`` — factory returning a ``TestClient`` for a role
  - ``seed_songs`` — inserts 4 org-scoped songs with louvor tags
  - ``clean_test_data`` — autouse, truncates mutable tables after each test
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


ADMIN_SONGS_URL = "/admin/songs/global"


class TestListGlobalSongs:
    """GET /admin/songs/global"""

    def test_returns_seeded_songs(self, make_client, seed_songs):
        """System admin sees all 4 seed songs via the admin endpoint."""
        client = make_client("system_admin")
        resp = client.get(ADMIN_SONGS_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        titles = {s["title"] for s in data}
        assert titles >= {"Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"}

    def test_response_shape(self, make_client, seed_songs):
        """Each item has title (str), energy (int), and tags (dict)."""
        client = make_client("system_admin")
        resp = client.get(ADMIN_SONGS_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

        for item in data:
            assert isinstance(item["title"], str)
            assert isinstance(item["energy"], int)
            assert isinstance(item["tags"], dict)
            # Should only have these three keys
            assert set(item.keys()) == {"title", "energy", "tags"}

    def test_empty_when_no_songs(self, make_client):
        """Returns empty list when no songs exist (no seed_songs fixture)."""
        client = make_client("system_admin")
        resp = client.get(ADMIN_SONGS_URL)

        assert resp.status_code == 200
        assert resp.json() == []

    def test_includes_newly_created_song(self, make_client, seed_songs):
        """A song created by an editor is visible to system admin."""
        editor_client = make_client("editor")
        create_resp = editor_client.post("/songs", json={
            "title": "Admin Visible Song",
            "energy": 2,
            "tags": {"louvor": 3},
        })
        assert create_resp.status_code == 200

        admin_client = make_client("system_admin")
        resp = admin_client.get(ADMIN_SONGS_URL)

        assert resp.status_code == 200
        titles = {s["title"] for s in resp.json()}
        assert "Admin Visible Song" in titles
