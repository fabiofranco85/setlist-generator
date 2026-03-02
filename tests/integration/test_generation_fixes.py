"""Integration tests for the generation fixes (Problems 1-4).

Tests the full workflow through repository + generator + formatter layers
using the filesystem backend. Each test class focuses on one of the four
fixed problems.
"""

import pytest

from library.event_type import EventType
from library.formatter import format_setlist_markdown
from library.generator import SetlistGenerator
from library.models import Setlist, Song
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


@pytest.fixture()
def songs_for_custom_type():
    """Songs with tags for both 'louvor' and 'final' moments."""
    return {
        "Song A": Song(title="Song A", tags={"louvor": 4, "final": 2}, energy=1, content="### Song A (C)"),
        "Song B": Song(title="Song B", tags={"louvor": 3}, energy=2, content="### Song B (D)"),
        "Song C": Song(title="Song C", tags={"louvor": 5, "final": 3}, energy=3, content="### Song C (Em)"),
        "Song D": Song(title="Song D", tags={"louvor": 4}, energy=4, content="### Song D (A)"),
    }


# ---------------------------------------------------------------------------
# Problem 1: Moment ordering preserved through generation
# ---------------------------------------------------------------------------


class TestMomentOrderingEndToEnd:
    """Verify that user-defined moment order is preserved through the full
    generation pipeline: event type → generator → formatter."""

    def test_ordered_moments_preserved_in_setlist(self, songs_for_custom_type):
        """Generator iterates moments in event type's order."""
        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 2, "final": 1},
            moments_order=["louvor", "final"],
        )

        generator = SetlistGenerator(songs_for_custom_type, [])
        setlist = generator.generate(
            "2026-03-10",
            event_type="custom",
            moments_config=et.ordered_moments,
        )

        # Setlist moments dict should preserve insertion order
        keys = list(setlist.moments.keys())
        assert keys == ["louvor", "final"]

    def test_reversed_order_also_preserved(self, songs_for_custom_type):
        """If user defines final before louvor, that order is preserved."""
        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 2, "final": 1},
            moments_order=["final", "louvor"],
        )

        generator = SetlistGenerator(songs_for_custom_type, [])
        setlist = generator.generate(
            "2026-03-10",
            moments_config=et.ordered_moments,
        )

        keys = list(setlist.moments.keys())
        assert keys == ["final", "louvor"]

    def test_formatter_uses_moments_order(self, songs_for_custom_type):
        """Markdown output respects the event type's moment order."""
        setlist = Setlist(
            date="2026-03-10",
            moments={"louvor": ["Song A"], "final": ["Song C"]},
        )

        md = format_setlist_markdown(
            setlist, songs_for_custom_type,
            moments_order=["louvor", "final"],
        )

        # "Louvor" should appear before "Final" in output
        louvor_pos = md.index("## Louvor")
        final_pos = md.index("## Final")
        assert louvor_pos < final_pos

    def test_formatter_reversed_order(self, songs_for_custom_type):
        """Reversed order: final before louvor in markdown."""
        setlist = Setlist(
            date="2026-03-10",
            moments={"louvor": ["Song A"], "final": ["Song C"]},
        )

        md = format_setlist_markdown(
            setlist, songs_for_custom_type,
            moments_order=["final", "louvor"],
        )

        final_pos = md.index("## Final")
        louvor_pos = md.index("## Louvor")
        assert final_pos < louvor_pos

    def test_filesystem_event_type_round_trip_preserves_order(self, project_dirs):
        """Save → load through filesystem repo preserves moments_order."""
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        et = EventType(
            slug="custom", name="Custom",
            moments={"louvor": 3, "final": 1},
            moments_order=["louvor", "final"],
        )
        repo.add(et)

        loaded = repo.get("custom")
        assert loaded is not None
        assert loaded.moments_order == ["louvor", "final"]
        assert list(loaded.ordered_moments.keys()) == ["louvor", "final"]

    def test_update_moments_updates_order(self, project_dirs):
        """Updating moments through repo also updates moments_order."""
        base, _, _ = project_dirs
        repo = FilesystemEventTypeRepository(base)

        et = EventType(slug="custom", name="Custom", moments={"louvor": 3})
        repo.add(et)

        repo.update("custom", moments={"final": 1, "louvor": 2})

        loaded = repo.get("custom")
        assert loaded is not None
        assert loaded.moments_order == ["final", "louvor"]


