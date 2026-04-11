"""Tests for the lyrics-only chord filter used by the no-chords PDF variant.

The filter strips pure chord lines while preserving lyric lines and standalone
section markers (like ``[Refrão]``). It reuses ``is_chord_line()`` from
``library/transposer.py`` so the classification is consistent with
transposition behavior.
"""

from library.pdf_formatter import _filter_out_chord_lines


def test_filter_removes_pure_chord_lines():
    content = "G   D   Em   C\nTua voz me chama"
    assert _filter_out_chord_lines(content) == "Tua voz me chama"


def test_filter_preserves_standalone_section_markers():
    content = "[Refrão]\nCristo é a rocha"
    # Standalone marker has no chord tokens after stripping the brackets,
    # so is_chord_line returns False and the line is preserved.
    assert _filter_out_chord_lines(content) == "[Refrão]\nCristo é a rocha"


def test_filter_strips_marker_plus_chords():
    content = "[Intro] G D Em\nCristo é a rocha"
    assert _filter_out_chord_lines(content) == "Cristo é a rocha"


def test_filter_preserves_portuguese_em_as_word():
    # "Em" in Portuguese means "in" — must not be confused with E-minor.
    # is_chord_line rejects this because not every token is a chord.
    content = "Em Deus nós confiamos"
    assert _filter_out_chord_lines(content) == "Em Deus nós confiamos"


def test_filter_preserves_blank_lines_between_verses():
    content = (
        "G       D\n"
        "Verso um\n"
        "\n"
        "C       G\n"
        "Verso dois"
    )
    expected = "Verso um\n\nVerso dois"
    assert _filter_out_chord_lines(content) == expected


def test_filter_rstrips_trailing_whitespace_on_kept_lines():
    content = "Tua voz me chama   \n   Lyric com espaço inicial   "
    result = _filter_out_chord_lines(content)
    # Trailing whitespace gone; leading whitespace left alone (may be meaningful).
    assert result == "Tua voz me chama\n   Lyric com espaço inicial"


def test_filter_handles_empty_content():
    assert _filter_out_chord_lines("") == ""


def test_filter_handles_complex_chord_patterns():
    # Extended chords like F7M(9), Em7(11)/B should all be stripped.
    content = (
        "F7M(9)  Em7(11)/B  A7(13-)\n"
        "Jesus, filho de Deus"
    )
    assert _filter_out_chord_lines(content) == "Jesus, filho de Deus"


def test_filter_strips_parenthesized_chord_alternation():
    # Pattern observed in real chord files: chords followed by an
    # alternative progression in parentheses. The inner parens tokens
    # don't individually parse as chords, so this requires the
    # "mixed chord line" heuristic.
    content = (
        "C            D          G      (Dm  G7)\n"
        "Como oferta viva em teu altar"
    )
    assert _filter_out_chord_lines(content) == "Como oferta viva em teu altar"


def test_filter_strips_chords_with_slash_inside_parens():
    # Real pattern: D7(4/9) — the chord regex doesn't parse this fully
    # because of the inner slash, so is_chord_line rejects the whole line.
    # The mixed-line heuristic must catch it.
    content = (
        "   Am  Bm7  C7M  D7(4/9)  G  Dm7  G7\n"
        "Estar ao teu lado, senhor"
    )
    assert _filter_out_chord_lines(content) == "Estar ao teu lado, senhor"


def test_filter_strips_parenthesized_chord_wrap():
    # Pattern: ( F#m B  E/G# A7M ) — chord progression wrapped in parens
    # as loose grouping.
    content = (
        "( F#m B  E/G# A7M )\n"
        "Tua presença é o que me basta"
    )
    assert _filter_out_chord_lines(content) == "Tua presença é o que me basta"


def test_filter_strips_chord_plus_riff_annotation():
    # Pattern: chords followed by a text annotation like "Riff".
    content = (
        "       Eb    F      Bb   Riff\n"
        "Vem reinar em mim, Senhor"
    )
    assert _filter_out_chord_lines(content) == "Vem reinar em mim, Senhor"
