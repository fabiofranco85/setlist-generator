"""
Transpose command - display a song transposed to a different key.
"""

from pathlib import Path

from library import load_songs
from library.transposer import (
    calculate_semitones,
    resolve_target_key,
    should_use_flats,
    transpose_content,
)


def _extract_key(content: str) -> str | None:
    """Extract the key from the ``### Title (Key)`` heading."""
    if not content:
        return None
    first_line = content.split("\n")[0].strip()
    if "(" in first_line and ")" in first_line:
        start = first_line.rfind("(")
        end = first_line.rfind(")")
        if start != -1 and end != -1 and end > start:
            return first_line[start + 1 : end].strip()
    return None


def run(song_name: str, to_key: str, save: bool = False):
    """Transpose a song and display the result.

    Args:
        song_name: Name of the song to transpose.
        to_key: Target key (e.g. "G", "Bb", "F#m").
        save: If True, overwrite the chord file with transposed content.
    """
    from cli.cli_utils import handle_error

    try:
        songs = load_songs(Path.cwd())
    except Exception as e:
        handle_error(f"Loading songs: {e}")

    if not songs:
        print("No songs found.")
        raise SystemExit(1)

    song = songs.get(song_name)
    if not song:
        # Fuzzy search
        print(f"\nSong not found: '{song_name}'")
        similar = [n for n in songs if song_name.lower() in n.lower()]
        if similar:
            print("\nDid you mean one of these?")
            for n in similar[:5]:
                print(f"  • {n}")
            print(f'\nTry: songbook transpose "{similar[0]}" --to {to_key}')
        else:
            print("\nNo similar songs found.")
            print("Use 'songbook view-song --list' to see all available songs.")
        raise SystemExit(1)

    content = song.content or ""
    original_key = _extract_key(content)

    if not original_key:
        handle_error(f"Could not detect key for '{song_name}'. "
                     "Ensure the chord file has a ### Title (Key) heading.")

    # Calculate transposition
    effective_key = resolve_target_key(original_key, to_key)
    try:
        semitones = calculate_semitones(original_key, effective_key)
    except ValueError as e:
        handle_error(str(e))

    use_flats = should_use_flats(effective_key)
    transposed = transpose_content(content, semitones, use_flats)

    # Parse heading for display
    lines = transposed.split("\n")
    title = song_name
    display_key = to_key
    display_content = transposed

    if lines and lines[0].strip().startswith("###"):
        heading = lines[0].replace("###", "").strip()
        display_content = "\n".join(lines[1:]).strip()
        if "(" in heading and ")" in heading:
            paren_start = heading.rfind("(")
            title = heading[:paren_start].strip()
            display_key = heading[paren_start + 1 : heading.rfind(")")].strip()

    # Display
    print()
    print("=" * 70)
    if semitones == 0:
        print(f"{title} ({original_key})")
        print("=" * 70)
        print(f"\n  Already in {to_key} — showing original.")
    else:
        print(f"{title} ({display_key})  [original: {original_key}]")
        print("=" * 70)

    # Metadata
    if song.tags:
        tags_display = []
        for moment, weight in song.tags.items():
            if weight == 3:
                tags_display.append(moment)
            else:
                tags_display.append(f"{moment}({weight})")
        print(f"\nTags:   {', '.join(tags_display)}")

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
    print()

    if display_content:
        print(display_content)
    else:
        print("(No chord content available)")
    print()

    # Save transposed content to chord file
    if save and semitones != 0:
        chord_file = Path.cwd() / "chords" / f"{song_name}.md"
        chord_file.write_text(transposed, encoding="utf-8")
        print(f"Saved transposed chords to {chord_file}")
    elif save and semitones == 0:
        print(f"Nothing to save — song is already in {to_key}.")
