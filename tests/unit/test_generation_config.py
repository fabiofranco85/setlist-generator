"""Tests for GenerationConfig dataclass and config injection."""

from unittest.mock import Mock

from library.config import (
    DEFAULT_ENERGY,
    DEFAULT_WEIGHT,
    ENERGY_ORDERING_ENABLED,
    ENERGY_ORDERING_RULES,
    GenerationConfig,
    MOMENTS_CONFIG,
    RECENCY_DECAY_DAYS,
    canonical_moment_order,
)


class TestGenerationConfigDefaults:
    """Test GenerationConfig.from_defaults() matches module constants."""

    def test_from_defaults_matches_constants(self):
        cfg = GenerationConfig.from_defaults()
        assert cfg.moments_config == MOMENTS_CONFIG
        assert cfg.recency_decay_days == RECENCY_DECAY_DAYS
        assert cfg.default_weight == DEFAULT_WEIGHT
        assert cfg.energy_ordering_enabled == ENERGY_ORDERING_ENABLED
        assert cfg.energy_ordering_rules == ENERGY_ORDERING_RULES
        assert cfg.default_energy == DEFAULT_ENERGY

    def test_from_defaults_creates_copies(self):
        cfg = GenerationConfig.from_defaults()
        # Should be equal but not the same object
        assert cfg.moments_config == MOMENTS_CONFIG
        assert cfg.moments_config is not MOMENTS_CONFIG

    def test_frozen(self):
        cfg = GenerationConfig.from_defaults()
        import pytest
        with pytest.raises(AttributeError):
            cfg.recency_decay_days = 99  # type: ignore[misc]

    def test_custom_values(self):
        cfg = GenerationConfig(
            moments_config={"louvor": 5},
            recency_decay_days=30,
            default_weight=5,
            energy_ordering_enabled=False,
        )
        assert cfg.moments_config == {"louvor": 5}
        assert cfg.recency_decay_days == 30
        assert cfg.default_weight == 5
        assert cfg.energy_ordering_enabled is False


class TestGenerationConfigFromRepo:
    """Test GenerationConfig.from_config_repo() reads from repository."""

    def test_from_config_repo(self):
        repo = Mock()
        repo.get_moments_config.return_value = {"louvor": 6}
        repo.get_recency_decay_days.return_value = 60
        repo.get_default_weight.return_value = 4
        repo.is_energy_ordering_enabled.return_value = False
        repo.get_energy_ordering_rules.return_value = {"louvor": "descending"}
        repo.get_default_energy.return_value = 3.0

        cfg = GenerationConfig.from_config_repo(repo)

        assert cfg.moments_config == {"louvor": 6}
        assert cfg.recency_decay_days == 60
        assert cfg.default_weight == 4
        assert cfg.energy_ordering_enabled is False
        assert cfg.energy_ordering_rules == {"louvor": "descending"}
        assert cfg.default_energy == 3.0

    def test_from_config_repo_calls_all_methods(self):
        repo = Mock()
        repo.get_moments_config.return_value = dict(MOMENTS_CONFIG)
        repo.get_recency_decay_days.return_value = RECENCY_DECAY_DAYS
        repo.get_default_weight.return_value = DEFAULT_WEIGHT
        repo.is_energy_ordering_enabled.return_value = ENERGY_ORDERING_ENABLED
        repo.get_energy_ordering_rules.return_value = dict(ENERGY_ORDERING_RULES)
        repo.get_default_energy.return_value = DEFAULT_ENERGY

        GenerationConfig.from_config_repo(repo)

        repo.get_moments_config.assert_called_once()
        repo.get_recency_decay_days.assert_called_once()
        repo.get_default_weight.assert_called_once()
        repo.is_energy_ordering_enabled.assert_called_once()
        repo.get_energy_ordering_rules.assert_called_once()
        repo.get_default_energy.assert_called_once()


