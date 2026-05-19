"""Delete command — remove a setlist's history record and output files."""

from library import get_repositories


def run(date, label, event_type, yes, output_dir, history_dir):
    """Delete a setlist (history JSON + markdown + PDF + lyrics PDF).

    Args:
        date: Target date (YYYY-MM-DD). Required.
        label: Optional label (empty for unlabeled setlist).
        event_type: Optional event type slug (empty for default type).
        yes: If True, skip the confirmation prompt.
        output_dir: Custom output directory.
        history_dir: Custom history directory.
    """
    import click

    from cli.cli_utils import (
        handle_error,
        resolve_event_type,
        resolve_paths,
        validate_label,
    )

    label = validate_label(label)

    paths = resolve_paths(output_dir, history_dir)
    repos = get_repositories(history_dir=paths.history_dir, output_dir=paths.output_dir)

    # Resolve event type — same routing helper used by every other command
    # so subdirectory placement stays consistent.
    et = resolve_event_type(repos, event_type)
    et_slug = event_type
    _ = et  # event type is fetched only to validate that the slug exists

    if not repos.history.exists(date, label=label, event_type=et_slug):
        label_desc = f" with label '{label}'" if label else ""
        type_desc = f" for event type '{et_slug}'" if et_slug and et_slug != "main" else ""
        handle_error(f"No setlist found for {date}{label_desc}{type_desc}")

    target_desc = date
    if label:
        target_desc += f" (label: {label})"
    if et_slug and et_slug != "main":
        target_desc += f" (event type: {et_slug})"

    if not yes:
        click.confirm(
            f"Delete setlist {target_desc}? This removes the history record and all output files.",
            abort=True,
        )

    # 1. Delete history first so a partial failure here leaves outputs we
    # can still find via the markdown filename — easier to recover from
    # than the opposite ordering.
    repos.history.delete(date, label=label, event_type=et_slug)

    # 2. Delete outputs (markdown + every PDF variant).
    deleted_outputs = repos.output.delete_outputs(date, label=label, event_type=et_slug)

    # --- Report ---
    print(f"\nDeleted setlist {target_desc}")

    if repos.history.backend_name == "filesystem":
        hist_dir = paths.history_dir
        if et_slug and et_slug != "main":
            hist_dir = hist_dir / et_slug
        setlist_id = f"{date}_{label}" if label else date
        print(f"  History: {hist_dir / f'{setlist_id}.json'}")
    else:
        print(f"  History: {repos.history.backend_name} database")

    for path in deleted_outputs:
        print(f"  Output:  {path}")
    if not deleted_outputs:
        print("  Output:  (no output files were present)")
