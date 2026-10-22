"""``--output-dir`` on its own must redirect where a command writes.

Before the fix the path resolver ignored ``--output-dir`` unless
``--history-dir`` was passed too, so a "write it somewhere else" run
silently overwrote the real ``output/`` files.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project: Path, monkeypatch) -> Path:
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.chdir(tmp_project)
    (tmp_project / "history" / "2026-11-18.json").write_text(
        json.dumps({"date": "2026-11-18", "moments": {"louvor": ["Upbeat Song"]}}),
        encoding="utf-8",
    )
    return tmp_project


def test_markdown_output_dir_alone_writes_there(project: Path):
    target = project / "scratch"

    result = CliRunner().invoke(
        cli, ["markdown", "--date", "2026-11-18", "--output-dir", str(target)]
    )

    assert result.exit_code == 0, result.output
    assert (target / "2026-11-18.md").exists()
    assert not (project / "output" / "2026-11-18.md").exists()
