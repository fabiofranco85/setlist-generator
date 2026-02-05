"""Output formatting for setlists.

The ``format_setlist_markdown()`` function is NOT deprecated and remains the
standard way to generate markdown content.

.. deprecated::
    The ``save_setlist_history()`` function is deprecated. Use repositories instead:

    >>> from library import get_repositories
    >>> repos = get_repositories()
    >>> repos.history.save(setlist)
"""

import json
import warnings
from pathlib import Path

from .models import Song, Setlist


def format_setlist_markdown(
    setlist: Setlist,
    songs: dict[str, Song]
) -> str:
    """Format setlist as markdown with chords."""
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


def save_setlist_history(
    setlist: Setlist,
    setlists_path: Path
) -> None:
    """
    Save setlist to history as JSON.

    .. deprecated::
        Use ``get_repositories().history.save(setlist)`` instead:

        >>> from library import get_repositories
        >>> repos = get_repositories(history_dir=setlists_path)
        >>> repos.history.save(setlist)

    Args:
        setlist: The setlist to save
        setlists_path: Path to history directory (e.g., Path("./history"))
    """
    warnings.warn(
        "save_setlist_history() is deprecated. Use get_repositories().history.save() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    setlists_path.mkdir(exist_ok=True)

    history_file = setlists_path / f"{setlist.date}.json"
    data = setlist.to_dict()

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
