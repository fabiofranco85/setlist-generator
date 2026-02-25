"""Interactive song picker for CLI commands.

Provides a searchable, navigable song selection menu using simple-term-menu.
Falls back to a numbered list when the terminal is non-interactive or the
dependency is missing.
"""

import sys

import click

from library.models import Song


ENERGY_LABELS = {1: "high", 2: "mid+", 3: "mid-", 4: "low"}


def extract_key(content: str) -> str:
    """Extract musical key from chord file header.

    Looks for the ``### Title (Key)`` pattern on the first line.

    Args:
        content: Full chord file content (markdown).

    Returns:
        The key string (e.g. ``"Bm"``, ``"G"``), or ``""`` if not found.
    """
    if not content:
        return ""
    first_line = content.split("\n")[0].strip()
    if "(" in first_line and ")" in first_line:
        start = first_line.rfind("(")
        end = first_line.rfind(")")
        if start != -1 and end != -1 and end > start:
            return first_line[start + 1 : end].strip()
    return ""


def format_song_entry(title: str, song: Song) -> str:
    """Format a single song line for the picker menu.

    Example output::

        Oceanos (Bm)  [3 mid-]  louvor(2)

    Args:
        title: Song title (canonical name).
        song: Song object with metadata.

    Returns:
        Formatted string for display.
    """
    key = extract_key(song.content)
    parts = [title]

    if key:
        parts[0] = f"{title} ({key})"

    if song.energy is not None:
        label = ENERGY_LABELS.get(int(song.energy), "?")
        parts.append(f"[{int(song.energy)} {label}]")

    if song.tags:
        tags_strs = []
        for moment, weight in song.tags.items():
            if weight == 3:
                tags_strs.append(moment)
            else:
                tags_strs.append(f"{moment}({weight})")
        parts.append(", ".join(tags_strs))

    return "  ".join(parts)


def _is_interactive() -> bool:
    """Check whether stdin and stdout are connected to a terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _pick_with_menu(entries: list[str], titles: list[str], title: str) -> str | None:
    """Show interactive terminal menu. Returns selected title or None."""
    from simple_term_menu import TerminalMenu

    menu = TerminalMenu(
        entries,
        title=title,
        search_key="/",
        show_search_hint=True,
    )
    index = menu.show()
    if index is None:
        return None
    return titles[index]


def _pick_with_fallback(entries: list[str], titles: list[str], title: str) -> str | None:
    """Numbered list fallback for non-interactive terminals."""
    click.echo(f"\n{title}\n")
    for i, entry in enumerate(entries, 1):
        click.echo(f"  {i}. {entry}")
    click.echo()

    try:
        choice = click.prompt(
            "Select song number (0 to cancel)",
            type=int,
            default=0,
        )
    except (click.Abort, EOFError):
        return None

    if choice == 0 or choice < 0 or choice > len(titles):
        return None
    return titles[choice - 1]


def pick_song(
    songs: dict[str, Song],
    *,
    title: str = "Pick a song:",
    moment_filter: str | None = None,
    exclude: set[str] | None = None,
) -> str | None:
    """Show an interactive song picker and return the selected title.

    Args:
        songs: Dictionary of song name -> Song object.
        title: Header text for the picker.
        moment_filter: If set, only show songs tagged for this moment.
        exclude: Set of song titles to hide (e.g., songs already in setlist).

    Returns:
        The selected song title, or ``None`` if cancelled.
    """
    exclude = exclude or set()

    # Build filtered and sorted list
    filtered: list[tuple[str, Song]] = []
    for name, song in sorted(songs.items()):
        if name in exclude:
            continue
        if moment_filter and not song.has_moment(moment_filter):
            continue
        filtered.append((name, song))

    if not filtered:
        click.echo("No songs available for selection.")
        return None

    entries = [format_song_entry(name, song) for name, song in filtered]
    titles = [name for name, _ in filtered]

    # Try interactive menu, fall back to numbered list
    if _is_interactive():
        try:
            return _pick_with_menu(entries, titles, title)
        except ImportError:
            pass

    return _pick_with_fallback(entries, titles, title)
