# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Documentation Structure

This project uses **path-scoped documentation** to keep context focused. Different documentation files load based on which code you're working on:

- **Core Architecture** (`.claude/rules/core-architecture.md`) - Always loaded. Contains project overview, algorithms, data structures, and configuration.
- **CLI Commands** (`.claude/rules/cli.md`) - Loads when working on `cli/**/*.py`. Contains all command documentation and usage examples.
- **SaaS API** (`.claude/rules/api.md`) - Loads when working on `api/**/*.py`, Supabase/S3 backends. Contains endpoints, auth, RBAC, schemas, and backend details.
- **Data Maintenance** (`.claude/rules/data-maintenance.md`) - Loads when working on maintenance scripts. Contains cleanup and import utilities.
- **Development Guide** (`.claude/rules/development.md`) - Loads when working on `library/**/*.py`. Contains module details and implementation patterns.

### Documentation Rules

Doc updates that match a feature change are *part of the surgical change* (see §3 below), not extra scope. Specifically:

- README.md and its references must reflect features as you implement, change, or remove them.
- CLAUDE.md and `.claude/*` files must stay in sync with the code they describe.
- Documentation updates land in the same commit as the code change, not after.

## Quick Start

### Installation
```bash
# Install with uv (recommended)
uv sync

# With PostgreSQL backend support
uv sync --group postgres

# With SaaS API layer (Supabase + S3 + FastAPI)
uv sync --group saas

# Alternative: Using pip
pip install -e .
```

### Adding New Dependencies (Developers)
```bash
# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name
```

### Basic Usage
```bash
songbook --help                      # Main help
songbook generate --date 2026-02-15  # Generate setlist
songbook generate --label evening    # Derive labeled variant from primary
songbook generate --label evening --replace 3  # Derive replacing 3 songs
songbook view-setlist --keys         # View setlist with keys
songbook view-setlist --label evening  # View labeled setlist
songbook view-song "Oceanos"         # View song details
songbook view-song                   # Interactive song picker
songbook edit "Oceanos"              # Open chord file in $EDITOR (default: vim)
songbook edit                        # Interactive picker → editor
songbook edit "Oceanos" --editor nano  # Override editor for this invocation
songbook info "Oceanos"              # Song statistics and history
songbook info                        # Interactive picker → statistics
songbook replace --moment louvor --position 2  # Replace song (re-applies energy ordering)
songbook replace --moment louvor --position 2 --pick  # Interactive picker
songbook replace --moment louvor --position 2 --keep-position  # Don't reorder by energy
songbook replace --moment louvor --position 2 --label evening  # Replace in labeled
songbook remove --moment louvor --position 2  # Remove a single song
songbook remove --moment crianças --all       # Remove an entire moment from the setlist
songbook label --date 2026-03-01 --to evening  # Add label to setlist
songbook label --date 2026-03-01 --label evening --to night  # Rename label
songbook label --date 2026-03-01 --label evening --remove  # Remove label
songbook delete --date 2026-02-15                    # Delete a setlist (prompts)
songbook delete --date 2026-02-15 --yes              # Delete without confirmation
songbook delete --date 2026-03-01 --label evening --yes  # Delete a labeled variant
songbook weights                     # Interactively edit song weights (pick moment → table)
songbook weights --moment louvor     # Jump straight to the louvor weights table
songbook weights -m louvor -e youth  # Same, scoped to the youth song pool
songbook transpose "Oceanos" --to G  # Transpose chords (preview)
songbook transpose "Oceanos" --to G --save  # Transpose and persist
songbook view-song "Oceanos" -t G    # View song transposed
songbook pdf --date 2026-02-15       # Generate PDF (with chords)
songbook pdf --date 2026-02-15 --no-chords  # Lyrics-only PDF for non-musicians
songbook pdf --label evening         # Generate PDF for labeled setlist
songbook markdown --date 2026-02-15  # Regenerate markdown from history
songbook youtube --date 2026-02-15   # Create YouTube playlist from setlist
songbook list-moments                # List available moments
songbook list-moments -e youth       # List moments for event type
songbook event-type list             # List event types
songbook event-type add youth --name "Youth Service"  # Add event type
songbook generate -e youth           # Generate for event type
```

## Project Overview

This is a **setlist generator** for church worship services. It intelligently selects songs based on:

