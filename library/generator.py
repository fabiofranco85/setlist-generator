"""Core setlist generation logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import MOMENTS_CONFIG
from .models import Song, Setlist
from .ordering import apply_energy_ordering
from .selector import calculate_recency_scores, select_songs_for_moment

if TYPE_CHECKING:
    from .observability import Observability
    from .repositories.protocols import SongRepository, HistoryRepository


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
    ):
        """
        Initialize generator with songs and history.

        Args:
            songs: Dictionary of available songs
            history: List of historical setlists
            obs: Observability container (defaults to noop)
        """
        from .observability import Observability as _Obs

        self.songs = songs
        self.history = history
        self.obs = obs or _Obs.noop()
        self._recency_scores: dict[str, float] = {}
        self._already_selected: set[str] = set()
        self._moments: dict[str, list[str]] = {}

    @classmethod
    def from_repositories(
        cls,
        songs_repo: SongRepository,
        history_repo: HistoryRepository,
        obs: Observability | None = None,
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

        Returns:
            SetlistGenerator instance initialized with repository data

        Example:
            >>> repos = get_repositories()
            >>> generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
            >>> setlist = generator.generate("2026-02-15")
        """
        songs = songs_repo.get_all()
        history = history_repo.get_all()
        return cls(songs, history, obs=obs)

    def generate(
        self,
        date: str,
        overrides: dict[str, list[str]] | None = None
    ) -> Setlist:
        """
        Generate a complete setlist for all moments.

        Args:
            date: Date for this setlist
            overrides: Optional manual song overrides per moment

        Returns:
            Setlist object with selected songs
        """
        with self.obs.tracer.span("generate_setlist", date=date):
            self.obs.logger.info("Generating setlist", date=date, songs=len(self.songs))

            with self.obs.metrics.timer("generate_duration"):
                # Calculate recency scores using the target date
                self._recency_scores = calculate_recency_scores(
                    self.songs,
                    self.history,
                    current_date=date
                )

                # Reset state for new generation
                self._already_selected = set()
                self._moments = {}

                # Generate songs for each moment
                for moment, count in MOMENTS_CONFIG.items():
                    self._generate_moment(moment, count, overrides)

            self.obs.metrics.counter("setlists_generated")
            self.obs.logger.info(
                "Setlist generated",
                date=date,
                moments=len(self._moments),
            )

        return Setlist(date=date, moments=self._moments)

    def _generate_moment(
        self,
        moment: str,
        count: int,
        overrides: dict[str, list[str]] | None
    ) -> None:
        """
        Select and order songs for a specific moment.

        Args:
            moment: The moment name (e.g., "louvor", "prelúdio")
            count: Number of songs needed
            overrides: Optional manual song overrides per moment
        """
        moment_overrides = overrides.get(moment) if overrides else None
        override_count = len(moment_overrides) if moment_overrides else 0

        # Select songs using scoring algorithm
        selected_with_energy = select_songs_for_moment(
            moment,
            count,
            self.songs,
            self._recency_scores,
            self._already_selected,  # Mutated internally
            moment_overrides
        )

        # Apply energy-based ordering (preserves override order)
        ordered_songs = apply_energy_ordering(moment, selected_with_energy, override_count)
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

    Returns:
        Setlist object with selected songs
    """
    generator = SetlistGenerator(songs, history, obs=obs)
    return generator.generate(date, overrides)
