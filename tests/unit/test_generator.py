"""Tests for library.generator — SetlistGenerator class."""

import random
from unittest.mock import MagicMock

import pytest

from library.config import MOMENTS_CONFIG
from library.generator import SetlistGenerator, generate_setlist
from library.models import Setlist
from tests.helpers.factories import make_song


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def generator(sample_songs, sample_history):
    return SetlistGenerator(sample_songs, sample_history)


# ---------------------------------------------------------------------------
# SetlistGenerator.generate
# ---------------------------------------------------------------------------


class TestSetlistGenerator:
    def test_returns_setlist(self, generator, fixed_random_seed):
        result = generator.generate("2026-02-15")
        assert isinstance(result, Setlist)

    def test_correct_date(self, generator, fixed_random_seed):
        result = generator.generate("2026-02-15")
        assert result.date == "2026-02-15"

    def test_all_moments_present(self, generator, fixed_random_seed):
        result = generator.generate("2026-02-15")
        for moment in MOMENTS_CONFIG:
            assert moment in result.moments

    def test_correct_song_counts(self, generator, fixed_random_seed):
        result = generator.generate("2026-02-15")
        for moment, count in MOMENTS_CONFIG.items():
            # May be less if not enough songs tagged for moment
            assert len(result.moments[moment]) <= count

    def test_overrides_applied(self):
        # Use enough songs that overrides for louvor won't be consumed earlier
        songs = {
            f"Song {i}": make_song(
                title=f"Song {i}",
                tags={"louvor": 3, "prelúdio": 3, "ofertório": 3,
                      "saudação": 3, "crianças": 3, "poslúdio": 3},
                energy=i % 4 + 1,
            )
            for i in range(12)
        }
        random.seed(42)
        gen = SetlistGenerator(songs, [])
        result = gen.generate(
            "2026-02-15",
            overrides={"louvor": ["Song 10", "Song 11"]},
        )
        louvor = result.moments["louvor"]
        assert "Song 10" in louvor
        assert "Song 11" in louvor

    def test_state_reset_between_calls(self, generator):
        random.seed(42)
        result1 = generator.generate("2026-02-15")
        random.seed(42)
        result2 = generator.generate("2026-02-15")
        assert result1.moments == result2.moments

    def test_no_duplicates_across_moments(self, generator, fixed_random_seed):
        result = generator.generate("2026-02-15")
        all_songs = []
        for song_list in result.moments.values():
            all_songs.extend(song_list)
        # With only 4 sample songs and 9 total slots, there may be fewer songs
        # but each song should appear at most once
        assert len(all_songs) == len(set(all_songs))


# ---------------------------------------------------------------------------
# SetlistGenerator.from_repositories
# ---------------------------------------------------------------------------


class TestFromRepositories:
    def test_creates_generator(self, sample_songs, sample_history):
        songs_repo = MagicMock()
        songs_repo.get_all.return_value = sample_songs
        history_repo = MagicMock()
        history_repo.get_all.return_value = sample_history

        gen = SetlistGenerator.from_repositories(songs_repo, history_repo)
        assert gen.songs == sample_songs
        assert gen.history == sample_history


# ---------------------------------------------------------------------------
# generate_setlist wrapper
# ---------------------------------------------------------------------------


class TestGenerateSetlistWrapper:
    def test_returns_setlist(self, sample_songs, sample_history, fixed_random_seed):
        result = generate_setlist(sample_songs, sample_history, "2026-02-15")
        assert isinstance(result, Setlist)
        assert result.date == "2026-02-15"
