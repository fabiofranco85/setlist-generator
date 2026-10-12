"""Import a chord sheet from a Cifra Club song page.

Backs the optional Cifra Club URL prompt of ``songbook add``. ``parse_page``
and ``render_sheet`` are pure; only ``fetch_page`` touches the network.

Cifra Club writes some songs in an easier shape played with a capo, e.g.
"Tom: Db (com forma de C)" with the capo on fret 1: the chords on the page are
C shapes, the song sounds in Db. ``ChordSheet.key`` is the written key,
``ChordSheet.sounding_key`` the real one. ``render_sheet`` transposes to the
sounding key by default, so the imported sheet is playable without a capo.

Parsing relies on the page markup as of 2026-10: the sheet is the
``<pre data-chord-content>`` block with chords wrapped in ``<b>`` tags, and the
key and capo sit next to the "Tom:" / "Capotraste:" labels. CSS class names
are generated per build, so none are used.
"""

from __future__ import annotations

import gzip
import html
import re
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from library.transposer import (
    calculate_semitones,
    resolve_target_key,
    should_use_flats,
    transpose_content,
)

# Akamai answers 403 to requests that don't look like a browser navigation.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

_PRE_RE = re.compile(r"<pre[^>]*data-chord-content[^>]*>(.*?)</pre>", re.S)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_KEY_RE = re.compile(r"<span>Tom:\s*</span>\s*<button[^>]*>(.*?)</button>", re.S)
_CAPO_RE = re.compile(r"<span>Capotraste:\s*</span>\s*<button[^>]*>(.*?)</button>", re.S)
# "Db (com forma de C)" -> sounding Db, written C
_SHAPE_RE = re.compile(r"^\s*(\S+)\s*\(com forma de\s+(\S+?)\)\s*$")


@dataclass(frozen=True)
class ChordSheet:
    """A chord sheet as published on Cifra Club."""

    title: str
    artist: str
    key: str           # key the chords are written in ("" if the page has none)
    sounding_key: str  # key the song sounds in; differs from ``key`` with a capo
    capo: str          # e.g. "1ª casa", "" without capo
    body: str          # chord-over-lyric lines, no heading


def is_cifraclub_url(url: str) -> bool:
    """True for an http(s) URL on cifraclub.com.br."""
    parsed = urlparse(url.strip())
    host = parsed.hostname or ""
    return parsed.scheme in ("http", "https") and (
        host == "cifraclub.com.br" or host.endswith(".cifraclub.com.br")
    )


def fetch_page(url: str, timeout: float = 20) -> str:
    """Download a Cifra Club page and return its HTML."""
    if not is_cifraclub_url(url):
        raise ValueError(f"'{url}' is not a Cifra Club URL.")
    req = urllib.request.Request(url.strip(), headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode(resp.headers.get_content_charset() or "utf-8")


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def parse_page(page: str) -> ChordSheet:
    """Extract the chord sheet and its metadata from a Cifra Club page.

    Raises:
        ValueError: The page has no chord block (not a song page, or the
            layout changed).
    """
    # React leaves "<!-- -->" between adjacent text nodes ("Tom<!-- -->: ").
    page = re.sub(r"<!--.*?-->", "", page, flags=re.S)

    pre = _PRE_RE.search(page)
    if not pre:
        raise ValueError("No chord sheet found on the page.")
    lines = html.unescape(re.sub(r"<[^>]+>", "", pre.group(1))).splitlines()
    body = "\n".join(line.rstrip() for line in lines).strip("\n")

    # "<Song> - <Artist> - Cifra Club"
    title_match = _TITLE_RE.search(page)
    parts = [p.strip() for p in _text(title_match.group(1)).split(" - ")] if title_match else [""]
    title = parts[0]
    artist = parts[1] if len(parts) > 2 else ""

    key_match = _KEY_RE.search(page)
    key_text = _text(key_match.group(1)) if key_match else ""
    shape = _SHAPE_RE.match(key_text)
    sounding_key, written_key = shape.groups() if shape else (key_text, key_text)

    capo_match = _CAPO_RE.search(page)
    capo = _text(capo_match.group(1)) if capo_match else ""

    return ChordSheet(title, artist, written_key, sounding_key, capo, body)


def render_sheet(sheet: ChordSheet, title: str, target_key: str = "") -> str:
    """Return the sheet as songbook chord content, transposed to ``target_key``.

    The heading uses ``title`` (the repertoire's title, not Cifra Club's).
    A blank ``target_key`` means the sounding key, so a capo sheet comes out
    playable without the capo. As in ``songbook transpose``, a major target
    for a minor song keeps it minor ("G" for a Bm song gives Gm).

    Raises:
        ValueError: ``target_key`` is not a key, or the page gave no key to
            transpose from.
    """
    content = f"### {title} ({sheet.key})\n\n{sheet.body}\n"
    target = target_key.strip() or sheet.sounding_key
    if not target or target == sheet.key:
        return content
    if not sheet.key:
        raise ValueError("The page shows no key, so the chords cannot be transposed.")

    effective = resolve_target_key(sheet.key, target)
    semitones = calculate_semitones(sheet.key, effective)  # raises on unknown key
    return transpose_content(content, semitones, should_use_flats(effective))
