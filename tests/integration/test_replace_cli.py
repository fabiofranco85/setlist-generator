"""End-to-end CliRunner tests for ``songbook replace``.

Covers the regression where ``--position 3`` appeared to change position
4 because energy reordering moved the new song. The fix has two
prongs:

1. **Manual user choice (`--with` or `--pick`) overrides every other
   ordering rule.** When the user explicitly picks both the song *and*
   the slot, energy reordering is skipped — the new song lands exactly
   where requested.
2. **Auto mode keeps the energy arc by default.** When no song is
   specified, the algorithm chooses the song *and* the placement, so
   energy ordering still applies. ``--keep-position`` is the opt-out
   for users who want auto-pick + position-stable replacement.

The ``(NEW)`` marker always tracks song *identity*, never position, so
even when energy reorder moves a song the marker follows the song.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture()
def project(tmp_project, monkeypatch) -> Path:
    """A tmp_project pre-seeded with a louvor setlist sorted ascending by energy.

    The fixture monkeypatches the storage backend to filesystem-on-tmp so
    the CLI doesn't pick up the developer's real history during tests.
    """
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_project)

    history_path = tmp_project / "history" / "2026-02-15.json"
    history_path.write_text(
        json.dumps(
            {
                "date": "2026-02-15",
                "moments": {
                    "prelúdio": ["Upbeat Song"],
                    "louvor": [
                        "Upbeat Song",      # energy 1
                        "Moderate Song",    # energy 2
                        "Reflective Song",  # energy 3
                        "Worship Song",     # energy 4
                    ],
                    "ofertório": ["Reflective Song"],
                    "saudação": ["Moderate Song"],
                    "crianças": ["Upbeat Song"],
                    "poslúdio": ["Worship Song"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_project


@pytest.fixture()
def project_with_extra(project: Path) -> Path:
    """``project`` plus a high-energy louvor candidate.

    Adds ``Extra Energy Song`` (energy 4, louvor-tagged) to the
    database and chord folder so tests can pick a song whose energy is
    very different from the song it replaces. With ascending energy
    ordering this guarantees that, when reorder is enabled, the new
    song moves away from the requested low-energy slot.
    """
    db = project / "database.csv"
    db.write_text(
        db.read_text(encoding="utf-8")
        + "Extra Energy Song;4;louvor(3);\n",
        encoding="utf-8",
    )
    (project / "chords" / "Extra Energy Song.md").write_text(
        "### Extra Energy Song (E)\n\nE       B\nLyrics...\n",
        encoding="utf-8",
    )
    return project


def _read_louvor(project: Path) -> list[str]:
    return json.loads(
        (project / "history" / "2026-02-15.json").read_text(encoding="utf-8")
    )["moments"]["louvor"]


# ---------------------------------------------------------------------------
# Manual replacement (--with) — explicit choice pins the song.
# ---------------------------------------------------------------------------


class TestManualReplacementOverridesRules:
    """User intent: 'I picked both the song and the slot — don't second-guess me.'"""

    def test_with_pins_song_to_requested_position(self, project_with_extra):
        """``--with "X" --position 1`` puts X at position 1 even though
        ascending energy ordering would otherwise push it to the back."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "1",
                "--with", "Extra Energy Song",
            ],
        )
        assert result.exit_code == 0, result.output

        louvor = _read_louvor(project_with_extra)
        assert louvor[0] == "Extra Energy Song", (
            f"manual --with must pin the song to the requested position, "
            f"got: {louvor!r}"
        )

    def test_with_marker_at_requested_position(self, project_with_extra):
        """``(NEW)`` marker appears on the new song at the requested slot."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "1",
                "--with", "Extra Energy Song",
            ],
        )
        assert result.exit_code == 0, result.output

        marker_lines = [
            line for line in result.output.splitlines()
            if "(NEW)" in line
        ]
        assert len(marker_lines) == 1
        assert "Extra Energy Song" in marker_lines[0]
        assert marker_lines[0].lstrip().startswith("1."), (
            f"(NEW) line should be at position 1 in the updated listing, "
            f"got: {marker_lines[0]!r}"
        )

    def test_with_does_not_show_drift_note(self, project_with_extra):
        """No reorder happened → no drift note, ever."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "1",
                "--with", "Extra Energy Song",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "energy reordering moved" not in result.output.lower()

    def test_with_announces_pin_in_selection_line(self, project_with_extra):
        """Make the no-reorder behavior explicit in the output so the
        user understands why energy ordering was skipped."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "1",
                "--with", "Extra Energy Song",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "pinned to requested position" in result.output


