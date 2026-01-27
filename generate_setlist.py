#!/usr/bin/env python3
"""
Setlist Generator for Church Services

Generates setlists based on:
- Song tags (moments) with optional weights
- Historical data (avoids recently used songs)
- Manual overrides via command line

Usage:
    python generate_setlist.py [options]

Examples:
    python generate_setlist.py
    python generate_setlist.py --date 2026-02-01
    python generate_setlist.py --override "louvor:Oceanos,Santo Pra Sempre"
    python generate_setlist.py --override "prelúdio:Estamos de Pé" --override "louvor:Oceanos"
"""

import argparse
import csv
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path


# Configuration
MOMENTS_CONFIG = {
    "prelúdio": 1,
    "ofertório": 1,
    "saudação": 1,
    "crianças": 1,
    "louvor": 4,
    "poslúdio": 1,
}

DEFAULT_WEIGHT = 3
RECENCY_PENALTY_PERFORMANCES = 3  # Number of performances until "fresh"

# Energy ordering configuration
ENERGY_ORDERING_ENABLED = True  # Master switch to enable/disable feature
ENERGY_ORDERING_RULES = {
    "louvor": "ascending",  # 1→4 (upbeat to worship)
    # Future: "ofertório": "descending", etc.
}
DEFAULT_ENERGY = 2.5  # Default for songs without energy metadata


def parse_tags(tags_str: str) -> dict[str, int]:
    """
    Parse tags string into dict of {moment: weight}.
    Supports formats: 'louvor', 'louvor(5)', 'louvor,prelúdio(3)'
    """
    if not tags_str.strip():
        return {}

    tags = {}
    for tag in tags_str.split(","):
        tag = tag.strip()
        if not tag:
            continue

        # Check for weight in parentheses: tag(weight)
        match = re.match(r"^(.+?)\((\d+)\)$", tag)
        if match:
            moment = match.group(1).strip()
            weight = int(match.group(2))
        else:
            moment = tag
            weight = DEFAULT_WEIGHT

        tags[moment] = weight

    return tags


