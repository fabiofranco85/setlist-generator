#!/usr/bin/env python3
"""Migrate chord files from the filesystem to PostgreSQL.

Reads chords/*.md from the project root and updates the `content` column
of matching rows in the `songs` table.

Usage:
    python scripts/migrate_chords_to_postgres.py --database-url postgresql://user:pass@host/db
    python scripts/migrate_chords_to_postgres.py  # uses DATABASE_URL env var

Idempotent: safe to re-run (updates existing rows, skips files with no matching song).
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_connection(database_url: str):
    """Create a psycopg connection."""
    try:
        import psycopg
    except ImportError:
        print(
            "Error: psycopg is not installed.\n"
            "Install with: uv sync --group postgres",
            file=sys.stderr,
        )
        sys.exit(1)

    return psycopg.connect(database_url)


def migrate_chords(conn, base_path: Path) -> tuple[int, int]:
    """Update the content column for songs that have chord files.

    Args:
        conn: psycopg connection.
        base_path: Project root containing chords/.

    Returns:
        Tuple of (updated count, skipped count).
    """
    chords_dir = base_path / "chords"

    if not chords_dir.exists():
        print(f"  Error: {chords_dir} not found", file=sys.stderr)
        sys.exit(1)

    chord_files = sorted(chords_dir.glob("*.md"))
    if not chord_files:
        print("  No chord files found")
        return 0, 0

    updated = 0
    skipped = 0

    with conn.cursor() as cur:
        for chord_file in chord_files:
            title = chord_file.stem
            content = chord_file.read_text(encoding="utf-8")

            cur.execute(
                "UPDATE songs SET content = %s WHERE title = %s",
                (content, title),
            )

            if cur.rowcount > 0:
                updated += 1
            else:
                print(f"  Skipped: {title} (no matching song in DB)")
                skipped += 1

    conn.commit()
    return updated, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Migrate chord files from filesystem to PostgreSQL"
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection string (or set DATABASE_URL env var)",
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root directory (default: auto-detected)",
    )
    args = parser.parse_args()

    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        print(
            "Error: No database URL. Use --database-url or set DATABASE_URL.",
            file=sys.stderr,
        )
        sys.exit(1)

    conn = get_connection(database_url)

    try:
        print("Migrating chord files to PostgreSQL...")
        updated, skipped = migrate_chords(conn, args.base_path)
        print(f"  Updated: {updated} songs")
        if skipped:
            print(f"  Skipped: {skipped} files (no matching song in DB)")
        print("Done!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
