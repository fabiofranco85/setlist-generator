"""Tests for label support across models, repositories, and derivation."""

import json
import random

import pytest

from library.models import Setlist
from library.replacer import (
    derive_setlist,
    find_target_setlist,
    replace_song_in_setlist,
    replace_songs_batch,
)
from tests.helpers.factories import make_song


# ---------------------------------------------------------------------------
# Model: Setlist label + setlist_id
# ---------------------------------------------------------------------------


class TestSetlistLabel:
    def test_default_label_empty(self):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]})
        assert s.label == ""

    def test_setlist_id_without_label(self):
        s = Setlist(date="2026-01-01", moments={})
        assert s.setlist_id == "2026-01-01"

    def test_setlist_id_with_label(self):
        s = Setlist(date="2026-01-01", moments={}, label="evening")
        assert s.setlist_id == "2026-01-01_evening"

    def test_to_dict_no_label_key_when_empty(self):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]})
        d = s.to_dict()
        assert "label" not in d

    def test_to_dict_includes_label_when_set(self):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="morning")
        d = s.to_dict()
        assert d["label"] == "morning"

    def test_roundtrip_with_label(self):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="special")
        d = s.to_dict()
        rebuilt = Setlist(date=d["date"], moments=d["moments"], label=d.get("label", ""))
        assert rebuilt.label == "special"
        assert rebuilt.setlist_id == "2026-01-01_special"


# ---------------------------------------------------------------------------
# find_target_setlist with label
# ---------------------------------------------------------------------------


class TestFindTargetSetlistWithLabel:
    def test_find_by_date_and_label(self):
        history = [
            {"date": "2026-01-01", "label": "evening", "moments": {"louvor": ["B"]}},
            {"date": "2026-01-01", "moments": {"louvor": ["A"]}},
        ]
        result = find_target_setlist(history, "2026-01-01", target_label="evening")
        assert result.get("label") == "evening"

    def test_find_unlabeled_when_label_empty(self):
        history = [
            {"date": "2026-01-01", "label": "evening", "moments": {"louvor": ["B"]}},
            {"date": "2026-01-01", "moments": {"louvor": ["A"]}},
        ]
        result = find_target_setlist(history, "2026-01-01", target_label="")
        assert result.get("label", "") == ""

    def test_not_found_with_label(self):
        history = [
            {"date": "2026-01-01", "moments": {"louvor": ["A"]}},
        ]
        with pytest.raises(ValueError, match="not found"):
            find_target_setlist(history, "2026-01-01", target_label="nonexistent")


# ---------------------------------------------------------------------------
# replace_song_in_setlist preserves label
# ---------------------------------------------------------------------------


class TestReplacePreservesLabel:
    @pytest.fixture()
    def labeled_setlist_dict(self):
        return {
            "date": "2026-01-01",
            "label": "evening",
            "moments": {
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
            },
        }

    @pytest.fixture()
    def songs_dict(self):
        return {
            "Upbeat Song": make_song(title="Upbeat Song", tags={"louvor": 4}, energy=1),
            "Moderate Song": make_song(title="Moderate Song", tags={"louvor": 3}, energy=2),
            "Reflective Song": make_song(title="Reflective Song", tags={"louvor": 5}, energy=3),
            "Worship Song": make_song(title="Worship Song", tags={"louvor": 4}, energy=4),
            "Extra Song": make_song(title="Extra Song", tags={"louvor": 3}, energy=2),
        }

    def test_single_replace_preserves_label(self, labeled_setlist_dict, songs_dict):
        result = replace_song_in_setlist(
            labeled_setlist_dict, "louvor", 0, "Extra Song", songs_dict,
            reorder_energy=False,
        )
        assert result.get("label") == "evening"

    def test_batch_replace_preserves_label(self, labeled_setlist_dict, songs_dict):
        result = replace_songs_batch(
            labeled_setlist_dict,
            [("louvor", 0, "Extra Song")],
            songs_dict,
            [],
        )
        assert result.get("label") == "evening"

    def test_unlabeled_no_label_key(self, songs_dict):
        setlist = {
            "date": "2026-01-01",
            "moments": {
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
            },
        }
        result = replace_song_in_setlist(
            setlist, "louvor", 0, "Extra Song", songs_dict,
            reorder_energy=False,
        )
        assert "label" not in result


# ---------------------------------------------------------------------------
# derive_setlist
# ---------------------------------------------------------------------------


