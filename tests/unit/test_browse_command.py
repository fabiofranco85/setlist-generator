"""Unit tests for the ``songbook browse`` CLI command.

``browse`` is a loop around two existing pieces: ``cli.picker.pick_song`` and
``cli.commands.view_song.render_song``. The interesting behavior is therefore
the *orchestration* — how many times the picker is re-shown, what gets paged,
and when the loop terminates.

Following ``test_weights_command.py``: a real in-memory fake repository, with
only the UI boundaries (``pick_song`` / ``echo_via_pager``) stubbed via
``mocker``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cli.commands import browse as browse_cmd
from library.models import Song


@dataclass
class FakeSongRepo:
    songs: dict[str, Song]

    def get_all(self):
        return dict(self.songs)


@dataclass
class FakeRepos:
    songs: FakeSongRepo


def _make_song(title, key="G", energy=2, tags=None):
    return Song(
        title=title,
        tags=dict(tags or {"louvor": 3}),
        energy=energy,
        content=f"### {title} ({key})\n\n{key}      Am\nLyrics for {title}",
    )


@pytest.fixture()
def songs():
    return {
        "Hosana": _make_song("Hosana", key="D", energy=3),
        "Oceanos": _make_song("Oceanos", key="Bm", energy=3),
    }


@pytest.fixture()
def wired(mocker, songs):
    """Wire browse against fake repos + stubbed UI; return the stub handles."""
    mocker.patch.object(
        browse_cmd, "get_repositories", return_value=FakeRepos(FakeSongRepo(songs))
    )
    mocker.patch.object(browse_cmd, "_is_interactive", return_value=True)
    pick = mocker.patch.object(browse_cmd, "pick_song")
    pager = mocker.patch.object(browse_cmd.click, "echo_via_pager")
    return pick, pager


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------


def test_browse_reopens_picker_until_cancelled(wired):
    pick, pager = wired
    # Two songs viewed, then Esc/q cancels the picker.
    pick.side_effect = ["Oceanos", "Hosana", None]

    browse_cmd.run()

    assert pick.call_count == 3  # two views + the cancelling one
    assert pager.call_count == 2  # only the two actual views paged


def test_browse_exits_without_paging_when_cancelled_immediately(wired):
    pick, pager = wired
    pick.side_effect = [None]

    browse_cmd.run()

    assert pager.call_count == 0


def test_browse_pages_the_selected_songs_content(wired):
    pick, pager = wired
    pick.side_effect = ["Oceanos", None]

    browse_cmd.run()

    paged_text = pager.call_args[0][0]
    assert "Oceanos" in paged_text
    assert "Lyrics for Oceanos" in paged_text
    assert "Bm" in paged_text  # key survives into the paged output


def test_browse_returns_cursor_to_the_last_viewed_song(wired):
    pick, pager = wired
    pick.side_effect = ["Oceanos", None]

    browse_cmd.run()

    # First open has no cursor hint; after viewing Oceanos the picker
    # should reopen positioned on it rather than jumping back to the top.
    assert pick.call_args_list[0].kwargs.get("cursor_title") is None
    assert pick.call_args_list[1].kwargs.get("cursor_title") == "Oceanos"


# ---------------------------------------------------------------------------
# Non-interactive / edge cases
# ---------------------------------------------------------------------------


def test_browse_is_one_shot_when_not_interactive(mocker, songs):
    mocker.patch.object(
        browse_cmd, "get_repositories", return_value=FakeRepos(FakeSongRepo(songs))
    )
    mocker.patch.object(browse_cmd, "_is_interactive", return_value=False)
    pick = mocker.patch.object(browse_cmd, "pick_song", return_value="Oceanos")
    pager = mocker.patch.object(browse_cmd.click, "echo_via_pager")

    browse_cmd.run()

    # Must not loop forever without a TTY: view one song, then stop.
    assert pick.call_count == 1
    assert pager.call_count == 1


def test_browse_on_empty_repertoire_exits_cleanly(mocker):
    mocker.patch.object(
        browse_cmd, "get_repositories", return_value=FakeRepos(FakeSongRepo({}))
    )
    pick = mocker.patch.object(browse_cmd, "pick_song")
    pager = mocker.patch.object(browse_cmd.click, "echo_via_pager")

    with pytest.raises(SystemExit) as exc:
        browse_cmd.run()

    assert exc.value.code == 1
    assert pick.call_count == 0
    assert pager.call_count == 0
