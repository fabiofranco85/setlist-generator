"""PostgreSQL integration tests for the generation fixes (Problems 1-4).

These tests use a temporary Docker PostgreSQL container (via the
docker_postgres fixture). They verify that fixes work end-to-end
against a real database — in particular, that JSONB key ordering
is handled correctly.

Run with:
    uv run pytest tests/integration/test_postgres_generation_fixes.py -v

Requires: Docker, psycopg (uv sync --group postgres)
"""

import json

import pytest

from library.event_type import EventType
from library.generator import SetlistGenerator

# Skip entire module if docker_postgres fixture can't be provided
# (Docker not available or psycopg not installed)
pytestmark = pytest.mark.postgres


@pytest.fixture()
def pg_event_type_repo(pg_pool, pg_clean_tables):
    """Create a PostgresEventTypeRepository."""
    from library.repositories.postgres.event_types import PostgresEventTypeRepository
    return PostgresEventTypeRepository(pg_pool)


@pytest.fixture()
def pg_history_repo(pg_pool, pg_clean_tables):
    """Create a PostgresHistoryRepository."""
    from library.repositories.postgres.history import PostgresHistoryRepository
    return PostgresHistoryRepository(pg_pool)


@pytest.fixture()
def pg_song_repo(pg_pool, pg_clean_tables):
    """Create a PostgresSongRepository with seeded songs."""
    from library.repositories.postgres.songs import PostgresSongRepository

    with pg_pool.connection() as conn:
        with conn.cursor() as cur:
            for title, energy, content in [
                ("Song A", 1.0, "### Song A (C)"),
                ("Song B", 2.0, "### Song B (D)"),
                ("Song C", 3.0, "### Song C (Em)"),
                ("Song D", 4.0, "### Song D (A)"),
            ]:
                cur.execute(
                    "INSERT INTO songs (title, energy, content) VALUES (%s, %s, %s)",
                    (title, energy, content),
                )
            for song_title, moment, weight in [
                ("Song A", "louvor", 4),
                ("Song A", "final", 2),
                ("Song B", "louvor", 3),
                ("Song C", "louvor", 5),
                ("Song C", "final", 3),
                ("Song D", "louvor", 4),
            ]:
                cur.execute(
                    "INSERT INTO song_tags (song_title, moment, weight) "
                    "VALUES (%s, %s, %s)",
                    (song_title, moment, weight),
                )
        conn.commit()

    return PostgresSongRepository(pg_pool)


# ---------------------------------------------------------------------------
# Problem 1: JSONB key ordering preserved via moments_order
# ---------------------------------------------------------------------------


