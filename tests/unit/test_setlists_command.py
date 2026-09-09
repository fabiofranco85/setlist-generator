"""Unit tests for the ``songbook setlists`` CLI command.

Covers the pure helpers (row building, input normalization) and the loop
orchestration: view / delete (``d``) / re-use (``r``) / quit.

Following ``test_weights_command.py`` and ``test_browse_command.py``: real
in-memory fakes, with only the UI boundaries stubbed via ``mocker``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cli.commands import setlists as setlists_cmd
from library.event_type import EventType
from library.models import Song
from tests.helpers.factories import make_song


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeHistoryRepo:
    records: list[dict]

    def get_all(self):
        # Real repos return newest-first, already sorted.
        return [dict(r) for r in self.records]

    def exists(self, date, label="", event_type=""):
        return any(
            r["date"] == date
            and (r.get("label") or "") == label
            and (r.get("event_type") or "") == event_type
            for r in self.records
        )

    def delete(self, date, label="", event_type=""):
        before = len(self.records)
        self.records = [
            r
            for r in self.records
            if not (
                r["date"] == date
                and (r.get("label") or "") == label
                and (r.get("event_type") or "") == event_type
            )
        ]
        if len(self.records) == before:
            raise KeyError(f"{date}/{label}")

    def save(self, setlist):
        self.records.insert(
            0,
            {
                "date": setlist.date,
                "label": setlist.label,
                "event_type": setlist.event_type,
                "moments": dict(setlist.moments),
            },
        )


@dataclass
class FakeOutputRepo:
    deleted: list = field(default_factory=list)
    saved: list = field(default_factory=list)

    def delete_outputs(self, date, label="", event_type=""):
        self.deleted.append((date, label, event_type))
        return []

    def save_markdown(self, date, content, label="", event_type=""):
        self.saved.append((date, label, event_type))
        return f"output/{date}.md"


@dataclass
class FakeSongRepo:
    songs: dict[str, Song] = field(default_factory=dict)

    def get_all(self):
        return dict(self.songs)


@dataclass
class FakeEventTypeRepo:
    types: dict[str, EventType] = field(default_factory=dict)

    def get(self, slug):
        return self.types.get(slug)

    def get_all(self):
        return dict(self.types)

    def get_default_slug(self):
        return "main"


@dataclass
class FakeRepos:
    history: FakeHistoryRepo
    output: FakeOutputRepo = field(default_factory=FakeOutputRepo)
    songs: FakeSongRepo = field(default_factory=FakeSongRepo)
    event_types: FakeEventTypeRepo = field(default_factory=FakeEventTypeRepo)


def _records():
    """Newest-first, mixing labeled / unlabeled / event-typed.

    Mirrors the real backend: `label` and `event_type` arrive as None or are
    absent entirely — never "".
    """
    return [
        {"date": "2026-09-13", "event_type": "ceia", "moments": {"louvor": ["A", "B"]}},
        {"date": "2026-07-19", "label": "culto_dia", "event_type": None,
         "moments": {"louvor": ["A"], "prelúdio": ["B"]}},
        {"date": "2026-07-19", "label": "culto_noite", "event_type": None,
         "moments": {"louvor": ["C"]}},
        {"date": "2026-06-28", "label": None, "event_type": None,
         "moments": {"louvor": ["D", "E", "F"]}},
    ]


@pytest.fixture()
def repos():
    return FakeRepos(history=FakeHistoryRepo(_records()))


@pytest.fixture()
def wired(mocker, repos):
    mocker.patch.object(setlists_cmd, "get_repositories", return_value=repos)
    mocker.patch.object(setlists_cmd, "_is_interactive", return_value=True)
    picker = mocker.patch.object(setlists_cmd, "_show_picker")
    pager = mocker.patch.object(setlists_cmd.click, "echo_via_pager")
    return picker, pager, repos


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_record_key_normalizes_missing_and_none_fields():
    # The real backend hands back None / absent keys, not "".
    assert setlists_cmd._record_key({"date": "2026-01-01"}) == ("2026-01-01", "", "")
    assert setlists_cmd._record_key(
        {"date": "2026-01-01", "label": None, "event_type": None}
    ) == ("2026-01-01", "", "")
    assert setlists_cmd._record_key(
        {"date": "2026-01-01", "label": "evening", "event_type": "ceia"}
    ) == ("2026-01-01", "evening", "ceia")


def test_song_count_totals_across_moments():
    assert setlists_cmd._song_count({"moments": {"louvor": ["A", "B"], "p": ["C"]}}) == 3
    assert setlists_cmd._song_count({"moments": {}}) == 0
    assert setlists_cmd._song_count({}) == 0


def test_build_rows_preserves_newest_first_order():
    rows, records = setlists_cmd._build_rows(_records())

    assert [r["date"] for r in records] == [
        "2026-09-13", "2026-07-19", "2026-07-19", "2026-06-28",
    ]
    assert rows[0].startswith("2026-09-13")


def test_build_rows_shows_label_song_count_and_event_type():
    rows, _ = setlists_cmd._build_rows(_records())

    assert "ceia" in rows[0]           # event type surfaced
    assert "2 songs" in rows[0]
    assert "culto_dia" in rows[1]
    assert "3 songs" in rows[3]


def test_build_rows_renders_unlabeled_setlists_without_crashing():
    # label=None must not leak a literal "None" into the row.
    rows, _ = setlists_cmd._build_rows(_records())

    assert "None" not in rows[0]
    assert "None" not in rows[3]


def test_build_rows_singular_song_label():
    rows, _ = setlists_cmd._build_rows(
        [{"date": "2026-01-01", "moments": {"louvor": ["Only"]}}]
    )
    assert "1 song" in rows[0]
    assert "1 songs" not in rows[0]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-02-15", "2026-02-15"),
        ("  2026-02-15 ", "2026-02-15"),
        # Lenient on input, canonical on output: an unpadded date is
        # unambiguous, so accept it and normalize rather than nitpick.
        ("2026-2-15", "2026-02-15"),
        ("15/02/2026", None),
        ("not-a-date", None),
        ("", None),
        ("2026-02-30", None),  # real calendar validation, not just a regex
    ],
)
def test_normalize_date(raw, expected):
    assert setlists_cmd._normalize_date(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("evening", "evening"),
        ("EVENING", "evening"),
        ("  evening  ", "evening"),
        ("culto_dia", "culto_dia"),
        ("culto-dia", "culto-dia"),
        ("", ""),          # blank = no label, valid
        ("-bad", None),
        ("has space", None),
        ("x" * 31, None),
    ],
)
def test_normalize_label(raw, expected):
    assert setlists_cmd._normalize_label(raw) == expected


# ---------------------------------------------------------------------------
# Loop: view
# ---------------------------------------------------------------------------


def test_enter_pages_the_setlist_then_reopens_until_quit(wired):
    picker, pager, _ = wired
    picker.side_effect = [(0, "enter"), (1, "enter"), None]

    setlists_cmd.run()

    assert picker.call_count == 3
    assert pager.call_count == 2


def test_quitting_immediately_pages_nothing(wired):
    picker, pager, _ = wired
    picker.side_effect = [None]

    setlists_cmd.run()

    assert pager.call_count == 0


def test_paged_view_contains_the_setlists_songs(wired):
    picker, pager, _ = wired
    picker.side_effect = [(3, "enter"), None]

    setlists_cmd.run()

    text = pager.call_args[0][0]
    assert "2026-06-28" in text
    assert "- D" in text


def test_empty_history_exits_without_opening_picker(mocker):
    mocker.patch.object(
        setlists_cmd, "get_repositories", return_value=FakeRepos(FakeHistoryRepo([]))
    )
    picker = mocker.patch.object(setlists_cmd, "_show_picker")

    with pytest.raises(SystemExit) as exc:
        setlists_cmd.run()

    assert exc.value.code == 1
    assert picker.call_count == 0


def test_non_interactive_is_one_shot(mocker, repos):
    mocker.patch.object(setlists_cmd, "get_repositories", return_value=repos)
    mocker.patch.object(setlists_cmd, "_is_interactive", return_value=False)
    picker = mocker.patch.object(
        setlists_cmd, "_show_picker", return_value=(0, "enter")
    )
    pager = mocker.patch.object(setlists_cmd.click, "echo_via_pager")

    setlists_cmd.run()

    assert picker.call_count == 1
    assert pager.call_count == 1


# ---------------------------------------------------------------------------
# Loop: delete (d)
# ---------------------------------------------------------------------------


def test_d_deletes_after_confirmation(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(1, "d"), None]
    mocker.patch.object(setlists_cmd.click, "confirm", return_value=True)

    setlists_cmd.run()

    keys = [setlists_cmd._record_key(r) for r in repos.history.records]
    assert ("2026-07-19", "culto_dia", "") not in keys
    assert len(repos.history.records) == 3
    # Outputs must be cleaned up too, not just the history record.
    assert repos.output.deleted == [("2026-07-19", "culto_dia", "")]


def test_d_declined_deletes_nothing(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(1, "d"), None]
    mocker.patch.object(setlists_cmd.click, "confirm", return_value=False)

    setlists_cmd.run()

    assert len(repos.history.records) == 4
    assert repos.output.deleted == []


def test_d_on_event_type_setlist_routes_the_event_type(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(0, "d"), None]
    mocker.patch.object(setlists_cmd.click, "confirm", return_value=True)

    setlists_cmd.run()

    # event_type must be threaded through, else the wrong record/files go.
    assert repos.output.deleted == [("2026-09-13", "", "ceia")]


def test_deleting_the_last_setlist_exits_cleanly(mocker):
    repos = FakeRepos(
        FakeHistoryRepo([{"date": "2026-01-01", "moments": {"louvor": ["A"]}}])
    )
    mocker.patch.object(setlists_cmd, "get_repositories", return_value=repos)
    mocker.patch.object(setlists_cmd, "_is_interactive", return_value=True)
    mocker.patch.object(setlists_cmd, "_show_picker", side_effect=[(0, "d"), None])
    mocker.patch.object(setlists_cmd.click, "confirm", return_value=True)
    mocker.patch.object(setlists_cmd.click, "echo_via_pager")

    # List becomes empty mid-loop: must not raise, must not re-open the picker.
    setlists_cmd.run()

    assert repos.history.records == []


# ---------------------------------------------------------------------------
# Loop: re-use (r)
# ---------------------------------------------------------------------------


def test_r_copies_the_setlist_to_the_requested_date(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(3, "r"), None]
    mocker.patch.object(setlists_cmd, "_prompt_reuse_target", return_value=("2026-12-25", "", ""))

    setlists_cmd.run()

    new = repos.history.records[0]
    assert new["date"] == "2026-12-25"
    assert new["label"] == ""
    # Same songs as the source setlist.
    assert new["moments"] == {"louvor": ["D", "E", "F"]}
    # Markdown regenerated for the new setlist.
    assert repos.output.saved == [("2026-12-25", "", "")]


def test_r_applies_the_requested_label(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(3, "r"), None]
    mocker.patch.object(
        setlists_cmd, "_prompt_reuse_target", return_value=("2026-12-25", "evening", "")
    )

    setlists_cmd.run()

    assert repos.history.records[0]["label"] == "evening"


def test_r_keeps_the_source_event_type_when_it_is_chosen(wired, mocker):
    """The menu starts on the source's type, so accepting it must round-trip."""
    picker, _, repos = wired
    picker.side_effect = [(0, "r"), None]  # the 'ceia' setlist
    mocker.patch.object(
        setlists_cmd, "_prompt_reuse_target", return_value=("2026-12-25", "", "ceia")
    )

    setlists_cmd.run()

    assert repos.history.records[0]["event_type"] == "ceia"
    assert repos.output.saved == [("2026-12-25", "", "ceia")]


