"""End-to-end tests for ``scripts/reconstruct_from_outputs.py``.

Runs against the filesystem backend in ``tmp_project`` so no database is
needed; the script only talks to the repository protocols.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from library.formatter import format_setlist_markdown
from library.models import Setlist
from library.repositories import get_repositories
from scripts.reconstruct_from_outputs import main
from tests.helpers.factories import make_song

NEW_CONTENT = "### Sublime (E)\n\nE      B\nSublime lyrics\n"
EDITED_CONTENT = "### Upbeat Song (D)\n\nD       G\nNew lyrics...\n"


@pytest.fixture
def project(tmp_project: Path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_project)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    return tmp_project


def _write_setlist(project: Path, setlist: Setlist, songs: dict) -> Path:
    rel = Path(setlist.event_type) if setlist.event_type else Path()
    path = project / "output" / rel / f"{setlist.setlist_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_setlist_markdown(setlist, songs), encoding="utf-8")
    return path


def _seed_newer_setlist(project: Path) -> None:
    songs = {
        "Upbeat Song": make_song(title="Upbeat Song", content=EDITED_CONTENT),
        "Sublime": make_song(title="Sublime", content=NEW_CONTENT),
    }
    _write_setlist(
        project,
        Setlist(date="2026-09-13", moments={"louvor": ["Upbeat Song", "Sublime"]}),
        songs,
    )


def test_dry_run_reports_plan_and_writes_nothing(project):
    _seed_newer_setlist(project)

    result = CliRunner().invoke(main, ["--dry-run"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "Sublime" in result.output
    assert "Upbeat Song" in result.output
    assert "2026-09-13" in result.output
    repos = get_repositories(backend="filesystem", base_path=project)
    assert not repos.songs.exists("Sublime")
    assert repos.songs.get_by_title("Upbeat Song").content != EDITED_CONTENT
    assert not repos.history.exists("2026-09-13")


def test_apply_prompts_for_new_song_then_writes_everything(project):
    _seed_newer_setlist(project)
    # energy, weight for louvor, extra moments, youtube, event types
    answers = "2\n5\n\n\n\n"

    result = CliRunner().invoke(main, [], input=answers, catch_exceptions=False)

    assert result.exit_code == 0, result.output
    repos = get_repositories(backend="filesystem", base_path=project)
    sublime = repos.songs.get_by_title("Sublime")
    assert sublime.energy == 2
    assert sublime.tags == {"louvor": 5}
    assert sublime.content == NEW_CONTENT
    assert sublime.youtube_url == ""
    assert sublime.event_types == []
    assert repos.songs.get_by_title("Upbeat Song").content == EDITED_CONTENT
    assert repos.history.get_by_date("2026-09-13")["moments"] == {
        "louvor": ["Upbeat Song", "Sublime"]
    }


def test_second_run_has_nothing_to_do(project):
    _seed_newer_setlist(project)
    runner = CliRunner()
    runner.invoke(main, [], input="2\n5\n\n\n\n", catch_exceptions=False)

    result = runner.invoke(main, ["--dry-run"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "Nothing to do" in result.output


def test_pre_dump_setlist_is_skipped_with_reason(project):
    songs = {"Upbeat Song": make_song(title="Upbeat Song")}
    _write_setlist(project, Setlist(date="2026-04-20", moments={"louvor": ["Upbeat Song"]}), songs)

    result = CliRunner().invoke(main, ["--dry-run"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "2026-04-20" in result.output
    assert "--include 2026-04-20" in result.output
    assert "Nothing to do" in result.output


def test_unknown_event_type_directory_aborts(project):
    songs = {"Upbeat Song": make_song(title="Upbeat Song")}
    _write_setlist(
        project,
        Setlist(date="2026-09-13", moments={"louvor": ["Upbeat Song"]}, event_type="ghost"),
        songs,
    )

    result = CliRunner().invoke(main, ["--dry-run"])

    assert result.exit_code != 0
    assert "ghost" in result.output
