"""PostgreSQL implementation of EventTypeRepository.

Event types are cached in memory after first load, invalidated on writes.
"""

import json

from ...event_type import EventType, DEFAULT_EVENT_TYPE_SLUG


class PostgresEventTypeRepository:
    """Event type repository backed by PostgreSQL.

    Storage:
    - ``event_types`` table: slug, name, description, moments (JSONB)

    Cached after first load; invalidated on any write operation.
    """

    def __init__(self, pool):
        """Initialize with a psycopg connection pool.

        Args:
            pool: A psycopg_pool.ConnectionPool instance.
        """
        self._pool = pool
        self._cache: dict[str, EventType] | None = None

    def _load_all(self) -> dict[str, EventType]:
        """Load all event types from the database."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT slug, name, description, moments FROM event_types ORDER BY slug"
                )
                rows = cur.fetchall()

        result: dict[str, EventType] = {}
        for slug, name, description, moments in rows:
            result[slug] = EventType(
                slug=slug,
                name=name,
                description=description or "",
                moments=moments if isinstance(moments, dict) else {},
            )
        return result

    def _ensure_loaded(self) -> dict[str, EventType]:
        """Ensure event types are loaded, using cache if available."""
        if self._cache is None:
            self._cache = self._load_all()
        return self._cache

    def get_all(self) -> dict[str, EventType]:
        """Get all event types indexed by slug."""
        return dict(self._ensure_loaded())

    def get(self, slug: str) -> EventType | None:
        """Get a single event type by slug."""
        return self._ensure_loaded().get(slug)

    def get_default_slug(self) -> str:
        """Get the default event type slug."""
        return DEFAULT_EVENT_TYPE_SLUG

    def add(self, event_type: EventType) -> None:
        """Add a new event type.

        Raises:
            ValueError: If slug already exists.
        """
        if self._ensure_loaded().get(event_type.slug):
            raise ValueError(f"Event type '{event_type.slug}' already exists")

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO event_types (slug, name, description, moments) "
                    "VALUES (%s, %s, %s, %s::jsonb)",
                    (event_type.slug, event_type.name, event_type.description,
                     json.dumps(event_type.moments)),
                )
                conn.commit()

        self._cache = None

    def update(self, slug: str, **kwargs) -> None:
        """Update an existing event type.

        Args:
            slug: Event type slug to update.
            **kwargs: Fields to update (name, description, moments).

        Raises:
            KeyError: If event type doesn't exist.
        """
        if not self._ensure_loaded().get(slug):
            raise KeyError(f"Event type '{slug}' not found")

        set_clauses = []
        params = []
        for key, value in kwargs.items():
            if key == "moments":
                set_clauses.append("moments = %s::jsonb")
                params.append(json.dumps(value))
            elif key in ("name", "description"):
                set_clauses.append(f"{key} = %s")
                params.append(value)

        if not set_clauses:
            return

        params.append(slug)
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE event_types SET {', '.join(set_clauses)} WHERE slug = %s",
                    params,
                )
                conn.commit()

        self._cache = None

    def remove(self, slug: str) -> None:
        """Remove an event type.

        Args:
            slug: Event type slug to remove.

        Raises:
            KeyError: If event type doesn't exist.
            ValueError: If trying to remove the default event type.
        """
        if slug == DEFAULT_EVENT_TYPE_SLUG:
            raise ValueError("Cannot remove the default event type")

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM event_types WHERE slug = %s",
                    (slug,),
                )
                if cur.rowcount == 0:
                    raise KeyError(f"Event type '{slug}' not found")
                conn.commit()

        self._cache = None
