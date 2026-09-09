"""Setlists command — browse generated setlists.

The setlist counterpart of ``songbook browse``: lists every generated setlist
newest-first and keeps the picker open so you can inspect one, come back, and
act on another.

Flow:

1. List all setlists (newest first), labeled or not, across event types.
2. ``Enter`` opens the setlist's songs in a pager — ``q`` returns to the list.
3. ``d`` deletes the setlist (history record + output files) after confirming.
4. ``r`` re-uses it: prompts for a date, an event type and an optional label,
   then copies the songs to that new setlist and regenerates its markdown.
   Copying into a *different* event type reconciles the moments first (see
   :mod:`library.reconciler`): whatever fits carries over, the rest is dropped
   with a reason, and every empty slot is either picked by the user or filled
   by the same selection the generator uses.
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
from cli.picker import pick_song
from library import (
    ENERGY_ORDERING_ENABLED,
    ENERGY_ORDERING_RULES,
    Setlist,
    calculate_recency_scores,
    filter_songs_for_event_type,
    format_setlist_markdown,
    get_repositories,
    is_default_event_type,
    plan_reconciliation,
)
from library.ordering import apply_energy_ordering
from library.selector import select_songs_for_moment

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


def _show_menu(rows: list[str], title: str, *, cursor_index: int = 0) -> int | None:
    """Show a plain single-select menu. Returns the chosen index, or None.

    ``_show_picker`` is specific to the setlist table (it carries the d/r
    accept keys); this is the generic one-choice-out-of-a-list counterpart.
    """
    if _is_interactive():
        try:
            from simple_term_menu import TerminalMenu

            return TerminalMenu(
                rows, title=title, search_key="/", show_search_hint=True,
                cursor_index=cursor_index,
            ).show()
        except ImportError:
            pass

    click.echo(f"\n{title}\n")
    for i, row in enumerate(rows, 1):
        click.echo(f"  {i}. {row}")
    try:
        choice = click.prompt("\nSelect number (0 to cancel)", type=int, default=0)
    except (click.Abort, EOFError):
        return None
    if choice <= 0 or choice > len(rows):
        return None
    return choice - 1


def _event_type_repo(repos):
    """Return the event type repository, or None when unusable."""
    repo = getattr(repos, "event_types", None)
    if repo is None:
        return None
    try:
        return repo if repo.get_all() else None
    except Exception:
        return None


def _pick_event_type(repos, current_slug: str) -> str | None:
    """Ask which event type the copy belongs to. Returns a slug, or None.

    The returned slug follows the repository convention: the default type is
    the empty string. Storing it as "main" instead would route to the same
    files while comparing unequal in ``exists()``, so the overwrite guard
    would wave through a clobber.

    Backends without event types (or with none defined) keep the source's
    type and are never prompted.
    """
    repo = _event_type_repo(repos)
    if repo is None:
        return current_slug

    types = repo.get_all()
    default_slug = repo.get_default_slug()
    # Default first, then alphabetical: the most-used type is one keypress away.
    slugs = sorted(types, key=lambda s: (s != default_slug, s))
    rows = [f"{slug}  {types[slug].name}" for slug in slugs]

    effective = current_slug or default_slug
    cursor = slugs.index(effective) if effective in slugs else 0

    index = _show_menu(
        rows,
        "Event type for the copy  (Esc/q to cancel)",
        cursor_index=cursor,
    )
    if index is None:
        return None

    chosen = slugs[index]
    return "" if is_default_event_type(chosen) else chosen


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


def _prompt_reuse_target(record: dict, repos) -> tuple[str, str, str] | None:
    """Ask for the new date, event type and optional label.

    Returns ``(date, label, event_type)``, or None when cancelled at any step.
    """
    click.echo(f"\nRe-using {_describe(record)} with the same songs.")

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

    event_type = _pick_event_type(repos, _record_key(record)[2])
    if event_type is None:
        return None

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
        return date, label, event_type


def _resolve_event_type(repos, slug: str):
    """Return the EventType for a slug ("" = default), or None.

    Never exits: a browse loop must survive a backend that cannot answer.
    """
    repo = _event_type_repo(repos)
    if repo is None:
        return None
    try:
        return repo.get(slug or repo.get_default_slug())
    except Exception:
        return None


def _report_plan(plan, target_name: str) -> None:
    """Print what carries over and what cannot, before anything is chosen."""
    click.echo(f"\n  Reconciling moments for '{target_name}':")

    for mp in plan.moments:
        kept = ", ".join(mp.carried) if mp.carried else "(nothing carried over)"
        suffix = f", {mp.slots} to choose" if mp.slots else ""
        click.echo(f"    {mp.moment}: {kept}{suffix}")

    for moment, songs in plan.dropped_moments.items():
        click.secho(
            f"    dropped {moment} ({', '.join(songs)}): "
            f"'{target_name}' has no such moment",
            fg="yellow",
        )
    for moment, song in plan.overflow:
        click.secho(f"    dropped {song}: no room left in {moment}", fg="yellow")
    for moment, song in plan.unavailable:
        click.secho(
            f"    dropped {song} (from {moment}): not available for "
            f"'{target_name}'",
            fg="yellow",
        )


def _fill_slots(plan, available: dict, history: list[dict], date: str) -> None:
    """Fill every empty slot: ask first, auto-select whatever is left blank.

    A chosen song is guaranteed a place in its moment but not a position, the
    same contract ``--desired`` has: energy ordering places it afterwards.
    """
    placed = {title for mp in plan.moments for title in mp.carried}

    # `slots` is kept as "still missing" throughout: every song that lands in
    # a moment decrements it. Without that invariant a moment's target size
    # would grow with each pick and the moment would overfill.
    for mp in plan.moments:
        total = mp.slots
        for slot in range(total):
            title = pick_song(
                available,
                title=(
                    f"{mp.moment}: pick song {slot + 1} of {total}  "
                    "(Esc to let the generator choose)"
                ),
                moment_filter=mp.moment,
                exclude=placed,
            )
            if title is None:
                continue
            mp.carried.append(title)
            mp.slots -= 1
            placed.add(title)

    pending = [mp for mp in plan.moments if mp.slots]
    if not pending:
        return

    recency_scores = calculate_recency_scores(available, history, current_date=date)
    for mp in pending:
        # `select_songs_for_moment` adds its picks to `placed`, which keeps
        # later moments from re-selecting the same song.
        selected = select_songs_for_moment(
            mp.moment, mp.slots, available, recency_scores, placed,
        )
        mp.carried.extend(title for title, _energy in selected)
        mp.slots -= len(selected)

        if mp.slots:
            click.secho(
                f"    ! {mp.moment} is {mp.slots} song(s) short: no other song "
                f"tagged '{mp.moment}' was available",
                fg="yellow",
            )


def _reconcile_moments(record: dict, repos, target_slug: str, date: str) -> dict | None:
    """Project a setlist's moments onto another event type. None to cancel."""
    et = _resolve_event_type(repos, target_slug)
    if et is None:
        click.secho(
            f"  Cannot read the moments of event type "
            f"'{target_slug or '(default)'}'; nothing was copied.",
            fg="red",
        )
        return None

    try:
        songs = repos.songs.get_all()
    except Exception as exc:
        click.secho(f"  Cannot load songs ({exc}); nothing was copied.", fg="red")
        return None

    # Filter with the resolved slug, not the stored one: songs bound to "main"
    # must stay available when the default type is addressed as "".
    available = filter_songs_for_event_type(songs, et.slug)

    plan = plan_reconciliation(record.get("moments", {}), et.ordered_moments, available)
    _report_plan(plan, et.name)

    if plan.total_slots:
        _fill_slots(plan, available, repos.history.get_all(), date)

    moments: dict[str, list[str]] = {}
    for mp in plan.moments:
        if not mp.carried:
            continue
        moments[mp.moment] = _energy_ordered(mp, available)
    return moments