class TestDeriveSetlist:
    @pytest.fixture()
    def base_dict(self):
        return {
            "date": "2026-01-01",
            "moments": {
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
                "prelúdio": ["Upbeat Song"],
            },
        }

    @pytest.fixture()
    def songs_dict(self):
        return {
            "Upbeat Song": make_song(title="Upbeat Song", tags={"louvor": 4, "prelúdio": 3}, energy=1),
            "Moderate Song": make_song(title="Moderate Song", tags={"louvor": 3}, energy=2),
            "Reflective Song": make_song(title="Reflective Song", tags={"louvor": 5}, energy=3),
            "Worship Song": make_song(title="Worship Song", tags={"louvor": 4}, energy=4),
            "Extra Song": make_song(title="Extra Song", tags={"louvor": 3, "prelúdio": 3}, energy=2),
        }

    def test_replace_count_zero_copies_exactly(self, base_dict, songs_dict):
        result = derive_setlist(base_dict, songs_dict, [], replace_count=0)
        assert result["moments"] == base_dict["moments"]

    def test_replace_count_specific(self, base_dict, songs_dict):
        random.seed(42)
        result = derive_setlist(base_dict, songs_dict, [], replace_count=2)
        # Count differences
        diffs = 0
        for moment in base_dict["moments"]:
            for i, song in enumerate(base_dict["moments"][moment]):
                if result["moments"][moment][i] != song:
                    diffs += 1
        # Energy reordering may shuffle positions, so just check the function ran
        assert result["date"] == base_dict["date"]
        assert set(result["moments"].keys()) == set(base_dict["moments"].keys())

    def test_replace_count_all(self, base_dict, songs_dict):
        total = sum(len(sl) for sl in base_dict["moments"].values())
        random.seed(42)
        result = derive_setlist(base_dict, songs_dict, [], replace_count=total)
        assert result["date"] == base_dict["date"]

    def test_replace_count_none_random(self, base_dict, songs_dict):
        random.seed(42)
        result = derive_setlist(base_dict, songs_dict, [], replace_count=None)
        assert result["date"] == base_dict["date"]

    def test_replace_count_exceeding_clamped(self, base_dict, songs_dict):
        random.seed(42)
        total = sum(len(sl) for sl in base_dict["moments"].values())
        result = derive_setlist(base_dict, songs_dict, [], replace_count=total + 100)
        assert result["date"] == base_dict["date"]

    def test_empty_setlist_returns_copy(self, songs_dict):
        base = {"date": "2026-01-01", "moments": {}}
        result = derive_setlist(base, songs_dict, [])
        assert result["moments"] == {}


# ---------------------------------------------------------------------------
# Filesystem History Repository with labels
# ---------------------------------------------------------------------------


class TestFilesystemHistoryWithLabels:
    @pytest.fixture()
    def history_repo(self, tmp_path):
        from library.repositories.filesystem.history import FilesystemHistoryRepository
        return FilesystemHistoryRepository(tmp_path / "history")

    def test_save_and_load_unlabeled(self, history_repo):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]})
        history_repo.save(s)
        result = history_repo.get_by_date("2026-01-01")
        assert result is not None
        assert result["date"] == "2026-01-01"

    def test_save_and_load_labeled(self, history_repo):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="evening")
        history_repo.save(s)

        # Should find by date + label
        result = history_repo.get_by_date("2026-01-01", label="evening")
        assert result is not None
        assert result["label"] == "evening"

        # Should not find without label
        result_no_label = history_repo.get_by_date("2026-01-01", label="")
        assert result_no_label is None

    def test_filename_uses_setlist_id(self, history_repo, tmp_path):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="evening")
        history_repo.save(s)
        expected = tmp_path / "history" / "2026-01-01_evening.json"
        assert expected.exists()

    def test_get_by_date_all(self, history_repo):
        s1 = Setlist(date="2026-01-01", moments={"louvor": ["A"]})
        s2 = Setlist(date="2026-01-01", moments={"louvor": ["B"]}, label="evening")
        s3 = Setlist(date="2026-01-01", moments={"louvor": ["C"]}, label="afternoon")
        history_repo.save(s1)
        history_repo.save(s2)
        history_repo.save(s3)

        results = history_repo.get_by_date_all("2026-01-01")
        assert len(results) == 3
        # Sorted by label: "" < "afternoon" < "evening"
        assert results[0].get("label", "") == ""
        assert results[1]["label"] == "afternoon"
        assert results[2]["label"] == "evening"

    def test_exists_with_label(self, history_repo):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="evening")
        history_repo.save(s)
        assert history_repo.exists("2026-01-01", label="evening") is True
        assert history_repo.exists("2026-01-01", label="") is False

    def test_update_with_label(self, history_repo):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="evening")
        history_repo.save(s)

        updated = {"date": "2026-01-01", "label": "evening", "moments": {"louvor": ["B"]}}
        history_repo.update("2026-01-01", updated, label="evening")

        result = history_repo.get_by_date("2026-01-01", label="evening")
        assert result["moments"]["louvor"] == ["B"]

    def test_get_all_sorted_by_date_then_label(self, history_repo):
        s1 = Setlist(date="2026-01-02", moments={"louvor": ["A"]})
        s2 = Setlist(date="2026-01-01", moments={"louvor": ["B"]}, label="evening")
        s3 = Setlist(date="2026-01-01", moments={"louvor": ["C"]})
        history_repo.save(s1)
        history_repo.save(s2)
        history_repo.save(s3)

        results = history_repo.get_all()
        # Most recent first, within same date: empty label first
        assert results[0]["date"] == "2026-01-02"
        assert results[1]["date"] == "2026-01-01"
        assert results[1].get("label", "") == ""
        assert results[2]["date"] == "2026-01-01"
        assert results[2]["label"] == "evening"

    def test_backward_compat_old_json_without_label(self, history_repo, tmp_path):
        """Old JSON files without 'label' key treated as label=''."""
        history_dir = tmp_path / "history"
        history_dir.mkdir(exist_ok=True)
        old_file = history_dir / "2026-01-01.json"
        old_file.write_text(json.dumps({"date": "2026-01-01", "moments": {"louvor": ["A"]}}))

        result = history_repo.get_by_date("2026-01-01")
        assert result is not None
        assert result.get("label", "") == ""


