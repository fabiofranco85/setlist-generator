"""Unit tests for PostgreSQL repository implementations.

All tests mock the psycopg pool/connection boundary — no database required.
"""

from contextlib import contextmanager
from datetime import date as Date
from unittest.mock import MagicMock, patch

import pytest

from library.models import Setlist


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockCursor:
    """Lightweight cursor mock that records executed queries."""

    def __init__(self):
        self.queries = []
        self.params = []
        self._results = []
        self.rowcount = 0
        self._rowcount_override = None

    def execute(self, query, params=None):
        self.queries.append(query)
        self.params.append(params)
        # Simulate rowcount for UPDATE/DELETE
        if self._rowcount_override is not None:
            self.rowcount = self._rowcount_override

    def fetchall(self):
        if self._results:
            return self._results.pop(0)
        return []

    def fetchone(self):
        if self._results:
            rows = self._results.pop(0)
            return rows[0] if rows else None
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockConnection:
    """Connection mock that yields a cursor."""

    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass


def make_pool(results=None, rowcount=None):
    """Create a mock pool that returns preset query results.

    Args:
        results: List of result sets. Each call to fetchall()/fetchone()
                 pops the next result set.
        rowcount: Override for cursor.rowcount (simulates affected rows).
    """
    cursor = MockCursor()
    cursor._results = list(results) if results else []
    cursor._rowcount_override = rowcount
    conn = MockConnection(cursor)

    pool = MagicMock()

    @contextmanager
    def connection():
        yield conn

    pool.connection = connection
    return pool, cursor


# ---------------------------------------------------------------------------
# PostgresSongRepository
# ---------------------------------------------------------------------------


class TestPostgresSongRepository:
    @pytest.fixture()
    def _import(self):
        """Import the module (skips if psycopg is required at import time)."""
        from library.repositories.postgres.songs import PostgresSongRepository
        return PostgresSongRepository

    def test_get_all_loads_and_caches(self, _import):
        Repo = _import
        songs_rows = [("Song A", 2.0, "chords A", "", []), ("Song B", 3.0, "chords B", "https://youtu.be/x", [])]
        tags_rows = [("Song A", "louvor", 5), ("Song A", "prelúdio", 3), ("Song B", "louvor", 4)]

        pool, cursor = make_pool(results=[songs_rows, tags_rows])
        repo = Repo(pool)

        songs = repo.get_all()
        assert len(songs) == 2
        assert songs["Song A"].title == "Song A"
        assert songs["Song A"].energy == 2.0
        assert songs["Song A"].tags == {"louvor": 5, "prelúdio": 3}
        assert songs["Song A"].content == "chords A"
        assert songs["Song B"].youtube_url == "https://youtu.be/x"

        # Second call uses cache (no additional queries)
        songs2 = repo.get_all()
        assert len(songs2) == 2
        # Only 2 queries total (songs + tags from first load)
        assert len(cursor.queries) == 2

    def test_get_by_title_found(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [("Song A", 2.0, "", "", [])],
            [("Song A", "louvor", 3)],
        ])
        repo = Repo(pool)
        song = repo.get_by_title("Song A")
        assert song is not None
        assert song.title == "Song A"

    def test_get_by_title_not_found(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[[], []])
        repo = Repo(pool)
        assert repo.get_by_title("Ghost") is None

    def test_search_case_insensitive(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [("Hello World", 2.0, "", "", []), ("Goodbye", 3.0, "", "", [])],
            [],
        ])
        repo = Repo(pool)
        results = repo.search("hello")
        assert len(results) == 1
        assert results[0].title == "Hello World"

    def test_exists_true(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [("Song A", 2.0, "", "", [])],
            [],
        ])
        repo = Repo(pool)
        assert repo.exists("Song A") is True

    def test_exists_false(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[[], []])
        repo = Repo(pool)
        assert repo.exists("Ghost") is False

    def test_update_content_success(self, _import):
        Repo = _import
        pool, cursor = make_pool(results=[
            [("Song A", 2.0, "old", "", [])],
            [("Song A", "louvor", 3)],
        ], rowcount=1)
        repo = Repo(pool)

        # Pre-load cache
        repo.get_all()

        repo.update_content("Song A", "new chords")

        # Verify UPDATE query was executed
        update_queries = [q for q in cursor.queries if "UPDATE" in q]
        assert len(update_queries) == 1
        assert cursor.params[2] == ("new chords", "Song A")

    def test_update_content_not_found(self, _import):
        Repo = _import
        pool, _ = make_pool(rowcount=0)
        repo = Repo(pool)

        with pytest.raises(KeyError, match="not found"):
            repo.update_content("Ghost", "content")

    def test_invalidate_cache(self, _import):
        Repo = _import
        pool, cursor = make_pool(results=[
            [("Song A", 2.0, "", "", [])], [],  # First load
            [("Song A", 2.0, "", "", []), ("Song B", 3.0, "", "", [])], [],  # Second load
        ])
        repo = Repo(pool)

        songs1 = repo.get_all()
        assert len(songs1) == 1

        repo.invalidate_cache()
        songs2 = repo.get_all()
        assert len(songs2) == 2
        # 4 queries total: 2 per load
        assert len(cursor.queries) == 4

    def test_default_energy_for_none(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [("Song A", None, "", "", [])],
            [],
        ])
        repo = Repo(pool)
        song = repo.get_by_title("Song A")
        assert song.energy == 2.5  # DEFAULT_ENERGY


