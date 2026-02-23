"""Tests for library.models — Song and Setlist dataclasses."""

from library.models import Setlist, Song
from tests.helpers.factories import make_song


class TestSong:
    def test_get_weight_existing_moment(self):
        song = make_song(tags={"louvor": 5, "prelúdio": 3})
        assert song.get_weight("louvor") == 5
        assert song.get_weight("prelúdio") == 3

    def test_get_weight_missing_moment_returns_zero(self):
        song = make_song(tags={"louvor": 5})
        assert song.get_weight("ofertório") == 0

    def test_has_moment_true(self):
        song = make_song(tags={"louvor": 5})
        assert song.has_moment("louvor") is True

    def test_has_moment_false(self):
        song = make_song(tags={"louvor": 5})
        assert song.has_moment("ofertório") is False

    def test_youtube_url_default_empty(self):
        song = Song(title="Test", tags={}, energy=2, content="")
        assert song.youtube_url == ""

    def test_youtube_url_custom(self):
        song = make_song(youtube_url="https://youtu.be/abc123")
        assert song.youtube_url == "https://youtu.be/abc123"

    def test_event_types_default_empty(self):
        song = Song(title="Test", tags={}, energy=2, content="")
        assert song.event_types == []

    def test_event_types_custom(self):
        song = make_song(event_types=["youth", "main"])
        assert song.event_types == ["youth", "main"]

    def test_is_available_for_event_type_unbound(self):
        song = make_song(event_types=[])
        assert song.is_available_for_event_type("youth") is True
        assert song.is_available_for_event_type("main") is True

    def test_is_available_for_event_type_bound(self):
        song = make_song(event_types=["youth"])
        assert song.is_available_for_event_type("youth") is True
        assert song.is_available_for_event_type("main") is False


class TestSetlist:
    def test_to_dict_structure(self, sample_setlist):
        d = sample_setlist.to_dict()
        assert d["date"] == "2026-02-15"
        assert "moments" in d
        assert isinstance(d["moments"], dict)

    def test_to_dict_preserves_moments(self, sample_setlist):
        d = sample_setlist.to_dict()
        assert d["moments"]["louvor"] == [
            "Upbeat Song",
            "Moderate Song",
            "Reflective Song",
            "Worship Song",
        ]

    def test_to_dict_roundtrip(self, sample_setlist):
        d = sample_setlist.to_dict()
        rebuilt = Setlist(date=d["date"], moments=d["moments"])
        assert rebuilt.date == sample_setlist.date
        assert rebuilt.moments == sample_setlist.moments

    def test_to_dict_omits_event_type_when_empty(self):
        setlist = Setlist(date="2026-02-15", moments={"louvor": ["A"]})
        d = setlist.to_dict()
        assert "event_type" not in d

    def test_to_dict_includes_event_type_when_set(self):
        setlist = Setlist(date="2026-02-15", moments={"louvor": ["A"]}, event_type="youth")
        d = setlist.to_dict()
        assert d["event_type"] == "youth"

    def test_setlist_id_excludes_event_type(self):
        """setlist_id intentionally excludes event_type — subdirectories handle routing."""
        setlist = Setlist(date="2026-02-15", moments={}, event_type="youth", label="evening")
        assert setlist.setlist_id == "2026-02-15_evening"
