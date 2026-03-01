"""Core setlist generation logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import MOMENTS_CONFIG, GenerationConfig
from .event_type import filter_songs_for_event_type
from .models import Song, Setlist
from .ordering import apply_energy_ordering
from .selector import calculate_recency_scores, select_songs_for_moment

if TYPE_CHECKING:
    from .observability import Observability
    from .repositories.protocols import SongRepository, HistoryRepository, ConfigRepository


class SetlistGenerator:
    """
    Orchestrates setlist generation with internal state management.

    This class encapsulates the stateful operations of setlist generation,
    managing recency scores and tracking already-selected songs internally.

    Example:
        >>> from library import get_repositories, SetlistGenerator
        >>> repos = get_repositories()
        >>> generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
        >>> setlist = generator.generate("2026-02-15", overrides={"louvor": ["Oceanos"]})
        >>> repos.history.save(setlist)
    """

    def __init__(
        self,
        songs: dict[str, Song],
        history: list[dict],
        obs: Observability | None = None,
        config: GenerationConfig | None = None,
    ):
        """
        Initialize generator with songs and history.

        Args:
            songs: Dictionary of available songs
            history: List of historical setlists
            obs: Observability container (defaults to noop)
            config: Generation config (defaults to GenerationConfig.from_defaults())
        """
        from .observability import Observability as _Obs

        self.songs = songs
        self.history = history
        self.obs = obs or _Obs.noop()
        self.config = config or GenerationConfig.from_defaults()
        self._recency_scores: dict[str, float] = {}
        self._already_selected: set[str] = set()
        self._moments: dict[str, list[str]] = {}

    @classmethod
    def from_repositories(
        cls,
        songs_repo: SongRepository,
        history_repo: HistoryRepository,
        obs: Observability | None = None,
        config_repo: ConfigRepository | None = None,
    ) -> SetlistGenerator:
        """
        Create a generator from repository instances.

        This is the recommended way to create a generator when using the
        repository pattern. It automatically extracts the data from the
        repositories.

        Args:
            songs_repo: Repository providing song data
            history_repo: Repository providing history data
            obs: Observability container (defaults to noop)
            config_repo: Optional config repository for per-org config overrides

        Returns:
            SetlistGenerator instance initialized with repository data

        Example:
            >>> repos = get_repositories()
            >>> generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
            >>> setlist = generator.generate("2026-02-15")
        """
        songs = songs_repo.get_all()
        history = history_repo.get_all()
        config = GenerationConfig.from_config_repo(config_repo) if config_repo else None
        return cls(songs, history, obs=obs, config=config)

    def generate(
        self,
        date: str,
        overrides: dict[str, list[str]] | None = None,
        label: str = "",
        event_type: str = "",
        moments_config: dict[str, int] | None = None,
    ) -> Setlist:
        """
        Generate a complete setlist for all moments.

        Args:
            date: Date for this setlist
            overrides: Optional manual song overrides per moment
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug for song filtering
            moments_config: Optional moments configuration override
                (defaults to MOMENTS_CONFIG)

        Returns:
            Setlist object with selected songs
        """
        effective_moments = moments_config or self.config.moments_config

        # Filter songs by event type if specified
        available = filter_songs_for_event_type(self.songs, event_type) if event_type else self.songs

        with self.obs.tracer.span("generate_setlist", date=date):
            self.obs.logger.info("Generating setlist", date=date, songs=len(available))

            with self.obs.metrics.timer("generate_duration"):
                # Calculate recency scores using ALL history (global recency)
                self._recency_scores = calculate_recency_scores(
                    available,
                    self.history,
                    current_date=date,
                    recency_decay_days=self.config.recency_decay_days,
                )

                # Reset state for new generation
                self._already_selected = set()
                self._moments = {}

                # Generate songs for each moment using the event type's config
                for moment, count in effective_moments.items():
                    self._generate_moment(moment, count, overrides, available)

            self.obs.metrics.counter("setlists_generated")
            self.obs.logger.info(
                "Setlist generated",
                date=date,
                moments=len(self._moments),
            )

        return Setlist(date=date, moments=self._moments, label=label, event_type=event_type)

    def _generate_moment(
        self,
        moment: str,
        count: int,
        overrides: dict[str, list[str]] | None,
        songs: dict[str, Song] | None = None,
    ) -> None:
        """
        Select and order songs for a specific moment.

        Args:
            moment: The moment name (e.g., "louvor", "prelúdio")
            count: Number of songs needed
            overrides: Optional manual song overrides per moment
            songs: Available songs (defaults to self.songs)
        """
        available = songs if songs is not None else self.songs
        moment_overrides = overrides.get(moment) if overrides else None
        override_count = len(moment_overrides) if moment_overrides else 0

        # Select songs using scoring algorithm
        selected_with_energy = select_songs_for_moment(
            moment,
            count,
            available,
            self._recency_scores,
            self._already_selected,  # Mutated internally
            moment_overrides
        )

        # Apply energy-based ordering (preserves override order)
        ordered_songs = apply_energy_ordering(
            moment,
            selected_with_energy,
            override_count,
            energy_ordering_enabled=self.config.energy_ordering_enabled,
            energy_ordering_rules=self.config.energy_ordering_rules,
        )
        self._moments[moment] = ordered_songs
        self.obs.logger.debug(
            "Moment generated", moment=moment, songs=len(ordered_songs),
        )


def generate_setlist(
    songs: dict[str, Song],
    history: list[dict],
    date: str,
    overrides: dict[str, list[str]] | None = None,
    obs: Any = None,
    label: str = "",
    event_type: str = "",
    moments_config: dict[str, int] | None = None,
    config: GenerationConfig | None = None,
) -> Setlist:
    """
    Generate a complete setlist for all moments.

    This is a backward-compatible functional wrapper around SetlistGenerator.
    For new code, consider using SetlistGenerator directly for better state management.

    Args:
        songs: Dictionary of available songs
        history: List of historical setlists
        date: Date for this setlist
        overrides: Optional manual song overrides per moment
        obs: Observability container (defaults to noop)
        label: Optional label for multiple setlists per date
        event_type: Optional event type slug for song filtering
        moments_config: Optional moments configuration override
        config: Generation config (defaults to GenerationConfig.from_defaults())

    Returns:
        Setlist object with selected songs
    """
    generator = SetlistGenerator(songs, history, obs=obs, config=config)
    return generator.generate(
        date, overrides, label=label,
        event_type=event_type, moments_config=moments_config,
    )
