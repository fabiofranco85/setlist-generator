"""End-to-end ``CliRunner`` tests for ``songbook add-to-setlist``.

The mirror of ``test_remove_cli.py``. What the user's contract is:

* ``--moment X --song S`` appends S to that moment and rewrites history +
  markdown.
* ``--position N`` puts it at that 1-indexed slot instead.
* Omitting ``--song`` opens the song picker.
* A moment the setlist does not have yet is created.
* Insertion is deliberately permissive about tags (a song need not be
  tagged for the moment) but strict about duplicates.
* Validation errors exit non-zero and leave the setlist on disk untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """Tmp project with a sparse setlist, leaving songs free to insert."""
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_project)

    # Two extra songs so a full louvor still leaves candidates free.
    with open(tmp_project / "database.csv", "a", encoding="utf-8") as f:
        f.write("Quiet Song;4;ofertório(3);\n")
        f.write("Spare Song;2;crianças(3);\n")
    for name, key in [("Quiet Song", "D"), ("Spare Song", "A")]:
        (tmp_project / "chords" / f"{name}.md").write_text(
            f"### {name} ({key})\n\n{key}    G\nLyrics...\n", encoding="utf-8"
        )

    (tmp_project / "history" / "2026-02-15.json").write_text(
        json.dumps(
            {
                "date": "2026-02-15",
                "moments": {
                    "prelúdio": ["Upbeat Song"],
                    "louvor": ["Moderate Song", "Reflective Song"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_project / "output" / "2026-02-15.md").write_text(
        "# Stale markdown\n", encoding="utf-8"
    )
    return tmp_project


def _history(project: Path, name: str = "2026-02-15.json") -> dict:
    return json.loads((project / "history" / name).read_text(encoding="utf-8"))


def _run(*args):
    return CliRunner().invoke(cli, ["add-to-setlist", *args])


class TestInsertion:
    def test_song_is_appended_when_no_position_given(self, project):
        result = _run("--moment", "louvor", "--song", "Worship Song",
                      "--date", "2026-02-15")

        assert result.exit_code == 0, result.output
        assert _history(project)["moments"]["louvor"] == [
            "Moderate Song", "Reflective Song", "Worship Song",
        ]

    def test_position_places_the_song_at_that_slot(self, project):
        result = _run("--moment", "louvor", "--song", "Worship Song",
                      "--position", "1", "--date", "2026-02-15")

        assert result.exit_code == 0, result.output
        assert _history(project)["moments"]["louvor"] == [
            "Worship Song", "Moderate Song", "Reflective Song",
        ]

    def test_a_moment_the_setlist_lacks_is_created(self, project):
        result = _run("--moment", "crianças", "--song", "Spare Song",
                      "--date", "2026-02-15")

        assert result.exit_code == 0, result.output
        assert _history(project)["moments"]["crianças"] == ["Spare Song"]

    def test_a_song_not_tagged_for_the_moment_is_accepted(self, project):
        """Deliberately permissive: the user named both song and slot."""
        result = _run("--moment", "ofertório", "--song", "Worship Song",
                      "--date", "2026-02-15")

        assert result.exit_code == 0, result.output
        assert _history(project)["moments"]["ofertório"] == ["Worship Song"]

    def test_markdown_is_regenerated(self, project):
        _run("--moment", "louvor", "--song", "Worship Song", "--date", "2026-02-15")

        markdown = (project / "output" / "2026-02-15.md").read_text(encoding="utf-8")
        assert "Stale markdown" not in markdown
        assert "Worship Song" in markdown


class TestPicker:
    def test_picker_opens_when_no_song_is_given(self, project, mocker):
        from cli.commands import add_to_setlist as cmd

        pick = mocker.patch.object(cmd, "pick_song", return_value="Worship Song")
        result = _run("--moment", "louvor", "--date", "2026-02-15")

        assert result.exit_code == 0, result.output
        assert pick.call_count == 1
        assert "Worship Song" in _history(project)["moments"]["louvor"]

    def test_picker_hides_songs_already_in_the_setlist(self, project, mocker):
        from cli.commands import add_to_setlist as cmd

        pick = mocker.patch.object(cmd, "pick_song", return_value="Worship Song")
        _run("--moment", "louvor", "--date", "2026-02-15")

        excluded = pick.call_args.kwargs["exclude"]
        assert {"Upbeat Song", "Moderate Song", "Reflective Song"} <= excluded

    def test_cancelling_the_picker_writes_nothing(self, project, mocker):
        from cli.commands import add_to_setlist as cmd

        mocker.patch.object(cmd, "pick_song", return_value=None)
        result = _run("--moment", "louvor", "--date", "2026-02-15")

        assert _history(project)["moments"]["louvor"] == [
            "Moderate Song", "Reflective Song",
        ]
        assert "ancel" in result.output


class TestValidation:
    def test_unknown_song_errors_without_touching_the_setlist(self, project):
        result = _run("--moment", "louvor", "--song", "Nope", "--date", "2026-02-15")

        assert result.exit_code != 0
        assert _history(project)["moments"]["louvor"] == [
            "Moderate Song", "Reflective Song",
        ]

    def test_a_song_already_in_the_setlist_errors(self, project):
        result = _run("--moment", "louvor", "--song", "Upbeat Song",
                      "--date", "2026-02-15")

        assert result.exit_code != 0
        assert "already in this setlist" in result.output

    def test_position_out_of_range_errors(self, project):
        result = _run("--moment", "louvor", "--song", "Worship Song",
                      "--position", "9", "--date", "2026-02-15")

        assert result.exit_code != 0
        assert _history(project)["moments"]["louvor"] == [
            "Moderate Song", "Reflective Song",
        ]

    def test_position_zero_errors(self, project):
        result = _run("--moment", "louvor", "--song", "Worship Song",
                      "--position", "0", "--date", "2026-02-15")

        assert result.exit_code != 0

    def test_missing_setlist_errors(self, project):
        result = _run("--moment", "louvor", "--song", "Worship Song",
                      "--date", "2026-12-25")

        assert result.exit_code != 0


class TestReporting:
    def test_exceeding_the_configured_count_is_allowed_with_a_note(self, project):
        """louvor is configured for 4; a 5th song is legal but called out."""
        history_file = project / "history" / "2026-02-15.json"
        data = json.loads(history_file.read_text(encoding="utf-8"))
        data["moments"]["louvor"] = [
            "Moderate Song", "Reflective Song", "Worship Song", "Upbeat Song",
        ]
        data["moments"].pop("prelúdio")
        history_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = _run("--moment", "louvor", "--song", "Quiet Song",
                      "--date", "2026-02-15")

        assert result.exit_code == 0, result.output
        assert len(_history(project)["moments"]["louvor"]) == 5
        assert "5" in result.output and "4" in result.output

    def test_stale_pdf_is_flagged(self, project):
        (project / "output" / "2026-02-15.pdf").write_text("%PDF-1.4\n", encoding="utf-8")

        result = _run("--moment", "louvor", "--song", "Worship Song",
                      "--date", "2026-02-15")

        assert "stale" in result.output
        assert "songbook pdf" in result.output


class TestRouting:
    def test_label_targets_the_labeled_setlist(self, project):
        (project / "history" / "2026-02-15_evening.json").write_text(
            json.dumps(
                {
                    "date": "2026-02-15",
                    "label": "evening",
                    "moments": {"louvor": ["Upbeat Song"]},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        result = _run("--moment", "louvor", "--song", "Worship Song",
                      "--date", "2026-02-15", "--label", "evening")

        assert result.exit_code == 0, result.output
        assert _history(project, "2026-02-15_evening.json")["moments"]["louvor"] == [
            "Upbeat Song", "Worship Song",
        ]
        # The unlabeled setlist for the same date is untouched.
        assert _history(project)["moments"]["louvor"] == [
            "Moderate Song", "Reflective Song",
        ]
