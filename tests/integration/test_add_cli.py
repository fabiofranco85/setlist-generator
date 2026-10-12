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


# ---------------------------------------------------------------------------
# Cifra Club import (interactive only)
# ---------------------------------------------------------------------------

_CIFRA_URL = "https://www.cifraclub.com.br/banda/cancao/"


@pytest.fixture()
def cifraclub(project, mocker):
    """Interactive terminal + a fake Cifra Club fetch (C shapes, capo 1 → Db)."""
    from library.cifraclub import ChordSheet

    mocker.patch("cli.commands.add._is_interactive", return_value=True)
    sheet = ChordSheet(
        title="Canção do Site", artist="Banda", key="C", sounding_key="Db",
        capo="1ª casa", body="[Intro] C  G\n\nC       G\nLetra de teste",
    )
    return mocker.patch("cli.commands.add._fetch_sheet", return_value=sheet)


def _add(input_text: str, *extra: str):
    # Prompt order: Cifra Club URL, key, YouTube (energy + tags come from flags).
    return CliRunner().invoke(
        cli,
        ["add", "Nova Canção", "--energy", "2", "--tags", "louvor(3)", *extra],
        input=input_text,
    )


def _chord_file(project: Path) -> str:
    return (project / "chords" / "Nova Canção.md").read_text(encoding="utf-8")


def test_add_cifraclub_blank_key_uses_sounding_key(project, cifraclub):
    result = _add(f"{_CIFRA_URL}\n\n\n", "--no-edit")
    assert result.exit_code == 0, result.output
    cifraclub.assert_called_once_with(_CIFRA_URL)
    assert "blank = Db; written in C with capo on 1ª casa" in result.output
    assert _chord_file(project) == (
        "### Nova Canção (Db)\n\n[Intro] Db Ab\n\nDb      Ab\nLetra de teste\n"  # chords keep their columns
    )


def test_add_cifraclub_explicit_key_transposes(project, cifraclub):
    result = _add(f"{_CIFRA_URL}\nd\n\n", "--no-edit")  # lowercase is accepted
    assert result.exit_code == 0, result.output
    assert _chord_file(project).startswith("### Nova Canção (D)\n\n[Intro] D  A\n")


def test_add_cifraclub_invalid_key_is_asked_again(project, cifraclub):
    result = _add(f"{_CIFRA_URL}\nH\nG\n\n", "--no-edit")
    assert result.exit_code == 0, result.output
    assert "Unknown key: H" in result.output
    assert _chord_file(project).startswith("### Nova Canção (G)\n")


def test_add_cifraclub_fetch_error_is_asked_again(project, cifraclub):
    good = cifraclub.return_value
    cifraclub.side_effect = [ValueError("No chord sheet found on the page."), good]
    result = _add(f"https://www.cifraclub.com.br/busca\n{_CIFRA_URL}\nC\n\n", "--no-edit")
    assert result.exit_code == 0, result.output
    assert "Could not import chords: No chord sheet found" in result.output
    assert _chord_file(project).startswith("### Nova Canção (C)\n\n[Intro] C  G\n")


def test_add_cifraclub_blank_url_keeps_stub(project, cifraclub):
    result = _add("\n\n", "--no-edit")
    assert result.exit_code == 0, result.output
    cifraclub.assert_not_called()
    assert _chord_file(project) == "### Nova Canção ()\n\n"


def test_add_cifraclub_opens_editor_on_imported_sheet(project, cifraclub, mocker):
    seen: dict = {}

    def _fake(argv, check):
        seen["argv"] = argv
        seen["content"] = Path(argv[-1]).read_text(encoding="utf-8")

    mocker.patch("cli.commands.edit.subprocess.run", side_effect=_fake)
    result = _add(f"{_CIFRA_URL}\n\n\n")
    assert result.exit_code == 0, result.output
    assert seen["argv"][0] == "vim"
    assert seen["content"].startswith("### Nova Canção (Db)\n")


def test_add_does_not_ask_for_cifraclub_when_not_interactive(project, mocker):
    fetch = mocker.patch("cli.commands.add._fetch_sheet")
    result = CliRunner().invoke(cli, [
        "add", "Nova Canção", "--energy", "2", "--tags", "louvor(3)", "--no-edit",
    ])
    assert result.exit_code == 0, result.output
    assert "Cifra Club" not in result.output
    fetch.assert_not_called()
