"""End-to-end ``CliRunner`` tests for ``songbook remove``.

These tests guard the contract from the user's perspective:

* ``--moment X --position N`` removes one song and rewrites the history
  JSON + markdown.
* ``--moment X --all`` removes the whole moment.
* The "last song cascades to remove the moment" rule fires through the
  CLI surface, not just inside the library function.
* Routing through label / event-type subdirectories matches the rest of
  the CLI surface (no clobbering main-event-type files when removing
  from a youth setlist, etc.).
* Validation errors (missing setlist, missing moment, bad position,
  conflicting flags) come back as non-zero exit codes with no on-disk
  mutation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


# ---------------------------------------------------------------------------
# Fixtures — a tmp project with one seeded setlist
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """Tmp project pre-seeded with a 2026-02-15 setlist (default event type)."""
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_project)

    setlist_json = {
        "date": "2026-02-15",
        "moments": {
            "prelúdio": ["Upbeat Song"],
            "louvor": [
                "Upbeat Song", "Moderate Song",
                "Reflective Song", "Worship Song",
            ],
            "ofertório": ["Reflective Song"],
            "saudação": ["Moderate Song"],
            "crianças": ["Upbeat Song"],
            "poslúdio": ["Worship Song"],
        },
    }
    (tmp_project / "history" / "2026-02-15.json").write_text(
        json.dumps(setlist_json, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_project / "output" / "2026-02-15.md").write_text(
        "# Stale markdown\n", encoding="utf-8"
    )
    return tmp_project


@pytest.fixture()
def project_with_labeled(project) -> Path:
    """``project`` plus a labeled variant for the same date."""
    setlist_json = {
        "date": "2026-02-15",
        "label": "evening",
        "moments": {
            "louvor": ["Upbeat Song", "Worship Song"],
            "poslúdio": ["Worship Song"],
        },
    }
    (project / "history" / "2026-02-15_evening.json").write_text(
        json.dumps(setlist_json, ensure_ascii=False), encoding="utf-8"
    )
    return project


@pytest.fixture()
def project_with_youth(project) -> Path:
    """``project`` plus a youth event type with its own setlist on a different date.

    The 'final' moment is chosen deliberately so that it doesn't collide
    with the default ``MOMENTS_CONFIG`` — a removal in youth must NOT
    leak into the default-type setlist.
    """
    (project / "history" / "youth").mkdir(parents=True, exist_ok=True)
    (project / "event_types.json").write_text(
        json.dumps(
            {
                "event_types": {
                    "main": {
                        "name": "Main", "description": "",
                        "moments": {
                            "prelúdio": 1, "ofertório": 1, "saudação": 1,
                            "crianças": 1, "louvor": 4, "poslúdio": 1,
                        },
                        "moments_order": [
                            "prelúdio", "ofertório", "saudação",
                            "crianças", "louvor", "poslúdio",
                        ],
                    },
                    "youth": {
                        "name": "Youth", "description": "",
                        "moments": {"louvor": 2, "final": 1},
                        "moments_order": ["louvor", "final"],
                    },
                },
                "default_slug": "main",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project / "history" / "youth" / "2026-03-20.json").write_text(
        json.dumps(
            {
                "date": "2026-03-20",
                "event_type": "youth",
                "moments": {
                    "louvor": ["Upbeat Song", "Worship Song"],
                    "final": ["Reflective Song"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return project


def _read_history(project: Path, filename: str) -> dict:
    return json.loads((project / "history" / filename).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Single-song removal
# ---------------------------------------------------------------------------


class TestRemoveSinglesong:
    def test_removes_song_at_position_from_moment(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--position", "2", "--date", "2026-02-15"],
        )
        assert result.exit_code == 0, result.output

        data = _read_history(project, "2026-02-15.json")
        # Position 2 (1-indexed) was "Moderate Song"
        assert "Moderate Song" not in data["moments"]["louvor"]
        assert data["moments"]["louvor"] == [
            "Upbeat Song", "Reflective Song", "Worship Song",
        ]

    def test_regenerates_markdown(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--position", "1", "--date", "2026-02-15"],
        )
        assert result.exit_code == 0, result.output

        md = (project / "output" / "2026-02-15.md").read_text(encoding="utf-8")
        # Stale stub is gone; real markdown now contains a real moment header
        assert "Stale markdown" not in md
        assert "louvor" in md.lower() or "louvor" in md


# ---------------------------------------------------------------------------
# Cascade — removing the last song drops the moment
# ---------------------------------------------------------------------------


class TestSingleSongCascade:
    def test_removing_only_song_in_moment_drops_moment(self, project):
        runner = CliRunner()
        # prelúdio has exactly one song
        result = runner.invoke(
            cli,
            ["remove", "--moment", "prelúdio", "--position", "1", "--date", "2026-02-15"],
        )
        assert result.exit_code == 0, result.output

        data = _read_history(project, "2026-02-15.json")
        assert "prelúdio" not in data["moments"]
        # Other moments survive
        assert "louvor" in data["moments"]

    def test_cascade_message_warns_user(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "prelúdio", "--position", "1", "--date", "2026-02-15"],
        )
        assert result.exit_code == 0, result.output
        # The CLI must give a heads-up that the moment is going away —
        # silently dropping the moment would be surprising.
        assert "only one song" in result.output
        assert "dropped" in result.output


# ---------------------------------------------------------------------------
# Whole-moment removal (--all)
# ---------------------------------------------------------------------------


class TestRemoveEntireMoment:
    def test_all_flag_drops_moment_and_all_songs(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--all", "--date", "2026-02-15"],
        )
        assert result.exit_code == 0, result.output

        data = _read_history(project, "2026-02-15.json")
        assert "louvor" not in data["moments"]
        # Other moments untouched
        assert data["moments"]["prelúdio"] == ["Upbeat Song"]
        assert len(data["moments"]) == 5

    def test_all_flag_works_on_single_song_moment(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "ofertório", "--all", "--date", "2026-02-15"],
        )
        assert result.exit_code == 0, result.output

        data = _read_history(project, "2026-02-15.json")
        assert "ofertório" not in data["moments"]


# ---------------------------------------------------------------------------
# Label routing
# ---------------------------------------------------------------------------


class TestRemoveInLabeledSetlist:
    def test_label_targets_correct_setlist(self, project_with_labeled):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "remove", "--moment", "louvor", "--position", "1",
                "--date", "2026-02-15", "--label", "evening",
            ],
        )
        assert result.exit_code == 0, result.output

        labeled = _read_history(project_with_labeled, "2026-02-15_evening.json")
        assert labeled["moments"]["louvor"] == ["Worship Song"]

        # Primary setlist is untouched
        primary = _read_history(project_with_labeled, "2026-02-15.json")
        assert len(primary["moments"]["louvor"]) == 4


# ---------------------------------------------------------------------------
# Event-type routing
# ---------------------------------------------------------------------------


class TestRemoveInEventTypeSubdirectory:
    def test_youth_remove_writes_to_youth_subdir(self, project_with_youth):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "remove", "--moment", "louvor", "--position", "1",
                "--date", "2026-03-20", "-e", "youth",
            ],
        )
        assert result.exit_code == 0, result.output

        # The youth file got updated
        data = _read_history(project_with_youth, "youth/2026-03-20.json")
        assert data["moments"]["louvor"] == ["Worship Song"]

        # Crucially: no main-event-type file should appear at the root
        # for the youth date (that would be the bug that motivated the
        # existing event-type subdirectory routing).
        assert not (project_with_youth / "history" / "2026-03-20.json").exists()


# ---------------------------------------------------------------------------
# Validation — must produce non-zero exit + leave disk untouched
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_position_and_all_are_mutually_exclusive(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "remove", "--moment", "louvor", "--position", "1",
                "--all", "--date", "2026-02-15",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_neither_position_nor_all_errors(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--date", "2026-02-15"],
        )
        assert result.exit_code != 0
        assert "--position" in result.output or "--all" in result.output

    def test_missing_setlist_errors(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--position", "1", "--date", "2099-01-01"],
        )
        assert result.exit_code != 0
        # The on-disk fixture must be untouched
        data = _read_history(project, "2026-02-15.json")
        assert len(data["moments"]["louvor"]) == 4

    def test_unknown_moment_errors(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "bogus", "--position", "1", "--date", "2026-02-15"],
        )
        assert result.exit_code != 0
        assert "not in this setlist" in result.output
        # Disk untouched
        data = _read_history(project, "2026-02-15.json")
        assert len(data["moments"]["louvor"]) == 4

    def test_position_out_of_range_errors(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--position", "99", "--date", "2026-02-15"],
        )
        assert result.exit_code != 0
        assert "out of range" in result.output

    def test_position_zero_errors(self, project):
        """1-indexed input: --position 0 must be rejected."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--position", "0", "--date", "2026-02-15"],
        )
        assert result.exit_code != 0
        assert "out of range" in result.output


