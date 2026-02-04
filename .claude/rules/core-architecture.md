# Core Architecture

This document describes the fundamental architecture and concepts of the setlist generator system. This documentation is always loaded regardless of which files you're working on.

## Project Overview

This is a **setlist generator** for church worship services. It intelligently selects songs based on:
- **Moments/Tags**: Songs are categorized into service moments (prelúdio, louvor, ofertório, saudação, crianças, poslúdio)
- **Weighted preferences**: Each song-moment association can have a weight (1-10, default 3)
- **Energy-based sequencing**: Songs are ordered by energy level to create emotional arcs (e.g., upbeat → worship)
- **Recency tracking**: Avoids recently used songs by tracking performance history
- **Manual overrides**: Allows forcing specific songs for any moment

## Core Algorithm

The song selection algorithm (`select_songs_for_moment`) uses a **composite scoring system**:

```
score = weight × (recency + 0.1) + random(0, 0.5)
```

Where:
- **weight**: From database.csv (e.g., `louvor(5)` → weight=5)
- **recency**: Time-based decay score (0.0 = just used, 1.0 = never used / very long ago)
- **random factor**: Adds variety to avoid deterministic selection

## Data Flow

1. **Load songs** from `database.csv` + `chords/*.md` files (includes energy metadata)
2. **Load history** from `history/*.json` (sorted by date, most recent first)
3. **Calculate recency scores** for all songs using time-based exponential decay (considers full history)
4. **Generate setlist** by selecting songs for each moment using score-based algorithm
5. **Apply energy ordering** to multi-song moments (e.g., louvor: 1→4 progression)
6. **Output**:
   - Terminal summary (song titles only)
   - `output/YYYY-MM-DD.md` (full markdown with chords)
   - `output/YYYY-MM-DD.pdf` (optional, with `--pdf` flag)
   - `history/YYYY-MM-DD.json` (history tracking)

## File Structure

```
.
├── database.csv                 # Song database: "song;energy;tags;youtube"
├── chords/                  # Individual song files with chords
│   └── <Song Name>.md       # Format: "# Song (Key)\n```\nchords...\n```"
├── output/                  # Generated markdown setlists
│   └── YYYY-MM-DD.md        # Human-readable setlist with full chords
├── history/                 # JSON history tracking
│   └── YYYY-MM-DD.json      # History tracking (moments → song lists)
└── library/                 # Core package (modular architecture)
    ├── __init__.py          # Public API exports
    ├── config.py            # Configuration constants
    ├── models.py            # Song and Setlist data structures
    ├── loader.py            # Data loading (CSV, history, chords)
    ├── selector.py          # Song selection algorithms
    ├── paths.py             # Path resolution utilities
    ├── ordering.py          # Energy-based ordering
    ├── transposer.py        # Chord transposition (chromatic)
    ├── generator.py         # Core setlist generation
    ├── formatter.py         # Output formatting (markdown, JSON)
    ├── pdf_formatter.py     # PDF generation (ReportLab)
    └── youtube.py           # YouTube playlist integration
```

## Modular Architecture

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
- `selector.py` - Song selection algorithms (scoring, recency calculation, usage queries)
- `ordering.py` - Energy-based ordering for emotional arcs
- `transposer.py` - Deterministic chromatic chord transposition (pure functions, `re` only)
- `generator.py` - Orchestrates the complete setlist generation (includes SetlistGenerator class)
- `formatter.py` - Output formatting (markdown, JSON)
- `pdf_formatter.py` - PDF generation using ReportLab
- `youtube.py` - YouTube playlist integration (URL parsing, OAuth, API)

## Hybrid Architecture (Functional + Object-Oriented)

The codebase uses a **hybrid approach** that combines functional and object-oriented programming:

- **Classes** for stateful operations (SetlistGenerator)
- **Functions** for stateless algorithms (ordering, formatting)

**Philosophy:** "Use classes where state lives, functions where logic flows"

**When to Use Classes:**
- Managing state (recency scores, selected songs)
- Providing query/command APIs
- Encapsulating complex workflows

**When to Use Functions:**
- Stateless transformations (energy ordering, chord transposition)
- Pure algorithms (score calculation)
- Simple utilities (formatting)

## Moments Configuration

Defined in `MOMENTS_CONFIG` (library/config.py):

| Moment      | Count | Description                 |
|-------------|-------|-----------------------------|
| prelúdio    | 1     | Opening/introductory song   |
| ofertório   | 1     | Offering song               |
| saudação    | 1     | Greeting/welcome song       |
| crianças    | 1     | Children's song             |
| louvor      | 4     | Main worship block          |
| poslúdio    | 1     | Closing song                |

## Tags Format

In `database.csv`:
- Format: `song;energy;tags;youtube`
- Energy: 1-4 scale (intrinsic property of the song)
- Tags: Moment assignments with optional weights
- YouTube: Optional YouTube video URL

Examples:
```csv
Oceanos;2;louvor(5);https://www.youtube.com/watch?v=XXXXXXXXXXX
Hosana;1;louvor;https://youtu.be/YYYYYYYYYYY
Lugar Secreto;4;louvor;
Autoridade e Poder;1;prelúdio,poslúdio
Brilha Jesus;2;saudação(4),poslúdio(2)
```

