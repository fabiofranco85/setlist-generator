"""PostgreSQL backend for repository pattern.

This module provides PostgreSQL-based implementations of all repository protocols
except OutputRepository, which reuses the filesystem implementation (output files
are always local).

Requires: psycopg[binary,pool]>=3.1
Install with: uv sync --group postgres
"""

from pathlib import Path
from typing import Any

from ..factory import RepositoryContainer
from ..filesystem.output import FilesystemOutputRepository
from ...paths import get_output_paths

from .connection import create_pool
from .songs import PostgresSongRepository
from .history import PostgresHistoryRepository
from .config import PostgresConfigRepository


class PostgresRepositoryContainer:
    """Factory for creating PostgreSQL-backed repositories.

    Creates a RepositoryContainer with PostgreSQL repos for songs, history,
    and config. Output repo uses filesystem (output files are always local).
    """

    @classmethod
    def create(
        cls,
        base_path: Path | None = None,
        database_url: str | None = None,
        output_dir: Path | None = None,
        **kwargs: Any,
    ) -> RepositoryContainer:
        """Create all repositories for the PostgreSQL backend.

        Args:
            base_path: Project root directory (used for output paths).
            database_url: PostgreSQL connection string. If None, reads
                          DATABASE_URL environment variable.
            output_dir: Override for output directory path.
            **kwargs: Additional arguments (ignored).

        Returns:
            RepositoryContainer with PostgreSQL + filesystem output repos.

        Raises:
            ImportError: If psycopg is not installed.
            ValueError: If no database URL is provided or found in env.
        """
        if base_path is None:
            base_path = Path.cwd()

        # Create shared connection pool
        pool = create_pool(conninfo=database_url)

        # Resolve output path (output is always filesystem)
        paths = get_output_paths(
            base_path,
            cli_output_dir=str(output_dir) if output_dir else None,
        )

        return RepositoryContainer(
            songs=PostgresSongRepository(pool),
            history=PostgresHistoryRepository(pool),
            config=PostgresConfigRepository(pool),
            output=FilesystemOutputRepository(paths.output_dir),
        )


__all__ = [
    "PostgresRepositoryContainer",
    "PostgresSongRepository",
    "PostgresHistoryRepository",
    "PostgresConfigRepository",
    "create_pool",
]
