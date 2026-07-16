"""Setlists command — browse generated setlists.

The setlist counterpart of ``songbook browse``: lists every generated setlist
newest-first and keeps the picker open so you can inspect one, come back, and
act on another.

Flow:

1. List all setlists (newest first), labeled or not, across event types.
2. ``Enter`` opens the setlist's songs in a pager — ``q`` returns to the list.
3. ``d`` deletes the setlist (history record + output files) after confirming.
4. ``r`` re-uses it: prompts for a date and optional label, then copies the
   same songs to that new setlist and regenerates its markdown.
5. ``Esc``/``q`` quits.

Composition over new logic: rendering is
``cli.commands.view_setlist.render_setlist``, and deletion/persistence go
through the repository layer exactly as ``songbook delete`` and
``songbook markdown`` do.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime

import click

from cli.commands.view_setlist import render_setlist
from library import (
    Setlist,
    format_setlist_markdown,
    get_repositories,
)

_DATE_FORMAT = "%Y-%m-%d"

# Mirrors cli_utils._LABEL_PATTERN. We can't use cli_utils.validate_label here:
# it calls handle_error() -> SystemExit, which would tear down the browse loop
# on a simple typo. Interactive input needs to re-prompt, not exit.
_LABEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_LABEL_MAX = 30


def _is_interactive() -> bool:
    """Return True when stdin and stdout are connected to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _record_key(record: dict) -> tuple[str, str, str]:
    """Return the ``(date, label, event_type)`` identity of a history record.

    Backends hand back ``None`` (or omit the key entirely) rather than ``""``,
    so normalize here — every lookup and comparison depends on it.
    """
    return (
        record["date"],
        record.get("label") or "",
        record.get("event_type") or "",
    )


def _song_count(record: dict) -> int:
    """Total number of songs across all of a setlist's moments."""
    return sum(len(songs) for songs in record.get("moments", {}).values())


def _format_row(record: dict, label_width: int) -> str:
    """Render one row of the setlist table."""
    _, label, event_type = _record_key(record)
    count = _song_count(record)
    plural = "" if count == 1 else "s"

    row = f"{record['date']}  {label:<{label_width}}  {count} song{plural}"
    if event_type:
        row += f"  [{event_type}]"
    return row


def _build_rows(history: list[dict]) -> tuple[list[str], list[dict]]:
    """Return ``(display_rows, records)``.

    Order is preserved from the repository, which already sorts newest-first.
    """
    label_width = max((len(_record_key(r)[1]) for r in history), default=0)
    rows = [_format_row(r, label_width) for r in history]
    return rows, list(history)


def _normalize_date(raw: str) -> str | None:
    """Return a canonical YYYY-MM-DD date, or None when invalid."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        # strptime also rejects impossible calendar dates (e.g. 2026-02-30).
        return datetime.strptime(raw, _DATE_FORMAT).strftime(_DATE_FORMAT)
    except ValueError:
        return None


def _normalize_label(raw: str) -> str | None:
    """Return a canonical label ("" for none), or None when invalid."""
    label = (raw or "").strip().lower()
    if not label:
        return ""
    if len(label) > _LABEL_MAX or not _LABEL_PATTERN.match(label):
        return None
    return label


def _describe(record: dict) -> str:
    """Human-readable identity of a setlist, for prompts and messages."""
    date, label, event_type = _record_key(record)
    desc = date
    if label:
        desc += f" ({label})"
    if event_type:
        desc += f" [{event_type}]"
    return desc


def _menu_title(count: int) -> str:
    plural = "s" if count != 1 else ""
    return (
        f"{count} setlist{plural}, newest first  —  "
        "Enter to view, d to delete, r to re-use, Esc/q to quit"
    )


def _show_picker(rows: list[str], cursor_index: int) -> tuple[int, str] | None:
    """Show the setlist table.

    Returns ``(index, accept_key)`` where ``accept_key`` is one of
    ``enter`` / ``d`` / ``r``, or ``None`` when cancelled.
    """
    if _is_interactive():
        try:
            from simple_term_menu import TerminalMenu

            menu = TerminalMenu(
                rows,
                title=_menu_title(len(rows)),
                search_key="/",
                show_search_hint=True,
                cursor_index=cursor_index,
                accept_keys=("enter", "d", "r"),
            )
            index = menu.show()
            if index is None:
                return None
            return index, menu.chosen_accept_key or "enter"
        except ImportError:
            pass

    # Non-interactive fallback: numbered list, view only. Delete/re-use are
    # destructive and key-driven, so they stay out of the scripted path.
    click.echo("\nSetlists (newest first):\n")
    for i, row in enumerate(rows, 1):
        click.echo(f"  {i}. {row}")
    try:
        choice = click.prompt(
            "\nSelect setlist number to view (0 to quit)", type=int, default=0
        )
    except (click.Abort, EOFError):
        return None
    if choice <= 0 or choice > len(rows):
        return None
    return choice - 1, "enter"


def _moments_order(repos, event_type: str) -> list[str] | None:
    """Best-effort moments order for an event type.

    Unlike ``cli_utils.resolve_event_type`` this never exits: a setlist whose
    event type has since been removed should still be viewable.
    """
    if repos.event_types is None:
        return None
    try:
        et = repos.event_types.get(event_type) if event_type else None
    except Exception:
        return None
    return et.moments_order if et else None


def _view(record: dict, repos) -> None:
    """Page the setlist's songs."""
    _, _, event_type = _record_key(record)
    try:
        songs = repos.songs.get_all()
    except Exception:
        songs = {}

    click.echo_via_pager(
        render_setlist(
            record,
            songs,
            show_keys=True,
            moments_order=_moments_order(repos, event_type),
        )
    )