# ---------------------------------------------------------------------------
# PostgresHistoryRepository
# ---------------------------------------------------------------------------


class TestPostgresHistoryRepository:
    @pytest.fixture()
    def _import(self):
        from library.repositories.postgres.history import PostgresHistoryRepository
        return PostgresHistoryRepository

    def test_get_all_empty(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[[]])
        repo = Repo(pool)
        assert repo.get_all() == []

    def test_get_all_sorted(self, _import):
        Repo = _import
        rows = [
            (Date(2026, 3, 1), "", {"louvor": ["A"]}, ""),
            (Date(2026, 2, 1), "", {"louvor": ["B"]}, ""),
            (Date(2026, 1, 1), "", {"louvor": ["C"]}, ""),
        ]
        pool, _ = make_pool(results=[rows])
        repo = Repo(pool)

        history = repo.get_all()
        assert len(history) == 3
        assert history[0]["date"] == "2026-03-01"
        assert history[2]["date"] == "2026-01-01"

    def test_get_all_omits_label_when_empty(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [(Date(2026, 1, 1), "", {"louvor": ["A"]}, "")],
        ])
        repo = Repo(pool)
        result = repo.get_all()
        assert "label" not in result[0]

    def test_get_all_includes_label_when_set(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [(Date(2026, 1, 1), "evening", {"louvor": ["A"]}, "")],
        ])
        repo = Repo(pool)
        result = repo.get_all()
        assert result[0]["label"] == "evening"

    def test_get_by_date_found(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [(Date(2026, 2, 15), "", {"louvor": ["A"]}, "")],
        ])
        repo = Repo(pool)
        result = repo.get_by_date("2026-02-15")
        assert result is not None
        assert result["date"] == "2026-02-15"
        assert result["moments"] == {"louvor": ["A"]}

    def test_get_by_date_not_found(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[[]])
        repo = Repo(pool)
        assert repo.get_by_date("2099-12-31") is None

    def test_get_by_date_with_label(self, _import):
        Repo = _import
        pool, cursor = make_pool(results=[
            [(Date(2026, 2, 15), "evening", {"louvor": ["A"]}, "")],
        ])
        repo = Repo(pool)
        result = repo.get_by_date("2026-02-15", label="evening")
        assert result is not None
        assert result["label"] == "evening"
        # Verify label and event_type were passed to query
        assert cursor.params[0] == ("2026-02-15", "evening", "")

    def test_get_by_date_all(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [
                (Date(2026, 3, 1), "", {"louvor": ["A"]}, ""),
                (Date(2026, 3, 1), "evening", {"louvor": ["B"]}, ""),
            ],
        ])
        repo = Repo(pool)
        results = repo.get_by_date_all("2026-03-01")
        assert len(results) == 2

    def test_get_latest(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [(Date(2026, 3, 1), "", {"louvor": ["A"]}, "")],
        ])
        repo = Repo(pool)
        result = repo.get_latest()
        assert result["date"] == "2026-03-01"

    def test_get_latest_empty(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[[]])
        repo = Repo(pool)
        assert repo.get_latest() is None

    def test_save(self, _import):
        Repo = _import
        pool, cursor = make_pool()
        repo = Repo(pool)

        setlist = Setlist(date="2026-02-15", moments={"louvor": ["A"]})
        repo.save(setlist)

        assert len(cursor.queries) == 1
        assert "INSERT" in cursor.queries[0]
        assert "ON CONFLICT" in cursor.queries[0]
        # Params: date, event_type, label, moments (JSON)
        assert cursor.params[0] == ("2026-02-15", "", "", '{"louvor": ["A"]}')

    def test_save_with_label(self, _import):
        Repo = _import
        pool, cursor = make_pool()
        repo = Repo(pool)

        setlist = Setlist(date="2026-02-15", moments={"louvor": ["A"]}, label="evening")
        repo.save(setlist)
        assert cursor.params[0] == ("2026-02-15", "", "evening", '{"louvor": ["A"]}')

    def test_update_success(self, _import):
        Repo = _import
        pool, cursor = make_pool(rowcount=1)
        repo = Repo(pool)

        repo.update("2026-02-15", {"date": "2026-02-15", "moments": {"louvor": ["B"]}})
        assert "UPDATE" in cursor.queries[0]

    def test_update_not_found(self, _import):
        Repo = _import
        pool, _ = make_pool(rowcount=0)
        repo = Repo(pool)

        with pytest.raises(KeyError, match="No setlist found"):
            repo.update("2099-12-31", {"date": "2099-12-31", "moments": {}})

    def test_exists_true(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[[(1,)]])
        repo = Repo(pool)
        assert repo.exists("2026-02-15") is True

    def test_exists_false(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[[]])
        repo = Repo(pool)
        assert repo.exists("2099-12-31") is False

    def test_delete_success(self, _import):
        Repo = _import
        pool, cursor = make_pool(rowcount=1)
        repo = Repo(pool)

        repo.delete("2026-02-15")
        assert "DELETE" in cursor.queries[0]

    def test_delete_not_found(self, _import):
        Repo = _import
        pool, _ = make_pool(rowcount=0)
        repo = Repo(pool)

        with pytest.raises(KeyError, match="No setlist found"):
            repo.delete("2099-12-31")


