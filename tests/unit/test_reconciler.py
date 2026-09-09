"""Unit tests for :mod:`library.reconciler`.

The planner projects one setlist's moments onto another event type's moment
shape. It is pure data in, pure data out: no prompting, no selection, no I/O.
The CLI turns the returned plan into prompts and auto-fills the leftovers.
"""

from __future__ import annotations

import pytest

from library.reconciler import MomentPlan, ReconcilePlan, plan_reconciliation
from tests.helpers.factories import make_song


@pytest.fixture()
def pool():
    """Songs available for the *target* event type (already filtered)."""
    return {
        "Alpha": make_song(title="Alpha", tags={"louvor": 3}),
        "Bravo": make_song(title="Bravo", tags={"louvor": 3}),
        "Charlie": make_song(title="Charlie", tags={"louvor": 3}),
        "Delta": make_song(title="Delta", tags={"prelúdio": 3}),
    }


def _plan_for(plan: ReconcilePlan, moment: str) -> MomentPlan:
    """Return the MomentPlan for a moment, failing the test when it is absent."""
    for mp in plan.moments:
        if mp.moment == moment:
            return mp
    raise AssertionError(f"no plan for moment {moment!r}")


def test_shared_moment_carries_its_songs(pool):
    plan = plan_reconciliation(
        {"louvor": ["Alpha", "Bravo"]}, {"louvor": 2}, pool
    )

    louvor = _plan_for(plan, "louvor")
    assert louvor.carried == ["Alpha", "Bravo"]
    assert louvor.slots == 0


def test_moment_order_follows_the_target_not_the_source(pool):
    plan = plan_reconciliation(
        {"louvor": ["Alpha"], "prelúdio": ["Delta"]},
        {"prelúdio": 1, "louvor": 1},
        pool,
    )

    assert [mp.moment for mp in plan.moments] == ["prelúdio", "louvor"]


def test_moment_absent_from_the_target_is_dropped_with_its_songs(pool):
    plan = plan_reconciliation(
        {"louvor": ["Alpha"], "prelúdio": ["Delta"]}, {"louvor": 1}, pool
    )

    assert [mp.moment for mp in plan.moments] == ["louvor"]
    assert plan.dropped_moments == {"prelúdio": ["Delta"]}


def test_moment_the_source_lacks_becomes_empty_slots(pool):
    plan = plan_reconciliation({"louvor": ["Alpha"]}, {"louvor": 1, "prelúdio": 1}, pool)

    prelude = _plan_for(plan, "prelúdio")
    assert prelude.carried == []
    assert prelude.slots == 1


def test_songs_beyond_the_target_count_overflow(pool):
    plan = plan_reconciliation(
        {"louvor": ["Alpha", "Bravo", "Charlie"]}, {"louvor": 2}, pool
    )

    louvor = _plan_for(plan, "louvor")
    assert louvor.carried == ["Alpha", "Bravo"]
    assert louvor.slots == 0
    assert plan.overflow == [("louvor", "Charlie")]


def test_song_missing_from_the_target_pool_is_dropped_and_frees_a_slot(pool):
    plan = plan_reconciliation(
        {"louvor": ["Alpha", "Youth Only"]}, {"louvor": 2}, pool
    )

    louvor = _plan_for(plan, "louvor")
    assert louvor.carried == ["Alpha"]
    assert louvor.slots == 1
    assert plan.unavailable == [("louvor", "Youth Only")]


def test_availability_is_filtered_before_the_count_is_applied(pool):
    """An unavailable song must not consume one of the target's slots.

    Truncating first would carry ["Alpha"] and report Charlie as overflow,
    leaving a slot empty for no reason while a perfectly legal song is thrown
    away. Filter, then truncate.
    """
    plan = plan_reconciliation(
        {"louvor": ["Alpha", "Youth Only", "Charlie"]}, {"louvor": 2}, pool
    )

    louvor = _plan_for(plan, "louvor")
    assert louvor.carried == ["Alpha", "Charlie"]
    assert louvor.slots == 0
    assert plan.overflow == []
    assert plan.unavailable == [("louvor", "Youth Only")]


def test_total_slots_sums_every_gap(pool):
    plan = plan_reconciliation(
        {"louvor": ["Alpha"]}, {"louvor": 3, "prelúdio": 2}, pool
    )

    assert plan.total_slots == 4


def test_identical_shape_needs_no_filling_and_drops_nothing(pool):
    plan = plan_reconciliation(
        {"louvor": ["Alpha", "Bravo"], "prelúdio": ["Delta"]},
        {"louvor": 2, "prelúdio": 1},
        pool,
    )

    assert plan.total_slots == 0
    assert plan.dropped_moments == {}
    assert plan.overflow == []
    assert plan.unavailable == []


def test_planning_does_not_mutate_the_source_moments(pool):
    source = {"louvor": ["Alpha", "Bravo", "Charlie"]}

    plan = plan_reconciliation(source, {"louvor": 1}, pool)
    plan.moments[0].carried.append("Bravo")

    assert source == {"louvor": ["Alpha", "Bravo", "Charlie"]}
