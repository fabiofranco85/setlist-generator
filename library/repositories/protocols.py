"""Repository protocol definitions for data access abstraction.

This module defines the interfaces (protocols) that all repository implementations
must follow. Using Protocol enables structural subtyping - any class that implements
the required methods satisfies the protocol without explicit inheritance.

Backends:
- Filesystem (default): CSV + JSON files (current behavior)
- PostgreSQL/Supabase: SQL database
- S3: Object storage for chord files and outputs (cloud)
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# SaaS-layer protocols (multi-tenant extensions)
# ---------------------------------------------------------------------------


@runtime_checkable
class MultiTenantSongRepository(SongRepository, Protocol):
    """Extended song repository with multi-tenant visibility and sharing.

    Builds on SongRepository with layered visibility (global/org/user),
    song forking, and sharing workflows. UUID identity is internal —
    the public API uses song titles at the boundary.
    """

    def get_effective_library(self) -> dict[str, Song]:
        """Get the merged song library visible to the current user.

        Merges global, org-level, and user-level songs with priority:
        user > org > global (higher visibility overrides lower).

        Returns:
            Dictionary mapping song titles to Song objects
        """
        ...

    def create(self, song: Song, visibility: str = "user") -> str:
        """Create a new song.

        Args:
            song: Song object to create
            visibility: Visibility level ('global', 'org', 'user')

        Returns:
            Title of the created song

        Raises:
            ValueError: If a song with the same title already exists
                at the same visibility scope
        """
        ...

    def delete(self, title: str) -> None:
        """Delete a song.

        Args:
            title: Song title to delete

        Raises:
            KeyError: If song doesn't exist
            PermissionError: If user doesn't own the song
        """
        ...

    def fork(self, title: str, overrides: dict) -> str:
        """Fork an existing song with modifications.

        Creates a user-level copy of a song with optional overrides
        (e.g., different key, modified chords). Sets parent_id to
        the source song.

        Args:
            title: Title of the song to fork
            overrides: Fields to override in the fork

        Returns:
            Title of the forked song

        Raises:
            KeyError: If source song doesn't exist
        """
        ...

    def share_to_org(self, title: str) -> None:
        """Promote a user-level song to org visibility.

        Args:
            title: Song title to share

        Raises:
            KeyError: If song doesn't exist
            PermissionError: If user doesn't own the song
            ValueError: If song is not user-level
        """
        ...

    def request_global_share(self, title: str) -> str:
        """Submit a request to promote a song to global visibility.

        Creates a share request that must be approved by a system admin.

        Args:
            title: Song title to request global sharing for

        Returns:
            Share request ID

        Raises:
            KeyError: If song doesn't exist
            ValueError: If song is already global
        """
        ...


@runtime_checkable
class ShareRequestRepository(Protocol):
    """Repository for managing song share requests.

    Share requests flow: user submits -> system admin reviews -> approve/reject.
    """

    def submit(self, song_title: str) -> str:
        """Submit a share request for global visibility.

        Args:
            song_title: Title of the song to share globally

        Returns:
            Request ID
        """
        ...

    def list_pending(self) -> list[dict]:
        """List all pending share requests.

        Returns:
            List of request dicts with keys: id, song_title, org_name,
            requested_by, created_at
        """
        ...

    def approve(self, request_id: str) -> None:
        """Approve a share request, promoting the song to global.

        Args:
            request_id: ID of the request to approve

        Raises:
            KeyError: If request doesn't exist
            ValueError: If request is not pending
        """
        ...

    def reject(self, request_id: str, reason: str) -> None:
        """Reject a share request.

        Args:
            request_id: ID of the request to reject
            reason: Explanation for the rejection

        Raises:
            KeyError: If request doesn't exist
            ValueError: If request is not pending
        """
        ...


@runtime_checkable
class UserRepository(Protocol):
    """Repository for user and organization membership management."""

    def get_user_orgs(self, user_id: str) -> list[dict]:
        """Get all organizations a user belongs to.

        Args:
            user_id: User UUID

        Returns:
            List of dicts with keys: org_id, org_name, org_slug, role
        """
        ...

    def get_org_members(self, org_id: str) -> list[dict]:
        """Get all members of an organization.

        Args:
            org_id: Organization UUID

        Returns:
            List of dicts with keys: user_id, email, role
        """
        ...

    def get_user_role(self, user_id: str, org_id: str) -> str | None:
        """Get a user's role in an organization.

        Args:
            user_id: User UUID
            org_id: Organization UUID

        Returns:
            Role string ('org_admin', 'editor', 'viewer') or None if not a member
        """
        ...

    def is_system_admin(self, user_id: str) -> bool:
        """Check if a user is a system administrator.

        Args:
            user_id: User UUID

        Returns:
            True if user is a system admin
        """
        ...


@runtime_checkable
class CloudOutputRepository(Protocol):
    """S3-compatible output repository returning URLs instead of Paths.

    Used in SaaS deployments where output files (markdown, PDF, chord content)
    are stored in object storage rather than the local filesystem.
    """

    def save_markdown(self, date: str, content: str, label: str = "", event_type: str = "") -> str:
        """Save setlist markdown to cloud storage.

        Args:
            date: Setlist date
            content: Markdown content
            label: Optional label
            event_type: Optional event type slug

        Returns:
            URL or key of the saved object
        """
        ...

    def save_pdf_bytes(self, date: str, pdf_bytes: bytes, label: str = "", event_type: str = "") -> str:
        """Save PDF bytes to cloud storage.

        Args:
            date: Setlist date
            pdf_bytes: PDF file content as bytes
            label: Optional label
            event_type: Optional event type slug

        Returns:
            URL or key of the saved object
        """
        ...

    def get_markdown_url(self, date: str, label: str = "", event_type: str = "") -> str | None:
        """Get URL for a stored markdown file.

        Returns:
            Presigned URL or None if not found
        """
        ...

    def get_pdf_url(self, date: str, label: str = "", event_type: str = "") -> str | None:
        """Get URL for a stored PDF file.

        Returns:
            Presigned URL or None if not found
        """
        ...

    def save_chord_content(self, song_id: str, content: str) -> str:
        """Save chord content to cloud storage.

        Args:
            song_id: Song identifier (UUID in Supabase)
            content: Chord markdown content

        Returns:
            S3 key of the saved object
        """
        ...

    def get_chord_content(self, song_id: str) -> str | None:
        """Get chord content from cloud storage.

        Args:
            song_id: Song identifier

        Returns:
            Chord content string or None if not found
        """
        ...

    def delete_outputs(self, date: str, label: str = "", event_type: str = "") -> int:
        """Delete output files from cloud storage.

        Args:
            date: Setlist date
            label: Optional label
            event_type: Optional event type slug

        Returns:
            Number of objects deleted
        """
        ...
