"""
View setlist command - display generated setlists.
"""

from datetime import datetime
from pathlib import Path

from library import get_repositories
from library.config import MOMENTS_CONFIG


def format_date_display(date_str: str) -> str:
    """Format date for display.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Formatted date like "Saturday, February 15, 2026"
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A, %B %d, %Y")


def display_setlist(setlist_dict: dict, songs: dict, show_keys: bool = False, output_dir: Path = None, history_dir: Path = None):
    """Display a setlist in formatted output.

    Args:
        setlist_dict: Setlist dictionary with date and moments
        songs: Dictionary of song name -> Song object
        show_keys: Whether to show song keys
        output_dir: Custom output directory (for file paths)
        history_dir: Custom history directory (for file paths)
    """
    date = setlist_dict["date"]
    label = setlist_dict.get("label", "")
    moments = setlist_dict["moments"]

    output_dir = output_dir or Path("output")
    history_dir = history_dir or Path("history")

    setlist_id = f"{date}_{label}" if label else date

    print("\n" + "=" * 60)
    header = f"SETLIST FOR {date}"
    if label:
        header += f" ({label})"
    print(header)
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
    output_md = output_dir / f"{setlist_id}.md"
    output_pdf = output_dir / f"{setlist_id}.pdf"
    history_json = history_dir / f"{setlist_id}.json"

    print("FILES:")
    print(f"  Markdown: {output_md}" + (" ✓" if output_md.exists() else " (not found)"))
    print(f"  PDF:      {output_pdf}" + (" ✓" if output_pdf.exists() else " (not generated)"))
    print(f"  History:  {history_json}" + (" ✓" if history_json.exists() else " (not found)"))
    print()


def run(date, keys, output_dir, history_dir, label="", event_type=""):
    """
    View generated setlist (latest or specific date).

    Args:
        date: Target date (YYYY-MM-DD) or None for latest
        keys: Whether to show song keys
        output_dir: Custom output directory
        history_dir: Custom history directory
        label: Optional label for multiple setlists per date
        event_type: Optional event type slug
    """
    from cli.cli_utils import resolve_paths, find_setlist_or_fail, validate_label, resolve_event_type

    label = validate_label(label)

    # Resolve paths
    paths = resolve_paths(output_dir, history_dir)
    history_dir_path = paths.history_dir
    output_dir_path = paths.output_dir

    # Load data via repositories
    repos = get_repositories(history_dir=history_dir_path, output_dir=output_dir_path)

    # Resolve event type for display name
    et = resolve_event_type(repos, event_type)

    # Find target setlist (handles errors internally)
    target_setlist = find_setlist_or_fail(repos, date, label, event_type=event_type)

    # Load songs if showing keys
    songs = {}
    if keys:
        try:
            songs = repos.songs.get_all()
        except Exception as e:
            print(f"Warning: Could not load songs: {e}")
            print("Continuing without keys...\n")

    # Display the setlist
    display_setlist(target_setlist, songs, show_keys=keys, output_dir=output_dir_path, history_dir=history_dir_path)
