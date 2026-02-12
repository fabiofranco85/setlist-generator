"""
Markdown command - regenerate markdown from existing setlist.
"""

from library import (
    Setlist,
    format_setlist_markdown,
    get_repositories,
)


def run(date, output_dir, history_dir, label=""):
    """
    Regenerate markdown from existing setlist history.

    Args:
        date: Target date (YYYY-MM-DD) or None for latest
        output_dir: Custom output directory
        history_dir: Custom history directory
        label: Optional label for multiple setlists per date
    """
    from cli.cli_utils import resolve_paths, handle_error, validate_label, find_setlist_or_fail

    label = validate_label(label)

    # Paths
    paths = resolve_paths(output_dir, history_dir)
    output_dir_path = paths.output_dir
    history_dir_path = paths.history_dir

    # Load data via repositories
    repos = get_repositories(history_dir=history_dir_path, output_dir=output_dir_path)

    print("Loading songs...")
    songs = repos.songs.get_all()
    print(f"Loaded {len(songs)} songs")

    # Find target setlist
    target_setlist = find_setlist_or_fail(repos, date, label)

    # Convert to Setlist object
    setlist = Setlist(
        date=target_setlist["date"],
        moments=target_setlist["moments"],
        label=target_setlist.get("label", ""),
    )

    # Display what we're generating
    header = f"\nRegenerating markdown for {setlist.date}"
    if setlist.label:
        header += f" ({setlist.label})"
    print(header + "...")
    print("Moments:")
    for moment, song_list in setlist.moments.items():
        display_moment = moment.capitalize()
        print(f"  {display_moment}: {', '.join(song_list)}")

    # Generate markdown
    markdown = format_setlist_markdown(setlist, songs)

    # Write output
    output_dir_path.mkdir(parents=True, exist_ok=True)
    output_path = output_dir_path / f"{setlist.setlist_id}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\n✓ Markdown saved to: {output_path}")