# ---------------------------------------------------------------------------
# Stale-PDF notice — pin the hint format
# ---------------------------------------------------------------------------


class TestStalePdfNotice:
    """The CLI emits a stale-PDF notice when an existing PDF is found.

    The notice must:
    * be emitted only when a PDF actually exists,
    * always include ``--date {resolved_date}`` even if the user invoked
      ``remove`` without ``--date`` (otherwise the suggested ``songbook
      pdf`` might pick a different "latest" setlist later — see the
      review of this feature for the footgun details).
    """

    def test_no_notice_when_no_pdf_exists(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remove", "--moment", "louvor", "--position", "1", "--date", "2026-02-15"],
        )
        assert result.exit_code == 0, result.output
        assert "stale" not in result.output.lower()

    def test_notice_names_resolved_date_when_date_flag_omitted(self, project):
        """If the user runs ``remove`` without ``--date``, the regenerate
        hint must still include ``--date <resolved>`` so the suggested
        command can't be hijacked by a later "latest" setlist.
        """
        # Seed a PDF on disk so the notice fires
        (project / "output" / "2026-02-15.pdf").write_bytes(b"%PDF-stub")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            # Note: no --date flag → "latest" resolution
            ["remove", "--moment", "louvor", "--position", "1"],
        )
        assert result.exit_code == 0, result.output
        assert "stale" in result.output.lower()
        # The crucial assertion — the date is named explicitly
        assert "--date 2026-02-15" in result.output
