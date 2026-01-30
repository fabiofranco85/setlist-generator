"""PDF formatting for setlists using ReportLab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Preformatted,
    Table,
    TableStyle,
)
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

from .models import Setlist, Song
from .config import MOMENTS_CONFIG


@dataclass
class TOCEntry:
    """Table of contents entry."""

    moment: str  # Display name (e.g., "Prelúdio")
    song_title: str
    song_key: str
    page_number: int
    is_moment_header: bool  # True for moment headers, False for songs


# Portuguese locale mappings
WEEKDAY_NAMES = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}

MONTH_NAMES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

# Moment display name mapping (internal → PDF)
MOMENT_DISPLAY_NAMES = {
    "prelúdio": "Prelúdio",
    "ofertório": "Oferta",
    "saudação": "Comunhão",
    "crianças": "Crianças",
    "louvor": "Louvor",
    "poslúdio": "Poslúdio",
}


def format_date_portuguese(date_str: str) -> str:
    """Convert YYYY-MM-DD to Portuguese format.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Formatted date like "Domingo, 25 de Janeiro de 2026"
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = WEEKDAY_NAMES[dt.weekday()]
    day = dt.day
    month = MONTH_NAMES[dt.month]
    year = dt.year
    return f"{weekday}, {day} de {month} de {year}"


def get_moment_display_name(moment: str) -> str:
    """Get PDF display name for a moment.

    Args:
        moment: Internal moment name (e.g., "ofertório")

    Returns:
        Display name for PDF (e.g., "Oferta")
    """
    return MOMENT_DISPLAY_NAMES.get(moment, moment.capitalize())


def parse_song_title_and_key(song_title: str, song: Song) -> Tuple[str, str]:
    """Extract title and key from song.

    Args:
        song_title: Song title (may contain key)
        song: Song object with content

    Returns:
        Tuple of (title, key)
    """
    # Try to extract key from song content (first line: ###Title (Key) or ### Title (Key))
    if song.content:
        first_line = song.content.split("\n")[0].strip()
        if "(" in first_line and ")" in first_line:
            # Extract key from markdown heading
            start = first_line.rfind("(")
            end = first_line.rfind(")")
            if start != -1 and end != -1 and end > start:
                key = first_line[start + 1 : end].strip()
                # Remove markdown heading and key from title
                title = (
                    first_line.replace("###", "")
                    .replace(f"({key})", "")
                    .strip()
                )
                return title, key

    # Fallback: use song_title as-is
    return song_title, ""


def extract_chord_content(song: Song) -> str:
    """Extract chord content from song (remove markdown heading).

    Args:
        song: Song object

    Returns:
        Chord content without the title line
    """
    if not song.content:
        return ""

    lines = song.content.split("\n")
    if lines and lines[0].strip().startswith("###"):
        # Remove first line (markdown heading) and any blank lines at start
        content_lines = lines[1:]
        # Skip initial blank lines
        while content_lines and not content_lines[0].strip():
            content_lines = content_lines[1:]
        return "\n".join(content_lines)

    return song.content.strip()


class PageTracker:
    """Tracks page numbers during PDF generation."""

    def __init__(self):
        self.page_map: Dict[str, int] = {}
        self.current_page = 2  # Page 1 is TOC
        self.current_moment: str | None = None

    def on_page(self, canvas, doc):
        """Callback for page breaks - tracks current page number."""
        pass  # Page tracking happens in build process


def build_toc_entries(
    setlist: Setlist, songs: Dict[str, Song], page_map: Dict[str, int]
) -> List[TOCEntry]:
    """Build table of contents entries.

    Args:
        setlist: Setlist object
        songs: Dictionary of song name -> Song
        page_map: Dictionary of moment -> page number

    Returns:
        List of TOCEntry objects
    """
    entries = []

    # Iterate through moments in order
    for moment in MOMENTS_CONFIG.keys():
        if moment not in setlist.moments:
            continue

        song_list = setlist.moments[moment]
        if not song_list:
            continue

        display_name = get_moment_display_name(moment)
        page_num = page_map.get(moment, 2)

        # Add moment header
        entries.append(
            TOCEntry(
                moment=display_name,
                song_title="",
                song_key="",
                page_number=page_num,
                is_moment_header=True,
            )
        )

        # Add songs for this moment
        for song_title in song_list:
            song = songs.get(song_title)
            if song:
                title, key = parse_song_title_and_key(song_title, song)
                entries.append(
                    TOCEntry(
                        moment=display_name,
                        song_title=title,
                        song_key=key,
                        page_number=page_num,
                        is_moment_header=False,
                    )
                )

    return entries


def create_styles():
    """Create custom paragraph styles for PDF."""
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName="Helvetica-Bold",
    )

    # Subtitle style (date)
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        fontSize=14,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName="Helvetica",
    )

    # TOC moment header style
    toc_moment_style = ParagraphStyle(
        "TOCMoment",
        fontSize=12,
        fontName="Helvetica-Bold",
        spaceAfter=0,
        leftIndent=0,
    )

    # TOC song style
    toc_song_style = ParagraphStyle(
        "TOCSong",
        fontSize=11,
        fontName="Helvetica",
        spaceAfter=0,
        leftIndent=20,
    )

    # Moment header style (content pages)
    moment_header_style = ParagraphStyle(
        "MomentHeader",
        fontSize=18,
        fontName="Helvetica-Bold",
        spaceAfter=12,
        spaceBefore=0,
    )

    # Song title style (content pages)
    song_title_style = ParagraphStyle(
        "SongTitle",
        fontSize=14,
        fontName="Helvetica",
        spaceAfter=12,
    )

    # Chord content style
    chord_style = ParagraphStyle(
        "Chords",
        fontSize=10,
        fontName="Courier",
        leftIndent=0,
        spaceAfter=0,
        leading=12,
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "toc_moment": toc_moment_style,
        "toc_song": toc_song_style,
        "moment_header": moment_header_style,
        "song_title": song_title_style,
        "chord": chord_style,
    }