# ---------------------------------------------------------------------------
# PostgresConfigRepository
# ---------------------------------------------------------------------------


class TestPostgresConfigRepository:
    @pytest.fixture()
    def _import(self):
        from library.repositories.postgres.config import PostgresConfigRepository
        return PostgresConfigRepository

    def test_loads_from_db(self, _import):
        Repo = _import
        pool, _ = make_pool(results=[
            [
                ("moments_config", {"louvor": 4, "prelúdio": 1}),
                ("recency_decay_days", 30),
                ("default_weight", 5),
                ("energy_ordering_enabled", False),
                ("energy_ordering_rules", {"louvor": "descending"}),
                ("default_energy", 3.0),
            ],
        ])
        repo = Repo(pool)

        assert repo.get_moments_config() == {"louvor": 4, "prelúdio": 1}
        assert repo.get_recency_decay_days() == 30
        assert repo.get_default_weight() == 5
        assert repo.is_energy_ordering_enabled() is False
        assert repo.get_energy_ordering_rules() == {"louvor": "descending"}
        assert repo.get_default_energy() == 3.0

    def test_falls_back_to_python_constants(self, _import):
        Repo = _import
        # Empty config table — should fall back to library/config.py defaults
        pool, _ = make_pool(results=[[]])
        repo = Repo(pool)

        assert repo.get_moments_config()["louvor"] == 4
        assert repo.get_recency_decay_days() == 45
        assert repo.get_default_weight() == 3
        assert repo.is_energy_ordering_enabled() is True
        assert repo.get_energy_ordering_rules() == {"louvor": "ascending"}
        assert repo.get_default_energy() == 2.5

    def test_caches_after_first_load(self, _import):
        Repo = _import
        pool, cursor = make_pool(results=[[("recency_decay_days", 60)]])
        repo = Repo(pool)

        repo.get_recency_decay_days()
        repo.get_default_weight()
        # Only 1 query (both reads served from cache)
        assert len(cursor.queries) == 1

    def test_invalidate_cache(self, _import):
        Repo = _import
        pool, cursor = make_pool(results=[
            [("recency_decay_days", 60)],
            [("recency_decay_days", 90)],
        ])
        repo = Repo(pool)

        assert repo.get_recency_decay_days() == 60
        repo.invalidate_cache()
        assert repo.get_recency_decay_days() == 90
        assert len(cursor.queries) == 2


# ---------------------------------------------------------------------------
# PostgresRepositoryContainer
# ---------------------------------------------------------------------------


class TestPostgresRepositoryContainer:
    def test_create_returns_container(self, tmp_path):
        """Container creates all repos with a shared pool."""
        from library.repositories.postgres.songs import PostgresSongRepository
        from library.repositories.postgres.history import PostgresHistoryRepository
        from library.repositories.postgres.config import PostgresConfigRepository
        from library.repositories.filesystem.output import FilesystemOutputRepository
        import library.repositories.postgres as pg_module

        mock_pool = MagicMock()

        original_create_pool = pg_module.create_pool
        pg_module.create_pool = lambda **kwargs: mock_pool
        try:
            container = pg_module.PostgresRepositoryContainer.create(
                base_path=tmp_path,
                database_url="postgresql://test:test@localhost/test",
            )
        finally:
            pg_module.create_pool = original_create_pool

        assert isinstance(container.songs, PostgresSongRepository)
        assert isinstance(container.history, PostgresHistoryRepository)
        assert isinstance(container.config, PostgresConfigRepository)
        assert isinstance(container.output, FilesystemOutputRepository)

    def test_create_missing_url_raises(self, tmp_path, monkeypatch):
        """Container raises ValueError if no database URL provided."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # create_pool raises ImportError (psycopg not installed) before
        # reaching the URL check. Mock the import to test the URL validation.
        mock_pool_cls = MagicMock()

        import library.repositories.postgres.connection as conn_mod

        with patch.dict("sys.modules", {"psycopg_pool": MagicMock(ConnectionPool=mock_pool_cls)}):
            with pytest.raises(ValueError, match="No database URL"):
                conn_mod.create_pool(conninfo=None)


# ---------------------------------------------------------------------------
# Factory registration
# ---------------------------------------------------------------------------


class TestFactoryRegistration:
    def test_postgres_backend_registered(self):
        """The postgres backend is registered if psycopg is importable."""
        from library.repositories.factory import RepositoryFactory

        # Since we can import the postgres module (no actual psycopg needed
        # for the container class itself), it should be registered
        try:
            from library.repositories.postgres import PostgresRepositoryContainer
            assert "postgres" in RepositoryFactory._backends
        except ImportError:
            # psycopg not installed — registration skipped, which is also valid
            pass
