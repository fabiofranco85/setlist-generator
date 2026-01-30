#!/usr/bin/env python3
"""View generated setlists (latest or specific date)."""

import argparse
from pathlib import Path
from datetime import datetime

from setlist import load_history, load_songs
from setlist.config import MOMENTS_CONFIG


def format_date_display(date_str: str) -> str:
    """Format date for display.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Formatted date like "Saturday, February 15, 2026"
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A, %B %d, %Y")


def display_setlist(setlist_dict: dict, songs: dict, show_keys: bool = False):
    """Display a setlist in formatted output.

    Args:
        setlist_dict: Setlist dictionary with date and moments
        songs: Dictionary of song name -> Song object
        show_keys: Whether to show song keys
    """
    date = setlist_dict["date"]
    moments = setlist_dict["moments"]

    print("\n" + "=" * 60)
    print(f"SETLIST FOR {date}")
    print(format_date_display(date))
    print("=" * 60)
    print()

    # Display each moment in order
    for moment in MOMENTS_CONFIG.keys():
        if moment not in moments:
            continue

        song_list = moments[moment]
        if not song_list:
            continue

        print(f"{moment.upper()}:")
        for song_title in song_list:
            if show_keys:
                # Try to extract key from song content
                song = songs.get(song_title)
                if song and song.content:
                    first_line = song.content.split("\n")[0].strip()
                    if "(" in first_line and ")" in first_line:
                        start = first_line.rfind("(")
                        end = first_line.rfind(")")
                        if start != -1 and end != -1 and end > start:
                            key = first_line[start + 1 : end].strip()
                            print(f"  - {song_title} ({key})")
                            continue

                print(f"  - {song_title}")
            else:
                print(f"  - {song_title}")
        print()

    # Show file paths
    output_md = Path("output") / f"{date}.md"
    output_pdf = Path("output") / f"{date}.pdf"
    history_json = Path("history") / f"{date}.json"

    print("FILES:")
    print(f"  Markdown: {output_md}" + (" ✓" if output_md.exists() else " (not found)"))
    print(f"  PDF:      {output_pdf}" + (" ✓" if output_pdf.exists() else " (not generated)"))
    print(f"  History:  {history_json}" + (" ✓" if history_json.exists() else " (not found)"))
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="View generated setlists (latest or specific date)"
    )
    parser.add_argument(
        "--date",
        help="Specific date to view (YYYY-MM-DD). If omitted, shows latest setlist.",
    )
    parser.add_argument(
        "--keys",
        "-k",
        action="store_true",
        help="Show song keys alongside titles",
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        help="Custom history directory (default: ./history)",
    )

    args = parser.parse_args()

    # Load history
    history_dir = args.history_dir or Path("./history")

    try:
        history = load_history(history_dir)
    except Exception as e:
        print(f"Error loading history: {e}")
        return 1

    if not history:
        print("No setlists found in history.")
        print(f"History directory: {history_dir}")
        return 1

    # Find target setlist
    if args.date:
        # Find specific date
        target_setlist = None
        for setlist in history:
            if setlist["date"] == args.date:
                target_setlist = setlist
                break

        if not target_setlist:
            print(f"No setlist found for date: {args.date}")
            print(f"\nAvailable dates:")
            for setlist in history[:10]:  # Show last 10
                print(f"  - {setlist['date']}")
            if len(history) > 10:
                print(f"  ... and {len(history) - 10} more")
            return 1
    else:
        # Use latest (first in list, since history is sorted newest first)
        target_setlist = history[0]

    # Load songs if showing keys
    songs = {}
    if args.keys:
        try:
            songs = load_songs(Path("."))
        except Exception as e:
            print(f"Warning: Could not load songs: {e}")
            print("Continuing without keys...\n")

    # Display the setlist
    display_setlist(target_setlist, songs, show_keys=args.keys)

    return 0


if __name__ == "__main__":
    exit(main())
