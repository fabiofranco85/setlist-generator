"""Unit tests for ``library/remover.py``.

These tests pin down the contracts that ``remove_song_from_setlist`` and
``remove_moment_from_setlist`` expose:

* Single-song removal returns a new setlist with the song gone.
* Removing the last song in a moment **drops the moment entirely** —
  this is the cascade behavior the user-facing feature spec calls out.
* Moment removal drops every song and the moment key together.
* Validation: missing moment or out-of-range position raises ``ValueError``
  with actionable messages.
* Immutability: the source dict is never mutated.
* Metadata (``date``, ``label``, ``event_type``) is preserved when set
  and **omitted** when empty (backward-compat with old JSON files that
  predate label/event_type — see ``Setlist.to_dict``).
"""

from __future__ import annotations

import copy

import pytest

from library.remover import (
    remove_moment_from_setlist,
    remove_song_from_setlist,
)


@pytest.fixture()
def setlist_dict(sample_setlist) -> dict:
    """A 6-moment setlist dict (louvor has 4 songs, others have 1)."""
    return sample_setlist.to_dict()


# ---------------------------------------------------------------------------
# remove_song_from_setlist — happy paths
# ---------------------------------------------------------------------------


def test_remove_song_from_multi_song_moment_keeps_moment(setlist_dict):
    """Removing one of four louvor songs leaves the moment with three."""
    result = remove_song_from_setlist(setlist_dict, "louvor", position=1)

    assert "louvor" in result["moments"]
    assert result["moments"]["louvor"] == [
        "Upbeat Song", "Reflective Song", "Worship Song",
    ]
    # Other moments untouched
    assert result["moments"]["prelúdio"] == ["Upbeat Song"]


def test_remove_song_returns_new_dict(setlist_dict):
    """The original setlist dict must not be mutated."""
    before = copy.deepcopy(setlist_dict)
    _ = remove_song_from_setlist(setlist_dict, "louvor", position=0)
    assert setlist_dict == before


def test_remove_song_preserves_date_label_event_type():
    setlist = {
        "date": "2026-03-01",
        "label": "evening",
        "event_type": "youth",
        "moments": {
            "louvor": ["A", "B"],
        },
    }
    result = remove_song_from_setlist(setlist, "louvor", position=0)
    assert result["date"] == "2026-03-01"
    assert result["label"] == "evening"
    assert result["event_type"] == "youth"
    assert result["moments"]["louvor"] == ["B"]


def test_remove_song_omits_label_and_event_type_when_empty(setlist_dict):
    """Backward-compat: a setlist without label/event_type stays that way."""
    result = remove_song_from_setlist(setlist_dict, "louvor", position=0)
    assert "label" not in result
    assert "event_type" not in result


def test_remove_song_preserves_moment_order():
    """Moment iteration order must survive a removal.

    Critical because postgres JSONB round-trips lose dict insertion order,
    so this contract is what the CLI relies on for display.
    """
    setlist = {
        "date": "2026-03-01",
        "moments": {
            # Deliberately not in canonical order
            "poslúdio": ["Z"],
            "louvor": ["A", "B"],
            "prelúdio": ["P"],
        },
    }
    result = remove_song_from_setlist(setlist, "louvor", position=0)
    assert list(result["moments"].keys()) == ["poslúdio", "louvor", "prelúdio"]


# ---------------------------------------------------------------------------
# remove_song_from_setlist — cascade behavior (the feature spec)
# ---------------------------------------------------------------------------


def test_remove_only_song_in_moment_drops_moment(setlist_dict):
    """The cascade: a single-song moment is removed when its song is removed."""
    # prelúdio has exactly one song in the fixture
    result = remove_song_from_setlist(setlist_dict, "prelúdio", position=0)

    assert "prelúdio" not in result["moments"]
    # Other moments survive
    assert "louvor" in result["moments"]
    assert len(result["moments"]["louvor"]) == 4


