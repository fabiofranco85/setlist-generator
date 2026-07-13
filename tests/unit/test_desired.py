"""Tests for desired-song resolution and moment assignment."""

import pytest

from library.desired import (
    assign_desired_to_moments,
    parse_desired,
    plan_desired_songs,
    resolve_desired_songs,
)
from tests.helpers.factories import make_song


# --------------------------------------------------------------------------
# parse_desired
# --------------------------------------------------------------------------


def test_parse_desired_splits_on_commas_and_trims():
    assert parse_desired("Bondade de Deus, Precioso ,Vou Seguir Com Fé") == [
        "Bondade de Deus",
        "Precioso",
        "Vou Seguir Com Fé",
    ]


def test_parse_desired_drops_empty_entries():
    assert parse_desired("Oceanos,, ,Hosana,") == ["Oceanos", "Hosana"]


def test_parse_desired_returns_empty_for_blank_input():
    assert parse_desired("") == []
    assert parse_desired("   ") == []
    assert parse_desired(None) == []


def test_parse_desired_deduplicates_preserving_order():
    """A song named twice should be placed once, not fight itself for a slot."""
    assert parse_desired("Oceanos, Hosana, oceanos") == ["Oceanos", "Hosana"]


# --------------------------------------------------------------------------
# resolve_desired_songs
# --------------------------------------------------------------------------


@pytest.fixture
def songs():
    return {
        "Bondade de Deus": make_song(title="Bondade de Deus", tags={"louvor": 7}, energy=4),
        "Precioso": make_song(title="Precioso", tags={"louvor": 3}, energy=4),
        "Vou Seguir Com Fé": make_song(
            title="Vou Seguir Com Fé", tags={"prelúdio": 3, "poslúdio": 3}, energy=2
        ),
        "Oceanos": make_song(title="Oceanos", tags={"louvor": 2}, energy=3),
    }


def test_resolve_matches_exact_titles(songs):
    resolved = resolve_desired_songs(["Oceanos"], songs)
    assert list(resolved) == ["Oceanos"]


def test_resolve_is_case_insensitive(songs):
    """The goal's own example writes 'com Fé' while the database stores 'Com Fé'."""
    resolved = resolve_desired_songs(["vou seguir com fé", "BONDADE DE DEUS"], songs)
    assert list(resolved) == ["Vou Seguir Com Fé", "Bondade de Deus"]


def test_resolve_returns_canonical_titles(songs):
    """Downstream code must receive the database's spelling, not the user's."""
    resolved = resolve_desired_songs(["precioso"], songs)
    assert list(resolved) == ["Precioso"]
    assert resolved["Precioso"] is songs["Precioso"]


def test_resolve_raises_for_unknown_song(songs):
    with pytest.raises(ValueError, match="Nao Existe"):
        resolve_desired_songs(["Nao Existe"], songs)


def test_resolve_reports_every_unknown_song_at_once(songs):
    """One run should surface all typos, not just the first."""
    with pytest.raises(ValueError) as exc:
        resolve_desired_songs(["Oceanos", "Bogus One", "Bogus Two"], songs)

    message = str(exc.value)
    assert "Bogus One" in message
    assert "Bogus Two" in message


def test_resolve_suggests_close_matches(songs):
    with pytest.raises(ValueError, match="Oceanos"):
        resolve_desired_songs(["Oceanoss"], songs)


# --------------------------------------------------------------------------
# assign_desired_to_moments
# --------------------------------------------------------------------------


def test_assigns_single_moment_song_to_its_moment(songs):
    assignment = assign_desired_to_moments(
        {"Bondade de Deus": songs["Bondade de Deus"]},
        capacities={"louvor": 4, "prelúdio": 1},
    )
    assert assignment == {"louvor": ["Bondade de Deus"]}


def test_prefers_the_highest_weight_moment():
    """A song tagged louvor(7) + prelúdio(2) belongs in louvor."""
    song = make_song(title="Dual", tags={"louvor": 7, "prelúdio": 2})
    assignment = assign_desired_to_moments(
        {"Dual": song}, capacities={"louvor": 4, "prelúdio": 1}
    )
    assert assignment == {"louvor": ["Dual"]}


