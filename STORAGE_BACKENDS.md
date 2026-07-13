# Storage Backends

The setlist generator uses a **repository pattern** to abstract data access, allowing you to switch between storage backends without changing your workflow.

## Overview

| Backend | Storage | Dependencies | Best For |
|---------|---------|--------------|----------|
| `filesystem` | CSV + JSON + `.md` files | None (built-in) | Local use, single user (explicit opt-in) |
| `postgres` | PostgreSQL database | `psycopg[binary,pool]` | Teams, servers, web apps |
| `supabase` | Supabase (Postgres + Auth + RLS) | `supabase>=2.0` | Multi-tenant SaaS deployments (paired with the FastAPI layer in `api/`) |

The backend is selected via the `STORAGE_BACKEND` environment variable (default: `postgres`). All CLI commands and programmatic APIs work identically regardless of backend.

**Output storage is independent.** All three data backends ship with a filesystem `OutputRepository` for markdown/PDF files. The SaaS API layer can additionally use an **S3-compatible** `CloudOutputRepository` (`library/repositories/s3/`, requires `boto3>=1.28`) to store outputs in AWS S3, Cloudflare R2, or MinIO — see `.claude/rules/api.md` for the cloud deployment story.

## Filesystem Backend

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
uv sync
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

> **The filesystem → PostgreSQL migration is complete and its scripts have been
> removed.** This repository ships no `database.csv`, `chords/`, or `history/`
> data; PostgreSQL is the source of truth. `scripts/migrate_to_postgres.py` and
> `scripts/migrate_chords_to_postgres.py` read those deleted directories, so
> they could only fail — they were deleted rather than left as traps.

To populate a **fresh** database, apply the schema and add songs through the CLI
(`songbook add`), which writes straight to the active backend:

```bash
psql $DATABASE_URL -f scripts/schema.sql
songbook add "Song Title" --energy 2 --tags "louvor(4)"
```

If you need the old importers, they are in git history:

```bash
git show 775dbc7:scripts/migrate_to_postgres.py
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
uv sync
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

There is no longer a second copy to fall out of sync with — PostgreSQL is the
only source of truth, and `database.csv` / `chords/` no longer exist. Edits made
through `songbook add`, `edit`, `weights`, and `youtube links` land in the
database directly.

If a command still shows stale data, it is the in-process song cache, not the
store: the repositories cache songs and config for the life of the process, so
start a new `songbook` invocation.

## Supabase Backend

The Supabase backend is the multi-tenant variant used by the SaaS API layer in `api/`. It uses Supabase's Postgres database with Row-Level Security policies for tenant isolation, and pairs with S3 (or an S3-compatible service) for output storage.

### Prerequisites

- A Supabase project (or local instance via `npx supabase start`)
- Python package: `supabase>=2.0` (and typically `boto3>=1.28` for S3 outputs)

### Installation

```bash
# Installs supabase, boto3, fastapi, uvicorn
uv sync --group saas
```

### Database Setup

```bash
# Apply the multi-tenant schema (RLS-enforced) and seed system config
psql $SUPABASE_DB_URL -f scripts/supabase_schema.sql
psql $SUPABASE_DB_URL -f scripts/supabase_seed.sql
```

The schema adds tenant tables (`orgs`, `memberships`, `system_admins`), a multi-tenant version of the data model, and a `share_requests` table for cross-org song sharing.

### Configuration

```bash
export STORAGE_BACKEND=supabase
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-service-role-key
```

Per-request, the API also expects:
- `Authorization: Bearer <jwt>` — Supabase user JWT
- `X-Org-Id: <uuid>` — Organization UUID (passed into RLS via `app.org_id`)

### Notes

- **Songs** have three visibility scopes (`global`, `org`, `user`) merged with priority `user > org > global` (`library/sharing.py:merge_effective_library`).
- **Config cascade**: `org_config` → `system_config` → Python constants in `library/config.py`.
- **Output**: filesystem by default; switch to `library/repositories/s3/S3OutputRepository` for cloud deployments (compatible with AWS S3, Cloudflare R2, and MinIO via `endpoint_url`).
- See `.claude/rules/api.md` for the full SaaS architecture, RBAC roles, and endpoint reference.

## Choosing a Backend

| Consideration | Filesystem | PostgreSQL | Supabase |
|--------------|-----------|------------|----------|
| Setup complexity | None | Moderate (requires PostgreSQL) | Moderate (Supabase project + S3 bucket) |
| External dependencies | None | `psycopg[binary,pool]` | `supabase>=2.0` (+ `boto3` for S3 outputs) |
| Multi-user access | No (file conflicts) | Yes (concurrent access) | Yes (multi-tenant with RLS) |
| Multi-tenant isolation | No | No | Yes (per-org via RLS) |
| Web app integration | Limited | Natural fit | Designed for it (paired with `api/`) |
| Backup | Copy files | `pg_dump` | Supabase backups + S3 versioning |
| Query flexibility | Read JSON files | SQL queries | SQL + PostgREST |
| Performance (small dataset) | Fast | Fast | Fast |
| Performance (large dataset) | Adequate | Better (indexed queries) | Better (indexed queries) |
