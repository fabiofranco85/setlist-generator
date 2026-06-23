"""Integration tests for PostgreSQL repositories.

These tests run against a throwaway PostgreSQL container provisioned by
the session-scoped ``docker_postgres`` fixture in
``tests/integration/conftest.py``. They are auto-skipped when Docker (or
``psycopg``) is unavailable.

Historically this file read ``DATABASE_URL`` directly and ran ``TRUNCATE``
on whatever database it pointed at — which is dangerous in development
environments where ``DATABASE_URL`` typically points at a real, populated
database. Migrating onto the shared ``docker_postgres`` / ``pg_pool`` /
``pg_clean_tables`` fixtures eliminates that risk entirely: the tests
provision their own isolated container and never read ``DATABASE_URL``.

Run with:
    uv run pytest tests/integration/test_postgres_repositories.py -v -m postgres
"""

import pytest

from library.models import Setlist

pytestmark = pytest.mark.postgres


@pytest.fixture()
def seed_songs(pg_pool, pg_clean_tables):
    """Insert a few test songs into the isolated test database.

    Depends on ``pg_clean_tables`` so the table state is reset before each
    test. The shared fixture lives in ``tests/integration/conftest.py``.
    """
    with pg_pool.connection() as conn:
        with conn.cursor() as cur:
            for title, energy, content, youtube in [
                ("Upbeat Song", 1.0, "### Upbeat Song (C)\nC G\nLyrics", ""),
                ("Moderate Song", 2.0, "### Moderate Song (D)\nD A\nLyrics", ""),
                ("Reflective Song", 3.0, "### Reflective Song (Em)\nEm Am\nLyrics", ""),
                ("Worship Song", 4.0, "### Worship Song (A)\nA E\nLyrics", "https://youtu.be/x"),
            ]:
                cur.execute(
                    "INSERT INTO songs (title, energy, content, youtube_url) VALUES (%s, %s, %s, %s)",
                    (title, energy, content, youtube),
                )
            for song_title, moment, weight in [
                ("Upbeat Song", "louvor", 4),
                ("Upbeat Song", "prelúdio", 3),
                ("Moderate Song", "louvor", 3),
                ("Moderate Song", "saudação", 4),
                ("Reflective Song", "louvor", 5),
                ("Reflective Song", "ofertório", 3),
                ("Worship Song", "louvor", 4),
                ("Worship Song", "poslúdio", 2),
            ]:
                cur.execute(
                    "INSERT INTO song_tags (song_title, moment, weight) VALUES (%s, %s, %s)",
                    (song_title, moment, weight),
                )
        conn.commit()


# ---------------------------------------------------------------------------
# SongRepository
# ---------------------------------------------------------------------------


