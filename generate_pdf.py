#!/usr/bin/env python3
"""
Generate PDF from existing setlist history.

This script takes an existing setlist from history and generates a PDF,
useful for regenerating PDFs after updates or for specific past dates.

Usage:
    python generate_pdf.py                    # Latest setlist
    python generate_pdf.py --date 2026-01-25  # Specific date
"""

import argparse
from pathlib import Path

from setlist import (
    Setlist,
    generate_setlist_pdf,
    get_output_paths,
    load_history,
    load_songs,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate PDF from existing setlist history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
      Generate PDF for the latest setlist in history

  %(prog)s --date 2026-01-25
      Generate PDF for a specific date

  %(prog)s --date 2026-01-25 --output-dir custom/output
      Generate PDF with custom output directory
        """,
    )

    parser.add_argument(
        "--date",
        default=None,
        help="Date of the setlist (default: latest in history)",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for PDF output (default: output/)",
    )

    parser.add_argument(
        "--history-dir",
        default=None,
        help="Directory to load history from (default: history/)",
    )

    args = parser.parse_args()

    # Paths
    base_path = Path(__file__).parent
    paths = get_output_paths(base_path, args.output_dir, args.history_dir)
    output_dir = paths.output_dir
    history_dir = paths.history_dir

    # Load data
    print("Loading songs...")
    songs = load_songs(base_path)
    print(f"Loaded {len(songs)} songs")

    print("Loading history...")
    history = load_history(history_dir)
    if not history:
        print("Error: No history files found. Generate a setlist first.")
        return

    print(f"Found {len(history)} historical setlists")

    # Find target setlist
    if args.date:
        # Find specific date
        target_setlist = None
        for setlist_dict in history:
            if setlist_dict["date"] == args.date:
                target_setlist = setlist_dict
                break

        if not target_setlist:
            print(f"Error: Setlist for {args.date} not found in history")
            print(f"Available dates: {', '.join(s['date'] for s in history[-5:])}")
            return
    else:
        # Use latest (first in history - already sorted by date desc)
        target_setlist = history[0]

    # Convert to Setlist object
    setlist = Setlist(date=target_setlist["date"], moments=target_setlist["moments"])

    # Display what we're generating
    print(f"\nGenerating PDF for {setlist.date}...")
    print("Moments:")
    for moment, song_list in setlist.moments.items():
        display_moment = moment.capitalize()
        print(f"  {display_moment}: {', '.join(song_list)}")

    # Generate PDF
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{setlist.date}.pdf"

    try:
        generate_setlist_pdf(setlist, songs, pdf_path)
        print(f"\n✓ PDF saved to: {pdf_path}")
    except ImportError:
        print(
            "\nError: ReportLab library not installed."
        )
        print("Install with: pip install reportlab")
        print("         or: uv pip install reportlab")
    except Exception as e:
        print(f"\nError generating PDF: {e}")
        raise


if __name__ == "__main__":
    main()
