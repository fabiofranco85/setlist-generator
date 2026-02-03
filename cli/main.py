"""
Main CLI entry point for songbook.

Provides a unified command-line interface for all songbook operations.
"""

import click
from cli.completions import (
    complete_song_names,
    complete_moment_names,
    complete_history_dates,
    complete_key_names,
)


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
      info           Show detailed statistics for a song
      transpose      Transpose a song to a different key
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
@click.option("--date", shell_complete=complete_history_dates, help="Target date (YYYY-MM-DD, default: today)")
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
    from cli.commands.generate import run
    run(date, override, pdf, no_save, output_dir, history_dir, output)


@cli.command("view-setlist")
@click.option("--date", shell_complete=complete_history_dates, help="Target date (default: latest)")
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
    from cli.commands.view_setlist import run
    run(date, keys, output_dir, history_dir)


@cli.command("view-song")
@click.argument("song_name", required=False, shell_complete=complete_song_names)
@click.option("--list", "-l", is_flag=True, help="List all songs")
@click.option("--no-metadata", is_flag=True, help="Hide tags/energy")
@click.option("--transpose", "-t", "transpose_to", shell_complete=complete_key_names, help="Transpose to key (e.g. G, Bb, F#m)")
def view_song(song_name, list, no_metadata, transpose_to):
    """View song lyrics, chords, and metadata.

    \b
    Examples:
      songbook view-song "Oceanos"
      songbook view-song --list
      songbook view-song "Hosana" --no-metadata
      songbook view-song "Oceanos" --transpose G
      songbook view-song "Oceanos" -t D
    """
    from cli.commands.view_song import run
    run(song_name, list, no_metadata, transpose_to)


@cli.command()
@click.argument("song_name", shell_complete=complete_song_names)
def info(song_name):
    """Show detailed statistics for a song.

    \b
    Displays metadata, recency score, and full usage history.

    \b
    Examples:
      songbook info "Oceanos"
      songbook info "Hosana"
    """
    from cli.commands.info import run
    run(song_name)


@cli.command()
@click.argument("song_name", shell_complete=complete_song_names)
@click.option("--to", "to_key", required=True, shell_complete=complete_key_names, help="Target key (e.g. G, Bb, F#m)")
@click.option("--save", is_flag=True, help="Overwrite the chord file with transposed chords")
def transpose(song_name, to_key, save):
    """Transpose a song to a different key.

    \b
    By default, shows a preview without modifying files.
    Use --save to overwrite the chord file with the transposed chords.

    \b
    Examples:
      songbook transpose "Oceanos" --to G          # preview only
      songbook transpose "Oceanos" --to G --save    # persist to file
      songbook transpose "Hosana" --to Bb
      songbook transpose "Lugar Secreto" --to A
    """
    from cli.commands.transpose import run
    run(song_name, to_key, save=save)


@cli.command("list-moments")
def list_moments():
    """List available service moments.

    \b
    Shows all available moments with their song counts and descriptions.
    Useful for knowing what values to use with --moment arguments.
    """
    from cli.commands.list_moments import run
    run()


@cli.command()
@click.option("--moment", required=True, shell_complete=complete_moment_names, help="Service moment (prelúdio, louvor, etc.)")
@click.option("--position", type=int, help="Position to replace (1-indexed)")
@click.option("--positions", help="Multiple positions (comma-separated)")
@click.option("--with", "replacement", shell_complete=complete_song_names, help="Manual song selection")
@click.option("--date", shell_complete=complete_history_dates, help="Target date (default: latest)")
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
    from cli.commands.replace import run
    run(moment, position, positions, replacement, date, output_dir, history_dir)


@cli.command()
@click.option("--date", shell_complete=complete_history_dates, help="Target date (default: latest)")
@click.option("--output-dir", help="Custom output directory")
@click.option("--history-dir", help="Custom history directory")
def pdf(date, output_dir, history_dir):
    """Generate PDF from existing setlist.

    \b
    Examples:
      songbook pdf
      songbook pdf --date 2026-02-15
    """
    from cli.commands.pdf import run
    run(date, output_dir, history_dir)


@cli.command()
@click.option("--history-dir", help="Custom history directory")
def cleanup(history_dir):
    """Run data quality checks on history files.

    \b
    Analyzes all history files for inconsistencies with database.csv:
    - Automatically fixes capitalization mismatches
    - Identifies songs in history that don't exist in database.csv
    - Provides fuzzy matching suggestions for similar song names
    - Creates timestamped backups before making changes
    """
    from cli.commands.maintenance import run_cleanup
    run_cleanup(history_dir)


@cli.command("fix-punctuation")
@click.option("--history-dir", help="Custom history directory")
def fix_punctuation(history_dir):
    """Normalize punctuation in history files.

    \b
    Fixes punctuation differences in history files to match canonical
    song names from database.csv (e.g., commas, hyphens).
    """
    from cli.commands.maintenance import run_fix_punctuation
    run_fix_punctuation(history_dir)


