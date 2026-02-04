"""Deterministic chord transposition — pure runtime transformation.

All functions are stateless (no dependencies beyond ``re``), following
the project convention for algorithm modules (cf. ``ordering.py``).
"""

import re

# ── chromatic scale in both sharp and flat notation ──────────────────

SHARP_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NOTES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Map every enharmonic spelling to a semitone index (0-11)
_NOTE_TO_INDEX: dict[str, int] = {}
for i, n in enumerate(SHARP_NOTES):
    _NOTE_TO_INDEX[n] = i
for i, n in enumerate(FLAT_NOTES):
    _NOTE_TO_INDEX[n] = i

# Keys whose conventional notation uses flats
_FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb",
              "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm"}

# ── regex for matching chord symbols ─────────────────────────────────

# A chord token is:  Root  [quality/extensions]  [/Bass]
#   Root = C | C# | Db | ... (uppercase letter + optional # or b)
#   Quality = any combo of m, M, 7, 9, 11, 13, dim, aug, sus, add, (, ), +, -
#   Bass = /Root
_ROOT_RE = r"[A-G][#b]?"
_QUALITY_RE = r"(?:m(?!aj)|M|maj|dim|aug|sus|add|\d+|\(|\)|\+|\-)*"
_CHORD_RE = re.compile(
    rf"({_ROOT_RE})({_QUALITY_RE})(?:/({_ROOT_RE}))?$"
)

# For scanning chord tokens inside a line (non-anchored)
_CHORD_TOKEN_RE = re.compile(
    rf"(?<![a-zà-ú])({_ROOT_RE}{_QUALITY_RE}(?:/{_ROOT_RE})?)(?![a-zà-ú])"
)


# ── public helpers ───────────────────────────────────────────────────

def should_use_flats(target_key: str) -> bool:
    """Determine whether *target_key* conventionally uses flats.

    >>> should_use_flats("Bb")
    True
    >>> should_use_flats("A")
    False
    """
    return target_key in _FLAT_KEYS


def resolve_target_key(from_key: str, to_key: str) -> str:
    """Resolve the effective target key, preserving minor/major quality.

    If *from_key* is minor (ends with ``m``) but *to_key* is not, the
    minor suffix is added to *to_key* so that flat/sharp conventions
    match the actual musical key.

    >>> resolve_target_key("Bm", "G")
    'Gm'
    >>> resolve_target_key("C", "G")
    'G'
    >>> resolve_target_key("Am", "Em")
    'Em'
    """
    from_is_minor = from_key.endswith("m") and from_key[:-1] in _NOTE_TO_INDEX
    to_is_minor = to_key.endswith("m") and to_key[:-1] in _NOTE_TO_INDEX

    if from_is_minor and not to_is_minor and to_key in _NOTE_TO_INDEX:
        return to_key + "m"
    return to_key


def calculate_semitones(from_key: str, to_key: str) -> int:
    """Return the signed semitone interval from *from_key* to *to_key*.

    Both arguments may include a trailing ``m`` for minor keys.

    >>> calculate_semitones("C", "G")
    7
    >>> calculate_semitones("G", "C")
    5
    >>> calculate_semitones("Bm", "Em")
    5
    """
    # Strip minor suffix for index lookup
    from_root = from_key.rstrip("m") if from_key.endswith("m") and from_key not in _NOTE_TO_INDEX else from_key
    to_root = to_key.rstrip("m") if to_key.endswith("m") and to_key not in _NOTE_TO_INDEX else to_key

    from_idx = _NOTE_TO_INDEX.get(from_root)
    to_idx = _NOTE_TO_INDEX.get(to_root)
    if from_idx is None:
        raise ValueError(f"Unknown key: {from_key}")
    if to_idx is None:
        raise ValueError(f"Unknown key: {to_key}")
    return (to_idx - from_idx) % 12


# ── core transposition functions ─────────────────────────────────────

