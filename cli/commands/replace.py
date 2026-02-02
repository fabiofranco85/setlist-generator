"""
Replace command - replace songs in generated setlists.
"""

import sys
from pathlib import Path

from library import (
    load_songs,
    load_history,
    format_setlist_markdown,
    save_setlist_history,
)
from library.models import Setlist
from library.replacer import (
    find_target_setlist,
    select_replacement_song,
    replace_song_in_setlist,
    replace_songs_batch,
)


def run(moment, position, positions, replacement, date, output_dir, history_dir):
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
    """
    from cli.cli_utils import resolve_paths, handle_error

    # Setup paths
    base_path = Path.cwd()
    paths = resolve_paths(output_dir, history_dir)

    print("Loading songs...")
    songs = load_songs(base_path)
    print(f"Loaded {len(songs)} songs")

    print("Loading history...")
    history = load_history(paths.history_dir)

    if not history:
        handle_error("No setlists found in history")

    print(f"Found {len(history)} historical setlists")

    # Find target setlist
    try:
        setlist_dict = find_target_setlist(history, date)
        print(f"\nTarget setlist: {setlist_dict['date']}")
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

    # Perform replacements
    try:
        if len(positions_zero_indexed) == 1:
            # Single replacement
            pos = positions_zero_indexed[0]
            old_song = moment_songs[pos]

            print(f"\nReplacing '{old_song}' at position {positions_list[0]}...")

            # Select replacement
            replacement_song = select_replacement_song(
                moment=moment,
                setlist=setlist_dict,
                position=pos,
                songs=songs,
                history=history,
                manual_replacement=replacement
            )

            mode = "manual" if replacement else "auto"
            print(f"Selected replacement ({mode}): '{replacement_song}'")

            # Apply replacement
            new_setlist_dict = replace_song_in_setlist(
                setlist_dict=setlist_dict,
                moment=moment,
                position=pos,
                replacement_song=replacement_song,
                songs=songs,
                reorder_energy=True
            )

        else:
            # Batch replacement
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
                history=history
            )

    except ValueError as e:
        handle_error(str(e))

    # Show updated setlist
    print(f"\nUpdated songs in '{moment}':")
    for idx, song in enumerate(new_setlist_dict["moments"][moment], start=1):
        marker = " (NEW)" if (idx - 1) in positions_zero_indexed else ""
        print(f"  {idx}. {song}{marker}")

    # Save updated files
    setlist_obj = Setlist(
        date=new_setlist_dict["date"],
        moments=new_setlist_dict["moments"]
    )

    # Save markdown
    markdown = format_setlist_markdown(setlist_obj, songs)
    output_path = paths.output_dir / f"{setlist_obj.date}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\nMarkdown saved to: {output_path}")

    # Save history
    save_setlist_history(setlist_obj, paths.history_dir)
    history_path = paths.history_dir / f"{setlist_obj.date}.json"
    print(f"History saved to: {history_path}")

    print("\n✅ Replacement complete!")
