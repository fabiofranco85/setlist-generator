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

### Replace Songs
```bash
# Auto-select replacement for position 2 in louvor
python replace_song.py --moment louvor --position 2

# Manual replacement with specific song
python replace_song.py --moment louvor --position 2 --with "Oceanos"

# Replace multiple positions (auto mode)
python replace_song.py --moment louvor --positions 1,3

# Replace for specific date
python replace_song.py --date 2026-03-15 --moment louvor --position 2
```

## Architecture

### Core Algorithm

The song selection algorithm (`select_songs_for_moment`) uses a **composite scoring system**:

```
score = weight × (recency + 0.1) + random(0, 0.5)
```

Where:
- **weight**: From tags.csv (e.g., `louvor(5)` → weight=5)
- **recency**: Time-based decay score (0.0 = just used, 1.0 = never used / very long ago)
- **random factor**: Adds variety to avoid deterministic selection

### Data Flow

1. **Load songs** from `tags.csv` + `chords/*.md` files (includes energy metadata)
2. **Load history** from `history/*.json` (sorted by date, most recent first)
3. **Calculate recency scores** for all songs using time-based exponential decay (considers full history)
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

### Time-Based Recency System

`RECENCY_DECAY_DAYS = 45` (setlist/config.py:16)

**NEW:** The system now uses **time-based exponential decay** to calculate recency scores, considering the **full history** of all services (not just the last 3).

**Formula:** `recency_score = 1.0 - exp(-days_since_last_use / DECAY_CONSTANT)`

Songs get higher scores the longer it's been since they were last used:

| Days Since Last Use | Score | Impact |
|---------------------|-------|--------|
| 7 days | 0.14 | Heavy penalty |
| 14 days | 0.27 | Strong penalty |
| 30 days | 0.49 | Moderate penalty |
| 45 days (decay constant) | 0.63 | Getting fresh |
| 60 days | 0.74 | Very fresh |
| 90+ days | 0.86+ | Almost "never used" |

**Key benefits:**
- ✅ Considers **all history**, not just last 3 performances
- ✅ Time-aware: 21 days ≠ 49 days (old system treated both as "beyond 3 services")
- ✅ Smooth, continuous scoring (no sharp cutoffs)
- ✅ Songs gradually become candidates again as time passes

**Configuration:**
- **30 days**: Faster cycling (small libraries, frequent services)
- **45 days**: Balanced (default - most churches)
- **60-90 days**: Slower cycling (larger libraries, maximum variety)

For detailed documentation, see: [`RECENCY_SYSTEM.md`](./RECENCY_SYSTEM.md)

## Modifying Song Selection Behavior

### Change moment counts
Edit `MOMENTS_CONFIG` in `setlist/config.py`

