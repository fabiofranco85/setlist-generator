"""Unit tests for the ``songbook youtube links`` CLI command.

We test against small in-memory fakes (the repository protocols are
``@runtime_checkable``, so duck-typing is enough). UI-layer interactions
(``_show_picker``, ``click.prompt``/``click.confirm``) are stubbed via
``mocker`` so the tests focus on classification, the URL prompt, and the
orchestration logic in ``run``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cli.commands import youtube_links as yt
from library.models import Song


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeEventTypeRepo:
    default_slug: str = "main"
    moments: dict[str, int] = field(
        default_factory=lambda: {"louvor": 4, "poslúdio": 1}
    )

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

    def update_youtube(self, title, youtube_url):
        if title not in self.songs:
            raise KeyError(title)
        old = self.songs[title]
        self.songs[title] = Song(
            title=old.title,
            tags=old.tags,
            energy=old.energy,
            content=old.content,
            youtube_url=youtube_url,
            event_types=old.event_types,
        )


@dataclass
class FakeHistoryRepo:
    setlist: dict

    def get_by_date(self, date, label="", event_type=""):
        if date == self.setlist["date"]:
            return self.setlist
        return None

    def get_all(self):
        return [self.setlist]


@dataclass
class FakeRepos:
    songs: FakeSongRepo
    history: FakeHistoryRepo
    event_types: FakeEventTypeRepo = field(default_factory=FakeEventTypeRepo)


def _make_song(title, youtube_url="", tags=None):
    return Song(
        title=title,
        tags=dict(tags or {"louvor": 3}),
        energy=2,
        content="",
        youtube_url=youtube_url,
    )


def _setlist(*titles):
    return {"date": "2026-02-15", "moments": {"louvor": list(titles)}}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_setlist_titles_dedupes_preserving_order():
    setlist = {
        "moments": {
            "louvor": ["A", "B", "A"],
            "poslúdio": ["B", "C"],
        }
    }
    assert yt._setlist_titles(setlist) == ["A", "B", "C"]


def test_status_ok_for_valid_youtube_url():
    song = _make_song("A", "https://youtu.be/abc123")
    status, text = yt._status_and_text(song)
    assert status == yt.STATUS_OK
    assert text == "https://youtu.be/abc123"


def test_status_missing_for_empty_url():
    status, text = yt._status_and_text(_make_song("A", ""))
    assert status == yt.STATUS_MISSING
    assert text == "(no link)"


def test_status_bad_for_unrecognized_url():
    status, text = yt._status_and_text(_make_song("A", "https://example.com/x"))
    assert status == yt.STATUS_BAD
    assert "unrecognized" in text


def test_status_bad_when_song_missing_from_database():
    status, text = yt._status_and_text(None)
    assert status == yt.STATUS_BAD
    assert "not in song database" in text


def test_build_rows_one_row_per_title_with_status():
    songs = {
        "A": _make_song("A", ""),
        "B": _make_song("B", "https://youtu.be/abc123"),
    }
    rows = yt._build_rows(["A", "B"], songs)
    assert len(rows) == 2
    assert rows[0].startswith(yt.STATUS_MISSING)
    assert rows[1].startswith(yt.STATUS_OK)


# ---------------------------------------------------------------------------
# _prompt_new_url
# ---------------------------------------------------------------------------


def test_prompt_returns_valid_url(mocker):
    mocker.patch.object(yt.click, "prompt", return_value="https://youtu.be/abc123")
    assert yt._prompt_new_url("A", "") == "https://youtu.be/abc123"


def test_prompt_reprompts_on_invalid_then_accepts(mocker):
    mocker.patch.object(
        yt.click, "prompt", side_effect=["not-a-url", "https://youtu.be/abc123"]
    )
    assert yt._prompt_new_url("A", "") == "https://youtu.be/abc123"


def test_prompt_blank_with_no_current_is_noop(mocker):
    mocker.patch.object(yt.click, "prompt", return_value="")
    assert yt._prompt_new_url("A", "") is None


def test_prompt_blank_with_current_clears_after_confirm(mocker):
    mocker.patch.object(yt.click, "prompt", return_value="")
    mocker.patch.object(yt.click, "confirm", return_value=True)
    assert yt._prompt_new_url("A", "https://youtu.be/old") == ""


def test_prompt_blank_with_current_keeps_when_confirm_declined(mocker):
    mocker.patch.object(yt.click, "prompt", return_value="")
    mocker.patch.object(yt.click, "confirm", return_value=False)
    assert yt._prompt_new_url("A", "https://youtu.be/old") is None


def test_prompt_unchanged_url_returns_none(mocker):
    mocker.patch.object(yt.click, "prompt", return_value="https://youtu.be/abc123")
    assert yt._prompt_new_url("A", "https://youtu.be/abc123") is None


# ---------------------------------------------------------------------------
# run() — orchestration
# ---------------------------------------------------------------------------


def test_run_saves_edit_and_exits_when_user_quits(mocker, capsys):
    repo = FakeSongRepo(
        {"A": _make_song("A", ""), "B": _make_song("B", "https://youtu.be/b")}
    )
    repos = FakeRepos(songs=repo, history=FakeHistoryRepo(_setlist("A", "B")))
    mocker.patch.object(yt, "get_repositories", return_value=repos)
    mocker.patch.object(yt, "_show_picker", side_effect=["A", None])
    mocker.patch.object(yt, "_prompt_new_url", return_value="https://youtu.be/new")
    mocker.patch.object(yt, "_is_interactive", return_value=True)

    yt.run("2026-02-15", None, None)

    assert repo.songs["A"].youtube_url == "https://youtu.be/new"
    out = capsys.readouterr().out
    assert "link updated" in out
    assert "build the playlist" in out


def test_run_clears_link_when_prompt_returns_empty(mocker, capsys):
    repo = FakeSongRepo({"A": _make_song("A", "https://youtu.be/old")})
    repos = FakeRepos(songs=repo, history=FakeHistoryRepo(_setlist("A")))
    mocker.patch.object(yt, "get_repositories", return_value=repos)
    mocker.patch.object(yt, "_show_picker", side_effect=["A", None])
    mocker.patch.object(yt, "_prompt_new_url", return_value="")
    mocker.patch.object(yt, "_is_interactive", return_value=True)

    yt.run("2026-02-15", None, None)

    assert repo.songs["A"].youtube_url == ""
    assert "link cleared" in capsys.readouterr().out


def test_run_cancel_on_first_pick_exits_cleanly(mocker, capsys):
    repo = FakeSongRepo({"A": _make_song("A", "")})
    repos = FakeRepos(songs=repo, history=FakeHistoryRepo(_setlist("A")))
    mocker.patch.object(yt, "get_repositories", return_value=repos)
    mocker.patch.object(yt, "_show_picker", return_value=None)

    yt.run("2026-02-15", None, None)

    assert "build the playlist" in capsys.readouterr().out


def test_run_skips_save_on_prompt_cancel(mocker, capsys):
    repo = FakeSongRepo({"A": _make_song("A", "")})
    repos = FakeRepos(songs=repo, history=FakeHistoryRepo(_setlist("A")))
    mocker.patch.object(yt, "get_repositories", return_value=repos)
    mocker.patch.object(yt, "_show_picker", side_effect=["A", None])
    mocker.patch.object(yt, "_prompt_new_url", return_value=None)
    mocker.patch.object(yt, "_is_interactive", return_value=True)

    yt.run("2026-02-15", None, None)

    assert repo.songs["A"].youtube_url == ""
    assert "updated" not in capsys.readouterr().out


def test_run_non_interactive_exits_after_single_save(mocker):
    repo = FakeSongRepo(
        {"A": _make_song("A", ""), "B": _make_song("B", "")}
    )
    repos = FakeRepos(songs=repo, history=FakeHistoryRepo(_setlist("A", "B")))
    mocker.patch.object(yt, "get_repositories", return_value=repos)
    mocker.patch.object(yt, "_show_picker", return_value="A")
    mocker.patch.object(yt, "_prompt_new_url", return_value="https://youtu.be/new")
    mocker.patch.object(yt, "_is_interactive", return_value=False)

    yt.run("2026-02-15", None, None)

    assert repo.songs["A"].youtube_url == "https://youtu.be/new"
    assert yt._show_picker.call_count == 1


def test_run_empty_setlist_prints_message(mocker, capsys):
    repo = FakeSongRepo({})
    empty = {"date": "2026-02-15", "moments": {}}
    repos = FakeRepos(songs=repo, history=FakeHistoryRepo(empty))
    mocker.patch.object(yt, "get_repositories", return_value=repos)

    yt.run("2026-02-15", None, None)

    assert "no songs" in capsys.readouterr().out.lower()
