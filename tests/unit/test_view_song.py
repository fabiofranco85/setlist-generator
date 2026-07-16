"""Unit tests for ``cli.commands.view_song.render_song``.

``render_song`` is the pure half of ``display_song``: it returns the rendered
text instead of printing it, so callers can route it to a pager (``songbook
browse``) or straight to stdout (``songbook view-song``).
"""

from __future__ import annotations

import pytest

from cli.commands.view_song import render_song
from library.models import Song


def _make_song(title="Oceanos", key="Bm", energy=3, tags=None):
    return Song(
        title=title,
        tags=dict(tags or {"louvor": 5}),
        energy=energy,
        content=f"### {title} ({key})\n\n{key}      G\nTua voz me chama",
    )


def test_render_song_returns_text_rather_than_printing(capsys):
    out = render_song("Oceanos", _make_song())

    assert isinstance(out, str)
    assert "Oceanos" in out
    assert "Tua voz me chama" in out
    # Nothing may go to stdout — the caller decides where the text lands.
    assert capsys.readouterr().out == ""


def test_render_song_includes_key_and_metadata():
    out = render_song("Oceanos", _make_song())

    assert "Oceanos (Bm)" in out
    assert "louvor(5)" in out
    assert "Energy: 3" in out


def test_render_song_shows_whole_energy_without_decimal():
    # Postgres stores energy as REAL, so a whole number arrives as 3.0.
    # It should read "Energy: 3", matching how the picker renders "[3 mid-]".
    out = render_song("Oceanos", _make_song(energy=3.0))

    assert "Energy: 3 - Moderate-low, reflective, slower" in out
    assert "3.0" not in out


def test_render_song_preserves_fractional_energy():
    # DEFAULT_ENERGY is 2.5, so fractional energy is legitimate and must not
    # be truncated to 2 by a naive int() cast.
    out = render_song("Oceanos", _make_song(energy=2.5))

    assert "Energy: 2.5" in out


def test_render_song_omits_metadata_when_disabled():
    out = render_song("Oceanos", _make_song(), show_metadata=False)

    assert "Tua voz me chama" in out
    assert "louvor(5)" not in out
    assert "Energy:" not in out


def test_render_song_without_chord_content_is_still_rendered():
    song = Song(title="Bare", tags={"louvor": 3}, energy=2, content="")

    out = render_song("Bare", song)

    assert "Bare" in out
    assert "No chord content available" in out


def test_render_song_transposes_and_notes_the_original_key():
    out = render_song("Oceanos", _make_song(key="Bm"), transpose_to="Am")

    assert "original: Bm" in out


def test_render_song_notes_when_already_in_target_key():
    out = render_song("Oceanos", _make_song(key="Bm"), transpose_to="Bm")

    assert "Already in Bm" in out


def test_render_song_raises_on_unparseable_target_key():
    with pytest.raises(ValueError):
        render_song("Oceanos", _make_song(key="Bm"), transpose_to="NotAKey")
