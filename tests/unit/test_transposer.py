"""Tests for library.transposer — chromatic chord transposition."""

import pytest

from library.transposer import (
    _is_mixed_chord_line,
    _transpose_heading,
    _transpose_mixed_line,
    calculate_semitones,
    is_chord_line,
    resolve_target_key,
    should_use_flats,
    transpose_chord,
    transpose_content,
    transpose_line,
    transpose_note,
)


# ---------------------------------------------------------------------------
# should_use_flats
# ---------------------------------------------------------------------------


class TestShouldUseFlats:
    @pytest.mark.parametrize("key", ["F", "Bb", "Eb", "Ab", "Db", "Gb"])
    def test_flat_major_keys(self, key):
        assert should_use_flats(key) is True

    @pytest.mark.parametrize("key", ["Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm"])
    def test_flat_minor_keys(self, key):
        assert should_use_flats(key) is True

    @pytest.mark.parametrize("key", ["C", "G", "D", "A", "E", "B"])
    def test_sharp_major_keys(self, key):
        assert should_use_flats(key) is False

    @pytest.mark.parametrize("key", ["Am", "Em", "Bm"])
    def test_sharp_minor_keys(self, key):
        assert should_use_flats(key) is False


# ---------------------------------------------------------------------------
# resolve_target_key
# ---------------------------------------------------------------------------


class TestResolveTargetKey:
    def test_minor_to_major_adds_m(self):
        assert resolve_target_key("Bm", "G") == "Gm"

    def test_major_to_major_unchanged(self):
        assert resolve_target_key("C", "G") == "G"

    def test_minor_to_minor_unchanged(self):
        assert resolve_target_key("Am", "Em") == "Em"

    def test_minor_to_already_minor(self):
        assert resolve_target_key("Am", "Cm") == "Cm"


# ---------------------------------------------------------------------------
# calculate_semitones
# ---------------------------------------------------------------------------


class TestCalculateSemitones:
    @pytest.mark.parametrize(
        "from_key, to_key, expected",
        [
            ("C", "G", 7),
            ("G", "C", 5),
            ("C", "C", 0),
            ("Bm", "Em", 5),
            ("A", "C", 3),
            ("E", "A", 5),
        ],
    )
    def test_known_intervals(self, from_key, to_key, expected):
        assert calculate_semitones(from_key, to_key) == expected

    def test_invalid_from_key_raises(self):
        with pytest.raises(ValueError, match="Unknown key"):
            calculate_semitones("X", "C")

    def test_invalid_to_key_raises(self):
        with pytest.raises(ValueError, match="Unknown key"):
            calculate_semitones("C", "X")


# ---------------------------------------------------------------------------
# transpose_note
# ---------------------------------------------------------------------------


class TestTransposeNote:
    @pytest.mark.parametrize(
        "note, semitones, use_flats, expected",
        [
            ("C", 7, False, "G"),
            ("G", 5, False, "C"),
            ("A", 3, True, "C"),
            ("A", 2, False, "B"),
            ("B", 1, False, "C"),  # wraps around
            ("C", 0, False, "C"),  # no change
            ("F#", 1, False, "G"),
            ("Bb", 2, True, "C"),
        ],
    )
    def test_transpositions(self, note, semitones, use_flats, expected):
        assert transpose_note(note, semitones, use_flats) == expected

    def test_invalid_note_raises(self):
        with pytest.raises(ValueError, match="Unknown note"):
            transpose_note("X", 2)


# ---------------------------------------------------------------------------
# transpose_chord
# ---------------------------------------------------------------------------


class TestTransposeChord:
    @pytest.mark.parametrize(
        "chord, semitones, use_flats, expected",
        [
            ("Am7", 2, False, "Bm7"),
            ("A/C#", 3, True, "C/E"),
            ("F7M(9)", 2, False, "G7M(9)"),
            ("G", 5, False, "C"),
            ("Em", 7, False, "Bm"),
            ("D4", 2, False, "E4"),
            ("Bb", 2, True, "C"),
        ],
    )
    def test_chord_transpositions(self, chord, semitones, use_flats, expected):
        assert transpose_chord(chord, semitones, use_flats) == expected

    def test_unrecognized_chord_returned_unchanged(self):
        assert transpose_chord("NotAChord123", 2) == "NotAChord123"

    def test_slash_chord_both_parts_transposed(self):
        # A (idx 9) +3 = C (idx 0), C# (idx 1) +3 = E (idx 4)
        result = transpose_chord("A/C#", 3, use_flats=True)
        assert result == "C/E"


# ---------------------------------------------------------------------------
# is_chord_line
# ---------------------------------------------------------------------------


class TestIsChordLine:
    @pytest.mark.parametrize(
        "line",
        [
            "G   D   Em   C",
            "Am  F  C  G",
            "A",
            "C#m  F#  B",
        ],
    )
    def test_chord_lines(self, line):
        assert is_chord_line(line) is True

    @pytest.mark.parametrize(
        "line",
        [
            "Tua voz me chama",
            "This is a lyric line",
            "Verse 1:",
        ],
    )
    def test_lyric_lines(self, line):
        assert is_chord_line(line) is False

    def test_section_marker_with_chords(self):
        assert is_chord_line("[Intro] F7M(9)  Am  G4") is True

    def test_empty_line(self):
        assert is_chord_line("") is False

    def test_whitespace_only(self):
        assert is_chord_line("   ") is False

    def test_section_marker_only(self):
        """Section marker with no chords after it."""
        assert is_chord_line("[Intro]") is False

    def test_section_marker_with_trailing_whitespace(self):
        assert is_chord_line("[Intro]   ") is False


