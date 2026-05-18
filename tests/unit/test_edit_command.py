"""Tests for cli.commands.edit — open a song in the user's editor."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from cli.commands import edit as edit_cmd
from cli.commands.edit import (
    DEFAULT_EDITOR,
    _inject_wait_flag,
    _is_gui_editor,
    _launch_editor,
    _suggest_similar,
    resolve_editor,
    run,
)
from tests.helpers.factories import make_song


# ---------------------------------------------------------------------------
# resolve_editor
# ---------------------------------------------------------------------------


class TestResolveEditor:
    def test_flag_wins_over_env_vars(self, monkeypatch):
        monkeypatch.setenv("VISUAL", "nano")
        monkeypatch.setenv("EDITOR", "emacs")
        assert resolve_editor("code --wait") == "code --wait"

    def test_visual_wins_over_editor(self, monkeypatch):
        monkeypatch.setenv("VISUAL", "nano")
        monkeypatch.setenv("EDITOR", "emacs")
        assert resolve_editor(None) == "nano"

    def test_editor_used_when_no_visual(self, monkeypatch):
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.setenv("EDITOR", "emacs")
        assert resolve_editor(None) == "emacs"

    def test_falls_back_to_vim(self, monkeypatch):
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        assert resolve_editor(None) == DEFAULT_EDITOR
        assert DEFAULT_EDITOR == "vim"

    def test_empty_string_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("VISUAL", "")
        monkeypatch.setenv("EDITOR", "  ")
        assert resolve_editor("") == DEFAULT_EDITOR

    def test_strips_surrounding_whitespace(self, monkeypatch):
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        assert resolve_editor("  nano  ") == "nano"


# ---------------------------------------------------------------------------
# _inject_wait_flag / _is_gui_editor
# ---------------------------------------------------------------------------


class TestInjectWaitFlag:
    @pytest.mark.parametrize(
        "editor, expected",
        [
            ("cursor", "cursor --wait"),
            ("code", "code --wait"),
            ("code-insiders", "code-insiders --wait"),
            ("subl", "subl --wait"),
            ("windsurf", "windsurf --wait"),
            ("zed", "zed --wait"),
            ("mate", "mate -w"),  # TextMate uses -w, not --wait
            ("atom", "atom --wait"),
        ],
    )
    def test_injects_wait_flag_for_known_gui_editors(self, editor, expected):
        assert _inject_wait_flag(editor) == expected

    @pytest.mark.parametrize("editor", ["vim", "nano", "emacs", "nvim", "vi", "ed"])
    def test_leaves_terminal_editors_untouched(self, editor):
        assert _inject_wait_flag(editor) == editor

    @pytest.mark.parametrize(
        "editor",
        [
            "cursor --wait",
            "code --wait",
            "code -w",
            "code --wait --new-window",
            "code --new-window --wait",
        ],
    )
    def test_does_not_double_inject_when_flag_already_present(self, editor):
        assert _inject_wait_flag(editor) == editor

    def test_matches_basename_for_absolute_paths(self):
        # Full path to the binary should still trigger injection.
        result = _inject_wait_flag("/usr/local/bin/cursor")
        assert result.endswith("--wait")
        assert "/usr/local/bin/cursor" in result

    def test_preserves_existing_args(self):
        # An extra flag like --new-window should be kept.
        result = _inject_wait_flag("code --new-window")
        # shlex.join order: original args first, then injected wait flag
        assert "--new-window" in result
        assert "--wait" in result

    def test_empty_editor_returns_unchanged(self):
        assert _inject_wait_flag("") == ""


class TestIsGuiEditor:
    @pytest.mark.parametrize(
        "editor", ["cursor", "code", "code --wait", "subl", "/usr/local/bin/cursor"]
    )
    def test_recognizes_gui_editors(self, editor):
        assert _is_gui_editor(editor) is True

    @pytest.mark.parametrize("editor", ["vim", "nano", "emacs", "vi", ""])
    def test_terminal_and_empty_are_not_gui(self, editor):
        assert _is_gui_editor(editor) is False


# ---------------------------------------------------------------------------
# _launch_editor
# ---------------------------------------------------------------------------


class TestLaunchEditor:
    def test_invokes_subprocess_with_split_argv(self, mocker, tmp_path):
        run_mock = mocker.patch("cli.commands.edit.subprocess.run")
        file = tmp_path / "Song.md"
        file.write_text("body")

        _launch_editor("code --wait", file)

        run_mock.assert_called_once_with(["code", "--wait", str(file)], check=True)

    def test_missing_editor_raises_systemexit(self, mocker, tmp_path, capsys):
        mocker.patch(
            "cli.commands.edit.subprocess.run",
            side_effect=FileNotFoundError("no such file"),
        )
        file = tmp_path / "Song.md"
        file.write_text("body")

        with pytest.raises(SystemExit) as exc:
            _launch_editor("not-a-real-editor", file)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "not-a-real-editor" in err

    def test_nonzero_exit_raises_systemexit(self, mocker, tmp_path, capsys):
        mocker.patch(
            "cli.commands.edit.subprocess.run",
            side_effect=subprocess.CalledProcessError(returncode=2, cmd=["vim"]),
        )
        file = tmp_path / "Song.md"
        file.write_text("body")

        with pytest.raises(SystemExit) as exc:
            _launch_editor("vim", file)
        assert exc.value.code == 1
        assert "status 2" in capsys.readouterr().err

    def test_gui_editor_gets_wait_flag_and_notice(self, mocker, tmp_path, capsys):
        """When $EDITOR is a GUI editor without --wait, inject it and tell the user."""
        run_mock = mocker.patch("cli.commands.edit.subprocess.run")
        file = tmp_path / "Song.md"
        file.write_text("body")

        _launch_editor("cursor", file)

        argv = run_mock.call_args[0][0]
        assert argv[0] == "cursor"
        assert "--wait" in argv  # injected
        assert argv[-1] == str(file)

        out = capsys.readouterr().out
        assert "Song.md" in out
        assert "cursor" in out
        assert "Close the editor" in out

    def test_terminal_editor_skips_notice_and_injection(self, mocker, tmp_path, capsys):
        run_mock = mocker.patch("cli.commands.edit.subprocess.run")
        file = tmp_path / "Song.md"
        file.write_text("body")

        _launch_editor("vim", file)

        argv = run_mock.call_args[0][0]
        assert argv == ["vim", str(file)]  # no flag injected
        assert capsys.readouterr().out == ""  # no notice for terminal editors


# ---------------------------------------------------------------------------
# _suggest_similar
# ---------------------------------------------------------------------------


class TestSuggestSimilar:
    def test_lists_matches(self, capsys):
        songs = {"Oceanos": make_song(title="Oceanos"), "Hosana": make_song(title="Hosana")}
        code = _suggest_similar("ocean", songs)
        assert code == 1
        out = capsys.readouterr().out
        assert "Did you mean" in out
        assert "Oceanos" in out

    def test_no_matches_falls_back_to_hint(self, capsys):
        songs = {"Oceanos": make_song(title="Oceanos")}
        code = _suggest_similar("totally-unrelated", songs)
        assert code == 1
        out = capsys.readouterr().out
        assert "No similar songs" in out
        assert "view-song --list" in out


# ---------------------------------------------------------------------------
# Helpers for the run() tests
# ---------------------------------------------------------------------------


class _FakeFsSongRepository:
    """In-memory stand-in for FilesystemSongRepository.

    We don't subclass the real class so we can keep the test pure-Python, but
    edit.py uses ``isinstance(..., FilesystemSongRepository)`` to branch. The
    tests patch that check so this fake activates the in-place edit path.
    """

    def __init__(self, base_path: Path, songs: dict):
        self.base_path = base_path
        self._songs = songs
        self.invalidated = 0

    def get_all(self):
        return dict(self._songs)

    def get_by_title(self, title):
        return self._songs.get(title)

    def update_content(self, title, content):
        self._songs[title].content = content

    def invalidate_cache(self):
        self.invalidated += 1


class _FakeOtherSongRepository:
    """Stand-in for a non-filesystem backend (postgres/supabase)."""

    def __init__(self, songs: dict):
        self._songs = songs
        self.updates: list[tuple[str, str]] = []

    def get_all(self):
        return dict(self._songs)

    def get_by_title(self, title):
        return self._songs.get(title)

    def update_content(self, title, content):
        self.updates.append((title, content))
        self._songs[title].content = content

    def invalidate_cache(self):  # pragma: no cover — not used on this path
        pass


@pytest.fixture()
def fs_repos(tmp_path):
    """Build a fake repository container with a filesystem-style song repo."""
    (tmp_path / "chords").mkdir()
    (tmp_path / "chords" / "Oceanos.md").write_text(
        "### Oceanos (Bm)\n\nBm  G\nLyrics...\n", encoding="utf-8"
    )
    songs = {
        "Oceanos": make_song(title="Oceanos", content="### Oceanos (Bm)\n\nBm  G\nLyrics...\n"),
        "Hosana": make_song(title="Hosana", content="### Hosana (D)\n\nD  A\n"),
    }
    songs_repo = _FakeFsSongRepository(tmp_path, songs)
    return SimpleNamespace(songs=songs_repo)


@pytest.fixture()
def remote_repos():
    songs = {
        "Oceanos": make_song(title="Oceanos", content="### Oceanos (Bm)\n\nBm  G\n"),
    }
    return SimpleNamespace(songs=_FakeOtherSongRepository(songs))


def _patch_fs_isinstance(mocker, is_filesystem: bool):
    """Force the edit module's isinstance check to a known answer."""
    mocker.patch.object(edit_cmd, "isinstance", lambda obj, cls: is_filesystem)


