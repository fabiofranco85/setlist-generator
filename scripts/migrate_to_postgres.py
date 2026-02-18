#!/usr/bin/env python3
"""Migrate filesystem data to PostgreSQL.

Reads database.csv, chords/*.md, and history/*.json from the project root
and upserts everything into a PostgreSQL database.

Usage:
    python scripts/migrate_to_postgres.py --database-url postgresql://user:pass@host/db
    python scripts/migrate_to_postgres.py --apply-schema  # Also run schema.sql first

Idempotent: safe to re-run (all operations use ON CONFLICT DO UPDATE).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

# Add project root to path so we can import library modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from library.loader import parse_tags


def get_connection(database_url: str):
    """Create a psycopg connection.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        A psycopg Connection object.
    """
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


def apply_schema(conn, schema_path: Path) -> None:
    """Execute the schema SQL file.

    Args:
        conn: psycopg connection.
        schema_path: Path to schema.sql.
    """
    sql = schema_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"  Applied schema from {schema_path}")


def migrate_songs(conn, base_path: Path) -> int:
    """Migrate songs from database.csv and chords/*.md.

    Args:
        conn: psycopg connection.
        base_path: Project root containing database.csv and chords/.

    Returns:
        Number of songs migrated.
    """
    db_file = base_path / "database.csv"
    chords_dir = base_path / "chords"

    if not db_file.exists():
        print(f"  Warning: {db_file} not found, skipping songs", file=sys.stderr)
        return 0

    count = 0
    with open(db_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            title = row["song"]
            energy_str = row.get("energy", "").strip()
            energy = float(energy_str) if energy_str else 2.5
            youtube_url = (row.get("youtube") or "").strip()

            # Load chord content
            chord_file = chords_dir / f"{title}.md"
            content = chord_file.read_text(encoding="utf-8") if chord_file.exists() else ""

            # Upsert song
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO songs (title, energy, content, youtube_url) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (title) DO UPDATE SET "
                    "energy = EXCLUDED.energy, content = EXCLUDED.content, "
                    "youtube_url = EXCLUDED.youtube_url",
                    (title, energy, content, youtube_url),
                )

                # Parse and upsert tags
                tags = parse_tags(row["tags"])
                for moment, weight in tags.items():
                    cur.execute(
                        "INSERT INTO song_tags (song_title, moment, weight) "
                        "VALUES (%s, %s, %s) "
                        "ON CONFLICT (song_title, moment) DO UPDATE SET "
                        "weight = EXCLUDED.weight",
                        (title, moment, weight),
                    )

                # Remove stale tags no longer in CSV
                if tags:
                    cur.execute(
                        "DELETE FROM song_tags "
                        "WHERE song_title = %s AND NOT (moment = ANY(%s))",
                        (title, list(tags.keys())),
                    )
                else:
                    cur.execute(
                        "DELETE FROM song_tags WHERE song_title = %s",
                        (title,),
                    )

            count += 1

    conn.commit()
    return count


def migrate_history(conn, base_path: Path) -> int:
    """Migrate setlist history from history/*.json.

    Args:
        conn: psycopg connection.
        base_path: Project root containing history/.

    Returns:
        Number of setlists migrated.
    """
    history_dir = base_path / "history"

    if not history_dir.exists():
        print(f"  Warning: {history_dir} not found, skipping history", file=sys.stderr)
        return 0

    count = 0
    for json_file in sorted(history_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  Warning: Skipping {json_file.name}: {e}", file=sys.stderr)
            continue

        # Validate required fields
        if "date" not in data or "moments" not in data:
            print(f"  Warning: Skipping {json_file.name}: missing date or moments", file=sys.stderr)
            continue

        date = data["date"]
        label = data.get("label", "")
        moments = data["moments"]

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO setlists (date, label, moments) "
                "VALUES (%s, %s, %s::jsonb) "
                "ON CONFLICT (date, label) DO UPDATE SET "
                "moments = EXCLUDED.moments",
                (date, label, json.dumps(moments)),
            )

        count += 1

    conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Migrate filesystem data to PostgreSQL"
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection string (or set DATABASE_URL env var)",
    )
    parser.add_argument(
        "--apply-schema",
        action="store_true",
        help="Run scripts/schema.sql before migrating data",
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root directory (default: auto-detected)",
    )
    args = parser.parse_args()

    # Resolve database URL
    import os

    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        print(
            "Error: No database URL. Use --database-url or set DATABASE_URL.",
            file=sys.stderr,
        )
        sys.exit(1)

    conn = get_connection(database_url)

    try:
        # Optionally apply schema
        if args.apply_schema:
            schema_path = PROJECT_ROOT / "scripts" / "schema.sql"
            if not schema_path.exists():
                print(f"Error: Schema file not found: {schema_path}", file=sys.stderr)
                sys.exit(1)
            print("Applying schema...")
            apply_schema(conn, schema_path)

        # Migrate songs
        print("Migrating songs...")
        song_count = migrate_songs(conn, args.base_path)
        print(f"  Migrated {song_count} songs")

        # Migrate history
        print("Migrating history...")
        history_count = migrate_history(conn, args.base_path)
        print(f"  Migrated {history_count} setlists")

        print("Migration complete!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
