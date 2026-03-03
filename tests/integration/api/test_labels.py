"""Integration tests for label management API endpoints against local Supabase.

Tests cover: adding, renaming, and removing labels on setlists, error cases
for duplicate/missing labels, and RBAC enforcement.

Fixtures used from conftest.py:
  - ``make_client(user_key)`` — factory returning a ``TestClient`` for a role
  - ``seed_songs`` — inserts 4 org-scoped songs with louvor tags
  - ``clean_test_data`` — autouse, truncates mutable tables after each test
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


LABELS_URL = "/labels"
SETLISTS_URL = "/setlists"
TEST_DATE = "2099-12-25"


def _generate_base_setlist(client, date=TEST_DATE):
    """Generate a base (unlabeled) setlist with overrides for all moments.

    Uses overrides to ensure success with the limited 4-song seed pool.
    """
    overrides = {
        "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
        "prelúdio": ["Upbeat Song"],
        "saudação": ["Moderate Song"],
        "ofertório": ["Reflective Song"],
        "poslúdio": ["Worship Song"],
        "crianças": ["Upbeat Song"],
    }
    resp = client.post("/setlists/generate", json={
        "date": date,
        "overrides": overrides,
    })
    assert resp.status_code == 200, resp.text
    return resp


# ── Add Label ────────────────────────────────────────────────────────────────


class TestAddLabel:
    """POST /labels?date=...&label=..."""

    def test_add_label(self, make_client, seed_songs):
        """Adding a label creates a labeled copy with moments."""
        client = make_client("editor")
        _generate_base_setlist(client)

        resp = client.post(LABELS_URL, params={"date": TEST_DATE, "label": "evening"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "evening"
        assert data["date"] == TEST_DATE
        assert isinstance(data["moments"], dict)
        assert "louvor" in data["moments"]

    def test_base_not_found_returns_404(self, make_client, seed_songs):
        """Adding a label when no base setlist exists returns 404."""
        client = make_client("editor")
        resp = client.post(LABELS_URL, params={"date": "1900-01-01", "label": "evening"})

        assert resp.status_code == 404

    def test_duplicate_label_returns_422(self, make_client, seed_songs):
        """Adding the same label twice returns 422."""
        client = make_client("editor")
        _generate_base_setlist(client)

        first = client.post(LABELS_URL, params={"date": TEST_DATE, "label": "morning"})
        assert first.status_code == 200

        second = client.post(LABELS_URL, params={"date": TEST_DATE, "label": "morning"})
        assert second.status_code == 422

    def test_labeled_retrievable_via_get(self, make_client, seed_songs):
        """Labeled setlist is retrievable via GET /setlists/{date}?label=..."""
        client = make_client("editor")
        _generate_base_setlist(client)
        client.post(LABELS_URL, params={"date": TEST_DATE, "label": "afternoon"})

        resp = client.get(f"{SETLISTS_URL}/{TEST_DATE}", params={"label": "afternoon"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "afternoon"
        assert data["date"] == TEST_DATE


# ── Rename Label ─────────────────────────────────────────────────────────────


class TestRenameLabel:
    """PATCH /labels/{label}?date=...&new_label=..."""

    def test_rename_label(self, make_client, seed_songs):
        """Renaming moves the label: old returns 404, new returns 200."""
        client = make_client("editor")
        _generate_base_setlist(client)
        client.post(LABELS_URL, params={"date": TEST_DATE, "label": "old-name"})

        resp = client.patch(
            f"{LABELS_URL}/old-name",
            params={"date": TEST_DATE, "new_label": "new-name"},
        )

        assert resp.status_code == 200
        assert resp.json()["label"] == "new-name"

        # Old label is gone
        old_resp = client.get(
            f"{SETLISTS_URL}/{TEST_DATE}", params={"label": "old-name"}
        )
        assert old_resp.status_code == 404

        # New label is accessible
        new_resp = client.get(
            f"{SETLISTS_URL}/{TEST_DATE}", params={"label": "new-name"}
        )
        assert new_resp.status_code == 200

    def test_rename_nonexistent_returns_404(self, make_client, seed_songs):
        """Renaming a non-existent label returns 404."""
        client = make_client("editor")
        _generate_base_setlist(client)

        resp = client.patch(
            f"{LABELS_URL}/ghost",
            params={"date": TEST_DATE, "new_label": "new"},
        )

        assert resp.status_code == 404

    def test_rename_to_existing_returns_422(self, make_client, seed_songs):
        """Renaming to an already-used label returns 422."""
        client = make_client("editor")
        _generate_base_setlist(client)
        client.post(LABELS_URL, params={"date": TEST_DATE, "label": "alpha"})
        client.post(LABELS_URL, params={"date": TEST_DATE, "label": "beta"})

        resp = client.patch(
            f"{LABELS_URL}/alpha",
            params={"date": TEST_DATE, "new_label": "beta"},
        )

        assert resp.status_code == 422


# ── Remove Label ─────────────────────────────────────────────────────────────


class TestRemoveLabel:
    """DELETE /labels/{label}?date=..."""

    def test_remove_label(self, make_client, seed_songs):
        """Removing a label returns 200; subsequent GET returns 404."""
        client = make_client("editor")
        _generate_base_setlist(client)
        client.post(LABELS_URL, params={"date": TEST_DATE, "label": "removable"})

        resp = client.delete(
            f"{LABELS_URL}/removable", params={"date": TEST_DATE}
        )
        assert resp.status_code == 200

        get_resp = client.get(
            f"{SETLISTS_URL}/{TEST_DATE}", params={"label": "removable"}
        )
        assert get_resp.status_code == 404

    def test_remove_nonexistent_returns_404(self, make_client, seed_songs):
        """Removing a non-existent label returns 404."""
        client = make_client("editor")
        _generate_base_setlist(client)

        resp = client.delete(
            f"{LABELS_URL}/ghost", params={"date": TEST_DATE}
        )

        assert resp.status_code == 404


# ── RBAC ─────────────────────────────────────────────────────────────────────


def test_viewer_cannot_add_label(make_client, seed_songs):
    """Viewer gets 403 (label add requires editor+)."""
    # Generate base with editor first
    editor = make_client("editor")
    _generate_base_setlist(editor)

    viewer = make_client("viewer")
    resp = viewer.post(LABELS_URL, params={"date": TEST_DATE, "label": "blocked"})

    assert resp.status_code == 403