def test_r_cancelled_saves_nothing(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(3, "r"), None]
    mocker.patch.object(setlists_cmd, "_prompt_reuse_target", return_value=None)

    setlists_cmd.run()

    assert len(repos.history.records) == 4
    assert repos.output.saved == []


def test_r_onto_an_existing_setlist_asks_before_overwriting(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(3, "r"), None]
    # Target 2026-09-13/ceia already exists -> must confirm, not clobber.
    mocker.patch.object(
        setlists_cmd, "_prompt_reuse_target", return_value=("2026-07-19", "culto_dia", "")
    )
    confirm = mocker.patch.object(setlists_cmd.click, "confirm", return_value=False)

    setlists_cmd.run()

    assert confirm.called
    assert repos.output.saved == []
    assert len(repos.history.records) == 4


def test_r_does_not_mutate_the_source_setlists_moments(wired, mocker):
    picker, _, repos = wired
    picker.side_effect = [(3, "r"), None]
    mocker.patch.object(setlists_cmd, "_prompt_reuse_target", return_value=("2026-12-25", "", ""))

    setlists_cmd.run()

    source = next(r for r in repos.history.records if r["date"] == "2026-06-28")
    new = repos.history.records[0]
    new["moments"]["louvor"].append("MUTATED")
    assert source["moments"]["louvor"] == ["D", "E", "F"]


