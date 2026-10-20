"""Tests for the lyrics-only chord filter used by the no-chords PDF variant.

The filter strips pure chord lines while preserving lyric lines and standalone
section markers (like ``[Refrão]``). It reuses ``is_chord_line()`` from
``library/transposer.py`` so the classification is consistent with
transposition behavior.
"""

from library.pdf_formatter import _filter_out_chord_lines, _strip_alignment_padding


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
    # Real pattern: D7(4/9). The slash inside the parens is part of the
    # extension, not a bass note, so the line is a plain chord line.
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


# --- Alignment padding (spaces / underscores added so chords land on syllables) ---


def test_padding_removes_underscores_inside_words():
    content = "Coroa__mos a Ti, ó rei Jesus\nA___le____lu____ia"
    assert _strip_alignment_padding(content) == "Coroamos a Ti, ó rei Jesus\nAleluia"


def test_padding_collapses_runs_of_spaces_between_words():
    content = "Quero Te ver,     quero Te ver"
    assert _strip_alignment_padding(content) == "Quero Te ver, quero Te ver"


def test_padding_strips_leading_spaces():
    content = "    Firme, oh Deus, está o meu cora__ção"
    assert _strip_alignment_padding(content) == "Firme, oh Deus, está o meu coração"


def test_padding_handles_underscore_and_spaces_together():
    content = "Vou  lu____tar e vencer"
    assert _strip_alignment_padding(content) == "Vou lutar e vencer"


def test_padding_drops_underscore_run_standing_alone_between_words():
    content = "Santo ___ Santo"
    assert _strip_alignment_padding(content) == "Santo Santo"


def test_padding_keeps_hyphens():
    # A hyphen can be real Portuguese ("tocar-Te"), so it is never touched.
    content = "Quero tocar - Te\nDa Tua presen - ça"
    assert _strip_alignment_padding(content) == content


def test_padding_preserves_blank_lines_and_section_markers():
    content = "[Refrão]\nSanto  Santo\n\nVerso   dois"
    assert _strip_alignment_padding(content) == "[Refrão]\nSanto Santo\n\nVerso dois"


def test_padding_handles_empty_content():
    assert _strip_alignment_padding("") == ""


def test_filter_strips_chord_lines_with_slash_inside_parens():
    content = "    A               B7(4/9)\nEu continuo olhando para Ti"
    assert _filter_out_chord_lines(content) == "Eu continuo olhando para Ti"


def test_filter_strips_guitar_tab_lines():
    content = (
        "[Solo]\n"
        "E|-----7--7/9-------------------------|\n"
        "B|-/9----------------7/9--9~----------|\n"
        "Tua graça me basta"
    )
    assert _filter_out_chord_lines(content) == "[Solo]\nTua graça me basta"
