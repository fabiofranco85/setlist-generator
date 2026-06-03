"""YouTube links command — review and edit the YouTube links of a setlist's songs.

A song's YouTube link lives on the *song* record (the ``youtube`` column of
``database.csv`` / the ``youtube_url`` DB column), not on the setlist. This
command uses a setlist only to decide *which* songs to show: it lists each song
with its link status and lets you add or fix links interactively.

Flow:

1. Resolve the target setlist (by date / label / event type).
2. Print every song with its link status (✓ valid, ✗ missing, ⚠ unrecognized).
3. Pick a song, type a YouTube URL (validated), save. Repeat.

Each save is committed immediately via ``repos.songs.update_youtube()`` so closing
the menu (or hitting ``Ctrl+C``) never loses an edit. Because the link belongs to
the song, an edit applies everywhere that song is used. Run ``songbook youtube
create`` afterward to build the playlist.
"""

from __future__ import annotations

import sys

import click

from library import get_repositories
from library.youtube import extract_video_id


STATUS_OK = "✓"
STATUS_MISSING = "✗"
STATUS_BAD = "⚠"


def _is_interactive() -> bool:
    """Return True when stdin and stdout are connected to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _setlist_titles(setlist: dict) -> list[str]:
    """Ordered, de-duplicated song titles across the setlist's moments."""
    titles: list[str] = []
    seen: set[str] = set()
    for song_list in setlist.get("moments", {}).values():
        for title in song_list:
            if title not in seen:
                seen.add(title)
                titles.append(title)
    return titles


def _status_and_text(song) -> tuple[str, str]:
    """Return (status_marker, display_text) for a song's YouTube link."""
    if song is None:
        return STATUS_BAD, "(not in song database)"

    url = (song.youtube_url or "").strip()
    if not url:
        return STATUS_MISSING, "(no link)"
    if extract_video_id(url) is None:
        return STATUS_BAD, f"{url}  (unrecognized URL)"
    return STATUS_OK, url


def _print_summary(titles: list[str], songs: dict) -> None:
    """Print the full setlist with each song's link status, plus a tally."""
    counts = {STATUS_OK: 0, STATUS_MISSING: 0, STATUS_BAD: 0}
    click.echo("")
    for i, title in enumerate(titles, 1):
        status, text = _status_and_text(songs.get(title))
        counts[status] += 1
        click.echo(f"  {i:>2}. {status} {title}  —  {text}")
    click.echo(
        f"\n  {counts[STATUS_OK]} ok · {counts[STATUS_MISSING]} missing · "
        f"{counts[STATUS_BAD]} unrecognized\n"
    )


def _build_rows(titles: list[str], songs: dict) -> list[str]:
    """Return picker display rows (one per title, status + current link)."""
    title_width = min(max((len(t) for t in titles), default=10), 40)
    rows = []
    for title in titles:
        status, text = _status_and_text(songs.get(title))
        rows.append(f"{status} {title:<{title_width}}  {text}")
    return rows


def _show_picker(rows: list[str], titles: list[str]) -> str | None:
    """Show the song list and return the chosen title, or ``None`` to quit."""
    if _is_interactive():
        try:
            from simple_term_menu import TerminalMenu

            menu = TerminalMenu(
                rows,
                title=(
                    f"Editing YouTube links "
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
    click.echo("Songs:\n")
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


def _prompt_new_url(title: str, current: str) -> str | None:
    """Ask for a new YouTube URL.

    Returns the new URL (``""`` clears the link), or ``None`` to cancel/keep.
    A blank entry clears an existing link only after confirmation; with no
    existing link a blank entry is a no-op.
    """
    current = (current or "").strip()
    while True:
        try:
            raw = click.prompt(
                f"YouTube URL for '{title}' (blank to keep/clear)",
                default="",
                show_default=False,
            )
        except (click.Abort, EOFError):
            return None

        raw = (raw or "").strip()
        if not raw:
            if current:
                try:
                    if click.confirm("  Clear the existing link?", default=False):
                        return ""
                except (click.Abort, EOFError):
                    return None
            return None

        if extract_video_id(raw) is None:
            click.secho(
                "  Not a recognized YouTube URL "
                "(expected youtube.com/watch?v=…, youtu.be/…, or /embed/…).",
                fg="yellow",
            )
            continue

        if raw == current:
            click.echo("  Link unchanged.")
            return None

        return raw


def run(date, output_dir, history_dir, label="", event_type=""):
    """Review and edit YouTube links for the songs in a setlist.

    Args:
        date: Target date (YYYY-MM-DD) or None for latest.
        output_dir: Custom output directory.
        history_dir: Custom history directory.
        label: Optional label for multiple setlists per date.
        event_type: Optional event type slug.
    """
    from cli.cli_utils import (
        resolve_paths,
        validate_label,
        find_setlist_or_fail,
        resolve_event_type,
    )

    label = validate_label(label)

    paths = resolve_paths(output_dir, history_dir)
    repos = get_repositories(
        history_dir=paths.history_dir, output_dir=paths.output_dir
    )

    et = resolve_event_type(repos, event_type)
    et_slug = event_type
    et_name = et.name if et and not (et_slug == "" or et_slug == "main") else ""

    setlist = find_setlist_or_fail(repos, date, label, event_type=et_slug)
    target_date = setlist["date"]
    target_label = setlist.get("label", "")

    titles = _setlist_titles(setlist)
    if not titles:
        click.echo("This setlist has no songs.")
        return

    header = f"YouTube links for {target_date}"
    if et_name:
        header += f" | {et_name}"
    if target_label:
        header += f" ({target_label})"
    click.echo("\n" + header)

    songs = repos.songs.get_all()
    _print_summary(titles, songs)

    while True:
        songs = repos.songs.get_all()
        rows = _build_rows(titles, songs)
        selected = _show_picker(rows, titles)
        if selected is None:
            break

        current = (songs[selected].youtube_url if selected in songs else "") or ""
        new_url = _prompt_new_url(selected, current)
        if new_url is None:
            if not _is_interactive():
                return
            continue

        try:
            repos.songs.update_youtube(selected, new_url)
        except (KeyError, ValueError) as exc:
            click.secho(f"  Failed to save: {exc}", fg="red")
            if not _is_interactive():
                raise SystemExit(1)
            continue

        if new_url == "":
            click.secho(f"  ✓ {selected}: link cleared", fg="green")
        else:
            click.secho(f"  ✓ {selected}: link updated", fg="green")

        if not _is_interactive():
            return

    click.echo("\nDone. Run 'songbook youtube create' to build the playlist.")
