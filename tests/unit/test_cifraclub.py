"""Tests for ``library/cifraclub.py`` (Cifra Club chord-sheet import).

The fixture mimics the real page markup (``<pre data-chord-content>`` with
``<b>`` chord tags, React's ``<!-- -->`` text-node separators, the "Tom:" and
"Capotraste:" buttons) with placeholder lyrics.
"""

from __future__ import annotations

import gzip

import pytest

from library.cifraclub import (
    ChordSheet,
    fetch_page,
    is_cifraclub_url,
    parse_page,
    render_sheet,
)


def _page(key_button: str = "Db<!-- --> (com forma de C)", capo: str | None = "1ª casa") -> str:
    capo_html = (
        f'<div class="IERZz"><span>Capotraste<!-- -->:</span> '
        f'<button type="button" class="eVroG">{capo}</button></div>'
        if capo
        else ""
    )
    return f"""<html><head><title>Canção de Teste - Banda Exemplo - Cifra Club</title></head>
<body>
<div><span>Tom<!-- -->: </span> <button type="button" class="eVroG">{key_button}</button></div>
{capo_html}
<pre class="_crVx" data-chord-content="true">[Intro] <b data-chord-name="C">C</b>  <b>Am7</b>  <b>G</b>

<div class="kvMV"><b>C</b>              <b>Am7</b>
  Primeira linha de teste   \n</div><div class="kvMV"><b>G</b>           <b>F7M(2)/C</b>
Segunda linha &amp; mais
</div>
[Refrão]

<b>F</b>       <b>C/E</b>
Refrão de exemplo
</pre>
</body></html>"""


# ---------------------------------------------------------------------------
# parse_page
# ---------------------------------------------------------------------------


def test_parse_reads_title_artist_key_and_capo():
    sheet = parse_page(_page())
    assert sheet.title == "Canção de Teste"
    assert sheet.artist == "Banda Exemplo"
    assert sheet.key == "C"
    assert sheet.sounding_key == "Db"
    assert sheet.capo == "1ª casa"

def test_body_strips_tags_keeps_alignment():
    body = parse_page(_page()).body
    lines = body.splitlines()
    assert lines[0] == "[Intro] C  Am7  G"
    assert lines[2] == "C              Am7"
    assert lines[3] == "  Primeira linha de teste"  # trailing spaces trimmed
    assert "Segunda linha & mais" in lines  # entities unescaped
    assert "<" not in body

def test_body_has_no_leading_or_trailing_blank_lines():
    body = parse_page(_page()).body
    assert not body.startswith("\n") and not body.endswith("\n")

def test_no_capo_means_written_equals_sounding():
    sheet = parse_page(_page(key_button="G", capo=None))
    assert sheet.key == sheet.sounding_key == "G"
    assert sheet.capo == ""

def test_missing_key_is_empty():
    page = _page().replace("<span>Tom<!-- -->: </span>", "")
    sheet = parse_page(page)
    assert sheet.key == sheet.sounding_key == ""

def test_no_chord_block_raises():
    with pytest.raises(ValueError, match="No chord sheet"):
        parse_page("<html><title>Busca - Cifra Club</title></html>")


# ---------------------------------------------------------------------------
# render_sheet
# ---------------------------------------------------------------------------


def _sheet(key="C", sounding="Db", capo="1ª casa") -> ChordSheet:
    return ChordSheet("Site Title", "Artist", key, sounding, capo, "C       G\nLetra")


def test_blank_key_transposes_to_sounding_key():
    content = render_sheet(_sheet(), "Minha Canção")
    assert content.splitlines()[0] == "### Minha Canção (Db)"
    assert content.splitlines()[2] == "Db      Ab"

def test_heading_uses_given_title_not_site_title():
    assert "Site Title" not in render_sheet(_sheet(), "Minha Canção")

def test_explicit_key():
    content = render_sheet(_sheet(), "X", "D")
    assert content.splitlines()[0] == "### X (D)"
    assert content.splitlines()[2] == "D       A"

def test_written_key_keeps_chords_as_is():
    content = render_sheet(_sheet(), "X", "C")
    assert content == "### X (C)\n\nC       G\nLetra\n"

def test_no_capo_and_blank_key_is_unchanged():
    content = render_sheet(_sheet(sounding="C", capo=""), "X")
    assert content == "### X (C)\n\nC       G\nLetra\n"

def test_minor_song_stays_minor():
    sheet = ChordSheet("t", "a", "Am", "Am", "", "Am      E\nLetra")
    content = render_sheet(sheet, "X", "E")
    assert content.splitlines()[0] == "### X (Em)"
    assert content.splitlines()[2] == "Em      B"

def test_unknown_key_raises():
    with pytest.raises(ValueError, match="Unknown key"):
        render_sheet(_sheet(), "X", "H")

def test_page_without_key_cannot_transpose():
    sheet = ChordSheet("t", "a", "", "", "", "C\nLetra")
    assert render_sheet(sheet, "X") == "### X ()\n\nC\nLetra\n"
    with pytest.raises(ValueError, match="no key"):
        render_sheet(sheet, "X", "D")


# ---------------------------------------------------------------------------
# is_cifraclub_url / fetch_page
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "https://www.cifraclub.com.br/artista/musica/",
    "http://cifraclub.com.br/artista/musica/",
    "  https://m.cifraclub.com.br/artista/musica/  ",
])
def test_accepts_cifraclub_urls(url):
    assert is_cifraclub_url(url)


@pytest.mark.parametrize("url", [
    "www.cifraclub.com.br/artista/musica/",      # no scheme
    "https://cifraclub.com.br.evil.example/x",   # look-alike host
    "https://www.youtube.com/watch?v=abc",
    "ftp://www.cifraclub.com.br/x",
    "",
])
def test_rejects_other_urls(url):
    assert not is_cifraclub_url(url)


def test_fetch_rejects_non_cifraclub_url_without_network(mocker):
    urlopen = mocker.patch("library.cifraclub.urllib.request.urlopen")
    with pytest.raises(ValueError, match="not a Cifra Club URL"):
        fetch_page("https://example.com/")
    urlopen.assert_not_called()


def test_fetch_sends_browser_headers_and_decompresses_gzip(mocker):
    resp = mocker.MagicMock()
    resp.read.return_value = gzip.compress("<p>olá</p>".encode("utf-8"))
    resp.headers.get.return_value = "gzip"
    resp.headers.get_content_charset.return_value = "utf-8"
    urlopen = mocker.patch("library.cifraclub.urllib.request.urlopen")
    urlopen.return_value.__enter__.return_value = resp

    assert fetch_page("https://www.cifraclub.com.br/a/b/") == "<p>olá</p>"
    request = urlopen.call_args[0][0]
    assert "Mozilla" in request.get_header("User-agent")
