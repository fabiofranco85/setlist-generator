"""Browse command — explore the repertoire song by song.

The interactive counterpart of ``view-song --list``: instead of printing a
static list and exiting, it keeps a searchable picker open so you can read one
song, come back, and pick another until you're done.

Flow:

1. Show every song in a searchable picker (title, key, energy, tags).
2. Selecting a song opens it in a pager — ``q`` returns to the picker.
3. Repeat until ``Esc`` / ``q`` closes the picker.

This is composition, not new logic: the picker is ``cli.picker.pick_song`` and
the rendering is ``cli.commands.view_song.render_song``. The pager gives long
chord sheets scrollback and in-song search for free, and ``q`` doubles as the
natural "go back" gesture.
"""

from __future__ import annotations

import sys

import click

from cli.commands.view_song import render_song
from cli.picker import pick_song
from library import get_repositories


def _is_interactive() -> bool:
    """Return True when stdin and stdout are connected to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _menu_title(count: int) -> str:
    """Header text for the browse picker."""
    plural = "s" if count != 1 else ""
    return f"Browse {count} song{plural}  —  Enter to view, / to search, Esc/q to quit"


def run() -> None:
    """Run the interactive browse loop."""
    try:
        repos = get_repositories()
        songs = repos.songs.get_all()
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1)

    if not songs:
        click.secho("No songs found.", fg="yellow")
        raise SystemExit(1)

    # Read-only command: fetch once and keep the list stable while browsing.
    last_viewed: str | None = None

    while True:
        selected = pick_song(
            songs,
            title=_menu_title(len(songs)),
            cursor_title=last_viewed,
        )
        if selected is None:
            click.echo("Done.")
            return

        click.echo_via_pager(render_song(selected, songs[selected]))
        last_viewed = selected

        if not _is_interactive():
            # One-shot mode: without a TTY there's no way to close the picker,
            # so looping would hang. Mirrors `songbook weights`.
            return
