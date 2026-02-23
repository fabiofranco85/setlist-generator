"""Repository protocol definitions for data access abstraction.

This module defines the interfaces (protocols) that all repository implementations
must follow. Using Protocol enables structural subtyping - any class that implements
the required methods satisfies the protocol without explicit inheritance.

Backends:
- Filesystem (default): CSV + JSON files (current behavior)
- PostgreSQL/Supabase: SQL database (future)
- MongoDB: Document database (future)
- S3: Object storage for chord files (future, hybrid)
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..event_type import EventType
from ..models import Song, Setlist


@runtime_checkable
class SongRepository(Protocol):
    """Interface for song data access.

    Implementations must provide methods for reading and updating songs.
    Songs include metadata (title, energy, tags, youtube_url) and content (chords).
    """

    def get_all(self) -> dict[str, Song]:
        """Get all songs indexed by title.

        Returns:
            Dictionary mapping song titles to Song objects
        """
        ...

    def get_by_title(self, title: str) -> Song | None:
        """Get a single song by exact title match.

        Args:
            title: Song title to look up

        Returns:
            Song object if found, None otherwise
        """
        ...

    def search(self, query: str) -> list[Song]:
        """Search songs by title (case-insensitive partial match).

        Args:
            query: Search string to match against titles

        Returns:
            List of matching Song objects
        """
        ...

    def update_content(self, title: str, content: str) -> None:
        """Update a song's chord content.

        Args:
            title: Song title to update
            content: New chord content (markdown)

        Raises:
            KeyError: If song with title doesn't exist
        """
        ...

    def exists(self, title: str) -> bool:
        """Check if a song exists.

        Args:
            title: Song title to check

        Returns:
            True if song exists, False otherwise
        """
        ...


@runtime_checkable
class HistoryRepository(Protocol):
    """Interface for setlist history access.

    Implementations must provide methods for reading and writing setlist history.
    History entries are stored by date (YYYY-MM-DD format).
    """

    def get_all(self) -> list[dict]:
        """Get all historical setlists sorted by date (most recent first).

        Returns:
            List of setlist dictionaries with 'date' and 'moments' keys
        """
        ...

    def get_by_date(self, date: str, label: str = "", event_type: str = "") -> dict | None:
        """Get a setlist by date, optional label, and optional event type.

        Args:
            date: Date string in YYYY-MM-DD format
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Returns:
            Setlist dictionary if found, None otherwise
        """
        ...

    def get_latest(self) -> dict | None:
        """Get the most recent setlist.

        Returns:
            Most recent setlist dictionary, or None if no history
        """
        ...

    def save(self, setlist: Setlist) -> None:
        """Save a new setlist to history.

        Args:
            setlist: Setlist object to save

        Note:
            If a setlist with the same date/label exists, it will be overwritten.
        """
        ...

    def update(self, date: str, setlist_dict: dict, label: str = "", event_type: str = "") -> None:
        """Update an existing setlist in history.

        Args:
            date: Date string identifying the setlist
            setlist_dict: Updated setlist dictionary
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Raises:
            KeyError: If no setlist exists for the given date/label/event_type
        """
        ...

    def exists(self, date: str, label: str = "", event_type: str = "") -> bool:
        """Check if a setlist exists for a date, optional label, and event type.

        Args:
            date: Date string in YYYY-MM-DD format
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Returns:
            True if setlist exists, False otherwise
        """
        ...

    def delete(self, date: str, label: str = "", event_type: str = "") -> None:
        """Delete a setlist by date, optional label, and event type.

        Args:
            date: Date string in YYYY-MM-DD format
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Raises:
            KeyError: If no setlist exists for the given date/label/event_type
        """
        ...

    def get_by_date_all(self, date: str, event_type: str = "") -> list[dict]:
        """Get all setlists for a date (all labels) within an event type.

        Args:
            date: Date string in YYYY-MM-DD format
            event_type: Optional event type slug (empty = default type)

        Returns:
            List of setlist dictionaries for the given date,
            sorted by label (empty label first, then alphabetical)
        """
        ...


@runtime_checkable
class ConfigRepository(Protocol):
    """Interface for configuration access.

    Implementations must provide methods for reading configuration values.
    For filesystem backend, reads from config.py constants.
    For database backends, reads from config table (enables per-org customization).
    """

    def get_moments_config(self) -> dict[str, int]:
        """Get service moments configuration.

        Returns:
            Dictionary mapping moment names to song counts
            Example: {"louvor": 4, "prelúdio": 1, ...}
        """
        ...

    def get_recency_decay_days(self) -> int:
        """Get recency decay constant in days.

        Returns:
            Number of days for exponential decay calculation (default: 45)
        """
        ...

    def get_default_weight(self) -> int:
        """Get default tag weight.

        Returns:
            Default weight for tags without explicit weight (default: 3)
        """
        ...

    def get_energy_ordering_rules(self) -> dict[str, str]:
        """Get energy ordering rules per moment.

        Returns:
            Dictionary mapping moment names to ordering direction
            Example: {"louvor": "ascending"}
        """
        ...

    def is_energy_ordering_enabled(self) -> bool:
        """Check if energy ordering is enabled.

        Returns:
            True if energy ordering should be applied, False otherwise
        """
        ...

    def get_default_energy(self) -> float:
        """Get default energy for songs without energy metadata.

        Returns:
            Default energy value (typically 2.5)
        """
        ...


@runtime_checkable
class OutputRepository(Protocol):
    """Interface for output file generation.

    Implementations must provide methods for saving setlist outputs.
    Outputs include markdown files and PDF files.
    """

    def save_markdown(self, date: str, content: str, label: str = "", event_type: str = "") -> Path:
        """Save setlist as markdown file.

        Args:
            date: Setlist date (used for filename)
            content: Markdown content to save
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Returns:
            Path to the saved file
        """
        ...

    def save_pdf(self, setlist: Setlist, songs: dict[str, Song]) -> Path:
        """Generate and save setlist as PDF.

        Args:
            setlist: Setlist object with date and moments
            songs: Dictionary of songs for chord content

        Returns:
            Path to the saved PDF file
        """
        ...

    def get_markdown_path(self, date: str, label: str = "", event_type: str = "") -> Path:
        """Get the path where markdown would be saved for a date.

        Args:
            date: Setlist date
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Returns:
            Path where markdown file would be saved
        """
        ...

    def delete_outputs(self, date: str, label: str = "", event_type: str = "") -> list[Path]:
        """Delete markdown and PDF output files for a setlist.

        Args:
            date: Setlist date
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Returns:
            List of paths that were actually deleted (may be empty)
        """
        ...

    def get_pdf_path(self, date: str, label: str = "", event_type: str = "") -> Path:
        """Get the path where PDF would be saved for a date.

        Args:
            date: Setlist date
            label: Optional label for multiple setlists per date
            event_type: Optional event type slug (empty = default type)

        Returns:
            Path where PDF file would be saved
        """
        ...


@runtime_checkable
class EventTypeRepository(Protocol):
    """Interface for event type data access.

    Implementations must provide methods for CRUD operations on event types.
    Event types define different service configurations with their own moments.
    """

    def get_all(self) -> dict[str, EventType]:
        """Get all event types indexed by slug.

        Returns:
            Dictionary mapping slugs to EventType objects
        """
        ...

    def get(self, slug: str) -> EventType | None:
        """Get a single event type by slug.

        Args:
            slug: Event type slug

        Returns:
            EventType if found, None otherwise
        """
        ...

    def get_default_slug(self) -> str:
        """Get the default event type slug.

        Returns:
            The default event type slug (typically "main")
        """
        ...

    def add(self, event_type: EventType) -> None:
        """Add a new event type.

        Args:
            event_type: EventType object to add

        Raises:
            ValueError: If slug already exists
        """
        ...

    def update(self, slug: str, **kwargs) -> None:
        """Update an existing event type.

        Args:
            slug: Event type slug to update
            **kwargs: Fields to update (name, description, moments)

        Raises:
            KeyError: If event type doesn't exist
        """
        ...

    def remove(self, slug: str) -> None:
        """Remove an event type.

        Args:
            slug: Event type slug to remove

        Raises:
            KeyError: If event type doesn't exist
            ValueError: If trying to remove the default type
        """
        ...
