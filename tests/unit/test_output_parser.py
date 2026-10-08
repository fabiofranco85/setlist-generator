"""Tests for library.output_parser: recovering setlists from output markdown."""

from pathlib import Path

import pytest

from library.formatter import format_setlist_markdown
from library.models import Setlist
from library.output_parser import (
    identity_from_path,
    parse_setlist_markdown,
    plan_reconstruction,
    resolve_title,
    scan_output_dir,
)
from tests.helpers.factories import make_song


def _songs(*titles_and_keys):
    """Build a songs dict whose content mirrors what the DB holds."""
    songs = {}
    for title, key in titles_and_keys:
        content = f"### {title} ({key})\n\n{key}      D\nLyrics of {title}\n"
        songs[title] = make_song(title=title, content=content)
    return songs


# --- identity_from_path -----------------------------------------------------


@pytest.mark.parametrize(
    "rel, expected",
    [
        ("2026-09-13.md", ("2026-09-13", "", "")),
        ("2026-06-07_morning.md", ("2026-06-07", "morning", "")),
        ("2026-06-28_culto_dia.md", ("2026-06-28", "culto_dia", "")),
        ("ceia/2026-09-13_culto_noite.md", ("2026-09-13", "culto_noite", "ceia")),
        ("jejumeoracao/2026-03-04.md", ("2026-03-04", "", "jejumeoracao")),
        ("2026-08-28_aniversario_lyrics.pdf", ("2026-08-28", "aniversario", "")),
        ("2026-02-08_lyrics.pdf", ("2026-02-08", "", "")),
    ],
)
def test_identity_from_path(rel, expected):
    root = Path("/x/output")
    assert identity_from_path(root / rel, root) == expected


def test_identity_from_path_rejects_bad_date():
    root = Path("/x/output")
    with pytest.raises(ValueError):
        identity_from_path(root / "notes.md", root)


# --- parse_setlist_markdown -------------------------------------------------


def _render(setlist, songs, **kwargs):
    return format_setlist_markdown(setlist, songs, **kwargs)


def test_markdown_round_trip_unlabeled_main():
    songs = _songs(("Oceanos", "G"), ("Hosana", "C"), ("Deus Grandão", "D"))
    setlist = Setlist(
        date="2026-09-13",
        moments={"louvor": ["Oceanos", "Hosana"], "crianças": ["Deus Grandão"]},
    )
    text = _render(setlist, songs)

    parsed = parse_setlist_markdown(
        text, date="2026-09-13", label="", event_type="", source=Path("a.md")
    )

    assert parsed.date == "2026-09-13"
    assert parsed.label == ""
    assert parsed.event_type == ""
    assert parsed.moments == {"louvor": ["Oceanos", "Hosana"], "crianças": ["Deus Grandão"]}
    assert parsed.contents == {t: s.content for t, s in songs.items()}


def test_markdown_round_trip_labeled_event_type_with_parentheses_in_name():
    songs = _songs(("Precioso", "A"), ("Agnus Dei", "E"))
    setlist = Setlist(
        date="2026-07-26",
        moments={"louvor": ["Precioso"], "ceia": ["Agnus Dei"]},
        label="culto_dia",
        event_type="ceia",
    )
    text = _render(
        setlist,
        songs,
        event_type_name="Culto (Ceia)",
        moments_order=["prelúdio", "louvor", "ceia", "poslúdio"],
    )
    assert text.startswith("# Setlist - 2026-07-26 | Culto (Ceia) (culto_dia)")

    parsed = parse_setlist_markdown(
        text, date="2026-07-26", label="culto_dia", event_type="ceia", source=Path("b.md")
    )

    assert parsed.label == "culto_dia"
    assert parsed.event_type == "ceia"
    assert parsed.moments == {"louvor": ["Precioso"], "ceia": ["Agnus Dei"]}
    assert parsed.contents["Agnus Dei"] == songs["Agnus Dei"].content


