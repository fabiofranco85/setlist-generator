"""Tests for song library merging and share validation."""

import pytest

from library.models import Song
from library.sharing import merge_effective_library, validate_share_request


def _song(title: str, **kwargs) -> Song:
    defaults = {"tags": {"louvor": 3}, "energy": 2, "content": ""}
    defaults.update(kwargs)
    return Song(title=title, **defaults)


class TestMergeEffectiveLibrary:

    def test_empty_all(self):
        assert merge_effective_library({}, {}, {}) == {}

    def test_global_only(self):
        songs = {"A": _song("A")}
        result = merge_effective_library(songs, {}, {})
        assert "A" in result

    def test_user_overrides_org(self):
        org = {"A": _song("A", energy=2)}
        user = {"A": _song("A", energy=4)}
        result = merge_effective_library({}, org, user)
        assert result["A"].energy == 4

    def test_org_overrides_global(self):
        g = {"A": _song("A", energy=1)}
        org = {"A": _song("A", energy=3)}
        result = merge_effective_library(g, org, {})
        assert result["A"].energy == 3

    def test_all_scopes_merged(self):
        g = {"G": _song("G")}
        org = {"O": _song("O")}
        user = {"U": _song("U")}
        result = merge_effective_library(g, org, user)
        assert set(result.keys()) == {"G", "O", "U"}


class TestValidateShareRequest:

    def test_user_to_org_valid(self):
        validate_share_request(_song("A"), "user", "org")

    def test_user_to_global_valid(self):
        validate_share_request(_song("A"), "user", "global")

    def test_org_to_global_valid(self):
        validate_share_request(_song("A"), "org", "global")

    def test_narrowing_rejected(self):
        with pytest.raises(ValueError, match="wider visibility"):
            validate_share_request(_song("A"), "global", "org")

    def test_same_scope_rejected(self):
        with pytest.raises(ValueError, match="wider visibility"):
            validate_share_request(_song("A"), "org", "org")

    def test_invalid_from_scope(self):
        with pytest.raises(ValueError, match="Invalid source scope"):
            validate_share_request(_song("A"), "invalid", "org")

    def test_invalid_to_scope(self):
        with pytest.raises(ValueError, match="Invalid target scope"):
            validate_share_request(_song("A"), "user", "invalid")
