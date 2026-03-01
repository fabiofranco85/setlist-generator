"""Energy-based ordering for creating emotional arcs."""

from .config import ENERGY_ORDERING_ENABLED, ENERGY_ORDERING_RULES


def apply_energy_ordering(
    moment: str,
    selected_songs: list[tuple[str, float]],
    override_count: int = 0,
    energy_ordering_enabled: bool | None = None,
    energy_ordering_rules: dict[str, str] | None = None,
) -> list[str]:
    """
    Sort songs by energy level according to moment-specific rules.
    Preserves the order of overridden songs (first override_count songs).

    Args:
        moment: The moment name (e.g., "louvor")
        selected_songs: List of (title, energy) tuples
        override_count: Number of songs at the start that were manually overridden
        energy_ordering_enabled: Whether ordering is enabled (defaults to module constant)
        energy_ordering_rules: Per-moment ordering rules (defaults to module constant)

    Returns:
        List of song titles sorted by energy (except overrides)
    """
    enabled = energy_ordering_enabled if energy_ordering_enabled is not None else ENERGY_ORDERING_ENABLED
    rules = energy_ordering_rules if energy_ordering_rules is not None else ENERGY_ORDERING_RULES

    if not enabled:
        return [title for title, _ in selected_songs]

    rule = rules.get(moment)
    if not rule:
        return [title for title, _ in selected_songs]

    # Separate overridden songs from auto-selected songs
    overridden = selected_songs[:override_count]
    auto_selected = selected_songs[override_count:]

    # Sort only auto-selected songs by energy
    if rule == "ascending":
        # Low to high: 1→2→3→4 (upbeat to worship)
        sorted_auto = sorted(auto_selected, key=lambda x: x[1])
    elif rule == "descending":
        # High to low: 4→3→2→1 (worship to upbeat)
        sorted_auto = sorted(auto_selected, key=lambda x: x[1], reverse=True)
    else:
        sorted_auto = auto_selected

    # Combine: overrides first (in original order), then sorted auto-selected
    final_songs = [title for title, _ in overridden] + [title for title, _ in sorted_auto]

    return final_songs
