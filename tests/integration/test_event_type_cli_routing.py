"""CLI routing for non-default event types: replace / markdown / label / view-setlist.

These tests guard a class of bugs where CLI commands that write or render
setlists forgot to route through the event type:

* ``replace -e <slug>`` used to write the markdown to the root output
  directory, overwriting (or shadowing) the default event type's
  markdown for the same date.
* ``replace`` (and ``derive``) used to canonicalize the moments dict to
  ``MOMENTS_CONFIG`` order, silently overwriting the event type's
  user-defined ``moments_order`` in saved history.
* ``replace`` / ``markdown`` / ``label`` forgot to thread
  ``moments_order`` into ``format_setlist_markdown``, so the rendered
  markdown ignored the event type's preferred moment sequence.
* ``view-setlist`` built file paths without the event-type subdirectory
  in its ``FILES`` section, reporting "(not found)" for files that did
  exist (at ``output/<slug>/`` and ``history/<slug>/``).

The shape of every test is: seed a youth event type whose
``moments_order`` reverses the default (``final`` before ``louvor``),
run a CLI command, then check on-disk state.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


# ---------------------------------------------------------------------------
# Fixture: tmp project with a 'youth' event type whose moments_order is
# ["final", "louvor"] — deliberately the reverse of how MOMENTS_CONFIG
# would canonicalize it.
# ---------------------------------------------------------------------------


@pytest.fixture()
def youth_project(tmp_path: Path, monkeypatch) -> Path:
    """A tmp project with default + 'youth' event types and a seeded youth setlist.

    The youth event type's ``moments_order`` is ``["final", "louvor"]`` so
    any code path that silently canonicalizes will flip it to
    ``["louvor", "final"]`` and be caught by the assertions below.
    """
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)

    # Songs: a small pool with both louvor- and final-tagged candidates,
    # plus a final-only song so the greedy selector never starves 'final'.
    (tmp_path / "chords").mkdir()
    (tmp_path / "history" / "youth").mkdir(parents=True)
    (tmp_path / "output").mkdir()
    (tmp_path / "database.csv").write_text(
        "song;energy;tags;youtube;event_types\n"
        "Louvor A;1;louvor(4)\n"
        "Louvor B;2;louvor(3)\n"
        "Louvor C;3;louvor(5)\n"
        "Final D;4;final(4)\n"
        "Final E;2;final(3)\n"
        "Extra F;3;louvor(2)\n",
        encoding="utf-8",
    )
    for name, key in [
        ("Louvor A", "C"), ("Louvor B", "D"), ("Louvor C", "Em"),
        ("Final D", "G"), ("Final E", "A"), ("Extra F", "F"),
    ]:
        (tmp_path / "chords" / f"{name}.md").write_text(
            f"### {name} ({key})\n\n{key}       G\nLyrics...\n",
            encoding="utf-8",
        )

    # Event types: a 'main' default + a 'youth' type whose moments_order
    # is the REVERSE of how MOMENTS_CONFIG would canonicalize it.
    (tmp_path / "event_types.json").write_text(
        json.dumps(
            {
                "event_types": {
                    "main": {
                        "name": "Main Event",
                        "description": "",
                        "moments": {
                            "prelúdio": 1, "ofertório": 1, "saudação": 1,
                            "crianças": 1, "louvor": 4, "poslúdio": 1,
                        },
                        "moments_order": [
                            "prelúdio", "ofertório", "saudação",
                            "crianças", "louvor", "poslúdio",
                        ],
                    },
                    "youth": {
                        "name": "Youth Service",
                        "description": "",
                        "moments": {"final": 1, "louvor": 2},
                        # Reverse of MOMENTS_CONFIG canonicalization
                        "moments_order": ["final", "louvor"],
                    },
                },
                "default_slug": "main",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Seed a youth setlist for 2026-03-20 with the user-defined order
    (tmp_path / "history" / "youth" / "2026-03-20.json").write_text(
        json.dumps(
            {
                "date": "2026-03-20",
                "event_type": "youth",
                "moments": {
                    "final": ["Final D"],
                    "louvor": ["Louvor A", "Louvor B"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return tmp_path


def _read_youth_history(project: Path) -> dict:
    return json.loads(
        (project / "history" / "youth" / "2026-03-20.json").read_text(encoding="utf-8")
    )


# ---------------------------------------------------------------------------
# replace -e youth — path routing
# ---------------------------------------------------------------------------


class TestReplaceWritesToEventTypeSubdirectory:
    """``replace -e youth`` must write markdown under ``output/youth/``,
    not ``output/`` — otherwise it overwrites the default event type's
    file for the same date.
    """

    def test_markdown_lands_in_event_type_subdirectory(self, youth_project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace", "-e", "youth",
                "--moment", "louvor", "--position", "1",
                "--with", "Louvor C",
            ],
        )
        assert result.exit_code == 0, result.output

        # The file MUST be in output/youth/, not at the root.
        assert (youth_project / "output" / "youth" / "2026-03-20.md").exists(), (
            "replace -e youth must write markdown to output/youth/"
        )
        assert not (youth_project / "output" / "2026-03-20.md").exists(), (
            "replace -e youth must NOT write markdown to the root output dir "
            "(would clobber the default event type's markdown)"
        )

    def test_does_not_clobber_default_event_type_markdown(self, youth_project):
        """Pre-existing default-event-type markdown for the same date must
        survive a youth-event-type replace."""
        sentinel = youth_project / "output" / "2026-03-20.md"
        sentinel.write_text("DEFAULT EVENT TYPE MARKDOWN", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace", "-e", "youth",
                "--moment", "louvor", "--position", "1",
                "--with", "Louvor C",
            ],
        )
        assert result.exit_code == 0, result.output
        assert sentinel.read_text(encoding="utf-8") == "DEFAULT EVENT TYPE MARKDOWN"


# ---------------------------------------------------------------------------
# replace -e youth — moments_order preservation
# ---------------------------------------------------------------------------


class TestReplacePreservesEventTypeMomentsOrder:
    """``replace`` must not canonicalize a non-default event type's
    ``moments_order`` (the input dict's order is the source of truth).
    """

    def test_history_keeps_event_type_moments_order(self, youth_project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace", "-e", "youth",
                "--moment", "louvor", "--position", "1",
                "--with", "Louvor C",
            ],
        )
        assert result.exit_code == 0, result.output

        saved = _read_youth_history(youth_project)
        assert list(saved["moments"].keys()) == ["final", "louvor"], (
            f"event type's moments_order must be preserved, got "
            f"{list(saved['moments'].keys())!r}"
        )

    def test_markdown_renders_in_event_type_order(self, youth_project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace", "-e", "youth",
                "--moment", "louvor", "--position", "1",
                "--with", "Louvor C",
            ],
        )
        assert result.exit_code == 0, result.output

        md = (youth_project / "output" / "youth" / "2026-03-20.md").read_text(encoding="utf-8")
        final_idx = md.find("## Final")
        louvor_idx = md.find("## Louvor")
        assert final_idx != -1 and louvor_idx != -1
        assert final_idx < louvor_idx, (
            "rendered markdown must follow the event type's moments_order "
            "(final before louvor)"
        )


# ---------------------------------------------------------------------------
# markdown -e youth — moments_order propagation
# ---------------------------------------------------------------------------


class TestRegenerateMarkdownUsesEventTypeOrder:
    """``songbook markdown -e youth`` regenerates from history and must
    render moments in the event type's order.
    """

    def test_regenerated_markdown_respects_moments_order(self, youth_project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["markdown", "-e", "youth", "--date", "2026-03-20"],
        )
        assert result.exit_code == 0, result.output

        md = (youth_project / "output" / "youth" / "2026-03-20.md").read_text(encoding="utf-8")
        final_idx = md.find("## Final")
        louvor_idx = md.find("## Louvor")
        assert final_idx < louvor_idx, (
            f"markdown -e youth must render final before louvor, got\n{md[:300]}"
        )


# ---------------------------------------------------------------------------
# label -e youth — moments_order propagation
# ---------------------------------------------------------------------------


class TestLabelAddPreservesEventTypeOrder:
    """``label -e youth --to evening`` regenerates markdown and must
    keep the event type's moment ordering.
    """

    def test_label_add_keeps_event_type_order(self, youth_project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "label", "-e", "youth",
                "--date", "2026-03-20",
                "--to", "evening",
            ],
        )
        assert result.exit_code == 0, result.output

        # File renamed to <date>_<label>.md under output/youth/
        labeled_md = youth_project / "output" / "youth" / "2026-03-20_evening.md"
        assert labeled_md.exists(), (
            f"labeled markdown must be saved to {labeled_md}, "
            f"output:\n{result.output}"
        )
        md = labeled_md.read_text(encoding="utf-8")
        final_idx = md.find("## Final")
        louvor_idx = md.find("## Louvor")
        assert final_idx < louvor_idx


# ---------------------------------------------------------------------------
# view-setlist -e youth — FILES section reports correct paths
# ---------------------------------------------------------------------------


class TestViewSetlistReportsEventTypePaths:
    """``view-setlist -e youth`` FILES section must report paths inside
    ``output/youth/`` and ``history/youth/`` — and show ✓ when the files
    actually exist there.
    """

    def test_files_section_uses_event_type_subdirectory(self, youth_project):
        # Ensure the markdown exists (so the ✓ check is meaningful).
        runner = CliRunner()
        runner.invoke(
            cli,
            ["markdown", "-e", "youth", "--date", "2026-03-20"],
        )

        result = runner.invoke(
            cli,
            ["view-setlist", "-e", "youth", "--date", "2026-03-20"],
        )
        assert result.exit_code == 0, result.output

        assert "output/youth/2026-03-20.md" in result.output
        assert "history/youth/2026-03-20.json" in result.output
        # The markdown was just (re)generated, so it must show ✓.
        marker_line = next(
            line for line in result.output.splitlines() if "Markdown:" in line
        )
        assert "✓" in marker_line, (
            f"FILES section should mark the markdown as present, got: "
            f"{marker_line!r}"
        )
