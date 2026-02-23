"""Output formatting for setlists.

This module provides functions for formatting setlists as markdown.

For saving setlists to history, use the repository pattern:

    >>> from library import get_repositories
    >>> repos = get_repositories()
    >>> repos.history.save(setlist)
"""

from .config import canonical_moment_order
from .models import Song, Setlist


def format_setlist_markdown(
    setlist: Setlist,
    songs: dict[str, Song],
    event_type_name: str = "",
) -> str:
    """Format setlist as markdown with chords.

    Args:
        setlist: Setlist object with date and moments
        songs: Dictionary mapping song titles to Song objects
        event_type_name: Optional event type display name (omitted if empty or default)

    Returns:
        Markdown string with full chord content for each song
    """
    header = f"# Setlist - {setlist.date}"
    if event_type_name:
        header += f" | {event_type_name}"
    if setlist.label:
        header += f" ({setlist.label})"
    lines = [header, ""]

    for moment in canonical_moment_order(setlist.moments):
        song_list = setlist.moments[moment]
        lines.append(f"## {moment.capitalize()}")
        lines.append("")

        for song_title in song_list:
            song = songs.get(song_title)
            if song and song.content:
                lines.append(song.content)
            else:
                lines.append(f"### {song_title}")
                lines.append("")
                lines.append("*(Content not found)*")
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("")

    return "\n".join(lines)
