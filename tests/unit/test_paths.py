"""Tests for library.paths — path resolution utilities."""

from pathlib import Path

import pytest

from library.paths import PathConfig, get_output_paths


class TestGetOutputPaths:
    def test_defaults_use_config_values(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        paths = get_output_paths(tmp_path)
        assert paths.output_dir == (tmp_path / "output").resolve()
        assert paths.history_dir == (tmp_path / "history").resolve()

    def test_cli_highest_priority(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SETLIST_OUTPUT_DIR", "/env/output")
        monkeypatch.setenv("SETLIST_HISTORY_DIR", "/env/history")
        paths = get_output_paths(
            tmp_path,
            cli_output_dir="/cli/output",
            cli_history_dir="/cli/history",
        )
        assert paths.output_dir == Path("/cli/output").resolve()
        assert paths.history_dir == Path("/cli/history").resolve()

    def test_env_vars_override_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SETLIST_OUTPUT_DIR", "/env/output")
        monkeypatch.setenv("SETLIST_HISTORY_DIR", "/env/history")
        paths = get_output_paths(tmp_path)
        assert paths.output_dir == Path("/env/output").resolve()
        assert paths.history_dir == Path("/env/history").resolve()

    def test_cli_output_dir_alone_is_honored(self, tmp_path, monkeypatch):
        """--output-dir works without --history-dir (postgres has no history dir)."""
        monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        paths = get_output_paths(tmp_path, cli_output_dir="/cli/out")
        assert paths.output_dir == Path("/cli/out").resolve()
        assert paths.history_dir == (tmp_path / "history").resolve()

    def test_cli_history_dir_alone_is_honored(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        paths = get_output_paths(tmp_path, cli_history_dir="/cli/hist")
        assert paths.output_dir == (tmp_path / "output").resolve()
        assert paths.history_dir == Path("/cli/hist").resolve()

    def test_each_dir_falls_through_independently(self, tmp_path, monkeypatch):
        """A CLI value for one dir does not stop the env var for the other."""
        monkeypatch.setenv("SETLIST_OUTPUT_DIR", "/env/output")
        monkeypatch.setenv("SETLIST_HISTORY_DIR", "/env/history")
        paths = get_output_paths(tmp_path, cli_output_dir="/cli/out")
        assert paths.output_dir == Path("/cli/out").resolve()
        assert paths.history_dir == Path("/env/history").resolve()

    def test_env_output_dir_alone_is_honored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SETLIST_OUTPUT_DIR", "/env/output")
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        paths = get_output_paths(tmp_path)
        assert paths.output_dir == Path("/env/output").resolve()
        assert paths.history_dir == (tmp_path / "history").resolve()

    def test_all_paths_resolved_to_absolute(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        paths = get_output_paths(tmp_path)
        assert paths.output_dir.is_absolute()
        assert paths.history_dir.is_absolute()


class TestPathConfig:
    def test_dataclass_fields(self):
        pc = PathConfig(output_dir=Path("/a"), history_dir=Path("/b"))
        assert pc.output_dir == Path("/a")
        assert pc.history_dir == Path("/b")
