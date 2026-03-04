"""Integration tests for event type API endpoints against local Supabase.

Tests cover: listing, getting, creating, updating, and deleting event types,
plus RBAC enforcement (org_admin required for writes).

Fixtures used from conftest.py:
  - ``make_client(user_key)`` — factory returning a ``TestClient`` for a role
  - ``clean_test_data`` — autouse, truncates mutable tables after each test
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


EVENT_TYPES_URL = "/event-types"


def _create_event_type(client, slug="test-type", name="Test Type", moments=None):
    """Helper: create an event type and return the response."""
    payload = {
        "slug": slug,
        "name": name,
        "moments": moments or {"louvor": 3, "prelúdio": 1},
    }
    return client.post(EVENT_TYPES_URL, json=payload)


# ── List ─────────────────────────────────────────────────────────────────────


class TestListEventTypes:
    """GET /event-types"""

    def test_list_empty(self, make_client):
        """Returns empty list when no event types exist."""
        client = make_client("viewer")
        resp = client.get(EVENT_TYPES_URL)

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, make_client):
        """Viewer sees event type created by org_admin."""
        admin = make_client("org_admin")
        create_resp = _create_event_type(admin)
        assert create_resp.status_code == 200

        viewer = make_client("viewer")
        resp = viewer.get(EVENT_TYPES_URL)

        assert resp.status_code == 200
        data = resp.json()
        slugs = {et["slug"] for et in data}
        assert "test-type" in slugs


# ── Get ──────────────────────────────────────────────────────────────────────


class TestGetEventType:
    """GET /event-types/{slug}"""

    def test_get_existing(self, make_client):
        """Returns correct slug, name, and moments for an existing type."""
        admin = make_client("org_admin")
        _create_event_type(admin, slug="youth", name="Youth Service", moments={"louvor": 5})

        viewer = make_client("viewer")
        resp = viewer.get(f"{EVENT_TYPES_URL}/youth")

        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "youth"
        assert data["name"] == "Youth Service"
        assert data["moments"] == {"louvor": 5}

    def test_get_nonexistent_returns_404(self, make_client):
        """404 for unknown slug."""
        client = make_client("viewer")
        resp = client.get(f"{EVENT_TYPES_URL}/nonexistent")

        assert resp.status_code == 404


# ── Create ───────────────────────────────────────────────────────────────────


class TestCreateEventType:
    """POST /event-types"""

    def test_org_admin_can_create(self, make_client):
        """Org admin can create an event type; response matches payload."""
        client = make_client("org_admin")
        resp = _create_event_type(
            client, slug="christmas", name="Christmas Service",
            moments={"louvor": 6, "prelúdio": 2},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "christmas"
        assert data["name"] == "Christmas Service"
        assert data["moments"] == {"louvor": 6, "prelúdio": 2}

    def test_duplicate_slug_returns_422(self, make_client):
        """Creating with the same slug twice returns 422."""
        client = make_client("org_admin")
        first = _create_event_type(client, slug="dup-type")
        assert first.status_code == 200

        second = _create_event_type(client, slug="dup-type")
        assert second.status_code == 422

    def test_invalid_slug_returns_422(self, make_client):
        """Invalid slug (uppercase/special chars) fails Pydantic validation."""
        client = make_client("org_admin")
        resp = client.post(EVENT_TYPES_URL, json={
            "slug": "Invalid!",
            "name": "Bad Slug",
            "moments": {},
        })

        assert resp.status_code == 422

    def test_empty_moments_gets_defaults(self, make_client):
        """Empty moments dict triggers EventType.__post_init__ defaults."""
        client = make_client("org_admin")
        resp = _create_event_type(client, slug="minimal", name="Minimal", moments={})

        assert resp.status_code == 200
        data = resp.json()
        # EventType.__post_init__ fills empty moments with MOMENTS_CONFIG
        assert len(data["moments"]) > 0
        assert "louvor" in data["moments"]


# ── Update ───────────────────────────────────────────────────────────────────


class TestUpdateEventType:
    """PATCH /event-types/{slug}"""

    def test_update_name_and_moments(self, make_client):
        """PATCH changes name and moments fields."""
        client = make_client("org_admin")
        _create_event_type(client, slug="updatable", name="Old Name", moments={"louvor": 2})

        resp = client.patch(f"{EVENT_TYPES_URL}/updatable", json={
            "name": "New Name",
            "moments": {"louvor": 5, "ofertório": 1},
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["moments"] == {"louvor": 5, "ofertório": 1}

    def test_update_nonexistent_returns_404(self, make_client):
        """Updating a non-existent slug returns 404."""
        client = make_client("org_admin")
        resp = client.patch(f"{EVENT_TYPES_URL}/ghost", json={"name": "Ghost"})

        assert resp.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────


class TestDeleteEventType:
    """DELETE /event-types/{slug}"""

    def test_delete_existing(self, make_client):
        """Deleting an event type returns 200; subsequent GET returns 404."""
        client = make_client("org_admin")
        _create_event_type(client, slug="doomed", name="Doomed Type")

        resp = client.delete(f"{EVENT_TYPES_URL}/doomed")
        assert resp.status_code == 200

        # Verify it's gone
        get_resp = client.get(f"{EVENT_TYPES_URL}/doomed")
        assert get_resp.status_code == 404

    def test_delete_default_returns_422(self, make_client):
        """Cannot delete the default event type ('main')."""
        client = make_client("org_admin")

        # First create 'main' so it exists
        _create_event_type(client, slug="main", name="Main Service")

        resp = client.delete(f"{EVENT_TYPES_URL}/main")
        assert resp.status_code == 422


# ── RBAC ─────────────────────────────────────────────────────────────────────


def test_editor_cannot_crud_event_types(make_client):
    """Editor gets 403 on POST (create requires org_admin)."""
    client = make_client("editor")
    resp = client.post(EVENT_TYPES_URL, json={
        "slug": "denied",
        "name": "Denied Type",
        "moments": {},
    })

    assert resp.status_code == 403