# ---------------------------------------------------------------------------
# Problem 2: Strict mode for custom event types
# ---------------------------------------------------------------------------


class TestStrictModeIntegration:
    """Full generation workflow with strict mode for custom event types."""

    def test_raises_for_untagged_moment(self):
        """Custom event type with a moment no songs are tagged for."""
        songs = {
            "Song A": Song(title="Song A", tags={"louvor": 3}, energy=2, content=""),
        }
        generator = SetlistGenerator(songs, [])

        with pytest.raises(ValueError, match="No songs available for moment 'final'"):
            generator.generate(
                "2026-03-10",
                moments_config={"louvor": 1, "final": 1},
            )

    def test_succeeds_when_all_moments_have_songs(self, songs_for_custom_type):
        """No error when all moments have tagged songs."""
        generator = SetlistGenerator(songs_for_custom_type, [])
        setlist = generator.generate(
            "2026-03-10",
            moments_config={"louvor": 2, "final": 1},
        )

        assert len(setlist.moments["louvor"]) == 2
        assert len(setlist.moments["final"]) == 1


# ---------------------------------------------------------------------------
# Problem 3: Backend-aware save messages
# ---------------------------------------------------------------------------


class TestBackendNameIntegration:
    """Verify backend_name property in filesystem context."""

    def test_filesystem_history_repo_backend_name(self, project_dirs):
        _, history_dir, _ = project_dirs
        repo = FilesystemHistoryRepository(history_dir)
        assert repo.backend_name == "filesystem"


# ---------------------------------------------------------------------------
# Problem 4: Output path routing for non-default event types
# ---------------------------------------------------------------------------


class TestOutputPathRouting:
    """Verify markdown and PDF paths use event type subdirectories."""

    def test_non_default_event_type_markdown_in_subdirectory(self, project_dirs):
        _, _, output_dir = project_dirs
        repo = FilesystemOutputRepository(output_dir)

        md_path = repo.save_markdown("2026-03-10", "# Test", event_type="custom")
        assert md_path.parent.name == "custom"
        assert md_path.name == "2026-03-10.md"
        assert md_path.exists()

    def test_default_event_type_markdown_at_root(self, project_dirs):
        _, _, output_dir = project_dirs
        repo = FilesystemOutputRepository(output_dir)

        md_path = repo.save_markdown("2026-03-10", "# Test")
        assert md_path.parent == output_dir
        assert md_path.name == "2026-03-10.md"

    def test_labeled_event_type_markdown_in_subdirectory(self, project_dirs):
        _, _, output_dir = project_dirs
        repo = FilesystemOutputRepository(output_dir)

        md_path = repo.save_markdown(
            "2026-03-10", "# Test", label="evening", event_type="custom",
        )
        assert md_path.parent.name == "custom"
        assert "evening" in md_path.name

    def test_pdf_path_routes_to_subdirectory(self, project_dirs):
        _, _, output_dir = project_dirs
        repo = FilesystemOutputRepository(output_dir)

        pdf_path = repo.get_pdf_path("2026-03-10", event_type="custom")
        assert pdf_path.parent.name == "custom"
        assert pdf_path.suffix == ".pdf"

    def test_full_generate_workflow_saves_to_correct_path(
        self, project_dirs, songs_for_custom_type,
    ):
        """End-to-end: generate setlist → save markdown → verify path."""
        _, history_dir, output_dir = project_dirs
        history_repo = FilesystemHistoryRepository(history_dir)
        output_repo = FilesystemOutputRepository(output_dir)

        generator = SetlistGenerator(songs_for_custom_type, [])
        setlist = generator.generate(
            "2026-03-10",
            event_type="custom",
            moments_config={"louvor": 2, "final": 1},
        )

        # Save markdown via repo
        md = format_setlist_markdown(setlist, songs_for_custom_type)
        md_path = output_repo.save_markdown(
            "2026-03-10", md, event_type="custom",
        )

        # Save history via repo
        history_repo.save(setlist)

        # Verify paths
        assert md_path == output_dir / "custom" / "2026-03-10.md"
        assert md_path.exists()
        assert (history_dir / "custom" / "2026-03-10.json").exists()
