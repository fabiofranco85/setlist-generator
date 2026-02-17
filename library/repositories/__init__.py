"""Repository pattern for data access abstraction.

This module provides a clean abstraction layer for data access, allowing
the application to switch between different storage backends:

- **filesystem** (default): CSV files + JSON files (current behavior)
- **postgres** (future): PostgreSQL/Supabase database
- **mongodb** (future): MongoDB document database

Usage:
    >>> from library.repositories import get_repositories
    >>> repos = get_repositories()  # Uses STORAGE_BACKEND env var
    >>> songs = repos.songs.get_all()
    >>> history = repos.history.get_all()

Configuration via environment variables:
    STORAGE_BACKEND=filesystem  # Default (current file-based behavior)
    STORAGE_BACKEND=postgres    # PostgreSQL/Supabase
    STORAGE_BACKEND=mongodb     # MongoDB

Backend-specific configuration:
    # PostgreSQL
    DATABASE_URL=postgresql://user:pass@host:5432/db

    # MongoDB
    MONGODB_URI=mongodb://localhost:27017
    MONGODB_DATABASE=setlist
"""

from .protocols import (
    SongRepository,
    HistoryRepository,
    ConfigRepository,
    OutputRepository,
)
from .factory import (
    RepositoryContainer,
    RepositoryFactory,
    get_repositories,
)
from .filesystem import (
    FilesystemRepositoryContainer,
    FilesystemSongRepository,
    FilesystemHistoryRepository,
    FilesystemConfigRepository,
    FilesystemOutputRepository,
)

# Register filesystem backend now that it's imported
RepositoryFactory.register("filesystem", FilesystemRepositoryContainer)

# Conditionally register PostgreSQL backend (requires psycopg)
try:
    from .postgres import (
        PostgresRepositoryContainer,
        PostgresSongRepository,
        PostgresHistoryRepository,
        PostgresConfigRepository,
    )

    RepositoryFactory.register("postgres", PostgresRepositoryContainer)
    _has_postgres = True
except ImportError:
    _has_postgres = False


__all__ = [
    # Protocols (interfaces)
    "SongRepository",
    "HistoryRepository",
    "ConfigRepository",
    "OutputRepository",
    # Factory
    "RepositoryContainer",
    "RepositoryFactory",
    "get_repositories",
    # Filesystem implementations
    "FilesystemRepositoryContainer",
    "FilesystemSongRepository",
    "FilesystemHistoryRepository",
    "FilesystemConfigRepository",
    "FilesystemOutputRepository",
]

if _has_postgres:
    __all__ += [
        "PostgresRepositoryContainer",
        "PostgresSongRepository",
        "PostgresHistoryRepository",
        "PostgresConfigRepository",
    ]
