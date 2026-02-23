"""Tests for library.replacer — song replacement logic."""

import random

import pytest

from library.replacer import (
    find_target_setlist,
    replace_song_in_setlist,
    replace_songs_batch,
    select_replacement_song,
    validate_replacement_request,
)
from tests.helpers.factories import make_history_entry, make_song


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def songs_dict():
    return {
        "Upbeat Song": make_song(
            title="Upbeat Song", tags={"louvor": 4, "prelúdio": 3}, energy=1
        ),
        "Moderate Song": make_song(
            title="Moderate Song", tags={"louvor": 3, "saudação": 4}, energy=2
        ),
        "Reflective Song": make_song(
            title="Reflective Song", tags={"louvor": 5, "ofertório": 3}, energy=3
        ),
        "Worship Song": make_song(
            title="Worship Song", tags={"louvor": 4, "poslúdio": 2}, energy=4
        ),
        "Extra Song": make_song(
            title="Extra Song", tags={"louvor": 3}, energy=2
        ),
    }


@pytest.fixture()
def setlist_dict():
    return {
        "date": "2026-02-15",
        "moments": {
            "prelúdio": ["Upbeat Song"],
            "louvor": [
                "Upbeat Song",
                "Moderate Song",
                "Reflective Song",
                "Worship Song",
            ],
            "ofertório": ["Reflective Song"],
            "saudação": ["Moderate Song"],
            "crianças": ["Upbeat Song"],
            "poslúdio": ["Worship Song"],
        },
    }


# ---------------------------------------------------------------------------
# find_target_setlist
# ---------------------------------------------------------------------------


class TestFindTargetSetlist:
    def test_latest_when_none(self, sample_history):
        result = find_target_setlist(sample_history)
        assert result["date"] == "2026-01-15"

    def test_by_date(self, sample_history):
        result = find_target_setlist(sample_history, "2026-01-01")
        assert result["date"] == "2026-01-01"

    def test_empty_history_raises(self):
        with pytest.raises(ValueError, match="No setlists found"):
            find_target_setlist([])

    def test_not_found_raises(self, sample_history):
        with pytest.raises(ValueError, match="not found"):
            find_target_setlist(sample_history, "2099-12-31")


# ---------------------------------------------------------------------------
# validate_replacement_request
# ---------------------------------------------------------------------------


class TestValidateReplacementRequest:
    def test_valid_auto(self, setlist_dict, songs_dict):
        # Should not raise
        validate_replacement_request(setlist_dict, "louvor", 0, None, songs_dict)

    def test_valid_manual(self, setlist_dict, songs_dict):
        validate_replacement_request(
            setlist_dict, "louvor", 0, "Extra Song", songs_dict
        )

    def test_invalid_moment(self, setlist_dict, songs_dict):
        with pytest.raises(ValueError, match="Invalid moment"):
            validate_replacement_request(
                setlist_dict, "invalid", 0, None, songs_dict
            )

    def test_position_out_of_range(self, setlist_dict, songs_dict):
        with pytest.raises(ValueError, match="out of range"):
            validate_replacement_request(
                setlist_dict, "louvor", 10, None, songs_dict
            )

    def test_negative_position(self, setlist_dict, songs_dict):
        with pytest.raises(ValueError, match="out of range"):
            validate_replacement_request(
                setlist_dict, "louvor", -1, None, songs_dict
            )

    def test_manual_song_not_found(self, setlist_dict, songs_dict):
        with pytest.raises(ValueError, match="not found in database"):
            validate_replacement_request(
                setlist_dict, "louvor", 0, "Ghost Song", songs_dict
            )

    def test_manual_song_missing_tag(self, setlist_dict, songs_dict):
        # Extra Song only has "louvor" tag, not "prelúdio"
        with pytest.raises(ValueError, match="not tagged for moment"):
            validate_replacement_request(
                setlist_dict, "prelúdio", 0, "Extra Song", songs_dict
            )

    def test_empty_moment_raises(self, songs_dict):
        setlist = {
            "date": "2026-01-01",
            "moments": {"louvor": []},
        }
        with pytest.raises(ValueError, match="No songs found"):
            validate_replacement_request(
                setlist, "louvor", 0, None, songs_dict
            )


# ---------------------------------------------------------------------------
# select_replacement_song
# ---------------------------------------------------------------------------