- **Moments/Tags**: Songs categorized into service moments (prelúdio, louvor, ofertório, saudação, crianças, poslúdio)
- **Event Types**: Different service types (main, youth, Christmas) with independent moment configurations and song filtering
- **Weighted preferences**: Each song-moment association can have a weight (1-10, default 3)
- **Energy-based sequencing**: Songs ordered by energy level (1-4) to create emotional arcs
- **Recency tracking**: Avoids recently used songs using time-based exponential decay (45-day default)
- **Manual overrides**: Allows forcing specific songs for any moment

## File Structure

```
.
├── database.csv                 # Song database: "song;energy;tags;youtube"
├── event_types.json             # Event type definitions (auto-created)
├── chords/                      # Individual song files with chords
│   └── <Song Name>.md
├── output/                      # Generated markdown/PDF setlists
│   ├── YYYY-MM-DD.md           # Default event type (root)
│   ├── YYYY-MM-DD_label.md     # Labeled setlist
│   └── <event-type>/           # Non-default event types (subdirectory)
│       └── YYYY-MM-DD.md
├── history/                     # JSON history tracking
│   ├── YYYY-MM-DD.json         # Default event type (root)
│   ├── YYYY-MM-DD_label.json   # Labeled setlist
│   └── <event-type>/           # Non-default event types (subdirectory)
│       └── YYYY-MM-DD.json
├── library/                     # Core package (modular architecture)
│   ├── config.py               # Configuration constants + GenerationConfig
│   ├── models.py               # Song and Setlist data structures
│   ├── event_type.py           # Event type definitions and filtering
│   ├── loader.py               # Tag parsing utilities
│   ├── labeler.py              # Setlist label management
│   ├── selector.py             # Song selection algorithms
│   ├── ordering.py             # Energy-based ordering
│   ├── transposer.py           # Chord transposition (chromatic)
│   ├── generator.py            # Core setlist generation
│   ├── replacer.py             # Song replacement + derivation
│   ├── formatter.py            # Output formatting
│   ├── pdf_formatter.py        # PDF generation (file + in-memory bytes, lyrics-only variant)
│   ├── paths.py                # Output path resolution (PathConfig dataclass)
│   ├── sharing.py              # Song library merging + share validation (SaaS)
│   ├── youtube.py              # YouTube playlist integration
│   ├── observability/          # Structured logging / metrics / tracing (ports + adapters)
│   └── repositories/           # Data access abstraction
│       ├── filesystem/         # Default CSV+JSON backend
│       ├── postgres/           # PostgreSQL backend (optional)
│       ├── supabase/           # Supabase multi-tenant backend (optional)
│       └── s3/                 # S3/R2 cloud output backend (optional)
├── api/                         # FastAPI SaaS API layer (see .claude/rules/api.md)
├── scripts/                     # Utilities
│   ├── schema.sql              # PostgreSQL DDL + seed data
│   ├── supabase_schema.sql     # Supabase multi-tenant schema + RLS
│   ├── supabase_seed.sql       # System config seed data
│   ├── migrate_event_types.sql    # Event types migration (existing DBs)
│   ├── migrate_moments_order.sql  # Add moments_order column (existing DBs)
│   └── migrate_to_postgres.py     # Filesystem → PostgreSQL migration
└── cli/                         # CLI interface
    ├── main.py                 # Entry point
    ├── picker.py               # Interactive song picker (searchable menu)
    └── commands/               # Command implementations
```

## Core Algorithm

Song selection uses a **composite scoring system**:

```
score = weight × (recency + 0.1) + random(0, 0.5)
```

Where:
- **weight**: From the song's tags (e.g., `louvor(5)` → weight=5)
- **recency**: Time-based decay score (0.0 = just used, 1.0 = never used)
- **random factor**: Adds variety to avoid deterministic selection

**Recency Formula:** `recency_score = 1.0 - exp(-days_since_last_use / 45)`

## Adding New Songs

1. Add to `database.csv`:
   ```csv
   New Song Title;2;louvor(4),prelúdio;https://youtu.be/VIDEO_ID
   # With optional 5th column to bind the song to specific event types
   Youth Anthem;1;louvor(5);https://youtu.be/VIDEO_ID;youth,christmas
   ```
   - Energy: 1=upbeat, 2=moderate-high, 3=moderate-low, 4=contemplative
   - Tags: moment names with optional weights in parentheses
   - YouTube: optional YouTube video URL
   - `event_types` (optional 5th column): comma-separated slugs to restrict the song to those event types; empty (or column omitted) = available for all types

