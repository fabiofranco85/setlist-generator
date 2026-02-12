"""
Generate command - create new setlists.
"""

from datetime import datetime
from pathlib import Path

from library import (
    MOMENTS_CONFIG,
    format_setlist_markdown,
    generate_setlist,
    generate_setlist_pdf,
    get_repositories,
)


def parse_overrides(override_args: tuple[str, ...] | None) -> dict[str, list[str]]:
    """
    Parse override arguments in format 'moment:song1,song2'.

    Args:
        override_args: Tuple of override strings

    Returns:
        Dictionary mapping moment names to song lists
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


def run(date, override, pdf, no_save, output_dir, history_dir, output, verbose=False,
        label="", replace_count=None):
    """
    Generate a setlist for a service date.

    Args:
        date: Target date (YYYY-MM-DD) or None for today
        override: Tuple of override strings (moment:song1,song2)
        pdf: Whether to generate PDF output
        no_save: Whether to skip saving to history (dry run)
        output_dir: Custom output directory
        history_dir: Custom history directory
        output: Custom output filename
        verbose: Whether to enable debug-level observability output
        label: Optional label for multiple setlists per date
        replace_count: Songs to replace when deriving (number string, "all", or None)
    """
    from cli.cli_utils import resolve_paths, print_metrics_summary, validate_label, handle_error
    from library.observability import Observability
    from library.replacer import derive_setlist
    from library.models import Setlist

    obs = Observability.for_cli(level="DEBUG" if verbose else "WARNING")

    # Validate label
    label = validate_label(label)

    # Validate --replace requires --label
    if replace_count is not None and not label:
        handle_error("--replace requires --label")

    # Use today if no date specified
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

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
    print(f"Found {len(history)} historical setlists")

    # Parse overrides
    overrides = parse_overrides(override)
    if overrides:
        print(f"Overrides: {overrides}")

    # Derivation path: when label is provided and a base setlist exists
    if label:
        existing = repos.history.get_by_date_all(date)
        if existing:
            # Derive from primary (first by label sort: unlabeled first)
            base = existing[0]
            print(f"\nDeriving setlist from base ({base.get('date')}"
                  f"{' / ' + base.get('label') if base.get('label') else ''})...")

            # Parse replace_count
            parsed_count = None
            if replace_count is not None:
                if replace_count.lower() == "all":
                    # Count total songs
                    total = sum(len(sl) for sl in base["moments"].values())
                    parsed_count = total
                else:
                    try:
                        parsed_count = int(replace_count)
                    except ValueError:
                        handle_error(f"Invalid --replace value: '{replace_count}'. Use a number or 'all'.")

            new_dict = derive_setlist(base, songs, history, replace_count=parsed_count)

            # Set label on the derived setlist
            new_dict["label"] = label

            setlist = Setlist(
                date=new_dict["date"],
                moments=new_dict["moments"],
                label=label,
            )
        else:
            # No base exists — generate fresh with label
            print(f"\nNo existing setlist for {date} — generating fresh with label '{label}'.")
            setlist = generate_setlist(songs, history, date, overrides, obs=obs, label=label)
    else:
        # Standard generation (no label)
        print("\nGenerating setlist...")
        setlist = generate_setlist(songs, history, date, overrides, obs=obs)

    # Display summary
    setlist_id = setlist.setlist_id
    print(f"\n{'=' * 50}")
    header = f"SETLIST FOR {date}"
    if label:
        header += f" ({label})"
    print(header)
    print(f"{'=' * 50}")
    for moment, song_list in setlist.moments.items():
        print(f"\n{moment.upper()}:")
        for song in song_list:
            print(f"  - {song}")

    # Generate markdown
    markdown = format_setlist_markdown(setlist, songs)

    # Save files
    output_path = Path(output) if output else output_dir_path / f"{setlist_id}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\nMarkdown saved to: {output_path}")

    if not no_save:
        repos.history.save(setlist)
        print(f"History saved to: {history_dir_path / f'{setlist_id}.json'}")
    else:
        print("(Dry run - history not saved)")

    # Generate PDF if requested
    if pdf:
        pdf_path = output_dir_path / f"{setlist_id}.pdf"
        print(f"\nGenerating PDF...")
        try:
            generate_setlist_pdf(setlist, songs, pdf_path)
            print(f"PDF saved to: {pdf_path}")
        except ImportError:
            print("Error: ReportLab library not installed.")
            print("Install with: uv sync            (installs all dependencies)")
            print("         or: uv add reportlab    (adds to pyproject.toml)")
            print("         or: pip install reportlab")
        except Exception as e:
            print(f"Error generating PDF: {e}")

    if verbose:
        print_metrics_summary(obs.metrics.get_summary())