### Change recency decay rate
Edit `RECENCY_DECAY_DAYS` in `setlist/config.py` (default: 45)
- Lower values (30) = faster cycling
- Higher values (60-90) = slower cycling, more variety

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
   ### New Song Title (G)

   G               D
   Verse lyrics...
   ```

3. Run generator - new song will be automatically included in selection pool

**Energy Classification Guide:**
- **Energy 1**: Fast tempo, celebratory, high intensity (e.g., Hosana)
- **Energy 2**: Moderate tempo, engaging, rhythmic (e.g., Oceanos)
- **Energy 3**: Slower tempo, reflective, thoughtful (e.g., Perfeito Amor)
- **Energy 4**: Very slow, intimate, deep worship (e.g., Lugar Secreto)

## Replacing Songs in Generated Setlists

After generating a setlist, users can replace songs using `replace_song.py`.

### Command Structure

```bash
python replace_song.py --moment MOMENT [--position N] [--with SONG] [--date DATE]
```

**Required:**
- `--moment`: Service moment (prelúdio, ofertório, saudação, crianças, louvor, poslúdio)

**Optional:**
- `--position N`: Position to replace (1-indexed). Default: 1
- `--positions N,N`: Multiple positions (comma-separated). Cannot be used with --position.
- `--with SONG`: Manual replacement (auto-select if omitted)
- `--date YYYY-MM-DD`: Target date (default: latest)
- `--output-dir`, `--history-dir`: Custom paths

**Note:** When neither `--position` nor `--positions` is specified, defaults to position 1.

### Implementation Details

**Core Module:** `setlist/replacer.py`

**Key Functions:**

1. **`find_target_setlist(history, target_date=None)`**
   - Locates setlist by date (latest or specific)
   - Returns: Setlist dict `{"date": "...", "moments": {...}}`
   - Raises: `ValueError` if date not found or no history exists

2. **`validate_replacement_request(setlist, moment, position, replacement_song, songs)`**
   - Validates moment exists in `MOMENTS_CONFIG`
   - Validates position in range (0-indexed internally)
   - Validates manual song exists and has required moment tag
   - Raises: `ValueError` with descriptive message on failure

3. **`select_replacement_song(moment, setlist, position, songs, history, manual_replacement=None)`**
   - Auto mode: Uses `select_songs_for_moment()` with exclusion set
   - Manual mode: Validates and returns user-specified song
   - Returns: Song title (str)
   - Raises: `ValueError` if no suitable replacement found

4. **`replace_song_in_setlist(setlist_dict, moment, position, replacement_song, songs, reorder_energy=True)`**
   - Single replacement with energy reordering
   - Creates new setlist dict (immutable pattern)
   - Calls `apply_energy_ordering()` if enabled
   - Returns: Updated setlist dict

5. **`replace_songs_batch(setlist_dict, replacements, songs, history)`**
   - Multiple replacements at once
   - Validates all replacements first
   - Prevents duplicate selections in batch
   - Reorders each affected moment by energy
   - Returns: Updated setlist dict

### Algorithm Details

**Auto-Selection Process:**

1. Build exclusion set: all songs in setlist EXCEPT the one being replaced
2. Calculate recency scores for target date (same date as original setlist)
3. Call `select_songs_for_moment()` with:
   - `count=1`
   - `already_selected=exclusion_set`
   - `overrides=None`
4. Apply energy ordering to the moment (all songs treated as auto-selected)

**Key Insight:** By excluding all songs EXCEPT the replacement target, the selection algorithm can "re-pick" for that position while avoiding duplicates.

**Recency Consistency:**
- Uses SAME date as original setlist for recency calculation
- Ensures consistent scoring with original generation
- Replacement candidates scored as if generated on that date

**Energy Reordering:**
- Always reapplied after replacement (if `ENERGY_ORDERING_ENABLED`)
- Maintains emotional arc (1→4 for louvor)
- All songs treated as auto-selected (no override preservation)
- Override count set to 0 when calling `apply_energy_ordering()`

**Position Indexing:**
- User-facing: 1-indexed (1, 2, 3, 4)
- Internal: 0-indexed (0, 1, 2, 3)
- Conversion: `internal_pos = user_pos - 1`

### Reusable Components

The replacement feature reuses existing modules:
- `selector.calculate_recency_scores()` - Time-based decay scoring
- `selector.select_songs_for_moment()` - Weighted selection algorithm
- `ordering.apply_energy_ordering()` - Energy-based song ordering
- `formatter.format_setlist_markdown()` - Markdown generation
- `formatter.save_setlist_history()` - JSON history saving
- `loader.load_songs()` - Load songs from CSV and chords
- `loader.load_history()` - Load historical setlists

### Error Handling

Validates and raises `ValueError` with descriptive messages for:
- Moment doesn't exist in `MOMENTS_CONFIG`
- Position out of valid range (0 to N-1 internally)
- Manual song doesn't exist in database
- Manual song not tagged for target moment
- Manual song already in setlist
- History directory empty
- Target date doesn't exist in history
- No available replacement songs (all eligible songs already used)

### Usage Examples

```bash
# Replace first song (defaults to position 1)
python replace_song.py --moment prelúdio

# Auto replacement - system picks best song for specific position
python replace_song.py --moment louvor --position 2

# Manual replacement - user specifies song
python replace_song.py --moment louvor --position 2 --with "Oceanos"

# Replace for specific date
python replace_song.py --date 2026-03-01 --moment louvor --position 2

# Batch replacement (all auto-selected)
python replace_song.py --moment louvor --positions 1,3
```

### Programmatic Usage

```python
from setlist import (
    load_songs,
    load_history,
    find_target_setlist,
    select_replacement_song,
    replace_song_in_setlist,
)
from pathlib import Path

# Load data
songs = load_songs(Path("."))
history = load_history(Path("./history"))

# Find latest setlist
setlist_dict = find_target_setlist(history)

# Auto-select replacement
replacement = select_replacement_song(
    moment="louvor",
    setlist=setlist_dict,
    position=1,  # 0-indexed internally
    songs=songs,
    history=history,
    manual_replacement=None  # Auto mode
)

# Apply replacement
new_setlist = replace_song_in_setlist(
    setlist_dict=setlist_dict,
    moment="louvor",
    position=1,
    replacement_song=replacement,
    songs=songs,
    reorder_energy=True
)

# Save results using formatter functions
from setlist import format_setlist_markdown, save_setlist_history
from setlist.models import Setlist

setlist_obj = Setlist(date=new_setlist["date"], moments=new_setlist["moments"])
markdown = format_setlist_markdown(setlist_obj, songs)
save_setlist_history(setlist_obj, Path("./history"))
```

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
```
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
