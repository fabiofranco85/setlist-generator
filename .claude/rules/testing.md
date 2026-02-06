---
paths:
  - "tests/**"
  - "**/test_*.py"
  - "**/conftest.py"
---

# Testing Guide

This document describes the testing conventions, tools, and patterns for the project. This documentation is loaded when working on test files.

## Stack

- **Framework:** pytest 9.x — plain functions, no `unittest.TestCase` or test classes
- **Coverage:** pytest-cov with branch coverage, 80% threshold
- **Mocking:** pytest-mock (`mocker` fixture) for system boundary mocks
- **Time freezing:** freezegun for date/time-dependent logic (recency scoring, history)
- **Configuration:** `pyproject.toml` under `[tool.pytest.ini_options]` and `[tool.coverage.*]`

## Directory Layout

```
tests/
├── conftest.py            # Root fixtures and automatic marker assignment
├── unit/                  # Fast, isolated tests (no I/O, no network)
│   └── conftest.py        # Unit-specific fixtures
├── integration/           # Tests that use the filesystem or full repository stack
│   └── conftest.py        # Integration-specific fixtures
└── helpers/
    └── factories.py       # Test data builders (Song, history entries, etc.)
```

**What goes where:**
- `unit/` — Pure logic tests: scoring, ordering, transposition, tag parsing, formatting. No file I/O.
- `integration/` — Tests that exercise the repository stack against a real (temporary) filesystem, or test CLI commands end-to-end.
- `helpers/` — Shared builder functions and test data factories. Not test files themselves.

## Markers

Markers `unit` and `integration` are **auto-applied** by directory via `pytest_collection_modifyitems` in the root conftest. You never need to decorate tests with `@pytest.mark.unit` or `@pytest.mark.integration`.

Use `@pytest.mark.slow` explicitly for tests that take more than a few seconds.

## Naming Conventions

- **Test files:** `test_<module>.py`, mirroring the source module (e.g., `test_selector.py` tests `library/selector.py`)
- **Test functions:** `test_<behavior_being_tested>` — describe the behavior, not the method name
  - Good: `test_never_used_song_gets_maximum_recency_score`
  - Bad: `test_calculate_recency_scores`
- **Fixtures:** Descriptive nouns (`sample_songs`, `tmp_project`, `empty_history`)

## Writing Tests

Tests are plain functions. No classes, no `setUp`/`tearDown`.

```python
def test_ascending_energy_ordering_for_louvor(sample_songs):
    """Louvor songs should be ordered from upbeat (1) to worship (4)."""
    names = ["Worship Song", "Upbeat Song", "Reflective Song"]
    ordered = apply_energy_ordering(names, "louvor", sample_songs, override_count=0)
    energies = [sample_songs[n].energy for n in ordered]
    assert energies == sorted(energies)
```

**Key conventions:**
- Fixtures handle all setup. No module-level state or global variables.
- Default fixture scope is `function`. Use `session` scope only for expensive shared resources.
- Use `pytest.raises` as a context manager with `match=` for specificity.
- Use `pytest.approx` for floating-point comparisons (especially recency scores).
- Use `@pytest.mark.parametrize` for multiple input/output cases instead of duplicating tests.

## Shared Fixtures

The root `conftest.py` provides these fixtures:

| Fixture | Description |
|---------|-------------|
| `sample_song` | A single `Song` instance with louvor + prelúdio tags |
| `sample_songs` | Dict of 4 songs covering energies 1–4 |
| `empty_history` | Empty list (no prior services) |
| `sample_history` | Two past services with dates and moments |
| `sample_setlist` | A complete `Setlist` object |
| `tmp_project` | Temporary project tree with `database.csv`, `chords/`, `history/`, `output/` |

Use `tmp_project` for integration tests that need a real filesystem. It creates an isolated directory in `tmp_path` that pytest auto-cleans.

## Mocking Policy

- **Mock at system boundaries only:** file I/O, YouTube API, Google OAuth, PDF generation, `date.today()`
- **Never mock** the code under test or its direct collaborators.
- **Prefer Protocol-based fakes** over `unittest.mock.patch`. The repository pattern already defines Protocols (`SongRepository`, `HistoryRepository`, etc.) — create in-memory implementations for unit tests.
- When patching is necessary, use the `mocker` fixture from pytest-mock. Do not stack `@patch` decorators.

**Freezing time:**
```python
from freezegun import freeze_time

@freeze_time("2026-02-15")
def test_recency_score_after_45_days(sample_songs):
    history = [{"date": "2026-01-01", "moments": {"louvor": ["Upbeat Song"]}}]
    scores = calculate_recency_scores(sample_songs, history, "2026-02-15")
    assert scores["Upbeat Song"] == pytest.approx(0.63, abs=0.02)
```

## How to Run

```bash
# Fast feedback loop (unit tests only)
uv run pytest tests/unit/ -v

# Integration tests
uv run pytest tests/integration/ -v

# Skip slow tests
uv run pytest -m "not slow" -v

# Full suite with coverage
uv run pytest tests/ --cov --cov-report=term-missing

# Single test file
uv run pytest tests/unit/test_selector.py -v

# Single test by name pattern
uv run pytest -k "recency" -v
```

## Adding New Tests

1. Create `tests/unit/test_<module>.py` or `tests/integration/test_<feature>.py`
2. Import the function/class under test from `library`
3. Use existing fixtures from conftest or create new ones in the appropriate conftest
4. If you need reusable test data builders, add them to `tests/helpers/factories.py`
