"""
Remove command — drop a song or an entire moment from an existing setlist.

Removal is structural-only: no recency recalculation, no energy
reorder, no selection algorithm. The library functions in
``library/remover.py`` own the "if the last song in a moment is
removed, drop the moment" cascade so this CLI stays a thin I/O layer.
"""

from library import (
    canonical_moment_order,
    format_setlist_markdown,
    get_repositories,
    remove_moment_from_setlist,
    remove_song_from_setlist,
)
from library.models import Setlist


def run(
    moment,
    position,
    all_songs,
    date,
    label,
    event_type,
    output_dir,
    history_dir,
    verbose=False,
):
    """Remove a song or an entire moment from a setlist.

    Args:
        moment: Service moment slug (required)
        position: 1-indexed position to remove (single-song mode)
        all_songs: If True, remove the entire moment (--all flag)
        date: Target date (YYYY-MM-DD) or None for latest
        label: Optional setlist label
        event_type: Optional event type slug
        output_dir: Custom output directory
        history_dir: Custom history directory
        verbose: Enable debug-level observability output
    """
    from cli.cli_utils import (
        find_setlist_or_fail,
        handle_error,
        print_metrics_summary,
        resolve_event_type,
        resolve_paths,
        validate_label,
    )
    from library.observability import Observability

    # --- Validate flag combination ---
    if position is not None and all_songs:
        handle_error("--position and --all are mutually exclusive")
    if position is None and not all_songs:
        handle_error(
            "Specify either --position N (remove a single song) or "
            "--all (remove the entire moment)"
        )

    obs = Observability.for_cli(level="DEBUG" if verbose else "WARNING")
    label = validate_label(label)

    # --- Setup ---
    paths = resolve_paths(output_dir, history_dir)
    repos = get_repositories(history_dir=paths.history_dir, output_dir=paths.output_dir)

    et = resolve_event_type(repos, event_type)
    et_slug = event_type
    et_name = et.name if et and not (et_slug == "" or et_slug == "main") else ""
    et_moments_order = et.moments_order if et else None
    moments_ref = {m: 0 for m in et_moments_order} if et_moments_order else None

    # --- Find target setlist ---
    setlist_dict = find_setlist_or_fail(repos, date, label=label, event_type=et_slug)
    resolved_date = setlist_dict["date"]

    header = f"\nTarget setlist: {resolved_date}"
    if label:
        header += f" ({label})"
    if et_name:
        header += f" | {et_name}"
    print(header)

    # --- Validate the moment exists in this setlist ---
    moments_in_setlist = setlist_dict.get("moments", {})
    if moment not in moments_in_setlist:
        available = ", ".join(moments_in_setlist.keys()) or "(none)"
        handle_error(
            f"Moment '{moment}' is not in this setlist. "
            f"Available moments: {available}"
        )

    # --- Perform removal ---
    try:
        if all_songs:
            song_count = len(moments_in_setlist[moment])
            print(f"\nRemoving moment '{moment}' ({song_count} song(s))...")
            new_setlist_dict = remove_moment_from_setlist(
                setlist_dict, moment, obs=obs
            )
        else:
            # The early validation guarantees `position` is set here (one
            # of --position or --all is required). The assert exists only
            # to satisfy Pyright — handle_error doesn't propagate its
            # NoReturn narrowing across compound boolean conditions.
            assert position is not None
            zero_indexed = position - 1
            moment_songs = moments_in_setlist[moment]
            if zero_indexed < 0 or zero_indexed >= len(moment_songs):
                handle_error(
                    f"Position {position} out of range. "
                    f"Moment '{moment}' has {len(moment_songs)} song(s) "
                    f"(1-{len(moment_songs)})"
                )
            removed_song = moment_songs[zero_indexed]
            cascade = len(moment_songs) == 1
            print(
                f"\nRemoving '{removed_song}' "
                f"at position {position} of moment '{moment}'..."
            )
            if cascade:
                print(
                    f"  Note: '{moment}' had only one song — "
                    f"the moment will be dropped from this setlist."
                )
            new_setlist_dict = remove_song_from_setlist(
                setlist_dict, moment, zero_indexed, obs=obs
            )
    except ValueError as e:
        handle_error(str(e))

    # --- Build Setlist object and persist ---
    setlist_obj = Setlist(
        date=new_setlist_dict["date"],
        moments=new_setlist_dict["moments"],
        label=new_setlist_dict.get("label", ""),
        event_type=new_setlist_dict.get("event_type", ""),
    )

    # Save history first so a partial failure on output regeneration
    # still leaves the source-of-truth (history JSON) in sync.
    repos.history.save(setlist_obj)

    # Regenerate markdown. PDFs are NOT auto-regenerated — we surface a
    # stale-PDF notice below so the user knows to run `songbook pdf`.
    songs = repos.songs.get_all()
    markdown = format_setlist_markdown(
        setlist_obj,
        songs,
        event_type_name=et_name,
        moments_order=et_moments_order,
    )
    output_path = repos.output.save_markdown(
        setlist_obj.date,
        markdown,
        label=setlist_obj.label,
        event_type=et_slug,
    )

    # --- Report ---
    print("\nUpdated setlist:")
    if not setlist_obj.moments:
        print(
            "  (no moments left — setlist is empty. "
            "Run 'songbook delete' to discard it.)"
        )
    else:
        for m in canonical_moment_order(setlist_obj.moments, reference_config=moments_ref):
            song_list = setlist_obj.moments[m]
            print(f"  {m}:")
            for idx, song in enumerate(song_list, start=1):
                print(f"    {idx}. {song}")

    print(f"\nMarkdown saved to: {output_path}")
    if repos.history.backend_name == "filesystem":
        hist_dir = paths.history_dir
        if et_slug and et_slug != "main":
            hist_dir = hist_dir / et_slug
        print(f"History saved to: {hist_dir / f'{setlist_obj.setlist_id}.json'}")
    else:
        print(f"History saved to {repos.history.backend_name} database")

    # If a PDF exists for this setlist it's now stale — call it out so
    # the user knows to regenerate. We do NOT auto-delete the PDF: the
    # user may have already printed or shared it, and overwriting an
    # opened file is worse than leaving a stale one. The hint always
    # includes the resolved date — never the user's original (maybe
    # absent) `--date` flag — because by the time the user runs the
    # suggested command, `--date` (latest) may resolve to a different
    # setlist than the one we just modified.
    pdf_path = repos.output.get_pdf_path(
        resolved_date, label=label, event_type=et_slug
    )
    if pdf_path.exists():
        print(
            f"\nNote: existing PDF at {pdf_path} is now stale. "
            f"Run 'songbook pdf --date {resolved_date}"
            + (f" --label {label}" if label else "")
            + (f" -e {et_slug}" if et_slug and et_slug != "main" else "")
            + "' to regenerate."
        )

    print("\n✅ Removal complete!")

    if verbose:
        print_metrics_summary(obs.metrics.get_summary())
