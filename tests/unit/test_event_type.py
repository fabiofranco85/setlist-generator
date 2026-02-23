"""Unit tests for event type module."""

import pytest

from library.event_type import (
    EventType,
    DEFAULT_EVENT_TYPE_SLUG,
    DEFAULT_EVENT_TYPE_NAME,
    validate_event_type_slug,
    is_default_event_type,
    filter_songs_for_event_type,
    load_event_types,
    save_event_types,
    create_default_event_types,
)
from library.config import MOMENTS_CONFIG
from library.models import Song


# ---------------------------------------------------------------------------
# EventType dataclass
# ---------------------------------------------------------------------------


class TestEventType:
    def test_defaults_moments_from_config(self):
        et = EventType(slug="test", name="Test")
        assert et.moments == dict(MOMENTS_CONFIG)

    def test_custom_moments(self):
        custom = {"louvor": 5, "prelúdio": 2}
        et = EventType(slug="test", name="Test", moments=custom)
        assert et.moments == custom

    def test_default_description(self):
        et = EventType(slug="test", name="Test")
        assert et.description == ""


# ---------------------------------------------------------------------------
# Slug validation
# ---------------------------------------------------------------------------


class TestValidateSlug:
    def test_valid_slugs(self):
        assert validate_event_type_slug("main") == "main"
        assert validate_event_type_slug("youth") == "youth"
        assert validate_event_type_slug("christmas-eve") == "christmas-eve"
        assert validate_event_type_slug("type1") == "type1"
        assert validate_event_type_slug("a") == "a"

    def test_normalizes_to_lowercase(self):
        assert validate_event_type_slug("Youth") == "youth"
        assert validate_event_type_slug("MAIN") == "main"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_event_type_slug("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError, match="at most 30"):
            validate_event_type_slug("a" * 31)

    def test_rejects_invalid_characters(self):
        with pytest.raises(ValueError, match="Invalid"):
            validate_event_type_slug("has space")

        with pytest.raises(ValueError, match="Invalid"):
            validate_event_type_slug("-starts-with-dash")


# ---------------------------------------------------------------------------
# is_default_event_type
# ---------------------------------------------------------------------------


class TestIsDefaultEventType:
    def test_default_slug(self):
        assert is_default_event_type("main") is True

    def test_non_default(self):
        assert is_default_event_type("youth") is False

    def test_empty_is_default(self):
        assert is_default_event_type("") is True


# ---------------------------------------------------------------------------
# filter_songs_for_event_type
# ---------------------------------------------------------------------------


class TestFilterSongs:
    def _make_songs(self):
        return {
            "Unbound": Song(title="Unbound", tags={"louvor": 3}, energy=2, content=""),
            "Youth Only": Song(
                title="Youth Only", tags={"louvor": 3}, energy=2, content="",
                event_types=["youth"],
            ),
            "Main Only": Song(
                title="Main Only", tags={"louvor": 3}, energy=2, content="",
                event_types=["main"],
            ),
            "Both": Song(
                title="Both", tags={"louvor": 3}, energy=2, content="",
                event_types=["main", "youth"],
            ),
        }

    def test_unbound_available_for_all(self):
        songs = self._make_songs()
        result = filter_songs_for_event_type(songs, "youth")
        assert "Unbound" in result

    def test_filters_by_event_type(self):
        songs = self._make_songs()
        result = filter_songs_for_event_type(songs, "youth")
        assert "Youth Only" in result
        assert "Main Only" not in result
        assert "Both" in result

    def test_empty_slug_returns_unbound_only(self):
        """Empty slug returns only unbound songs (generator skips filtering for empty slug)."""
        songs = self._make_songs()
        result = filter_songs_for_event_type(songs, "")
        assert len(result) == 1
        assert "Unbound" in result

    def test_default_slug_includes_bound_to_main(self):
        songs = self._make_songs()
        result = filter_songs_for_event_type(songs, "main")
        assert "Main Only" in result
        assert "Youth Only" not in result
        assert "Unbound" in result


# ---------------------------------------------------------------------------
# load / save / create_default
# ---------------------------------------------------------------------------


class TestLoadSave:
    def test_create_default(self):
        data = create_default_event_types()
        assert DEFAULT_EVENT_TYPE_SLUG in data
        et = data[DEFAULT_EVENT_TYPE_SLUG]
        assert et.name == DEFAULT_EVENT_TYPE_NAME
        assert et.moments == dict(MOMENTS_CONFIG)

    def test_save_and_load(self, tmp_path):
        path = tmp_path / "event_types.json"
        data = create_default_event_types()
        save_event_types(data, path)

        loaded = load_event_types(path)
        assert DEFAULT_EVENT_TYPE_SLUG in loaded
        assert loaded[DEFAULT_EVENT_TYPE_SLUG].name == DEFAULT_EVENT_TYPE_NAME

    def test_load_returns_default_if_missing(self, tmp_path):
        path = tmp_path / "event_types.json"
        assert not path.exists()

        loaded = load_event_types(path)
        assert DEFAULT_EVENT_TYPE_SLUG in loaded
        # load_event_types does NOT create the file (that's the repo's job)
        assert not path.exists()

    def test_load_preserves_custom_types(self, tmp_path):
        path = tmp_path / "event_types.json"
        data = create_default_event_types()
        data["youth"] = EventType(
            slug="youth",
            name="Youth Service",
            description="Friday evening",
            moments={"louvor": 5},
        )
        save_event_types(data, path)

        loaded = load_event_types(path)
        assert "youth" in loaded
        assert loaded["youth"].name == "Youth Service"
