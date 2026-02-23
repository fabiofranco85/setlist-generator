"""Event type management for supporting multiple service configurations.

An event type defines a distinct kind of service (e.g., Main, Youth, Christmas)
with its own moments configuration. Songs can optionally be bound to specific
event types; unbound songs are available for all types.

Event types are stored in event_types.json at the project root.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import MOMENTS_CONFIG

DEFAULT_EVENT_TYPE_SLUG = "main"
DEFAULT_EVENT_TYPE_NAME = "Main Event"

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class EventType:
    """Represents a service event type with its own moments configuration."""

    slug: str
    name: str
    description: str = ""
    moments: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if not self.moments:
            self.moments = dict(MOMENTS_CONFIG)


def validate_event_type_slug(slug: str) -> str:
    """Validate and normalize an event type slug.

    Slugs must be lowercase alphanumeric with hyphens, 1-30 chars,
    starting with a letter or digit.

    Args:
        slug: Slug string to validate

    Returns:
        Validated slug string

    Raises:
        ValueError: If slug is invalid
    """
    slug = slug.strip().lower()

    if not slug:
        raise ValueError("Event type slug cannot be empty")

    if len(slug) > 30:
        raise ValueError("Event type slug must be at most 30 characters")

    if not _SLUG_PATTERN.match(slug):
        raise ValueError(
            f"Invalid event type slug '{slug}'. "
            "Slugs must start with a letter or digit and contain only "
            "lowercase letters, digits, and hyphens."
        )

    return slug


def is_default_event_type(slug: str) -> bool:
    """Check if a slug refers to the default event type."""
    return slug == DEFAULT_EVENT_TYPE_SLUG or slug == ""


def filter_songs_for_event_type(songs: dict, slug: str) -> dict:
    """Filter songs available for a given event type.

    Unbound songs (empty event_types list) are available for ALL event types.
    Bound songs are only available for their listed event types.

    Args:
        songs: Dictionary mapping song titles to Song objects
        slug: Event type slug to filter for

    Returns:
        Filtered dictionary of available songs
    """
    return {
        title: song
        for title, song in songs.items()
        if song.is_available_for_event_type(slug)
    }


def load_event_types(path: Path) -> dict[str, EventType]:
    """Load event types from a JSON file.

    Args:
        path: Path to event_types.json

    Returns:
        Dictionary mapping slugs to EventType objects
    """
    if not path.exists():
        return create_default_event_types()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = {}
    for slug, info in data.get("event_types", {}).items():
        result[slug] = EventType(
            slug=slug,
            name=info.get("name", slug),
            description=info.get("description", ""),
            moments=info.get("moments", dict(MOMENTS_CONFIG)),
        )

    return result


def save_event_types(event_types: dict[str, EventType], path: Path) -> None:
    """Save event types to a JSON file.

    Args:
        event_types: Dictionary mapping slugs to EventType objects
        path: Path to event_types.json
    """
    data = {"event_types": {}}
    for slug, et in event_types.items():
        data["event_types"][slug] = {
            "name": et.name,
            "description": et.description,
            "moments": et.moments,
        }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_default_event_types() -> dict[str, EventType]:
    """Create the default event types structure.

    Returns:
        Dictionary with just the default event type
    """
    return {
        DEFAULT_EVENT_TYPE_SLUG: EventType(
            slug=DEFAULT_EVENT_TYPE_SLUG,
            name=DEFAULT_EVENT_TYPE_NAME,
            description="Default service configuration",
            moments=dict(MOMENTS_CONFIG),
        )
    }
