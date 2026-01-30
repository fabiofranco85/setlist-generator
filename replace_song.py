#!/usr/bin/env python3
"""
Replace songs in a generated setlist.

Usage:
    # Replace first song (position defaults to 1)
    python replace_song.py --moment prelúdio

    # Auto-select replacement for specific position
    python replace_song.py --moment louvor --position 2

    # Manual replacement
    python replace_song.py --moment louvor --position 2 --with "Oceanos"

    # Replace for specific date
    python replace_song.py --date 2026-03-01 --moment louvor --position 2

    # Replace multiple positions
    python replace_song.py --moment louvor --positions 1,3
"""

import argparse
import sys
from pathlib import Path

from setlist import (
    load_songs,
    load_history,
    format_setlist_markdown,
    save_setlist_history,
    get_output_paths,
)
from setlist.models import Setlist
from setlist.replacer import (
    find_target_setlist,
    select_replacement_song,
    replace_song_in_setlist,
    replace_songs_batch,
)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Replace songs in a generated setlist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replace first song (defaults to position 1)
  python replace_song.py --moment prelúdio

  # Auto-select replacement for louvor position 2
  python replace_song.py --moment louvor --position 2

  # Manual replacement
  python replace_song.py --moment louvor --position 2 --with "Oceanos"

  # Replace for specific date
  python replace_song.py --date 2026-03-01 --moment louvor --position 2

  # Replace multiple positions (auto mode)
  python replace_song.py --moment louvor --positions 1,3
"""
    )

    parser.add_argument(
        "--moment",
        required=True,
        help="Service moment (prelúdio, ofertório, saudação, crianças, louvor, poslúdio)"
    )

    # Single or multiple positions (mutually exclusive)
    position_group = parser.add_mutually_exclusive_group(required=False)
    position_group.add_argument(
        "--position",
        type=int,
        help="Position to replace (1-indexed, e.g., 1-4 for louvor). Default: 1"
    )
    position_group.add_argument(
        "--positions",
        type=str,
        help="Multiple positions to replace (comma-separated, e.g., '1,3')"
    )

    parser.add_argument(
        "--date",
        help="Target date (YYYY-MM-DD). Default: latest setlist"
    )

    parser.add_argument(
        "--with",
        dest="replacement_song",
        help="Manual replacement song (default: auto-select)"
    )

    parser.add_argument(
        "--output-dir",
        help="Output directory for markdown files"
    )

    parser.add_argument(
        "--history-dir",
        help="History directory for JSON files"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup paths
    base_path = Path(__file__).parent
    paths = get_output_paths(
        base_path,
        cli_output_dir=args.output_dir,
        cli_history_dir=args.history_dir
    )

    print("Loading songs...")
    songs = load_songs(base_path)
    print(f"Loaded {len(songs)} songs")

    print("Loading history...")
    history = load_history(paths.history_dir)

    if not history:
        print("ERROR: No setlists found in history", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(history)} historical setlists")

    # Find target setlist
    try:
        setlist_dict = find_target_setlist(history, args.date)
        print(f"\nTarget setlist: {setlist_dict['date']}")
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse positions
    if args.position is not None:
        # Single replacement
        positions = [args.position]
    elif args.positions is not None:
        # Multiple replacements
        try:
            positions = [int(p.strip()) for p in args.positions.split(",")]
        except ValueError:
            print("ERROR: Invalid positions format. Use comma-separated integers (e.g., '1,3')", file=sys.stderr)
            sys.exit(1)
    else:
        # Default to position 1 when neither is specified
        positions = [1]

    # Convert from 1-indexed (user) to 0-indexed (internal)
    positions_zero_indexed = [p - 1 for p in positions]

    # Validate and show current songs
    moment_songs = setlist_dict["moments"].get(args.moment, [])

    if not moment_songs:
        print(f"ERROR: No songs found in moment '{args.moment}'", file=sys.stderr)
        sys.exit(1)

    # Validate positions are in range
    max_position = len(moment_songs)
    for pos_zero in positions_zero_indexed:
        if pos_zero < 0 or pos_zero >= max_position:
            print(
                f"ERROR: Position {pos_zero + 1} out of range. "
                f"Moment '{args.moment}' has {max_position} song(s) (1-{max_position})",
                file=sys.stderr
            )
            sys.exit(1)

    print(f"\nCurrent songs in '{args.moment}':")
    for idx, song in enumerate(moment_songs, start=1):
        marker = " (TO REPLACE)" if (idx - 1) in positions_zero_indexed else ""
        print(f"  {idx}. {song}{marker}")

    # Perform replacements
    try:
        if len(positions_zero_indexed) == 1:
            # Single replacement
            position = positions_zero_indexed[0]
            old_song = moment_songs[position]

            print(f"\nReplacing '{old_song}' at position {positions[0]}...")

            # Select replacement
            replacement = select_replacement_song(
                moment=args.moment,
                setlist=setlist_dict,
                position=position,
                songs=songs,
                history=history,
                manual_replacement=args.replacement_song
            )

            mode = "manual" if args.replacement_song else "auto"
            print(f"Selected replacement ({mode}): '{replacement}'")

            # Apply replacement
            new_setlist_dict = replace_song_in_setlist(
                setlist_dict=setlist_dict,
                moment=args.moment,
                position=position,
                replacement_song=replacement,
                songs=songs,
                reorder_energy=True
            )

        else:
            # Batch replacement
            if args.replacement_song:
                print("ERROR: Cannot use --with for multiple positions", file=sys.stderr)
                sys.exit(1)

            print(f"\nReplacing {len(positions_zero_indexed)} songs...")

            replacements = [
                (args.moment, pos, None)
                for pos in positions_zero_indexed
            ]

            new_setlist_dict = replace_songs_batch(
                setlist_dict=setlist_dict,
                replacements=replacements,
                songs=songs,
                history=history
            )

    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Show updated setlist
    print(f"\nUpdated songs in '{args.moment}':")
    for idx, song in enumerate(new_setlist_dict["moments"][args.moment], start=1):
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


if __name__ == "__main__":
    main()
