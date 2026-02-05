"""
View song command - display song lyrics, chords, and metadata.
"""

from library import get_repositories


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
    print("  songbook view-song \"Song Name\"")
    print()


def display_song(song_name: str, songs: dict, show_metadata: bool = True,
                 transpose_to: str | None = None):
    """Display a song's content, optionally transposed.

    Args:
        song_name: Name of the song to display
        songs: Dictionary of song name -> Song object
        show_metadata: Whether to show metadata (tags, energy)
        transpose_to: Target key for transposition (None = no transposition)
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
            print(f"\nTry: songbook view-song \"{similar[0]}\"")
        else:
            print(f"\nNo similar songs found.")
            print(f"Use 'songbook view-song --list' to see all available songs.")

        return 1

    # Extract title and key from content
    title = song_name
    key = ""
    content = song.content or ""

    # Apply transposition if requested
    original_key = ""
    if transpose_to:
        from library.transposer import (
            calculate_semitones,
            resolve_target_key,
            should_use_flats,
            transpose_content,
        )

    if transpose_to and content:
        # Extract original key before transposing
        first_line = content.split("\n")[0].strip()
        if "(" in first_line and ")" in first_line:
            s = first_line.rfind("(")
            e = first_line.rfind(")")
            if s != -1 and e != -1 and e > s:
                original_key = first_line[s + 1 : e].strip()

        if original_key:
            try:
                effective_key = resolve_target_key(original_key, transpose_to)
                semitones = calculate_semitones(original_key, effective_key)
                use_flats = should_use_flats(effective_key)
                content = transpose_content(content, semitones, use_flats)
            except ValueError as exc:
                print(f"\nTransposition error: {exc}")
                return 1

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
    if transpose_to and original_key:
        semitones = calculate_semitones(original_key, transpose_to)
        if semitones == 0:
            print(f"{title} ({key})")
        else:
            print(f"{title} ({key})  [original: {original_key}]")
    elif key:
        print(f"{title} ({key})")
    else:
        print(title)
    print("=" * 70)

    # Note when already in target key
    if transpose_to and original_key:
        semitones = calculate_semitones(original_key, transpose_to)
        if semitones == 0:
            print(f"\n  Already in {transpose_to} — showing original.")

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


def run(song_name, list_songs, no_metadata, transpose_to=None):
    """
    View a specific song's lyrics and chords.

    Args:
        song_name: Name of the song to view
        list_songs: Whether to list all available songs
        no_metadata: Whether to hide metadata (tags, energy)
        transpose_to: Target key for transposition (None = no transposition)
    """
    from cli.cli_utils import handle_error

    # Load songs
    try:
        repos = get_repositories()
        songs = repos.songs.get_all()
    except Exception as e:
        handle_error(f"Loading songs: {e}")

    if not songs:
        print("No songs found.")
        raise SystemExit(1)

    # List all songs if requested
    if list_songs:
        list_all_songs(songs)
        return

    # Require song name if not listing
    if not song_name:
        print("Error: Please provide a song name or use --list to see all songs.")
        print()
        print("Usage:")
        print("  songbook view-song \"Song Name\"")
        print("  songbook view-song --list")
        raise SystemExit(1)

    # Display the song
    exit_code = display_song(song_name, songs, show_metadata=not no_metadata,
                             transpose_to=transpose_to)
    if exit_code != 0:
        raise SystemExit(exit_code)
