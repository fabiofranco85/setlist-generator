"""Supabase config repository with system -> org cascade."""

from __future__ import annotations

from typing import Any

from ...config import (
    DEFAULT_ENERGY,
    DEFAULT_WEIGHT,
    ENERGY_ORDERING_ENABLED,
    ENERGY_ORDERING_RULES,
    MOMENTS_CONFIG,
    RECENCY_DECAY_DAYS,
)


class SupabaseConfigRepository:
    """Config repository with cascading: org_config -> system_config -> Python constants.

    Reads configuration values with fallback chain:
    1. org_config (per-org overrides)
    2. system_config (system-wide defaults in DB)
    3. Python constants from library/config.py
    """

    def __init__(self, client: Any, org_id: str):
        self._client = client
        self._org_id = org_id
        self._cache: dict[str, Any] | None = None

    def _load_cache(self) -> dict[str, Any]:
        if self._cache is not None:
            return self._cache

        # Load system config
        sys_response = self._client.table("system_config").select("key, value").execute()
        system_vals = {row["key"]: row["value"] for row in sys_response.data}

        # Load org config (overrides)
        org_vals: dict[str, Any] = {}
        if self._org_id:
            org_response = (
                self._client.table("org_config")
                .select("key, value")
                .eq("org_id", self._org_id)
                .execute()
            )
            org_vals = {row["key"]: row["value"] for row in org_response.data}

        # Merge: org overrides system
        merged = {**system_vals, **org_vals}
        self._cache = merged
        return merged

    def _get_value(self, key: str, fallback: Any) -> Any:
        """Get a config value with cascade fallback."""
        cache = self._load_cache()
        return cache.get(key, fallback)

    def get_moments_config(self) -> dict[str, int]:
        return self._get_value("moments_config", dict(MOMENTS_CONFIG))

    def get_recency_decay_days(self) -> int:
        return int(self._get_value("recency_decay_days", RECENCY_DECAY_DAYS))

    def get_default_weight(self) -> int:
        return int(self._get_value("default_weight", DEFAULT_WEIGHT))

    def get_energy_ordering_rules(self) -> dict[str, str]:
        return self._get_value("energy_ordering_rules", dict(ENERGY_ORDERING_RULES))

    def is_energy_ordering_enabled(self) -> bool:
        return bool(self._get_value("energy_ordering_enabled", ENERGY_ORDERING_ENABLED))

    def get_default_energy(self) -> float:
        return float(self._get_value("default_energy", DEFAULT_ENERGY))