class TestPostgresMomentOrdering:
    """Verify that moments_order survives JSONB round-trip in PostgreSQL."""

    def test_jsonb_alphabetizes_keys(self, pg_pool, pg_clean_tables):
        """Prove that JSONB sorts keys alphabetically (the bug we're fixing)."""
        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO event_types (slug, name, moments) "
                    "VALUES (%s, %s, %s::jsonb)",
                    ("test", "Test", json.dumps({"louvor": 3, "final": 1})),
                )
                conn.commit()
                cur.execute("SELECT moments FROM event_types WHERE slug = 'test'")
                row = cur.fetchone()

        # JSONB returns keys in alphabetical order
        keys = list(row[0].keys())
        assert keys == ["final", "louvor"], (
            "PostgreSQL JSONB should alphabetize keys — "
            "if this fails, the test premise is wrong"
        )

    def test_moments_order_preserves_user_order(self, pg_event_type_repo):
        """Despite JSONB alphabetizing, moments_order preserves user intent."""
        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 3, "final": 1},
            moments_order=["louvor", "final"],
        )
        pg_event_type_repo.add(et)

        # Force cache invalidation to read from DB
        pg_event_type_repo._cache = None
        loaded = pg_event_type_repo.get("custom")

        assert loaded.moments_order == ["louvor", "final"]
        assert list(loaded.ordered_moments.keys()) == ["louvor", "final"]

    def test_ordered_moments_values_correct(self, pg_event_type_repo):
        """ordered_moments returns correct counts in the right order."""
        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 3, "final": 1},
            moments_order=["louvor", "final"],
        )
        pg_event_type_repo.add(et)

        pg_event_type_repo._cache = None
        loaded = pg_event_type_repo.get("custom")

        om = loaded.ordered_moments
        assert om == {"louvor": 3, "final": 1}
        assert list(om.keys()) == ["louvor", "final"]

    def test_update_moments_updates_order(self, pg_event_type_repo):
        """Updating moments through the repo also updates moments_order."""
        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 3},
        )
        pg_event_type_repo.add(et)

        pg_event_type_repo.update("custom", moments={"final": 1, "louvor": 2})

        pg_event_type_repo._cache = None
        loaded = pg_event_type_repo.get("custom")

        assert loaded.moments_order == ["final", "louvor"]

    def test_null_moments_order_defaults(self, pg_pool, pg_clean_tables):
        """Old rows with NULL moments_order still work (backward compat).

        When moments_order is NULL, the fallback derives order from the JSONB
        moments dict — which PostgreSQL returns alphabetically. This is the
        best we can do for old data without an explicit ordering.
        """
        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO event_types (slug, name, moments, moments_order) "
                    "VALUES (%s, %s, %s::jsonb, NULL)",
                    ("old", "Old Type", json.dumps({"zebra": 1, "alpha": 2})),
                )
                conn.commit()

        from library.repositories.postgres.event_types import PostgresEventTypeRepository
        repo = PostgresEventTypeRepository(pg_pool)
        loaded = repo.get("old")

        # moments_order defaults from JSONB key order (alphabetical)
        assert loaded is not None
        assert loaded.moments_order == ["alpha", "zebra"]
        # ordered_moments also follows alphabetical
        assert list(loaded.ordered_moments.keys()) == ["alpha", "zebra"]


# ---------------------------------------------------------------------------
# Problem 1+2: Full generation through PostgreSQL
# ---------------------------------------------------------------------------


class TestPostgresGenerationWorkflow:
    """End-to-end generation using real PostgreSQL data."""

    def test_generate_with_custom_moments_order(
        self, pg_event_type_repo, pg_song_repo, pg_history_repo,
    ):
        """Full workflow: create event type → generate setlist → verify order.

        Uses louvor=1 so that at least one 'final'-tagged song
        (Song A or Song C) remains available for the final moment.
        """
        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 1, "final": 1},
            moments_order=["louvor", "final"],
        )
        pg_event_type_repo.add(et)

        # Load data via repos
        songs = pg_song_repo.get_all()
        history = pg_history_repo.get_all()

        # Generate using ordered_moments
        pg_event_type_repo._cache = None
        loaded_et = pg_event_type_repo.get("custom")

        generator = SetlistGenerator(songs, history)
        setlist = generator.generate(
            "2026-03-10",
            event_type="custom",
            moments_config=loaded_et.ordered_moments,
        )

        # Moments should be in the event type's order
        keys = list(setlist.moments.keys())
        assert keys == ["louvor", "final"]
        assert len(setlist.moments["louvor"]) == 1
        assert len(setlist.moments["final"]) == 1

    def test_strict_mode_raises_for_untagged(self, pg_song_repo, pg_history_repo):
        """Custom event type with untagged moment raises ValueError."""
        songs = pg_song_repo.get_all()
        history = pg_history_repo.get_all()

        generator = SetlistGenerator(songs, history)

        with pytest.raises(ValueError, match="No songs available for moment 'nonexistent'"):
            generator.generate(
                "2026-03-10",
                moments_config={"louvor": 1, "nonexistent": 1},
            )


# ---------------------------------------------------------------------------
# Problem 3: Backend name
# ---------------------------------------------------------------------------


class TestPostgresBackendName:
    def test_postgres_backend_name(self, pg_history_repo):
        assert pg_history_repo.backend_name == "postgres"