class TestPostgresSongRepository:
    @pytest.fixture()
    def repo(self, pg_pool, seed_songs):
        from library.repositories.postgres.songs import PostgresSongRepository
        return PostgresSongRepository(pg_pool)

    def test_get_all_count(self, repo):
        songs = repo.get_all()
        assert len(songs) == 4

    def test_get_all_keys(self, repo):
        songs = repo.get_all()
        assert "Upbeat Song" in songs
        assert "Worship Song" in songs

    def test_get_by_title_found(self, repo):
        song = repo.get_by_title("Upbeat Song")
        assert song is not None
        assert song.title == "Upbeat Song"
        assert song.energy == 1.0

    def test_get_by_title_not_found(self, repo):
        assert repo.get_by_title("Ghost") is None

    def test_search_case_insensitive(self, repo):
        results = repo.search("upbeat")
        assert len(results) == 1
        assert results[0].title == "Upbeat Song"

    def test_search_partial_match(self, repo):
        results = repo.search("Song")
        assert len(results) == 4

    def test_tags_parsed_correctly(self, repo):
        song = repo.get_by_title("Upbeat Song")
        assert song.tags == {"louvor": 4, "prelúdio": 3}

    def test_content_loaded(self, repo):
        song = repo.get_by_title("Upbeat Song")
        assert "### Upbeat Song (C)" in song.content

    def test_youtube_url(self, repo):
        song = repo.get_by_title("Worship Song")
        assert song.youtube_url == "https://youtu.be/x"

    def test_update_content(self, repo):
        new_content = "### Upbeat Song (D)\nD A\nNew lyrics"
        repo.update_content("Upbeat Song", new_content)
        song = repo.get_by_title("Upbeat Song")
        assert song.content == new_content

    def test_update_content_not_found_raises(self, repo):
        with pytest.raises(KeyError, match="not found"):
            repo.update_content("Ghost", "content")

    def test_exists(self, repo):
        assert repo.exists("Upbeat Song") is True
        assert repo.exists("Ghost") is False

    def test_add_song(self, repo, pg_pool):
        from library.models import Song

        repo.add(Song(
            title="Novo Louvor",
            tags={"louvor": 5, "prelúdio": 3},
            energy=2.0,
            content="### Novo Louvor (G)\n\nG C\nLyrics",
            youtube_url="https://youtu.be/abc123",
        ))
        # Fresh repo proves the rows hit the database, not just the cache.
        from library.repositories.postgres.songs import PostgresSongRepository

        fresh = PostgresSongRepository(pg_pool)
        song = fresh.get_by_title("Novo Louvor")
        assert song is not None
        assert song.tags == {"louvor": 5, "prelúdio": 3}
        assert song.energy == 2.0
        assert song.content == "### Novo Louvor (G)\n\nG C\nLyrics"
        assert song.youtube_url == "https://youtu.be/abc123"

    def test_add_song_with_event_types(self, repo, pg_pool):
        from library.models import Song
        from library.repositories.postgres.songs import PostgresSongRepository

        repo.add(Song(
            title="Youth Anthem",
            tags={"louvor": 5},
            energy=1.0,
            content="",
            event_types=["youth"],
        ))
        fresh = PostgresSongRepository(pg_pool)
        song = fresh.get_by_title("Youth Anthem")
        assert song is not None and song.event_types == ["youth"]

    def test_add_duplicate_title_raises(self, repo):
        from library.models import Song

        with pytest.raises(ValueError, match="already exists"):
            repo.add(Song(title="Upbeat Song", tags={"louvor": 3}, energy=1.0, content=""))

    def test_add_invalidates_cache(self, repo):
        from library.models import Song

        assert repo.get_by_title("Novo Louvor") is None  # primes the cache
        repo.add(Song(title="Novo Louvor", tags={"louvor": 3}, energy=2.0, content=""))
        assert repo.get_by_title("Novo Louvor") is not None


# ---------------------------------------------------------------------------
# HistoryRepository
# ---------------------------------------------------------------------------


