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
        # When neither moment is in MOMENTS_CONFIG, the canonical fallback
        # sorts extras alphabetically — matches list(moments.keys()) here.
        assert et.moments_order == ["alpha", "beta"]

    def test_null_moments_order_canonicalizes_standard_moments(self):
        """When moments_order is NULL AND the moments overlap with the
        canonical MOMENTS_CONFIG, the loader uses canonical service order
        instead of trusting postgres' JSONB key order (which is binary, not
        user-defined). Regression for the user-visible "main shows alphabetical
        moments" bug — the seed SQL inserted main without moments_order,
        leaving it NULL, and the fallback used to surface JSONB internal order.
        """
        Repo = self._import()
        # Simulate postgres JSONB returning keys in non-canonical order
        rows = [(
            "main", "Main Event", "",
            {"louvor": 4, "crianças": 1, "poslúdio": 1, "prelúdio": 1,
             "ofertório": 1, "saudação": 1},
            None,  # moments_order NULL (seed-inserted main)
        )]
        pool, _ = make_pool(results=[rows])
        repo = Repo(pool)

        et = repo.get("main")
        # Canonical service order — matches MOMENTS_CONFIG.
        assert et.moments_order == [
            "prelúdio", "ofertório", "saudação", "crianças", "louvor", "poslúdio",
        ]

    def test_empty_moments_order_canonicalizes_standard_moments(self):
        """Same as above but with an empty-list moments_order (vs NULL)."""
        Repo = self._import()
        rows = [(
            "main", "Main Event", "",
            {"louvor": 4, "prelúdio": 1, "poslúdio": 1},
            [],  # empty list — also triggers canonical fallback
        )]
        pool, _ = make_pool(results=[rows])
        repo = Repo(pool)

        et = repo.get("main")
        assert et.moments_order == ["prelúdio", "louvor", "poslúdio"]


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
