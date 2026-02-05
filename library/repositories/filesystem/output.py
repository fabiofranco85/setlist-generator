"""Filesystem implementation of OutputRepository.

This module provides output file generation to the local filesystem:
- Markdown setlists: output/{YYYY-MM-DD}.md
- PDF setlists: output/{YYYY-MM-DD}.pdf
"""

from pathlib import Path

from ...models import Song, Setlist
from ...formatter import format_setlist_markdown


class FilesystemOutputRepository:
    """Output repository backed by filesystem storage.

    Storage format:
    - output/{date}.md: Markdown setlist with chords
    - output/{date}.pdf: PDF setlist with table of contents

    Attributes:
        output_dir: Directory for output files
    """

    def __init__(self, output_dir: Path):
        """Initialize repository with output directory.

        Args:
            output_dir: Directory for output files (markdown and PDF)
        """
        self.output_dir = output_dir

    def _ensure_dir(self) -> None:
        """Ensure output directory exists."""
        self.output_dir.mkdir(exist_ok=True)

    def save_markdown(self, date: str, content: str) -> Path:
        """Save setlist as markdown file.

        Args:
            date: Setlist date (used for filename)
            content: Markdown content to save

        Returns:
            Path to the saved file
        """
        self._ensure_dir()
        output_path = self.output_dir / f"{date}.md"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def save_pdf(self, setlist: Setlist, songs: dict[str, Song]) -> Path:
        """Generate and save setlist as PDF.

        Args:
            setlist: Setlist object with date and moments
            songs: Dictionary of songs for chord content

        Returns:
            Path to the saved PDF file

        Raises:
            ImportError: If reportlab is not installed
        """
        try:
            from ...pdf_formatter import generate_setlist_pdf
        except ImportError as e:
            raise ImportError(
                "PDF generation requires reportlab. "
                "Install with: pip install reportlab"
            ) from e

        self._ensure_dir()
        output_path = self.output_dir / f"{setlist.date}.pdf"
        generate_setlist_pdf(setlist, songs, output_path)
        return output_path

    def get_markdown_path(self, date: str) -> Path:
        """Get the path where markdown would be saved for a date.

        Args:
            date: Setlist date

        Returns:
            Path where markdown file would be saved
        """
        return self.output_dir / f"{date}.md"

    def get_pdf_path(self, date: str) -> Path:
        """Get the path where PDF would be saved for a date.

        Args:
            date: Setlist date

        Returns:
            Path where PDF file would be saved
        """
        return self.output_dir / f"{date}.pdf"

    def save_from_setlist(
        self, setlist: Setlist, songs: dict[str, Song], include_pdf: bool = False
    ) -> tuple[Path, Path | None]:
        """Convenience method to save both markdown and optionally PDF.

        Args:
            setlist: Setlist object with date and moments
            songs: Dictionary of songs for chord content
            include_pdf: Whether to also generate PDF

        Returns:
            Tuple of (markdown_path, pdf_path or None)
        """
        # Generate and save markdown
        markdown_content = format_setlist_markdown(setlist, songs)
        md_path = self.save_markdown(setlist.date, markdown_content)

        # Optionally generate PDF
        pdf_path = None
        if include_pdf:
            pdf_path = self.save_pdf(setlist, songs)

        return md_path, pdf_path