# ---------------------------------------------------------------------------
# Loop: re-use into another event type
# ---------------------------------------------------------------------------


def _event_types() -> dict[str, EventType]:
    """Three shapes: default, a smaller one, and a bigger one."""
    return {
        "main": EventType(slug="main", name="Main Event",
                          moments={"louvor": 2, "prelúdio": 1}),
        "ceia": EventType(slug="ceia", name="Ceia", moments={"louvor": 2}),
        "youth": EventType(slug="youth", name="Youth Service",
                           moments={"louvor": 3, "crianças": 1}),
    }


def _songs() -> dict[str, Song]:
    return {
        "A": make_song(title="A", tags={"louvor": 3}, energy=1),
        "B": make_song(title="B", tags={"louvor": 3}, energy=2),
        "C": make_song(title="C", tags={"louvor": 3}, energy=3),
        "D": make_song(title="D", tags={"louvor": 3}, energy=1),
        "E": make_song(title="E", tags={"louvor": 3}, energy=2),
        "F": make_song(title="F", tags={"louvor": 3}, energy=4),
        "Kids One": make_song(title="Kids One", tags={"crianças": 3}, energy=2),
        "Kids Two": make_song(title="Kids Two", tags={"crianças": 3}, energy=2),
        "Youth Only": make_song(title="Youth Only", tags={"louvor": 5}, energy=2,
                                event_types=["youth"]),
    }