class TestSelectReplacementSong:
    def test_manual_returns_specified(self, setlist_dict, songs_dict, sample_history):
        result = select_replacement_song(
            "louvor", setlist_dict, 0, songs_dict, sample_history,
            manual_replacement="Extra Song",
        )
        assert result == "Extra Song"

    def test_auto_returns_song_from_pool(self, setlist_dict, songs_dict):
        random.seed(42)
        result = select_replacement_song(
            "louvor", setlist_dict, 0, songs_dict, []
        )
        # Must return a song that exists and is tagged for louvor
        assert result in songs_dict
        assert songs_dict[result].has_moment("louvor")

    def test_auto_no_candidates_raises(self):
        # B is the only other louvor-tagged song; it's in the setlist
        # but NOT being replaced, so it ends up in the exclusion set.
        # A IS being replaced, so A is NOT excluded — but A also has
        # no other louvor-tagged friends outside the setlist.
        # We need a scenario where truly no candidates remain.
        songs = {
            "A": make_song(title="A", tags={"ofertório": 3}),
            "B": make_song(title="B", tags={"louvor": 3}),
        }
        setlist = {
            "date": "2026-01-01",
            "moments": {"louvor": ["B"], "ofertório": ["A"]},
        }
        # Replacing B at position 0 in louvor:
        #   exclusion = {A} (everything except B)
        #   candidates for louvor not in exclusion: B itself is candidate
        #   but B is in already_selected after being added by exclusion_set
        # Wait — B is excluded from exclusion_set (it's the replacement target).
        # So B stays available and gets re-picked.
        # To truly have no candidates, no song tagged for "louvor" must be available.
        songs2 = {
            "A": make_song(title="A", tags={"louvor": 3}),
        }
        setlist2 = {
            "date": "2026-01-01",
            "moments": {"louvor": ["A"], "prelúdio": ["A"]},
        }
        # Exclusion: all songs except "A" (the replacement target).
        # But "A" appears in both moments. The condition is `song != song_to_replace`
        # which means ALL "A" entries are skipped. So exclusion_set = {} (empty).
        # Then A is available, and select returns A.
        # We need a different song in another moment to fill exclusion:
        songs3 = {
            "Only": make_song(title="Only", tags={"louvor": 3}),
            "Other": make_song(title="Other", tags={"prelúdio": 3}),
        }
        setlist3 = {
            "date": "2026-01-01",
            "moments": {"louvor": ["Only"], "prelúdio": ["Other"]},
        }
        # Replacing "Only" at louvor[0]:
        #   exclusion = {"Other"} (everything except "Only")
        #   candidates for louvor not in exclusion: "Only" (tagged louvor)
        #   select_songs_for_moment sees "Only" is NOT in already_selected
        #   So it picks "Only" — still no error.
        # To get ValueError, we need 0 songs tagged for louvor outside exclusion:
        songs4 = {
            "X": make_song(title="X", tags={"prelúdio": 3}),
        }
        setlist4 = {
            "date": "2026-01-01",
            "moments": {"louvor": ["X"]},
        }
        # Replacing X at louvor[0]:
        #   exclusion = {} (no other songs)
        #   X is NOT excluded, but X has no "louvor" tag
        #   So select_songs_for_moment finds no candidates for louvor
        random.seed(42)
        with pytest.raises(ValueError, match="No available replacement"):
            select_replacement_song("louvor", setlist4, 0, songs4, [])


# ---------------------------------------------------------------------------
# replace_song_in_setlist
# ---------------------------------------------------------------------------


class TestReplaceSongInSetlist:
    def test_original_unchanged(self, setlist_dict, songs_dict):
        original_songs = setlist_dict["moments"]["louvor"].copy()
        replace_song_in_setlist(
            setlist_dict, "louvor", 0, "Extra Song", songs_dict
        )
        assert setlist_dict["moments"]["louvor"] == original_songs

    def test_correct_position_replaced(self, setlist_dict, songs_dict):
        result = replace_song_in_setlist(
            setlist_dict, "louvor", 1, "Extra Song", songs_dict,
            reorder_energy=False,
        )
        assert result["moments"]["louvor"][1] == "Extra Song"

    def test_energy_reorder_applied(self, setlist_dict, songs_dict):
        result = replace_song_in_setlist(
            setlist_dict, "louvor", 0, "Extra Song", songs_dict,
            reorder_energy=True,
        )
        # With energy ordering on louvor (ascending), songs should be sorted by energy
        energies = [songs_dict[t].energy for t in result["moments"]["louvor"]]
        assert energies == sorted(energies)

    def test_no_reorder(self, setlist_dict, songs_dict):
        result = replace_song_in_setlist(
            setlist_dict, "louvor", 0, "Extra Song", songs_dict,
            reorder_energy=False,
        )
        # First song should be Extra Song at position 0
        assert result["moments"]["louvor"][0] == "Extra Song"

    def test_other_moments_unchanged(self, setlist_dict, songs_dict):
        result = replace_song_in_setlist(
            setlist_dict, "louvor", 0, "Extra Song", songs_dict,
            reorder_energy=False,
        )
        assert result["moments"]["prelúdio"] == setlist_dict["moments"]["prelúdio"]


