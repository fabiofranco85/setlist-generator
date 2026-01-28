"""Data models for songs and setlists."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Song:
    """Represents a song with its metadata."""
    title: str
    tags: Dict[str, int]  # {moment: weight}
    energy: float
    content: str  # Chord sheet content

    def get_weight(self, moment: str) -> int:
        """Get weight for a specific moment."""
        return self.tags.get(moment, 0)

    def has_moment(self, moment: str) -> bool:
        """Check if song is tagged for a moment."""
        return moment in self.tags


@dataclass
class Setlist:
    """Represents a generated setlist."""
    date: str
    moments: Dict[str, list[str]]  # {moment: [song_titles]}

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date,
            "moments": self.moments
        }
