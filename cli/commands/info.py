"""
Info command - display detailed statistics for a song.
"""

from pathlib import Path

from library import (
    calculate_recency_scores,
    get_days_since_last_use,
    get_song_usage_history,
    load_history,
    load_songs,
)


def _extract_key(content: str) -> str:
    """Extract key from chord file first line (### Title (Key) pattern)."""
    if not content:
        return ""
    first_line = content.split("\n")[0].strip()
    if "(" in first_line and ")" in first_line:
        start = first_line.rfind("(")
        end = first_line.rfind(")")
        if start != -1 and end != -1 and end > start:
            return first_line[start + 1 : end].strip()
    return ""


def run(song_name: str):
    """Show detailed statistics for a song."""
    from cli.cli_utils import handle_error, resolve_paths

    # Load songs
    try:
        songs = load_songs(Path.cwd())
    except Exception as e:
        handle_error(f"Loading songs: {e}")

    if not songs:
        handle_error("No songs found.")

    # Look up the song
    song = songs.get(song_name)
    if not song:
        print(f"\nSong not found: '{song_name}'")
        print("Searching for similar songs...")

        similar = []
        search_lower = song_name.lower()
        for name in songs:
            if search_lower in name.lower():
                similar.append(name)

        if similar:
            print("\nDid you mean one of these?")
            for name in similar[:5]:
                print(f"  - {name}")
            print(f'\nTry: songbook info "{similar[0]}"')
        else:
            print("\nNo similar songs found.")
            print("Use 'songbook view-song --list' to see all available songs.")

        raise SystemExit(1)

    # Load history
    paths = resolve_paths(None, None)
    history = load_history(paths.history_dir)

    # Extract key from chord content
    key = _extract_key(song.content)

    # Calculate recency
    recency_scores = calculate_recency_scores(songs, history)
    recency_score = recency_scores.get(song_name, 1.0)
    days_since = get_days_since_last_use(song_name, history)
    usages = get_song_usage_history(song_name, history)

    # --- Display ---

    # Header
    header = f"{song_name} ({key})" if key else song_name
    print()
    print("=" * 60)
    print(header)
    print("=" * 60)

    # Energy
    energy_desc = {
        1: "High energy, upbeat, celebratory",
        2: "Moderate-high, engaging, rhythmic",
        3: "Moderate-low, reflective, slower",
        4: "Deep worship, contemplative, intimate",
    }
    energy = song.energy
    if energy is None:
        energy_display = "N/A"
        desc = "Unknown"
    else:
        desc = energy_desc.get(int(energy), "Unknown")
        energy_display = int(energy) if energy == int(energy) else energy
    print()
    print(f"Energy:  {energy_display} - {desc}")

    # Tags
    if song.tags:
        tags_parts = []
        for moment, weight in song.tags.items():
            if weight == 3:
                tags_parts.append(moment)
            else:
                tags_parts.append(f"{moment}({weight})")
        print(f"Tags:    {', '.join(tags_parts)}")
    else:
        print("Tags:    (none)")

    # Recency section
    print()
    print("-" * 60)
    print("RECENCY")
    print("-" * 60)
    print(f"Score:          {recency_score:.2f}")

    if days_since is not None:
        print(f"Last used:      {days_since} day(s) ago")
    else:
        print("Last used:      never")

    # Usage history section
    print()
    print("-" * 60)
    print(f"USAGE HISTORY ({len(usages)} time(s))")
    print("-" * 60)

    if usages:
        for entry in usages:
            moments_str = ", ".join(entry["moments"])
            print(f"  {entry['date']}  {moments_str}")
    else:
        print("  (no usage history)")

    print()
