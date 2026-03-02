"""Unit tests for EventType moments_order and ordered_moments (Problem 1).

These tests verify that:
- moments_order defaults to dict key order
- ordered_moments returns moments in the user-specified order
- round-trip through load/save preserves ordering
"""

import json

from library.config import MOMENTS_CONFIG
from library.event_type import (
    EventType,
    create_default_event_types,
    load_event_types,
    save_event_types,
)


class TestMomentsOrderField:
    """Tests for the moments_order field on EventType."""

    def test_defaults_from_moments_keys(self):
        et = EventType(slug="test", name="Test", moments={"louvor": 3, "final": 1})
        assert et.moments_order == ["louvor", "final"]

    def test_defaults_from_moments_config_when_empty(self):
        et = EventType(slug="test", name="Test")
        assert et.moments_order == list(MOMENTS_CONFIG.keys())

    def test_explicit_order_preserved(self):
        et = EventType(
            slug="test", name="Test",
            moments={"final": 1, "louvor": 3},
            moments_order=["louvor", "final"],
        )
        assert et.moments_order == ["louvor", "final"]

    def test_empty_list_defaults_to_moments_keys(self):
        et = EventType(
            slug="test", name="Test",
            moments={"louvor": 3, "final": 1},
            moments_order=[],
        )
        assert et.moments_order == ["louvor", "final"]


class TestOrderedMoments:
    """Tests for the ordered_moments property."""

    def test_returns_moments_in_order(self):
        et = EventType(
            slug="test", name="Test",
            moments={"final": 1, "louvor": 3},
            moments_order=["louvor", "final"],
        )
        keys = list(et.ordered_moments.keys())
        assert keys == ["louvor", "final"]

    def test_preserves_values(self):
        et = EventType(
            slug="test", name="Test",
            moments={"final": 1, "louvor": 3},
            moments_order=["louvor", "final"],
        )
        assert et.ordered_moments == {"louvor": 3, "final": 1}

    def test_handles_extra_keys_in_moments(self):
        """Keys in moments but not in moments_order are appended."""
        et = EventType(
            slug="test", name="Test",
            moments={"louvor": 3, "final": 1, "extra": 2},
            moments_order=["louvor", "final"],
        )
        keys = list(et.ordered_moments.keys())
        assert keys == ["louvor", "final", "extra"]

    def test_handles_stale_keys_in_order(self):
        """Keys in moments_order that aren't in moments are skipped."""
        et = EventType(
            slug="test", name="Test",
            moments={"louvor": 3},
            moments_order=["louvor", "removed"],
        )
        keys = list(et.ordered_moments.keys())
        assert keys == ["louvor"]

    def test_default_event_type_preserves_config_order(self):
        et = EventType(slug="main", name="Main")
        expected_keys = list(MOMENTS_CONFIG.keys())
        assert list(et.ordered_moments.keys()) == expected_keys


class TestSaveLoadPreservesOrder:
    """Test that save/load round-trip preserves moments_order."""

    def test_round_trip_preserves_custom_order(self, tmp_path):
        path = tmp_path / "event_types.json"
        data = create_default_event_types()
        data["custom"] = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 3, "final": 1},
            moments_order=["louvor", "final"],
        )
        save_event_types(data, path)

        loaded = load_event_types(path)
        assert loaded["custom"].moments_order == ["louvor", "final"]
        assert list(loaded["custom"].ordered_moments.keys()) == ["louvor", "final"]

    def test_load_missing_moments_order_defaults(self, tmp_path):
        """Backward compat: old JSON without moments_order derives from dict."""
        path = tmp_path / "event_types.json"
        path.write_text(json.dumps({
            "event_types": {
                "old": {
                    "name": "Old Type",
                    "description": "",
                    "moments": {"louvor": 3, "final": 1},
                    # No moments_order key
                }
            }
        }))

        loaded = load_event_types(path)
        # Should default from moments dict key order
        assert loaded["old"].moments_order == ["louvor", "final"]

    def test_save_includes_moments_order_in_json(self, tmp_path):
        path = tmp_path / "event_types.json"
        data = {
            "custom": EventType(
                slug="custom", name="Custom",
                moments={"final": 1, "louvor": 3},
                moments_order=["louvor", "final"],
            ),
        }
        save_event_types(data, path)

        raw = json.loads(path.read_text())
        assert raw["event_types"]["custom"]["moments_order"] == ["louvor", "final"]
