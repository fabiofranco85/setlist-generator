"""Weights command — interactively edit song-moment weights.

Each song-moment pair has its own weight (1-10, default 3) that drives the
selection-score formula::

    score = weight × (recency + 0.1) + random(0, 0.5)

Raising a song's weight increases how often it gets picked for that moment;
lowering it pushes it down the queue without removing it from the moment.

Flow:

1. Pick a moment (via ``--moment`` or interactive menu).
2. Show a scrollable list of songs tagged for that moment, with current
   weights.
3. Select a row, type the new weight, save. Repeat.

Each save is committed immediately via ``repos.songs.update_tags()`` so closing
the menu (or hitting ``Ctrl+C``) never loses an edit.
"""

from __future__ import annotations

import sys
from typing import Iterable

import click

from library import get_repositories
from library.event_type import filter_songs_for_event_type
from library.models import Song


WEIGHT_MIN = 1
WEIGHT_MAX = 10


def _is_interactive() -> bool:
    """Return True when stdin and stdout are connected to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _resolve_moments_config(repos, event_type: str) -> dict[str, int]:
    """Return the moments dict for the chosen event type, or the global default."""
    if event_type and repos.event_types is not None:
        et = repos.event_types.get(event_type)
        if et is not None:
            return et.moments

        from cli.cli_utils import handle_error

        available = ", ".join(repos.event_types.get_all().keys()) or "(none)"
        handle_error(
            f"Event type '{event_type}' not found.\n"
            f"Available event types: {available}"
        )

    if repos.event_types is not None:
        default_slug = repos.event_types.get_default_slug()
        et = repos.event_types.get(default_slug)
        if et is not None:
            return et.moments

    from library.config import MOMENTS_CONFIG

    return dict(MOMENTS_CONFIG)


def _pick_moment(moments: Iterable[str]) -> str | None:
    """Prompt the user to pick a moment. Returns ``None`` if cancelled."""
    moments_list = list(moments)
    if not moments_list:
        return None

    if _is_interactive():
        try:
            from simple_term_menu import TerminalMenu

            menu = TerminalMenu(
                moments_list,
                title="Pick a moment to edit weights for:",
            )
            index = menu.show()
            return moments_list[index] if index is not None else None
        except ImportError:
            pass

    # Non-interactive fallback
    click.echo("\nAvailable moments:")
    for i, m in enumerate(moments_list, 1):
        click.echo(f"  {i}. {m}")
    try:
        choice = click.prompt("Select moment number (0 to cancel)", type=int, default=0)
    except (click.Abort, EOFError):
        return None
    if choice <= 0 or choice > len(moments_list):
        return None
    return moments_list[choice - 1]


def _format_row(title: str, weight: int, title_width: int) -> str:
    """Render a single row of the weights table."""
    return f"{title:<{title_width}}  [weight: {weight}]"


def _build_rows(songs_for_moment: list[tuple[str, Song]], moment: str) -> tuple[list[str], list[str]]:
    """Return (display_rows, song_titles) sorted by weight desc, then title."""
    sorted_songs = sorted(
        songs_for_moment,
        key=lambda pair: (-pair[1].get_weight(moment), pair[0].lower()),
    )
    title_width = max((len(title) for title, _ in sorted_songs), default=10)
    title_width = min(title_width, 40)  # cap so terminal doesn't wrap

    rows = [
        _format_row(title, song.get_weight(moment), title_width)
        for title, song in sorted_songs
    ]
    titles = [title for title, _ in sorted_songs]
    return rows, titles


def _prompt_new_weight(title: str, moment: str, current: int) -> int | None:
    """Ask for a new weight, validate it, return ``None`` on cancel."""
    while True:
        try:
            raw = click.prompt(
                f"New weight for '{title}' in {moment} "
                f"({WEIGHT_MIN}-{WEIGHT_MAX}, blank to cancel)",
                default="",
                show_default=False,
            )
        except (click.Abort, EOFError):
            return None

        raw = (raw or "").strip()
        if not raw:
            return None

        try:
            new_weight = int(raw)
        except ValueError:
            click.secho(f"  '{raw}' is not a valid integer.", fg="yellow")
            continue

        if not (WEIGHT_MIN <= new_weight <= WEIGHT_MAX):
            click.secho(
                f"  Weight must be between {WEIGHT_MIN} and {WEIGHT_MAX}.",
                fg="yellow",
            )
            continue

        if new_weight == current:
            click.echo("  Weight unchanged.")
            return None

        return new_weight


def _save_weight(repos, title: str, moment: str, new_weight: int) -> None:
    """Persist the new weight by replacing the song's full tag set."""
    song = repos.songs.get_by_title(title)
    if song is None:
        raise KeyError(f"Song '{title}' disappeared mid-edit")

    new_tags = dict(song.tags)
    new_tags[moment] = new_weight
    repos.songs.update_tags(title, new_tags)