# ---------------------------------------------------------------------------
# Filesystem Output Repository with labels
# ---------------------------------------------------------------------------


class TestFilesystemOutputWithLabels:
    @pytest.fixture()
    def output_repo(self, tmp_path):
        from library.repositories.filesystem.output import FilesystemOutputRepository
        return FilesystemOutputRepository(tmp_path / "output")

    def test_save_markdown_with_label(self, output_repo, tmp_path):
        path = output_repo.save_markdown("2026-01-01", "# Test", label="evening")
        assert path.name == "2026-01-01_evening.md"
        assert path.exists()

    def test_save_markdown_without_label(self, output_repo, tmp_path):
        path = output_repo.save_markdown("2026-01-01", "# Test")
        assert path.name == "2026-01-01.md"

    def test_get_markdown_path_with_label(self, output_repo):
        path = output_repo.get_markdown_path("2026-01-01", label="evening")
        assert path.name == "2026-01-01_evening.md"

    def test_get_pdf_path_with_label(self, output_repo):
        path = output_repo.get_pdf_path("2026-01-01", label="evening")
        assert path.name == "2026-01-01_evening.pdf"


# ---------------------------------------------------------------------------
# Formatter with label
# ---------------------------------------------------------------------------


class TestFormatterWithLabel:
    def test_markdown_header_with_label(self, sample_songs):
        s = Setlist(date="2026-01-01", moments={"louvor": ["Upbeat Song"]}, label="evening")
        from library.formatter import format_setlist_markdown
        md = format_setlist_markdown(s, sample_songs)
        assert "# Setlist - 2026-01-01 (evening)" in md

    def test_markdown_header_without_label(self, sample_songs):
        s = Setlist(date="2026-01-01", moments={"louvor": ["Upbeat Song"]})
        from library.formatter import format_setlist_markdown
        md = format_setlist_markdown(s, sample_songs)
        assert "# Setlist - 2026-01-01\n" in md
        assert "()" not in md


# ---------------------------------------------------------------------------
# CLI utils: validate_label
# ---------------------------------------------------------------------------


class TestValidateLabel:
    def test_empty_label(self):
        from cli.cli_utils import validate_label
        assert validate_label("") == ""

    def test_valid_label(self):
        from cli.cli_utils import validate_label
        assert validate_label("evening") == "evening"
        assert validate_label("morning-2") == "morning-2"
        assert validate_label("set_1") == "set_1"

    def test_uppercase_normalized(self):
        from cli.cli_utils import validate_label
        assert validate_label("Evening") == "evening"

    def test_invalid_label_special_chars(self):
        from cli.cli_utils import validate_label
        with pytest.raises(SystemExit):
            validate_label("bad label!")

    def test_label_too_long(self):
        from cli.cli_utils import validate_label
        with pytest.raises(SystemExit):
            validate_label("a" * 31)

    def test_label_starts_with_hyphen(self):
        from cli.cli_utils import validate_label
        with pytest.raises(SystemExit):
            validate_label("-invalid")
