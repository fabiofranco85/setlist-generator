"""Root conftest — shared fixtures and automatic marker assignment."""

from pathlib import Path

import pytest

from library.models import Setlist, Song

# ---------------------------------------------------------------------------
# Automatic markers based on directory
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply ``unit`` / ``integration`` markers by test location."""
    for item in items:
        parts = item.path.parts
        if "unit" in parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in parts:
            item.add_marker(pytest.mark.integration)


# ---------------------------------------------------------------------------
# Song fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_song() -> Song:
    """A single Song instance useful as a minimal test building block."""
    return Song(
        title="Test Song",
        tags={"louvor": 5, "prelúdio": 3},
        energy=2,
        content="### Test Song (G)\n\nG       D\nLyrics here...",
        youtube_url="",
    )


@pytest.fixture()
def sample_songs() -> dict[str, Song]:
    """A small catalogue of songs covering different energies and moments."""
    return {
        "Upbeat Song": Song(
            title="Upbeat Song",
            tags={"louvor": 4, "prelúdio": 3},
            energy=1,
            content="### Upbeat Song (C)\n\nC       G\nUpbeat lyrics...",
        ),
        "Moderate Song": Song(
            title="Moderate Song",
            tags={"louvor": 3, "saudação": 4},
            energy=2,
            content="### Moderate Song (D)\n\nD       A\nModerate lyrics...",
        ),
        "Reflective Song": Song(
            title="Reflective Song",
            tags={"louvor": 5, "ofertório": 3},
            energy=3,
            content="### Reflective Song (Em)\n\nEm      Am\nReflective lyrics...",
        ),
        "Worship Song": Song(
            title="Worship Song",
            tags={"louvor": 4, "poslúdio": 2},
            energy=4,
            content="### Worship Song (A)\n\nA       E\nWorship lyrics...",
        ),
    }


# ---------------------------------------------------------------------------
# History fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_history() -> list[dict]:
    """An empty history list — no songs have ever been used."""
    return []


@pytest.fixture()
def sample_history() -> list[dict]:
    """A small history list with two past services (most-recent first)."""
    return [
        {
            "date": "2026-01-15",
            "moments": {
                "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
                "prelúdio": ["Upbeat Song"],
            },
        },
        {
            "date": "2026-01-01",
            "moments": {
                "louvor": ["Moderate Song", "Worship Song", "Reflective Song", "Upbeat Song"],
                "ofertório": ["Reflective Song"],
            },
        },
    ]


# ---------------------------------------------------------------------------
# Setlist fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_setlist() -> Setlist:
    """A complete Setlist object for testing formatters, replacers, etc."""
    return Setlist(
        date="2026-02-15",
        moments={
            "prelúdio": ["Upbeat Song"],
            "louvor": ["Upbeat Song", "Moderate Song", "Reflective Song", "Worship Song"],
            "ofertório": ["Reflective Song"],
            "saudação": ["Moderate Song"],
            "crianças": ["Upbeat Song"],
            "poslúdio": ["Worship Song"],
        },
    )


# ---------------------------------------------------------------------------
# Filesystem / tmp directory helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project tree inside ``tmp_path``.

    Returns the base path containing ``database.csv``, ``chords/``,
    ``history/``, and ``output/`` directories ready for repository use.
    """
    (tmp_path / "chords").mkdir()
    (tmp_path / "history").mkdir()
    (tmp_path / "output").mkdir()

    # Minimal database with header
    db = tmp_path / "database.csv"
    db.write_text(
        "song;energy;tags;youtube\n"
        "Upbeat Song;1;louvor(4),prelúdio;\n"
        "Moderate Song;2;louvor(3),saudação(4);\n"
        "Reflective Song;3;louvor(5),ofertório;\n"
        "Worship Song;4;louvor(4),poslúdio(2);\n",
        encoding="utf-8",
    )

    # Minimal chord files
    for name, key in [
        ("Upbeat Song", "C"),
        ("Moderate Song", "D"),
        ("Reflective Song", "Em"),
        ("Worship Song", "A"),
    ]:
        chord_file = tmp_path / "chords" / f"{name}.md"
        chord_file.write_text(f"### {name} ({key})\n\n{key}       G\nLyrics...\n")

    return tmp_path
