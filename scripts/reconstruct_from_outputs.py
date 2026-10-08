"""Backfill the database from the setlist markdown in ``output/``.

Disaster-recovery companion to ``.backups/*.sql.gz``: restore the newest dump,
then run this to replay everything the output files know that the dump does
not. It never deletes anything.

    uv run python scripts/reconstruct_from_outputs.py --dry-run   # show the diff
    uv run python scripts/reconstruct_from_outputs.py             # apply it

What it replays, in this order:

1. Songs that exist only in the output (prompts for energy, weights, YouTube
   URL and event-type binding, since the markdown carries none of that).
2. Chord content that is newer in the output than in the database.
3. Setlists missing from the database.

Setlists dated on or before ``--since`` (the dump date) are skipped unless
named with ``--include``; ``--exclude`` drops any setlist. Ids look like
``2026-09-13``, ``2026-06-07_morning`` or ``ceia/2026-09-13_culto_dia``.
Re-running on an up-to-date database does nothing.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.commands.add import ENERGY_MAX, ENERGY_MIN, _validate_youtube  # noqa: E402
from cli.main import _load_dotenv  # noqa: E402
from library.loader import parse_tags  # noqa: E402
from library.models import Song  # noqa: E402
from library.output_parser import NewSong, Plan, plan_reconstruction, scan_output_dir  # noqa: E402
from library.repositories import get_repositories  # noqa: E402

DUMP_DATE = "2026-05-18"


def _describe(plan: Plan, pdf_only: list[str]) -> None:
    if plan.new_songs:
        click.echo(f"New songs ({len(plan.new_songs)}):")
        for song in plan.new_songs.values():
            moments = ", ".join(f"{m}×{n}" for m, n in song.moments.items())
            click.echo(f"  + {song.title}  [{moments}]  from {', '.join(song.sources)}")
    if plan.content_updates:
        click.echo(f"Chord content updates ({len(plan.content_updates)}):")
        for update in plan.content_updates.values():
            click.echo(f"  ~ {update.title}  (newest: {update.source_date})")
            diff = difflib.unified_diff(
                update.old.splitlines(), update.new.splitlines(), "db", "output", lineterm="", n=1
            )
            for line in diff:
                click.echo(f"      {line}")
    if plan.setlists:
        click.echo(f"Setlists to save ({len(plan.setlists)}):")
        for setlist in plan.setlists:
            counts = ", ".join(f"{m}: {len(s)}" for m, s in setlist.moments.items())
            prefix = f"{setlist.event_type}/" if setlist.event_type else ""
            click.echo(f"  + {prefix}{setlist.setlist_id}  ({counts})")
    if plan.skipped:
        click.echo(f"Skipped ({len(plan.skipped)}):")
        for sid, reason in plan.skipped:
            click.echo(f"  - {sid}: {reason}")
    if pdf_only:
        click.echo(f"PDF-only setlists, no chord content to recover ({len(pdf_only)}):")
        for sid in pdf_only:
            click.echo(f"  - {sid}")
    if not (plan.new_songs or plan.content_updates or plan.setlists):
        click.echo("Nothing to do.")


def _prompt_song(new_song: NewSong, event_type_slugs: list[str]) -> Song:
    click.echo(f"\n{new_song.title}: appeared in {', '.join(new_song.sources)}")
    energy = click.prompt(f"  Energy ({ENERGY_MIN}-{ENERGY_MAX})", type=click.IntRange(ENERGY_MIN, ENERGY_MAX))
    tags = {
        moment: click.prompt(f"  Weight for '{moment}'", type=click.IntRange(1, 10), default=3)
        for moment in new_song.moments
    }
    extra = click.prompt("  Extra moments, e.g. 'poslúdio(2)' (blank = none)", default="", show_default=False)
    if extra.strip():
        tags.update(parse_tags(extra))
    while True:
        try:
            youtube_url = _validate_youtube(click.prompt("  YouTube URL (blank = none)", default="", show_default=False))
            break
        except ValueError as exc:
            click.echo(f"  {exc}")
    while True:
        raw = click.prompt(
            f"  Bind to event types {event_type_slugs} (comma list, blank = all)", default="", show_default=False
        )
        event_types = [s.strip() for s in raw.split(",") if s.strip()]
        unknown = [s for s in event_types if s not in event_type_slugs]
        if not unknown:
            break
        click.echo(f"  Unknown event type(s): {', '.join(unknown)}")
    return Song(
        title=new_song.title,
        tags=tags,
        energy=energy,
        content=new_song.content,
        youtube_url=youtube_url,
        event_types=event_types,
    )


@click.command()
@click.option("--output-dir", default="output", type=click.Path(path_type=Path), show_default=True)
@click.option("--since", default=DUMP_DATE, show_default=True, help="Skip setlists dated on or before this.")
@click.option("--include", multiple=True, metavar="ID", help="Consider this setlist even if dated before --since.")
@click.option("--exclude", multiple=True, metavar="ID", help="Never touch this setlist.")
@click.option("--dry-run", is_flag=True, help="Print the plan and write nothing.")
def main(output_dir: Path, since: str, include: tuple[str, ...], exclude: tuple[str, ...], dry_run: bool) -> None:
    """Replay songs, chord edits and setlists from OUTPUT_DIR into the database."""
    _load_dotenv()
    repos = get_repositories()
    click.echo(f"Backend: {repos.history.backend_name}")

    parsed, pdf_only = scan_output_dir(output_dir)
    slugs = sorted(slug for slug in repos.event_types.get_all() if slug != "main")
    unknown = sorted({p.event_type for p in parsed if p.event_type and p.event_type not in slugs})
    if unknown:
        raise click.ClickException(
            f"output/ has subdirectories for unknown event types: {', '.join(unknown)}. "
            "Create them first with 'songbook event-type add'."
        )

    db_songs = repos.songs.get_all()
    db_keys = {(s["date"], s.get("event_type", ""), s.get("label", "")) for s in repos.history.get_all()}
    plan = plan_reconstruction(
        parsed,
        db_songs=db_songs,
        db_setlist_keys=db_keys,
        since=since,
        include=set(include),
        exclude=set(exclude),
    )
    _describe(plan, pdf_only)
    if dry_run or not (plan.new_songs or plan.content_updates or plan.setlists):
        return

    for new_song in plan.new_songs.values():
        repos.songs.add(_prompt_song(new_song, slugs))
        click.echo(f"  added {new_song.title}")
    for update in plan.content_updates.values():
        repos.songs.update_content(update.title, update.new)
        click.echo(f"  updated content of {update.title}")
    for setlist in plan.setlists:
        repos.history.save(setlist)
        click.echo(f"  saved {setlist.setlist_id}" + (f" ({setlist.event_type})" if setlist.event_type else ""))
    click.echo(
        f"\nDone: {len(plan.new_songs)} songs added, {len(plan.content_updates)} contents updated, "
        f"{len(plan.setlists)} setlists saved."
    )


if __name__ == "__main__":
    main()