2. Create `chords/New Song Title.md`:
   ```markdown
   ### New Song Title (G)

   G               D
   Verse lyrics...
   ```

3. Run generator - new song automatically included in selection pool

## Common Tasks

**Generate setlist:**
```bash
songbook generate --date 2026-02-15
songbook generate --pdf                       # Include PDF output (with chords)
songbook generate --pdf --no-chords           # Also produce a lyrics-only PDF
songbook generate -e youth --date 2026-03-20  # Generate for event type
```

**Lyrics-only PDF (for singers / non-musicians):**

`--no-chords` (on `pdf` and on `generate --pdf`) strips chord lines, the chord-key suffix from song titles, and from the table of contents. The variant is written next to the regular PDF with a `_lyrics` suffix (e.g. `output/2026-02-15_lyrics.pdf`) so both can coexist on disk.

**Multiple setlists per date (labels):**
```bash
songbook generate --date 2026-03-01                      # Primary (unlabeled)
songbook generate --date 2026-03-01 --label evening      # Derive from primary
songbook generate --date 2026-03-01 --label evening --replace 3  # Replace exactly 3
songbook generate --date 2026-03-01 --label evening --replace all  # Replace all
```

**Replace a song:**
```bash
songbook replace --moment louvor --position 2
songbook replace --moment louvor --position 2 --pick             # Interactive picker
songbook replace --moment louvor --position 2 --with "Oceanos"   # Manual
songbook replace --moment louvor --position 2 --keep-position    # Don't reorder by energy
songbook replace --moment louvor --position 2 --label evening    # In labeled setlist
```

**Replacement semantics:**

- **Manual choice (`--with "Song"` or `--pick`)** always wins. The new song is pinned at the exact requested position, energy reordering is skipped, no surprises. This is what you want when you're sure both *which* song and *where*.
- **Auto mode** (no `--with`, no `--pick`) keeps the moment's energy arc by reapplying energy ordering after the swap. A new song with very different energy can land at a different position than the one you asked for; the CLI prints a clear note when this happens and shows the actual new position. Pass `--keep-position` to opt out and pin the auto-picked song to the exact requested position.

**Remove a song or moment:**
```bash
songbook remove --moment louvor --position 2                   # Remove a single song
songbook remove --moment crianças --all                        # Remove the entire moment
songbook remove --moment louvor --position 1 --label evening   # In labeled setlist
songbook remove --moment louvor --all -e youth                 # In event-type setlist
```

**Removal semantics:**

- Exactly one of `--position N` (1-indexed, single song) or `--all` (whole moment) is required.
- **Cascade**: if `--position` removes the last song in its moment, the moment is dropped from the setlist. The CLI prints a heads-up when this happens.
- Markdown is regenerated immediately. An existing PDF is **not** auto-deleted but is flagged as stale — run `songbook pdf` to refresh it. No recency recalculation, no energy reordering — removal is structural-only.
- If a removal leaves the setlist with zero moments, the empty setlist is saved (not auto-deleted); use `songbook delete` to discard it.

**Manage labels:**
```bash
songbook label --date 2026-03-01 --to evening                  # Add label
songbook label --date 2026-03-01 --label evening --to night    # Rename label
songbook label --date 2026-03-01 --label evening --remove      # Remove label
```

**Delete a setlist:**
```bash
songbook delete --date 2026-02-15                              # Prompts to confirm
songbook delete --date 2026-02-15 --yes                        # Skip confirmation
songbook delete --date 2026-03-01 --label evening --yes        # Delete a labeled variant
songbook delete --date 2026-03-20 -e youth --yes               # Delete an event-type setlist
```

Removes the history record and every output file (markdown, regular PDF,
and the lyrics-only `_lyrics.pdf` variant). `--date` is required —
deletion never defaults to the latest setlist to avoid wiping a recent
service by accident. Labels and event types are independent: deleting an
unlabeled primary leaves its labeled siblings (e.g. `evening`) intact,
and vice versa.

**Manage event types:**
```bash
songbook event-type list                                       # List all event types
songbook event-type add youth --name "Youth Service"           # Add event type
songbook event-type edit youth --description "Friday evening"  # Edit event type
songbook event-type moments youth --set "louvor=5,prelúdio=1"  # Set moments
songbook event-type remove youth                               # Remove event type
songbook event-type default --name "Sunday Worship"            # Edit default type
```

**Song statistics:**
```bash
songbook info            # Interactive picker → statistics
songbook info "Oceanos"  # Metadata, recency, and usage history
```

