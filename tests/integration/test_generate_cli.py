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

The file also covers the overwrite-confirmation flow that prevents
``generate`` from silently clobbering an existing setlist:

* When a setlist already exists at the target ``(date, label,
  event_type)`` triple, ``generate`` must prompt before overwriting.
* ``--yes`` / ``-y`` skips the prompt for scripts / CI.
* ``--no-save`` disables the check entirely (dry-run path writes
  nothing, so no collision is possible).
* Collision detection is exact-key: a labeled variant doesn't trigger
  the prompt when generating the primary, and a different event type
  doesn't trigger the prompt either.
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
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
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


# ---------------------------------------------------------------------------
# Overwrite-confirmation flow
# ---------------------------------------------------------------------------
#
# These tests pin down the prompt that fires when ``generate`` would
# overwrite an existing setlist. The bug class being prevented is the
# one that wiped out the original ceia setlist for 2026-05-24 earlier
# in this branch's history: ``repos.history.save()`` silently replaces
# any setlist with the same (date, label, event_type) key, and a user
# (or agent) re-running ``generate`` could clobber real work without
# realizing it existed.
#
# Pattern note: ``CliRunner.invoke(input="y\n")`` feeds keystrokes to
# click.confirm; ``input="n\n"`` rejects, which click.confirm with
# ``abort=True`` converts into a non-zero exit via click.Abort.


def _seed_simple_event_types(project: Path) -> None:
    """Write event_types.json with ``main`` and ``youth`` configured as
    simple 1-moment (louvor only) types.

    Using a simple moments shape is a deliberate fixture choice: the
    base ``tmp_project`` only has 5 songs, and the default 6-moment
    MOMENTS_CONFIG can't be re-generated cleanly once one of those
    songs is already pinned by a pre-seeded setlist (the recency-aware
    selector starves on small pools). Restricting to a single louvor
    moment sidesteps that mechanical limitation entirely; the
    confirmation-flow tests don't care about generation richness.
    """
    (project / "event_types.json").write_text(
        json.dumps(
            {
                "event_types": {
                    "main": {
                        "name": "Main", "description": "",
                        "moments": {"louvor": 1},
                        "moments_order": ["louvor"],
                    },
                    "youth": {
                        "name": "Youth", "description": "",
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


@pytest.fixture()
def project_with_existing(project) -> tuple[Path, dict]:
    """``project`` plus a simple ``main`` event type + a pre-seeded
    setlist at 2026-02-15. Returns (project_path, setlist_dict) so
    tests can read the file back and compare against the original."""
    _seed_simple_event_types(project)
    setlist = {
        "date": "2026-02-15",
        "moments": {"louvor": ["Upbeat Song"]},
    }
    (project / "history" / "2026-02-15.json").write_text(
        json.dumps(setlist, ensure_ascii=False), encoding="utf-8"
    )
    return project, setlist


class TestConfirmationPromptOnCollision:
    """When a setlist already exists at the target identity,
    ``generate`` must prompt before overwriting."""

    def test_existing_setlist_prompts_and_confirm_overwrites(
        self, project_with_existing
    ):
        project, _ = project_with_existing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15"],
            input="y\n",
        )
        assert result.exit_code == 0, result.output
        assert "already exists" in result.output
        assert (project / "history" / "2026-02-15.json").exists()

    def test_existing_setlist_prompts_and_abort_keeps_original(
        self, project_with_existing
    ):
        project, original = project_with_existing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15"],
            input="n\n",
        )
        # click.confirm with abort=True raises click.Abort on rejection.
        assert result.exit_code != 0
        # The original on-disk file is untouched — the contract.
        on_disk = json.loads(
            (project / "history" / "2026-02-15.json").read_text(encoding="utf-8")
        )
        assert on_disk == original

    def test_yes_flag_skips_prompt_and_overwrites(self, project_with_existing):
        """``--yes`` must skip the prompt entirely (CI / scripts)."""
        project, _ = project_with_existing
        runner = CliRunner()
        # Deliberately no input — the test fails if the prompt fires
        # at all (CliRunner with no input EOFs and aborts).
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15", "--yes"],
        )
        assert result.exit_code == 0, result.output
        assert "overwriting existing setlist" in result.output
        assert "(--yes)" in result.output

    def test_short_y_flag_skips_prompt(self, project_with_existing):
        """``-y`` is the documented short form; must work identically."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15", "-y"],
        )
        assert result.exit_code == 0, result.output

    def test_no_save_skips_check_entirely(self, project_with_existing):
        """--no-save doesn't write history → no collision possible →
        no prompt should fire even though the target exists on disk.

        Without this short-circuit, a dry-run against an existing
        setlist would still prompt the user even though nothing would
        be written, which is gratuitous."""
        project, original = project_with_existing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15", "--no-save"],
            # No input — if the prompt fires the test fails on EOF.
        )
        assert result.exit_code == 0, result.output
        assert "Dry run" in result.output
        # The on-disk file is untouched (no write happened).
        on_disk = json.loads(
            (project / "history" / "2026-02-15.json").read_text(encoding="utf-8")
        )
        assert on_disk == original


class TestConfirmationKeyScopedToFullIdentity:
    """The collision key is the full ``(date, label, event_type)``
    triple — not just date. Generating a labeled variant when only the
    primary exists must NOT prompt; targeting an existing labeled
    variant must."""

    def test_existing_primary_does_not_block_labeled_generation(
        self, project_with_existing
    ):
        """Generating with --label evening when only the primary exists
        for that date is a *derivation*, targeting a different identity
        (label='evening' ≠ label=''). No prompt should fire."""
        project, _ = project_with_existing
        runner = CliRunner()
        # No input — prompt firing would EOF and fail.
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15", "--label", "evening", "--replace", "0"],
        )
        assert result.exit_code == 0, result.output
        assert "already exists" not in result.output
        assert (project / "history" / "2026-02-15.json").exists()
        assert (project / "history" / "2026-02-15_evening.json").exists()

    def test_existing_labeled_blocks_relabel_attempt(self, project):
        """When the target labeled variant already exists, the prompt
        fires — and aborting leaves the labeled file untouched."""
        _seed_simple_event_types(project)
        primary = {
            "date": "2026-02-15",
            "moments": {"louvor": ["Upbeat Song"]},
        }
        labeled = {**primary, "label": "evening"}
        (project / "history" / "2026-02-15.json").write_text(
            json.dumps(primary, ensure_ascii=False), encoding="utf-8"
        )
        (project / "history" / "2026-02-15_evening.json").write_text(
            json.dumps(labeled, ensure_ascii=False), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15", "--label", "evening", "--replace", "0"],
            input="n\n",
        )
        assert result.exit_code != 0
        assert "already exists" in result.output
        on_disk = json.loads(
            (project / "history" / "2026-02-15_evening.json").read_text(encoding="utf-8")
        )
        assert on_disk == labeled

    def test_existing_main_does_not_block_event_type_generation(
        self, project_with_existing
    ):
        """Generating with -e youth must not prompt when only a main
        setlist exists for the date — different event_type, different
        target identity."""
        project, _ = project_with_existing
        runner = CliRunner()
        # No input — prompt firing would EOF and fail.
        result = runner.invoke(
            cli,
            ["generate", "--date", "2026-02-15", "-e", "youth"],
        )
        assert result.exit_code == 0, result.output
        assert "already exists" not in result.output
        assert (project / "history" / "2026-02-15.json").exists()
        assert (project / "history" / "youth" / "2026-02-15.json").exists()
