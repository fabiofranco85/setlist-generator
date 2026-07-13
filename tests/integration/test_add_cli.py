"""End-to-end CliRunner tests for ``songbook add``.

Exercises the real ``FilesystemSongRepository`` against the ``tmp_project``
fixture: ``add`` creates the song row in database.csv plus a stub chord file,
validates its inputs, and (unless ``--no-edit``) opens the editor on the new
chord sheet reusing the ``edit`` machinery.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """tmp_project rooted as cwd with no env-var contamination."""
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.chdir(tmp_project)
    return tmp_project


def _db_lines(project: Path) -> list[str]:
    return (project / "database.csv").read_text(encoding="utf-8").splitlines()


def test_add_creates_song_via_flags(project):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "Novo Louvor",
        "--energy", "2",
        "--tags", "louvor(5),prelúdio",
        "--youtube", "https://youtu.be/abc123",
        "--no-edit",
    ])
    assert result.exit_code == 0, result.output
    assert "Created" in result.output

    # database.csv row
    assert any(ln.startswith("Novo Louvor;2;louvor(5),prelúdio;https://youtu.be/abc123")
               for ln in _db_lines(project)), result.output
    # stub chord file
    chord_file = project / "chords" / "Novo Louvor.md"
    assert chord_file.exists()
    assert chord_file.read_text(encoding="utf-8") == "### Novo Louvor ()\n\n"


def test_add_rejects_duplicate(project):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "Upbeat Song", "--energy", "2", "--tags", "louvor(3)", "--no-edit",
    ])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_add_requires_at_least_one_moment(project):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "Tagless", "--energy", "2", "--tags", "", "--no-edit",
    ])
    assert result.exit_code == 1
    assert "at least one moment" in result.output.lower()
    # nothing persisted
    assert not any(ln.startswith("Tagless;") for ln in _db_lines(project))


def test_add_rejects_invalid_energy(project):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "BadEnergy", "--energy", "9", "--tags", "louvor(3)", "--no-edit",
    ])
    assert result.exit_code == 1
    assert "1" in result.output and "4" in result.output
    assert not any(ln.startswith("BadEnergy;") for ln in _db_lines(project))


def test_add_rejects_invalid_youtube(project):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "BadLink", "--energy", "2", "--tags", "louvor(3)",
        "--youtube", "not-a-youtube-url", "--no-edit",
    ])
    assert result.exit_code == 1
    assert "youtube" in result.output.lower()
    assert not any(ln.startswith("BadLink;") for ln in _db_lines(project))


def test_add_rejects_invalid_weight(project):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "BadWeight", "--energy", "2", "--tags", "louvor(99)", "--no-edit",
    ])
    assert result.exit_code == 1
    assert not any(ln.startswith("BadWeight;") for ln in _db_lines(project))


def test_add_event_type_binding(project):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "Youth Anthem", "--energy", "1", "--tags", "louvor(5)",
        "-e", "youth", "--no-edit",
    ])
    assert result.exit_code == 0, result.output
    assert any("Youth Anthem;" in ln and ln.rstrip().endswith("youth")
               for ln in _db_lines(project)), result.output


def test_add_opens_editor_for_chords(project, mocker):
    """Without --no-edit, the editor opens on the new chord sheet."""
    new_body = "### Novo Louvor (G)\n\nG       C\nLetra nova\n"

    def _fake(argv, check):  # mirrors subprocess.run(..., check=True)
        Path(argv[-1]).write_text(new_body, encoding="utf-8")

    # add reuses edit's _launch_editor → patch subprocess.run there.
    mocker.patch("cli.commands.edit.subprocess.run", side_effect=_fake)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "add", "Novo Louvor", "--energy", "2", "--tags", "louvor(3)",
    ])
    assert result.exit_code == 0, result.output
    chord_file = project / "chords" / "Novo Louvor.md"
    assert chord_file.read_text(encoding="utf-8") == new_body


def test_add_interactive_prompts(project):
    """Missing fields are prompted for; blank YouTube is skipped."""
    runner = CliRunner()
    # title, energy, tags, youtube(blank)
    result = runner.invoke(
        cli,
        ["add", "--no-edit"],
        input="Cancao Nova\n3\nlouvor(4)\n\n",
    )
    assert result.exit_code == 0, result.output
    assert any(ln.startswith("Cancao Nova;3;louvor(4);") for ln in _db_lines(project)), result.output
