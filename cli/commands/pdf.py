"""
PDF command - generate PDF from existing setlist.
"""

from library import (
    Setlist,
    generate_setlist_pdf,
    get_repositories,
)


def run(date, output_dir, history_dir):
    """
    Generate PDF from existing setlist history.

    Args:
        date: Target date (YYYY-MM-DD) or None for latest
        output_dir: Custom output directory
        history_dir: Custom history directory
    """
    from cli.cli_utils import resolve_paths, handle_error

    # Paths
    paths = resolve_paths(output_dir, history_dir)
    output_dir_path = paths.output_dir
    history_dir_path = paths.history_dir

    # Load data via repositories
    repos = get_repositories(history_dir=history_dir_path, output_dir=output_dir_path)

    print("Loading songs...")
    songs = repos.songs.get_all()
    print(f"Loaded {len(songs)} songs")

    print("Loading history...")
    history = repos.history.get_all()
    if not history:
        handle_error("No history files found. Generate a setlist first.")

    print(f"Found {len(history)} historical setlists")

    # Find target setlist
    if date:
        # Find specific date
        target_setlist = None
        for setlist_dict in history:
            if setlist_dict.get("date") == date:
                target_setlist = setlist_dict
                break

        if not target_setlist:
            print(f"Error: Setlist for {date} not found in history")
            print(f"Available dates: {', '.join(s['date'] for s in history[-5:] if 'date' in s)}")
            raise SystemExit(1)
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
    output_dir_path.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir_path / f"{setlist.date}.pdf"

    try:
        generate_setlist_pdf(setlist, songs, pdf_path)
        print(f"\n✓ PDF saved to: {pdf_path}")
    except ImportError:
        print("\nError: ReportLab library not installed.")
        print("Install with: uv sync            (installs all dependencies)")
        print("         or: uv add reportlab    (adds to pyproject.toml)")
        print("         or: pip install reportlab")
        raise SystemExit(1)
    except Exception as e:
        handle_error(f"Generating PDF: {e}")
