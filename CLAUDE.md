# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **setlist generator** for church worship services. It intelligently selects songs based on:
- **Moments/Tags**: Songs are categorized into service moments (prelúdio, louvor, ofertório, saudação, crianças, poslúdio)
- **Weighted preferences**: Each song-moment association can have a weight (1-10, default 3)
- **Energy-based sequencing**: Songs are ordered by energy level to create emotional arcs (e.g., upbeat → worship)
- **Recency tracking**: Avoids recently used songs by tracking performance history
- **Manual overrides**: Allows forcing specific songs for any moment

## Key Commands

### Generate Setlist
```bash
# Generate for today
python generate_setlist.py

# Generate for specific date
python generate_setlist.py --date 2026-02-15

# Override specific moments
python generate_setlist.py --override "louvor:Oceanos,Santo Pra Sempre"
python generate_setlist.py --override "prelúdio:Estamos de Pé" --override "louvor:Oceanos"

# Dry run (don't save to history)
python generate_setlist.py --no-save

# Custom output directories
python generate_setlist.py --output-dir custom/output --history-dir custom/history
```

### Running with uv
```bash
uv run generate_setlist.py [options]
```

## Architecture

### Core Algorithm

The song selection algorithm (`select_songs_for_moment`) uses a **composite scoring system**:

```
score = weight × (recency + 0.1) + random(0, 0.5)
```

Where:
- **weight**: From tags.csv (e.g., `louvor(5)` → weight=5)
- **recency**: Penalty factor based on last 3 performances (0.0 = just used, 1.0 = never used)
- **random factor**: Adds variety to avoid deterministic selection

### Data Flow

1. **Load songs** from `tags.csv` + `chords/*.md` files (includes energy metadata)
2. **Load history** from `history/*.json` (sorted by date, most recent first)
3. **Calculate recency scores** for all songs based on last 3 performances
4. **Generate setlist** by selecting songs for each moment using score-based algorithm
5. **Apply energy ordering** to multi-song moments (e.g., louvor: 1→4 progression)
6. **Output**:
   - Terminal summary (song titles only)
   - `output/YYYY-MM-DD.md` (full markdown with chords)
   - `history/YYYY-MM-DD.json` (history tracking)

### File Structure

```
.
├── tags.csv                 # Song database: "song;energy;tags"
├── chords/                  # Individual song files with chords
│   └── <Song Name>.md       # Format: "# Song (Key)\n```\nchords...\n```"
├── output/                  # Generated markdown setlists
│   └── YYYY-MM-DD.md        # Human-readable setlist with full chords
├── history/                 # JSON history tracking
│   └── YYYY-MM-DD.json      # History tracking (moments → song lists)
├── generate_setlist.py      # CLI entry point
└── setlist/                 # Core package (modular architecture)
    ├── __init__.py          # Public API exports
    ├── config.py            # Configuration constants
    ├── models.py            # Song and Setlist data structures
    ├── loader.py            # Data loading (CSV, history, chords)
    ├── selector.py          # Song selection algorithms
    ├── paths.py             # Path resolution utilities
    ├── ordering.py          # Energy-based ordering
    ├── generator.py         # Core setlist generation
    └── formatter.py         # Output formatting (markdown, JSON)
```

### Modular Architecture

The codebase is organized into focused modules for better maintainability and reusability:

**Benefits:**
- **Single Responsibility**: Each module has one clear purpose
- **Testability**: Modules can be tested independently
- **Extensibility**: Easy to add new features (e.g., new selection algorithms, ordering strategies)
- **Reusability**: Can be imported by other scripts or used to build a web API

**Module Responsibilities:**
- `config.py` - Configuration constants (moments, weights, energy rules)
- `models.py` - Data structures (Song, Setlist dataclasses)
- `loader.py` - Load songs from CSV and history from JSON
- `selector.py` - Song selection algorithms (scoring, recency calculation)
- `ordering.py` - Energy-based ordering for emotional arcs
- `generator.py` - Orchestrates the complete setlist generation (includes SetlistGenerator class)
- `formatter.py` - Output formatting (markdown, JSON)

