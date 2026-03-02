"""Unit tests for PostgresEventTypeRepository moments_order handling (Problem 1).

Verifies that the PostgreSQL backend correctly stores and retrieves
moments_order alongside moments, preserving user-defined key order
even though JSONB alphabetizes keys.
"""

import json

from tests.unit.test_postgres_repositories import make_pool


class TestPostgresEventTypeLoadMomentsOrder:
    """Test _load_all() reads moments_order from rows."""

    def _import(self):
        from library.repositories.postgres.event_types import PostgresEventTypeRepository
        return PostgresEventTypeRepository

    def test_loads_moments_order_from_db(self):
        Repo = self._import()
        rows = [
            # slug, name, description, moments, moments_order
            ("custom", "Custom", "", {"final": 1, "louvor": 3}, ["louvor", "final"]),
        ]
        pool, _ = make_pool(results=[rows])
        repo = Repo(pool)

        all_types = repo.get_all()
        et = all_types["custom"]
        assert et.moments_order == ["louvor", "final"]
        assert list(et.ordered_moments.keys()) == ["louvor", "final"]

    def test_handles_null_moments_order(self):
        """When moments_order is NULL (e.g. old row), defaults from moments keys."""
        Repo = self._import()
        rows = [
            ("old", "Old Type", "", {"alpha": 1, "beta": 2}, None),
        ]
        pool, _ = make_pool(results=[rows])
        repo = Repo(pool)

        et = repo.get("old")
        # __post_init__ defaults from moments dict
        assert et.moments_order == ["alpha", "beta"]


class TestPostgresEventTypeAddMomentsOrder:
    """Test add() stores moments_order."""

    def _import(self):
        from library.repositories.postgres.event_types import PostgresEventTypeRepository
        return PostgresEventTypeRepository

    def test_add_stores_moments_order(self):
        Repo = self._import()
        from library.event_type import EventType

        # First call: _ensure_loaded() returns empty (no existing types)
        # Second call after add: not needed (cache invalidated)
        pool, cursor = make_pool(results=[[]])
        repo = Repo(pool)

        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 3, "final": 1},
            moments_order=["louvor", "final"],
        )
        repo.add(et)

        # Verify the INSERT included moments_order
        insert_query = cursor.queries[-1]
        assert "moments_order" in insert_query
        # The params should include the serialized moments_order
        insert_params = cursor.params[-1]
        assert json.loads(insert_params[4]) == ["louvor", "final"]


class TestPostgresEventTypeUpdateMomentsOrder:
    """Test update() auto-updates moments_order when moments change."""

    def _import(self):
        from library.repositories.postgres.event_types import PostgresEventTypeRepository
        return PostgresEventTypeRepository

    def test_update_moments_also_updates_order(self):
        Repo = self._import()
        from library.event_type import EventType

        # _ensure_loaded returns existing type
        rows = [
            ("custom", "Custom", "", {"louvor": 3}, ["louvor"]),
        ]
        pool, cursor = make_pool(results=[rows])
        repo = Repo(pool)

        repo.update("custom", moments={"louvor": 3, "final": 1})

        # Verify the UPDATE SET clause includes moments_order
        update_query = cursor.queries[-1]
        assert "moments_order" in update_query

    def test_update_name_does_not_touch_order(self):
        Repo = self._import()
        rows = [
            ("custom", "Custom", "", {"louvor": 3}, ["louvor"]),
        ]
        pool, cursor = make_pool(results=[rows])
        repo = Repo(pool)

        repo.update("custom", name="Renamed")

        update_query = cursor.queries[-1]
        assert "moments_order" not in update_query
