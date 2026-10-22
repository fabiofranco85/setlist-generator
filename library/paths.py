"""Path resolution utilities for output and history directories.

This module provides centralized path resolution with multi-layer configuration,
applied to each directory on its own:
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

    Each directory is resolved on its own, so ``--output-dir`` works without
    ``--history-dir``. That matters on the postgres backend, where history
    lives in the database and there is no history directory to pass.

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
    # Priority 3 & 4: Config defaults with fallback
    try:
        from .config import DEFAULT_OUTPUT_DIR, DEFAULT_HISTORY_DIR
        default_output = DEFAULT_OUTPUT_DIR
        default_history = DEFAULT_HISTORY_DIR
    except (ImportError, AttributeError):
        # Fallback if config doesn't have these constants
        default_output = "output"
        default_history = "history"

    def resolve(cli_value: str | None, env_var: str, default: str) -> Path:
        # Priority 1: CLI argument
        if cli_value is not None:
            return Path(cli_value).resolve()
        # Priority 2: Environment variable
        env_value = os.getenv(env_var)
        if env_value:
            return Path(env_value).resolve()
        return (base_path / default).resolve()

    return PathConfig(
        output_dir=resolve(cli_output_dir, "SETLIST_OUTPUT_DIR", default_output),
        history_dir=resolve(cli_history_dir, "SETLIST_HISTORY_DIR", default_history),
    )
