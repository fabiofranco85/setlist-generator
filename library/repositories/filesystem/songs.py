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

                songs[title] = Song(
                    title=title,
                    tags=tags,
                    energy=energy,
                    content=content,
                    youtube_url=youtube_url,
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
