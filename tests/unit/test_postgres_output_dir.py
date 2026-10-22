"""The postgres container must write output where it is told to.

History lives in the database on this backend, so callers pass only
``output_dir``. It used to be dropped, and every ``--output-dir`` run wrote
into ``output/`` instead.
"""

from pathlib import Path

import pytest

pytest.importorskip("psycopg_pool")

from library.repositories import postgres


def test_output_dir_is_used_without_history_dir(tmp_path, mocker, monkeypatch):
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    mocker.patch.object(postgres, "create_pool")  # no database needed
    target = tmp_path / "elsewhere"

    repos = postgres.PostgresRepositoryContainer.create(
        base_path=tmp_path, output_dir=target
    )

    assert repos.output.get_markdown_path("2026-11-18") == target.resolve() / "2026-11-18.md"


def test_default_output_dir_without_override(tmp_path, mocker, monkeypatch):
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    mocker.patch.object(postgres, "create_pool")

    repos = postgres.PostgresRepositoryContainer.create(base_path=tmp_path)

    assert repos.output.get_markdown_path("2026-11-18").parent == (tmp_path / "output").resolve()
