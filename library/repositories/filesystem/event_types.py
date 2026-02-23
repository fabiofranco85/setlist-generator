"""Filesystem implementation of EventTypeRepository.

This module provides event type management using a JSON file:
- event_types.json at the project root
- Creates default file on first access if missing
"""

from pathlib import Path

from ...event_type import (
    DEFAULT_EVENT_TYPE_SLUG,
    EventType,
    create_default_event_types,
    load_event_types,
    save_event_types,
)


class FilesystemEventTypeRepository:
    """Event type repository backed by a JSON file.

    Storage format:
    - event_types.json: {"event_types": {"slug": {"name": ..., "moments": ...}}}

    Attributes:
        _file_path: Path to event_types.json
    """

    def __init__(self, base_path: Path):
        """Initialize repository with base path.

        Args:
            base_path: Project root directory containing event_types.json
        """
        self._file_path = base_path / "event_types.json"
        self._cache: dict[str, EventType] | None = None

    def _ensure_loaded(self) -> dict[str, EventType]:
        """Load event types, creating default file if missing."""
        if self._cache is None:
            self._cache = load_event_types(self._file_path)
            if not self._file_path.exists():
                save_event_types(self._cache, self._file_path)
        return self._cache

    def _invalidate_cache(self) -> None:
        """Clear cache, forcing reload on next access."""
        self._cache = None

    def get_all(self) -> dict[str, EventType]:
        """Get all event types indexed by slug."""
        return dict(self._ensure_loaded())

    def get(self, slug: str) -> EventType | None:
        """Get a single event type by slug."""
        return self._ensure_loaded().get(slug)

    def get_default_slug(self) -> str:
        """Get the default event type slug."""
        return DEFAULT_EVENT_TYPE_SLUG

    def add(self, event_type: EventType) -> None:
        """Add a new event type.

        Raises:
            ValueError: If slug already exists
        """
        data = self._ensure_loaded()
        if event_type.slug in data:
            raise ValueError(f"Event type '{event_type.slug}' already exists")

        data[event_type.slug] = event_type
        save_event_types(data, self._file_path)
        self._invalidate_cache()

    def update(self, slug: str, **kwargs) -> None:
        """Update an existing event type.

        Raises:
            KeyError: If event type doesn't exist
        """
        data = self._ensure_loaded()
        if slug not in data:
            raise KeyError(f"Event type '{slug}' not found")

        et = data[slug]
        if "name" in kwargs:
            et.name = kwargs["name"]
        if "description" in kwargs:
            et.description = kwargs["description"]
        if "moments" in kwargs:
            et.moments = kwargs["moments"]

        save_event_types(data, self._file_path)
        self._invalidate_cache()

    def remove(self, slug: str) -> None:
        """Remove an event type.

        Raises:
            KeyError: If event type doesn't exist
            ValueError: If trying to remove the default type
        """
        if slug == DEFAULT_EVENT_TYPE_SLUG:
            raise ValueError("Cannot remove the default event type")

        data = self._ensure_loaded()
        if slug not in data:
            raise KeyError(f"Event type '{slug}' not found")

        del data[slug]
        save_event_types(data, self._file_path)
        self._invalidate_cache()
