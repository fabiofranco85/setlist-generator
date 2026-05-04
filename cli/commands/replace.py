"""
Replace command - replace songs in generated setlists.
"""

import sys
from pathlib import Path

from library import (
    format_setlist_markdown,
    get_repositories,
)
from library.models import Setlist
from library.replacer import (
    find_target_setlist,
    select_replacement_song,
    replace_song_in_setlist,
    replace_songs_batch,
)


def compute_position_drift(
    requested_positions_zero_indexed: list[int],
    replacement_titles: list[str],
    new_moment_songs: list[str],
) -> list[tuple[int, int, str]]:
    """Return the list of replacements whose new song moved during reordering.

    Each tuple is ``(requested_position_1_indexed, actual_position_1_indexed,
    title)``. Replacements whose final position equals the requested
    position are omitted. ``replacement_titles`` and
    ``requested_positions_zero_indexed`` are paired by index — same length,
    same order.

    Used by the CLI to print a drift warning when energy reordering moves
    the new song to a slot other than the one the user asked for.
    """
    if len(requested_positions_zero_indexed) != len(replacement_titles):
        raise ValueError(
            "requested_positions_zero_indexed and replacement_titles must "
            "have the same length"
        )

    drift: list[tuple[int, int, str]] = []
    for req_zero, title in zip(requested_positions_zero_indexed, replacement_titles):
        try:
            actual_zero = new_moment_songs.index(title)
        except ValueError:
            # Song dropped out of the moment entirely — shouldn't happen with
            # normal replacement, but stay defensive instead of crashing the CLI.
            continue
        if actual_zero != req_zero:
            drift.append((req_zero + 1, actual_zero + 1, title))
    return drift


def format_updated_moment_lines(
    new_moment_songs: list[str],
    replacement_titles: set[str],
) -> list[str]:
    """Render the "Updated songs in '<moment>':" block.

    The ``(NEW)`` marker is attached by *song identity*, not by position —
    so when energy reordering moves a new song to a different slot the
    marker follows the song instead of staying on whichever song happened
    to land at the originally requested position.
    """
    return [
        f"  {idx}. {song}{' (NEW)' if song in replacement_titles else ''}"
        for idx, song in enumerate(new_moment_songs, start=1)
    ]