def test_markdown_heading_without_space_after_hashes_is_tolerated():
    text = (
        "# Setlist - 2026-02-08\n\n"
        "## Prelúdio\n\n"
        "###Abra os olhos do meu coração (E)\n\nE2\nSanto\n\n---\n\n\n"
    )
    parsed = parse_setlist_markdown(
        text, date="2026-02-08", label="", event_type="", source=Path("c.md")
    )
    assert parsed.moments == {"prelúdio": ["Abra os olhos do meu coração"]}
    assert parsed.contents["Abra os olhos do meu coração"].startswith("###Abra")


def test_markdown_empty_moment_section_is_dropped():
    text = "# Setlist - 2026-03-04\n\n## Louvor\n\n### A (G)\n\nG\nla\n\n---\n\n\n## Final\n\n\n"
    parsed = parse_setlist_markdown(
        text, date="2026-03-04", label="", event_type="", source=Path("d.md")
    )
    assert list(parsed.moments) == ["louvor"]


def test_markdown_header_date_mismatch_raises():
    text = "# Setlist - 2026-01-01\n\n## Louvor\n\n### A (G)\n\nG\n\n---\n\n\n"
    with pytest.raises(ValueError, match="2026-02-02"):
        parse_setlist_markdown(
            text, date="2026-02-02", label="", event_type="", source=Path("e.md")
        )


# --- resolve_title ----------------------------------------------------------


def test_resolve_title_exact_match():
    assert resolve_title("Oceanos", ["Oceanos", "Hosana"]) == "Oceanos"


def test_resolve_title_ignores_punctuation_and_case():
    known = ["Espírito Enche a Minha Vida"]
    assert resolve_title("Espírito, Enche a Minha Vida", known) == known[0]
    assert resolve_title("espírito enche a minha vida", known) == known[0]


def test_resolve_title_no_false_positive():
    assert resolve_title("Oceano de Paz", ["Oceanos"]) is None


# --- scan_output_dir --------------------------------------------------------


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_scan_output_dir_parses_markdown_and_reports_pdf_only(tmp_path):
    songs = _songs(("Oceanos", "G"))
    _write(
        tmp_path,
        "2026-09-13.md",
        _render(Setlist(date="2026-09-13", moments={"louvor": ["Oceanos"]}), songs),
    )
    _write(
        tmp_path,
        "ceia/2026-09-13_culto_dia.md",
        _render(
            Setlist(date="2026-09-13", moments={"louvor": ["Oceanos"]}, label="culto_dia"),
            songs,
        ),
    )
    _write(tmp_path, "2026-09-13_lyrics.pdf", "not a pdf")
    _write(tmp_path, "2026-09-13.pdf", "not a pdf")
    _write(tmp_path, "2026-08-28_aniversario.pdf", "not a pdf")
    _write(tmp_path, "2026-08-28_aniversario_lyrics.pdf", "not a pdf")
    _write(tmp_path, ".DS_Store", "")

    parsed, pdf_only = scan_output_dir(tmp_path)

    assert sorted(p.key() for p in parsed) == [
        ("2026-09-13", "", ""),
        ("2026-09-13", "ceia", "culto_dia"),
    ]
    assert pdf_only == ["2026-08-28_aniversario"]


# --- plan_reconstruction ----------------------------------------------------


def _parsed(date, moments, songs, label="", event_type="", name=None):
    text = _render(
        Setlist(date=date, moments=moments, label=label, event_type=event_type), songs
    )
    return parse_setlist_markdown(
        text,
        date=date,
        label=label,
        event_type=event_type,
        source=Path(name or f"{date}.md"),
    )


def test_plan_new_song_changed_content_and_missing_setlist():
    db_songs = _songs(("Oceanos", "G"))
    edited = dict(db_songs)
    edited["Oceanos"] = make_song(title="Oceanos", content="### Oceanos (A)\n\nA\nnew\n")
    newer = _songs(("Sublime", "E"))
    parsed = [_parsed("2026-09-13", {"louvor": ["Oceanos", "Sublime"]}, {**edited, **newer})]

    plan = plan_reconstruction(
        parsed, db_songs=db_songs, db_setlist_keys=set(), since="2026-05-18"
    )

    assert list(plan.new_songs) == ["Sublime"]
    assert plan.new_songs["Sublime"].content == newer["Sublime"].content
    assert plan.new_songs["Sublime"].moments == {"louvor": 1}
    assert list(plan.content_updates) == ["Oceanos"]
    assert plan.content_updates["Oceanos"].new == edited["Oceanos"].content
    assert [s.to_dict() for s in plan.setlists] == [
        {"date": "2026-09-13", "moments": {"louvor": ["Oceanos", "Sublime"]}}
    ]
    assert plan.skipped == []