@pytest.fixture()
def rich_repos():
    """Repos with real songs and event types, for the cross-type paths."""
    return FakeRepos(
        history=FakeHistoryRepo(_records()),
        songs=FakeSongRepo(_songs()),
        event_types=FakeEventTypeRepo(_event_types()),
    )


def _reuse_into(mocker, record, repos, event_type, date="2026-12-25", label=""):
    """Run ``_reuse`` with the prompts answered up front."""
    mocker.patch.object(
        setlists_cmd, "_prompt_reuse_target", return_value=(date, label, event_type)
    )
    setlists_cmd._reuse(record, repos)
    return repos.history.records[0]


# --- the event type prompt -------------------------------------------------


def test_reuse_prompt_asks_for_date_event_type_then_label(mocker, rich_repos):
    mocker.patch.object(setlists_cmd.click, "prompt", side_effect=["2026-12-25", "evening"])
    mocker.patch.object(setlists_cmd, "_pick_event_type", return_value="youth")

    assert setlists_cmd._prompt_reuse_target(
        _records()[0], rich_repos
    ) == ("2026-12-25", "evening", "youth")


def test_cancelling_the_event_type_menu_cancels_the_reuse(mocker, rich_repos):
    mocker.patch.object(setlists_cmd.click, "prompt", side_effect=["2026-12-25", ""])
    mocker.patch.object(setlists_cmd, "_pick_event_type", return_value=None)

    assert setlists_cmd._prompt_reuse_target(_records()[0], rich_repos) is None


def test_event_type_menu_starts_on_the_source_type(mocker, rich_repos):
    menu = mocker.patch.object(setlists_cmd, "_show_menu", return_value=0)

    setlists_cmd._pick_event_type(rich_repos, "ceia")

    rows = menu.call_args[0][0]
    assert rows[menu.call_args.kwargs["cursor_index"]].startswith("ceia")
    assert any(row.startswith("youth") for row in rows)


def test_picking_the_default_event_type_yields_the_empty_slug(mocker, rich_repos):
    """The repo layer stores default-type setlists with an empty slug.

    Saving one as "main" would write to the same file while comparing unequal
    in `exists()`, so the overwrite guard would wave through a clobber.
    """
    mocker.patch.object(setlists_cmd, "_show_menu", return_value=0)  # "main" sorts first

    assert setlists_cmd._pick_event_type(rich_repos, "ceia") == ""