# ---------------------------------------------------------------------------
# run() — filesystem branch
# ---------------------------------------------------------------------------


class TestRunFilesystem:
    def test_opens_chord_file_in_place_and_invalidates_cache(
        self, mocker, fs_repos, monkeypatch, capsys
    ):
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        mocker.patch("cli.commands.edit.get_repositories", return_value=fs_repos)
        _patch_fs_isinstance(mocker, True)

        captured = {}

        def fake_run(argv, check):
            captured["argv"] = argv
            # Simulate the editor saving a change.
            Path(argv[-1]).write_text("### Oceanos (Bm)\n\nedited body\n", encoding="utf-8")

        mocker.patch("cli.commands.edit.subprocess.run", side_effect=fake_run)

        run("Oceanos", editor="vim")

        argv = captured["argv"]
        assert argv[0] == "vim"
        assert argv[-1].endswith("chords/Oceanos.md")
        assert fs_repos.songs.invalidated == 1
        out = capsys.readouterr().out
        assert "Saved changes" in out

    def test_no_change_message_when_file_untouched(self, mocker, fs_repos, capsys):
        mocker.patch("cli.commands.edit.get_repositories", return_value=fs_repos)
        _patch_fs_isinstance(mocker, True)
        mocker.patch("cli.commands.edit.subprocess.run")  # no-op editor

        run("Oceanos", editor="vim")

        assert "No changes made" in capsys.readouterr().out
        assert fs_repos.songs.invalidated == 1

    def test_creates_stub_when_chord_file_missing(self, mocker, fs_repos, capsys):
        # Drop the existing file and add a song with no chord file on disk
        (fs_repos.songs.base_path / "chords" / "Oceanos.md").unlink()
        fs_repos.songs._songs["Brand New"] = make_song(title="Brand New", content="")

        mocker.patch("cli.commands.edit.get_repositories", return_value=fs_repos)
        _patch_fs_isinstance(mocker, True)

        captured = {}

        def fake_run(argv, check):
            captured["path"] = argv[-1]

        mocker.patch("cli.commands.edit.subprocess.run", side_effect=fake_run)

        run("Brand New", editor="vim")

        chord_path = fs_repos.songs.base_path / "chords" / "Brand New.md"
        assert chord_path.exists()
        assert chord_path.read_text(encoding="utf-8").startswith("### Brand New ()")
        out = capsys.readouterr().out
        assert "Created" in out  # stub creation message


