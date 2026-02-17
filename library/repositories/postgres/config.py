"""PostgreSQL implementation of ConfigRepository.

Configuration is loaded once and cached. Falls back to Python constants
from library/config.py if a key is missing in the database.
"""

from typing import Any

from ...config import (
    MOMENTS_CONFIG,
    RECENCY_DECAY_DAYS,
    DEFAULT_WEIGHT,
    ENERGY_ORDERING_RULES,
    ENERGY_ORDERING_ENABLED,
    DEFAULT_ENERGY,
)


class PostgresConfigRepository:
    """Config repository backed by PostgreSQL.

    Storage:
    - ``config`` table: key (TEXT PK), value (JSONB)

    Values are cached after first load. Falls back to Python constants
    for any key not present in the database.
    """

    def __init__(self, pool):
        """Initialize with a psycopg connection pool.

        Args:
            pool: A psycopg_pool.ConnectionPool instance.
        """
        self._pool = pool
        self._cache: dict[str, Any] | None = None

    def _load_all(self) -> dict[str, Any]:
        """Load all config key-value pairs from the database.

        Returns:
            Dictionary mapping config keys to their JSONB values.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT key, value FROM config")
                rows = cur.fetchall()

        return {key: value for key, value in rows}

    def _ensure_loaded(self) -> dict[str, Any]:
        """Ensure config is loaded, using cache if available."""
        if self._cache is None:
            self._cache = self._load_all()
        return self._cache

    def _get(self, key: str, fallback):
        """Get a config value by key, falling back to a Python constant.

        Args:
            key: Config key to look up.
            fallback: Value to return if key is not in the database.

        Returns:
            The config value (JSONB auto-deserialized by psycopg).
        """
        config = self._ensure_loaded()
        return config.get(key, fallback)

    def get_moments_config(self) -> dict[str, int]:
        """Get service moments configuration."""
        return dict(self._get("moments_config", MOMENTS_CONFIG))

    def get_recency_decay_days(self) -> int:
        """Get recency decay constant in days."""
        return int(self._get("recency_decay_days", RECENCY_DECAY_DAYS))

    def get_default_weight(self) -> int:
        """Get default tag weight."""
        return int(self._get("default_weight", DEFAULT_WEIGHT))

    def get_energy_ordering_rules(self) -> dict[str, str]:
        """Get energy ordering rules per moment."""
        return dict(self._get("energy_ordering_rules", ENERGY_ORDERING_RULES))

    def is_energy_ordering_enabled(self) -> bool:
        """Check if energy ordering is enabled."""
        return bool(self._get("energy_ordering_enabled", ENERGY_ORDERING_ENABLED))

    def get_default_energy(self) -> float:
        """Get default energy for songs without energy metadata."""
        return float(self._get("default_energy", DEFAULT_ENERGY))

    def invalidate_cache(self) -> None:
        """Clear the internal cache, forcing a reload on next access."""
        self._cache = None
