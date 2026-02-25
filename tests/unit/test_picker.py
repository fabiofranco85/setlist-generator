"""Tests for cli.picker — interactive song picker."""

from unittest.mock import patch

import pytest

from cli.picker import extract_key, format_song_entry, pick_song
from tests.helpers.factories import make_song


# ---------------------------------------------------------------------------
# extract_key
# ---------------------------------------------------------------------------


class TestExtractKey:
    def test_standard_key(self):
        assert extract_key("### Oceanos (Bm)\n\nBm  G\nLyrics") == "Bm"

    def test_sharp_key(self):
        assert extract_key("### Song (F#m)\n\nF#m  A") == "F#m"

    def test_flat_key(self):
        assert extract_key("### Song (Bb)\n\nBb  Eb") == "Bb"

    def test_empty_content(self):
        assert extract_key("") == ""

    def test_no_key_in_header(self):
        assert extract_key("### Just a Title\n\nG D") == ""

    def test_no_parens(self):
        assert extract_key("Some random text") == ""

    def test_key_with_whitespace(self):
        assert extract_key("### Song ( G )\n\nG D") == "G"


# ---------------------------------------------------------------------------
# format_song_entry
# ---------------------------------------------------------------------------


class TestFormatSongEntry:
    def test_full_metadata(self):
        song = make_song(
            title="Oceanos",
            tags={"louvor": 5, "prelúdio": 3},
            energy=3,
            content="### Oceanos (Bm)\n\nBm  G",
        )
        result = format_song_entry("Oceanos", song)
        assert "Oceanos (Bm)" in result
        assert "[3 mid-]" in result
        assert "louvor(5)" in result
        assert "prelúdio" in result  # default weight, no parens

    def test_missing_key(self):
        song = make_song(
            title="No Key",
            content="### No Key\n\nG  D",
        )
        result = format_song_entry("No Key", song)
        assert "No Key" in result
        assert "()" not in result  # Should not show empty parens

    def test_default_weight_no_parens(self):
        song = make_song(
            title="Simple",
            tags={"louvor": 3},
            energy=2,
            content="### Simple (G)\n\nG D",
        )
        result = format_song_entry("Simple", song)
        assert "louvor" in result
        assert "louvor(3)" not in result  # default weight omits number

    def test_energy_labels(self):
        for energy, label in [(1, "high"), (2, "mid+"), (3, "mid-"), (4, "low")]:
            song = make_song(energy=energy, content="### S (G)\n")
            result = format_song_entry("S", song)
            assert f"[{energy} {label}]" in result


# ---------------------------------------------------------------------------
# pick_song
# ---------------------------------------------------------------------------


class TestPickSong:
    @pytest.fixture()
    def songs_dict(self):
        return {
            "Oceanos": make_song(
                title="Oceanos",
                tags={"louvor": 5},
                energy=3,
                content="### Oceanos (Bm)\n\nBm G",
            ),
            "Hosana": make_song(
                title="Hosana",
                tags={"louvor": 3, "prelúdio": 3},
                energy=2,
                content="### Hosana (D)\n\nD A",
            ),
            "Lugar Secreto": make_song(
                title="Lugar Secreto",
                tags={"louvor": 4},
                energy=4,
                content="### Lugar Secreto (A)\n\nA E",
            ),
        }

    @patch("cli.picker._is_interactive", return_value=True)
    @patch("cli.picker._pick_with_menu")
    def test_selected_index(self, mock_menu, mock_interactive, songs_dict):
        mock_menu.return_value = "Oceanos"
        result = pick_song(songs_dict)
        assert result == "Oceanos"
        mock_menu.assert_called_once()

    @patch("cli.picker._is_interactive", return_value=True)
    @patch("cli.picker._pick_with_menu")
    def test_cancelled(self, mock_menu, mock_interactive, songs_dict):
        mock_menu.return_value = None
        result = pick_song(songs_dict)
        assert result is None

    @patch("cli.picker._is_interactive", return_value=True)
    @patch("cli.picker._pick_with_menu")
    def test_moment_filter(self, mock_menu, mock_interactive, songs_dict):
        # Add a song only tagged for prelúdio
        songs_dict["Intro Song"] = make_song(
            title="Intro Song",
            tags={"prelúdio": 3},
            energy=1,
            content="### Intro Song (C)\n\nC G",
        )
        mock_menu.return_value = "Hosana"

        result = pick_song(songs_dict, moment_filter="prelúdio")
        assert result == "Hosana"

        # Check that entries passed to menu only include prelúdio songs
        call_args = mock_menu.call_args
        titles = call_args[0][1]  # second positional arg = titles list
        assert "Oceanos" not in titles  # louvor only
        assert "Lugar Secreto" not in titles  # louvor only
        assert "Hosana" in titles  # has prelúdio
        assert "Intro Song" in titles  # has prelúdio

    @patch("cli.picker._is_interactive", return_value=True)
    @patch("cli.picker._pick_with_menu")
    def test_exclude_set(self, mock_menu, mock_interactive, songs_dict):
        mock_menu.return_value = "Lugar Secreto"

        result = pick_song(songs_dict, exclude={"Oceanos", "Hosana"})
        assert result == "Lugar Secreto"

        call_args = mock_menu.call_args
        titles = call_args[0][1]
        assert "Oceanos" not in titles
        assert "Hosana" not in titles
        assert "Lugar Secreto" in titles

    @patch("cli.picker._is_interactive", return_value=False)
    @patch("cli.picker._pick_with_fallback")
    def test_non_interactive_uses_fallback(self, mock_fallback, mock_interactive, songs_dict):
        mock_fallback.return_value = "Hosana"
        result = pick_song(songs_dict)
        assert result == "Hosana"
        mock_fallback.assert_called_once()

    @patch("cli.picker._is_interactive", return_value=True)
    @patch("cli.picker._pick_with_menu", side_effect=ImportError("no simple_term_menu"))
    @patch("cli.picker._pick_with_fallback")
    def test_import_error_falls_back(self, mock_fallback, mock_menu, mock_interactive, songs_dict):
        mock_fallback.return_value = "Oceanos"
        result = pick_song(songs_dict)
        assert result == "Oceanos"
        mock_fallback.assert_called_once()

    def test_empty_after_filter(self, songs_dict):
        result = pick_song(songs_dict, moment_filter="ofertório")
        assert result is None

    @patch("cli.picker._is_interactive", return_value=True)
    @patch("cli.picker._pick_with_menu")
    def test_entries_sorted_alphabetically(self, mock_menu, mock_interactive, songs_dict):
        mock_menu.return_value = "Hosana"
        pick_song(songs_dict)

        call_args = mock_menu.call_args
        titles = call_args[0][1]
        assert titles == sorted(titles)