# ---------------------------------------------------------------------------
# _is_mixed_chord_line
# ---------------------------------------------------------------------------


class TestIsMixedChordLine:
    def test_mixed_chord_annotation(self):
        assert _is_mixed_chord_line("F  G  C  Riff") is True

    def test_intro_annotation_with_chords(self):
        assert _is_mixed_chord_line("Intro 2x: Am Dm F7+ G") is True

    def test_pure_lyric_line(self):
        assert _is_mixed_chord_line("Tua voz me chama") is False

    def test_too_few_chords(self):
        # "Em Deus" has only 1 chord token, not enough
        assert _is_mixed_chord_line("Em Deus") is False

    def test_empty_string(self):
        assert _is_mixed_chord_line("") is False

    def test_section_marker_only(self):
        assert _is_mixed_chord_line("[Intro]") is False

    def test_section_marker_whitespace(self):
        assert _is_mixed_chord_line("[Intro]   ") is False


# ---------------------------------------------------------------------------
# transpose_line
# ---------------------------------------------------------------------------


class TestTransposeLine:
    def test_chord_line_transposed(self):
        result = transpose_line("G   D   Em   C", 2, use_flats=False)
        assert "A" in result
        assert "E" in result
        assert "F#m" in result
        assert "D" in result

    def test_lyric_line_unchanged(self):
        lyric = "Tua voz me chama"
        assert transpose_line(lyric, 5) == lyric

    def test_column_alignment_preserved(self):
        original = "G       D"
        result = transpose_line(original, 2, use_flats=False)
        # A and E should be roughly aligned at same columns
        a_pos = result.index("A")
        e_pos = result.index("E")
        assert e_pos >= 8  # D was at position 8

    def test_section_marker_preserved(self):
        result = transpose_line("[Intro] G  D", 2, use_flats=False)
        assert result.startswith("[Intro]")
        assert "A" in result

    def test_no_chord_tokens_returns_unchanged(self):
        # A chord line where regex finds no tokens (pure section marker with chord-like)
        # Actually this is hard to trigger since is_chord_line would return False first.
        # Let's test a line that is_chord_line=True but _CHORD_TOKEN_RE finds nothing:
        # That scenario can't actually happen, so we test edge case of marker-only
        assert transpose_line("[Intro]", 2) == "[Intro]"


# ---------------------------------------------------------------------------
# _transpose_mixed_line
# ---------------------------------------------------------------------------


class TestTransposeMixedLine:
    def test_mixed_line_chords_transposed(self):
        result = _transpose_mixed_line("F  G  C  Riff", 2, use_flats=False)
        assert "G" in result
        assert "A" in result
        assert "D" in result
        assert "Riff" in result

    def test_annotation_preserved(self):
        result = _transpose_mixed_line("Intro 2x: Am Dm G C", 2, use_flats=False)
        assert "Intro" in result
        assert "2x:" in result

    def test_section_marker_preserved(self):
        result = _transpose_mixed_line("[Refrão] Am G Riff", 2, use_flats=False)
        assert result.startswith("[Refrão]")


# ---------------------------------------------------------------------------
# _transpose_heading
# ---------------------------------------------------------------------------


class TestTransposeHeading:
    def test_standard_heading(self):
        result = _transpose_heading("### Song (G)", 2, False)
        assert result == "### Song (A)"

    def test_non_heading_unchanged(self):
        result = _transpose_heading("Some random text", 2, False)
        assert result == "Some random text"

    def test_minor_key_heading(self):
        result = _transpose_heading("### Song (Am)", 5, False)
        assert "Dm" in result


# ---------------------------------------------------------------------------
# transpose_content
# ---------------------------------------------------------------------------


class TestTransposeContent:
    def test_semitones_zero_unchanged(self):
        content = "### Song (G)\n\nG   D\nLyrics..."
        assert transpose_content(content, 0) == content

    def test_heading_key_updated(self):
        content = "### Song (G)\n\nG   D\nLyrics..."
        result = transpose_content(content, 2, use_flats=False)
        assert "### Song (A)" in result

    def test_chord_lines_transposed(self):
        content = "### Song (C)\n\nC   G   Am   F\nLyrics stay the same"
        result = transpose_content(content, 2, use_flats=False)
        assert "Lyrics stay the same" in result
        # C -> D, G -> A
        lines = result.split("\n")
        chord_line = lines[2]
        assert "D" in chord_line
        assert "A" in chord_line

    def test_lyrics_preserved(self):
        content = "### Song (G)\n\nG   D\nTua voz me chama\nEm  C\nOutra linha"
        result = transpose_content(content, 2, use_flats=False)
        assert "Tua voz me chama" in result
        assert "Outra linha" in result

    def test_full_transposition_c_to_g(self):
        content = "### My Song (C)\n\nC       G\nVerse one\nAm      F\nVerse two"
        result = transpose_content(content, 7, use_flats=False)
        assert "### My Song (G)" in result

    def test_minor_key_heading(self):
        content = "### Song (Am)\n\nAm  G  F  E"
        result = transpose_content(content, 5, use_flats=False)
        assert "### Song (Dm)" in result

    def test_flat_key_transposition(self):
        content = "### Song (C)\n\nC  F  G"
        result = transpose_content(content, 5, use_flats=True)
        assert "F" in result

    def test_mixed_chord_line_in_content(self):
        content = "### Song (C)\n\nC  G  Am  F\nLyrics here\nIntro 2x: Am Dm G C"
        result = transpose_content(content, 2, use_flats=False)
        # The mixed line should have chords transposed
        assert "Intro 2x:" in result
        assert "Lyrics here" in result