@cli.command("import-history")
def import_history():
    """Import external setlist data.

    \b
    Imports setlist data from external sources and converts it to
    the internal history format. Requires editing the script first
    to add your data.
    """
    from cli.commands.maintenance import run_import
    run_import()


@cli.command("install-completion")
@click.option("--shell", type=click.Choice(['bash', 'zsh', 'fish']),
              help="Shell type (auto-detected if not specified)")
def install_completion(shell):
    """Install shell completion for songbook.

    \b
    Enables tab completion for commands, song names, moments, and dates.
    The shell type is auto-detected if not specified.

    \b
    Examples:
      songbook install-completion           # Auto-detect shell
      songbook install-completion --shell bash
      songbook install-completion --shell zsh
      songbook install-completion --shell fish

    \b
    After installation, restart your shell or run:
      source ~/.bashrc   (bash)
      source ~/.zshrc    (zsh)
      fish: completions auto-load, just restart
    """
    import os
    import subprocess
    from pathlib import Path

    # Auto-detect shell if not specified
    if not shell:
        shell_path = os.environ.get('SHELL', '')
        if 'bash' in shell_path:
            shell = 'bash'
        elif 'zsh' in shell_path:
            shell = 'zsh'
        elif 'fish' in shell_path:
            shell = 'fish'
        else:
            click.secho("Could not detect shell. Please specify with --shell", fg="red", err=True)
            click.echo("Example: songbook install-completion --shell bash")
            raise SystemExit(1)

    click.echo(f"Installing completion for {shell}...")

    # Generate completion script
    env = os.environ.copy()
    if shell == 'bash':
        env['_SONGBOOK_COMPLETE'] = 'bash_source'
    elif shell == 'zsh':
        env['_SONGBOOK_COMPLETE'] = 'zsh_source'
    elif shell == 'fish':
        env['_SONGBOOK_COMPLETE'] = 'fish_source'

    try:
        result = subprocess.run(
            ['songbook'],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        completion_script = result.stdout

        # Install based on shell type
        if shell == 'bash':
            # Save to ~/.songbook-complete.bash
            completion_path = Path.home() / '.songbook-complete.bash'
            completion_path.write_text(completion_script)
            click.secho(f"✓ Completion script saved to {completion_path}", fg="green")

            # Add source line to ~/.bashrc if not present
            bashrc_path = Path.home() / '.bashrc'
            source_line = f'source {completion_path}\n'

            if bashrc_path.exists():
                bashrc_content = bashrc_path.read_text()
                if str(completion_path) not in bashrc_content:
                    with bashrc_path.open('a') as f:
                        f.write(f'\n# Songbook completion\n{source_line}')
                    click.secho(f"✓ Added source line to {bashrc_path}", fg="green")
                else:
                    click.secho(f"✓ Source line already in {bashrc_path}", fg="yellow")
            else:
                click.secho(f"⚠ {bashrc_path} not found. Add this line manually:", fg="yellow")
                click.echo(f"  {source_line}")

            click.echo()
            click.secho("To activate completion, run:", fg="cyan")
            click.echo(f"  source ~/.bashrc")

        elif shell == 'zsh':
            # Save to ~/.songbook-complete.zsh
            completion_path = Path.home() / '.songbook-complete.zsh'
            completion_path.write_text(completion_script)
            click.secho(f"✓ Completion script saved to {completion_path}", fg="green")

            # Add source line to ~/.zshrc if not present
            zshrc_path = Path.home() / '.zshrc'
            source_line = f'source {completion_path}\n'

            if zshrc_path.exists():
                zshrc_content = zshrc_path.read_text()
                if str(completion_path) not in zshrc_content:
                    with zshrc_path.open('a') as f:
                        f.write(f'\n# Songbook completion\n{source_line}')
                    click.secho(f"✓ Added source line to {zshrc_path}", fg="green")
                else:
                    click.secho(f"✓ Source line already in {zshrc_path}", fg="yellow")
            else:
                click.secho(f"⚠ {zshrc_path} not found. Add this line manually:", fg="yellow")
                click.echo(f"  {source_line}")

            click.echo()
            click.secho("To activate completion, run:", fg="cyan")
            click.echo(f"  source ~/.zshrc")

        elif shell == 'fish':
            # Save to ~/.config/fish/completions/songbook.fish
            fish_dir = Path.home() / '.config' / 'fish' / 'completions'
            fish_dir.mkdir(parents=True, exist_ok=True)
            completion_path = fish_dir / 'songbook.fish'
            completion_path.write_text(completion_script)
            click.secho(f"✓ Completion script saved to {completion_path}", fg="green")

            click.echo()
            click.secho("Fish automatically loads completions. Just restart your shell:", fg="cyan")
            click.echo("  exec fish")

        click.echo()
        click.secho("✓ Installation complete!", fg="green", bold=True)
        click.echo()
        click.echo("For detailed documentation, see:")
        click.echo("  .claude/SHELL_COMPLETION.md")

    except subprocess.CalledProcessError as e:
        click.secho(f"Error generating completion script: {e.stderr}", fg="red", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.secho(f"Installation failed: {e}", fg="red", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