### Hybrid Architecture (Functional + Object-Oriented)

The codebase uses a **hybrid approach** that combines functional and object-oriented programming:

- **Classes** for stateful operations (SetlistGenerator)
- **Functions** for stateless algorithms (ordering, formatting)

**Philosophy:** "Use classes where state lives, functions where logic flows"

**When to Use Classes:**
- Managing state (recency scores, selected songs)
- Providing query/command APIs
- Encapsulating complex workflows

**When to Use Functions:**
- Stateless transformations (energy ordering)
- Pure algorithms (score calculation)
- Simple utilities (formatting)

**SetlistGenerator Class:**

The `SetlistGenerator` class encapsulates the stateful operations of setlist generation:

```python
from setlist import SetlistGenerator, load_songs, load_history
from pathlib import Path

# Load data
songs = load_songs(Path("."))
history = load_history(Path("./history"))

# Create generator (manages state internally)
generator = SetlistGenerator(songs, history)

# Generate setlist
setlist = generator.generate(
    date="2026-02-15",
    overrides={"louvor": ["Oceanos", "Ousado Amor"]}
)

# Access results
for moment, song_list in setlist.moments.items():
    print(f"{moment}: {', '.join(song_list)}")
```

**Benefits of SetlistGenerator class:**
- ✓ State managed internally (no mutable parameter passing)
- ✓ Clear lifecycle (init → generate → return)
- ✓ Easy to test (mock constructor params)
- ✓ Reusable (generate multiple setlists with same instance)

**Backward-Compatible Functional API:**

For backward compatibility, the functional API is still available:

```python
from setlist import load_songs, load_history, generate_setlist
from pathlib import Path

# Load data
songs = load_songs(Path("."))
history = load_history(Path("./history"))

# Generate setlist (functional style)
setlist = generate_setlist(
    songs=songs,
    history=history,
    date="2026-02-15",
    overrides={"louvor": ["Oceanos", "Ousado Amor"]}
)
```

Both APIs produce identical results. New code should prefer `SetlistGenerator` for better state management.

**Programmatic Usage:**

The package can be imported and used programmatically. See the "Hybrid Architecture" section above for examples of both the object-oriented (`SetlistGenerator` class) and functional (`generate_setlist` function) APIs.

### Output Path Configuration

The generator supports configurable output paths through multiple methods with the following priority (highest to lowest):

**1. CLI Arguments (Highest Priority):**
```bash
python generate_setlist.py --output-dir custom/output --history-dir custom/history
```

**2. Environment Variables:**
```bash
export SETLIST_OUTPUT_DIR=/data/output
export SETLIST_HISTORY_DIR=/data/history
python generate_setlist.py
```

**3. Configuration File (setlist/config.py):**
```python
DEFAULT_OUTPUT_DIR = "output"    # Markdown files
DEFAULT_HISTORY_DIR = "history"  # JSON tracking
```

**4. Hardcoded Defaults:**
If no configuration is provided, uses `output/` for markdown files and `history/` for JSON tracking.

**Programmatic Usage:**
```python
from setlist import get_output_paths
from pathlib import Path

# Use defaults
paths = get_output_paths(Path("."))
print(paths.output_dir)   # Path("output")
print(paths.history_dir)  # Path("history")

# Override with custom paths
paths = get_output_paths(
    base_path=Path("."),
    cli_output_dir="custom/out",
    cli_history_dir="custom/hist"
)
```

### Moments Configuration

Defined in `MOMENTS_CONFIG` (setlist/config.py):

| Moment      | Count | Description                 |
|-------------|-------|-----------------------------|
| prelúdio    | 1     | Opening/introductory song   |
| ofertório   | 1     | Offering song               |
| saudação    | 1     | Greeting/welcome song       |
| crianças    | 1     | Children's song             |
| louvor      | 4     | Main worship block          |
| poslúdio    | 1     | Closing song                |

### Tags Format

