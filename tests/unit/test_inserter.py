"""Unit tests for :mod:`library.inserter`.

The mirror of ``test_remover.py``: insertion is structural-only (no energy
reorder, no selection, no recency), positions are zero-indexed like
``remove_song_from_setlist``, and the input dict is never mutated.
"""

from __future__ import annotations

import pytest

from library.inserter import add_song_to_setlist


@pytest.fixture()
def setlist():
    return {
        "date": "2026-09-13",
        "label": "culto_dia",
        "event_type": "ceia",
        "moments": {
            "louvor": ["Alpha", "Bravo", "Charlie"],
            "ofertório": ["Delta"],
        },
    }


def test_appends_when_no_position_is_given(setlist):
    new = add_song_to_setlist(setlist, "louvor", "Echo")

    assert new["moments"]["louvor"] == ["Alpha", "Bravo", "Charlie", "Echo"]


def test_inserts_at_the_requested_position(setlist):
    new = add_song_to_setlist(setlist, "louvor", "Echo", position=1)

    assert new["moments"]["louvor"] == ["Alpha", "Echo", "Bravo", "Charlie"]


def test_position_zero_puts_the_song_first(setlist):
    new = add_song_to_setlist(setlist, "louvor", "Echo", position=0)

    assert new["moments"]["louvor"][0] == "Echo"


def test_position_one_past_the_end_appends(setlist):
    new = add_song_to_setlist(setlist, "louvor", "Echo", position=3)

    assert new["moments"]["louvor"] == ["Alpha", "Bravo", "Charlie", "Echo"]


def test_position_beyond_one_past_the_end_is_rejected(setlist):
    with pytest.raises(ValueError, match="out of range"):
        add_song_to_setlist(setlist, "louvor", "Echo", position=4)


def test_negative_position_is_rejected(setlist):
    with pytest.raises(ValueError, match="out of range"):
        add_song_to_setlist(setlist, "louvor", "Echo", position=-1)


def test_a_moment_the_setlist_lacks_is_created(setlist):
    """The mirror of remove's drop-the-moment-when-emptied cascade."""
    new = add_song_to_setlist(setlist, "crianças", "Echo")

    assert new["moments"]["crianças"] == ["Echo"]
    # Existing moments survive untouched.
    assert new["moments"]["louvor"] == ["Alpha", "Bravo", "Charlie"]


def test_a_song_already_in_the_setlist_is_rejected(setlist):
    """Duplicates break the exclusion and recency logic elsewhere."""
    with pytest.raises(ValueError, match="already in this setlist"):
        add_song_to_setlist(setlist, "louvor", "Delta")


def test_the_duplicate_check_names_the_moment_holding_the_song(setlist):
    with pytest.raises(ValueError, match="ofertório"):
        add_song_to_setlist(setlist, "louvor", "Delta")


def test_the_input_setlist_is_not_mutated(setlist):
    new = add_song_to_setlist(setlist, "louvor", "Echo")
    new["moments"]["louvor"].append("MUTATED")

    assert setlist["moments"]["louvor"] == ["Alpha", "Bravo", "Charlie"]


def test_date_label_and_event_type_are_preserved(setlist):
    new = add_song_to_setlist(setlist, "louvor", "Echo")

    assert new["date"] == "2026-09-13"
    assert new["label"] == "culto_dia"
    assert new["event_type"] == "ceia"


def test_other_moments_are_left_alone(setlist):
    new = add_song_to_setlist(setlist, "louvor", "Echo")

    assert new["moments"]["ofertório"] == ["Delta"]
