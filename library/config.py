"""Configuration constants for setlist generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repositories.protocols import ConfigRepository

# Service moments configuration
MOMENTS_CONFIG = {
    "prelúdio": 1,
    "ofertório": 1,
    "saudação": 1,
    "crianças": 1,
    "louvor": 4,
    "poslúdio": 1,
}

# Selection algorithm parameters
DEFAULT_WEIGHT = 3
RECENCY_DECAY_DAYS = 45  # Days for a song to feel "fresh" again (time-based decay)

# Energy ordering configuration
ENERGY_ORDERING_ENABLED = True  # Master switch to enable/disable feature
ENERGY_ORDERING_RULES = {
    "louvor": "ascending",  # 1→4 (upbeat to worship)
    # Future: "ofertório": "descending", etc.
}
DEFAULT_ENERGY = 2.5  # Default for songs without energy metadata

# Output path configuration
DEFAULT_OUTPUT_DIR = "output"      # Markdown setlists directory
DEFAULT_HISTORY_DIR = "history"    # JSON tracking directory

# Environment variable names (for documentation)
ENV_OUTPUT_DIR = "SETLIST_OUTPUT_DIR"
ENV_HISTORY_DIR = "SETLIST_HISTORY_DIR"

def canonical_moment_order(
    moments: dict,
    reference_config: dict[str, int] | None = None,
) -> list[str]:
    """Return moment keys in canonical display order.

    Moments in reference_config appear in that order.
    Extra moments (from custom event types) appended alphabetically.

    Args:
        moments: Dictionary of moments to order
        reference_config: Reference config for ordering (defaults to MOMENTS_CONFIG)
    """
    ref = reference_config if reference_config is not None else MOMENTS_CONFIG
    ordered = [m for m in ref if m in moments]
    extra = sorted(m for m in moments if m not in ref)
    return ordered + extra


@dataclass(frozen=True)
class GenerationConfig:
    """Immutable configuration bundle for setlist generation.

    Encapsulates all config values needed by the generation pipeline,
    enabling per-org overrides in a multi-tenant SaaS context while
    preserving backward compatibility via from_defaults().
    """

    moments_config: dict[str, int]
    recency_decay_days: int = RECENCY_DECAY_DAYS
    default_weight: int = DEFAULT_WEIGHT
    energy_ordering_enabled: bool = ENERGY_ORDERING_ENABLED
    energy_ordering_rules: dict[str, str] = field(
        default_factory=lambda: dict(ENERGY_ORDERING_RULES)
    )
    default_energy: float = DEFAULT_ENERGY

    @classmethod
    def from_defaults(cls) -> GenerationConfig:
        """Create config from module-level defaults.

        This preserves the current behavior for CLI and standalone usage.
        """
        return cls(moments_config=dict(MOMENTS_CONFIG))

    @classmethod
    def from_config_repo(cls, repo: ConfigRepository) -> GenerationConfig:
        """Create config from a ConfigRepository.

        Reads all values from the repository, enabling per-org overrides
        in database-backed deployments.

        Args:
            repo: ConfigRepository providing config values
        """
        return cls(
            moments_config=repo.get_moments_config(),
            recency_decay_days=repo.get_recency_decay_days(),
            default_weight=repo.get_default_weight(),
            energy_ordering_enabled=repo.is_energy_ordering_enabled(),
            energy_ordering_rules=repo.get_energy_ordering_rules(),
            default_energy=repo.get_default_energy(),
        )


# YouTube integration
YOUTUBE_PLAYLIST_NAME_PATTERN = "Culto {DD.MM.YY}"
YOUTUBE_PLAYLIST_PRIVACY = "unlisted"
YOUTUBE_CLIENT_SECRETS_FILE = "client_secrets.json"
YOUTUBE_TOKEN_FILE = ".youtube_token.json"