class TestPostgresHistoryRepository:
    @pytest.fixture()
    def repo(self, pg_pool, pg_clean_tables):
        from library.repositories.postgres.history import PostgresHistoryRepository
        return PostgresHistoryRepository(pg_pool)

    def test_get_all_empty(self, repo):
        assert repo.get_all() == []

    def test_save_and_get_all(self, repo):
        setlist = Setlist(date="2026-02-15", moments={"louvor": ["Song A"]})
        repo.save(setlist)
        history = repo.get_all()
        assert len(history) == 1
        assert history[0]["date"] == "2026-02-15"

    def test_get_by_date_found(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["Song A"]}))
        result = repo.get_by_date("2026-02-15")
        assert result is not None
        assert result["date"] == "2026-02-15"

    def test_get_by_date_not_found(self, repo):
        assert repo.get_by_date("2099-12-31") is None

    def test_get_latest_empty(self, repo):
        assert repo.get_latest() is None

    def test_get_latest(self, repo):
        repo.save(Setlist(date="2026-01-01", moments={"louvor": ["A"]}))
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["B"]}))
        latest = repo.get_latest()
        assert latest["date"] == "2026-02-15"

    def test_save_overwrites_existing(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["A"]}))
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["B"]}))
        result = repo.get_by_date("2026-02-15")
        assert result["moments"]["louvor"] == ["B"]

    def test_update_existing(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["A"]}))
        repo.update("2026-02-15", {"date": "2026-02-15", "moments": {"louvor": ["B"]}})
        result = repo.get_by_date("2026-02-15")
        assert result["moments"]["louvor"] == ["B"]

    def test_update_nonexistent_raises(self, repo):
        with pytest.raises(KeyError, match="No setlist found"):
            repo.update("2099-12-31", {"date": "2099-12-31", "moments": {}})

    def test_exists(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["A"]}))
        assert repo.exists("2026-02-15") is True
        assert repo.exists("2099-12-31") is False

    def test_delete(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["A"]}))
        repo.delete("2026-02-15")
        assert repo.exists("2026-02-15") is False

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(KeyError, match="No setlist found"):
            repo.delete("2099-12-31")

    def test_get_all_sorted_most_recent_first(self, repo):
        repo.save(Setlist(date="2026-01-01", moments={"louvor": ["A"]}))
        repo.save(Setlist(date="2026-03-01", moments={"louvor": ["B"]}))
        repo.save(Setlist(date="2026-02-01", moments={"louvor": ["C"]}))
        history = repo.get_all()
        dates = [h["date"] for h in history]
        assert dates == ["2026-03-01", "2026-02-01", "2026-01-01"]

    def test_labeled_setlists(self, repo):
        repo.save(Setlist(date="2026-03-01", moments={"louvor": ["A"]}))
        repo.save(Setlist(date="2026-03-01", moments={"louvor": ["B"]}, label="evening"))

        # get_by_date with specific label
        result = repo.get_by_date("2026-03-01", label="evening")
        assert result is not None
        assert result["label"] == "evening"

        # get_by_date_all
        all_for_date = repo.get_by_date_all("2026-03-01")
        assert len(all_for_date) == 2

        # Unlabeled result has no "label" key
        unlabeled = repo.get_by_date("2026-03-01")
        assert "label" not in unlabeled


# ---------------------------------------------------------------------------
# ConfigRepository
# ---------------------------------------------------------------------------


class TestPostgresConfigRepository:
    @pytest.fixture()
    def repo(self, pg_pool, pg_clean_tables):
        from library.repositories.postgres.config import PostgresConfigRepository
        return PostgresConfigRepository(pg_pool)

    def test_moments(self, repo):
        moments = repo.get_moments_config()
        assert "louvor" in moments
        assert moments["louvor"] == 4

    def test_recency_decay(self, repo):
        assert repo.get_recency_decay_days() == 45

    def test_default_weight(self, repo):
        assert repo.get_default_weight() == 3

    def test_energy_ordering(self, repo):
        assert repo.is_energy_ordering_enabled() is True
        rules = repo.get_energy_ordering_rules()
        assert rules.get("louvor") == "ascending"

    def test_default_energy(self, repo):
        assert repo.get_default_energy() == 2.5


# ---------------------------------------------------------------------------
# Factory integration
# ---------------------------------------------------------------------------


class TestGetRepositoriesPostgres:
    def test_postgres_backend(self, docker_postgres, pg_clean_tables, tmp_path, monkeypatch):
        """get_repositories(backend='postgres') returns a working container.

        Points DATABASE_URL at the throwaway test container rather than
        whatever the developer's shell has set.
        """
        monkeypatch.setenv("DATABASE_URL", docker_postgres)

        from library.repositories import get_repositories

        repos = get_repositories(backend="postgres", base_path=tmp_path)
        try:
            # Should be able to use config repo
            moments = repos.config.get_moments_config()
            assert "louvor" in moments
        finally:
            # Close the pool created by get_repositories to avoid GC warnings
            repos.songs._pool.close()
