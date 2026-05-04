"""Unit tests for the pure helpers in cli/commands/replace.py.

These cover the (NEW) marker placement and the energy-reorder drift
detection that the bug "songbook replace --moment louvor --position 3
keeps changing position 4" surfaced. The helpers are deliberately
side-effect-free so the bug can be characterized without standing up a
full CliRunner pipeline.
"""

from __future__ import annotations

import pytest

from cli.commands.replace import compute_position_drift, format_updated_moment_lines


class TestFormatUpdatedMomentLines:
    def test_marker_follows_song_identity_not_position(self):
        """
        The bug: when energy reorder moves the new song to a different slot,
        a position-based ``(NEW)`` marker labels whatever song happened to
        land at the originally requested position. The helper must instead
        attach the marker to the new song's *title*, wherever it ended up.
        """
        new_moment_songs = ["Upbeat", "NEW Song", "Moderate", "Worship"]
        replacement_titles = {"NEW Song"}

        lines = format_updated_moment_lines(new_moment_songs, replacement_titles)

        assert lines == [
            "  1. Upbeat",
            "  2. NEW Song (NEW)",  # marker travels with the title
            "  3. Moderate",
            "  4. Worship",
        ]

    def test_no_marker_when_replacement_set_empty(self):
        lines = format_updated_moment_lines(["A", "B", "C"], set())
        assert all("(NEW)" not in line for line in lines)

    def test_multiple_new_songs_each_marked(self):
        lines = format_updated_moment_lines(
            ["A", "NEW1", "B", "NEW2"],
            {"NEW1", "NEW2"},
        )
        assert lines[1].endswith("(NEW)")
        assert lines[3].endswith("(NEW)")
        assert "(NEW)" not in lines[0] and "(NEW)" not in lines[2]


class TestComputePositionDrift:
    def test_no_drift_when_song_stays_at_requested_position(self):
        """The new song landed exactly where the user asked → no drift output."""
        drift = compute_position_drift(
            requested_positions_zero_indexed=[2],
            replacement_titles=["NEW"],
            new_moment_songs=["A", "B", "NEW", "D"],
        )
        assert drift == []

    def test_drift_when_energy_reorder_moves_new_song(self):
        """
        Reproduces the bug: user asked for position 1 (0-indexed: 0); the
        new song landed at position 3 (0-indexed: 2). The drift entry uses
        1-indexed positions for user-facing output.
        """
        drift = compute_position_drift(
            requested_positions_zero_indexed=[0],
            replacement_titles=["NEW"],
            new_moment_songs=["Moderate", "Reflective", "NEW", "Worship"],
        )
        assert drift == [(1, 3, "NEW")]

    def test_drift_for_multiple_replacements(self):
        drift = compute_position_drift(
            requested_positions_zero_indexed=[0, 2],
            replacement_titles=["NEW1", "NEW2"],
            new_moment_songs=["A", "NEW1", "NEW2", "D"],
            #                  0     1       2       3
            # NEW1 requested at idx 0 → landed at idx 1 → drift
            # NEW2 requested at idx 2 → landed at idx 2 → no drift
        )
        assert drift == [(1, 2, "NEW1")]

    def test_skips_songs_not_present_in_new_moment(self):
        """
        Defensive: if a replacement title somehow isn't in the new moment
        (shouldn't happen in normal flow), skip it instead of raising. This
        keeps the CLI from crashing on edge cases like batch replace
        producing duplicate song dedup.
        """
        drift = compute_position_drift(
            requested_positions_zero_indexed=[0],
            replacement_titles=["GHOST"],
            new_moment_songs=["A", "B", "C"],
        )
        assert drift == []

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError, match="same length"):
            compute_position_drift(
                requested_positions_zero_indexed=[0, 1],
                replacement_titles=["only-one"],
                new_moment_songs=["A", "B"],
            )
