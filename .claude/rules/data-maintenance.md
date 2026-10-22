---
paths:
  - "cli/commands/maintenance.py"
  - "scripts/**/*.py"
  - "scripts/**/*.sql"
  - "migrate_folders.py"
---

# Data Maintenance Utilities

This document describes the data-maintenance commands and migration scripts in the project. It loads when working on maintenance code, the `scripts/` directory, or `migrate_folders.py`.

## Overview

Maintenance work splits into two layers:

1. **CLI maintenance commands** — `songbook cleanup`, `songbook fix-punctuation`, `songbook import-history`. Implemented as thin shims in `cli/commands/maintenance.py` that defer to top-level helper modules (`cleanup_history`, `fix_punctuation`, `import_real_history`).
2. **Migration scripts** — one-shot `scripts/*.py` and `scripts/*.sql` files plus `migrate_folders.py` at the project root. Used during schema upgrades or storage-backend transitions.

> **Status note:** The shim commands reference helper modules (`cleanup_history`, `fix_punctuation`, `import_real_history`) that are not currently checked into the repository. As a result, `songbook cleanup`, `songbook fix-punctuation`, and `songbook import-history` will raise `ModuleNotFoundError` until those helpers are added (or the shims are rewritten in-place). When fixing or extending these commands, treat `cli/commands/maintenance.py` as the integration boundary — the actual algorithms live (or should live) in the helper modules.

## CLI Commands

### songbook cleanup

**Module:** `cli/commands/maintenance.py:run_cleanup`
**Defers to:** `cleanup_history.main()` (top-level helper, not in `library/`)

Intended behavior — automated quality check for history files:

- Analyse all history files for inconsistencies with `database.csv`
- Auto-fix capitalization mismatches (e.g. `"deus grandão" → "Deus Grandão"`)
- Identify songs in history not present in `database.csv`
- Suggest similar database entries via fuzzy match
- Snapshot a backup of the `history/` directory before changing anything

```bash
songbook cleanup
```

**Caveat:** the shim accepts `--history-dir` but the underlying script uses a hardcoded `./history` path; the shim prints a warning when a custom dir is supplied. Fix this when you reintroduce/modify the helper.

### songbook fix-punctuation

**Module:** `cli/commands/maintenance.py:run_fix_punctuation`
**Defers to:** `fix_punctuation.main()`

Intended behavior — normalize punctuation differences in history files (commas, hyphens) to match canonical names from `database.csv`. Same `--history-dir` caveat as `cleanup`.

```bash
songbook fix-punctuation
```

### songbook import-history

**Module:** `cli/commands/maintenance.py:run_import`
**Defers to:** `import_real_history.main()`

Interactive workflow that imports external setlist data into the internal `history/*.json` format. The shim prompts the user to confirm they have edited the helper script's `raw_data` dictionary before running.

```bash
songbook import-history
```

