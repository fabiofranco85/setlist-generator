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
