"""End-to-end CliRunner tests for ``songbook generate --desired``.

``--desired`` names songs that must appear in the setlist without saying where
they go — the generator picks the moment. These tests pin the contract:

* Every desired song reaches the saved setlist.
* Names match case-insensitively (the flag is typed by hand, and the goal's own
  example writes "Vou Seguir com Fé" against a database storing "Com").
* An unknown song aborts the run *before* anything is written to disk.
* A desired set that cannot fit the moments aborts the same way.
* Desired songs are placed by energy, not pinned to the front like ``--override``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli

DATE = "2026-07-19"

# song;energy;tags;youtube — enough candidates per moment that auto-selection
# has real choices to make, so "the desired song got in" is not a foregone
# conclusion.
DATABASE = """song;energy;tags;youtube
Bondade de Deus;4;louvor(7);
Precioso;4;louvor(3);
Vou Seguir Com Fé;2;prelúdio,poslúdio;
Santo de Deus;1;louvor(4);
Hosana;3;louvor(3);
Oceanos;3;louvor(2);
Eu Te Busco;1;louvor(3);
Estamos de Pé;2;prelúdio,poslúdio;
Rude Cruz;2;prelúdio,poslúdio;
Rio de Vida;2;saudação,ofertório;
Te Agradeço;2;ofertório,saudação;
Rei Davi;1;crianças;
Noite de Paz;3;natal-prelúdio;
"""

ENERGIES = {
    line.split(";")[0]: int(line.split(";")[1])
    for line in DATABASE.strip().splitlines()[1:]
}


@pytest.fixture()
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    for name in ("SETLIST_OUTPUT_DIR", "SETLIST_HISTORY_DIR", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)

    (tmp_path / "chords").mkdir()
    (tmp_path / "history").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "database.csv").write_text(DATABASE, encoding="utf-8")

    for line in DATABASE.strip().splitlines()[1:]:
        title = line.split(";")[0]
        (tmp_path / "chords" / f"{title}.md").write_text(
            f"### {title} (G)\n\nG       D\nLyrics...\n", encoding="utf-8"
        )

    monkeypatch.chdir(tmp_path)
    return tmp_path


def saved_setlist(project: Path) -> dict:
    return json.loads((project / "history" / f"{DATE}.json").read_text(encoding="utf-8"))


def generate(*args):
    return CliRunner().invoke(cli, ["generate", "--date", DATE, "--yes", *args])


def test_all_desired_songs_reach_the_saved_setlist(project):
    result = generate("--desired", "Bondade de Deus, Precioso, Vou Seguir Com Fé")
    assert result.exit_code == 0, result.output

    moments = saved_setlist(project)["moments"]
    placed = {song for song_list in moments.values() for song in song_list}
    assert {"Bondade de Deus", "Precioso", "Vou Seguir Com Fé"} <= placed


def test_desired_songs_are_matched_case_insensitively(project):
    """The goal's own example: user types 'com Fé', database stores 'Com Fé'."""
    result = generate("--desired", "bondade de deus, Vou Seguir com Fé")
    assert result.exit_code == 0, result.output

    moments = saved_setlist(project)["moments"]
    placed = {song for song_list in moments.values() for song in song_list}
    assert {"Bondade de Deus", "Vou Seguir Com Fé"} <= placed


def test_desired_songs_land_in_the_moment_the_system_chose(project):
    result = generate("--desired", "Bondade de Deus, Vou Seguir Com Fé")
    assert result.exit_code == 0, result.output

    moments = saved_setlist(project)["moments"]
    assert "Bondade de Deus" in moments["louvor"]
    assert moments["prelúdio"] == ["Vou Seguir Com Fé"]


def test_desired_songs_follow_the_energy_arc(project):
    """Louvor ascends 1->4, so an energy-4 desired song sinks to the end.

    Asserted tie-safely: 'Precioso' is also energy 4 and may be auto-picked, in
    which case it can share the tail. What must hold is that the arc is sorted
    and the desired song is *not* pinned to the front — the whole difference
    between --desired and --override.
    """
    result = generate("--desired", "Bondade de Deus")
    assert result.exit_code == 0, result.output

    louvor = saved_setlist(project)["moments"]["louvor"]
    energies = [ENERGIES[title] for title in louvor]

    assert energies == sorted(energies), f"energy arc broken: {louvor}"
    assert louvor[0] != "Bondade de Deus"  # not pinned to the front
    assert "Bondade de Deus" in louvor[-2:]  # only Precioso (also 4) can tie it


def test_summary_marks_where_each_desired_song_landed(project):
    result = generate("--desired", "Bondade de Deus")
    assert result.exit_code == 0
    assert "Bondade de Deus  (desired)" in result.output


def test_unknown_song_aborts_before_writing_anything(project):
    result = generate("--desired", "Bondade de Deus, Nao Existe")

    assert result.exit_code == 1
    assert "Nao Existe" in result.output
    assert not (project / "history" / f"{DATE}.json").exists()
    assert not (project / "output" / f"{DATE}.md").exists()


def test_unknown_song_suggests_a_close_match(project):
    result = generate("--desired", "Oceanoss")

    assert result.exit_code == 1
    assert "did you mean: Oceanos" in result.output


def test_every_unknown_song_is_reported_in_one_run(project):
    result = generate("--desired", "Bogus One, Bogus Two")

    assert result.exit_code == 1
    assert "Bogus One" in result.output
    assert "Bogus Two" in result.output


def test_oversubscribed_moment_aborts(project):
    """Five louvor-only songs cannot fit four louvor slots."""
    result = generate(
        "--desired",
        "Bondade de Deus, Precioso, Santo de Deus, Hosana, Oceanos, Eu Te Busco",
    )

    assert result.exit_code == 1
    assert "louvor" in result.output
    assert not (project / "history" / f"{DATE}.json").exists()


def test_song_tagged_only_for_another_event_types_moments_aborts(project):
    result = generate("--desired", "Noite de Paz")

    assert result.exit_code == 1
    assert "Noite de Paz" in result.output


def test_desired_is_rejected_when_deriving_a_labeled_setlist(project):
    """Derivation copies from a base instead of running selection, so there is
    no assignment step for --desired to hook into. Refuse, don't ignore."""
    assert generate().exit_code == 0  # seed the base setlist

    result = CliRunner().invoke(
        cli,
        ["generate", "--date", DATE, "--yes", "--label", "evening",
         "--desired", "Bondade de Deus"],
    )

    assert result.exit_code == 1
    assert "--desired cannot be combined" in result.output


def test_desired_works_alongside_override(project):
    """--override pins its song to the front; --desired still sorts by energy."""
    result = generate(
        "--override", "louvor:Oceanos",
        "--desired", "Bondade de Deus",
    )
    assert result.exit_code == 0, result.output

    louvor = saved_setlist(project)["moments"]["louvor"]
    assert louvor[0] == "Oceanos"  # pinned at the front despite energy 3

    # Everything after the pinned override is energy-sorted, desired included.
    tail = louvor[1:]
    tail_energies = [ENERGIES[title] for title in tail]
    assert tail_energies == sorted(tail_energies)
    assert "Bondade de Deus" in tail