def test_plan_maps_heading_title_to_db_title():
    db_songs = {
        "Espírito Enche a Minha Vida": make_song(
            title="Espírito Enche a Minha Vida",
            content="### Espírito, Enche a Minha Vida (C)\n\nC\nvem\n",
        )
    }
    parsed = [_parsed("2026-09-13", {"louvor": ["Espírito Enche a Minha Vida"]}, db_songs)]

    plan = plan_reconstruction(
        parsed, db_songs=db_songs, db_setlist_keys=set(), since="2026-05-18"
    )

    assert plan.new_songs == {}
    assert plan.content_updates == {}
    assert plan.setlists[0].moments == {"louvor": ["Espírito Enche a Minha Vida"]}


def test_plan_newest_setlist_wins_for_content():
    old = _songs(("Precioso", "A"))
    new = {"Precioso": make_song(title="Precioso", content="### Precioso (B)\n\nB\nnewer\n")}
    parsed = [
        _parsed("2026-09-13", {"louvor": ["Precioso"]}, new),
        _parsed("2026-06-07", {"louvor": ["Precioso"]}, old),
    ]

    plan = plan_reconstruction(
        parsed, db_songs=old, db_setlist_keys=set(), since="2026-05-18"
    )

    assert plan.content_updates["Precioso"].new == new["Precioso"].content
    assert plan.content_updates["Precioso"].source_date == "2026-09-13"


def test_plan_skips_pre_dump_setlists_with_reasons():
    songs = _songs(("Oceanos", "G"))
    parsed = [
        _parsed("2026-05-10", {"louvor": ["Oceanos"]}, songs),
        _parsed("2026-04-20", {"louvor": ["Oceanos"]}, songs),
    ]

    plan = plan_reconstruction(
        parsed,
        db_songs=songs,
        db_setlist_keys={("2026-05-10", "", "")},
        since="2026-05-18",
    )

    assert plan.setlists == []
    assert plan.new_songs == {}
    assert plan.content_updates == {}
    assert plan.skipped == [
        ("2026-04-20", "pre-dump, not in DB; pass --include 2026-04-20"),
        ("2026-05-10", "already in DB (pre-dump)"),
    ]


def test_plan_include_and_exclude_override_date_rule():
    songs = _songs(("Oceanos", "G"))
    parsed = [
        _parsed("2026-04-20", {"louvor": ["Oceanos"]}, songs),
        _parsed("2026-09-13", {"louvor": ["Oceanos"]}, songs, label="noite"),
    ]

    plan = plan_reconstruction(
        parsed,
        db_songs=songs,
        db_setlist_keys=set(),
        since="2026-05-18",
        include={"2026-04-20"},
        exclude={"2026-09-13_noite"},
    )

    assert [s.setlist_id for s in plan.setlists] == ["2026-04-20"]
    assert plan.skipped == [("2026-09-13_noite", "excluded")]


def test_plan_setlist_id_includes_event_type_prefix():
    songs = _songs(("Oceanos", "G"))
    parsed = [_parsed("2026-09-13", {"louvor": ["Oceanos"]}, songs, label="culto_dia", event_type="ceia")]

    plan = plan_reconstruction(
        parsed, db_songs=songs, db_setlist_keys=set(), since="2026-05-18",
        exclude={"ceia/2026-09-13_culto_dia"},
    )

    assert plan.skipped == [("ceia/2026-09-13_culto_dia", "excluded")]


def test_plan_is_empty_once_applied():
    songs = _songs(("Oceanos", "G"), ("Sublime", "E"))
    parsed = [_parsed("2026-09-13", {"louvor": ["Oceanos", "Sublime"]}, songs)]

    plan = plan_reconstruction(
        parsed,
        db_songs=songs,
        db_setlist_keys={("2026-09-13", "", "")},
        since="2026-05-18",
    )

    assert plan.new_songs == {}
    assert plan.content_updates == {}
    assert plan.setlists == []
    assert plan.skipped == []
