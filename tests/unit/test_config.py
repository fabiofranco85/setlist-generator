"""Tests for library.config — configuration helpers."""

from library.config import canonical_moment_order


class TestCanonicalMomentOrder:
    def test_full_moments_returns_config_order(self):
        """All MOMENTS_CONFIG keys in correct order."""
        moments = {
            "louvor": ["A"],
            "prelúdio": ["B"],
            "poslúdio": ["C"],
            "saudação": ["D"],
            "ofertório": ["E"],
            "crianças": ["F"],
        }
        result = canonical_moment_order(moments)
        assert result == [
            "prelúdio", "ofertório", "saudação",
            "crianças", "louvor", "poslúdio",
        ]

    def test_subset_preserves_relative_order(self):
        """Subset of moments still in canonical order."""
        moments = {"louvor": ["A"], "prelúdio": ["B"]}
        result = canonical_moment_order(moments)
        assert result == ["prelúdio", "louvor"]

    def test_extra_moments_appended_alphabetically(self):
        """Custom moments not in MOMENTS_CONFIG go at the end."""
        moments = {"louvor": ["A"], "prelúdio": ["B"], "adoração": ["C"]}
        result = canonical_moment_order(moments)
        assert result == ["prelúdio", "louvor", "adoração"]

    def test_multiple_extra_moments_sorted(self):
        """Multiple custom moments sorted alphabetically after canonical ones."""
        moments = {"louvor": ["A"], "zebra": ["B"], "adoração": ["C"]}
        result = canonical_moment_order(moments)
        assert result == ["louvor", "adoração", "zebra"]

    def test_empty_returns_empty(self):
        assert canonical_moment_order({}) == []

    def test_only_extra_moments(self):
        """Only custom moments — all sorted alphabetically."""
        moments = {"worship": ["A"], "adoration": ["B"]}
        result = canonical_moment_order(moments)
        assert result == ["adoration", "worship"]