def load_songs(base_path: Path) -> dict[str, dict]:
    """
    Load songs from tags.csv and their content from chords/*.md files.
    Returns: {song_title: {"tags": {moment: weight}, "energy": float, "content": str}}
    """
    songs = {}
    tags_file = base_path / "tags.csv"
    chords_path = base_path / "chords"

    with open(tags_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            title = row["song"]

            # Parse energy (default if missing or invalid)
            energy_str = row.get("energy", "").strip()
            try:
                energy = float(energy_str) if energy_str else DEFAULT_ENERGY
            except ValueError:
                energy = DEFAULT_ENERGY

            # Parse tags (existing logic)
            tags = parse_tags(row["tags"])

            # Load song content from chords folder
            song_file = chords_path / f"{title}.md"
            content = ""
            if song_file.exists():
                with open(song_file, "r", encoding="utf-8") as sf:
                    content = sf.read()

            songs[title] = {
                "tags": tags,
                "energy": energy,
                "content": content
            }

    return songs


def load_history(setlists_path: Path) -> list[dict]:
    """
    Load historical setlists, sorted by date (most recent first).
    """
    history = []

    if not setlists_path.exists():
        return history

    for file in setlists_path.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            history.append(data)

    # Sort by date, most recent first
    history.sort(key=lambda x: x.get("date", ""), reverse=True)
    return history


def calculate_recency_scores(songs: dict, history: list[dict]) -> dict[str, float]:
    """
    Calculate the recency score for each song.
    Higher score = longer since last used = better candidate.

    Returns: {song_title: recency_score}
    """
    scores = {}

    # Initialize all songs with max score (never used)
    for title in songs:
        scores[title] = 1.0

    # Penalize recently used songs
    for i, setlist in enumerate(history[:RECENCY_PENALTY_PERFORMANCES]):
        penalty_factor = 1 - ((RECENCY_PENALTY_PERFORMANCES - i) / RECENCY_PENALTY_PERFORMANCES)

        # Get all songs from this setlist
        for moment, song_list in setlist.get("moments", {}).items():
            for song in song_list:
                if song in scores:
                    # Apply penalty (more recent = lower score)
                    scores[song] = min(scores[song], penalty_factor)

    return scores


def select_songs_for_moment(
    moment: str,
    count: int,
    songs: dict,
    recency_scores: dict,
    already_selected: set,
    overrides: list[str] | None = None
) -> list[tuple[str, float]]:
    """
    Select songs for a specific moment.
    Returns list of (title, energy) tuples.
    """
    selected = []

    # Handle overrides first
    if overrides:
        for song in overrides:
            if song in songs and song not in already_selected:
                energy = songs[song].get("energy", DEFAULT_ENERGY)
                selected.append((song, energy))
                already_selected.add(song)

        if len(selected) >= count:
            return selected[:count]

    # Get candidate songs for this moment
    candidates = []
    for title, data in songs.items():
        if title in already_selected:
            continue
        if moment not in data["tags"]:
            continue

        weight = data["tags"][moment]
        recency = recency_scores.get(title, 1.0)

        # Combined score: weight * recency
        # This prioritizes high-weight songs that haven't been used recently
        score = weight * (recency + 0.1)  # +0.1 to avoid zero scores
        candidates.append((title, score))

    # Sort by score (descending) with some randomization
    # Add small random factor to avoid always picking the same songs
    candidates.sort(key=lambda x: x[1] + random.uniform(0, 0.5), reverse=True)

    # Select remaining needed songs
    for title, _ in candidates:
        if len(selected) >= count:
            break
        energy = songs[title].get("energy", DEFAULT_ENERGY)
        selected.append((title, energy))
        already_selected.add(title)

    return selected


def apply_energy_ordering(
    moment: str,
    selected_songs: list[tuple[str, float]],
    override_count: int = 0
) -> list[str]:
    """
    Sort songs by energy level according to moment-specific rules.
    Preserves the order of overridden songs (first override_count songs).

    Args:
        moment: The moment name (e.g., "louvor")
        selected_songs: List of (title, energy) tuples
        override_count: Number of songs at the start that were manually overridden

    Returns:
        List of song titles sorted by energy (except overrides)
    """
    if not ENERGY_ORDERING_ENABLED:
        return [title for title, _ in selected_songs]

    rule = ENERGY_ORDERING_RULES.get(moment)
    if not rule:
        return [title for title, _ in selected_songs]

    # Separate overridden songs from auto-selected songs
    overridden = selected_songs[:override_count]
    auto_selected = selected_songs[override_count:]

    # Sort only auto-selected songs by energy
    if rule == "ascending":
        # Low to high: 1→2→3→4 (upbeat to worship)
        sorted_auto = sorted(auto_selected, key=lambda x: x[1])
    elif rule == "descending":
        # High to low: 4→3→2→1 (worship to upbeat)
        sorted_auto = sorted(auto_selected, key=lambda x: x[1], reverse=True)
    else:
        sorted_auto = auto_selected

    # Combine: overrides first (in original order), then sorted auto-selected
    final_songs = [title for title, _ in overridden] + [title for title, _ in sorted_auto]

    return final_songs


def generate_setlist(
    songs: dict,
    history: list[dict],
    overrides: dict[str, list[str]] | None = None
) -> dict[str, list[str]]:
    """
    Generate a complete setlist for all moments.
    """
    recency_scores = calculate_recency_scores(songs, history)
    already_selected = set()
    setlist = {}

    for moment, count in MOMENTS_CONFIG.items():
        moment_overrides = overrides.get(moment) if overrides else None
        override_count = len(moment_overrides) if moment_overrides else 0

        selected_with_energy = select_songs_for_moment(
            moment, count, songs, recency_scores, already_selected, moment_overrides
        )

        # Apply energy-based ordering (preserves override order)
        ordered_songs = apply_energy_ordering(moment, selected_with_energy, override_count)
        setlist[moment] = ordered_songs

    return setlist


def format_setlist_markdown(setlist: dict[str, list[str]], songs: dict, date: str) -> str:
    """
    Format setlist as markdown with song content.
    """
    lines = [f"# Setlist - {date}", ""]

    for moment, song_list in setlist.items():
        lines.append(f"## {moment.capitalize()}")
        lines.append("")

        for song_title in song_list:
            content = songs.get(song_title, {}).get("content", "")
            if content:
                lines.append(content)
            else:
                lines.append(f"### {song_title}")
                lines.append("")
                lines.append("*(Content not found)*")
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("")

    return "\n".join(lines)


def save_setlist_history(setlist: dict[str, list[str]], date: str, setlists_path: Path):
    """
    Save setlist to history as JSON.
    """
    setlists_path.mkdir(exist_ok=True)

    history_file = setlists_path / f"{date}.json"
    data = {
        "date": date,
        "moments": setlist
    }

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_overrides(override_args: list[str] | None) -> dict[str, list[str]]:
    """
    Parse override arguments in format 'moment:song1,song2'.
    """
    if not override_args:
        return {}

    overrides = {}
    for override in override_args:
        if ":" not in override:
            print(f"Warning: Invalid override format '{override}', expected 'moment:song1,song2'")
            continue

        moment, songs_str = override.split(":", 1)
        moment = moment.strip()
        songs = [s.strip() for s in songs_str.split(",")]

        if moment not in MOMENTS_CONFIG:
            print(f"Warning: Unknown moment '{moment}'")
            continue

        overrides[moment] = songs

    return overrides


def main():
    parser = argparse.ArgumentParser(
        description="Generate a setlist for church services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
      Generate setlist for today

  %(prog)s --date 2026-02-01
      Generate setlist for specific date

  %(prog)s --override "louvor:Oceanos,Santo Pra Sempre"
      Force specific songs for louvor moment

  %(prog)s --override "prelúdio:Estamos de Pé" --override "louvor:Oceanos"
      Multiple overrides

Moments: prelúdio, ofertório, saudação, crianças, louvor (4 songs), poslúdio
        """
    )

    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date for the setlist (default: today)"
    )

    parser.add_argument(
        "--override",
        action="append",
        help="Override songs for a moment: 'moment:song1,song2'"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save to history (dry run)"
    )

    parser.add_argument(
        "--output",
        help="Output file path (default: setlists/YYYY-MM-DD.md)"
    )

    args = parser.parse_args()

    # Paths
    base_path = Path(__file__).parent
    setlists_path = base_path / "setlists"

    # Load data
    print("Loading songs...")
    songs = load_songs(base_path)
    print(f"Loaded {len(songs)} songs")

    print("Loading history...")
    history = load_history(setlists_path)
    print(f"Found {len(history)} historical setlists")

    # Parse overrides
    overrides = parse_overrides(args.override)
    if overrides:
        print(f"Overrides: {overrides}")

    # Generate setlist
    print("\nGenerating setlist...")
    setlist = generate_setlist(songs, history, overrides)

    # Display summary
    print(f"\n{'=' * 50}")
    print(f"SETLIST FOR {args.date}")
    print(f"{'=' * 50}")
    for moment, song_list in setlist.items():
        print(f"\n{moment.upper()}:")
        for song in song_list:
            print(f"  - {song}")

    # Generate markdown
    markdown = format_setlist_markdown(setlist, songs, args.date)

    # Save files
    output_path = Path(args.output) if args.output else setlists_path / f"{args.date}.md"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\nMarkdown saved to: {output_path}")

    if not args.no_save:
        save_setlist_history(setlist, args.date, setlists_path)
        print(f"History saved to: {setlists_path / f'{args.date}.json'}")
    else:
        print("(Dry run - history not saved)")


if __name__ == "__main__":
    main()
