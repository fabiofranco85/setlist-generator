# Storage Backends

The setlist generator uses a **repository pattern** to abstract data access, allowing you to switch between storage backends without changing your workflow.

## Overview

| Backend | Storage | Dependencies | Best For |
|---------|---------|--------------|----------|
| `filesystem` (default) | CSV + JSON + `.md` files | None (built-in) | Local use, single user |
| `postgres` | PostgreSQL database | `psycopg[binary,pool]` | Teams, servers, web apps |

The backend is selected via the `STORAGE_BACKEND` environment variable (default: `filesystem`). All CLI commands and programmatic APIs work identically regardless of backend.

## Filesystem Backend (Default)

The filesystem backend stores data as plain files in the project directory. No extra setup is needed.

### How It Works

| Data | Format | Location |
|------|--------|----------|
| Song database | CSV (semicolon-delimited) | `database.csv` |
| Chord sheets | Markdown | `chords/*.md` |
| Setlist history | JSON | `history/*.json` |
| Generated output | Markdown + PDF | `output/*.md`, `output/*.pdf` |

### When to Use

- Single-user, local development
- Simple deployments without a database server
- Quick setup with zero external dependencies

No configuration needed — this is the default.

## PostgreSQL Backend

The PostgreSQL backend stores songs, tags, history, and configuration in a relational database. Output files (markdown and PDF) are always written to the local filesystem.

### Prerequisites

- PostgreSQL 14 or higher
- Python package: `psycopg[binary,pool]>=3.1`

### Installation

```bash
# Install the optional PostgreSQL dependency group
uv sync --group postgres
```

### Database Setup

1. **Create a PostgreSQL database:**

   ```bash
   createdb songbook
   ```

2. **Apply the schema:**

   ```bash
   psql postgresql://user:pass@localhost/songbook -f scripts/schema.sql
   ```

   The schema creates five tables:

   | Table | Purpose |
   |-------|---------|
   | `songs` | Song metadata (title, energy, content, YouTube URL, event_types) |
   | `song_tags` | Normalized moment-weight associations |
   | `setlists` | Setlist history with JSONB moments, event_type, label |
   | `config` | Key-value configuration (JSONB values) |
   | `event_types` | Event type definitions with JSONB moments |

   Key columns for event types:
   - `songs.event_types` — `TEXT[] DEFAULT '{}'` (empty = available for all types)
   - `setlists.event_type` — `TEXT DEFAULT ''` (empty = default type)
   - `setlists` unique constraint: `(date, event_type, label)`

   The schema is idempotent — safe to re-run (`IF NOT EXISTS` / `ON CONFLICT DO NOTHING`).

   **For existing databases**, apply the event types migration:
   ```bash
   psql $DATABASE_URL -f scripts/migrate_event_types.sql
   ```

### Migrating Existing Data

If you have existing data in `database.csv`, `chords/`, and `history/`, migrate it to PostgreSQL:

```bash
python scripts/migrate_to_postgres.py --database-url postgresql://user:pass@localhost/songbook
```

Options:

| Flag | Description |
|------|-------------|
| `--database-url URL` | PostgreSQL connection string (or set `DATABASE_URL` env var) |
| `--apply-schema` | Run `scripts/schema.sql` before migrating |
| `--base-path PATH` | Project root directory (auto-detected by default) |

The migration script is **idempotent** — all operations use `ON CONFLICT DO UPDATE`, so it's safe to re-run after adding new songs or history.

**Combined setup and migration:**

```bash
python scripts/migrate_to_postgres.py \
  --database-url postgresql://user:pass@localhost/songbook \
  --apply-schema
```

### Configuration

Set two environment variables to use the PostgreSQL backend:

```bash
export STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://user:pass@localhost:5432/songbook
```

For convenience, you can place these in a `.env` file (manually sourced) or your shell profile:

```bash
# In ~/.bashrc or ~/.zshrc
export STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://user:pass@localhost:5432/songbook
```

### Usage

Once configured, all CLI commands work exactly as with the filesystem backend:

```bash
# Generate setlist
songbook generate --date 2026-03-15

# View setlist
songbook view-setlist --date 2026-03-15 --keys

# Replace a song
songbook replace --moment louvor --position 2

# Generate PDF
songbook pdf --date 2026-03-15
```

You can also pass environment variables inline:

```bash
STORAGE_BACKEND=postgres DATABASE_URL=postgresql://... songbook generate
```

**Programmatic usage:**

```python
from library import get_repositories, SetlistGenerator

# Explicit backend selection
repos = get_repositories(backend="postgres", database_url="postgresql://user:pass@localhost/songbook")

# Or via environment variables (STORAGE_BACKEND + DATABASE_URL)
repos = get_repositories()

# Same API as filesystem
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
setlist = generator.generate("2026-03-15")
repos.history.save(setlist)
```

### Architecture Notes

- **Connection pooling**: A shared `psycopg_pool.ConnectionPool` (1-5 connections) is created once and reused across all repositories.
- **Caching**: Songs and config are cached in memory after the first read. History is not cached (always reads from the database for freshness).
- **Config fallback**: If a config key is missing from the `config` table, the system falls back to the Python constants in `library/config.py`.
- **Output files**: Markdown and PDF output always uses the local filesystem, regardless of backend. Only song data, history, and configuration are stored in PostgreSQL.

### Troubleshooting

#### "PostgreSQL backend requires psycopg"

The `psycopg` package is not installed. Run:

```bash
uv sync --group postgres
```

#### "No database URL provided"

Set the `DATABASE_URL` environment variable or pass `database_url=` to `get_repositories()`:

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/songbook
```

#### Connection refused

Verify that PostgreSQL is running and the connection string is correct:

```bash
# Test the connection
psql $DATABASE_URL -c "SELECT 1"
```

Common issues:
- PostgreSQL service not running (`brew services start postgresql` on macOS)
- Wrong port (default is 5432)
- Authentication failure (check username/password)

#### Schema not applied

If you see errors about missing tables, apply the schema:

```bash
psql $DATABASE_URL -f scripts/schema.sql
```

#### Data out of sync

If songs or history seem outdated after editing `database.csv`, re-run the migration:

```bash
python scripts/migrate_to_postgres.py --database-url $DATABASE_URL
```

## Choosing a Backend

| Consideration | Filesystem | PostgreSQL |
|--------------|-----------|------------|
| Setup complexity | None | Moderate (requires PostgreSQL) |
| External dependencies | None | `psycopg[binary,pool]` |
| Multi-user access | No (file conflicts) | Yes (concurrent access) |
| Web app integration | Limited | Natural fit |
| Backup | Copy files | `pg_dump` |
| Query flexibility | Read JSON files | SQL queries |
| Performance (small dataset) | Fast | Fast |
| Performance (large dataset) | Adequate | Better (indexed queries) |
