"""Integration tests for config API endpoints against local Supabase.

Tests cover: reading effective config (system defaults), updating org-specific
overrides, field type validation, and RBAC enforcement.

Fixtures used from conftest.py:
  - ``make_client(user_key)`` — factory returning a ``TestClient`` for a role
  - ``clean_test_data`` — autouse, truncates mutable tables after each test
    (re-seeds system_config, truncates org_config)
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.supabase, pytest.mark.slow]


CONFIG_URL = "/config"

# Expected system defaults (from clean_test_data re-seed)
SYSTEM_DEFAULTS = {
    "moments_config": {
        "prelúdio": 1, "ofertório": 1, "saudação": 1,
        "crianças": 1, "louvor": 4, "poslúdio": 1,
    },
    "recency_decay_days": 45,
    "default_weight": 3,
    "energy_ordering_enabled": True,
    "energy_ordering_rules": {"louvor": "ascending"},
    "default_energy": 2.5,
}


# ── Get Config ───────────────────────────────────────────────────────────────


class TestGetConfig:
    """GET /config"""

    def test_get_default_config(self, make_client):
        """Returns all 6 fields with system default values."""
        client = make_client("viewer")
        resp = client.get(CONFIG_URL)

        assert resp.status_code == 200
        data = resp.json()

        assert data["moments_config"] == SYSTEM_DEFAULTS["moments_config"]
        assert data["recency_decay_days"] == SYSTEM_DEFAULTS["recency_decay_days"]
        assert data["default_weight"] == SYSTEM_DEFAULTS["default_weight"]
        assert data["energy_ordering_enabled"] == SYSTEM_DEFAULTS["energy_ordering_enabled"]
        assert data["energy_ordering_rules"] == SYSTEM_DEFAULTS["energy_ordering_rules"]
        assert data["default_energy"] == SYSTEM_DEFAULTS["default_energy"]

    def test_config_response_types(self, make_client):
        """Verify field types are correct."""
        client = make_client("viewer")
        resp = client.get(CONFIG_URL)

        assert resp.status_code == 200
        data = resp.json()

        assert isinstance(data["moments_config"], dict)
        assert isinstance(data["recency_decay_days"], int)
        assert isinstance(data["default_weight"], int)
        assert isinstance(data["energy_ordering_enabled"], bool)
        assert isinstance(data["energy_ordering_rules"], dict)
        assert isinstance(data["default_energy"], (int, float))


# ── Update Config ────────────────────────────────────────────────────────────


class TestUpdateConfig:
    """PATCH /config"""

    def test_update_single_field(self, make_client):
        """Updating recency_decay_days persists; other fields unchanged."""
        client = make_client("org_admin")
        resp = client.patch(CONFIG_URL, json={"recency_decay_days": 30})

        assert resp.status_code == 200
        data = resp.json()
        assert data["recency_decay_days"] == 30
        # Other fields remain at defaults
        assert data["default_weight"] == SYSTEM_DEFAULTS["default_weight"]
        assert data["energy_ordering_enabled"] == SYSTEM_DEFAULTS["energy_ordering_enabled"]

    def test_update_multiple_fields(self, make_client):
        """Two fields updated in one PATCH."""
        client = make_client("org_admin")
        resp = client.patch(CONFIG_URL, json={
            "recency_decay_days": 60,
            "default_weight": 5,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["recency_decay_days"] == 60
        assert data["default_weight"] == 5

    def test_update_moments_config(self, make_client):
        """Dict field (moments_config) replaced entirely."""
        client = make_client("org_admin")
        new_moments = {"louvor": 5, "prelúdio": 2}
        resp = client.patch(CONFIG_URL, json={"moments_config": new_moments})

        assert resp.status_code == 200
        data = resp.json()
        assert data["moments_config"] == new_moments

    def test_update_persists_across_requests(self, make_client):
        """PATCH then fresh GET reads updated value."""
        admin = make_client("org_admin")
        patch_resp = admin.patch(CONFIG_URL, json={"default_weight": 7})
        assert patch_resp.status_code == 200

        # Fresh client to avoid any in-process caching
        viewer = make_client("viewer")
        get_resp = viewer.get(CONFIG_URL)
        assert get_resp.status_code == 200
        assert get_resp.json()["default_weight"] == 7


# ── RBAC ─────────────────────────────────────────────────────────────────────


def test_editor_cannot_update_config(make_client):
    """Editor PATCH returns 403 (requires org_admin)."""
    client = make_client("editor")
    resp = client.patch(CONFIG_URL, json={"default_weight": 99})

    assert resp.status_code == 403
