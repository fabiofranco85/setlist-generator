"""Unit tests for ``cli.commands.view_setlist.render_setlist``.

``render_setlist`` is the pure half of ``display_setlist``: it returns the
setlist's header + moments as text instead of printing, so callers can page it
(``songbook setlists``) or print it (``songbook view-setlist``). The FILES
section stays in ``display_setlist`` — it's specific to that command.
"""

from __future__ import annotations

from cli.commands.view_setlist import render_setlist
from library.models import Song


def _songs():
    return {
        "Oceanos": Song(
            title="Oceanos", tags={"louvor": 5}, energy=3.0,
            content="### Oceanos (Bm)\n\nBm G",
        ),
        "Hosana": Song(
            title="Hosana", tags={"louvor": 3}, energy=3.0,
            content="### Hosana (E)\n\nE C#m",
        ),
    }


def _record():
    return {
        "date": "2026-02-15",
        "label": "",
        "moments": {"louvor": ["Oceanos", "Hosana"], "prelúdio": ["Oceanos"]},
    }


def test_render_setlist_returns_text_rather_than_printing(capsys):
    out = render_setlist(_record(), _songs())

    assert isinstance(out, str)
    assert "2026-02-15" in out
    assert capsys.readouterr().out == ""


def test_render_setlist_lists_every_moment_and_song():
    out = render_setlist(_record(), _songs())

    assert "LOUVOR:" in out
    assert "PRELÚDIO:" in out
    assert "- Oceanos" in out
    assert "- Hosana" in out


def test_render_setlist_shows_keys_when_requested():
    out = render_setlist(_record(), _songs(), show_keys=True)

    assert "Oceanos (Bm)" in out
    assert "Hosana (E)" in out


def test_render_setlist_omits_keys_by_default():
    out = render_setlist(_record(), _songs())

    assert "(Bm)" not in out


def test_render_setlist_includes_label_in_header():
    record = _record() | {"label": "evening"}

    out = render_setlist(record, _songs())

    assert "evening" in out


def test_render_setlist_skips_empty_moments():
    record = _record() | {"moments": {"louvor": ["Oceanos"], "crianças": []}}

    out = render_setlist(record, _songs())

    assert "LOUVOR:" in out
    assert "CRIANÇAS:" not in out


def test_render_setlist_excludes_the_files_section():
    # FILES belongs to view-setlist, not to the rendered setlist itself.
    out = render_setlist(_record(), _songs())

    assert "FILES:" not in out
