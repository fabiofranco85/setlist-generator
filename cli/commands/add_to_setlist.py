"""
Add-to-setlist command: put a specific song into a moment of an existing setlist.

The mirror of ``songbook remove``. Insertion is structural-only: no recency,
no energy reorder, no selection algorithm. The caller names the song and
(optionally) the slot, so both decisions are already made, which is the same
reasoning that makes ``replace --with`` skip energy ordering.

Deliberately permissive about tags: a song does not have to be tagged for the
moment it is being added to, because one-off services do unusual things. It is
strict about duplicates, which the rest of the system relies on.
"""

from difflib import get_close_matches

from cli.picker import pick_song
from library import (
    MOMENTS_CONFIG,
    add_song_to_setlist,
    canonical_moment_order,
    filter_songs_for_event_type,
    format_setlist_markdown,
    get_repositories,
)
from library.models import Setlist


def run(
    moment,
    position,
    song,
    date,
    label,
    event_type,
    output_dir,
    history_dir,
    verbose=False,
):
    """Insert a song into a moment of an existing setlist.

    Args:
        moment: Service moment slug (required)
        position: 1-indexed slot the song should occupy (None appends)
        song: Song title; None opens the interactive picker
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

    songs = repos.songs.get_all()
    already_in_setlist = {
        title
        for song_list in setlist_dict.get("moments", {}).values()
        for title in song_list
    }

    # --- Resolve the song (explicit, or via the picker) ---
    if song is None:
        song = _pick(songs, et, already_in_setlist, moment)
        if song is None:
            print("\nCancelled — nothing was added.")
            return
    elif song not in songs:
        # Exact, case-sensitive match, like `replace --with`. Suggest, because
        # accented titles are easy to mistype.
        suggestions = get_close_matches(song, list(songs), n=3, cutoff=0.6)
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        handle_error(f"Song '{song}' not found in the database.{hint}")

    # --- Insert ---
    # 1-indexed on the command line, zero-indexed in the library, matching
    # `songbook remove`.
    zero_indexed = None if position is None else position - 1
    where = f"at position {position}" if position is not None else "at the end"
    print(f"\nAdding '{song}' to moment '{moment}' {where}...")

    if moment not in setlist_dict.get("moments", {}):
        print(f"  Note: '{moment}' is not in this setlist yet — it will be created.")

    try:
        new_setlist_dict = add_song_to_setlist(
            setlist_dict, moment, song, position=zero_indexed, obs=obs
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

    # History first so a partial failure on output regeneration still leaves
    # the source of truth in sync (same ordering as `remove`).
    repos.history.save(setlist_obj)

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
    for m in canonical_moment_order(setlist_obj.moments, reference_config=moments_ref):
        print(f"  {m}:")
        for idx, title in enumerate(setlist_obj.moments[m], start=1):
            marker = "  <-- added" if title == song else ""
            print(f"    {idx}. {title}{marker}")

    # A moment may now hold more songs than its event type configures. That is
    # allowed on purpose (it is the reason this command exists), but say so, so
    # nobody is surprised when the next `generate` produces the configured size.
    configured = (et.ordered_moments if et else MOMENTS_CONFIG).get(moment)
    actual = len(setlist_obj.moments[moment])
    if configured is not None and actual > configured:
        print(
            f"\nNote: '{moment}' now has {actual} songs, more than the "
            f"{configured} this event type configures. That only affects newly "
            f"generated setlists — this one keeps what you set."
        )

    print(f"\nMarkdown saved to: {output_path}")
    if repos.history.backend_name == "filesystem":
        hist_dir = paths.history_dir
        if et_slug and et_slug != "main":
            hist_dir = hist_dir / et_slug
        print(f"History saved to: {hist_dir / f'{setlist_obj.setlist_id}.json'}")
    else:
        print(f"History saved to {repos.history.backend_name} database")

    # Stale-PDF notice, verbatim in spirit from `remove`: never auto-delete a
    # PDF the user may have printed or shared, and always name the *resolved*
    # date so the suggested command targets this setlist later too.
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

    print("\n✅ Song added!")

    if verbose:
        print_metrics_summary(obs.metrics.get_summary())


def _pick(songs, et, already_in_setlist, moment):
    """Open the song picker over the songs this setlist may still use.

    The pool is the event type's songs minus what is already in the setlist.
    It is deliberately *not* filtered by moment: ``--song`` accepts any song,
    so the picker must be able to reach the same set.
    """
    pool = filter_songs_for_event_type(songs, et.slug) if et else songs
    return pick_song(
        pool,
        title=f"Pick a song to add to '{moment}':",
        exclude=already_in_setlist,
    )
