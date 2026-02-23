"""PostgreSQL implementation of HistoryRepository.

Unlike the song repository, history is NOT cached — it changes frequently
and the queries are indexed. Each method executes SQL directly.
"""

import json

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
    def _row_to_dict(date, label, moments, event_type="") -> dict:
        """Convert a database row to the standard setlist dict format.

        Args:
            date: datetime.date from the database.
            label: Label string (may be empty).
            moments: JSONB dict of moments.
            event_type: Event type slug (may be empty).

        Returns:
            Setlist dictionary matching the filesystem format.
        """
        result = {
            "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
            "moments": moments,
        }
        if label:
            result["label"] = label
        if event_type:
            result["event_type"] = event_type
        return result

    def get_all(self) -> list[dict]:
        """Get all historical setlists sorted by date (most recent first)."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, label, moments, event_type FROM setlists "
                    "ORDER BY date DESC, event_type ASC, label ASC"
                )
                rows = cur.fetchall()

        return [self._row_to_dict(date, label, moments, event_type)
                for date, label, moments, event_type in rows]

    def get_by_date(self, date: str, label: str = "", event_type: str = "") -> dict | None:
        """Get a setlist by date, optional label, and optional event type."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, label, moments, event_type FROM setlists "
                    "WHERE date = %s AND label = %s AND event_type = %s",
                    (date, label, event_type),
                )
                row = cur.fetchone()

        if row is None:
            return None
        return self._row_to_dict(*row)

    def get_by_date_all(self, date: str, event_type: str = "") -> list[dict]:
        """Get all setlists for a date (all labels), optionally filtered by event type."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                if event_type:
                    cur.execute(
                        "SELECT date, label, moments, event_type FROM setlists "
                        "WHERE date = %s AND event_type = %s ORDER BY label ASC",
                        (date, event_type),
                    )
                else:
                    cur.execute(
                        "SELECT date, label, moments, event_type FROM setlists "
                        "WHERE date = %s ORDER BY event_type ASC, label ASC",
                        (date,),
                    )
                rows = cur.fetchall()

        return [self._row_to_dict(date, label, moments, et)
                for date, label, moments, et in rows]

    def get_latest(self) -> dict | None:
        """Get the most recent setlist."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, label, moments, event_type FROM setlists "
                    "ORDER BY date DESC, event_type ASC, label ASC LIMIT 1"
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
                    "INSERT INTO setlists (date, event_type, label, moments) "
                    "VALUES (%s, %s, %s, %s::jsonb) "
                    "ON CONFLICT (date, event_type, label) DO UPDATE SET moments = EXCLUDED.moments",
                    (setlist.date, setlist.event_type, setlist.label, json.dumps(setlist.moments)),
                )
                conn.commit()

    def update(self, date: str, setlist_dict: dict, label: str = "", event_type: str = "") -> None:
        """Update an existing setlist in history.

        Raises:
            KeyError: If no setlist exists for the given date/label/event_type.
        """
        moments = setlist_dict.get("moments", {})
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE setlists SET moments = %s::jsonb "
                    "WHERE date = %s AND label = %s AND event_type = %s",
                    (json.dumps(moments), date, label, event_type),
                )
                if cur.rowcount == 0:
                    setlist_id = f"{date}_{label}" if label else date
                    raise KeyError(f"No setlist found for: {setlist_id}")
                conn.commit()

    def exists(self, date: str, label: str = "", event_type: str = "") -> bool:
        """Check if a setlist exists for a date, label, and event type."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM setlists WHERE date = %s AND label = %s AND event_type = %s",
                    (date, label, event_type),
                )
                return cur.fetchone() is not None

    def delete(self, date: str, label: str = "", event_type: str = "") -> None:
        """Delete a setlist by date, label, and event type.

        Raises:
            KeyError: If no setlist exists for the given date/label/event_type.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM setlists WHERE date = %s AND label = %s AND event_type = %s",
                    (date, label, event_type),
                )
                if cur.rowcount == 0:
                    setlist_id = f"{date}_{label}" if label else date
                    raise KeyError(f"No setlist found for: {setlist_id}")
                conn.commit()
