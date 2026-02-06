"""Tests for library.selector — recency, selection, and usage queries."""

import random
from math import exp

import pytest
from freezegun import freeze_time

from library.selector import (
    calculate_recency_scores,
    get_days_since_last_use,
    get_song_usage_history,
    select_songs_for_moment,
)
from tests.helpers.factories import make_history_entry, make_song


# ---------------------------------------------------------------------------
# calculate_recency_scores
# ---------------------------------------------------------------------------


class TestCalculateRecencyScores:
    def test_empty_history_all_ones(self, sample_songs):
        scores = calculate_recency_scores(sample_songs, [], current_date="2026-02-15")
        for title in sample_songs:
            assert scores[title] == 1.0

    def test_same_day_is_zero(self):
        songs = {"A": make_song(title="A")}
        history = [make_history_entry("2026-02-15", louvor=["A"])]
        scores = calculate_recency_scores(songs, history, current_date="2026-02-15")
        assert scores["A"] == 0.0

    @pytest.mark.parametrize(
        "days, expected_low, expected_high",
        [
            (7, 0.10, 0.18),
            (14, 0.24, 0.32),
            (45, 0.60, 0.66),
            (90, 0.84, 0.90),
        ],
    )
    def test_score_at_various_days(self, days, expected_low, expected_high):
        songs = {"A": make_song(title="A")}
        history = [make_history_entry("2026-01-01", louvor=["A"])]
        # current_date = 2026-01-01 + days
        from datetime import datetime, timedelta

        target = (datetime(2026, 1, 1) + timedelta(days=days)).strftime("%Y-%m-%d")
        scores = calculate_recency_scores(songs, history, current_date=target)
        assert expected_low < scores["A"] < expected_high

    def test_never_used_song_gets_one(self):
        songs = {"A": make_song(title="A"), "B": make_song(title="B")}
        history = [make_history_entry("2026-01-01", louvor=["A"])]
        scores = calculate_recency_scores(songs, history, current_date="2026-02-15")
        assert scores["B"] == 1.0

    def test_malformed_date_skipped(self):
        songs = {"A": make_song(title="A")}
        history = [{"date": "not-a-date", "moments": {"louvor": ["A"]}}]
        scores = calculate_recency_scores(songs, history, current_date="2026-02-15")
        assert scores["A"] == 1.0  # treated as never used

    def test_missing_date_key_skipped(self):
        songs = {"A": make_song(title="A")}
        history = [{"moments": {"louvor": ["A"]}}]
        scores = calculate_recency_scores(songs, history, current_date="2026-02-15")
        assert scores["A"] == 1.0

    @freeze_time("2026-02-15")
    def test_current_date_none_uses_today(self):
        songs = {"A": make_song(title="A")}
        history = [make_history_entry("2026-02-15", louvor=["A"])]
        scores = calculate_recency_scores(songs, history, current_date=None)
        assert scores["A"] == 0.0

    def test_most_recent_occurrence_used(self):
        """Only the most recent appearance matters for recency."""
        songs = {"A": make_song(title="A")}
        history = [
            make_history_entry("2026-02-01", louvor=["A"]),  # most recent first
            make_history_entry("2026-01-01", louvor=["A"]),
        ]
        scores = calculate_recency_scores(songs, history, current_date="2026-02-15")
        # Should use 2026-02-01 (14 days ago), not 2026-01-01 (45 days)
        expected = 1.0 - exp(-14 / 45)
        assert abs(scores["A"] - expected) < 0.01


# ---------------------------------------------------------------------------
# select_songs_for_moment
# ---------------------------------------------------------------------------