def _energy_ordered(mp, available: dict) -> list[str]:
    """Re-apply the moment's energy arc to its final song list."""
    if not (ENERGY_ORDERING_ENABLED and mp.moment in ENERGY_ORDERING_RULES):
        return list(mp.carried)

    with_energy = [
        (title, available[title].energy) for title in mp.carried if title in available
    ]
    return apply_energy_ordering(
        mp.moment,
        with_energy,
        0,
        energy_ordering_enabled=ENERGY_ORDERING_ENABLED,
        energy_ordering_rules=ENERGY_ORDERING_RULES,
    )


def _reuse(record: dict, repos) -> None:
    """Copy a setlist's songs onto a new date/label, possibly another type."""
    target = _prompt_reuse_target(record, repos)
    if target is None:
        click.echo("  Cancelled.")
        return

    date, label, event_type = target

    # Re-using onto an existing setlist would silently clobber it, the same
    # hazard `songbook generate` guards with its overwrite prompt.
    if repos.history.exists(date, label=label, event_type=event_type):
        existing = date + (f" ({label})" if label else "")
        if not click.confirm(f"  Setlist {existing} already exists. Overwrite it?",
                             default=False):
            click.echo("  Cancelled.")
            return

    if event_type == _record_key(record)[2]:
        # Same event type: a straight copy. Deep-copy the song lists so the
        # source record never aliases the new one.
        moments = {m: list(songs) for m, songs in record["moments"].items()}
    else:
        moments = _reconcile_moments(record, repos, event_type, date)
        if moments is None:
            click.echo("  Cancelled.")
            return

    setlist = Setlist(
        date=date,
        moments=moments,
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

    click.secho(f"  ✓ Re-used as {_describe(setlist.to_dict())}", fg="green")
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