def transpose_note(note: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose a single note name by *semitones*.

    >>> transpose_note("C", 7)
    'G'
    >>> transpose_note("A", 3, use_flats=True)
    'C'
    """
    idx = _NOTE_TO_INDEX.get(note)
    if idx is None:
        raise ValueError(f"Unknown note: {note}")
    new_idx = (idx + semitones) % 12
    return FLAT_NOTES[new_idx] if use_flats else SHARP_NOTES[new_idx]


def transpose_chord(chord: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose a full chord symbol, moving only root and optional bass.

    Quality / extensions are preserved verbatim.

    >>> transpose_chord("Am7", 2)
    'Bm7'
    >>> transpose_chord("A/C#", 3, use_flats=True)
    'C/Eb'
    >>> transpose_chord("F7M(9)", 2)
    'G7M(9)'
    """
    m = _CHORD_RE.match(chord)
    if not m:
        return chord  # not a recognized chord — return unchanged
    root, quality, bass = m.group(1), m.group(2), m.group(3)
    new_root = transpose_note(root, semitones, use_flats)
    result = new_root + quality
    if bass:
        new_bass = transpose_note(bass, semitones, use_flats)
        result += "/" + new_bass
    return result


# ── line classification ──────────────────────────────────────────────

# Section markers like [Intro], [Refrão], etc.
_SECTION_MARKER_RE = re.compile(r"^\[.*?\]\s*")

def is_chord_line(line: str) -> bool:
    """Return ``True`` if *line* looks like a chord line.

    A chord line is one where every non-whitespace, non-section-marker
    token parses as a valid chord symbol.

    >>> is_chord_line("G   D   Em   C")
    True
    >>> is_chord_line("Tua voz me chama")
    False
    >>> is_chord_line("[Intro] F7M(9)  Am  G4(6)")
    True
    >>> is_chord_line("")
    False
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Remove section markers like [Intro], [Refrão]
    test = _SECTION_MARKER_RE.sub("", stripped).strip()
    if not test:
        return False

    tokens = test.split()
    if not tokens:
        return False

    for token in tokens:
        if not _CHORD_RE.match(token):
            return False
    return True


def _is_mixed_chord_line(line: str) -> bool:
    """Return ``True`` if *line* mixes chord tokens with non-chord annotations.

    A mixed chord line has at least 2 chord tokens and the chord tokens
    outnumber (or equal) the non-chord tokens.  This avoids false positives
    on lyric lines that happen to contain a chord-like word (e.g. Portuguese
    "Em" = "in" looks like E-minor).

    >>> _is_mixed_chord_line("F  G  C  Riff")
    True
    >>> _is_mixed_chord_line("Intro 2x: Am Dm F7+ G")
    True
    >>> _is_mixed_chord_line("Tua voz me chama")
    False
    >>> _is_mixed_chord_line("Em Deus")
    False
    """
    stripped = line.strip()
    if not stripped:
        return False

    test = _SECTION_MARKER_RE.sub("", stripped).strip()
    if not test:
        return False

    tokens = test.split()
    if not tokens:
        return False

    chord_count = sum(1 for t in tokens if _CHORD_RE.match(t))
    non_chord_count = len(tokens) - chord_count
    return chord_count >= 2 and non_chord_count >= 1 and chord_count >= non_chord_count


# ── line-level transposition with column alignment ───────────────────

def transpose_line(line: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose all chords in a chord line, preserving column positions.

    Non-chord lines are returned unchanged.

    The algorithm:
      1. Record each chord's start column in the original line.
      2. Transpose each chord.
      3. Place each transposed chord at the original column.
      4. If the new chord is longer than available space, ensure at
         least one space separates it from the next chord.
    """
    if not is_chord_line(line):
        return line

    # Collect (start_col, original_token, transposed_token)
    entries: list[tuple[int, str, str]] = []

    # Find section marker if present and keep it in place
    marker_match = _SECTION_MARKER_RE.match(line)
    marker = marker_match.group(0) if marker_match else ""
    search_start = len(marker)

    for m in _CHORD_TOKEN_RE.finditer(line, search_start):
        original = m.group(0)
        transposed = transpose_chord(original, semitones, use_flats)
        entries.append((m.start(), original, transposed))

    if not entries:
        return line

    # Reconstruct the line preserving column alignment
    parts: list[str] = []
    if marker:
        parts.append(marker)

    cursor = len(marker)
    for start_col, _orig, transposed in entries:
        # Pad to reach the original start column
        gap = start_col - cursor
        if gap < 1 and parts:
            gap = 1  # ensure at least one space between chords
        parts.append(" " * gap)
        parts.append(transposed)
        cursor += gap + len(transposed)

    return "".join(parts)


def _transpose_mixed_line(line: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose chord tokens in a mixed chord/annotation line.

    Unlike :func:`transpose_line` (which only handles pure chord lines),
    this preserves non-chord tokens (e.g. ``Riff``, ``Intro 2x:``) while
    transposing the chord tokens and maintaining column alignment.
    """
    marker_match = _SECTION_MARKER_RE.match(line)
    marker = marker_match.group(0) if marker_match else ""
    search_start = len(marker)

    # Classify every whitespace-delimited token as chord or non-chord
    entries: list[tuple[int, str]] = []  # (start_col, output_text)
    for m in re.finditer(r"\S+", line):
        if m.start() < search_start:
            continue  # inside section marker — skip
        token = m.group(0)
        if _CHORD_RE.match(token):
            entries.append((m.start(), transpose_chord(token, semitones, use_flats)))
        else:
            entries.append((m.start(), token))  # keep annotation as-is

    if not entries:
        return line

    # Reconstruct preserving column alignment
    parts: list[str] = []
    if marker:
        parts.append(marker)

    cursor = len(marker)
    for start_col, text in entries:
        gap = start_col - cursor
        if gap < 1 and parts:
            gap = 1
        parts.append(" " * gap)
        parts.append(text)
        cursor += gap + len(text)

    return "".join(parts)


# ── heading key replacement ──────────────────────────────────────────

_HEADING_KEY_RE = re.compile(r"(###\s*.+?\()([A-G][#b]?m?)(\)\s*)$")


def _transpose_heading(line: str, semitones: int, use_flats: bool) -> str:
    """Transpose the key annotation in a ``### Title (Key)`` heading."""
    m = _HEADING_KEY_RE.match(line)
    if not m:
        return line
    prefix, old_key, suffix = m.group(1), m.group(2), m.group(3)
    new_key = _transpose_key(old_key, semitones, use_flats)
    return prefix + new_key + suffix


def _transpose_key(key: str, semitones: int, use_flats: bool) -> str:
    """Transpose a key label like ``Bm`` or ``G``."""
    if key.endswith("m") and key[:-1] in _NOTE_TO_INDEX:
        return transpose_note(key[:-1], semitones, use_flats) + "m"
    return transpose_note(key, semitones, use_flats)


# ── full-content transposition ───────────────────────────────────────

def transpose_content(content: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose an entire song's markdown content.

    Processes each line: headings get their key updated, chord lines
    get all chords transposed (with alignment), and lyric / blank lines
    pass through unchanged.

    If *semitones* is 0 the content is returned as-is.
    """
    if semitones == 0:
        return content

    result_lines: list[str] = []
    for line in content.split("\n"):
        if line.strip().startswith("###"):
            result_lines.append(_transpose_heading(line, semitones, use_flats))
        elif is_chord_line(line):
            result_lines.append(transpose_line(line, semitones, use_flats))
        elif _is_mixed_chord_line(line):
            result_lines.append(_transpose_mixed_line(line, semitones, use_flats))
        else:
            result_lines.append(line)
    return "\n".join(result_lines)