def build_pdf_content(
    setlist: Setlist,
    songs: Dict[str, Song],
    formatted_date: str,
    toc_entries: List[TOCEntry],
    styles: dict,
) -> List:
    """Build flowables for PDF content.

    Args:
        setlist: Setlist object
        songs: Dictionary of songs
        formatted_date: Formatted date string
        toc_entries: TOC entries
        styles: Style dictionary

    Returns:
        List of flowables for PDF
    """
    story = []

    # Page 1: Table of Contents
    story.append(Paragraph("Setlist", styles["title"]))
    story.append(Paragraph(formatted_date, styles["subtitle"]))
    story.append(Spacer(1, 0.5 * cm))

    # Build TOC table
    toc_data = []
    for entry in toc_entries:
        if entry.is_moment_header:
            # Moment header row
            row = [
                Paragraph(entry.moment, styles["toc_moment"]),
                Paragraph(str(entry.page_number), styles["toc_moment"]),
            ]
        else:
            # Song row (indented)
            song_with_key = (
                f"{entry.song_title} ({entry.song_key})"
                if entry.song_key
                else entry.song_title
            )
            row = [
                Paragraph(f"  {song_with_key}", styles["toc_song"]),
                Paragraph(str(entry.page_number), styles["toc_song"]),
            ]
        toc_data.append(row)

    # Create TOC table
    toc_table = Table(toc_data, colWidths=[14 * cm, 2 * cm])
    toc_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(toc_table)

    # Content pages: Each moment starts on a new page
    for moment in MOMENTS_CONFIG.keys():
        if moment not in setlist.moments:
            continue

        song_list = setlist.moments[moment]
        if not song_list:
            continue

        # Page break before each moment
        story.append(PageBreak())

        # Moment header
        display_name = get_moment_display_name(moment)
        story.append(Paragraph(display_name, styles["moment_header"]))
        story.append(Spacer(1, 0.3 * cm))

        # Songs for this moment
        for song_title in song_list:
            song = songs.get(song_title)
            if not song:
                continue

            # Song title with key
            title, key = parse_song_title_and_key(song_title, song)
            title_with_key = f"{title} ({key})" if key else title
            story.append(Paragraph(title_with_key, styles["song_title"]))

            # Chord content (monospace)
            chord_content = extract_chord_content(song)
            if chord_content:
                # Use Preformatted for monospace rendering
                preformatted = Preformatted(
                    chord_content,
                    styles["chord"],
                    maxLineLength=100,  # Allow long lines
                )
                story.append(preformatted)
                story.append(Spacer(1, 0.5 * cm))

    return story


def calculate_page_numbers(
    setlist: Setlist, songs: Dict[str, Song], formatted_date: str, output_path: Path
) -> Dict[str, int]:
    """Calculate page numbers using two-pass rendering.

    Args:
        setlist: Setlist object
        songs: Dictionary of songs
        formatted_date: Formatted date string
        output_path: Output file path

    Returns:
        Dictionary mapping moment -> page number
    """
    # For simplicity, we'll estimate page numbers based on content length
    # A more accurate approach would require actual rendering, but this is sufficient
    page_map = {}
    current_page = 2  # Page 1 is TOC

    for moment in MOMENTS_CONFIG.keys():
        if moment not in setlist.moments:
            continue

        song_list = setlist.moments[moment]
        if not song_list:
            continue

        # Mark moment start page
        page_map[moment] = current_page

        # Estimate pages for songs in this moment
        # (Simple heuristic: each song ~2-3 pages based on content length)
        for song_title in song_list:
            song = songs.get(song_title)
            if song and song.content:
                # Rough estimate: 1 page per 600 characters
                lines = song.content.count("\n")
                estimated_pages = max(1, lines // 25)
                current_page += estimated_pages

    return page_map


def generate_setlist_pdf(
    setlist: Setlist, songs: Dict[str, Song], output_path: Path
) -> None:
    """Generate PDF setlist matching the reference format.

    Args:
        setlist: Setlist object with date and moments
        songs: Dictionary mapping song names to Song objects
        output_path: Path where PDF should be saved
    """
    # Format date
    formatted_date = format_date_portuguese(setlist.date)

    # Calculate page numbers (simplified - just use moment starts)
    # For a more accurate TOC, we could do a two-pass render
    page_map = {}
    current_page = 2  # Page 1 is TOC

    for moment in MOMENTS_CONFIG.keys():
        if moment not in setlist.moments:
            continue
        song_list = setlist.moments[moment]
        if song_list:
            page_map[moment] = current_page
            # Increment page for next moment (each moment starts new page)
            current_page += 1

    # Create styles
    styles = create_styles()

    # Build TOC entries
    toc_entries = build_toc_entries(setlist, songs, page_map)

    # Build PDF content
    story = build_pdf_content(setlist, songs, formatted_date, toc_entries, styles)

    # Create PDF
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    # Build PDF
    doc.build(story)
