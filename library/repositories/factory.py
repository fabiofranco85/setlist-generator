"""Repository factory for creating backend-specific implementations.

This module provides the factory pattern for instantiating repositories
based on the configured storage backend. The backend is determined by:
1. Explicit parameter to get_repositories()
2. STORAGE_BACKEND environment variable
3. Default: "filesystem"

Example:
    >>> repos = get_repositories()  # Uses STORAGE_BACKEND env var or default
    >>> repos = get_repositories(backend="filesystem")  # Explicit filesystem
    >>> repos = get_repositories(backend="postgres", database_url="...")  # Future
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .protocols import (
    SongRepository,
    HistoryRepository,
    ConfigRepository,
    OutputRepository,
    EventTypeRepository,
    UserRepository,
    ShareRequestRepository,
    CloudOutputRepository,
)


@dataclass
class RepositoryContainer:
    """Container for all repository instances.

    This dataclass bundles all repository types together, making it easy
    to pass around and inject dependencies. The factory function returns
    this container with all repositories initialized for the selected backend.

    Attributes:
        songs: Repository for song data access
        history: Repository for setlist history access
        config: Repository for configuration access
        output: Repository for output file generation
        event_types: Repository for event type management (optional)
    """

    songs: SongRepository
    history: HistoryRepository
    config: ConfigRepository
    output: OutputRepository
    event_types: EventTypeRepository | None = None


@dataclass
class SaaSRepositoryContainer(RepositoryContainer):
    """Extended container for SaaS deployments with multi-tenant support.

    Adds user management, song sharing workflows, and cloud output storage
    on top of the base RepositoryContainer.
    """

    users: UserRepository | None = None
    share_requests: ShareRequestRepository | None = None
    cloud_output: CloudOutputRepository | None = None


class RepositoryFactory:
    """Factory for creating repository implementations.

    This class maps backend names to their implementation modules and
    provides a unified interface for creating all repositories for a backend.
    """

    # Registry of backend names to implementation factories
    _backends: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, container_class: type) -> None:
        """Register a backend implementation.

        Args:
            name: Backend identifier (e.g., "filesystem", "postgres")
            container_class: Class that creates RepositoryContainer for this backend
        """
        cls._backends[name] = container_class

    @classmethod
    def create(cls, backend: str, **kwargs: Any) -> RepositoryContainer:
        """Create repositories for the specified backend.

        Args:
            backend: Backend name ("filesystem", "postgres", "mongodb", etc.)
            **kwargs: Backend-specific configuration

        Returns:
            RepositoryContainer with all repositories for the backend

        Raises:
            ValueError: If backend is not registered
        """
        if backend not in cls._backends:
            available = ", ".join(cls._backends.keys()) or "(none registered)"
            raise ValueError(
                f"Unknown storage backend: '{backend}'. "
                f"Available backends: {available}"
            )

        container_class = cls._backends[backend]
        return container_class.create(**kwargs)


def get_repositories(
    backend: str | None = None,
    base_path: Path | None = None,
    history_dir: Path | None = None,
    output_dir: Path | None = None,
    **kwargs: Any,
) -> RepositoryContainer:
    """Create repositories based on storage backend configuration.

    This is the main entry point for getting repository instances. It reads
    the backend from the STORAGE_BACKEND environment variable (or uses the
    explicit parameter) and creates all repositories for that backend.

    Args:
        backend: Storage backend name. If None, reads from STORAGE_BACKEND
                 environment variable, defaulting to "filesystem".
        base_path: Base path for filesystem operations (default: current directory).
                   Used by filesystem backend for locating database.csv and chords/.
        history_dir: Path to history directory. If None, uses default from config.
        output_dir: Path to output directory. If None, uses default from config.
        **kwargs: Additional backend-specific configuration (e.g., database_url
                  for postgres backend).

    Returns:
        RepositoryContainer with all repository instances

    Examples:
        # Use default filesystem backend
        >>> repos = get_repositories()
        >>> songs = repos.songs.get_all()

        # Explicit filesystem with custom paths
        >>> repos = get_repositories(
        ...     backend="filesystem",
        ...     base_path=Path("/data/songs"),
        ...     history_dir=Path("/data/history"),
        ... )

        # Future: PostgreSQL backend
        >>> repos = get_repositories(
        ...     backend="postgres",
        ...     database_url="postgresql://user:pass@host/db",
        ... )
    """
    # Determine backend
    if backend is None:
        backend = os.getenv("STORAGE_BACKEND", "filesystem")

    # Set up common filesystem paths if not provided
    if base_path is None:
        base_path = Path.cwd()

    # Pass paths to kwargs for filesystem backend
    kwargs["base_path"] = base_path
    if history_dir is not None:
        kwargs["history_dir"] = history_dir
    if output_dir is not None:
        kwargs["output_dir"] = output_dir

    return RepositoryFactory.create(backend, **kwargs)


# Register filesystem backend on module import
# This ensures the default backend is always available
def _register_filesystem_backend() -> None:
    """Register the filesystem backend implementation."""
    try:
        from .filesystem import FilesystemRepositoryContainer

        RepositoryFactory.register("filesystem", FilesystemRepositoryContainer)
    except ModuleNotFoundError:
        # Filesystem module not yet created - will be registered when available
        # Using ModuleNotFoundError (not ImportError) to avoid masking real errors
        # like syntax errors or missing dependencies within the module
        pass


_register_filesystem_backend()