def test_cascade_removes_last_song_of_moment_with_two_songs():
    """Removing the only remaining song after a previous removal cascades."""
    setlist = {
        "date": "2026-03-01",
        "moments": {"louvor": ["A", "B"]},
    }
    after_first = remove_song_from_setlist(setlist, "louvor", position=0)
    assert after_first["moments"]["louvor"] == ["B"]

    after_second = remove_song_from_setlist(after_first, "louvor", position=0)
    assert "louvor" not in after_second["moments"]
    assert after_second["moments"] == {}


# ---------------------------------------------------------------------------
# remove_song_from_setlist — validation
# ---------------------------------------------------------------------------


def test_remove_song_unknown_moment_raises(setlist_dict):
    with pytest.raises(ValueError, match="not in this setlist"):
        remove_song_from_setlist(setlist_dict, "nonexistent", position=0)


def test_remove_song_position_out_of_range_high(setlist_dict):
    # louvor has 4 songs (positions 0-3); position 5 is out of range
    with pytest.raises(ValueError, match="out of range"):
        remove_song_from_setlist(setlist_dict, "louvor", position=5)


def test_remove_song_position_out_of_range_negative(setlist_dict):
    with pytest.raises(ValueError, match="out of range"):
        remove_song_from_setlist(setlist_dict, "louvor", position=-1)


def test_remove_song_error_message_lists_available_moments(setlist_dict):
    """The error message should help the user find the correct moment."""
    try:
        remove_song_from_setlist(setlist_dict, "bogus", position=0)
    except ValueError as e:
        msg = str(e)
        assert "louvor" in msg  # one of the real moments
        assert "prelúdio" in msg


# ---------------------------------------------------------------------------
# remove_moment_from_setlist — happy paths
# ---------------------------------------------------------------------------


def test_remove_moment_drops_all_songs_and_moment(setlist_dict):
    """The whole 4-song louvor block disappears in one call."""
    result = remove_moment_from_setlist(setlist_dict, "louvor")

    assert "louvor" not in result["moments"]
    # Other moments survive intact
    assert "prelúdio" in result["moments"]
    assert "poslúdio" in result["moments"]


def test_remove_moment_returns_new_dict(setlist_dict):
    before = copy.deepcopy(setlist_dict)
    _ = remove_moment_from_setlist(setlist_dict, "louvor")
    assert setlist_dict == before


def test_remove_moment_preserves_metadata():
    setlist = {
        "date": "2026-03-01",
        "label": "evening",
        "event_type": "youth",
        "moments": {"louvor": ["A", "B"], "prelúdio": ["P"]},
    }
    result = remove_moment_from_setlist(setlist, "prelúdio")
    assert result["date"] == "2026-03-01"
    assert result["label"] == "evening"
    assert result["event_type"] == "youth"
    assert "prelúdio" not in result["moments"]
    assert result["moments"]["louvor"] == ["A", "B"]


def test_remove_only_moment_yields_empty_moments_dict():
    """Removing the last moment leaves an empty moments dict — valid state."""
    setlist = {
        "date": "2026-03-01",
        "moments": {"louvor": ["A"]},
    }
    result = remove_moment_from_setlist(setlist, "louvor")
    assert result["moments"] == {}


# ---------------------------------------------------------------------------
# remove_moment_from_setlist — validation
# ---------------------------------------------------------------------------


def test_remove_moment_unknown_raises(setlist_dict):
    with pytest.raises(ValueError, match="not in this setlist"):
        remove_moment_from_setlist(setlist_dict, "nonexistent")


def test_remove_moment_error_lists_available_moments(setlist_dict):
    try:
        remove_moment_from_setlist(setlist_dict, "bogus")
    except ValueError as e:
        assert "louvor" in str(e)


def test_remove_moment_from_empty_setlist_raises():
    """Empty moments → no moment to remove → helpful error."""
    setlist = {"date": "2026-03-01", "moments": {}}
    with pytest.raises(ValueError, match="not in this setlist"):
        remove_moment_from_setlist(setlist, "louvor")