def _delete(record: dict, repos) -> None:
    """Delete a setlist's history record and output files, after confirming."""
    date, label, event_type = _record_key(record)

    if not click.confirm(
        f"Delete setlist {_describe(record)}? "
        "This removes the history record and all output files",
        default=False,
    ):
        click.echo("  Kept.")
        return

    # History first: a partial failure then leaves outputs we can still find
    # by filename, which is easier to recover from than the reverse ordering.
    # (Same rationale as `songbook delete`.)
    repos.history.delete(date, label=label, event_type=event_type)
    deleted = repos.output.delete_outputs(date, label=label, event_type=event_type)

    click.secho(f"  ✓ Deleted {_describe(record)}", fg="green")
    for path in deleted:
        click.echo(f"    removed {path}")


def _prompt_reuse_target(record: dict) -> tuple[str, str] | None:
    """Ask for the new date and optional label. None when cancelled."""
    click.echo(f"\nRe-using {_describe(record)} — same songs, new date.")

    while True:
        try:
            raw = click.prompt("  New date (YYYY-MM-DD, blank to cancel)",
                               default="", show_default=False)
        except (click.Abort, EOFError):
            return None
        if not (raw or "").strip():
            return None
        date = _normalize_date(raw)
        if date is None:
            click.secho(f"  '{raw.strip()}' is not a valid YYYY-MM-DD date.", fg="yellow")
            continue
        break

    while True:
        try:
            raw = click.prompt("  Label (optional, blank for none)",
                               default="", show_default=False)
        except (click.Abort, EOFError):
            return None
        label = _normalize_label(raw)
        if label is None:
            click.secho(
                f"  Invalid label '{raw.strip()}'. Use lowercase letters, digits, "
                f"hyphens and underscores (max {_LABEL_MAX}).",
                fg="yellow",
            )
            continue
        return date, label


def _reuse(record: dict, repos) -> None:
    """Copy a setlist's songs onto a new date/label."""
    target = _prompt_reuse_target(record)
    if target is None:
        click.echo("  Cancelled.")
        return

    date, label = target
    _, _, event_type = _record_key(record)

    # Re-using onto an existing setlist would silently clobber it — the same
    # hazard `songbook generate` guards with its overwrite prompt.
    if repos.history.exists(date, label=label, event_type=event_type):
        existing = date + (f" ({label})" if label else "")
        if not click.confirm(f"  Setlist {existing} already exists. Overwrite it?",
                             default=False):
            click.echo("  Cancelled.")
            return

    # Deep-copy the song lists: the source record must not alias the new one.
    setlist = Setlist(
        date=date,
        moments={m: list(songs) for m, songs in record["moments"].items()},
        label=label,
        event_type=event_type,
    )
    repos.history.save(setlist)

    try:
        songs = repos.songs.get_all()
        markdown = format_setlist_markdown(
            setlist, songs, moments_order=_moments_order(repos, event_type)
        )
        md_path = repos.output.save_markdown(
            setlist.date, markdown, label=setlist.label, event_type=event_type
        )
    except Exception as exc:
        # History is saved and correct; only the rendered output is missing.
        click.secho(f"  ✓ Saved setlist {_describe(setlist.to_dict())}", fg="green")
        click.secho(f"  ! Markdown not regenerated: {exc}", fg="yellow")
        click.echo("    Run `songbook markdown` to produce it.")
        return

    click.secho(f"  ✓ Re-used as {date}" + (f" ({label})" if label else ""), fg="green")
    click.echo(f"    Markdown: {md_path}")


def run() -> None:
    """Run the interactive setlist browser."""
    try:
        repos = get_repositories()
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1)

    cursor_index = 0

    while True:
        # Refresh every pass: delete and re-use both mutate the list.
        history = repos.history.get_all()
        if not history:
            click.secho("No setlists found.", fg="yellow")
            raise SystemExit(1)

        rows, records = _build_rows(history)
        cursor_index = min(cursor_index, len(rows) - 1)

        result = _show_picker(rows, cursor_index)
        if result is None:
            click.echo("Done.")
            return

        index, key = result
        cursor_index = index
        record = records[index]

        if key == "d":
            _delete(record, repos)
            # The deleted row is gone; the list has already shifted up.
            if not repos.history.get_all():
                click.echo("No setlists left.")
                return
        elif key == "r":
            _reuse(record, repos)
        else:
            _view(record, repos)

        if not _is_interactive():
            # One-shot mode: without a TTY there's no way to close the picker.
            return
