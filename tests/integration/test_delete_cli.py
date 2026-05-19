"""End-to-end CliRunner tests for ``songbook delete``.

`delete` is a destructive operation. The contract:

* ``--date`` is required. We don't default to the latest setlist for a
  destructive op — silently nuking the most recent service is never the
  user's intent.
* History JSON + ALL output files (markdown, regular PDF, lyrics-only PDF)
  are removed together. The setlist disappears from disk; partial state
  is not allowed.
* A confirmation prompt protects against typos. ``--yes`` / ``-y`` skips
  it for scripts and tests.
* Labeled setlists and event-type setlists route through the same repo
  primitives, so they're covered to lock in the routing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """tmp_project pre-seeded with a 2026-02-15 setlist on the filesystem backend."""
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_project)

    setlist_json = {
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
    (tmp_project / "history" / "2026-02-15.json").write_text(
        json.dumps(setlist_json, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_project / "output" / "2026-02-15.md").write_text(
        "# Setlist 2026-02-15\n", encoding="utf-8"
    )
    return tmp_project


# ---------------------------------------------------------------------------
# Happy path — unlabeled setlist
# ---------------------------------------------------------------------------


class TestDeleteUnlabeledSetlist:
    def test_yes_flag_removes_history_json(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15", "--yes"]
        )
        assert result.exit_code == 0, result.output
        assert not (project / "history" / "2026-02-15.json").exists()

    def test_yes_flag_removes_markdown_output(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15", "--yes"]
        )
        assert result.exit_code == 0, result.output
        assert not (project / "output" / "2026-02-15.md").exists()

    def test_reports_what_was_deleted(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15", "--yes"]
        )
        assert result.exit_code == 0, result.output
        # The user should see confirmation of what disappeared so they can
        # spot mistakes immediately (wrong date, wrong label, etc.).
        assert "2026-02-15" in result.output
        assert "2026-02-15.json" in result.output
        assert "2026-02-15.md" in result.output


# ---------------------------------------------------------------------------
# Labeled setlist — same flow, different filename routing
# ---------------------------------------------------------------------------


class TestDeleteLabeledSetlist:
    def test_label_targets_only_that_variant(self, project):
        # Add an evening variant alongside the unlabeled primary.
        evening_json = {
            "date": "2026-02-15",
            "label": "evening",
            "moments": {"louvor": ["Reflective Song"]},
        }
        (project / "history" / "2026-02-15_evening.json").write_text(
            json.dumps(evening_json, ensure_ascii=False), encoding="utf-8"
        )
        (project / "output" / "2026-02-15_evening.md").write_text(
            "# Evening\n", encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15", "--label", "evening", "--yes"]
        )
        assert result.exit_code == 0, result.output

        # Labeled variant deleted.
        assert not (project / "history" / "2026-02-15_evening.json").exists()
        assert not (project / "output" / "2026-02-15_evening.md").exists()
        # Primary untouched — labels are independent setlists.
        assert (project / "history" / "2026-02-15.json").exists()
        assert (project / "output" / "2026-02-15.md").exists()


# ---------------------------------------------------------------------------
# PDF + lyrics-only PDF cleanup
# ---------------------------------------------------------------------------


class TestDeleteRemovesAllPdfVariants:
    def test_removes_regular_pdf(self, project):
        (project / "output" / "2026-02-15.pdf").write_text("%PDF-fake\n")
        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15", "--yes"]
        )
        assert result.exit_code == 0, result.output
        assert not (project / "output" / "2026-02-15.pdf").exists()

    def test_removes_lyrics_only_pdf_variant(self, project):
        # ``--no-chords`` writes the lyrics-only variant with a ``_lyrics``
        # suffix. Deleting the setlist must clean that file too, otherwise
        # we leave orphans behind.
        (project / "output" / "2026-02-15_lyrics.pdf").write_text("%PDF-fake\n")
        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15", "--yes"]
        )
        assert result.exit_code == 0, result.output
        assert not (project / "output" / "2026-02-15_lyrics.pdf").exists()


# ---------------------------------------------------------------------------
# Event type routing
# ---------------------------------------------------------------------------


class TestDeleteEventTypeSetlist:
    def test_event_type_targets_subdirectory(self, project):
        # Build a youth event type and a setlist under its subdirectory.
        (project / "event_types.json").write_text(
            json.dumps({
                "event_types": {
                    "main": {
                        "name": "Main Service",
                        "description": "",
                        "moments": {"louvor": 4, "prelúdio": 1, "poslúdio": 1,
                                    "saudação": 1, "ofertório": 1, "crianças": 1},
                    },
                    "youth": {
                        "name": "Youth Service",
                        "description": "",
                        "moments": {"louvor": 2},
                    },
                },
            }),
            encoding="utf-8",
        )
        youth_history = project / "history" / "youth"
        youth_history.mkdir(parents=True)
        (youth_history / "2026-03-20.json").write_text(
            json.dumps({
                "date": "2026-03-20",
                "event_type": "youth",
                "moments": {"louvor": ["Upbeat Song", "Moderate Song"]},
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        youth_output = project / "output" / "youth"
        youth_output.mkdir(parents=True)
        (youth_output / "2026-03-20.md").write_text("# Youth\n")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2026-03-20", "-e", "youth", "--yes"]
        )
        assert result.exit_code == 0, result.output

        assert not (youth_history / "2026-03-20.json").exists()
        assert not (youth_output / "2026-03-20.md").exists()


# ---------------------------------------------------------------------------
# Confirmation prompt
# ---------------------------------------------------------------------------


class TestConfirmationPrompt:
    def test_without_yes_prompts_user(self, project):
        runner = CliRunner()
        # User types 'y\n' at the prompt → deletion proceeds.
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15"], input="y\n"
        )
        assert result.exit_code == 0, result.output
        assert not (project / "history" / "2026-02-15.json").exists()

    def test_declining_prompt_keeps_files(self, project):
        runner = CliRunner()
        # User types 'n\n' at the prompt → abort, files stay.
        result = runner.invoke(
            cli, ["delete", "--date", "2026-02-15"], input="n\n"
        )
        # Click's Abort raises SystemExit(1).
        assert result.exit_code == 1
        assert (project / "history" / "2026-02-15.json").exists()
        assert (project / "output" / "2026-02-15.md").exists()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_missing_date_argument(self, project):
        runner = CliRunner()
        result = runner.invoke(cli, ["delete", "--yes"])
        assert result.exit_code != 0
        # Click's auto-generated error mentions the missing option.
        assert "--date" in result.output

    def test_unknown_setlist_errors_out(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["delete", "--date", "2099-12-31", "--yes"]
        )
        assert result.exit_code != 0
        assert "2099-12-31" in result.output

    def test_unknown_setlist_does_not_touch_existing(self, project):
        runner = CliRunner()
        runner.invoke(cli, ["delete", "--date", "2099-12-31", "--yes"])
        # The real setlist must still be on disk.
        assert (project / "history" / "2026-02-15.json").exists()
        assert (project / "output" / "2026-02-15.md").exists()
