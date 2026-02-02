"""Path resolution utilities for output and history directories.

This module provides centralized path resolution with multi-layer configuration:
1. CLI arguments (highest priority)
2. Environment variables
3. Config defaults (from config.py)
4. Hardcoded fallbacks

Example:
    >>> from pathlib import Path
    >>> paths = get_output_paths(Path("."))
    >>> print(paths.output_dir)  # Path("output")
    >>> print(paths.history_dir)  # Path("history")
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PathConfig:
    """Configuration for output and history paths.

    Attributes:
        output_dir: Directory for markdown setlist files
        history_dir: Directory for JSON history tracking files
    """
    output_dir: Path
    history_dir: Path


def get_output_paths(
    base_path: Path,
    cli_output_dir: str | None = None,
    cli_history_dir: str | None = None
) -> PathConfig:
    """Resolve output paths with priority: CLI > ENV > config > defaults.

    Configuration priority (highest to lowest):
    1. CLI arguments (cli_output_dir, cli_history_dir)
    2. Environment variables (SETLIST_OUTPUT_DIR, SETLIST_HISTORY_DIR)
    3. Config defaults (DEFAULT_OUTPUT_DIR, DEFAULT_HISTORY_DIR from config.py)
    4. Hardcoded fallbacks ("output", "history")

    Args:
        base_path: Project root directory (usually Path("."))
        cli_output_dir: Optional CLI argument for output directory
        cli_history_dir: Optional CLI argument for history directory

    Returns:
        PathConfig with resolved absolute paths for output and history directories

    Examples:
        # Use defaults
        >>> paths = get_output_paths(Path("."))

        # Use CLI arguments
        >>> paths = get_output_paths(Path("."), "custom/out", "custom/hist")

        # Use environment variables (CLI args are None)
        >>> os.environ["SETLIST_OUTPUT_DIR"] = "/data/output"
        >>> paths = get_output_paths(Path("."))
    """
    # Priority 1: CLI arguments (both must be provided to use this layer)
    if cli_output_dir is not None and cli_history_dir is not None:
        return PathConfig(
            output_dir=Path(cli_output_dir).resolve(),
            history_dir=Path(cli_history_dir).resolve()
        )

    # Priority 2: Environment variables (both must be set to use this layer)
    env_output = os.getenv("SETLIST_OUTPUT_DIR")
    env_history = os.getenv("SETLIST_HISTORY_DIR")
    if env_output and env_history:
        return PathConfig(
            output_dir=Path(env_output).resolve(),
            history_dir=Path(env_history).resolve()
        )

    # Priority 3 & 4: Config defaults with fallback
    try:
        from .config import DEFAULT_OUTPUT_DIR, DEFAULT_HISTORY_DIR
        output_dir = DEFAULT_OUTPUT_DIR
        history_dir = DEFAULT_HISTORY_DIR
    except (ImportError, AttributeError):
        # Fallback if config doesn't have these constants
        output_dir = "output"
        history_dir = "history"

    return PathConfig(
        output_dir=(base_path / output_dir).resolve(),
        history_dir=(base_path / history_dir).resolve()
    )