def test_breaks_weight_ties_by_service_order():
    """Equal weights: the moment declared first in the config wins."""
    song = make_song(title="Tied", tags={"prelúdio": 3, "poslúdio": 3})
    assignment = assign_desired_to_moments(
        {"Tied": song}, capacities={"prelúdio": 1, "poslúdio": 1}
    )
    assert assignment == {"prelúdio": ["Tied"]}


def test_relocates_an_earlier_song_so_that_all_desired_songs_fit():
    """The backtracking case that plain greedy-by-weight gets wrong.

    Both songs prefer prelúdio, which holds exactly one. A greedy pass seats
    the first and then declares the second unfittable — even though poslúdio
    is wide open. The augmenting path must re-seat the first into poslúdio.
    """
    a = make_song(title="A", tags={"prelúdio": 3, "poslúdio": 3})
    b = make_song(title="B", tags={"prelúdio": 5})

    assignment = assign_desired_to_moments(
        {"A": a, "B": b}, capacities={"prelúdio": 1, "poslúdio": 1}
    )

    assert assignment["prelúdio"] == ["B"]
    assert assignment["poslúdio"] == ["A"]


def test_respects_moment_capacity():
    """Five louvor-only songs cannot fit into four louvor slots."""
    desired = {
        f"Song {i}": make_song(title=f"Song {i}", tags={"louvor": 3}) for i in range(5)
    }
    with pytest.raises(ValueError, match="louvor"):
        assign_desired_to_moments(desired, capacities={"louvor": 4})


def test_raises_when_song_has_no_taggable_moment():
    """A song tagged only for moments outside the active config cannot be placed."""
    song = make_song(title="Natal Only", tags={"natal-prelúdio": 3})
    with pytest.raises(ValueError, match="Natal Only"):
        assign_desired_to_moments({"Natal Only": song}, capacities={"louvor": 4})


def test_zero_capacity_moment_is_unusable():
    """Overrides can consume every slot in a moment, leaving no room."""
    song = make_song(title="Solo", tags={"louvor": 3})
    with pytest.raises(ValueError, match="Solo"):
        assign_desired_to_moments({"Solo": song}, capacities={"louvor": 0})


def test_empty_desired_set_assigns_nothing():
    assert assign_desired_to_moments({}, capacities={"louvor": 4}) == {}


# --------------------------------------------------------------------------
# plan_desired_songs (resolution + capacity + assignment)
# --------------------------------------------------------------------------


def test_plan_end_to_end_matches_the_goal_example(songs):
    plan = plan_desired_songs(
        ["Bondade de Deus", "Precioso", "Vou Seguir com Fé"],
        songs,
        moments_config={"prelúdio": 1, "louvor": 4, "poslúdio": 1},
    )
    assert plan == {
        "louvor": ["Bondade de Deus", "Precioso"],
        "prelúdio": ["Vou Seguir Com Fé"],
    }


def test_plan_discounts_capacity_already_taken_by_overrides(songs):
    """Overrides consume slots first; desired songs compete for what's left."""
    with pytest.raises(ValueError, match="louvor"):
        plan_desired_songs(
            ["Bondade de Deus", "Precioso"],
            songs,
            moments_config={"louvor": 3},
            overrides={"louvor": ["A", "B"]},  # 2 of 3 louvor slots gone
        )


def test_plan_skips_songs_already_pinned_by_an_override(songs):
    """An overridden song is already guaranteed — it must not also claim a slot."""
    plan = plan_desired_songs(
        ["Bondade de Deus", "Precioso"],
        songs,
        moments_config={"louvor": 2},
        overrides={"louvor": ["Precioso"]},
    )
    assert plan == {"louvor": ["Bondade de Deus"]}


def test_plan_rejects_song_unavailable_for_the_event_type():
    """Event-type filtering happens upstream; the song simply isn't in the pool."""
    pool = {"Main Song": make_song(title="Main Song", tags={"louvor": 3})}
    with pytest.raises(ValueError, match="Youth Anthem"):
        plan_desired_songs(
            ["Youth Anthem"], pool, moments_config={"louvor": 4}
        )
