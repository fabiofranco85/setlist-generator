"""
View setlist command - display generated setlists.
"""

from datetime import datetime
from pathlib import Path

from library import canonical_moment_order, get_repositories
from library.event_type import is_default_event_type


def format_date_display(date_str: str) -> str:
    """Format date for display.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Formatted date like "Saturday, February 15, 2026"
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A, %B %d, %Y")


def render_setlist(
    setlist_dict: dict,
    songs: dict,
    show_keys: bool = False,
    moments_order: list[str] | None = None,
) -> str:
    """Render a setlist's header and moments as text.

    The pure counterpart of :func:`display_setlist`: returns the text instead
    of printing it, so callers can page it (``songbook setlists``) or print it
    (``songbook view-setlist``). The FILES section is deliberately excluded —
    it belongs to ``view-setlist``, not to the setlist itself.

    Args:
        setlist_dict: Setlist dictionary with date and moments
        songs: Dictionary of song name -> Song object (used for keys)
        show_keys: Whether to show song keys
        moments_order: Explicit moment ordering from the event type (see
            :func:`display_setlist`)

    Returns:
        The rendered setlist text.
    """
    from cli.picker import extract_key

    date = setlist_dict["date"]
    # Backends store label as None (or omit it), not "" — normalize.
    label = setlist_dict.get("label") or ""
    moments = setlist_dict["moments"]

    out: list[str] = []

    out.append("")
    out.append("=" * 60)
    header = f"SETLIST FOR {date}"
    if label:
        header += f" ({label})"
    out.append(header)
    out.append(format_date_display(date))
    out.append("=" * 60)
    out.append("")

    # Display each moment using the event type's moments_order so that
    # custom moments are preserved AND the user-defined service order is
    # honored (postgres JSONB doesn't preserve dict insertion order).
    moments_ref = {m: 0 for m in moments_order} if moments_order else None
    for moment in canonical_moment_order(moments, reference_config=moments_ref):
        song_list = moments[moment]
        if not song_list:
            continue

        out.append(f"{moment.upper()}:")
        for song_title in song_list:
            key = ""
            if show_keys:
                song = songs.get(song_title)
                key = extract_key(song.content) if song else ""
            out.append(f"  - {song_title} ({key})" if key else f"  - {song_title}")
        out.append("")

    return "\n".join(out)


def display_setlist(
    setlist_dict: dict,
    songs: dict,
    show_keys: bool = False,
    output_dir: Path | None = None,
    history_dir: Path | None = None,
    event_type: str = "",
    moments_order: list[str] | None = None,
):
    """Display a setlist in formatted output.

    Args:
        setlist_dict: Setlist dictionary with date and moments
        songs: Dictionary of song name -> Song object
        show_keys: Whether to show song keys
        output_dir: Custom output directory (for file paths)
        history_dir: Custom history directory (for file paths)
        event_type: Event type slug for subdirectory routing (empty = default)
        moments_order: Explicit moment ordering from the event type — when
            the setlist was loaded from postgres, ``setlist_dict["moments"]``
            comes back in JSONB key order, not the user-defined service
            order. Pass the event type's ``moments_order`` to recover the
            intended order. When None, falls back to ``MOMENTS_CONFIG``.
    """
    date = setlist_dict["date"]
    label = setlist_dict.get("label") or ""

    output_dir = output_dir or Path("output")
    history_dir = history_dir or Path("history")

    setlist_id = f"{date}_{label}" if label else date

    # Non-default event types are routed to subdirectories on the
    # filesystem backend. Mirror that here so the FILES section reports
    # the real on-disk location (and shows ✓ when the files exist).
    if not is_default_event_type(event_type):
        output_dir = output_dir / event_type
        history_dir = history_dir / event_type

    print(render_setlist(setlist_dict, songs, show_keys=show_keys, moments_order=moments_order))

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
    display_setlist(
        target_setlist, songs, show_keys=keys,
        output_dir=output_dir_path, history_dir=history_dir_path,
        event_type=event_type,
        moments_order=et.moments_order if et else None,
    )
