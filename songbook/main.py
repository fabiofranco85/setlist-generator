"""
Main CLI entry point for songbook.

Provides a unified command-line interface for all songbook operations.
"""

import click


@click.group()
@click.version_option(version="1.0.0", prog_name="songbook")
def cli():
    """Church worship setlist generator.

    Unified CLI for managing worship service setlists.

    \b
    Core Commands:
      generate       Generate new setlist for a service date
      view-setlist   View generated setlist (markdown format)
      view-song      View song lyrics, chords, and metadata
      replace        Replace song in existing setlist
      pdf            Generate PDF from existing setlist
      list-moments   List available service moments

    \b
    Maintenance Commands:
      cleanup          Run data quality checks on history files
      fix-punctuation  Normalize punctuation in history files
      import-history   Import external setlist data

    Use 'songbook <command> --help' for command-specific help.
    """
    pass


@cli.command()
@click.option("--date", help="Target date (YYYY-MM-DD, default: today)")
@click.option("--override", multiple=True, help="Force songs: MOMENT:SONG1,SONG2")
@click.option("--pdf", is_flag=True, help="Generate PDF output")
@click.option("--no-save", is_flag=True, help="Dry run (don't save to history)")
@click.option("--output-dir", help="Custom markdown output directory")
@click.option("--history-dir", help="Custom history directory")
@click.option("--output", help="Custom output filename")
def generate(date, override, pdf, no_save, output_dir, history_dir, output):
    """Generate new setlist for a service date.

    \b
    Examples:
      songbook generate
      songbook generate --date 2026-02-15 --pdf
      songbook generate --override "louvor:Oceanos,Santo Pra Sempre"
      songbook generate --override "prelúdio:Estamos de Pé" --override "louvor:Oceanos"
    """
    from songbook.commands.generate import run
    run(date, override, pdf, no_save, output_dir, history_dir, output)


@cli.command("view-setlist")
@click.option("--date", help="Target date (default: latest)")
@click.option("--keys", "-k", is_flag=True, help="Show song keys")
@click.option("--output-dir", help="Custom output directory")
@click.option("--history-dir", help="Custom history directory")
def view_setlist(date, keys, output_dir, history_dir):
    """View generated setlist (markdown format).

    \b
    Examples:
      songbook view-setlist
      songbook view-setlist --keys
      songbook view-setlist --date 2026-02-15
    """
    from songbook.commands.view_setlist import run
    run(date, keys, output_dir, history_dir)


@cli.command("view-song")
@click.argument("song_name", required=False)
@click.option("--list", "-l", is_flag=True, help="List all songs")
@click.option("--no-metadata", is_flag=True, help="Hide tags/energy")
def view_song(song_name, list, no_metadata):
    """View song lyrics, chords, and metadata.

    \b
    Examples:
      songbook view-song "Oceanos"
      songbook view-song --list
      songbook view-song "Hosana" --no-metadata
    """
    from songbook.commands.view_song import run
    run(song_name, list, no_metadata)


@cli.command("list-moments")
def list_moments():
    """List available service moments.

    \b
    Shows all available moments with their song counts and descriptions.
    Useful for knowing what values to use with --moment arguments.
    """
    from songbook.commands.list_moments import run
    run()


@cli.command()
@click.option("--moment", required=True, help="Service moment (prelúdio, louvor, etc.)")
@click.option("--position", type=int, help="Position to replace (1-indexed)")
@click.option("--positions", help="Multiple positions (comma-separated)")
@click.option("--with", "replacement", help="Manual song selection")
@click.option("--date", help="Target date (default: latest)")
@click.option("--output-dir", help="Custom output directory")
@click.option("--history-dir", help="Custom history directory")
def replace(moment, position, positions, replacement, date, output_dir, history_dir):
    """Replace song in existing setlist.

    \b
    Examples:
      songbook replace --moment prelúdio
      songbook replace --moment louvor --position 2
      songbook replace --moment louvor --position 2 --with "Oceanos"
      songbook replace --moment louvor --positions 1,3
    """
    from songbook.commands.replace import run
    run(moment, position, positions, replacement, date, output_dir, history_dir)


@cli.command()
@click.option("--date", help="Target date (default: latest)")
@click.option("--output-dir", help="Custom output directory")
@click.option("--history-dir", help="Custom history directory")
def pdf(date, output_dir, history_dir):
    """Generate PDF from existing setlist.

    \b
    Examples:
      songbook pdf
      songbook pdf --date 2026-02-15
    """
    from songbook.commands.pdf import run
    run(date, output_dir, history_dir)


@cli.command()
@click.option("--history-dir", help="Custom history directory")
def cleanup(history_dir):
    """Run data quality checks on history files.

    \b
    Analyzes all history files for inconsistencies with tags.csv:
    - Automatically fixes capitalization mismatches
    - Identifies songs in history that don't exist in tags.csv
    - Provides fuzzy matching suggestions for similar song names
    - Creates timestamped backups before making changes
    """
    from songbook.commands.maintenance import run_cleanup
    run_cleanup(history_dir)


@cli.command("fix-punctuation")
@click.option("--history-dir", help="Custom history directory")
def fix_punctuation(history_dir):
    """Normalize punctuation in history files.

    \b
    Fixes punctuation differences in history files to match canonical
    song names from tags.csv (e.g., commas, hyphens).
    """
    from songbook.commands.maintenance import run_fix_punctuation
    run_fix_punctuation(history_dir)


@cli.command("import-history")
def import_history():
    """Import external setlist data.

    \b
    Imports setlist data from external sources and converts it to
    the internal history format. Requires editing the script first
    to add your data.
    """
    from songbook.commands.maintenance import run_import
    run_import()


if __name__ == "__main__":
    cli()