def run(moment, position, positions, replacement, date, output_dir, history_dir, verbose=False, label="",
        event_type="", pick=False, keep_position=False):
    """
    Replace song in existing setlist.

    Args:
        moment: Service moment
        position: Single position to replace (1-indexed)
        positions: Multiple positions (comma-separated string)
        replacement: Manual song selection
        date: Target date (YYYY-MM-DD) or None for latest
        output_dir: Custom output directory
        history_dir: Custom history directory
        verbose: Whether to enable debug-level observability output
        label: Optional label for multiple setlists per date
        event_type: Optional event type slug
        pick: Whether to use interactive picker for replacement
    """
    from cli.cli_utils import resolve_paths, handle_error, print_metrics_summary, validate_label, find_setlist_or_fail, resolve_event_type
    from library.observability import Observability

    if pick and replacement:
        handle_error("Cannot use --pick and --with together. Use one or the other.")

    if pick and positions:
        handle_error("Cannot use --pick with --positions. Use --pick with a single --position.")

    obs = Observability.for_cli(level="DEBUG" if verbose else "WARNING")
    label = validate_label(label)

    # Setup paths
    paths = resolve_paths(output_dir, history_dir)

    # Load data via repositories
    repos = get_repositories(history_dir=paths.history_dir, output_dir=paths.output_dir)

    # Resolve event type
    et = resolve_event_type(repos, event_type)
    et_slug = event_type
    et_name = et.name if et and not (et_slug == "" or et_slug == "main") else ""

    print("Loading songs...")
    songs = repos.songs.get_all()
    print(f"Loaded {len(songs)} songs")

    print("Loading history...")
    history = repos.history.get_all()

    if not history:
        handle_error("No setlists found in history")

    print(f"Found {len(history)} historical setlists")

    # Find target setlist
    try:
        setlist_dict = find_target_setlist(history, date, target_label=label, event_type=et_slug)
        setlist_label = setlist_dict.get("label", "")
        header = f"\nTarget setlist: {setlist_dict['date']}"
        if setlist_label:
            header += f" ({setlist_label})"
        print(header)
    except ValueError as e:
        handle_error(str(e))

    # Parse positions
    if position is not None:
        # Single replacement
        positions_list = [position]
    elif positions is not None:
        # Multiple replacements
        try:
            positions_list = [int(p.strip()) for p in positions.split(",")]
        except ValueError:
            handle_error("Invalid positions format. Use comma-separated integers (e.g., '1,3')")
    else:
        # Default to position 1 when neither is specified
        positions_list = [1]

    # Convert from 1-indexed (user) to 0-indexed (internal)
    positions_zero_indexed = [p - 1 for p in positions_list]

    # Validate and show current songs
    moment_songs = setlist_dict["moments"].get(moment, [])

    if not moment_songs:
        handle_error(f"No songs found in moment '{moment}'")

    # Validate positions are in range
    max_position = len(moment_songs)
    for pos_zero in positions_zero_indexed:
        if pos_zero < 0 or pos_zero >= max_position:
            handle_error(
                f"Position {pos_zero + 1} out of range. "
                f"Moment '{moment}' has {max_position} song(s) (1-{max_position})"
            )

    print(f"\nCurrent songs in '{moment}':")
    for idx, song in enumerate(moment_songs, start=1):
        marker = " (TO REPLACE)" if (idx - 1) in positions_zero_indexed else ""
        print(f"  {idx}. {song}{marker}")

    # Whether to reapply energy ordering after the replacement.
    #
    # Manual user choices (`--with` or `--pick`) are an explicit commitment:
    # the user picked a specific song AND a specific slot, so reapplying
    # energy ordering would silently overrule the request. Auto mode is
    # the opposite — the user is delegating both song *and* placement to
    # the algorithm — so we keep the energy arc unless the user passes
    # `--keep-position` to opt out.
    is_manual_choice = pick or (replacement is not None)
    reorder_after_replace = not is_manual_choice and not keep_position

    # Perform replacements
    replacement_titles: list[str] = []
    try:
        if len(positions_zero_indexed) == 1:
            # Single replacement
            pos = positions_zero_indexed[0]
            old_song = moment_songs[pos]

            print(f"\nReplacing '{old_song}' at position {positions_list[0]}...")

            # Interactive picker: let user choose replacement
            if pick:
                from cli.picker import pick_song

                # Build exclusion set: all songs currently in setlist except the one being replaced
                exclude = set()
                for m, slist in setlist_dict["moments"].items():
                    for i, s in enumerate(slist):
                        if m == moment and i == pos:
                            continue
                        exclude.add(s)

                picked = pick_song(
                    songs,
                    title=f"Pick replacement for '{old_song}' ({moment} #{positions_list[0]}):",
                    moment_filter=moment,
                    exclude=exclude,
                )
                if not picked:
                    print("Cancelled.")
                    raise SystemExit(0)
                replacement = picked

            # Select replacement
            replacement_song = select_replacement_song(
                moment=moment,
                setlist=setlist_dict,
                position=pos,
                songs=songs,
                history=history,
                manual_replacement=replacement
            )

            mode = "pick" if pick else ("manual" if replacement else "auto")
            mode_suffix = (
                " — pinned to requested position, no energy reorder"
                if is_manual_choice
                else ""
            )
            print(f"Selected replacement ({mode}): '{replacement_song}'{mode_suffix}")

            # Apply replacement
            new_setlist_dict = replace_song_in_setlist(
                setlist_dict=setlist_dict,
                moment=moment,
                position=pos,
                replacement_song=replacement_song,
                songs=songs,
                reorder_energy=reorder_after_replace,
                obs=obs,
            )
            replacement_titles = [replacement_song]

        else:
            # Batch replacement (always auto — manual choice rejected above
            # for multi-position; the only knob is --keep-position).
            if replacement:
                handle_error("Cannot use manual replacement (--with) for multiple positions")

            print(f"\nReplacing {len(positions_zero_indexed)} songs...")

            replacements_list = [
                (moment, pos, None)
                for pos in positions_zero_indexed
            ]

            new_setlist_dict = replace_songs_batch(
                setlist_dict=setlist_dict,
                replacements=replacements_list,
                songs=songs,
                history=history,
                obs=obs,
                reorder_energy=not keep_position,
            )
            # Recover the chosen replacement titles by diffing the moment.
            old_titles_by_pos = {
                pos: setlist_dict["moments"][moment][pos]
                for pos in positions_zero_indexed
            }
            new_moment_for_diff = new_setlist_dict["moments"][moment]
            old_set = set(setlist_dict["moments"][moment])
            replacement_titles = [
                title for title in new_moment_for_diff
                if title not in old_set
            ]
            # Stable order: first appearance in the new moment list
            seen: set[str] = set()
            replacement_titles = [
                t for t in replacement_titles
                if not (t in seen or seen.add(t))
            ]

    except ValueError as e:
        handle_error(str(e))

    # Show updated setlist — mark NEW songs by identity, not by position,
    # so energy reordering doesn't mislabel which song is the replacement.
    new_moment_songs = new_setlist_dict["moments"][moment]
    print(f"\nUpdated songs in '{moment}':")
    for line in format_updated_moment_lines(new_moment_songs, set(replacement_titles)):
        print(line)

    # Surface energy-reorder drift so users aren't surprised when the new
    # song ends up at a different position than the one they requested.
    # Only meaningful when energy reordering actually ran — i.e., auto mode
    # without --keep-position. Manual choices (--with / --pick) skip the
    # reorder entirely and so by definition cannot drift.
    reorder_ran = (
        len(positions_zero_indexed) == 1
        and reorder_after_replace
    ) or (
        len(positions_zero_indexed) > 1
        and not keep_position
    )
    if reorder_ran:
        drift = compute_position_drift(
            positions_zero_indexed, replacement_titles, new_moment_songs
        )
        if drift:
            print(
                "\nNote: energy reordering moved the new song(s) to a different "
                "position than requested. Use --keep-position to disable "
                "reordering for replace."
            )
            for requested_1idx, actual_1idx, title in drift:
                print(
                    f"  • '{title}' requested at position {requested_1idx}, "
                    f"now at position {actual_1idx}"
                )

    # Save updated files
    setlist_obj = Setlist(
        date=new_setlist_dict["date"],
        moments=new_setlist_dict["moments"],
        label=new_setlist_dict.get("label", ""),
        event_type=new_setlist_dict.get("event_type", ""),
    )

    # Save markdown
    markdown = format_setlist_markdown(setlist_obj, songs, event_type_name=et_name)
    output_path = paths.output_dir / f"{setlist_obj.setlist_id}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\nMarkdown saved to: {output_path}")

    # Save history
    repos.history.save(setlist_obj)
    history_path = paths.history_dir / f"{setlist_obj.setlist_id}.json"
    print(f"History saved to: {history_path}")

    print("\n✅ Replacement complete!")

    if verbose:
        print_metrics_summary(obs.metrics.get_summary())
