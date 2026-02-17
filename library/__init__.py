"""Setlist generation package for church services."""

from .config import (
    DEFAULT_ENERGY,
    DEFAULT_HISTORY_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_WEIGHT,
    ENERGY_ORDERING_ENABLED,
    ENERGY_ORDERING_RULES,
    MOMENTS_CONFIG,
    RECENCY_DECAY_DAYS,
)
from .formatter import format_setlist_markdown
from .labeler import relabel_setlist
from .generator import SetlistGenerator, generate_setlist
from .loader import parse_tags
from .selector import (
    calculate_recency_scores,
    get_days_since_last_use,
    get_song_usage_history,
)
from .models import Setlist, Song
from .paths import PathConfig, get_output_paths
from .pdf_formatter import generate_setlist_pdf
from .replacer import (
    derive_setlist,
    find_target_setlist,
    replace_song_in_setlist,
    replace_songs_batch,
    select_replacement_song,
    validate_replacement_request,
)
from .transposer import (
    calculate_semitones,
    resolve_target_key,
    should_use_flats,
    transpose_content,
)
from .youtube import (
    create_setlist_playlist,
    extract_video_id,
    format_playlist_name,
    resolve_setlist_videos,
)
from .repositories import (
    get_repositories,
    RepositoryContainer,
    RepositoryFactory,
    # Protocols
    SongRepository,
    HistoryRepository,
    ConfigRepository,
    OutputRepository,
    # Filesystem implementations
    FilesystemRepositoryContainer,
    FilesystemSongRepository,
    FilesystemHistoryRepository,
    FilesystemConfigRepository,
    FilesystemOutputRepository,
)
# Conditionally import PostgreSQL implementations
try:
    from .repositories.postgres import (
        PostgresRepositoryContainer,
        PostgresSongRepository,
        PostgresHistoryRepository,
        PostgresConfigRepository,
    )

    _has_postgres = True
except ImportError:
    _has_postgres = False
from .observability import (
    Observability,
    LoggerPort,
    MetricsPort,
    TracerPort,
    Span,
    NullLogger,
    NullMetrics,
    NullTracer,
    NullSpan,
)

__all__ = [
    # Configuration
    "MOMENTS_CONFIG",
    "DEFAULT_WEIGHT",
    "RECENCY_DECAY_DAYS",
    "ENERGY_ORDERING_ENABLED",
    "ENERGY_ORDERING_RULES",
    "DEFAULT_ENERGY",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_HISTORY_DIR",
    # Models
    "Song",
    "Setlist",
    # Labeler
    "relabel_setlist",
    # Core functions
    "parse_tags",
    "calculate_recency_scores",
    "get_song_usage_history",
    "get_days_since_last_use",
    "generate_setlist",
    "format_setlist_markdown",
    "generate_setlist_pdf",
    # Classes
    "SetlistGenerator",
    # Path utilities
    "PathConfig",
    "get_output_paths",
    # Replacement functions
    "derive_setlist",
    "find_target_setlist",
    "select_replacement_song",
    "replace_song_in_setlist",
    "replace_songs_batch",
    "validate_replacement_request",
    # Transposition
    "transpose_content",
    "calculate_semitones",
    "should_use_flats",
    "resolve_target_key",
    # YouTube integration
    "extract_video_id",
    "format_playlist_name",
    "resolve_setlist_videos",
    "create_setlist_playlist",
    # Repository pattern
    "get_repositories",
    "RepositoryContainer",
    "RepositoryFactory",
    # Repository protocols
    "SongRepository",
    "HistoryRepository",
    "ConfigRepository",
    "OutputRepository",
    # Filesystem repositories
    "FilesystemRepositoryContainer",
    "FilesystemSongRepository",
    "FilesystemHistoryRepository",
    "FilesystemConfigRepository",
    "FilesystemOutputRepository",
]

if _has_postgres:
    __all__ += [
        # PostgreSQL repositories
        "PostgresRepositoryContainer",
        "PostgresSongRepository",
        "PostgresHistoryRepository",
        "PostgresConfigRepository",
    ]

__all__ += [
    # Observability
    "Observability",
    "LoggerPort",
    "MetricsPort",
    "TracerPort",
    "Span",
    "NullLogger",
    "NullMetrics",
    "NullTracer",
    "NullSpan",
]
