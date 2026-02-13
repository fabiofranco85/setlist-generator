"""
Label command — add, rename, or remove labels on existing setlists.
"""

from library import (
    format_setlist_markdown,
    get_repositories,
    relabel_setlist,
)


def run(date, label, to_label, remove, output_dir, history_dir):
    """
    Manage setlist labels (add, rename, or remove).

    Args:
        date: Target date (YYYY-MM-DD)
        label: Source label (empty string for unlabeled)
        to_label: New label to assign (None if removing)
        remove: Whether to remove the label
        output_dir: Custom output directory
        history_dir: Custom history directory
    """
    from cli.cli_utils import resolve_paths, handle_error, validate_label, find_setlist_or_fail

    # --- Validate inputs ---
    if not remove and not to_label:
        handle_error("Either --to or --remove is required")

    if remove and to_label:
        handle_error("--to and --remove are mutually exclusive")

    label = validate_label(label)

    if remove and not label:
        handle_error("--remove requires --label (nothing to remove from an unlabeled setlist)")

    new_label = ""
    if to_label:
        new_label = validate_label(to_label)

    if new_label == label:
        handle_error(f"Source and target labels are the same: '{label or '(unlabeled)'}'")

    # --- Setup ---
    paths = resolve_paths(output_dir, history_dir)
    repos = get_repositories(history_dir=paths.history_dir, output_dir=paths.output_dir)

    # --- Load source setlist ---
    source_dict = find_setlist_or_fail(repos, date, label=label)

    source_desc = f"{date}"
    if label:
        source_desc += f" ({label})"

    target_desc = f"{date}"
    if new_label:
        target_desc += f" ({new_label})"

    # --- Check target doesn't conflict ---
    if repos.history.exists(date, label=new_label):
        target_name = new_label or "(unlabeled)"
        handle_error(
            f"A setlist already exists for {date} with label '{target_name}'.\n"
            f"Delete or rename it first."
        )

    # --- Relabel ---
    new_setlist = relabel_setlist(source_dict, new_label)

    # --- Write-first, delete-second (crash-safe) ---
    # 1. Save new history
    repos.history.save(new_setlist)

    # 2. Regenerate and save markdown
    songs = repos.songs.get_all()
    markdown = format_setlist_markdown(new_setlist, songs)
    md_path = repos.output.save_markdown(date, markdown, label=new_label)

    # 3. Delete old history
    repos.history.delete(date, label=label)

    # 4. Delete old outputs
    deleted_outputs = repos.output.delete_outputs(date, label=label)

    # --- Report ---
    if remove:
        action = f"Removed label '{label}' from"
    elif label:
        action = f"Renamed label '{label}' -> '{new_label}' on"
    else:
        action = f"Added label '{new_label}' to"

    print(f"\n{action} setlist {date}")
    print(f"  History: {paths.history_dir / f'{new_setlist.setlist_id}.json'}")
    print(f"  Markdown: {md_path}")

    had_pdf = any(p.suffix == ".pdf" for p in deleted_outputs)
    if had_pdf:
        print(f"\n  Note: Old PDF was removed. Run 'songbook pdf --date {date}"
              + (f" --label {new_label}" if new_label else "")
              + "' to regenerate.")
