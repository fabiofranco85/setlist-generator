"""Add command — create a new song in the repertoire.

The mirror of ``songbook edit``: collect a new song's metadata (interactively
or via flags), persist it through the active ``SongRepository``, then open the
chord sheet in the user's editor (unless ``--no-edit``).

Resolution per field:
- A value supplied via a flag is validated once; an invalid value aborts.
- A missing required field (title, energy, moments) is prompted for, and the
  prompt re-asks until the value is valid.
- The optional YouTube link is prompted for only on an interactive terminal,
  so flag-driven / scripted runs never block on it.

The editor step reuses the ``edit`` command's machinery, so GUI-editor
auto-wait and the filesystem/temp-file split behave identically.
"""

from __future__ import annotations

import sys

import click

from library import get_repositories
from library.loader import parse_tags
from library.models import Song
from library.youtube import extract_video_id


ENERGY_MIN, ENERGY_MAX = 1, 4
WEIGHT_MIN, WEIGHT_MAX = 1, 10


def _is_interactive() -> bool:
    """Return True when stdin and stdout are both connected to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _validate_energy(value: int) -> int:
    """Return ``value`` if it is a valid energy level, else raise ValueError."""
    if not (ENERGY_MIN <= value <= ENERGY_MAX):
        raise ValueError(f"Energy must be between {ENERGY_MIN} and {ENERGY_MAX}.")
    return value


def _validate_tags(raw: str) -> dict[str, int]:
    """Parse and validate a tag string into ``{moment: weight}``.

    Requires at least one moment and weights within ``[WEIGHT_MIN, WEIGHT_MAX]``.
    """
    tags = parse_tags(raw)
    if not tags:
        raise ValueError(
            'At least one moment is required (e.g. "louvor(5),prelúdio").'
        )
    for moment, weight in tags.items():
        if not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            raise ValueError(
                f"Weight for '{moment}' must be between {WEIGHT_MIN} and {WEIGHT_MAX}."
            )
    return tags


def _validate_youtube(raw: str) -> str:
    """Return a validated YouTube URL, or "" when blank. Raise on bad URL."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if extract_video_id(raw) is None:
        raise ValueError(f"'{raw}' is not a valid YouTube URL.")
    return raw


def _resolve_title(repos, title_arg: str | None) -> str:
    """Resolve the song title (arg or prompt) and ensure it is new."""
    title = (title_arg or "").strip()
    if not title:
        title = click.prompt("Title").strip()
    if not title:
        raise ValueError("Title cannot be empty.")
    if repos.songs.exists(title):
        raise ValueError(
            f"Song '{title}' already exists. "
            f'Use `songbook edit "{title}"` to edit it.'
        )
    return title


def _resolve_energy(energy_flag: int | None) -> int:
    """Resolve the energy level from a flag (validate once) or a prompt loop."""
    if energy_flag is not None:
        return _validate_energy(energy_flag)
    while True:
        raw = click.prompt(f"Energy ({ENERGY_MIN}-{ENERGY_MAX})", type=int)
        try:
            return _validate_energy(raw)
        except ValueError as exc:
            click.secho(f"  {exc}", fg="yellow")


def _resolve_tags(tags_flag: str | None) -> dict[str, int]:
    """Resolve the moment tags from a flag (validate once) or a prompt loop."""
    if tags_flag is not None:
        return _validate_tags(tags_flag)
    while True:
        raw = click.prompt(
            'Moments (e.g. "louvor(5),prelúdio")', default="", show_default=False
        )
        try:
            return _validate_tags(raw)
        except ValueError as exc:
            click.secho(f"  {exc}", fg="yellow")


def _resolve_youtube(youtube_flag: str | None) -> str:
    """Resolve the optional YouTube link.

    A flag value is validated once. When no flag is given, the link is prompted
    for only on an interactive terminal; otherwise it is left empty so scripted
    runs don't block.
    """
    if youtube_flag is not None:
        return _validate_youtube(youtube_flag)
    if not _is_interactive():
        return ""
    while True:
        raw = click.prompt("YouTube URL (blank to skip)", default="", show_default=False)
        try:
            return _validate_youtube(raw)
        except ValueError as exc:
            click.secho(f"  {exc}", fg="yellow")


def run(
    title: str | None = None,
    energy: int | None = None,
    tags: str | None = None,
    youtube: str | None = None,
    event_types: tuple[str, ...] = (),
    editor: str | None = None,
    no_edit: bool = False,
) -> None:
    """Create a new song, then open its chord sheet in the editor.

    Args:
        title: Song title (prompted if omitted).
        energy: Energy level 1-4 (prompted if omitted).
        tags: Moment tags string, e.g. ``"louvor(5),prelúdio"`` (prompted if
            omitted). At least one moment is required.
        youtube: Optional YouTube URL (prompted on a TTY if omitted).
        event_types: Event-type slugs to bind the song to (empty = all types).
        editor: Editor command override (same resolution as ``edit``).
        no_edit: Skip opening the editor after creating the record.
    """
    from cli.cli_utils import handle_error

    try:
        repos = get_repositories()
    except Exception as exc:
        handle_error(f"loading repositories: {exc}")

    try:
        resolved_title = _resolve_title(repos, title)
        resolved_energy = _resolve_energy(energy)
        resolved_tags = _resolve_tags(tags)
        resolved_youtube = _resolve_youtube(youtube)
    except ValueError as exc:
        handle_error(exc)
    except click.Abort:
        handle_error(
            "Aborted. Provide a title plus --energy and --tags to add a song "
            "non-interactively."
        )

    song = Song(
        title=resolved_title,
        tags=resolved_tags,
        energy=resolved_energy,
        content=f"### {resolved_title} ()\n\n",
        youtube_url=resolved_youtube,
        event_types=[e.strip() for e in event_types if e and e.strip()],
    )

    try:
        repos.songs.add(song)
    except ValueError as exc:
        handle_error(exc)

    click.secho(f"✓ Created '{resolved_title}'", fg="green")

    if no_edit:
        click.echo(f'  Add chords later with: songbook edit "{resolved_title}"')
        return

    # Reuse edit's machinery so the chord-editing experience is identical.
    from cli.commands.edit import (
        resolve_editor,
        _edit_filesystem,
        _edit_via_tempfile,
    )
    from library.repositories.filesystem.songs import FilesystemSongRepository

    editor_cmd = resolve_editor(editor)
    if isinstance(repos.songs, FilesystemSongRepository):
        _edit_filesystem(repos, resolved_title, editor_cmd)
    else:
        _edit_via_tempfile(repos, resolved_title, editor_cmd)