# ---------------------------------------------------------------------------
# run() — non-filesystem branch (tmp-file round-trip)
# ---------------------------------------------------------------------------


class TestRunOtherBackend:
    def test_round_trips_via_tempfile_and_calls_update_content(
        self, mocker, remote_repos, capsys
    ):
        mocker.patch("cli.commands.edit.get_repositories", return_value=remote_repos)
        _patch_fs_isinstance(mocker, False)

        def fake_run(argv, check):
            Path(argv[-1]).write_text("edited remotely", encoding="utf-8")

        mocker.patch("cli.commands.edit.subprocess.run", side_effect=fake_run)

        run("Oceanos", editor="vim")

        assert remote_repos.songs.updates == [("Oceanos", "edited remotely")]
        assert "Saved changes for 'Oceanos'" in capsys.readouterr().out

    def test_no_update_when_content_unchanged(self, mocker, remote_repos, capsys):
        mocker.patch("cli.commands.edit.get_repositories", return_value=remote_repos)
        _patch_fs_isinstance(mocker, False)
        mocker.patch("cli.commands.edit.subprocess.run")  # editor leaves file alone

        run("Oceanos", editor="vim")

        assert remote_repos.songs.updates == []
        assert "No changes made" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run() — dispatch behaviour
# ---------------------------------------------------------------------------


