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
    youtube_url: str = ""  # Optional YouTube video URL

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
    label: str = ""

    @property
    def setlist_id(self) -> str:
        """Unique identifier combining date and optional label.

        Returns:
            "{date}_{label}" if label is set, otherwise just "{date}"
        """
        if self.label:
            return f"{self.date}_{self.label}"
        return self.date

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = {
            "date": self.date,
            "moments": self.moments,
        }
        if self.label:
            d["label"] = self.label
        return d
