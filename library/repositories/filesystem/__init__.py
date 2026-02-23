"""Filesystem backend for repository pattern.

This module provides file-based implementations of all repository protocols:
- SongRepository: CSV + markdown files
- HistoryRepository: JSON files
- ConfigRepository: Python constants
- OutputRepository: Markdown + PDF files
- EventTypeRepository: JSON file

This is the default backend and maintains backward compatibility with
the original file-based storage format.
"""

from pathlib import Path
from typing import Any

from ..factory import RepositoryContainer
from ...paths import get_output_paths

from .songs import FilesystemSongRepository
from .history import FilesystemHistoryRepository
from .config import FilesystemConfigRepository
from .output import FilesystemOutputRepository
from .event_types import FilesystemEventTypeRepository


class FilesystemRepositoryContainer:
    """Factory for creating filesystem-based repositories.

    This class creates a RepositoryContainer with all repositories
    configured for filesystem storage.
    """

    @classmethod
    def create(
        cls,
        base_path: Path | None = None,
        history_dir: Path | None = None,
        output_dir: Path | None = None,
        **kwargs: Any,
    ) -> RepositoryContainer:
        """Create all repositories for filesystem backend.

        Args:
            base_path: Project root directory (default: current directory)
            history_dir: Override for history directory path
            output_dir: Override for output directory path
            **kwargs: Additional arguments (ignored for filesystem)

        Returns:
            RepositoryContainer with all filesystem repositories
        """
        if base_path is None:
            base_path = Path.cwd()

        # Use get_output_paths for consistent path resolution
        # This respects CLI args > env vars > config > defaults
        paths = get_output_paths(
            base_path,
            cli_output_dir=str(output_dir) if output_dir else None,
            cli_history_dir=str(history_dir) if history_dir else None,
        )

        return RepositoryContainer(
            songs=FilesystemSongRepository(base_path),
            history=FilesystemHistoryRepository(paths.history_dir),
            config=FilesystemConfigRepository(),
            output=FilesystemOutputRepository(paths.output_dir),
            event_types=FilesystemEventTypeRepository(base_path),
        )


__all__ = [
    "FilesystemRepositoryContainer",
    "FilesystemSongRepository",
    "FilesystemHistoryRepository",
    "FilesystemConfigRepository",
    "FilesystemOutputRepository",
    "FilesystemEventTypeRepository",
]
