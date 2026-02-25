# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Documentation Structure

This project uses **path-scoped documentation** to keep context focused. Different documentation files load based on which code you're working on:

- **Core Architecture** (`.claude/rules/core-architecture.md`) - Always loaded. Contains project overview, algorithms, data structures, and configuration.
- **CLI Commands** (`.claude/rules/cli.md`) - Loads when working on `cli/**/*.py`. Contains all command documentation and usage examples.
- **Data Maintenance** (`.claude/rules/data-maintenance.md`) - Loads when working on maintenance scripts. Contains cleanup and import utilities.
- **Development Guide** (`.claude/rules/development.md`) - Loads when working on `library/**/*.py`. Contains module details and implementation patterns.

### Documentation Rules

- Always update README.md and its references when implementing, changing, or removing features
- Keep CLAUDE.md and .claude/* files in sync with code changes
- Update documentation before committing

## Quick Start

### Installation
```bash
# Install with uv (recommended)
uv sync

# With PostgreSQL backend support
uv sync --group postgres

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
songbook info "Oceanos"              # Song statistics and history
songbook info                        # Interactive picker → statistics
songbook replace --moment louvor --position 2  # Replace song
songbook replace --moment louvor --position 2 --pick  # Interactive picker
songbook replace --moment louvor --position 2 --label evening  # Replace in labeled
songbook label --date 2026-03-01 --to evening  # Add label to setlist
songbook label --date 2026-03-01 --label evening --to night  # Rename label
songbook label --date 2026-03-01 --label evening --remove  # Remove label
songbook transpose "Oceanos" --to G  # Transpose chords (preview)
songbook transpose "Oceanos" --to G --save  # Transpose and persist
songbook view-song "Oceanos" -t G    # View song transposed
songbook pdf --date 2026-02-15       # Generate PDF
songbook pdf --label evening         # Generate PDF for labeled setlist
songbook markdown --date 2026-02-15  # Regenerate markdown from history
songbook youtube --date 2026-02-15   # Create YouTube playlist from setlist
songbook list-moments                # List available moments
songbook list-moments -e youth       # List moments for event type
songbook event-type list             # List event types
songbook event-type add youth --name "Youth Service"  # Add event type
songbook generate -e youth           # Generate for event type
songbook cleanup                     # Data quality checks
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
│   ├── config.py               # Configuration constants
│   ├── models.py               # Song and Setlist data structures
│   ├── event_type.py           # Event type definitions and filtering
│   ├── loader.py               # Data loading
│   ├── labeler.py              # Setlist label management
│   ├── selector.py             # Song selection algorithms
│   ├── ordering.py             # Energy-based ordering
│   ├── transposer.py           # Chord transposition (chromatic)
│   ├── generator.py            # Core setlist generation
│   ├── replacer.py             # Song replacement + derivation
│   ├── formatter.py            # Output formatting
│   ├── pdf_formatter.py        # PDF generation
│   ├── youtube.py              # YouTube playlist integration
│   └── repositories/           # Data access abstraction
│       ├── filesystem/         # Default CSV+JSON backend
│       └── postgres/           # PostgreSQL backend (optional)
├── scripts/                     # Utilities
│   ├── schema.sql              # PostgreSQL DDL + seed data
│   ├── migrate_event_types.sql # Event types migration (existing DBs)
│   └── migrate_to_postgres.py  # Filesystem → PostgreSQL migration
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
   ```
   - Energy: 1=upbeat, 2=moderate-high, 3=moderate-low, 4=contemplative
   - Tags: moment names with optional weights in parentheses
   - YouTube: optional YouTube video URL

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
songbook generate --pdf  # Include PDF output
songbook generate -e youth --date 2026-03-20  # Generate for event type
```

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
songbook replace --moment louvor --position 2 --pick            # Interactive picker
songbook replace --moment louvor --position 2 --with "Oceanos"  # Manual
songbook replace --moment louvor --position 2 --label evening   # In labeled setlist
```

**Manage labels:**
```bash
songbook label --date 2026-03-01 --to evening                  # Add label
songbook label --date 2026-03-01 --label evening --to night    # Rename label
songbook label --date 2026-03-01 --label evening --remove      # Remove label
```

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

**Transpose a song:**
```bash
songbook transpose "Oceanos" --to G          # Preview only
songbook transpose "Oceanos" --to G --save   # Overwrite chord file
songbook view-song "Oceanos" --transpose G   # View transposed (always dry)
```

**View setlist:**
```bash
songbook view-setlist --date 2026-02-15 --keys
songbook view-setlist --date 2026-03-01 --label evening  # View labeled
```

**Data quality:**
```bash
songbook cleanup  # Check and fix data issues
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
- `repos.history.get_by_date(date, label="", event_type="")` - Get specific setlist
- `repos.history.get_by_date_all(date)` - Get all setlists for a date (all labels/types)
- `repos.history.exists(date, label="", event_type="")` - Check if setlist exists
- `repos.history.update(date, data, label="", event_type="")` - Update a setlist
- `repos.history.delete(date, label="", event_type="")` - Delete a setlist
- `repos.output.save_markdown(date, content, label="", event_type="")` - Save markdown
- `repos.output.get_markdown_path(date, label="", event_type="")` - Get output path
- `repos.output.get_pdf_path(date, label="", event_type="")` - Get PDF path
- `repos.output.delete_outputs(date, label="", event_type="")` - Delete md + pdf files
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

### Storage Backend

Set `STORAGE_BACKEND` environment variable to choose the data backend:

```bash
STORAGE_BACKEND=filesystem   # Default (CSV + JSON files)
STORAGE_BACKEND=postgres     # PostgreSQL database
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

## Dependencies

- Python 3.12+
- Standard library (no external dependencies for core functionality)
- `simple-term-menu` for interactive song picker (CLI)
- Optional: `reportlab` for PDF generation
- Optional: `psycopg[binary,pool]>=3.1` for PostgreSQL backend
- Optional: `uv` for package management

## Further Reading

For detailed documentation on specific areas, see the path-scoped documentation files in `.claude/rules/`:

- **Architecture details** → `.claude/rules/core-architecture.md`
- **CLI commands** → `.claude/rules/cli.md`
- **Data maintenance** → `.claude/rules/data-maintenance.md`
- **Development patterns** → `.claude/rules/development.md`
- **Recency system** → `RECENCY_SYSTEM.md`
- **Storage backends** → `STORAGE_BACKENDS.md`
- **YouTube integration** → `YOUTUBE.md`
