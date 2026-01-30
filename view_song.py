#!/usr/bin/env python3
"""View a specific song's lyrics and chords."""

import argparse
from pathlib import Path

from setlist import load_songs


def list_all_songs(songs: dict):
    """Display all available songs.

    Args:
        songs: Dictionary of song name -> Song object
    """
    print("\n" + "=" * 60)
    print(f"AVAILABLE SONGS ({len(songs)} total)")
    print("=" * 60)
    print()

    # Group by tags if available
    song_list = sorted(songs.keys())

    for song_name in song_list:
        song = songs[song_name]
        # Try to extract key from content
        key = ""
        if song.content:
            first_line = song.content.split("\n")[0].strip()
            if "(" in first_line and ")" in first_line:
                start = first_line.rfind("(")
                end = first_line.rfind(")")
                if start != -1 and end != -1 and end > start:
                    key = first_line[start + 1 : end].strip()

        # Show tags
        tags_str = ", ".join(song.tags.keys()) if song.tags else "no tags"

        if key:
            print(f"  • {song_name} ({key}) - {tags_str}")
        else:
            print(f"  • {song_name} - {tags_str}")

    print()
    print("USAGE:")
    print("  python view_song.py \"Song Name\"")
    print()


def display_song(song_name: str, songs: dict, show_metadata: bool = True):
    """Display a song's content.

    Args:
        song_name: Name of the song to display
        songs: Dictionary of song name -> Song object
        show_metadata: Whether to show metadata (tags, energy)
    """
    song = songs.get(song_name)

    if not song:
        print(f"\nSong not found: '{song_name}'")
        print(f"\nSearching for similar songs...")

        # Find similar songs (case-insensitive partial match)
        similar = []
        search_lower = song_name.lower()
        for name in songs.keys():
            if search_lower in name.lower():
                similar.append(name)

        if similar:
            print(f"\nDid you mean one of these?")
            for name in similar[:5]:  # Show max 5 suggestions
                print(f"  • {name}")
            print(f"\nTry: python view_song.py \"{similar[0]}\"")
        else:
            print(f"\nNo similar songs found.")
            print(f"Use 'python view_song.py --list' to see all available songs.")

        return 1

    # Extract title and key from content
    title = song_name
    key = ""
    content = song.content or ""

    if content:
        lines = content.split("\n")
        first_line = lines[0].strip()

        # Parse markdown heading: ### Title (Key)
        if first_line.startswith("###"):
            first_line = first_line.replace("###", "").strip()

            if "(" in first_line and ")" in first_line:
                start = first_line.rfind("(")
                end = first_line.rfind(")")
                if start != -1 and end != -1 and end > start:
                    key = first_line[start + 1 : end].strip()
                    title = first_line[:start].strip()

            # Remove first line from content
            content = "\n".join(lines[1:]).strip()

    # Display header
    print("\n" + "=" * 70)
    if key:
        print(f"{title} ({key})")
    else:
        print(title)
    print("=" * 70)

    # Show metadata if requested
    if show_metadata:
        print()
        if song.tags:
            tags_display = []
            for moment, weight in song.tags.items():
                if weight == 3:  # Default weight
                    tags_display.append(moment)
                else:
                    tags_display.append(f"{moment}({weight})")
            print(f"Tags:   {', '.join(tags_display)}")

        if song.energy:
            energy_desc = {
                1: "High energy, upbeat, celebratory",
                2: "Moderate-high, engaging, rhythmic",
                3: "Moderate-low, reflective, slower",
                4: "Deep worship, contemplative, intimate",
            }
            desc = energy_desc.get(song.energy, "Unknown")
            print(f"Energy: {song.energy} - {desc}")

        print()
        print("-" * 70)

    # Display content
    print()
    if content:
        print(content)
    else:
        print("(No chord content available)")
    print()

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="View a specific song's lyrics and chords"
    )
    parser.add_argument(
        "song_name",
        nargs="?",
        help="Name of the song to view (use quotes if it contains spaces)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all available songs",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Hide metadata (tags, energy)",
    )

    args = parser.parse_args()

    # Load songs
    try:
        songs = load_songs(Path("."))
    except Exception as e:
        print(f"Error loading songs: {e}")
        return 1

    if not songs:
        print("No songs found.")
        return 1

    # List all songs if requested
    if args.list:
        list_all_songs(songs)
        return 0

    # Require song name if not listing
    if not args.song_name:
        print("Error: Please provide a song name or use --list to see all songs.")
        print()
        print("Usage:")
        print("  python view_song.py \"Song Name\"")
        print("  python view_song.py --list")
        return 1

    # Display the song
    return display_song(args.song_name, songs, show_metadata=not args.no_metadata)


if __name__ == "__main__":
    exit(main())
