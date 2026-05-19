"""Unit tests for ``FilesystemOutputRepository.delete_outputs``.

`delete_outputs` is the lower-layer primitive that ``songbook delete`` (and
``songbook label`` during rename) lean on. The contract:

* Removes ``<setlist_id>.md`` and ``<setlist_id>.pdf`` when present.
* Also removes any ``<setlist_id>_<variant>.pdf`` siblings — today only
  ``_lyrics.pdf``, but anything matching the pattern (so a future variant
  doesn't silently leak files).
* Routes through the event-type subdirectory when given a non-default slug.
* Returns the actual paths it deleted, for the CLI to echo back.
* Doesn't blow up when nothing exists — returns ``[]``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from library.repositories.filesystem.output import FilesystemOutputRepository


@pytest.fixture()
def output_dir(tmp_path: Path) -> Path:
    (tmp_path / "output").mkdir()
    return tmp_path / "output"


@pytest.fixture()
def repo(output_dir: Path) -> FilesystemOutputRepository:
    return FilesystemOutputRepository(output_dir)


def test_deletes_markdown_and_regular_pdf(repo, output_dir):
    md = output_dir / "2026-02-15.md"
    pdf = output_dir / "2026-02-15.pdf"
    md.write_text("# md\n")
    pdf.write_text("%PDF\n")

    deleted = repo.delete_outputs("2026-02-15")

    assert set(deleted) == {md, pdf}
    assert not md.exists()
    assert not pdf.exists()


def test_deletes_lyrics_pdf_variant(repo, output_dir):
    """Lyrics-only PDFs (``_lyrics.pdf``) must not be left as orphans."""
    md = output_dir / "2026-02-15.md"
    lyrics_pdf = output_dir / "2026-02-15_lyrics.pdf"
    md.write_text("# md\n")
    lyrics_pdf.write_text("%PDF\n")

    deleted = repo.delete_outputs("2026-02-15")

    assert lyrics_pdf in deleted
    assert not lyrics_pdf.exists()


def test_does_not_touch_unrelated_dates(repo, output_dir):
    """Setlist IDs are distinct; deleting one must not glob neighbors."""
    keep = output_dir / "2026-02-22.md"
    keep.write_text("# keep\n")
    target = output_dir / "2026-02-15.md"
    target.write_text("# target\n")

    repo.delete_outputs("2026-02-15")

    assert not target.exists()
    assert keep.exists()


def test_does_not_touch_other_label_variants(repo, output_dir):
    """``--label`` setlists are independent — deleting one label must
    not touch the unlabeled primary or sibling labels."""
    primary_md = output_dir / "2026-02-15.md"
    primary_md.write_text("# primary\n")
    evening_md = output_dir / "2026-02-15_evening.md"
    evening_md.write_text("# evening\n")
    night_md = output_dir / "2026-02-15_night.md"
    night_md.write_text("# night\n")

    repo.delete_outputs("2026-02-15", label="evening")

    assert not evening_md.exists()
    assert primary_md.exists()
    assert night_md.exists()


def test_empty_when_nothing_to_delete(repo):
    """No files on disk → empty list, no exceptions."""
    assert repo.delete_outputs("1999-01-01") == []


def test_routes_through_event_type_subdir(repo, output_dir):
    youth_dir = output_dir / "youth"
    youth_dir.mkdir()
    md = youth_dir / "2026-03-20.md"
    pdf = youth_dir / "2026-03-20.pdf"
    lyrics_pdf = youth_dir / "2026-03-20_lyrics.pdf"
    md.write_text("# md\n")
    pdf.write_text("%PDF\n")
    lyrics_pdf.write_text("%PDF\n")

    deleted = repo.delete_outputs("2026-03-20", event_type="youth")

    assert set(deleted) == {md, pdf, lyrics_pdf}
    assert not md.exists()
    assert not pdf.exists()
    assert not lyrics_pdf.exists()


def test_label_variant_does_not_match_unlabeled_pdf_variants(repo, output_dir):
    """Glob anchoring check: deleting ``2026-02-15_evening`` must not
    sweep up ``2026-02-15_lyrics.pdf`` (which belongs to the unlabeled
    primary). The setlist_id prefix is the boundary."""
    primary_lyrics = output_dir / "2026-02-15_lyrics.pdf"
    primary_lyrics.write_text("%PDF\n")
    evening_md = output_dir / "2026-02-15_evening.md"
    evening_md.write_text("# evening\n")

    repo.delete_outputs("2026-02-15", label="evening")

    assert not evening_md.exists()
    assert primary_lyrics.exists(), (
        "lyrics PDF for the unlabeled primary must survive deleting the "
        "labeled variant — setlist_ids are distinct boundaries"
    )


def test_unlabeled_delete_does_not_match_labeled_variants(repo, output_dir):
    """Inverse direction of the previous test, and a much sharper trap:
    a naive ``{setlist_id}_*.pdf`` glob would accidentally sweep up every
    labeled variant when deleting the unlabeled primary (because
    ``2026-02-15_evening.pdf`` starts with ``2026-02-15_``)."""
    primary_md = output_dir / "2026-02-15.md"
    primary_lyrics = output_dir / "2026-02-15_lyrics.pdf"
    primary_md.write_text("# primary\n")
    primary_lyrics.write_text("%PDF\n")

    # Sibling labeled variant — must survive deleting the unlabeled.
    evening_pdf = output_dir / "2026-02-15_evening.pdf"
    evening_lyrics = output_dir / "2026-02-15_evening_lyrics.pdf"
    evening_pdf.write_text("%PDF\n")
    evening_lyrics.write_text("%PDF\n")

    repo.delete_outputs("2026-02-15")

    # Unlabeled gone (md + lyrics variant).
    assert not primary_md.exists()
    assert not primary_lyrics.exists()
    # Labeled sibling — every file — untouched.
    assert evening_pdf.exists(), (
        "labeled regular PDF must survive deleting the unlabeled primary"
    )
    assert evening_lyrics.exists(), (
        "labeled lyrics variant must survive deleting the unlabeled primary"
    )