In `tags.csv`:
- Format: `song;energy;tags`
- Energy: 1-4 scale (intrinsic property of the song)
- Tags: Moment assignments with optional weights

Examples:
```csv
Oceanos;2;louvor(5)
Hosana;1;louvor
Lugar Secreto;4;louvor
Autoridade e Poder;1;prelúdio,poslúdio
Brilha Jesus;2;saudação(4),poslúdio(2)
```

Tag syntax:
- Basic: `moment` (uses default weight 3)
- Weighted: `moment(5)` (weight 5)
- Multiple: `moment1,moment2(4)` (moment1 uses weight 3, moment2 uses weight 4)

### Energy System

Songs have an intrinsic **energy level** (1-4) that defines their musical character:

| Energy | Description | Examples |
|--------|-------------|----------|
| **1** | High energy, upbeat, celebratory | Hosana, Santo Pra Sempre, Estamos de Pé |
| **2** | Moderate-high, engaging, rhythmic | Oceanos, Ousado Amor, Grande É o Senhor |
| **3** | Moderate-low, reflective, slower | Perfeito Amor, Consagração, Jesus Em Tua Presença |
| **4** | Deep worship, contemplative, intimate | Tudo é Perda, Lugar Secreto, Aos Pés da Cruz |

**Energy Ordering:**
- Configured per moment in `ENERGY_ORDERING_RULES` (generate_setlist.py:45-48)
- **Louvor**: Ascending order (1→4) creates an emotional arc from upbeat to worship
- **Override preservation**: Manually specified songs maintain user's exact order
- **Auto-selected songs**: Sorted by energy level according to moment rules
- Can be disabled: Set `ENERGY_ORDERING_ENABLED = False` (generate_setlist.py:44)

**Example louvor progression:**
```
1. Hosana (energy: 1) - upbeat, celebratory
2. Oceanos (energy: 2) - engaging, rhythmic
3. Perfeito Amor (energy: 3) - reflective
4. Lugar Secreto (energy: 4) - deep worship
```

### Recency Penalty System

`RECENCY_PENALTY_PERFORMANCES = 3` (generate_setlist.py:41)

Songs are penalized based on how recently they were used:
- **Used in last setlist**: recency = 0.0 (heavily penalized)
- **Used 2 setlists ago**: recency = 0.33
- **Used 3 setlists ago**: recency = 0.67
- **Not used in last 3**: recency = 1.0 (no penalty)

This ensures variety while still allowing high-weight songs to appear relatively frequently.

## Modifying Song Selection Behavior

### Change moment counts
Edit `MOMENTS_CONFIG` in `setlist/config.py`

### Change recency window
Edit `RECENCY_PENALTY_PERFORMANCES` in `setlist/config.py` (default: 3)

### Change default weight
Edit `DEFAULT_WEIGHT` in `setlist/config.py` (default: 3)

### Adjust randomization
Edit the random factor in `setlist/selector.py` (line ~87):
```python
candidates.sort(key=lambda x: x[1] + random.uniform(0, 0.5), reverse=True)
```

### Disable or modify energy ordering
Edit `ENERGY_ORDERING_ENABLED` or `ENERGY_ORDERING_RULES` in `setlist/config.py`

## Adding New Songs

1. Add entry to `tags.csv` with energy and tags:
   ```csv
   New Song Title;2;louvor(4),prelúdio
   ```
   - Choose energy 1-4 based on musical character (1=upbeat, 4=contemplative)
   - If unsure, use 2 or 3 (moderate energy)

2. Create `chords/New Song Title.md`:
   ```markdown
   # New Song Title (G)

   ```
   G               D
   Verse lyrics...
   ```
   ```

3. Run generator - new song will be automatically included in selection pool

**Energy Classification Guide:**
- **Energy 1**: Fast tempo, celebratory, high intensity (e.g., Hosana)
- **Energy 2**: Moderate tempo, engaging, rhythmic (e.g., Oceanos)
- **Energy 3**: Slower tempo, reflective, thoughtful (e.g., Perfeito Amor)
- **Energy 4**: Very slow, intimate, deep worship (e.g., Lugar Secreto)

