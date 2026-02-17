"""PostgreSQL implementation of HistoryRepository.

Unlike the song repository, history is NOT cached — it changes frequently
and the queries are indexed. Each method executes SQL directly.
"""

from ...models import Setlist


class PostgresHistoryRepository:
    """History repository backed by PostgreSQL.

    Storage:
    - ``setlists`` table: date, label, moments (JSONB)
    - Unique constraint on (date, label)

    All methods query the database directly (no caching).
    """

    def __init__(self, pool):
        """Initialize with a psycopg connection pool.

        Args:
            pool: A psycopg_pool.ConnectionPool instance.
        """
        self._pool = pool

    @staticmethod
    def _row_to_dict(date, label, moments) -> dict:
        """Convert a database row to the standard setlist dict format.

        Args:
            date: datetime.date from the database.
            label: Label string (may be empty).
            moments: JSONB dict of moments.

        Returns:
            Setlist dictionary matching the filesystem format.
        """
        result = {
            "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
            "moments": moments,
        }
        if label:
            result["label"] = label
        return result

    def get_all(self) -> list[dict]:
        """Get all historical setlists sorted by date (most recent first)."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, label, moments FROM setlists "
                    "ORDER BY date DESC, label ASC"
                )
                rows = cur.fetchall()

        return [self._row_to_dict(date, label, moments) for date, label, moments in rows]

    def get_by_date(self, date: str, label: str = "") -> dict | None:
        """Get a setlist by date and optional label."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, label, moments FROM setlists "
                    "WHERE date = %s AND label = %s",
                    (date, label),
                )
                row = cur.fetchone()

        if row is None:
            return None
        return self._row_to_dict(*row)

    def get_by_date_all(self, date: str) -> list[dict]:
        """Get all setlists for a date (all labels)."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, label, moments FROM setlists "
                    "WHERE date = %s ORDER BY label ASC",
                    (date,),
                )
                rows = cur.fetchall()

        return [self._row_to_dict(date, label, moments) for date, label, moments in rows]

    def get_latest(self) -> dict | None:
        """Get the most recent setlist."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, label, moments FROM setlists "
                    "ORDER BY date DESC, label ASC LIMIT 1"
                )
                row = cur.fetchone()

        if row is None:
            return None
        return self._row_to_dict(*row)

    def save(self, setlist: Setlist) -> None:
        """Save a new setlist to history (upsert)."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO setlists (date, label, moments) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (date, label) DO UPDATE SET moments = EXCLUDED.moments",
                    (setlist.date, setlist.label, setlist.to_dict()["moments"]),
                )
                conn.commit()

    def update(self, date: str, setlist_dict: dict, label: str = "") -> None:
        """Update an existing setlist in history.

        Raises:
            KeyError: If no setlist exists for the given date/label.
        """
        moments = setlist_dict.get("moments", {})
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE setlists SET moments = %s WHERE date = %s AND label = %s",
                    (moments, date, label),
                )
                if cur.rowcount == 0:
                    setlist_id = f"{date}_{label}" if label else date
                    raise KeyError(f"No setlist found for: {setlist_id}")
                conn.commit()

    def exists(self, date: str, label: str = "") -> bool:
        """Check if a setlist exists for a date and optional label."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM setlists WHERE date = %s AND label = %s",
                    (date, label),
                )
                return cur.fetchone() is not None

    def delete(self, date: str, label: str = "") -> None:
        """Delete a setlist by date and optional label.

        Raises:
            KeyError: If no setlist exists for the given date/label.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM setlists WHERE date = %s AND label = %s",
                    (date, label),
                )
                if cur.rowcount == 0:
                    setlist_id = f"{date}_{label}" if label else date
                    raise KeyError(f"No setlist found for: {setlist_id}")
                conn.commit()
