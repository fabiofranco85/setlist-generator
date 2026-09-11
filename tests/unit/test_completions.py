"""Unit tests for the shell-completion callbacks in ``cli/completions.py``.

These functions run inside a TAB press, so two properties matter beyond
"returns the right values": they must read through the **repository layer**
(the filesystem ``history/`` directory no longer exists — postgres is the
source of truth), and they must never raise, because a traceback printed by
a completion hook corrupts the user's command line.

Fakes are Protocol-shaped in-memory objects, following
``test_browse_command.py`` / ``test_weights_command.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import click
import pytest

from cli import completions
from cli.main import cli as songbook_cli
from library.event_type import EventType
from tests.helpers.factories import make_song


@dataclass
class FakeHistoryRepo:
    entries: list[dict] = field(default_factory=list)

    def get_all(self) -> list[dict]:
        return [dict(e) for e in self.entries]


@dataclass
class FakeEventTypeRepo:
    types: dict[str, EventType] = field(default_factory=dict)

    def get_all(self) -> dict[str, EventType]:
        return dict(self.types)


@dataclass
class FakeSongRepo:
    songs: dict = field(default_factory=dict)

    def get_all(self) -> dict:
        return dict(self.songs)


@dataclass
class FakeRepos:
    history: FakeHistoryRepo = field(default_factory=FakeHistoryRepo)
    event_types: FakeEventTypeRepo = field(default_factory=FakeEventTypeRepo)
    songs: FakeSongRepo = field(default_factory=FakeSongRepo)


@pytest.fixture()
def repos(mocker):
    """Patch ``get_repositories`` and hand the test the fake container."""
    container = FakeRepos(
        history=FakeHistoryRepo(
            [
                {"date": "2026-03-01", "label": "evening", "moments": {}},
                {"date": "2026-03-01", "moments": {}},
                {"date": "2026-02-15", "moments": {}},
                {"date": "2025-12-25", "label": "night", "moments": {}},
            ]
        ),
        event_types=FakeEventTypeRepo(
            {
                "main": EventType(slug="main", name="Main Event"),
                "youth": EventType(slug="youth", name="Youth Service"),
                "christmas": EventType(slug="christmas", name="Christmas"),
            }
        ),
        songs=FakeSongRepo({"Oceanos": make_song(title="Oceanos")}),
    )
    mocker.patch("library.get_repositories", return_value=container)
    return container


def _values(items):
    return [item.value for item in items]


class TestCompleteHistoryDates:
    def test_returns_dates_from_the_history_repository(self, repos):
        result = completions.complete_history_dates(None, None, "")

        assert _values(result) == ["2026-03-01", "2026-02-15", "2025-12-25"]

    def test_filters_by_prefix(self, repos):
        result = completions.complete_history_dates(None, None, "2026-")

        assert _values(result) == ["2026-03-01", "2026-02-15"]

    def test_returns_empty_list_when_the_backend_is_unreachable(self, mocker):
        mocker.patch("library.get_repositories", side_effect=RuntimeError("no DB"))

        assert completions.complete_history_dates(None, None, "2026") == []


class TestCompleteHistoryLabels:
    def test_returns_labels_from_the_history_repository(self, repos):
        result = completions.complete_history_labels(None, None, "")

        assert _values(result) == ["evening", "night"]

    def test_filters_by_prefix(self, repos):
        result = completions.complete_history_labels(None, None, "ev")

        assert _values(result) == ["evening"]

    def test_returns_empty_list_when_the_backend_is_unreachable(self, mocker):
        mocker.patch("library.get_repositories", side_effect=RuntimeError("no DB"))

        assert completions.complete_history_labels(None, None, "") == []


class TestCompleteEventTypeSlugs:
    def test_returns_slugs_from_the_event_type_repository(self, repos):
        result = completions.complete_event_type_slugs(None, None, "")

        assert _values(result) == ["christmas", "main", "youth"]

    def test_filters_by_prefix(self, repos):
        result = completions.complete_event_type_slugs(None, None, "y")

        assert _values(result) == ["youth"]

    def test_describes_each_slug_with_its_display_name(self, repos):
        result = completions.complete_event_type_slugs(None, None, "youth")

        assert result[0].help == "Youth Service"

    def test_returns_empty_list_when_the_backend_is_unreachable(self, mocker):
        mocker.patch("library.get_repositories", side_effect=RuntimeError("no DB"))

        assert completions.complete_event_type_slugs(None, None, "") == []


def _walk_params(command, path=()):
    """Yield ``(command path, param)`` for every param in the CLI tree."""
    here = path + (command.name,)
    for param in command.params:
        yield here, param
    for sub in getattr(command, "commands", {}).values():
        yield from _walk_params(sub, here)


def _params_named(*names):
    """Every param in the songbook CLI whose declaration matches one of names."""
    return [
        (path, param)
        for path, param in _walk_params(songbook_cli)
        if any(name in param.opts or param.name == name for name in names)
    ]


def _complete(param, incomplete):
    """Ask a Click param what it would complete, the way a TAB press does."""
    ctx = click.Context(songbook_cli)
    return [item.value for item in param.shell_complete(ctx, incomplete)]


class TestCompletionsAreWiredAcrossTheCLI:
    """Structural guard: a new command must not ship without its completions.

    Every user-facing value with a known, enumerable set of valid values should
    complete. These tests drive each param through ``shell_complete`` — the same
    entry point Click uses on TAB — so they fail when a command is added (or an
    option copy-pasted) without the matching ``shell_complete=`` callback.
    """

    @pytest.mark.parametrize(
        "declaration, incomplete, expected",
        [
            ("--event-type", "y", ["youth"]),
            ("--date", "2026-", ["2026-03-01", "2026-02-15"]),
            ("--label", "ev", ["evening"]),
            ("--moment", "lou", ["louvor"]),
        ],
    )
    def test_every_option_completes_its_values(
        self, repos, declaration, incomplete, expected
    ):
        found = _params_named(declaration)
        assert found, f"no {declaration} option found — did the CLI change?"

        missing = [
            "/".join(path)
            for path, param in found
            if _complete(param, incomplete) != expected
        ]
        assert missing == [], f"{declaration} does not complete on: {missing}"

    def test_event_type_subcommands_complete_existing_slugs(self, repos):
        """`edit`, `remove` and `moments` act on a slug that already exists.

        `add` is deliberately excluded — it names a brand-new slug, so there is
        nothing to complete.
        """
        group = songbook_cli.commands["event-type"]

        for name in ("edit", "remove", "moments"):
            slug_arg = next(
                p for p in group.commands[name].params
                if isinstance(p, click.Argument) and p.name == "slug"
            )
            assert _complete(slug_arg, "y") == ["youth"], (
                f"event-type {name} <slug> does not complete event types"
            )

    def test_song_arguments_complete_song_names(self, repos):
        found = _params_named("song_name")
        assert found, "no song_name argument found — did the CLI change?"

        missing = [
            "/".join(path)
            for path, param in found
            if _complete(param, "oce") != ["Oceanos"]
        ]
        assert missing == [], f"song argument does not complete on: {missing}"


class TestUnknownCommandsOfferNothing:
    """A typo'd command must not be completed as if it were valid.

    Click resolves an unknown command name against the root group under
    ``resilient_parsing`` (it suppresses the "No such command" failure during
    completion), so ``_resolve_context`` hands back the *root* context with the
    bogus token dropped. Completion then offers the whole top-level command
    list: ``songbook songs a<TAB>`` becomes ``songbook songs add``, which fails
    at real parse time. Nothing should be offered after a token that cannot be
    a command.
    """

    @staticmethod
    def _complete_args(args, incomplete):
        """Drive the same entry point a TAB press goes through."""
        from click.shell_completion import ShellComplete

        completer = ShellComplete(songbook_cli, {}, "songbook", "_SONGBOOK_COMPLETE")
        return [item.value for item in completer.get_completions(args, incomplete)]

    def test_nothing_is_offered_after_an_unknown_command(self, repos):
        assert self._complete_args(["songs"], "a") == []

    def test_nothing_is_offered_after_an_unknown_command_with_no_prefix(self, repos):
        assert self._complete_args(["nonsense"], "") == []

    def test_nothing_is_offered_after_an_unknown_subcommand(self, repos):
        assert self._complete_args(["event-type", "bogus"], "a") == []

    def test_top_level_commands_still_complete(self, repos):
        assert "add" in self._complete_args([], "a")

    def test_a_valid_command_still_completes_its_options(self, repos):
        assert "--moment" in self._complete_args(["remove"], "--mom")

    def test_a_valid_subcommand_still_completes(self, repos):
        assert "list" in self._complete_args(["event-type"], "li")

    def test_a_group_option_before_the_command_does_not_block_completion(self, repos):
        assert "add" in self._complete_args(["--verbose"], "a")
