"""Tests for library.youtube — pure functions and credential handling."""

from unittest.mock import MagicMock, patch

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

    def test_moment_order_follows_setlist(self):
        """Songs should appear in the setlist's moment iteration order."""
        songs = {
            "A": make_song(title="A", youtube_url="https://youtu.be/a", tags={"prelúdio": 3}),
            "B": make_song(title="B", youtube_url="https://youtu.be/b", tags={"louvor": 3}),
        }
        # Setlist has louvor first, prelúdio second
        setlist = {
            "moments": {
                "louvor": ["B"],
                "prelúdio": ["A"],
            },
        }
        result = resolve_setlist_videos(setlist, songs)
        titles = [t for t, _ in result]
        # Should follow setlist moment order (louvor before prelúdio)
        assert titles == ["B", "A"]

        # Reverse order in setlist
        setlist_reversed = {
            "moments": {
                "prelúdio": ["A"],
                "louvor": ["B"],
            },
        }
        result_reversed = resolve_setlist_videos(setlist_reversed, songs)
        titles_reversed = [t for t, _ in result_reversed]
        assert titles_reversed == ["A", "B"]


# ---------------------------------------------------------------------------
# get_credentials — refresh failure fallthrough
# ---------------------------------------------------------------------------


class TestGetCredentialsRefreshFallthrough:
    """When cached token refresh fails, get_credentials should re-authenticate."""

    @patch("google_auth_oauthlib.flow.InstalledAppFlow")
    @patch("google.oauth2.credentials.Credentials")
    def test_refresh_failure_triggers_reauth(
        self, mock_creds_cls, mock_flow_cls, tmp_path
    ):
        """If creds.refresh() raises, fall through to InstalledAppFlow."""
        from library.youtube import get_credentials

        # Set up fake client_secrets and token files
        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text("{}")
        token_file = tmp_path / ".youtube_token.json"
        token_file.write_text("{}")

        # Mock expired credentials whose refresh() raises
        expired_creds = MagicMock()
        expired_creds.valid = False
        expired_creds.expired = True
        expired_creds.refresh_token = "old-refresh-token"
        expired_creds.refresh.side_effect = Exception("Token has been revoked")
        mock_creds_cls.from_authorized_user_file.return_value = expired_creds

        # Mock the re-auth flow
        fresh_creds = MagicMock()
        fresh_creds.to_json.return_value = '{"token": "new"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = fresh_creds
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow

        result = get_credentials(
            client_secrets_path=str(secrets_file),
            token_path=str(token_file),
        )

        # Should have attempted refresh
        expired_creds.refresh.assert_called_once()
        # Should have fallen through to browser flow
        mock_flow.run_local_server.assert_called_once_with(port=0)
        # Should return the fresh credentials
        assert result is fresh_creds
        # Token file should be updated
        assert token_file.read_text() == '{"token": "new"}'

    @patch("google_auth_oauthlib.flow.InstalledAppFlow")
    @patch("google.oauth2.credentials.Credentials")
    def test_successful_refresh_skips_reauth(
        self, mock_creds_cls, mock_flow_cls, tmp_path
    ):
        """If creds.refresh() succeeds, do not launch browser flow."""
        from library.youtube import get_credentials

        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text("{}")
        token_file = tmp_path / ".youtube_token.json"
        token_file.write_text("{}")

        # Mock expired credentials whose refresh() succeeds
        refreshed_creds = MagicMock()
        refreshed_creds.valid = False
        refreshed_creds.expired = True
        refreshed_creds.refresh_token = "valid-refresh-token"
        refreshed_creds.refresh.return_value = None  # success
        refreshed_creds.to_json.return_value = '{"token": "refreshed"}'
        mock_creds_cls.from_authorized_user_file.return_value = refreshed_creds

        result = get_credentials(
            client_secrets_path=str(secrets_file),
            token_path=str(token_file),
        )

        # Should have refreshed successfully
        refreshed_creds.refresh.assert_called_once()
        # Should NOT have launched browser flow
        mock_flow_cls.from_client_secrets_file.assert_not_called()
        # Should return the refreshed credentials
        assert result is refreshed_creds
