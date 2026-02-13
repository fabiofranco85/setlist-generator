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

    @staticmethod
    def _make_setlist_id(date: str, label: str = "") -> str:
        """Build setlist_id from date and optional label."""
        if label:
            return f"{date}_{label}"
        return date

    def save_markdown(self, date: str, content: str, label: str = "") -> Path:
        """Save setlist as markdown file.

        Args:
            date: Setlist date (used for filename)
            content: Markdown content to save
            label: Optional label for multiple setlists per date

        Returns:
            Path to the saved file
        """
        self._ensure_dir()
        setlist_id = self._make_setlist_id(date, label)
        output_path = self.output_dir / f"{setlist_id}.md"
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
        output_path = self.output_dir / f"{setlist.setlist_id}.pdf"
        generate_setlist_pdf(setlist, songs, output_path)
        return output_path

    def delete_outputs(self, date: str, label: str = "") -> list[Path]:
        """Delete markdown and PDF output files for a setlist.

        Args:
            date: Setlist date
            label: Optional label for multiple setlists per date

        Returns:
            List of paths that were actually deleted (may be empty)
        """
        setlist_id = self._make_setlist_id(date, label)
        deleted = []
        for ext in (".md", ".pdf"):
            path = self.output_dir / f"{setlist_id}{ext}"
            if path.exists():
                path.unlink()
                deleted.append(path)
        return deleted

    def get_markdown_path(self, date: str, label: str = "") -> Path:
        """Get the path where markdown would be saved for a date.

        Args:
            date: Setlist date
            label: Optional label for multiple setlists per date

        Returns:
            Path where markdown file would be saved
        """
        setlist_id = self._make_setlist_id(date, label)
        return self.output_dir / f"{setlist_id}.md"

    def get_pdf_path(self, date: str, label: str = "") -> Path:
        """Get the path where PDF would be saved for a date.

        Args:
            date: Setlist date
            label: Optional label for multiple setlists per date

        Returns:
            Path where PDF file would be saved
        """
        setlist_id = self._make_setlist_id(date, label)
        return self.output_dir / f"{setlist_id}.pdf"

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
        md_path = self.save_markdown(setlist.date, markdown_content, label=setlist.label)

        # Optionally generate PDF
        pdf_path = None
        if include_pdf:
            pdf_path = self.save_pdf(setlist, songs)

        return md_path, pdf_path
