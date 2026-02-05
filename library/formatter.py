"""Output formatting for setlists.

This module provides functions for formatting setlists as markdown.

For saving setlists to history, use the repository pattern:

    >>> from library import get_repositories
    >>> repos = get_repositories()
    >>> repos.history.save(setlist)
"""

from .models import Song, Setlist


def format_setlist_markdown(
    setlist: Setlist,
    songs: dict[str, Song]
) -> str:
    """Format setlist as markdown with chords.

    Args:
        setlist: Setlist object with date and moments
        songs: Dictionary mapping song titles to Song objects

    Returns:
        Markdown string with full chord content for each song
    """
    lines = [f"# Setlist - {setlist.date}", ""]

    for moment, song_list in setlist.moments.items():
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