Expected external format (per the shim's interactive prompt and historical helper behavior):

```json
{
  "2025-12-28": {
    "format": "setlist_with_moments",
    "service_moments": {
      "Prelúdio": [{"title": "Song Name", "key": "D"}],
      "Louvor": [
        {"title": "Song 1", "key": "G"},
        {"title": "Song 2", "key": "C"}
      ]
    }
  }
}
```

Suggested moment-name mapping for any reimplementation:

| External (Portuguese long form) | Internal moment slug |
|---------------------------------|----------------------|
| Prelúdio                        | prelúdio             |
| Louvor                          | louvor               |
| Oferta                          | ofertório            |
| Comunhão                        | saudação             |
| Crianças                        | crianças             |
| Poslúdio                        | poslúdio             |

## Migration Scripts

Located in `scripts/` and at the project root.

### scripts/schema.sql / scripts/supabase_schema.sql

DDL for the PostgreSQL and Supabase backends respectively. Idempotent (`IF NOT EXISTS` / `ON CONFLICT DO NOTHING`). Apply with `psql $DATABASE_URL -f scripts/schema.sql`.

### scripts/supabase_seed.sql

Seeds the `system_config` table with values matching `library/config.py` defaults, so a fresh Supabase project starts in a working state.

### scripts/migrate_event_types.sql

For existing PostgreSQL databases — adds the event-type columns and `event_types` table introduced by commit `f507027`.

### scripts/migrate_moments_order.sql

Adds the `moments_order` column to existing `event_types` tables (introduced by commits `775aadf` / `3696d7d`).

### scripts/migrate_set_org_context.sql

Helper SQL for setting Supabase RLS context (`current_setting('app.org_id', true)::UUID`).

### scripts/migrate_to_postgres.py, scripts/migrate_chords_to_postgres.py — **DELETED**

Both were one-shot filesystem → PostgreSQL importers: the first loaded
`database.csv` / `chords/` / `history/` / `event_types.json`, the second
backfilled `songs.content` from `chords/*.md`.

They were **deleted** once the migration completed and PostgreSQL became the
sole source of truth. The directories they read no longer exist in this repo, so
both could only ever fail — leaving them in place would have been a trap for
anyone (human or agent) who found them and assumed they still worked.

Recover from git history if ever needed:

```bash
git show 775dbc7:scripts/migrate_to_postgres.py
git show 775dbc7:scripts/migrate_chords_to_postgres.py
```

To populate a fresh database, apply `scripts/schema.sql` and add songs via
`songbook add`, which writes straight to the active backend.

### scripts/reconstruct_from_outputs.py

Disaster-recovery replay. After restoring a `.backups/*.sql.gz` dump, it
replays everything the markdown in `output/` knows that the database does not.
The markdown written by `format_setlist_markdown` embeds every song's chord
sheet verbatim, so it doubles as a backup of both setlists and chord content.

```bash
uv run python scripts/reconstruct_from_outputs.py --dry-run   # print the diff, write nothing
uv run python scripts/reconstruct_from_outputs.py             # apply it
```

What it does, in order:

1. **New songs** (in `output/` but not in the DB): prompts for energy, a weight
   per moment the song appeared in, extra moments, YouTube URL and event-type
   binding, then `repos.songs.add()`. The markdown carries none of that
   metadata, so the prompts are unavoidable.
2. **Chord content** newer in `output/` than in the DB: `update_content()`.
   The newest setlist date wins when a song appears with several variants.
3. **Setlists** missing from the DB: `repos.history.save()` (upsert).

Selection rules:

- Setlist identity comes from the file path, `output/[<event_type>/]{date}[_{label}].md`,
  never from the header line (an event type name may itself contain parentheses).
- Setlists dated on or before `--since` (default: the date of the dump the
  script was written for, `2026-05-18`) are skipped and reported, unless named
  with `--include <id>`. `--exclude <id>` drops any setlist. Ids look like
  `2026-09-13`, `2026-06-07_morning`, `ceia/2026-09-13_culto_dia`.
- PDF-only setlists (no sibling `.md`) are reported but not replayed; a PDF
  carries no chord content.
- `*_lyrics*` files are ignored.
- An `output/<slug>/` directory for an unknown event type aborts the run;
  create the event type first.
- Re-running on an up-to-date database prints "Nothing to do."

The parser and planner are pure functions in `library/output_parser.py`
(`scan_output_dir`, `parse_setlist_markdown`, `resolve_title`,
`plan_reconstruction`), unit-tested in `tests/unit/test_output_parser.py`; the
script itself is covered end-to-end on the filesystem backend in
`tests/integration/test_reconstruct_script.py`.

### scripts/supabase_hardening.sql

Enables row-level security (no policies) on the five tables and revokes the
default grants from `anon` and `authenticated`, so Supabase's Data API cannot
read the repertoire. The CLI's `postgres` role bypasses RLS. Idempotent; apply
right after creating or restoring the schema on a Supabase project. Fails on a
plain Postgres (the roles do not exist), which is expected.

### scripts/backup_db.sh

Dumps the database named by `.env`'s `DATABASE_URL` into
`.backups/songbook-<UTC stamp>.sql.gz` as plain SQL (`--clean --if-exists
--no-owner --no-privileges`, schema `public` only). Needs a `pg_dump` at least
as new as the server (see `STORAGE_BACKENDS.md`, "Hosting on Supabase").

## Workflow: Disaster Recovery

The database is the only copy of song metadata (energy, weights, YouTube URLs,
event-type bindings); `output/` is a second copy of setlists and chord content.
To rebuild after losing the database:

```bash
# 0. Snapshot output/ first: the steps below regenerate files, and output/ is
#    gitignored, so a mistyped path has no other copy to fall back on.
cp -R output .backups/output-$(date -u +%Y%m%dT%H%M%SZ)

# 1. Restore the newest dump (carries its own DDL)
set -a; source .env; set +a
gunzip -c .backups/songbook-<stamp>.sql.gz | psql "$DATABASE_URL" -v ON_ERROR_STOP=1 --single-transaction

# 2. Harden (Supabase only)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/supabase_hardening.sql

# 3. Replay what output/ knows since the dump
uv run python scripts/reconstruct_from_outputs.py --dry-run --since <dump date>
uv run python scripts/reconstruct_from_outputs.py --since <dump date>

# 4. Verify: regenerate a few setlists into a scratch dir and diff against output/
songbook markdown --date 2026-09-13 -e ceia -l culto_dia --output-dir /tmp/rt/out
diff /tmp/rt/out/ceia/2026-09-13_culto_dia.md output/ceia/2026-09-13_culto_dia.md

# 5. Take a fresh backup
scripts/backup_db.sh
```

A regenerated file differs from the snapshot only where a song's chord content
was edited or transposed after that file was written, since the newest content
wins.

### migrate_folders.py (project root)

One-shot reorganisation that splits the legacy `setlists/` directory into `output/` (markdown) and `history/` (JSON). Run from the project root once; safe to delete after a successful migration.

```bash
python migrate_folders.py
```

## Workflow: Importing External Data

Once the helper modules are in place, the canonical end-to-end workflow is:

```bash
# 1. Edit raw_data in the helper script (import_real_history.py)
# 2. Import
songbook import-history

# 3. Check for data-quality issues
songbook cleanup

# 4. Normalize punctuation if cleanup flagged any
songbook fix-punctuation

# 5. Re-run cleanup to verify (should report 0 issues)
songbook cleanup

# 6. Smoke-test generation against the imported history
songbook generate --date 2026-03-01 --no-save
songbook view-setlist --date 2026-03-01 --keys
```

## Common Issues

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `ModuleNotFoundError: cleanup_history` (or similar) | Helper module not in the repo yet | Add the helper module at the project root, or rewrite `maintenance.py` to inline the algorithm |
| Cleanup reports a song that exists in `database.csv` | Capitalization or punctuation drift | `songbook cleanup` auto-fixes capitalization; punctuation needs `fix-punctuation` mappings |
| `songbook cleanup --history-dir custom/` ignores the flag | Shim limitation: helper uses hardcoded `./history` | Update the helper to accept a `--history-dir` argument |
| Import skips dates with `Unknown moment: XYZ` | External moment name not in the mapping | Extend the mapping table in the helper |

## Testing

Until the helper modules are reintroduced, the shim commands cannot be exercised end-to-end. When adding tests for new helpers:

```python
def test_capitalization_fix(tmp_path):
    """Capitalization fixes match canonical database entries."""
    # 1. Seed a tmp_path with database.csv + history/*.json
    # 2. Invoke the cleanup helper with cwd=tmp_path
    # 3. Assert the history JSON now uses canonical capitalization
```

For migration scripts, prefer integration tests against a temporary database (`postgres` marker) over unit tests with mocks — the value is in the SQL doing the right thing.
