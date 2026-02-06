"""Tests for library.ordering — energy-based song ordering."""

import pytest

from library.ordering import apply_energy_ordering


class TestApplyEnergyOrdering:
    """Tests for apply_energy_ordering()."""

    def test_ascending_louvor(self):
        """Louvor should sort 1→4 (ascending energy)."""
        songs = [("D", 4), ("B", 2), ("A", 1), ("C", 3)]
        result = apply_energy_ordering("louvor", songs)
        assert result == ["A", "B", "C", "D"]

    def test_no_rule_for_moment_preserves_order(self):
        """Moments without a rule keep their original order."""
        songs = [("D", 4), ("A", 1)]
        result = apply_energy_ordering("prelúdio", songs)
        assert result == ["D", "A"]

    def test_disabled_via_monkeypatch(self, monkeypatch):
        monkeypatch.setattr("library.ordering.ENERGY_ORDERING_ENABLED", False)
        songs = [("D", 4), ("A", 1)]
        result = apply_energy_ordering("louvor", songs)
        assert result == ["D", "A"]  # preserved, not sorted

    def test_override_preservation(self):
        """First override_count songs keep user's order."""
        songs = [("Z", 4), ("Y", 3), ("B", 2), ("A", 1)]
        result = apply_energy_ordering("louvor", songs, override_count=2)
        # First 2 stay as-is, last 2 sorted ascending
        assert result == ["Z", "Y", "A", "B"]

    def test_override_count_zero_sorts_all(self):
        songs = [("D", 4), ("B", 2), ("A", 1), ("C", 3)]
        result = apply_energy_ordering("louvor", songs, override_count=0)
        assert result == ["A", "B", "C", "D"]

    def test_all_overrides_no_sorting(self):
        songs = [("D", 4), ("B", 2)]
        result = apply_energy_ordering("louvor", songs, override_count=2)
        assert result == ["D", "B"]

    def test_empty_input(self):
        result = apply_energy_ordering("louvor", [])
        assert result == []

    def test_single_song(self):
        result = apply_energy_ordering("louvor", [("A", 3)])
        assert result == ["A"]

    def test_unknown_rule_value(self, monkeypatch):
        """An unrecognized rule string should pass through unchanged."""
        monkeypatch.setattr(
            "library.ordering.ENERGY_ORDERING_RULES",
            {"louvor": "random_order"},
        )
        songs = [("D", 4), ("A", 1)]
        result = apply_energy_ordering("louvor", songs)
        assert result == ["D", "A"]
