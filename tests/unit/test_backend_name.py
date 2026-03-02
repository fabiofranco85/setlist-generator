"""Unit tests for HistoryRepository.backend_name property (Problem 3).

Each backend must expose a backend_name property so the CLI can print
appropriate save-confirmation messages.
"""

from library.repositories.filesystem.history import FilesystemHistoryRepository


class TestFilesystemBackendName:
    def test_returns_filesystem(self, tmp_path):
        repo = FilesystemHistoryRepository(tmp_path)
        assert repo.backend_name == "filesystem"


class TestPostgresBackendName:
    def test_returns_postgres(self):
        from library.repositories.postgres.history import PostgresHistoryRepository
        from tests.unit.test_postgres_repositories import make_pool

        pool, _ = make_pool()
        repo = PostgresHistoryRepository(pool)
        assert repo.backend_name == "postgres"


class TestSupabaseBackendName:
    def test_returns_supabase(self):
        try:
            from library.repositories.supabase.history import SupabaseHistoryRepository
        except ImportError:
            import pytest
            pytest.skip("supabase not installed")

        from unittest.mock import MagicMock
        mock_client = MagicMock()
        repo = SupabaseHistoryRepository(mock_client, org_id="test-org")
        assert repo.backend_name == "supabase"
