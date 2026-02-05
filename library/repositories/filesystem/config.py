"""Filesystem implementation of ConfigRepository.

This module provides configuration access by reading from library/config.py.
For the filesystem backend, configuration is stored as Python constants.
"""

from ...config import (
    MOMENTS_CONFIG,
    RECENCY_DECAY_DAYS,
    DEFAULT_WEIGHT,
    ENERGY_ORDERING_RULES,
    ENERGY_ORDERING_ENABLED,
    DEFAULT_ENERGY,
)


class FilesystemConfigRepository:
    """Config repository backed by Python constants.

    For the filesystem backend, configuration is defined in library/config.py
    as module-level constants. This repository provides a protocol-compliant
    interface to access those values.

    In database backends, this would read from a config table, enabling
    per-organization customization (e.g., different moments for different churches).
    """

    def get_moments_config(self) -> dict[str, int]:
        """Get service moments configuration.

        Returns:
            Dictionary mapping moment names to song counts
            Example: {"louvor": 4, "prelúdio": 1, ...}
        """
        return dict(MOMENTS_CONFIG)

    def get_recency_decay_days(self) -> int:
        """Get recency decay constant in days.

        Returns:
            Number of days for exponential decay calculation (default: 45)
        """
        return RECENCY_DECAY_DAYS

    def get_default_weight(self) -> int:
        """Get default tag weight.

        Returns:
            Default weight for tags without explicit weight (default: 3)
        """
        return DEFAULT_WEIGHT

    def get_energy_ordering_rules(self) -> dict[str, str]:
        """Get energy ordering rules per moment.

        Returns:
            Dictionary mapping moment names to ordering direction
            Example: {"louvor": "ascending"}
        """
        return dict(ENERGY_ORDERING_RULES)

    def is_energy_ordering_enabled(self) -> bool:
        """Check if energy ordering is enabled.

        Returns:
            True if energy ordering should be applied, False otherwise
        """
        return ENERGY_ORDERING_ENABLED

    def get_default_energy(self) -> float:
        """Get default energy for songs without energy metadata.

        Returns:
            Default energy value (typically 2.5)
        """
        return DEFAULT_ENERGY