Tag syntax:
- Basic: `moment` (uses default weight 3)
- Weighted: `moment(5)` (weight 5)
- Multiple: `moment1,moment2(4)` (moment1 uses weight 3, moment2 uses weight 4)

## Energy System

Songs have an intrinsic **energy level** (1-4) that defines their musical character:

| Energy | Description | Examples |
|--------|-------------|----------|
| **1** | High energy, upbeat, celebratory | Hosana, Santo Pra Sempre, Estamos de Pé |
| **2** | Moderate-high, engaging, rhythmic | Oceanos, Ousado Amor, Grande É o Senhor |
| **3** | Moderate-low, reflective, slower | Perfeito Amor, Consagração, Jesus Em Tua Presença |
| **4** | Deep worship, contemplative, intimate | Tudo é Perda, Lugar Secreto, Aos Pés da Cruz |

**Energy Ordering:**
- Configured per moment in `ENERGY_ORDERING_RULES` (library/config.py)
- **Louvor**: Ascending order (1→4) creates an emotional arc from upbeat to worship
- **Override preservation**: Manually specified songs maintain user's exact order
- **Auto-selected songs**: Sorted by energy level according to moment rules
- Can be disabled: Set `ENERGY_ORDERING_ENABLED = False` (library/config.py)

**Example louvor progression:**
```
1. Hosana (energy: 1) - upbeat, celebratory
2. Oceanos (energy: 2) - engaging, rhythmic
3. Perfeito Amor (energy: 3) - reflective
4. Lugar Secreto (energy: 4) - deep worship
```

## Time-Based Recency System

`RECENCY_DECAY_DAYS = 45` (library/config.py:16)

The system uses **time-based exponential decay** to calculate recency scores, considering the **full history** of all services (not just the last 3).

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

For detailed documentation, see: [`RECENCY_SYSTEM.md`](../../RECENCY_SYSTEM.md)

## Output Path Configuration

The generator supports configurable output paths through multiple methods with the following priority (highest to lowest):

**1. CLI Arguments (Highest Priority):**
```bash
songbook generate --output-dir custom/output --history-dir custom/history
```

**2. Environment Variables:**
```bash
export SETLIST_OUTPUT_DIR=/data/output
export SETLIST_HISTORY_DIR=/data/history
songbook generate
```

**3. Configuration File (library/config.py):**
```python
DEFAULT_OUTPUT_DIR = "output"    # Markdown files
DEFAULT_HISTORY_DIR = "history"  # JSON tracking
```

**4. Hardcoded Defaults:**
If no configuration is provided, uses `output/` for markdown files and `history/` for JSON tracking.

**Programmatic Usage:**
```python
from library import get_output_paths
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

## Modifying Song Selection Behavior

### Change moment counts
Edit `MOMENTS_CONFIG` in `library/config.py`

### Change recency decay rate
Edit `RECENCY_DECAY_DAYS` in `library/config.py` (default: 45)
- Lower values (30) = faster cycling
- Higher values (60-90) = slower cycling, more variety

### Change default weight
Edit `DEFAULT_WEIGHT` in `library/config.py` (default: 3)

### Adjust randomization
Edit the random factor in `library/selector.py` (line ~87):
```python
candidates.sort(key=lambda x: x[1] + random.uniform(0, 0.5), reverse=True)
```

### Disable or modify energy ordering
Edit `ENERGY_ORDERING_ENABLED` or `ENERGY_ORDERING_RULES` in `library/config.py`

## Adding New Songs

1. Add entry to `database.csv` with energy and tags:
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

## Programmatic Usage

### SetlistGenerator Class (Recommended)

The `SetlistGenerator` class encapsulates the stateful operations of setlist generation:

```python
from library import SetlistGenerator, load_songs, load_history
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

### Functional API (Backward Compatible)

For backward compatibility, the functional API is still available:

```python
from library import load_songs, load_history, generate_setlist
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

### Chord Transposition

The `transposer` module provides deterministic chromatic transposition as pure functions:

```python
from library import transpose_content, calculate_semitones, should_use_flats, resolve_target_key

# Transpose song content from Bm to G (resolves to Gm for minor keys)
original_key = "Bm"
target_input = "G"
effective_key = resolve_target_key(original_key, target_input)  # "Gm"
semitones = calculate_semitones(original_key, effective_key)     # 8
use_flats = should_use_flats(effective_key)                     # True (Gm uses flats)

transposed = transpose_content(song.content, semitones, use_flats)
```

**Key functions:**
- `transpose_content(content, semitones, use_flats)` - Transpose full markdown content
- `calculate_semitones(from_key, to_key)` - Interval between two keys
- `should_use_flats(key)` - Whether a key conventionally uses flats
- `resolve_target_key(from_key, to_key)` - Preserve minor/major quality from source key

## Dependencies

- Python 3.12+
- Standard library only (no external dependencies for core functionality)
- Optional: `reportlab` for PDF generation
- Optional: `uv` for package management