def _refresh_songs_for_moment(
    repos, moment: str, event_type: str
) -> list[tuple[str, Song]]:
    """Reload songs and return those tagged for ``moment`` (event-type filtered)."""
    all_songs = repos.songs.get_all()
    if event_type:
        all_songs = filter_songs_for_event_type(all_songs, event_type)
    return [
        (title, song)
        for title, song in all_songs.items()
        if song.has_moment(moment)
    ]


def _show_picker(rows: list[str], titles: list[str], moment: str) -> str | None:
    """Show the song-weight table and return the chosen title, or ``None``."""
    if _is_interactive():
        try:
            from simple_term_menu import TerminalMenu

            menu = TerminalMenu(
                rows,
                title=(
                    f"Editing weights for '{moment}' "
                    f"({len(rows)} song{'s' if len(rows) != 1 else ''})  —  "
                    "Enter to edit, Esc/q to quit"
                ),
                search_key="/",
                show_search_hint=True,
            )
            index = menu.show()
            return titles[index] if index is not None else None
        except ImportError:
            pass

    # Non-interactive fallback: numbered list
    click.echo(f"\nWeights for '{moment}':\n")
    for i, row in enumerate(rows, 1):
        click.echo(f"  {i}. {row}")
    try:
        choice = click.prompt(
            "\nSelect song number to edit (0 to quit)", type=int, default=0
        )
    except (click.Abort, EOFError):
        return None
    if choice <= 0 or choice > len(titles):
        return None
    return titles[choice - 1]


def run(moment: str | None = None, event_type: str = "") -> None:
    """Run the interactive weights editor.

    Args:
        moment: Pre-selected moment slug (skip the moment picker if set).
        event_type: Event-type slug for filtering songs (empty = default).
    """
    try:
        repos = get_repositories()
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1)

    moments_config = _resolve_moments_config(repos, event_type)

    if moment:
        if moment not in moments_config:
            click.secho(
                f"Error: moment '{moment}' not configured.\n"
                f"Available moments: {', '.join(moments_config.keys())}",
                fg="red",
                err=True,
            )
            raise SystemExit(1)
    else:
        moment = _pick_moment(moments_config.keys())
        if moment is None:
            click.echo("Cancelled.")
            return

    while True:
        songs_for_moment = _refresh_songs_for_moment(repos, moment, event_type)
        if not songs_for_moment:
            click.echo(
                f"\nNo songs are currently tagged for '{moment}'."
                f"  Tag songs via database.csv first, then re-run this command."
            )
            return

        rows, titles = _build_rows(songs_for_moment, moment)
        selected = _show_picker(rows, titles, moment)
        if selected is None:
            click.echo("Done.")
            return

        song = next(s for t, s in songs_for_moment if t == selected)
        current = song.get_weight(moment)
        new_weight = _prompt_new_weight(selected, moment, current)
        if new_weight is None:
            # Cancelled this edit — keep looping in interactive mode,
            # exit cleanly in non-interactive mode (one-shot semantics).
            if not _is_interactive():
                return
            continue

        try:
            _save_weight(repos, selected, moment, new_weight)
        except (KeyError, ValueError) as exc:
            click.secho(f"  Failed to save: {exc}", fg="red")
            if not _is_interactive():
                raise SystemExit(1)
            continue

        click.secho(
            f"  ✓ {selected}: weight {current} → {new_weight}", fg="green"
        )

        if not _is_interactive():
            # One-shot mode: exit after a single save.
            return
