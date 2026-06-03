"""Filesystem implementation of SongRepository.

This module provides song data access using the traditional file-based storage:
- Song metadata: database.csv (semicolon-delimited)
- Chord content: chords/<Song Title>.md (markdown files)
"""

import csv
from pathlib import Path

from ...config import DEFAULT_WEIGHT, DEFAULT_ENERGY
from ...models import Song
from ...loader import parse_tags


def serialize_tags(tags: dict[str, int], default_weight: int = DEFAULT_WEIGHT) -> str:
    """Render a tag dict back to the comma-separated CSV form.

    Weights equal to ``default_weight`` are written bare (``"louvor"``); other
    weights are written with parentheses (``"louvor(5)"``). This is the inverse
    of :func:`library.loader.parse_tags` and produces minimal diffs when the
    weight matches the default.
    """
    parts: list[str] = []
    for moment, weight in tags.items():
        if weight == default_weight:
            parts.append(moment)
        else:
            parts.append(f"{moment}({weight})")
    return ",".join(parts)


class FilesystemSongRepository:
    """Song repository backed by filesystem storage.

    Storage format:
    - database.csv: "song;energy;tags;youtube" header
    - chords/*.md: Individual chord files named by song title

    Attributes:
        base_path: Project root directory containing database.csv and chords/
    """

    def __init__(self, base_path: Path):
        """Initialize repository with base path.

        Args:
            base_path: Project root directory
        """
        self.base_path = base_path
        self._database_file = base_path / "database.csv"
        self._chords_path = base_path / "chords"
        self._songs_cache: dict[str, Song] | None = None

    def _load_songs(self) -> dict[str, Song]:
        """Load songs from database.csv and chords/*.md files.

        Returns:
            Dictionary mapping song titles to Song objects

        Raises:
            FileNotFoundError: If database.csv doesn't exist
        """
        songs = {}

        if not self._database_file.exists():
            raise FileNotFoundError(
                f"Song database not found: {self._database_file}. "
                "Ensure database.csv exists in the project root."
            )

        with open(self._database_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                title = row["song"]

                # Parse energy (default if missing or invalid)
                energy_str = row.get("energy", "").strip()
                try:
                    energy = float(energy_str) if energy_str else DEFAULT_ENERGY
                except ValueError:
                    energy = DEFAULT_ENERGY

                # Parse tags
                tags = parse_tags(row["tags"])

                # Load song content from chords folder
                song_file = self._chords_path / f"{title}.md"
                content = ""
                if song_file.exists():
                    with open(song_file, "r", encoding="utf-8") as sf:
                        content = sf.read()

                # Parse YouTube URL (optional column)
                youtube_url = (row.get("youtube") or "").strip()

                # Parse event types (optional column)
                event_types_str = (row.get("event_types") or "").strip()
                event_types = [
                    et.strip() for et in event_types_str.split(",") if et.strip()
                ] if event_types_str else []

                songs[title] = Song(
                    title=title,
                    tags=tags,
                    energy=energy,
                    content=content,
                    youtube_url=youtube_url,
                    event_types=event_types,
                )

        return songs

    def _ensure_loaded(self) -> dict[str, Song]:
        """Ensure songs are loaded, using cache if available."""
        if self._songs_cache is None:
            self._songs_cache = self._load_songs()
        return self._songs_cache

    def get_all(self) -> dict[str, Song]:
        """Get all songs indexed by title.

        Returns:
            Dictionary mapping song titles to Song objects
        """
        return self._ensure_loaded().copy()

    def get_by_title(self, title: str) -> Song | None:
        """Get a single song by exact title match.

        Args:
            title: Song title to look up

        Returns:
            Song object if found, None otherwise
        """
        return self._ensure_loaded().get(title)

    def search(self, query: str) -> list[Song]:
        """Search songs by title (case-insensitive partial match).

        Args:
            query: Search string to match against titles

        Returns:
            List of matching Song objects
        """
        query_lower = query.lower()
        return [
            song
            for song in self._ensure_loaded().values()
            if query_lower in song.title.lower()
        ]

    def update_content(self, title: str, content: str) -> None:
        """Update a song's chord content.

        Args:
            title: Song title to update
            content: New chord content (markdown)

        Raises:
            KeyError: If song with title doesn't exist
        """
        songs = self._ensure_loaded()
        if title not in songs:
            raise KeyError(f"Song '{title}' not found in database")

        # Update chord file
        song_file = self._chords_path / f"{title}.md"
        song_file.write_text(content, encoding="utf-8")

        # Update cache
        songs[title] = Song(
            title=title,
            tags=songs[title].tags,
            energy=songs[title].energy,
            content=content,
            youtube_url=songs[title].youtube_url,
        )

    def update_tags(self, title: str, tags: dict[str, int]) -> None:
        """Rewrite a song's tag row in ``database.csv``.

        Reads the CSV row-by-row, replaces the ``tags`` column for the target
        song, and writes the file back preserving the original column order
        (including the optional ``youtube`` and ``event_types`` columns).

        Args:
            title: Song title to update.
            tags: New ``{moment: weight}`` mapping. Empty dict clears all tags.

        Raises:
            KeyError: If song with ``title`` doesn't exist.
            ValueError: If any weight is not a positive integer.
        """
        for moment, weight in tags.items():
            if not isinstance(weight, int) or weight < 1:
                raise ValueError(
                    f"Invalid weight for '{moment}': {weight!r}. "
                    "Weights must be positive integers."
                )

        if not self._database_file.exists():
            raise FileNotFoundError(
                f"Song database not found: {self._database_file}"
            )

        with open(self._database_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            fieldnames = reader.fieldnames or []
            rows = list(reader)

        found = False
        new_tags_str = serialize_tags(tags)
        for row in rows:
            if row.get("song") == title:
                row["tags"] = new_tags_str
                found = True
                break

        if not found:
            raise KeyError(f"Song '{title}' not found in database")

        with open(self._database_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

        # Invalidate cache so subsequent reads pick up the new tags
        self._songs_cache = None

    def update_youtube(self, title: str, youtube_url: str) -> None:
        """Rewrite a song's ``youtube`` column in ``database.csv``.

        Reads the CSV row-by-row, replaces the ``youtube`` column for the
        target song, and writes the file back preserving the original column
        order. The value is stored verbatim (pass ``""`` to clear the link).

        Args:
            title: Song title to update.
            youtube_url: YouTube URL, or "" to clear the link.

        Raises:
            KeyError: If song with ``title`` doesn't exist.
        """
        if not self._database_file.exists():
            raise FileNotFoundError(
                f"Song database not found: {self._database_file}"
            )

        with open(self._database_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        # Ensure the optional 'youtube' column exists so DictWriter accepts it.
        if "youtube" not in fieldnames:
            fieldnames.append("youtube")

        found = False
        for row in rows:
            if row.get("song") == title:
                row["youtube"] = youtube_url
                found = True
                break

        if not found:
            raise KeyError(f"Song '{title}' not found in database")

        with open(self._database_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

        # Invalidate cache so subsequent reads pick up the new URL
        self._songs_cache = None

    def exists(self, title: str) -> bool:
        """Check if a song exists.

        Args:
            title: Song title to check

        Returns:
            True if song exists, False otherwise
        """
        return title in self._ensure_loaded()

    def invalidate_cache(self) -> None:
        """Clear the internal cache, forcing a reload on next access.

        Use this if files have been modified externally.
        """
        self._songs_cache = None
