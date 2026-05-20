"""End-to-end CliRunner tests for ``songbook generate``.

These tests guard the derivation branch in ``cli/commands/generate.py``,
specifically the contract around ``--replace``:

* ``--replace`` is meaningful only when an existing base setlist can be
  derived from. If no base exists for the given ``(date, event_type)``
  pair, the CLI must fail loudly with a clear message — silently
  dropping the flag and falling through to fresh generation was the
  previous buggy behavior and is the regression this file pins down.
* Lookups are scoped by event type. A base setlist for ``ceia`` does
  NOT satisfy a ``--replace`` request targeting ``main`` (or the
  default empty event type) — the cross-event-type lookup invariant is
  preserved.
* ``--label`` without ``--replace`` still falls through to fresh
  generation when no base exists. This is the documented behavior and
  must not regress.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """tmp_project with no pre-seeded setlists, env vars cleared.

    Extends the database with a ``crianças``-tagged song so the default
    main moments config can be satisfied during fresh generation — the
    base ``tmp_project`` fixture omits it.
    """
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_project)

    db = tmp_project / "database.csv"
    db.write_text(
        db.read_text(encoding="utf-8")
        + "Children Song;2;crianças,louvor(2);\n",
        encoding="utf-8",
    )
    (tmp_project / "chords" / "Children Song.md").write_text(
        "### Children Song (G)\n\nG       D\nLyrics...\n", encoding="utf-8"
    )
    return tmp_project


@pytest.fixture()
def project_with_ceia_setlist(project) -> Path:
    """``project`` plus a ``ceia`` event type and a seeded ceia setlist on
    2026-03-01. The ``main`` event type uses default moments; ``ceia`` adds
    one extra moment (``ceia``) on top of the standard set, mirroring the
    cross-event-type scenario from the conversation.
    """
    (project / "history" / "ceia").mkdir(parents=True)
    (project / "event_types.json").write_text(
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
                    "ceia": {
                        "name": "Ceia Service",
                        "description": "",
                        "moments": {
                            "prelúdio": 1, "ofertório": 1, "saudação": 1,
                            "crianças": 1, "louvor": 4, "poslúdio": 1,
                            "ceia": 1,
                        },
                        "moments_order": [
                            "prelúdio", "ofertório", "saudação",
                            "crianças", "louvor", "ceia", "poslúdio",
                        ],
                    },
                },
                "default_slug": "main",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (project / "history" / "ceia" / "2026-03-01.json").write_text(
        json.dumps(
            {
                "date": "2026-03-01",
                "event_type": "ceia",
                "moments": {
                    "prelúdio": ["Upbeat Song"],
                    "ofertório": ["Reflective Song"],
                    "saudação": ["Moderate Song"],
                    "crianças": ["Upbeat Song"],
                    "louvor": [
                        "Upbeat Song", "Moderate Song",
                        "Reflective Song", "Worship Song",
                    ],
                    "ceia": ["Worship Song"],
                    "poslúdio": ["Worship Song"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return project


class TestReplaceRequiresExistingBase:
    """``--replace`` is meaningless without a base setlist to derive from.

    Before the fix, the CLI silently ignored ``--replace`` and produced a
    freshly generated setlist — surprising and undiscoverable. After the
    fix, it errors out with a message naming the date AND the event type
    that was searched, so the user can correct either dimension.
    """

    def test_replace_without_any_base_setlist_errors(self, project):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15", "--label", "evening", "--replace", "3"],
        )
        assert result.exit_code != 0, (
            "--replace without a base must fail, not silently fall through "
            "to fresh generation"
        )
        assert "--replace" in result.output
        assert "2026-02-15" in result.output
        # No history file should have been created — the failure must be
        # before any side effects.
        assert not (project / "history" / "2026-02-15_evening.json").exists()

    def test_replace_targeting_main_with_only_ceia_base_errors(
        self, project_with_ceia_setlist
    ):
        """The scenario from the explanatory conversation: a ceia setlist
        exists for 2026-03-01, but the user runs ``generate -e main
        --label evening --replace 3``. Cross-event-type lookups are
        scoped, so no ``main`` base is found and the command must error.
        """
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "generate", "--date", "2026-03-01",
                "-e", "main",
                "--label", "evening", "--replace", "3",
            ],
        )
        assert result.exit_code != 0, (
            "A ceia base must NOT satisfy a --replace request targeting main; "
            "the cross-event-type lookup invariant requires a same-type base"
        )
        assert "--replace" in result.output
        assert "main" in result.output, (
            "Error must name the event type that was searched, so the user "
            "can spot whether they targeted the wrong event type"
        )
        # The ceia setlist must be untouched by the failed derivation attempt.
        assert (
            project_with_ceia_setlist / "history" / "ceia" / "2026-03-01.json"
        ).exists()
        # And no spurious main setlist should have been created.
        assert not (
            project_with_ceia_setlist / "history" / "2026-03-01_evening.json"
        ).exists()


class TestLabelWithoutReplaceStillFallsThrough:
    """Negative regression: the fix must NOT break the documented
    fall-through path where ``--label`` alone (no ``--replace``) generates
    a fresh labeled setlist when no base exists.

    Uses a custom ``simple`` event type with one moment to decouple this
    test from the default ``main`` config (which requires song variety
    the minimal fixture deliberately doesn't provide).
    """

    def test_label_without_replace_generates_fresh(self, project):
        (project / "event_types.json").write_text(
            json.dumps(
                {
                    "event_types": {
                        "main": {
                            "name": "Main", "description": "",
                            "moments": {"louvor": 1},
                            "moments_order": ["louvor"],
                        },
                        "simple": {
                            "name": "Simple", "description": "",
                            "moments": {"louvor": 1},
                            "moments_order": ["louvor"],
                        },
                    },
                    "default_slug": "main",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "generate", "--date", "2026-02-15",
                "-e", "simple", "--label", "evening",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (
            project / "history" / "simple" / "2026-02-15_evening.json"
        ).exists()
