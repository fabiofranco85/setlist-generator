"""End-to-end CliRunner tests for the ``songbook youtube`` command group.

Covers:
- the group wiring (``youtube create`` + ``youtube links``) after converting the
  former flat ``youtube`` command into a group,
- the ``youtube links`` editor persisting a validated URL to ``database.csv`` on
  the filesystem backend (non-interactive, one-shot semantics).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """A tmp_project pre-seeded with a setlist, pinned to the filesystem backend.

    Mirrors the isolation used by the other CLI integration tests: drop the
    backend/path env vars (so the developer's .env-driven postgres backend isn't
    used) and chdir into the temp project so database.csv/history resolve there.
    """
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_project)

    (tmp_project / "history" / "2026-02-15.json").write_text(
        json.dumps(
            {
                "date": "2026-02-15",
                "moments": {
                    "louvor": ["Upbeat Song", "Moderate Song"],
                    "poslúdio": ["Worship Song"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_project


def _db_line(project: Path, title: str) -> str:
    return next(
        ln
        for ln in (project / "database.csv").read_text(encoding="utf-8").splitlines()
        if ln.startswith(f"{title};")
    )


# ---------------------------------------------------------------------------
# Group wiring
# ---------------------------------------------------------------------------


def test_youtube_group_help_lists_subcommands(project):
    result = CliRunner().invoke(cli, ["youtube", "--help"])
    assert result.exit_code == 0, result.output
    assert "create" in result.output
    assert "links" in result.output


def test_youtube_create_help_still_works(project):
    # The former flat `songbook youtube` behavior now lives at `youtube create`.
    result = CliRunner().invoke(cli, ["youtube", "create", "--help"])
    assert result.exit_code == 0, result.output
    assert "playlist" in result.output.lower()


# ---------------------------------------------------------------------------
# youtube links — editing
# ---------------------------------------------------------------------------


def test_links_shows_status_summary(project):
    result = CliRunner().invoke(
        cli, ["youtube", "links", "--date", "2026-02-15"], input="0\n"
    )
    assert result.exit_code == 0, result.output
    # Both seeded songs lack links → shown as missing.
    assert "Upbeat Song" in result.output
    assert "missing" in result.output


def test_links_persists_valid_url_to_csv(project):
    result = CliRunner().invoke(
        cli,
        ["youtube", "links", "--date", "2026-02-15"],
        input="1\nhttps://youtu.be/abc123\n",
    )
    assert result.exit_code == 0, result.output
    assert "https://youtu.be/abc123" in _db_line(project, "Upbeat Song")


def test_links_rejects_invalid_url_then_accepts(project):
    result = CliRunner().invoke(
        cli,
        ["youtube", "links", "--date", "2026-02-15"],
        input="1\nnot-a-url\nhttps://youtu.be/abc123\n",
    )
    assert result.exit_code == 0, result.output
    assert "recognized" in result.output.lower()
    assert "https://youtu.be/abc123" in _db_line(project, "Upbeat Song")


def test_links_unknown_date_errors(project):
    result = CliRunner().invoke(cli, ["youtube", "links", "--date", "1999-01-01"])
    assert result.exit_code != 0