## Data Maintenance Utilities

The project includes several utility scripts for maintaining data quality and importing external data.

### cleanup_history.py

**Purpose:** Automated data quality checker and fixer for history files.

**What it does:**
- Analyzes all history files for inconsistencies with tags.csv
- Automatically fixes capitalization mismatches (e.g., "deus grandão" → "Deus Grandão")
- Identifies songs in history that don't exist in tags.csv
- Provides fuzzy matching suggestions for similar song names
- Creates timestamped backups before making changes

**When to use:**
- After importing external data
- When you suspect data quality issues
- As a periodic health check (monthly/quarterly)
- Before major changes to tags.csv

**Usage:**
```bash
python cleanup_history.py
```

**Output:**
- Shows capitalization fixes applied
- Lists missing songs with suggestions
- Creates backup directory (e.g., `history_backup_20260129_105330`)

**Example output:**
```
Step 1: Analyzing history files...
  ✓ Loaded 57 songs from tags.csv
  ✓ Found 11 issue(s)

Step 2: Applying capitalization fixes...
  📝 2025-08-31.json
     • 'Reina em mim' → 'Reina em Mim'

Step 3: Songs that need to be added to tags.csv
  ❌ 'New Song Title'
      → Not found in tags.csv
      → Suggested action: Add to tags.csv with energy and moment tags
```

### fix_punctuation.py

**Purpose:** Normalize punctuation differences in history files to match canonical song names.

**What it does:**
- Fixes punctuation variants (commas, hyphens) to match tags.csv
- Handles common variations like "Em Espírito, Em Verdade" → "Em Espírito Em Verdade"
- Updates history files in place

**When to use:**
- After running cleanup_history.py and finding punctuation mismatches
- When importing data with inconsistent punctuation
- As a follow-up to manual history edits

**Usage:**
```bash
python fix_punctuation.py
```

**Note:** This script has a predefined mapping of punctuation variants. Edit the `PUNCTUATION_FIXES` dictionary to add new mappings.

### import_real_history.py

**Purpose:** Import external setlist data and convert it to the internal history format.

**What it does:**
- Parses setlist data from external JSON format
- Maps moment names (e.g., "Oferta" → "ofertório", "Comunhão" → "saudação")
- Filters for supported formats (setlist_with_moments)
- Deletes existing fake/example history files
- Creates properly formatted history/*.json files

**When to use:**
- Initial project setup with existing service history
- Migrating from another system
- Importing bulk historical data

**Usage:**
1. Edit the `raw_data` dictionary in the script with your data
2. Run: `python import_real_history.py`

**Data format expected:**
```python
{
  "2025-12-28": {
    "format": "setlist_with_moments",
    "service_moments": {
      "Prelúdio": [{"title": "Song Name", "key": "D"}],
      "Louvor": [
        {"title": "Song 1", "key": "G"},
        {"title": "Song 2", "key": "C"}
      ]
      # ... other moments
    }
  }
}
```

**Note:** Only processes entries with `format: "setlist_with_moments"`. Other formats are ignored.

### Data Quality Best Practices

1. **Run cleanup_history.py regularly** - Catches issues early
2. **Verify after imports** - Always run cleanup after importing external data
3. **Keep backups** - The cleanup script creates backups automatically
4. **Fix root causes** - If punctuation issues recur, update data entry processes
5. **Document moment mappings** - Keep track of external → internal moment name mappings

### Workflow: Importing External Data

```bash
# 1. Prepare your data in import_real_history.py
# 2. Run import
python import_real_history.py

# 3. Check for data quality issues
python cleanup_history.py

# 4. Fix punctuation if needed
python fix_punctuation.py

# 5. Verify final state
python cleanup_history.py  # Should show 0 issues

# 6. Test generation
python generate_setlist.py --date 2026-03-01 --no-save
```

## Dependencies

- Python 3.12+
- Standard library only (no external dependencies)
- Optional: `uv` for package management
