"""Recover setlists and chord content from ``output/`` markdown files.

``format_setlist_markdown`` embeds every song's chord sheet verbatim, so the
markdown is a faithful (if accidental) backup of both the setlist and the song
content. This module inverts it. Pure functions, no I/O beyond reading files in
``scan_output_dir``; the database side lives in
``scripts/reconstruct_from_outputs.py``.

Identity (date, label, event type) comes from the file path,
``output/[<event_type>/]{date}[_{label}].md``, never from the header line: an
event type name may itself contain parentheses (``Culto (Ceia) (culto_dia)``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date as _date
from pathlib import Path

from .models import Setlist, Song

SEPARATOR = "\n\n---\n\n"
HEADING_RE = re.compile(r"^###\s*(.+?)(?:\s*\(([^()]*)\))?\s*$")
_ID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:_(.+))?$")
_LYRICS_SUFFIX = "_lyrics"
_PUNCTUATION_RE = re.compile(r"[,.?!:;]")


def setlist_id_for(date: str, label: str, event_type: str) -> str:
    """Return ``[<event_type>/]{date}[_{label}]``, the id used by --include/--exclude."""
    sid = f"{date}_{label}" if label else date
    return f"{event_type}/{sid}" if event_type else sid


@dataclass(frozen=True)
class ParsedSetlist:
    date: str
    label: str
    event_type: str
    moments: dict[str, list[str]]  # moment slug -> heading titles, as written
    contents: dict[str, str]  # heading title -> verbatim chord content
    source: Path

    def key(self) -> tuple[str, str, str]:
        return (self.date, self.event_type, self.label)

    @property
    def setlist_id(self) -> str:
        return setlist_id_for(self.date, self.label, self.event_type)


def identity_from_path(path: Path, output_root: Path) -> tuple[str, str, str]:
    """Derive ``(date, label, event_type)`` from an output file path."""
    rel = path.relative_to(output_root)
    event_type = rel.parts[0] if len(rel.parts) == 2 else ""
    stem = path.stem
    if stem.endswith(_LYRICS_SUFFIX):
        stem = stem[: -len(_LYRICS_SUFFIX)]
    match = _ID_RE.match(stem)
    if not match:
        raise ValueError(f"{path}: file name is not {{date}}[_{{label}}]")
    date, label = match.group(1), match.group(2) or ""
    _date.fromisoformat(date)  # raises ValueError on a malformed date
    return date, label, event_type


def parse_setlist_markdown(
    text: str, *, date: str, label: str, event_type: str, source: Path
) -> ParsedSetlist:
    """Invert ``format_setlist_markdown``. Raises ValueError on malformed input."""
    header, *sections = re.split(r"^## ", text, flags=re.MULTILINE)
    expected = f"# Setlist - {date}"
    if not header.startswith(expected):
        raise ValueError(f"{source}: header does not start with '{expected}'")

    moments: dict[str, list[str]] = {}
    contents: dict[str, str] = {}
    for section in sections:
        heading, _, body = section.partition("\n")
        moment = heading.strip().lower()
        body = body.removeprefix("\n")
        *pieces, remainder = body.split(SEPARATOR)
        if remainder not in ("", "\n"):
            raise ValueError(f"{source}: moment '{moment}' is not separated by '---'")
        titles: list[str] = []
        for piece in pieces:
            first_line = piece.split("\n", 1)[0]
            match = HEADING_RE.match(first_line)
            if not match:
                raise ValueError(f"{source}: song heading not found: {first_line!r}")
            title = match.group(1)
            titles.append(title)
            if "*(Content not found)*" not in piece:
                contents[title] = piece
        if titles:
            moments[moment] = titles

    return ParsedSetlist(
        date=date,
        label=label,
        event_type=event_type,
        moments=moments,
        contents=contents,
        source=source,
    )


def _normalize(title: str) -> str:
    return " ".join(_PUNCTUATION_RE.sub("", title).casefold().split())


def resolve_title(heading_title: str, known_titles) -> str | None:
    """Map a heading title to a known title: exact, else ignoring case and punctuation."""
    known = list(known_titles)
    if heading_title in known:
        return heading_title
    wanted = _normalize(heading_title)
    for title in known:
        if _normalize(title) == wanted:
            return title
    return None


def scan_output_dir(root: Path) -> tuple[list[ParsedSetlist], list[str]]:
    """Parse every setlist markdown under ``root``.

    Returns the parsed setlists and the ids of PDF-only setlists (a ``.pdf``
    with no sibling ``.md``), which carry no chord content and are left to the
    caller to report.
    """
    parsed: list[ParsedSetlist] = []
    pdf_only: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.name.startswith(".") or not path.is_file():
            continue
        if path.stem.endswith(_LYRICS_SUFFIX):
            continue
        if path.suffix == ".md":
            date, label, event_type = identity_from_path(path, root)
            text = path.read_text(encoding="utf-8")
            parsed.append(
                parse_setlist_markdown(
                    text, date=date, label=label, event_type=event_type, source=path
                )
            )
        elif path.suffix == ".pdf" and not path.with_suffix(".md").exists():
            pdf_only.append(setlist_id_for(*identity_from_path(path, root)))
    return parsed, pdf_only


@dataclass
class NewSong:
    title: str
    content: str
    moments: dict[str, int]  # moment -> number of appearances
    sources: list[str] = field(default_factory=list)  # setlist ids, newest first


@dataclass(frozen=True)
class ContentUpdate:
    title: str
    old: str
    new: str
    source_date: str
    source: Path


@dataclass
class Plan:
    new_songs: dict[str, NewSong] = field(default_factory=dict)
    content_updates: dict[str, ContentUpdate] = field(default_factory=dict)
    setlists: list[Setlist] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (setlist id, reason)


def plan_reconstruction(
    parsed: list[ParsedSetlist],
    *,
    db_songs: dict[str, Song],
    db_setlist_keys: set[tuple[str, str, str]],
    since: str,
    include: frozenset[str] | set[str] = frozenset(),
    exclude: frozenset[str] | set[str] = frozenset(),
) -> Plan:
    """Diff parsed output against the database.

    A setlist is considered when its date is after ``since`` (the dump date)
    or its id is in ``include``, unless its id is in ``exclude``. Considered
    setlists contribute song content (newest date wins) and are upserted when
    missing from the database. Re-running on an up-to-date database yields an
    empty plan.
    """
    plan = Plan()
    selected: list[ParsedSetlist] = []
    for p in sorted(parsed, key=lambda p: (p.date, str(p.source))):
        sid = p.setlist_id
        if sid in exclude:
            plan.skipped.append((sid, "excluded"))
        elif p.date <= since and sid not in include:
            if p.key() in db_setlist_keys:
                plan.skipped.append((sid, "already in DB (pre-dump)"))
            else:
                plan.skipped.append((sid, f"pre-dump, not in DB; pass --include {sid}"))
        else:
            selected.append(p)

    resolved_moments: dict[tuple[str, str, str], dict[str, list[str]]] = {}
    decided: set[str] = set()  # titles whose newest content has been seen
    for p in reversed(selected):  # newest first, so the first content seen wins
        moments: dict[str, list[str]] = {}
        for moment, titles in p.moments.items():
            for heading_title in titles:
                title = resolve_title(heading_title, [*db_songs, *plan.new_songs])
                content = p.contents.get(heading_title)
                if title is None:
                    title = heading_title
                    plan.new_songs[title] = NewSong(title=title, content=content or "", moments={})
                new_song = plan.new_songs.get(title)
                if new_song is not None:
                    new_song.moments[moment] = new_song.moments.get(moment, 0) + 1
                    if p.setlist_id not in new_song.sources:
                        new_song.sources.append(p.setlist_id)
                elif title not in decided and content is not None:
                    decided.add(title)
                    if content != db_songs[title].content:
                        plan.content_updates[title] = ContentUpdate(
                            title=title,
                            old=db_songs[title].content,
                            new=content,
                            source_date=p.date,
                            source=p.source,
                        )
                moments.setdefault(moment, []).append(title)
        resolved_moments[p.key()] = moments

    for p in selected:
        if p.key() not in db_setlist_keys:
            plan.setlists.append(
                Setlist(
                    date=p.date,
                    moments=resolved_moments[p.key()],
                    label=p.label,
                    event_type=p.event_type,
                )
            )
    return plan
