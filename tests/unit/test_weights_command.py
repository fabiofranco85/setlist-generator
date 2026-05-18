"""Unit tests for the ``songbook weights`` CLI command.

We test against a small in-memory fake repository (the protocol is
``@runtime_checkable``, so duck-typing is enough). UI-layer interactions
(``_show_picker`` and ``_prompt_new_weight``) are stubbed via ``mocker`` so
the test focuses on the orchestration logic in ``run``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cli.commands import weights as weights_cmd
from library.models import Song


@dataclass
class FakeEventTypeRepo:
    """Just enough of EventTypeRepository to satisfy _resolve_moments_config."""

    moments: dict[str, int] = field(
        default_factory=lambda: {"prelúdio": 1, "louvor": 4, "poslúdio": 1}
    )
    default_slug: str = "main"

    def get(self, slug):
        from library.event_type import EventType

        if slug == self.default_slug:
            return EventType(slug=self.default_slug, name="Main", moments=self.moments)
        return None

    def get_all(self):
        return {self.default_slug: self.get(self.default_slug)}

    def get_default_slug(self):
        return self.default_slug


@dataclass
class FakeSongRepo:
    songs: dict[str, Song]

    def get_all(self):
        return dict(self.songs)

    def get_by_title(self, title):
        return self.songs.get(title)

    def update_tags(self, title, tags):
        if title not in self.songs:
            raise KeyError(title)
        old = self.songs[title]
        self.songs[title] = Song(
            title=old.title,
            tags=dict(tags),
            energy=old.energy,
            content=old.content,
            youtube_url=old.youtube_url,
            event_types=old.event_types,
        )


@dataclass
class FakeRepos:
    songs: FakeSongRepo
    event_types: FakeEventTypeRepo = field(default_factory=FakeEventTypeRepo)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _make_song(title, tags, energy=2):
    return Song(title=title, tags=dict(tags), energy=energy, content="")


def test_build_rows_sorts_by_weight_desc_then_title():
    songs = [
        ("Oceanos", _make_song("Oceanos", {"louvor": 5})),
        ("Aurora", _make_song("Aurora", {"louvor": 7})),
        ("Hosana", _make_song("Hosana", {"louvor": 5})),
    ]
    rows, titles = weights_cmd._build_rows(songs, "louvor")
    # Highest weight first; ties broken by case-insensitive title sort
    assert titles == ["Aurora", "Hosana", "Oceanos"]
    # The weight column should appear in each row
    for row, expected_weight in zip(rows, [7, 5, 5]):
        assert f"[weight: {expected_weight}]" in row


def test_format_row_pads_title_to_requested_width():
    line = weights_cmd._format_row("Aurora", 7, title_width=12)
    # Title pad + double space separator
    assert line.startswith("Aurora      ")
    assert "[weight: 7]" in line


def test_refresh_songs_for_moment_filters_by_event_type():
    # Songs bound to an event type should drop out when filtering by a
    # different event type, mirroring filter_songs_for_event_type semantics.
    bound = _make_song("Youth Song", {"louvor": 4})
    bound.event_types = ["youth"]
    unbound = _make_song("Generic", {"louvor": 3})

    repos = FakeRepos(songs=FakeSongRepo({"Youth Song": bound, "Generic": unbound}))
    out_youth = weights_cmd._refresh_songs_for_moment(repos, "louvor", "youth")
    out_main = weights_cmd._refresh_songs_for_moment(repos, "louvor", "main")
    assert {t for t, _ in out_youth} == {"Youth Song", "Generic"}
    # "Generic" is unbound — visible everywhere. "Youth Song" is hidden from main.
    assert {t for t, _ in out_main} == {"Generic"}


def test_refresh_songs_for_moment_skips_untagged_songs():
    a = _make_song("A", {"louvor": 5})
    b = _make_song("B", {"prelúdio": 3})  # no louvor tag
    repos = FakeRepos(songs=FakeSongRepo({"A": a, "B": b}))
    out = weights_cmd._refresh_songs_for_moment(repos, "louvor", "")
    assert {t for t, _ in out} == {"A"}


# ---------------------------------------------------------------------------
# _save_weight — full-replacement semantics
# ---------------------------------------------------------------------------


def test_save_weight_preserves_other_moment_tags():
    song = _make_song("Multi", {"louvor": 5, "prelúdio": 3})
    repo = FakeSongRepo({"Multi": song})
    repos = FakeRepos(songs=repo)

    weights_cmd._save_weight(repos, "Multi", "louvor", 9)

    # prelúdio weight is preserved; only louvor is changed.
    assert repo.songs["Multi"].tags == {"louvor": 9, "prelúdio": 3}


def test_save_weight_unknown_song_raises():
    repo = FakeSongRepo({})
    repos = FakeRepos(songs=repo)
    with pytest.raises(KeyError):
        weights_cmd._save_weight(repos, "Ghost", "louvor", 5)


# ---------------------------------------------------------------------------
# run() — orchestration
# ---------------------------------------------------------------------------


def test_run_with_unknown_moment_exits_with_error(mocker, capsys):
    songs = {"A": _make_song("A", {"louvor": 5})}
    repos = FakeRepos(songs=FakeSongRepo(songs))
    mocker.patch.object(weights_cmd, "get_repositories", return_value=repos)
    with pytest.raises(SystemExit) as exc:
        weights_cmd.run(moment="not-a-real-moment")
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "not configured" in err


def test_run_with_empty_moment_pool_prints_message(mocker, capsys):
    # No song is tagged for 'poslúdio' → command exits cleanly with a hint.
    songs = {"A": _make_song("A", {"louvor": 5})}
    repos = FakeRepos(songs=FakeSongRepo(songs))
    mocker.patch.object(weights_cmd, "get_repositories", return_value=repos)
    weights_cmd.run(moment="poslúdio")
    out = capsys.readouterr().out
    assert "No songs are currently tagged for 'poslúdio'" in out


def test_run_saves_edit_and_exits_when_user_quits(mocker, capsys):
    songs = {
        "A": _make_song("A", {"louvor": 5}),
        "B": _make_song("B", {"louvor": 3}),
    }
    repo = FakeSongRepo(songs)
    repos = FakeRepos(songs=repo)
    mocker.patch.object(weights_cmd, "get_repositories", return_value=repos)

    # First _show_picker call returns "A"; second returns None (quit).
    mocker.patch.object(
        weights_cmd, "_show_picker", side_effect=["A", None]
    )
    mocker.patch.object(weights_cmd, "_prompt_new_weight", return_value=8)
    # Force interactive code path so loop continues after the first edit.
    mocker.patch.object(weights_cmd, "_is_interactive", return_value=True)

    weights_cmd.run(moment="louvor")

    assert repo.songs["A"].tags["louvor"] == 8
    out = capsys.readouterr().out
    assert "5 → 8" in out
    assert "Done." in out


def test_run_cancel_on_first_pick_exits_cleanly(mocker, capsys):
    songs = {"A": _make_song("A", {"louvor": 5})}
    repos = FakeRepos(songs=FakeSongRepo(songs))
    mocker.patch.object(weights_cmd, "get_repositories", return_value=repos)
    mocker.patch.object(weights_cmd, "_show_picker", return_value=None)

    weights_cmd.run(moment="louvor")

    out = capsys.readouterr().out
    assert "Done." in out


def test_run_skips_save_on_prompt_cancel(mocker, capsys):
    songs = {"A": _make_song("A", {"louvor": 5})}
    repo = FakeSongRepo(songs)
    repos = FakeRepos(songs=repo)
    mocker.patch.object(weights_cmd, "get_repositories", return_value=repos)
    # Pick "A", then user hits enter on the weight prompt (cancel) → exit loop.
    mocker.patch.object(weights_cmd, "_show_picker", side_effect=["A", None])
    mocker.patch.object(weights_cmd, "_prompt_new_weight", return_value=None)
    mocker.patch.object(weights_cmd, "_is_interactive", return_value=True)

    weights_cmd.run(moment="louvor")

    # Weight unchanged
    assert repo.songs["A"].tags["louvor"] == 5
    out = capsys.readouterr().out
    assert "→" not in out  # no save line was printed


def test_run_non_interactive_exits_after_single_save(mocker):
    # Non-interactive mode = one-shot: pick, save, exit (no loop).
    songs = {
        "A": _make_song("A", {"louvor": 5}),
        "B": _make_song("B", {"louvor": 3}),
    }
    repo = FakeSongRepo(songs)
    repos = FakeRepos(songs=repo)
    mocker.patch.object(weights_cmd, "get_repositories", return_value=repos)
    mocker.patch.object(weights_cmd, "_show_picker", return_value="A")
    mocker.patch.object(weights_cmd, "_prompt_new_weight", return_value=9)
    mocker.patch.object(weights_cmd, "_is_interactive", return_value=False)

    weights_cmd.run(moment="louvor")

    assert repo.songs["A"].tags["louvor"] == 9
    # _show_picker should have been called only once (no loop in non-interactive)
    assert weights_cmd._show_picker.call_count == 1
