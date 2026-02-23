"""
Markdown command - regenerate markdown from existing setlist.
"""

from library import (
    Setlist,
    format_setlist_markdown,
    get_repositories,
)


def run(date, output_dir, history_dir, label="", event_type=""):
    """
    Regenerate markdown from existing setlist history.

    Args:
        date: Target date (YYYY-MM-DD) or None for latest
        output_dir: Custom output directory
        history_dir: Custom history directory
        label: Optional label for multiple setlists per date
        event_type: Optional event type slug
    """
    from cli.cli_utils import resolve_paths, handle_error, validate_label, find_setlist_or_fail, resolve_event_type

    label = validate_label(label)

    # Paths
    paths = resolve_paths(output_dir, history_dir)
    output_dir_path = paths.output_dir
    history_dir_path = paths.history_dir

    # Load data via repositories
    repos = get_repositories(history_dir=history_dir_path, output_dir=output_dir_path)

    # Resolve event type
    et = resolve_event_type(repos, event_type)
    et_slug = event_type
    et_name = et.name if et and not (et_slug == "" or et_slug == "main") else ""

    print("Loading songs...")
    songs = repos.songs.get_all()
    print(f"Loaded {len(songs)} songs")

    # Find target setlist
    target_setlist = find_setlist_or_fail(repos, date, label, event_type=et_slug)

    # Convert to Setlist object
    setlist = Setlist(
        date=target_setlist["date"],
        moments=target_setlist["moments"],
        label=target_setlist.get("label", ""),
        event_type=target_setlist.get("event_type", ""),
    )

    # Display what we're generating
    header = f"\nRegenerating markdown for {setlist.date}"
    if et_name:
        header += f" | {et_name}"
    if setlist.label:
        header += f" ({setlist.label})"
    print(header + "...")
    print("Moments:")
    for moment, song_list in setlist.moments.items():
        display_moment = moment.capitalize()
        print(f"  {display_moment}: {', '.join(song_list)}")

    # Generate markdown
    markdown = format_setlist_markdown(setlist, songs, event_type_name=et_name)

    # Write output via repository (handles subdirectory routing)
    md_path = repos.output.save_markdown(setlist.date, markdown, label=setlist.label, event_type=et_slug)
    print(f"\n✓ Markdown saved to: {md_path}")