**Edit song-moment weights:**
```bash
songbook weights                        # Interactive moment picker, then song table
songbook weights --moment louvor        # Skip the moment picker
songbook weights -m louvor -e youth     # Same, filtered to the youth song pool
```

The command lists songs tagged for the chosen moment with their current weight,
opens a searchable menu, and prompts for a new weight on `Enter`. Each edit is
saved immediately via `repos.songs.update_tags()` — no separate "save" step,
no risk of losing changes on `Ctrl+C`. Weights must be integers between 1 and
10. Adding a song to a *new* moment (one it isn't tagged for yet) is out of
scope for this command — do that via `database.csv` or your storage backend.

**Transpose a song:**
```bash
songbook transpose "Oceanos" --to G          # Preview only
songbook transpose "Oceanos" --to G --save   # Overwrite chord file
songbook view-song "Oceanos" --transpose G   # View transposed (always dry)
```

**Edit a song's chords/lyrics in an editor:**
```bash
songbook edit "Oceanos"                      # Opens chords/Oceanos.md in $EDITOR
songbook edit                                # Interactive picker, then editor
songbook edit "Oceanos" --editor nano        # Pick a specific editor
EDITOR=code songbook edit "Oceanos"          # via $EDITOR (must block on exit)
```

Editor priority: `--editor` > `$VISUAL` > `$EDITOR` > `vim`. If the chord file
doesn't exist yet, a stub `### Title ()` heading is created so the editor opens
on a real file. On the filesystem backend the chord file is edited in place;
on other backends (postgres / supabase) the content is round-tripped through a
temp file and persisted via `repos.songs.update_content()`.

**GUI editors auto-block**: For `cursor`, `code`, `code-insiders`, `windsurf`,
`zed`, `subl`, `mate`, and `atom`, the appropriate wait flag (`--wait` / `-w`)
is auto-injected if not already present. Without it, GUI editor binaries
return immediately (they just signal an open window) and the CLI would print
"No changes made." before you can type. A "Close the editor tab/window to
continue..." notice is printed so it's clear the CLI is waiting on you.

**View setlist:**
```bash
songbook view-setlist --date 2026-02-15 --keys
songbook view-setlist --date 2026-03-01 --label evening  # View labeled
```

## Programmatic Usage

```python
from library import get_repositories, SetlistGenerator

# Get repositories (uses STORAGE_BACKEND env var, default: filesystem)
repos = get_repositories()

# Create generator from repositories
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)

# Generate setlist
setlist = generator.generate(
    date="2026-02-15",
    overrides={"louvor": ["Oceanos", "Ousado Amor"]}
)

# Generate labeled setlist (for multiple services on same date)
evening = generator.generate(date="2026-02-15", label="evening")

# Generate for a specific event type (uses its moments config)
from library import filter_songs_for_event_type
et = repos.event_types.get("youth")
youth_songs = filter_songs_for_event_type(repos.songs.get_all(), "youth")
setlist = generator.generate(
    date="2026-03-20",
    event_type="youth",
    moments_config=et.moments,
)

# Derive a labeled variant from an existing setlist
from library import derive_setlist
songs = repos.songs.get_all()
history = repos.history.get_all()
base = repos.history.get_by_date("2026-02-15")
derived = derive_setlist(base, songs, history, replace_count=3)

# Save through repositories
repos.history.save(setlist)

# Access results
for moment, song_list in setlist.moments.items():
    print(f"{moment}: {', '.join(song_list)}")
```

**Key repository methods (label-aware and event-type-aware):**
- `repos.songs.update_tags(title, tags)` - Replace a song's full ``{moment: weight}`` mapping (used by `songbook weights`). Raises `KeyError` if the song is missing, `ValueError` for invalid weights.
- `repos.history.backend_name` - Property returning the backend name (e.g. `"filesystem"`, `"postgres"`)
- `repos.history.get_by_date(date, label="", event_type="")` - Get specific setlist
- `repos.history.get_by_date_all(date)` - Get all setlists for a date (all labels/types)
- `repos.history.exists(date, label="", event_type="")` - Check if setlist exists
- `repos.history.update(date, data, label="", event_type="")` - Update a setlist
- `repos.history.delete(date, label="", event_type="")` - Delete a setlist
- `repos.output.save_markdown(date, content, label="", event_type="")` - Save markdown
- `repos.output.save_pdf(setlist, songs, variant="")` - Save PDF; pass `variant="lyrics"` for the lyrics-only variant (filename gets `_lyrics` suffix)
- `repos.output.get_markdown_path(date, label="", event_type="")` - Get output path
- `repos.output.get_pdf_path(date, label="", event_type="", variant="")` - Get PDF path (with optional variant suffix)
- `repos.output.delete_outputs(date, label="", event_type="")` - Delete md + pdf + `_lyrics.pdf` variant files for the given setlist_id (returns the list of paths actually deleted)
- `repos.event_types.get_all()` - Get all event types
- `repos.event_types.get(slug)` - Get event type by slug
- `repos.event_types.add(event_type)` - Add new event type
- `repos.event_types.update(slug, **kwargs)` - Update event type
- `repos.event_types.remove(slug)` - Remove event type (not default)

## Configuration

Key settings in `library/config.py`:

- `MOMENTS_CONFIG` - Service moments and counts (louvor: 4 songs, others: 1 song)
- `RECENCY_DECAY_DAYS` - Recency calculation (default: 45 days)
- `ENERGY_ORDERING_ENABLED` - Enable/disable energy ordering (default: True)
- `DEFAULT_WEIGHT` - Default tag weight (default: 3)
- `DEFAULT_ENERGY` - Fallback energy for songs without explicit energy (default: 2.5)
- `GenerationConfig` - Frozen dataclass that bundles all of the above. `GenerationConfig.from_defaults()` reproduces the CLI behavior; `GenerationConfig.from_config_repo(repo)` reads per-org overrides for the SaaS API. Threaded through `SetlistGenerator`, `selector.calculate_recency_scores`, `ordering.apply_energy_ordering`, `loader.parse_tags`, and `replacer.*`.

### Storage Backend

Set `STORAGE_BACKEND` environment variable to choose the data backend:

```bash
STORAGE_BACKEND=filesystem   # Default (CSV + JSON files)
STORAGE_BACKEND=postgres     # PostgreSQL database
STORAGE_BACKEND=supabase     # Supabase multi-tenant (SaaS)
```

**PostgreSQL setup:**
```bash
# Install psycopg
uv sync --group postgres

# Apply schema
psql $DATABASE_URL -f scripts/schema.sql

# Migrate existing data
python scripts/migrate_to_postgres.py --database-url $DATABASE_URL

# Use postgres backend
STORAGE_BACKEND=postgres DATABASE_URL=postgresql://user:pass@host/db songbook generate --date 2026-03-15
```

### SaaS API (Multi-Tenant)

The `api/` package provides a FastAPI multi-tenant API backed by Supabase (auth + RLS) and S3 (output storage). Install with `uv sync --group saas` and run with `uvicorn api:create_app --factory --reload`. See `.claude/rules/api.md` for full documentation.

### Running API Tests

API integration tests run against a local Supabase instance:

```bash
# Prerequisites: Docker running
npx supabase start          # Start local Supabase (one-time)
uv sync --group dev --group saas --group postgres  # Install test + saas + postgres deps

# Run API tests
uv run pytest tests/integration/api/ -v -m supabase

# Run everything except API tests (when Docker unavailable)
uv run pytest tests/ -m "not supabase"
```

Tests exercise the full endpoint pipeline (routes, schemas, PostgREST queries, JSONB handling) against real Postgres. See `.claude/rules/testing.md` for fixture details.

## Dependencies

- Python 3.12+
- Standard library (no external dependencies for core functionality)
- `simple-term-menu` for interactive song picker (CLI)
- Optional: `reportlab` for PDF generation
- Optional: `psycopg[binary,pool]>=3.1` for PostgreSQL backend
- Optional: `supabase>=2.0`, `boto3>=1.28`, `fastapi>=0.115`, `uvicorn>=0.30` for SaaS API
- Optional: `uv` for package management

## Further Reading

For detailed documentation on specific areas, see the path-scoped documentation files in `.claude/rules/`:

- **Architecture details** → `.claude/rules/core-architecture.md`
- **CLI commands** → `.claude/rules/cli.md`
- **Data maintenance** → `.claude/rules/data-maintenance.md`
- **Development patterns** → `.claude/rules/development.md`
- **Recency system** → `RECENCY_SYSTEM.md`
- **SaaS API** → `.claude/rules/api.md`
- **Storage backends** → `STORAGE_BACKENDS.md`
- **YouTube integration** → `YOUTUBE.md`

---

## Behavioral Guidelines for Claude

Guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