class TestCanonicalMomentOrder:
    """Test canonical_moment_order with reference_config parameter."""

    def test_default_reference(self):
        moments = {"louvor": ["A"], "prelúdio": ["B"], "extra": ["C"]}
        order = canonical_moment_order(moments)
        assert order == ["prelúdio", "louvor", "extra"]

    def test_custom_reference(self):
        reference = {"worship": 4, "opening": 1}
        moments = {"opening": ["A"], "worship": ["B"], "closing": ["C"]}
        order = canonical_moment_order(moments, reference_config=reference)
        assert order == ["worship", "opening", "closing"]

    def test_empty_reference(self):
        moments = {"c": 1, "a": 2, "b": 3}
        order = canonical_moment_order(moments, reference_config={})
        # All extra, sorted alphabetically
        assert order == ["a", "b", "c"]


class TestConfigInjectionBackwardCompat:
    """Test that refactored functions work without explicit config."""

    def test_calculate_recency_scores_default(self, sample_songs, sample_history):
        from library.selector import calculate_recency_scores

        # Should work with no explicit recency_decay_days
        scores = calculate_recency_scores(
            sample_songs, sample_history, current_date="2026-02-15"
        )
        assert len(scores) == len(sample_songs)

    def test_calculate_recency_scores_custom_decay(self, sample_songs, sample_history):
        from library.selector import calculate_recency_scores

        scores_default = calculate_recency_scores(
            sample_songs, sample_history, current_date="2026-02-15"
        )
        scores_fast = calculate_recency_scores(
            sample_songs, sample_history, current_date="2026-02-15",
            recency_decay_days=10,
        )
        # With faster decay, scores should be higher (songs feel fresher sooner)
        for title in sample_songs:
            if title in scores_default and scores_default[title] < 1.0:
                assert scores_fast[title] >= scores_default[title]

    def test_apply_energy_ordering_default(self):
        from library.ordering import apply_energy_ordering

        songs = [("A", 3.0), ("B", 1.0), ("C", 4.0)]
        result = apply_energy_ordering("louvor", songs)
        assert result == ["B", "A", "C"]

    def test_apply_energy_ordering_disabled(self):
        from library.ordering import apply_energy_ordering

        songs = [("A", 3.0), ("B", 1.0), ("C", 4.0)]
        result = apply_energy_ordering(
            "louvor", songs, energy_ordering_enabled=False,
        )
        assert result == ["A", "B", "C"]  # Original order

    def test_apply_energy_ordering_custom_rules(self):
        from library.ordering import apply_energy_ordering

        songs = [("A", 3.0), ("B", 1.0), ("C", 4.0)]
        result = apply_energy_ordering(
            "louvor", songs,
            energy_ordering_rules={"louvor": "descending"},
        )
        assert result == ["C", "A", "B"]

    def test_parse_tags_default(self):
        from library.loader import parse_tags

        result = parse_tags("louvor")
        assert result == {"louvor": DEFAULT_WEIGHT}

    def test_parse_tags_custom_default_weight(self):
        from library.loader import parse_tags

        result = parse_tags("louvor", default_weight=7)
        assert result == {"louvor": 7}

    def test_parse_tags_explicit_weight_unaffected(self):
        from library.loader import parse_tags

        result = parse_tags("louvor(5)", default_weight=7)
        assert result == {"louvor": 5}  # Explicit weight overrides default

    def test_generator_with_config(self, sample_songs, empty_history):
        from library.generator import SetlistGenerator

        cfg = GenerationConfig(
            moments_config={"louvor": 2},
            recency_decay_days=30,
            energy_ordering_enabled=False,
        )
        gen = SetlistGenerator(sample_songs, empty_history, config=cfg)
        setlist = gen.generate("2026-03-01")
        assert len(setlist.moments["louvor"]) == 2

    def test_generator_default_config(self, sample_songs, empty_history):
        from library.generator import SetlistGenerator

        gen = SetlistGenerator(sample_songs, empty_history)
        setlist = gen.generate("2026-03-01")
        # Default config uses MOMENTS_CONFIG which has "louvor" moment
        assert "louvor" in setlist.moments
        # Can't fill all 4 louvor slots with only 4 total songs shared across moments
        assert len(setlist.moments["louvor"]) <= MOMENTS_CONFIG["louvor"]
