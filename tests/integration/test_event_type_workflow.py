"""Integration tests for event type workflow.

Tests the full lifecycle: create event type, generate setlist with it,
verify filesystem routing and subdirectory structure.
"""

import pytest

from library.event_type import (
    EventType,
    DEFAULT_EVENT_TYPE_SLUG,
)
from library.models import Setlist
from library.repositories.filesystem import (
    FilesystemEventTypeRepository,
    FilesystemHistoryRepository,
    FilesystemOutputRepository,
)


@pytest.fixture()
def project_dirs(tmp_path):
    """Create minimal project directories."""
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return tmp_path, history_dir, output_dir


class TestEventTypeRepository:
    def test_creates_default_on_first_access(self, project_dirs):
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        all_types = repo.get_all()
        assert DEFAULT_EVENT_TYPE_SLUG in all_types
        assert (base / "event_types.json").exists()

    def test_add_and_get(self, project_dirs):
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        youth = EventType(slug="youth", name="Youth Service", moments={"louvor": 5})
        repo.add(youth)

        result = repo.get("youth")
        assert result is not None
        assert result.name == "Youth Service"
        assert result.moments == {"louvor": 5}

    def test_add_duplicate_raises(self, project_dirs):
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        youth = EventType(slug="youth", name="Youth")
        repo.add(youth)

        with pytest.raises(ValueError, match="already exists"):
            repo.add(youth)

    def test_update(self, project_dirs):
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        youth = EventType(slug="youth", name="Youth")
        repo.add(youth)

        repo.update("youth", name="Friday Youth", description="Every Friday")

        result = repo.get("youth")
        assert result.name == "Friday Youth"
        assert result.description == "Every Friday"

    def test_remove(self, project_dirs):
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        youth = EventType(slug="youth", name="Youth")
        repo.add(youth)
        assert repo.get("youth") is not None

        repo.remove("youth")
        assert repo.get("youth") is None

    def test_cannot_remove_default(self, project_dirs):
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        with pytest.raises(ValueError, match="default"):
            repo.remove(DEFAULT_EVENT_TYPE_SLUG)


class TestSubdirectoryRouting:
    """Test that non-default event types use subdirectories."""

    def test_history_default_at_root(self, project_dirs):
        _, history_dir, _ = project_dirs
        repo = FilesystemHistoryRepository(history_dir)

        setlist = Setlist(
            date="2026-03-15",
            moments={"louvor": ["A"]},
        )
        repo.save(setlist)

        # Default event type saves at root
        assert (history_dir / "2026-03-15.json").exists()

    def test_history_non_default_in_subdirectory(self, project_dirs):
        _, history_dir, _ = project_dirs
        repo = FilesystemHistoryRepository(history_dir)

        setlist = Setlist(
            date="2026-03-15",
            moments={"louvor": ["A"]},
            event_type="youth",
        )
        repo.save(setlist)

        # Non-default type saves in subdirectory
        assert (history_dir / "youth" / "2026-03-15.json").exists()
        assert not (history_dir / "2026-03-15.json").exists()

    def test_history_get_by_date_with_event_type(self, project_dirs):
        _, history_dir, _ = project_dirs
        repo = FilesystemHistoryRepository(history_dir)

        # Save two setlists: one default, one youth
        default_sl = Setlist(
            date="2026-03-15",
            moments={"louvor": ["A"]},
        )
        youth_sl = Setlist(
            date="2026-03-15",
            moments={"louvor": ["B"]},
            event_type="youth",
        )
        repo.save(default_sl)
        repo.save(youth_sl)

        # Retrieve by event type
        result = repo.get_by_date("2026-03-15", event_type="youth")
        assert result is not None
        assert result["moments"]["louvor"] == ["B"]
        assert result.get("event_type") == "youth"

        # Default has no event_type key (backward compat)
        default_result = repo.get_by_date("2026-03-15")
        assert default_result is not None
        assert default_result["moments"]["louvor"] == ["A"]

    def test_history_get_all_includes_subdirectories(self, project_dirs):
        _, history_dir, _ = project_dirs
        repo = FilesystemHistoryRepository(history_dir)

        # Save setlists across types
        for et in ["", "youth"]:
            sl = Setlist(
                date="2026-03-15",
                moments={"louvor": ["Song"]},
                event_type=et,
            )
            repo.save(sl)

        history = repo.get_all()
        assert len(history) == 2

    def test_output_non_default_in_subdirectory(self, project_dirs):
        _, _, output_dir = project_dirs
        repo = FilesystemOutputRepository(output_dir)

        md_path = repo.save_markdown("2026-03-15", "# Test", event_type="youth")
        assert "youth" in str(md_path)
        assert md_path.exists()

    def test_output_default_at_root(self, project_dirs):
        _, _, output_dir = project_dirs
        repo = FilesystemOutputRepository(output_dir)

        md_path = repo.save_markdown("2026-03-15", "# Test")
        assert md_path == output_dir / "2026-03-15.md"
        assert md_path.exists()
