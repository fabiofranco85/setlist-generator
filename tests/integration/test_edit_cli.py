"""End-to-end CliRunner tests for ``songbook edit``.

Exercises the real ``FilesystemSongRepository`` against the ``tmp_project``
fixture so we trust the in-place edit path: chord file changes are picked
up by subsequent ``get_all()`` calls (cache invalidation) and brand-new
songs get a stub heading before the editor opens.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """tmp_project rooted as cwd with no env-var contamination."""
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.chdir(tmp_project)
    return tmp_project


def _editor_that_writes(new_body: str):
    """Build a fake subprocess.run that rewrites the file the editor was given."""
    def _fake(argv, check):  # signature matches subprocess.run(..., check=True)
        Path(argv[-1]).write_text(new_body, encoding="utf-8")
    return _fake


def test_edit_persists_changes_to_chord_file(project, mocker):
    """Editor saves a new body → chord file on disk is updated."""
    new_body = "### Upbeat Song (C)\n\nC       G\nEdited lyrics line\n"
    mocker.patch("cli.commands.edit.subprocess.run", side_effect=_editor_that_writes(new_body))

    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "Upbeat Song"])

    assert result.exit_code == 0, result.output
    assert "Saved changes" in result.output
    chord_file = project / "chords" / "Upbeat Song.md"
    assert chord_file.read_text(encoding="utf-8") == new_body


def test_edit_propagates_to_subsequent_song_loads(project, mocker):
    """After editing, a freshly built repository should see the new content
    (proves invalidate_cache() worked + writes are real)."""
    new_body = "### Reflective Song (Em)\n\nEm  Am\nFresh chord chart\n"
    mocker.patch("cli.commands.edit.subprocess.run", side_effect=_editor_that_writes(new_body))

    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "Reflective Song"])
    assert result.exit_code == 0, result.output

    from library import get_repositories
    repos = get_repositories()
    assert repos.songs.get_by_title("Reflective Song").content == new_body


def test_edit_creates_stub_for_song_with_no_chord_file(project, mocker):
    """Songs in database.csv that have no chord file yet get a stub heading."""
    # Add a new song to database.csv with no corresponding chord file.
    db = project / "database.csv"
    db.write_text(db.read_text() + "Brand New;2;louvor(3);\n", encoding="utf-8")

    captured: dict = {}

    def _fake(argv, check):
        captured["path"] = Path(argv[-1])
        captured["initial_body"] = captured["path"].read_text(encoding="utf-8")

    mocker.patch("cli.commands.edit.subprocess.run", side_effect=_fake)

    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "Brand New"])

    assert result.exit_code == 0, result.output
    chord_file = project / "chords" / "Brand New.md"
    assert chord_file.exists()
    # Editor saw a real file with a stub heading before the user edited it.
    assert captured["initial_body"].startswith("### Brand New ()")
    assert "Created" in result.output  # stub-created notice


def test_edit_unknown_song_returns_exit_1(project):
    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "Not A Real Song"])
    assert result.exit_code == 1
    assert "Song not found" in result.output


def test_editor_flag_overrides_env(project, mocker, monkeypatch):
    monkeypatch.setenv("EDITOR", "should-not-be-used")
    captured: dict = {}

    def _fake(argv, check):
        captured["argv"] = argv

    mocker.patch("cli.commands.edit.subprocess.run", side_effect=_fake)

    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "Upbeat Song", "--editor", "nano"])
    assert result.exit_code == 0, result.output
    assert captured["argv"][0] == "nano"


def test_default_editor_is_vim_when_no_env(project, mocker):
    captured: dict = {}

    def _fake(argv, check):
        captured["argv"] = argv

    mocker.patch("cli.commands.edit.subprocess.run", side_effect=_fake)

    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "Upbeat Song"])
    assert result.exit_code == 0, result.output
    assert captured["argv"][0] == "vim"