class TestSelectSongsForMoment:
    def test_basic_selection(self, sample_songs, fixed_random_seed):
        recency = {t: 1.0 for t in sample_songs}
        selected = select_songs_for_moment(
            "louvor", 4, sample_songs, recency, set()
        )
        assert len(selected) == 4
        # Each item is (title, energy)
        titles = [t for t, _ in selected]
        assert all(t in sample_songs for t in titles)

    def test_overrides_come_first(self, sample_songs, fixed_random_seed):
        recency = {t: 1.0 for t in sample_songs}
        selected = select_songs_for_moment(
            "louvor",
            4,
            sample_songs,
            recency,
            set(),
            overrides=["Reflective Song", "Worship Song"],
        )
        titles = [t for t, _ in selected]
        assert titles[0] == "Reflective Song"
        assert titles[1] == "Worship Song"

    def test_overrides_truncated_to_count(self, sample_songs, fixed_random_seed):
        recency = {t: 1.0 for t in sample_songs}
        selected = select_songs_for_moment(
            "louvor",
            2,
            sample_songs,
            recency,
            set(),
            overrides=["Reflective Song", "Worship Song", "Upbeat Song"],
        )
        assert len(selected) == 2

    def test_already_selected_excluded(self, sample_songs, fixed_random_seed):
        recency = {t: 1.0 for t in sample_songs}
        already = {"Upbeat Song", "Moderate Song"}
        selected = select_songs_for_moment(
            "louvor", 2, sample_songs, recency, already
        )
        titles = [t for t, _ in selected]
        assert "Upbeat Song" not in titles
        assert "Moderate Song" not in titles

    def test_mutates_already_selected(self, sample_songs, fixed_random_seed):
        recency = {t: 1.0 for t in sample_songs}
        already = set()
        select_songs_for_moment("louvor", 2, sample_songs, recency, already)
        assert len(already) == 2

    def test_override_not_in_songs_skipped(self, sample_songs, fixed_random_seed):
        recency = {t: 1.0 for t in sample_songs}
        selected = select_songs_for_moment(
            "louvor",
            4,
            sample_songs,
            recency,
            set(),
            overrides=["Nonexistent Song"],
        )
        titles = [t for t, _ in selected]
        assert "Nonexistent Song" not in titles

    def test_no_candidates_returns_empty(self, fixed_random_seed):
        songs = {"A": make_song(title="A", tags={"prelúdio": 3})}
        recency = {"A": 1.0}
        selected = select_songs_for_moment(
            "louvor", 1, songs, recency, set()
        )
        assert selected == []

    def test_deterministic_with_seed(self, sample_songs):
        recency = {t: 1.0 for t in sample_songs}
        random.seed(42)
        first = select_songs_for_moment("louvor", 4, sample_songs, recency, set())
        random.seed(42)
        second = select_songs_for_moment(
            "louvor", 4, sample_songs, recency, set()
        )
        assert first == second


# ---------------------------------------------------------------------------
# get_song_usage_history
# ---------------------------------------------------------------------------


class TestGetSongUsageHistory:
    def test_found_in_multiple_dates(self, sample_history):
        usages = get_song_usage_history("Moderate Song", sample_history)
        assert len(usages) == 2
        # Should be ascending by date
        assert usages[0]["date"] == "2026-01-01"
        assert usages[1]["date"] == "2026-01-15"

    def test_not_found(self, sample_history):
        usages = get_song_usage_history("Nonexistent Song", sample_history)
        assert usages == []

    def test_ascending_order(self, sample_history):
        usages = get_song_usage_history("Upbeat Song", sample_history)
        dates = [u["date"] for u in usages]
        assert dates == sorted(dates)

    def test_moments_included(self, sample_history):
        usages = get_song_usage_history("Reflective Song", sample_history)
        # In 2026-01-01: louvor + ofertório
        entry_jan01 = next(u for u in usages if u["date"] == "2026-01-01")
        assert set(entry_jan01["moments"]) == {"louvor", "ofertório"}

    def test_missing_date_key_skipped(self):
        history = [{"moments": {"louvor": ["A"]}}]
        usages = get_song_usage_history("A", history)
        assert usages == []


# ---------------------------------------------------------------------------
# get_days_since_last_use
# ---------------------------------------------------------------------------


class TestGetDaysSinceLastUse:
    def test_known_song(self, sample_history):
        days = get_days_since_last_use(
            "Upbeat Song", sample_history, current_date="2026-02-15"
        )
        # Most recent use: 2026-01-15, so 31 days
        assert days == 31

    def test_never_used(self, sample_history):
        days = get_days_since_last_use(
            "Nonexistent Song", sample_history, current_date="2026-02-15"
        )
        assert days is None

    def test_malformed_date_skipped(self):
        history = [{"date": "bad-date", "moments": {"louvor": ["A"]}}]
        days = get_days_since_last_use("A", history, current_date="2026-02-15")
        assert days is None

    @freeze_time("2026-02-15")
    def test_current_date_none_uses_today(self, sample_history):
        days = get_days_since_last_use("Upbeat Song", sample_history)
        assert days == 31
