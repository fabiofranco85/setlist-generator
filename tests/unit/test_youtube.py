"""Tests for library.youtube — pure functions (no API calls)."""

import pytest

from library.youtube import extract_video_id, format_playlist_name, resolve_setlist_videos
from tests.helpers.factories import make_song


# ---------------------------------------------------------------------------
# extract_video_id
# ---------------------------------------------------------------------------


class TestExtractVideoId:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # With extra params
            (
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30",
                "dQw4w9WgXcQ",
            ),
        ],
    )
    def test_valid_urls(self, url, expected):
        assert extract_video_id(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "   ",
            "https://example.com/watch?v=abc",
            "not-a-url",
            "https://www.youtube.com/watch",  # no v param
        ],
    )
    def test_invalid_urls_return_none(self, url):
        assert extract_video_id(url) is None

    def test_none_like_empty(self):
        assert extract_video_id("") is None

    def test_embed_with_trailing_path(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ/extra"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_youtu_be_with_extra_params(self):
        url = "https://youtu.be/dQw4w9WgXcQ?t=30"
        assert extract_video_id(url) == "dQw4w9WgXcQ"


# ---------------------------------------------------------------------------
# format_playlist_name
# ---------------------------------------------------------------------------


class TestFormatPlaylistName:
    def test_default_pattern(self):
        result = format_playlist_name("2026-02-15")
        assert result == "Culto 15.02.26"

    def test_custom_pattern_dd_mm_yyyy(self):
        result = format_playlist_name("2026-02-15", "Service {DD.MM.YYYY}")
        assert result == "Service 15.02.2026"

    def test_custom_pattern_iso(self):
        result = format_playlist_name("2026-02-15", "Setlist {YYYY-MM-DD}")
        assert result == "Setlist 2026-02-15"

    def test_all_placeholders(self):
        result = format_playlist_name(
            "2026-12-25",
            "{DD.MM.YY} | {DD.MM.YYYY} | {YYYY-MM-DD}",
        )
        assert result == "25.12.26 | 25.12.2026 | 2026-12-25"


# ---------------------------------------------------------------------------
# resolve_setlist_videos
# ---------------------------------------------------------------------------


class TestResolveSetlistVideos:
    def test_songs_with_youtube_url(self):
        songs = {
            "A": make_song(
                title="A",
                youtube_url="https://youtu.be/abc123",
                tags={"louvor": 3},
            ),
        }
        setlist = {"moments": {"louvor": ["A"]}}
        result = resolve_setlist_videos(setlist, songs)
        assert len(result) >= 1
        title, vid = next((t, v) for t, v in result if t == "A")
        assert vid == "abc123"

    def test_songs_without_youtube_url(self):
        songs = {"A": make_song(title="A", youtube_url="", tags={"louvor": 3})}
        setlist = {"moments": {"louvor": ["A"]}}
        result = resolve_setlist_videos(setlist, songs)
        title, vid = next((t, v) for t, v in result if t == "A")
        assert vid is None

    def test_song_not_in_dict(self):
        songs = {}
        setlist = {"moments": {"louvor": ["Missing"]}}
        result = resolve_setlist_videos(setlist, songs)
        title, vid = next((t, v) for t, v in result if t == "Missing")
        assert vid is None

    def test_moment_order_follows_config(self):
        """Songs should appear in MOMENTS_CONFIG iteration order."""
        from library.config import MOMENTS_CONFIG

        songs = {
            "A": make_song(title="A", youtube_url="https://youtu.be/a", tags={"prelúdio": 3}),
            "B": make_song(title="B", youtube_url="https://youtu.be/b", tags={"louvor": 3}),
        }
        setlist = {
            "moments": {
                "louvor": ["B"],
                "prelúdio": ["A"],
            },
        }
        result = resolve_setlist_videos(setlist, songs)
        titles = [t for t, _ in result]
        # prelúdio comes before louvor in MOMENTS_CONFIG
        moments_order = list(MOMENTS_CONFIG.keys())
        pre_idx = moments_order.index("prelúdio")
        lou_idx = moments_order.index("louvor")
        if pre_idx < lou_idx:
            assert titles.index("A") < titles.index("B")
