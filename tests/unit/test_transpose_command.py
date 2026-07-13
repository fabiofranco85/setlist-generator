"""Tests for cli.commands.transpose — the ``--save`` persistence path.

These tests guard the contract that ``transpose --save`` persists through the
repository layer (``repos.songs.update_content``) so it routes to whatever
``STORAGE_BACKEND`` is configured, instead of writing a ``chords/<song>.md``
file directly on the filesystem (which leaks filesystem output even when the
backend is postgres/supabase).
"""

from types import SimpleNamespace

import pytest

from cli.commands import transpose
from tests.helpers.factories import make_song


class _FakeSongRepository:
    """Backend-agnostic stand-in: records update_content calls, writes nothing."""

    def __init__(self, songs: dict):
        self._songs = songs
        self.updates: list[tuple[str, str]] = []

    def get_all(self):
        return dict(self._songs)

    def update_content(self, title: str, content: str) -> None:
        self.updates.append((title, content))
        self._songs[title].content = content


@pytest.fixture()
def repos(tmp_path, monkeypatch):
    """Fake repo container, with cwd pointed at an empty tmp dir.

    The cwd is switched so that any stray ``chords/<song>.md`` write (the bug)
    would land under ``tmp_path`` where we can assert it does NOT happen. A real
    ``chords/`` directory is created so the buggy direct-write path could
    succeed — making the "no file written" assertion meaningful.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "chords").mkdir()
    song = make_song(
        title="Oceanos",
        content="### Oceanos (Bm)\n\nBm      G\nLyrics here...\n",
        tags={"louvor": 2},
        energy=3,
    )
    repo = _FakeSongRepository({"Oceanos": song})
    return SimpleNamespace(songs=repo)


def test_save_persists_via_repository_not_filesystem(mocker, repos, tmp_path, capsys):
    mocker.patch("cli.commands.transpose.get_repositories", return_value=repos)

    transpose.run("Oceanos", "G", save=True)

    # Persisted through the backend-agnostic repository API exactly once.
    assert len(repos.songs.updates) == 1
    title, content = repos.songs.updates[0]
    assert title == "Oceanos"
    # Bm --to G resolves to the minor equivalent (Gm); heading is rewritten.
    assert "### Oceanos (Gm)" in content

    # The bug: no chord file written directly to the filesystem.
    assert not (tmp_path / "chords" / "Oceanos.md").exists()

    assert "Saved" in capsys.readouterr().out


def test_preview_does_not_persist(mocker, repos, tmp_path):
    mocker.patch("cli.commands.transpose.get_repositories", return_value=repos)

    transpose.run("Oceanos", "G", save=False)

    assert repos.songs.updates == []
    assert not (tmp_path / "chords" / "Oceanos.md").exists()


def test_save_same_key_does_not_persist(mocker, repos, tmp_path, capsys):
    mocker.patch("cli.commands.transpose.get_repositories", return_value=repos)

    transpose.run("Oceanos", "Bm", save=True)

    assert repos.songs.updates == []
    assert not (tmp_path / "chords" / "Oceanos.md").exists()
    assert "Nothing to save" in capsys.readouterr().out
