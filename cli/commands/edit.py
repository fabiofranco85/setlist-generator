"""
Edit command - open a song's chord file in the user's editor.

Editor resolution order (highest priority first):
    1. ``--editor`` CLI option
    2. ``$VISUAL`` environment variable
    3. ``$EDITOR`` environment variable
    4. ``vim`` (default)

For the filesystem backend, the chord file under ``chords/<title>.md`` is
opened in place. If the file does not yet exist, a stub heading is written so
the editor opens on a real file. For other backends (postgres, supabase, ...)
the current chord content is round-tripped through a temporary file and
written back via ``repos.songs.update_content``.
"""

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from library import get_repositories


DEFAULT_EDITOR = "vim"

# Editors that detach from the terminal by default and need an explicit
# wait flag to block until the file is closed. Without it, the CLI exits
# immediately and reports "No changes made" before the user can type anything.
# Mapping: command basename -> wait flag (matched against argv[1:] verbatim).
GUI_EDITOR_WAIT_FLAGS: dict[str, str] = {
    "code": "--wait",
    "code-insiders": "--wait",
    "cursor": "--wait",
    "windsurf": "--wait",
    "zed": "--wait",
    "subl": "--wait",
    "mate": "-w",
    "atom": "--wait",
}

# Argv tokens that already imply "block until the editor closes" — used to
# avoid double-injecting a wait flag the user (or env var) already supplied.
_WAIT_FLAG_ALIASES = {"--wait", "-w", "-W"}


def _inject_wait_flag(editor: str) -> str:
    """Append a wait flag to ``editor`` if the binary is a known GUI editor.

    GUI editors (Cursor, VS Code, Sublime, Zed, TextMate, ...) hand the file
    off to a running window and return immediately. Without the wait flag the
    CLI would exit before the user can edit anything. We inject the flag iff
    the binary's basename is in ``GUI_EDITOR_WAIT_FLAGS`` and no wait flag is
    already present in the command. Vim, nano, emacs, etc. are left untouched.

    Args:
        editor: Editor command string (may contain arguments).

    Returns:
        Possibly augmented editor command. ``shlex.join`` ensures the result
        round-trips correctly through ``shlex.split`` in ``_launch_editor``.
    """
    parts = shlex.split(editor)
    if not parts:
        return editor

    binary = Path(parts[0]).name  # handle /usr/local/bin/cursor → "cursor"
    flag = GUI_EDITOR_WAIT_FLAGS.get(binary)
    if not flag:
        return editor

    if any(token in _WAIT_FLAG_ALIASES for token in parts[1:]):
        return editor  # user already supplied a wait flag

    return shlex.join(parts + [flag])


def _is_gui_editor(editor: str) -> bool:
    """True if the editor command's binary is a known GUI editor."""
    parts = shlex.split(editor)
    if not parts:
        return False
    return Path(parts[0]).name in GUI_EDITOR_WAIT_FLAGS


def resolve_editor(editor_flag: str | None = None) -> str:
    """Return the editor command to run.

    Args:
        editor_flag: Value passed via ``--editor`` (may be ``None`` or empty).

    Returns:
        Editor command string (may contain arguments, e.g. ``"code --wait"``).
    """
    for candidate in (editor_flag, os.environ.get("VISUAL"), os.environ.get("EDITOR")):
        if candidate and candidate.strip():
            return candidate.strip()
    return DEFAULT_EDITOR


def _launch_editor(editor: str, file_path: Path) -> None:
    """Run the editor on ``file_path``, exiting with a friendly message on failure.

    For known GUI editors a wait flag is auto-injected so the CLI blocks until
    the editor window is closed. A "waiting" notice is printed so the user
    knows where to look — otherwise it appears as though the CLI is hung.
    """
    effective_editor = _inject_wait_flag(editor)
    argv = shlex.split(effective_editor) + [str(file_path)]

    if _is_gui_editor(editor):
        binary = Path(shlex.split(editor)[0]).name
        print(
            f"Opening {file_path.name} in {binary}. "
            f"Close the editor tab/window to continue..."
        )

    try:
        subprocess.run(argv, check=True)
    except FileNotFoundError:
        print(
            f"Error: editor not found: '{editor}'. "
            "Set $EDITOR or pass --editor to choose a different one.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        print(f"Error: editor exited with status {exc.returncode}.", file=sys.stderr)
        raise SystemExit(1)


def _suggest_similar(song_name: str, songs: dict) -> int:
    """Print fuzzy-match suggestions for an unknown song. Returns exit code."""
    print(f"\nSong not found: '{song_name}'")
    similar = [n for n in songs if song_name.lower() in n.lower()]
    if similar:
        print("\nDid you mean one of these?")
        for n in similar[:5]:
            print(f"  • {n}")
        print(f'\nTry: songbook edit "{similar[0]}"')
    else:
        print("\nNo similar songs found.")
        print("Use 'songbook view-song --list' to see all available songs.")
    return 1


def _edit_filesystem(repos, title: str, editor: str) -> int:
    """Edit the chord file in place for the filesystem backend."""
    chord_path: Path = repos.songs.base_path / "chords" / f"{title}.md"
    chord_path.parent.mkdir(parents=True, exist_ok=True)

    created_stub = False
    if not chord_path.exists():
        chord_path.write_text(f"### {title} ()\n\n", encoding="utf-8")
        created_stub = True

    before = chord_path.read_text(encoding="utf-8")
    _launch_editor(editor, chord_path)
    after = chord_path.read_text(encoding="utf-8")

    repos.songs.invalidate_cache()

    if after != before:
        print(f"✓ Saved changes to {chord_path}")
    elif created_stub:
        print(f"✓ Created {chord_path} (no edits made)")
    else:
        print("No changes made.")
    return 0


def _edit_via_tempfile(repos, title: str, editor: str) -> int:
    """Edit content through a temp file for non-filesystem backends."""
    song = repos.songs.get_by_title(title)
    original = (song.content if song else "") or f"### {title} ()\n\n"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(original)
        tmp_path = Path(tmp.name)

    try:
        _launch_editor(editor, tmp_path)
        new_content = tmp_path.read_text(encoding="utf-8")
        if new_content != original:
            repos.songs.update_content(title, new_content)
            print(f"✓ Saved changes for '{title}'")
        else:
            print("No changes made.")
    finally:
        tmp_path.unlink(missing_ok=True)
    return 0


def run(song_name: str | None, editor: str | None = None) -> None:
    """Open a song's chord file in the user's editor.

    Args:
        song_name: Title of the song to edit, or ``None`` to launch the
            interactive picker.
        editor: Optional editor command (overrides ``$VISUAL`` / ``$EDITOR``).
    """
    try:
        repos = get_repositories()
        songs = repos.songs.get_all()
    except Exception as exc:
        print(f"Error: loading songs: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if not songs:
        print("No songs found.")
        raise SystemExit(1)

    if not song_name:
        from cli.picker import pick_song

        song_name = pick_song(songs, title="Pick a song to edit:")
        if not song_name:
            raise SystemExit(0)

    if song_name not in songs:
        raise SystemExit(_suggest_similar(song_name, songs))

    editor_cmd = resolve_editor(editor)

    # Filesystem backend gets in-place editing; others round-trip via tmp file.
    from library.repositories.filesystem.songs import FilesystemSongRepository

    if isinstance(repos.songs, FilesystemSongRepository):
        exit_code = _edit_filesystem(repos, song_name, editor_cmd)
    else:
        exit_code = _edit_via_tempfile(repos, song_name, editor_cmd)

    if exit_code != 0:
        raise SystemExit(exit_code)
