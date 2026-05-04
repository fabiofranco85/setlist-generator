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

### scripts/migrate_to_postgres.py

One-shot migration of filesystem data (`database.csv`, `chords/`, `history/`, `event_types.json`) into PostgreSQL. Idempotent — uses `ON CONFLICT DO UPDATE` everywhere.

```bash
python scripts/migrate_to_postgres.py --database-url postgresql://user:pass@host/db
python scripts/migrate_to_postgres.py --database-url $DATABASE_URL --apply-schema
```

### scripts/migrate_chords_to_postgres.py

Backfills `songs.content` (chord markdown) from `chords/*.md` into PostgreSQL. Useful when the schema migration ran before the chord files were imported.

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
