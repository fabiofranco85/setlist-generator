#!/usr/bin/env python3
"""
Setlist Generator for Church Services - CLI Entry Point

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
from datetime import datetime
from pathlib import Path

from setlist import (
    MOMENTS_CONFIG,
    format_setlist_markdown,
    generate_setlist,
    load_history,
    load_songs,
    save_setlist_history,
)


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
    setlist = generate_setlist(songs, history, args.date, overrides)

    # Display summary
    print(f"\n{'=' * 50}")
    print(f"SETLIST FOR {args.date}")
    print(f"{'=' * 50}")
    for moment, song_list in setlist.moments.items():
        print(f"\n{moment.upper()}:")
        for song in song_list:
            print(f"  - {song}")

    # Generate markdown
    markdown = format_setlist_markdown(setlist, songs)

    # Save files
    output_path = Path(args.output) if args.output else setlists_path / f"{args.date}.md"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\nMarkdown saved to: {output_path}")

    if not args.no_save:
        save_setlist_history(setlist, setlists_path)
        print(f"History saved to: {setlists_path / f'{args.date}.json'}")
    else:
        print("(Dry run - history not saved)")


if __name__ == "__main__":
    main()
