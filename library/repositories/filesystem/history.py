"""Filesystem implementation of HistoryRepository.

This module provides setlist history access using JSON files:
- Each setlist is stored as history/{YYYY-MM-DD}.json
- Files contain: {"date": "YYYY-MM-DD", "moments": {"moment": ["songs"]}}
"""

import json
from pathlib import Path

from ...models import Setlist


class FilesystemHistoryRepository:
    """History repository backed by filesystem storage.

    Storage format:
    - history/{date}.json: One JSON file per setlist date
    - Format: {"date": "YYYY-MM-DD", "moments": {"moment_name": ["song1", "song2"]}}

    Attributes:
        history_dir: Directory containing history JSON files
    """

    def __init__(self, history_dir: Path):
        """Initialize repository with history directory.

        Args:
            history_dir: Directory for history JSON files
        """
        self.history_dir = history_dir
        self._history_cache: list[dict] | None = None

    def _load_history(self) -> list[dict]:
        """Load all setlist history from JSON files.

        Returns:
            List of setlist dictionaries sorted by date (most recent first)
        """
        history = []

        if not self.history_dir.exists():
            return history

        for file in self.history_dir.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                history.append(data)

        # Sort by date, most recent first
        history.sort(key=lambda x: x.get("date", ""), reverse=True)
        return history

    def _ensure_loaded(self) -> list[dict]:
        """Ensure history is loaded, using cache if available."""
        if self._history_cache is None:
            self._history_cache = self._load_history()
        return self._history_cache

    def _invalidate_cache(self) -> None:
        """Clear the internal cache, forcing a reload on next access."""
        self._history_cache = None

    def get_all(self) -> list[dict]:
        """Get all historical setlists sorted by date (most recent first).

        Returns:
            List of setlist dictionaries with 'date' and 'moments' keys
        """
        # Return a copy to prevent external mutation
        return [dict(entry) for entry in self._ensure_loaded()]

    def get_by_date(self, date: str) -> dict | None:
        """Get a setlist by date.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            Setlist dictionary if found, None otherwise
        """
        for entry in self._ensure_loaded():
            if entry.get("date") == date:
                return dict(entry)
        return None

    def get_latest(self) -> dict | None:
        """Get the most recent setlist.

        Returns:
            Most recent setlist dictionary, or None if no history
        """
        history = self._ensure_loaded()
        if history:
            return dict(history[0])
        return None

    def save(self, setlist: Setlist) -> None:
        """Save a new setlist to history.

        Args:
            setlist: Setlist object to save

        Note:
            If a setlist with the same date exists, it will be overwritten.
        """
        # Ensure directory exists
        self.history_dir.mkdir(exist_ok=True)

        # Save to file
        history_file = self.history_dir / f"{setlist.date}.json"
        data = setlist.to_dict()

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Invalidate cache since we modified data
        self._invalidate_cache()

    def update(self, date: str, setlist_dict: dict) -> None:
        """Update an existing setlist in history.

        Args:
            date: Date string identifying the setlist
            setlist_dict: Updated setlist dictionary

        Raises:
            KeyError: If no setlist exists for the given date
        """
        history_file = self.history_dir / f"{date}.json"

        if not history_file.exists():
            raise KeyError(f"No setlist found for date: {date}")

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(setlist_dict, f, ensure_ascii=False, indent=2)

        # Invalidate cache since we modified data
        self._invalidate_cache()

    def exists(self, date: str) -> bool:
        """Check if a setlist exists for a date.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            True if setlist exists, False otherwise
        """
        history_file = self.history_dir / f"{date}.json"
        return history_file.exists()

    def invalidate_cache(self) -> None:
        """Clear the internal cache, forcing a reload on next access.

        Use this if files have been modified externally.
        """
        self._invalidate_cache()
