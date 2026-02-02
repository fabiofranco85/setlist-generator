"""Unit tests for shell completion functions."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from click.shell_completion import CompletionItem

from songbook.completions import (
    complete_song_names,
    complete_moment_names,
    complete_history_dates,
)


class TestCompleteSongNames:
    """Tests for complete_song_names() function."""

    def test_complete_all_songs(self):
        """Test completion with empty input returns all songs."""
        ctx = MagicMock()
        param = MagicMock()

        results = complete_song_names(ctx, param, "")

        # Should return CompletionItem objects
        assert all(isinstance(item, CompletionItem) for item in results)

        # Should return all 55 songs from database.csv
        assert len(results) > 50  # At least 50 songs

        # Results should be sorted alphabetically
        song_names = [item.value for item in results]
        assert song_names == sorted(song_names)

    def test_complete_partial_match(self):
        """Test completion with partial input filters correctly."""
        ctx = MagicMock()
        param = MagicMock()

        results = complete_song_names(ctx, param, "Oce")

        # Should find "Oceanos"
        assert len(results) >= 1
        assert any("Oceanos" in item.value for item in results)

    def test_complete_case_insensitive(self):
        """Test completion is case-insensitive."""
        ctx = MagicMock()
        param = MagicMock()

        # Test with different cases
        results_lower = complete_song_names(ctx, param, "oce")
        results_upper = complete_song_names(ctx, param, "OCE")
        results_mixed = complete_song_names(ctx, param, "OcE")

        # All should return same results
        assert len(results_lower) == len(results_upper) == len(results_mixed)

        # Should find "Oceanos"
        assert any("Oceanos" in item.value for item in results_lower)

    def test_complete_no_match(self):
        """Test completion with no matches returns empty list."""
        ctx = MagicMock()
        param = MagicMock()

        results = complete_song_names(ctx, param, "XYZNONEXISTENT")

        # Should return empty list
        assert results == []

    def test_complete_error_handling(self, tmp_path, monkeypatch):
        """Test completion gracefully handles missing database.csv."""
        ctx = MagicMock()
        param = MagicMock()

        # Change to directory without database.csv
        monkeypatch.chdir(tmp_path)

        results = complete_song_names(ctx, param, "test")

        # Should return empty list instead of raising exception
        assert results == []


class TestCompleteMomentNames:
    """Tests for complete_moment_names() function."""

    def test_complete_all_moments(self):
        """Test completion with empty input returns all moments."""
        ctx = MagicMock()
        param = MagicMock()

        results = complete_moment_names(ctx, param, "")

        # Should return CompletionItem objects
        assert all(isinstance(item, CompletionItem) for item in results)

        # Should return all 6 moments
        assert len(results) == 6

        # Should include expected moments
        moment_names = [item.value for item in results]
        assert "louvor" in moment_names
        assert "prelúdio" in moment_names
        assert "ofertório" in moment_names
        assert "saudação" in moment_names
        assert "crianças" in moment_names
        assert "poslúdio" in moment_names

    def test_complete_partial_match(self):
        """Test completion with partial input filters correctly."""
        ctx = MagicMock()
        param = MagicMock()

        results = complete_moment_names(ctx, param, "lou")

        # Should find "louvor"
        assert len(results) == 1
        assert results[0].value == "louvor"

    def test_complete_case_insensitive(self):
        """Test completion is case-insensitive."""
        ctx = MagicMock()
        param = MagicMock()

        results_lower = complete_moment_names(ctx, param, "pre")
        results_upper = complete_moment_names(ctx, param, "PRE")

        # Both should return "prelúdio"
        assert len(results_lower) == len(results_upper) == 1
        assert results_lower[0].value == "prelúdio"

    def test_complete_no_match(self):
        """Test completion with no matches returns empty list."""
        ctx = MagicMock()
        param = MagicMock()

        results = complete_moment_names(ctx, param, "xyz")

        # Should return empty list
        assert results == []


class TestCompleteHistoryDates:
    """Tests for complete_history_dates() function."""

    def test_complete_all_dates(self, tmp_path, monkeypatch):
        """Test completion with empty input returns all dates."""
        # Create test history directory
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create test history files
        (history_dir / "2025-12-25.json").write_text("{}")
        (history_dir / "2025-12-18.json").write_text("{}")
        (history_dir / "2025-11-03.json").write_text("{}")
        (history_dir / "2024-01-01.json").write_text("{}")

        # Mock resolve_paths to return our test directory
        from setlist.paths import PathConfig

        def mock_resolve_paths(output_dir, history_dir):
            return PathConfig(
                output_dir=tmp_path / "output",
                history_dir=tmp_path / "history"
            )

        monkeypatch.setattr("songbook.cli_utils.resolve_paths", mock_resolve_paths)

        ctx = MagicMock()
        ctx.params = {}
        param = MagicMock()

        results = complete_history_dates(ctx, param, "")

        # Should return CompletionItem objects
        assert all(isinstance(item, CompletionItem) for item in results)

        # Should return all 4 dates
        assert len(results) == 4

        # Should be sorted descending (most recent first)
        date_values = [item.value for item in results]
        assert date_values == ["2025-12-25", "2025-12-18", "2025-11-03", "2024-01-01"]

    def test_complete_partial_match(self, tmp_path, monkeypatch):
        """Test completion with partial input filters correctly."""
        # Create test history directory
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create test history files
        (history_dir / "2025-12-25.json").write_text("{}")
        (history_dir / "2025-12-18.json").write_text("{}")
        (history_dir / "2024-01-01.json").write_text("{}")

        # Mock resolve_paths
        from setlist.paths import PathConfig

        def mock_resolve_paths(output_dir, history_dir):
            return PathConfig(
                output_dir=tmp_path / "output",
                history_dir=tmp_path / "history"
            )

        monkeypatch.setattr("songbook.cli_utils.resolve_paths", mock_resolve_paths)

        ctx = MagicMock()
        ctx.params = {}
        param = MagicMock()

        results = complete_history_dates(ctx, param, "2025-12")

        # Should find only December 2025 dates
        assert len(results) == 2
        date_values = [item.value for item in results]
        assert "2025-12-25" in date_values
        assert "2025-12-18" in date_values
        assert "2024-01-01" not in date_values

    def test_complete_descending_order(self, tmp_path, monkeypatch):
        """Test that dates are sorted in descending order (most recent first)."""
        # Create test history directory
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create files in non-chronological order
        (history_dir / "2024-01-01.json").write_text("{}")
        (history_dir / "2025-12-25.json").write_text("{}")
        (history_dir / "2025-06-15.json").write_text("{}")

        # Mock resolve_paths
        from setlist.paths import PathConfig

        def mock_resolve_paths(output_dir, history_dir):
            return PathConfig(
                output_dir=tmp_path / "output",
                history_dir=tmp_path / "history"
            )

        monkeypatch.setattr("songbook.cli_utils.resolve_paths", mock_resolve_paths)

        ctx = MagicMock()
        ctx.params = {}
        param = MagicMock()

        results = complete_history_dates(ctx, param, "")

        # Should be sorted descending
        date_values = [item.value for item in results]
        assert date_values == ["2025-12-25", "2025-06-15", "2024-01-01"]

    def test_complete_missing_history_dir(self, tmp_path, monkeypatch):
        """Test completion gracefully handles missing history directory."""
        # Mock resolve_paths to return non-existent directory
        from setlist.paths import PathConfig

        def mock_resolve_paths(output_dir, history_dir):
            return PathConfig(
                output_dir=tmp_path / "output",
                history_dir=tmp_path / "nonexistent"
            )

        monkeypatch.setattr("songbook.cli_utils.resolve_paths", mock_resolve_paths)

        ctx = MagicMock()
        ctx.params = {}
        param = MagicMock()

        results = complete_history_dates(ctx, param, "")

        # Should return empty list instead of raising exception
        assert results == []

    def test_complete_no_match(self, tmp_path, monkeypatch):
        """Test completion with no matches returns empty list."""
        # Create test history directory
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create test history files
        (history_dir / "2025-12-25.json").write_text("{}")

        # Mock resolve_paths
        from setlist.paths import PathConfig

        def mock_resolve_paths(output_dir, history_dir):
            return PathConfig(
                output_dir=tmp_path / "output",
                history_dir=tmp_path / "history"
            )

        monkeypatch.setattr("songbook.cli_utils.resolve_paths", mock_resolve_paths)

        ctx = MagicMock()
        ctx.params = {}
        param = MagicMock()

        results = complete_history_dates(ctx, param, "2024-")

        # Should return empty list (no 2024 dates)
        assert results == []
