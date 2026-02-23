"""PostgreSQL implementation of SongRepository.

Songs and their tags are loaded in bulk (two queries) and cached in memory,
mirroring the filesystem backend's approach. The cache is invalidated on
writes (update_content).
"""

from ...models import Song
from ...config import DEFAULT_ENERGY


class PostgresSongRepository:
    """Song repository backed by PostgreSQL.

    Storage:
    - ``songs`` table: title, energy, content, youtube_url
    - ``song_tags`` table: song_title, moment, weight (normalized)

    The entire catalogue is loaded once and cached. Reads operate on
    the in-memory cache; writes go to the database and invalidate the cache.
    """

    def __init__(self, pool):
        """Initialize with a psycopg connection pool.

        Args:
            pool: A psycopg_pool.ConnectionPool instance.
        """
        self._pool = pool
        self._songs_cache: dict[str, Song] | None = None

    def _load_all(self) -> dict[str, Song]:
        """Load all songs from the database (two queries, joined in Python).

        Returns:
            Dictionary mapping song titles to Song objects.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                # Load songs
                cur.execute(
                    "SELECT title, energy, content, youtube_url, event_types FROM songs ORDER BY title"
                )
                songs_rows = cur.fetchall()

                # Load tags
                cur.execute(
                    "SELECT song_title, moment, weight FROM song_tags ORDER BY song_title"
                )
                tags_rows = cur.fetchall()

        # Build tags lookup: {title: {moment: weight}}
        tags_by_title: dict[str, dict[str, int]] = {}
        for song_title, moment, weight in tags_rows:
            tags_by_title.setdefault(song_title, {})[moment] = weight

        # Build Song objects
        songs: dict[str, Song] = {}
        for title, energy, content, youtube_url, event_types_arr in songs_rows:
            songs[title] = Song(
                title=title,
                tags=tags_by_title.get(title, {}),
                energy=energy if energy is not None else DEFAULT_ENERGY,
                content=content or "",
                youtube_url=youtube_url or "",
                event_types=list(event_types_arr) if event_types_arr else [],
            )

        return songs

    def _ensure_loaded(self) -> dict[str, Song]:
        """Ensure songs are loaded, using cache if available."""
        if self._songs_cache is None:
            self._songs_cache = self._load_all()
        return self._songs_cache

    def get_all(self) -> dict[str, Song]:
        """Get all songs indexed by title."""
        return self._ensure_loaded().copy()

    def get_by_title(self, title: str) -> Song | None:
        """Get a single song by exact title match."""
        return self._ensure_loaded().get(title)

    def search(self, query: str) -> list[Song]:
        """Search songs by title (case-insensitive partial match)."""
        query_lower = query.lower()
        return [
            song
            for song in self._ensure_loaded().values()
            if query_lower in song.title.lower()
        ]

    def update_content(self, title: str, content: str) -> None:
        """Update a song's chord content.

        Args:
            title: Song title to update.
            content: New chord content (markdown).

        Raises:
            KeyError: If song with title doesn't exist.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE songs SET content = %s WHERE title = %s",
                    (content, title),
                )
                if cur.rowcount == 0:
                    raise KeyError(f"Song '{title}' not found in database")
                conn.commit()

        # Invalidate cache so next read picks up the change
        self._songs_cache = None

    def exists(self, title: str) -> bool:
        """Check if a song exists."""
        return title in self._ensure_loaded()

    def invalidate_cache(self) -> None:
        """Clear the internal cache, forcing a reload on next access."""
        self._songs_cache = None
