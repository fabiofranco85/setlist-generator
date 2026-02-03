# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Documentation Structure

This project uses **path-scoped documentation** to keep context focused. Different documentation files load based on which code you're working on:

- **Core Architecture** (`.claude/rules/core-architecture.md`) - Always loaded. Contains project overview, algorithms, data structures, and configuration.
- **CLI Commands** (`.claude/rules/cli.md`) - Loads when working on `cli/**/*.py`. Contains all command documentation and usage examples.
- **Data Maintenance** (`.claude/rules/data-maintenance.md`) - Loads when working on maintenance scripts. Contains cleanup and import utilities.
- **Development Guide** (`.claude/rules/development.md`) - Loads when working on `library/**/*.py`. Contains module details and implementation patterns.

## Quick Start

### Installation
```bash
# Install with uv (recommended)
uv sync

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
songbook view-setlist --keys         # View setlist with keys
songbook view-song "Oceanos"         # View song details
songbook replace --moment louvor --position 2  # Replace song
songbook transpose "Oceanos" --to G  # Transpose chords (preview)
songbook transpose "Oceanos" --to G --save  # Transpose and persist
songbook view-song "Oceanos" -t G    # View song transposed
songbook pdf --date 2026-02-15       # Generate PDF
songbook list-moments                # List available moments
songbook cleanup                     # Data quality checks
```

## Project Overview

This is a **setlist generator** for church worship services. It intelligently selects songs based on:

- **Moments/Tags**: Songs categorized into service moments (prelúdio, louvor, ofertório, saudação, crianças, poslúdio)
- **Weighted preferences**: Each song-moment association can have a weight (1-10, default 3)
- **Energy-based sequencing**: Songs ordered by energy level (1-4) to create emotional arcs
- **Recency tracking**: Avoids recently used songs using time-based exponential decay (45-day default)
- **Manual overrides**: Allows forcing specific songs for any moment

## File Structure

```
.
├── database.csv                 # Song database: "song;energy;tags"
├── chords/                      # Individual song files with chords
│   └── <Song Name>.md
├── output/                      # Generated markdown setlists
│   └── YYYY-MM-DD.md
├── history/                     # JSON history tracking
│   └── YYYY-MM-DD.json
├── library/                     # Core package (modular architecture)
│   ├── config.py               # Configuration constants
│   ├── models.py               # Song and Setlist data structures
│   ├── loader.py               # Data loading
│   ├── selector.py             # Song selection algorithms
│   ├── ordering.py             # Energy-based ordering
│   ├── transposer.py           # Chord transposition (chromatic)
│   ├── generator.py            # Core setlist generation
│   ├── formatter.py            # Output formatting
│   └── pdf_formatter.py        # PDF generation
└── cli/                         # CLI interface
    ├── main.py                 # Entry point
    └── commands/               # Command implementations
```

## Core Algorithm

Song selection uses a **composite scoring system**:

```
score = weight × (recency + 0.1) + random(0, 0.5)
```

Where:
- **weight**: From database.csv tags (e.g., `louvor(5)` → weight=5)
- **recency**: Time-based decay score (0.0 = just used, 1.0 = never used)
- **random factor**: Adds variety to avoid deterministic selection

**Recency Formula:** `recency_score = 1.0 - exp(-days_since_last_use / 45)`

## Adding New Songs

1. Add to `database.csv`:
   ```csv
   New Song Title;2;louvor(4),prelúdio
   ```
   - Energy: 1=upbeat, 2=moderate-high, 3=moderate-low, 4=contemplative
   - Tags: moment names with optional weights in parentheses

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
```

**Replace a song:**
```bash
songbook replace --moment louvor --position 2
songbook replace --moment louvor --position 2 --with "Oceanos"  # Manual
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
```

**Data quality:**
```bash
songbook cleanup  # Check and fix data issues
```

## Programmatic Usage

```python
from library import SetlistGenerator, load_songs, load_history
from pathlib import Path

# Load data
songs = load_songs(Path("."))
history = load_history(Path("./history"))

# Generate setlist
generator = SetlistGenerator(songs, history)
setlist = generator.generate(
    date="2026-02-15",
    overrides={"louvor": ["Oceanos", "Ousado Amor"]}
)

# Access results
for moment, song_list in setlist.moments.items():
    print(f"{moment}: {', '.join(song_list)}")
```

## Configuration

Key settings in `library/config.py`:

- `MOMENTS_CONFIG` - Service moments and counts (louvor: 4 songs, others: 1 song)
- `RECENCY_DECAY_DAYS` - Recency calculation (default: 45 days)
- `ENERGY_ORDERING_ENABLED` - Enable/disable energy ordering (default: True)
- `DEFAULT_WEIGHT` - Default tag weight (default: 3)

## Dependencies

- Python 3.12+
- Standard library (no external dependencies for core functionality)
- Optional: `reportlab` for PDF generation
- Optional: `uv` for package management

## Further Reading

For detailed documentation on specific areas, see the path-scoped documentation files in `.claude/rules/`:

- **Architecture details** → `.claude/rules/core-architecture.md`
- **CLI commands** → `.claude/rules/cli.md`
- **Data maintenance** → `.claude/rules/data-maintenance.md`
- **Development patterns** → `.claude/rules/development.md`
- **Recency system** → `RECENCY_SYSTEM.md`
