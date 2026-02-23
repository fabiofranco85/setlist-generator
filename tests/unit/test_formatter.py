"""Tests for library.formatter — setlist markdown formatting."""

from library.formatter import format_setlist_markdown
from library.models import Setlist, Song
from tests.helpers.factories import make_song


class TestFormatSetlistMarkdown:
    def test_header_contains_date(self, sample_setlist, sample_songs):
        md = format_setlist_markdown(sample_setlist, sample_songs)
        assert "# Setlist - 2026-02-15" in md

    def test_moment_headers_capitalized(self, sample_setlist, sample_songs):
        md = format_setlist_markdown(sample_setlist, sample_songs)
        assert "## Louvor" in md
        assert "## Prelúdio" in md

    def test_song_content_included(self, sample_setlist, sample_songs):
        md = format_setlist_markdown(sample_setlist, sample_songs)
        assert "### Upbeat Song (C)" in md
        assert "Upbeat lyrics..." in md

    def test_missing_song_shows_placeholder(self):
        setlist = Setlist(
            date="2026-02-15",
            moments={"louvor": ["Ghost Song"]},
        )
        songs = {}  # no songs at all
        md = format_setlist_markdown(setlist, songs)
        assert "*(Content not found)*" in md
        assert "### Ghost Song" in md

    def test_separator_between_songs(self, sample_setlist, sample_songs):
        md = format_setlist_markdown(sample_setlist, sample_songs)
        assert "---" in md

    def test_empty_content_song_shows_placeholder(self):
        setlist = Setlist(date="2026-01-01", moments={"louvor": ["Empty"]})
        songs = {"Empty": make_song(title="Empty", content="")}
        md = format_setlist_markdown(setlist, songs)
        assert "*(Content not found)*" in md

    def test_moments_in_canonical_order(self):
        """Moments appear in MOMENTS_CONFIG order regardless of dict insertion order."""
        setlist = Setlist(
            date="2026-01-01",
            moments={
                "louvor": ["Song A"],
                "poslúdio": ["Song B"],
                "prelúdio": ["Song C"],
            },
        )
        songs = {
            "Song A": make_song(title="Song A"),
            "Song B": make_song(title="Song B"),
            "Song C": make_song(title="Song C"),
        }
        md = format_setlist_markdown(setlist, songs)
        headers = [line for line in md.split("\n") if line.startswith("## ")]
        assert headers == ["## Prelúdio", "## Louvor", "## Poslúdio"]

    def test_moments_order_with_all_moments_scrambled(self, sample_songs):
        """Full setlist with all 6 moments in wrong dict order still outputs correctly."""
        setlist = Setlist(
            date="2026-01-01",
            moments={
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
                "crianças": ["Upbeat Song"],
                "poslúdio": ["Worship Song"],
                "prelúdio": ["Upbeat Song"],
                "ofertório": ["Reflective Song"],
                "saudação": ["Moderate Song"],
            },
        )
        md = format_setlist_markdown(setlist, sample_songs)
        headers = [line for line in md.split("\n") if line.startswith("## ")]
        assert headers == [
            "## Prelúdio", "## Ofertório", "## Saudação",
            "## Crianças", "## Louvor", "## Poslúdio",
        ]
