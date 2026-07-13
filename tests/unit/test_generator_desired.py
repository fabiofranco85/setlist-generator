"""Generator behavior for `--desired` songs."""

import pytest

from library.generator import SetlistGenerator
from tests.helpers.factories import make_song

MOMENTS = {"prelúdio": 1, "louvor": 4, "poslúdio": 1}


@pytest.fixture
def songs():
    """A pool with several candidates per moment, so auto-selection has choices."""
    pool = {
        "Bondade de Deus": make_song(title="Bondade de Deus", tags={"louvor": 7}, energy=4),
        "Precioso": make_song(title="Precioso", tags={"louvor": 3}, energy=4),
        "Vou Seguir Com Fé": make_song(
            title="Vou Seguir Com Fé", tags={"prelúdio": 3, "poslúdio": 3}, energy=2
        ),
        "Santo de Deus": make_song(title="Santo de Deus", tags={"louvor": 4}, energy=1),
        "Hosana": make_song(title="Hosana", tags={"louvor": 3}, energy=3),
        "Oceanos": make_song(title="Oceanos", tags={"louvor": 2}, energy=3),
        "Eu Te Busco": make_song(title="Eu Te Busco", tags={"louvor": 3}, energy=1),
    }
    for name in ("Estamos de Pé", "Rude Cruz", "Rio de Vida"):
        pool[name] = make_song(title=name, tags={"prelúdio": 3, "poslúdio": 3}, energy=2)
    return pool


def generate(songs, desired=None, **kwargs):
    generator = SetlistGenerator(songs, history=[])
    return generator.generate(
        "2026-02-15", moments_config=MOMENTS, desired=desired, **kwargs
    )


def test_every_desired_song_appears_in_the_setlist(songs):
    setlist = generate(songs, desired=["Bondade de Deus", "Precioso", "Vou Seguir com Fé"])

    placed = {song for song_list in setlist.moments.values() for song in song_list}
    assert {"Bondade de Deus", "Precioso", "Vou Seguir Com Fé"} <= placed


def test_desired_songs_land_in_their_assigned_moments(songs):
    setlist = generate(songs, desired=["Bondade de Deus", "Precioso", "Vou Seguir com Fé"])

    assert "Bondade de Deus" in setlist.moments["louvor"]
    assert "Precioso" in setlist.moments["louvor"]
    assert setlist.moments["prelúdio"] == ["Vou Seguir Com Fé"]


def test_moment_counts_are_unchanged_by_desired_songs(songs):
    """Desired songs occupy slots — they do not inflate the moment."""
    setlist = generate(songs, desired=["Bondade de Deus", "Precioso"])

    assert len(setlist.moments["louvor"]) == MOMENTS["louvor"]
    assert len(setlist.moments["prelúdio"]) == MOMENTS["prelúdio"]


def test_desired_songs_are_placed_by_energy_not_pinned_to_the_front(songs):
    """Louvor is an ascending arc; two energy-4 desired songs belong at the end."""
    setlist = generate(songs, desired=["Bondade de Deus", "Precioso"])

    louvor = setlist.moments["louvor"]
    energies = [songs[title].energy for title in louvor]
    assert energies == sorted(energies), f"energy arc broken: {louvor}"
    assert set(louvor[-2:]) == {"Bondade de Deus", "Precioso"}


def test_overrides_stay_pinned_while_desired_songs_flow(songs):
    """--override still wins position 1; --desired still sorts by energy."""
    setlist = generate(
        songs,
        desired=["Bondade de Deus"],
        overrides={"louvor": ["Oceanos"]},
    )

    louvor = setlist.moments["louvor"]
    assert louvor[0] == "Oceanos"  # pinned at the front despite energy 3

    # Everything after the pinned override is energy-sorted, desired included.
    tail = louvor[1:]
    tail_energies = [songs[title].energy for title in tail]
    assert tail_energies == sorted(tail_energies)
    assert "Bondade de Deus" in tail


@pytest.mark.parametrize("run", range(15))
def test_a_desired_song_is_not_stolen_by_an_earlier_moment(run):
    """Regression: reservation against auto-selection in other moments.

    'Dual' is tagged for both louvor and prelúdio, and is assigned to prelúdio
    (higher weight). Louvor is generated first and could auto-pick it on a lucky
    roll of the random factor, which would leave prelúdio to fill with something
    else. Repeated to defeat the randomness in the scoring formula.
    """
    songs = {
        "Dual": make_song(title="Dual", tags={"louvor": 3, "prelúdio": 9}, energy=2),
        "Filler A": make_song(title="Filler A", tags={"louvor": 9}, energy=1),
        "Filler B": make_song(title="Filler B", tags={"prelúdio": 9}, energy=1),
    }
    generator = SetlistGenerator(songs, history=[])
    setlist = generator.generate(
        "2026-02-15", moments_config={"louvor": 2, "prelúdio": 1}, desired=["Dual"]
    )

    assert setlist.moments["prelúdio"] == ["Dual"]
    assert "Dual" not in setlist.moments["louvor"]


def test_unknown_desired_song_aborts_generation(songs):
    with pytest.raises(ValueError, match="Nao Existe"):
        generate(songs, desired=["Nao Existe"])


def test_oversubscribed_moment_aborts_generation(songs):
    """Five louvor-only songs cannot fit into four louvor slots."""
    with pytest.raises(ValueError, match="louvor"):
        generate(
            songs,
            desired=[
                "Bondade de Deus", "Precioso", "Santo de Deus",
                "Hosana", "Oceanos", "Eu Te Busco",
            ],
        )


def test_desired_song_bound_to_another_event_type_is_rejected(songs):
    """Event-type filtering runs first, so the song is simply not in the pool."""
    songs["Youth Anthem"] = make_song(
        title="Youth Anthem", tags={"louvor": 5}, energy=1, event_types=["youth"]
    )
    with pytest.raises(ValueError, match="Youth Anthem"):
        generate(songs, desired=["Youth Anthem"], event_type="main")


def test_no_desired_songs_leaves_generation_untouched(songs):
    setlist = generate(songs, desired=None)
    assert len(setlist.moments["louvor"]) == 4