class TestRunDispatch:
    def test_picker_launched_when_no_song_name(self, mocker, fs_repos):
        mocker.patch("cli.commands.edit.get_repositories", return_value=fs_repos)
        _patch_fs_isinstance(mocker, True)
        pick = mocker.patch("cli.picker.pick_song", return_value="Oceanos")
        mocker.patch("cli.commands.edit.subprocess.run")

        run(None, editor="vim")

        pick.assert_called_once()

    def test_picker_cancel_exits_cleanly(self, mocker, fs_repos):
        mocker.patch("cli.commands.edit.get_repositories", return_value=fs_repos)
        mocker.patch("cli.picker.pick_song", return_value=None)

        with pytest.raises(SystemExit) as exc:
            run(None, editor="vim")
        assert exc.value.code == 0

    def test_unknown_song_returns_exit_1_with_suggestions(self, mocker, fs_repos, capsys):
        mocker.patch("cli.commands.edit.get_repositories", return_value=fs_repos)

        with pytest.raises(SystemExit) as exc:
            run("ocean", editor="vim")
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Did you mean" in out
        assert "Oceanos" in out

    def test_empty_library_exits_with_message(self, mocker, capsys):
        empty_repos = SimpleNamespace(songs=_FakeFsSongRepository(Path("."), {}))
        mocker.patch("cli.commands.edit.get_repositories", return_value=empty_repos)

        with pytest.raises(SystemExit) as exc:
            run("Anything", editor="vim")
        assert exc.value.code == 1
        assert "No songs found" in capsys.readouterr().out

    def test_repository_failure_exits_with_message(self, mocker, capsys):
        mocker.patch(
            "cli.commands.edit.get_repositories",
            side_effect=RuntimeError("db down"),
        )

        with pytest.raises(SystemExit) as exc:
            run("Oceanos", editor="vim")
        assert exc.value.code == 1
        assert "db down" in capsys.readouterr().err
