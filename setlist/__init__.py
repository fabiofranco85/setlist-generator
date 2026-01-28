"""Setlist generation package for church services."""

from .config import (
    DEFAULT_ENERGY,
    DEFAULT_HISTORY_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_WEIGHT,
    ENERGY_ORDERING_ENABLED,
    ENERGY_ORDERING_RULES,
    MOMENTS_CONFIG,
    RECENCY_PENALTY_PERFORMANCES,
)
from .formatter import format_setlist_markdown, save_setlist_history
from .generator import SetlistGenerator, generate_setlist
from .loader import load_history, load_songs
from .models import Setlist, Song
from .paths import PathConfig, get_output_paths

__all__ = [
    # Configuration
    "MOMENTS_CONFIG",
    "DEFAULT_WEIGHT",
    "RECENCY_PENALTY_PERFORMANCES",
    "ENERGY_ORDERING_ENABLED",
    "ENERGY_ORDERING_RULES",
    "DEFAULT_ENERGY",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_HISTORY_DIR",
    # Models
    "Song",
    "Setlist",
    # Core functions
    "load_songs",
    "load_history",
    "generate_setlist",
    "format_setlist_markdown",
    "save_setlist_history",
    # Classes
    "SetlistGenerator",
    # Path utilities
    "PathConfig",
    "get_output_paths",
]