def test_event_type_prompt_is_skipped_when_the_backend_has_none(mocker, repos):
    menu = mocker.patch.object(setlists_cmd, "_show_menu")
    repos.event_types = None

    assert setlists_cmd._pick_event_type(repos, "ceia") == "ceia"
    assert menu.call_count == 0


# --- reconciliation --------------------------------------------------------


def test_same_event_type_copies_the_songs_and_never_prompts(mocker, rich_repos):
    pick = mocker.patch.object(setlists_cmd, "pick_song")

    new = _reuse_into(mocker, _records()[0], rich_repos, "ceia")

    assert new["moments"] == {"louvor": ["A", "B"]}
    assert pick.call_count == 0


def test_reuse_into_a_smaller_event_type_drops_the_overflow(mocker, rich_repos):
    source = {"date": "2026-06-28", "moments": {"louvor": ["D", "E", "F"]}}

    new = _reuse_into(mocker, source, rich_repos, "ceia")

    assert new["moments"] == {"louvor": ["D", "E"]}
    assert new["event_type"] == "ceia"


def test_reuse_drops_moments_the_target_event_type_lacks(mocker, rich_repos):
    source = {"date": "2026-07-19", "moments": {"louvor": ["A"], "prelúdio": ["B"]}}
    mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    new = _reuse_into(mocker, source, rich_repos, "ceia")

    assert "prelúdio" not in new["moments"]


def test_reuse_prompts_once_per_empty_slot(mocker, rich_repos):
    # ceia louvor(2) -> youth louvor(3) + crianças(1): two slots to fill.
    pick = mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    _reuse_into(mocker, _records()[0], rich_repos, "youth")

    assert pick.call_count == 2
    moments_asked = {call.kwargs["moment_filter"] for call in pick.call_args_list}
    assert moments_asked == {"louvor", "crianças"}


def test_a_picked_song_lands_in_its_moment(mocker, rich_repos):
    mocker.patch.object(setlists_cmd, "pick_song", side_effect=["C", "Kids Two"])

    new = _reuse_into(mocker, _records()[0], rich_repos, "youth")

    assert set(new["moments"]["louvor"]) == {"A", "B", "C"}
    assert new["moments"]["crianças"] == ["Kids Two"]


def test_a_blank_slot_is_auto_filled_from_the_moments_candidates(mocker, rich_repos):
    mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    new = _reuse_into(mocker, _records()[0], rich_repos, "youth")

    assert len(new["moments"]["louvor"]) == 3
    assert new["moments"]["crianças"][0] in {"Kids One", "Kids Two"}


def test_auto_fill_never_repeats_a_song_already_in_the_setlist(mocker, rich_repos):
    mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    new = _reuse_into(mocker, _records()[0], rich_repos, "youth")

    placed = [s for songs in new["moments"].values() for s in songs]
    assert len(placed) == len(set(placed))


def test_songs_bound_to_another_event_type_are_dropped(mocker, rich_repos):
    source = {"date": "2026-09-13", "event_type": "youth",
              "moments": {"louvor": ["A", "Youth Only"]}}
    mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    new = _reuse_into(mocker, source, rich_repos, "ceia")

    assert "Youth Only" not in new["moments"]["louvor"]
    # The freed slot is refilled rather than left short.
    assert len(new["moments"]["louvor"]) == 2


def test_moment_order_follows_the_target_event_type(mocker, rich_repos):
    source = {"date": "2026-09-13", "moments": {"crianças": ["Kids One"]}}
    mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    new = _reuse_into(mocker, source, rich_repos, "youth")

    assert list(new["moments"].keys()) == ["louvor", "crianças"]


def test_the_picker_only_offers_songs_not_already_placed(mocker, rich_repos):
    pick = mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    _reuse_into(mocker, _records()[0], rich_repos, "youth")

    louvor_call = next(
        c for c in pick.call_args_list if c.kwargs["moment_filter"] == "louvor"
    )
    assert {"A", "B"} <= louvor_call.kwargs["exclude"]
    # Youth-bound songs are legal here; songs bound elsewhere never reach the pool.
    assert "Youth Only" in louvor_call.args[0]


def test_markdown_is_written_under_the_new_event_type(mocker, rich_repos):
    mocker.patch.object(setlists_cmd, "pick_song", return_value=None)

    _reuse_into(mocker, _records()[0], rich_repos, "youth", label="evening")

    assert rich_repos.output.saved == [("2026-12-25", "evening", "youth")]