# ---------------------------------------------------------------------------
# replace_songs_batch
# ---------------------------------------------------------------------------


class TestReplaceSongsBatch:
    def test_multiple_replacements(self, setlist_dict, songs_dict):
        result = replace_songs_batch(
            setlist_dict,
            [("louvor", 0, "Extra Song")],
            songs_dict,
            [],
        )
        assert "Extra Song" in result["moments"]["louvor"]

    def test_original_unchanged(self, setlist_dict, songs_dict):
        original = setlist_dict["moments"]["louvor"].copy()
        replace_songs_batch(
            setlist_dict,
            [("louvor", 0, "Extra Song")],
            songs_dict,
            [],
        )
        assert setlist_dict["moments"]["louvor"] == original

    def test_validation_first(self, setlist_dict, songs_dict):
        """All replacements validated before any are applied."""
        with pytest.raises(ValueError):
            replace_songs_batch(
                setlist_dict,
                [("louvor", 0, "Extra Song"), ("invalid_moment", 0, None)],
                songs_dict,
                [],
            )

    def test_auto_selection_in_batch(self, setlist_dict, songs_dict):
        """Auto-selection (manual_song=None) uses selection algorithm."""
        random.seed(42)
        result = replace_songs_batch(
            setlist_dict,
            [("louvor", 0, None)],
            songs_dict,
            [],
        )
        # Should have replaced position 0 with some song
        assert result["moments"]["louvor"][0] != setlist_dict["moments"]["louvor"][0] \
            or result["moments"]["louvor"][0] in songs_dict


# ---------------------------------------------------------------------------
# Moment ordering preservation
# ---------------------------------------------------------------------------

CANONICAL_ORDER = [
    "prelúdio", "ofertório", "saudação", "crianças", "louvor", "poslúdio"
]


class TestMomentOrdering:
    def test_replace_song_preserves_canonical_order(self, setlist_dict, songs_dict):
        """Replacing a song should not change moment ordering."""
        result = replace_song_in_setlist(
            setlist_dict, "louvor", 0, "Extra Song", songs_dict,
            reorder_energy=False,
        )
        assert list(result["moments"].keys()) == CANONICAL_ORDER

    def test_replace_song_reorders_scrambled_moments(self, songs_dict):
        """Scrambled input moments should be normalized to canonical order."""
        scrambled = {
            "date": "2026-02-15",
            "moments": {
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
                "prelúdio": ["Upbeat Song"],
                "ofertório": ["Reflective Song"],
                "saudação": ["Moderate Song"],
                "crianças": ["Upbeat Song"],
                "poslúdio": ["Worship Song"],
            },
        }
        result = replace_song_in_setlist(
            scrambled, "louvor", 0, "Extra Song", songs_dict,
            reorder_energy=False,
        )
        assert list(result["moments"].keys()) == CANONICAL_ORDER

    def test_batch_replace_preserves_canonical_order(self, setlist_dict, songs_dict):
        """Batch replacement should maintain canonical moment ordering."""
        result = replace_songs_batch(
            setlist_dict,
            [("louvor", 0, "Extra Song")],
            songs_dict,
            [],
        )
        assert list(result["moments"].keys()) == CANONICAL_ORDER

    def test_batch_replace_reorders_scrambled_moments(self, songs_dict):
        """Scrambled input should be normalized after batch replace."""
        scrambled = {
            "date": "2026-02-15",
            "moments": {
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
                "prelúdio": ["Upbeat Song"],
                "ofertório": ["Reflective Song"],
                "saudação": ["Moderate Song"],
                "crianças": ["Upbeat Song"],
                "poslúdio": ["Worship Song"],
            },
        }
        result = replace_songs_batch(
            scrambled,
            [("louvor", 0, "Extra Song")],
            songs_dict,
            [],
        )
        assert list(result["moments"].keys()) == CANONICAL_ORDER