# ---------------------------------------------------------------------------
# Auto mode — algorithm chooses both song and placement → reorder applies.
# ---------------------------------------------------------------------------


class TestAutoReplacementKeepsEnergyArc:
    def test_auto_replace_drift_shows_marker_and_note(
        self, project_with_extra, monkeypatch
    ):
        """
        Auto mode still reapplies energy ordering after the swap. With
        the seeded selection deterministically picking ``Extra Energy
        Song`` (energy 4) for a request to replace position 1 (energy
        1), the new song must drift to a later position and the CLI
        must (a) put the (NEW) marker on the song wherever it landed,
        and (b) print a clear drift note.

        We force the auto-picker by patching ``select_replacement_song``
        — that keeps the test independent of the scoring algorithm's
        randomization while still exercising the full reorder path.
        """
        monkeypatch.setattr(
            "cli.commands.replace.select_replacement_song",
            lambda **kwargs: "Extra Energy Song",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "1",
            ],
        )
        assert result.exit_code == 0, result.output

        # Drift note appears.
        assert "energy reordering moved" in result.output.lower()
        assert "--keep-position" in result.output

        # (NEW) marker is on Extra Energy Song wherever the reorder
        # placed it — not on whichever song was bumped into position 1.
        marker_lines = [
            line for line in result.output.splitlines() if "(NEW)" in line
        ]
        assert len(marker_lines) == 1
        assert "Extra Energy Song" in marker_lines[0]

        # Persisted setlist: ascending energy reorder pushes the
        # energy-4 replacement to position 3 or 4, NOT position 1.
        louvor = _read_louvor(project_with_extra)
        assert louvor[0] != "Extra Energy Song"
        assert "Extra Energy Song" in louvor

    def test_auto_replace_without_drift_shows_no_note(self, project, monkeypatch):
        """Auto-pick a same-energy replacement → song stays at the
        requested position by stable sort → no drift note."""
        # Add a louvor candidate with the same energy as Reflective Song.
        db = project / "database.csv"
        db.write_text(
            db.read_text(encoding="utf-8")
            + "Same Energy Song;3;louvor(3);\n",
            encoding="utf-8",
        )
        (project / "chords" / "Same Energy Song.md").write_text(
            "### Same Energy Song (D)\n\nD       A\nLyrics...\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "cli.commands.replace.select_replacement_song",
            lambda **kwargs: "Same Energy Song",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "3",
            ],
        )
        assert result.exit_code == 0, result.output

        louvor = _read_louvor(project)
        assert louvor[2] == "Same Energy Song"
        assert "energy reordering moved" not in result.output.lower()


# ---------------------------------------------------------------------------
# --keep-position — the auto-mode opt-out.
# ---------------------------------------------------------------------------


class TestKeepPositionFlag:
    def test_keep_position_in_auto_mode_pins_song(
        self, project_with_extra, monkeypatch
    ):
        """``--keep-position`` works in auto mode: the auto-picked song
        stays at the requested slot regardless of its energy."""
        monkeypatch.setattr(
            "cli.commands.replace.select_replacement_song",
            lambda **kwargs: "Extra Energy Song",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "1",
                "--keep-position",
            ],
        )
        assert result.exit_code == 0, result.output

        louvor = _read_louvor(project_with_extra)
        assert louvor[0] == "Extra Energy Song"
        assert "energy reordering moved" not in result.output.lower()

    def test_keep_position_redundant_with_manual(self, project_with_extra):
        """``--with "X" --keep-position`` is harmless — the song is
        pinned either way. This test exists to lock in the no-crash
        contract for users who pass both flags."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "--moment", "louvor",
                "--position", "1",
                "--with", "Extra Energy Song",
                "--keep-position",
            ],
        )
        assert result.exit_code == 0, result.output
        louvor = _read_louvor(project_with_extra)
        assert louvor[0] == "Extra Energy Song"
