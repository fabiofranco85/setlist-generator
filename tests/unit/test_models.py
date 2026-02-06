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
