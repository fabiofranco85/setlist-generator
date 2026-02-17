---
paths:
  - "library/**/*.py"
---

# Development Guide

This document provides guidance for developers working on the core setlist library. This documentation is loaded when working on core library code.

## Module Responsibilities

The `library/` package is organized into focused modules:

### config.py
**Purpose:** Configuration constants and settings

**Contents:**
- `MOMENTS_CONFIG` - Service moments with counts and descriptions
- `DEFAULT_WEIGHT` - Default tag weight (3)
- `RECENCY_DECAY_DAYS` - Recency calculation parameter (45 days)
- `ENERGY_ORDERING_ENABLED` - Toggle energy ordering (True)
- `ENERGY_ORDERING_RULES` - Per-moment ordering rules
- `DEFAULT_OUTPUT_DIR` - Markdown output directory ("output")
- `DEFAULT_HISTORY_DIR` - History tracking directory ("history")

**When to modify:**
- Adding new service moments
- Adjusting selection behavior
- Changing default paths

### models.py
**Purpose:** Data structures

**Contents:**
- `Song` dataclass - Represents a song with name, key, tags, energy, chords
- `Setlist` dataclass - Represents a generated setlist with date, moments, and optional label

**When to modify:**
- Adding new song metadata fields
- Adding new setlist properties
- Changing data validation rules

**Example:**
```python
@dataclass
class Song:
    name: str
    key: str
    tags: Dict[str, int]  # moment → weight
    energy: int           # 1-4 scale
    chords: str          # Markdown content

@dataclass
class Setlist:
    date: str                      # YYYY-MM-DD
    moments: Dict[str, List[str]]  # moment → [song names]
    label: str = ""                # Optional label (e.g. "evening", "morning")

    @property
    def setlist_id(self) -> str:   # "YYYY-MM-DD_label" or just "YYYY-MM-DD"
        ...

    def to_dict(self) -> dict:     # Omits "label" key when empty
        ...
```

**Label conventions:**
- `label=""` (default) — unlabeled/primary setlist
- `setlist_id` = `"{date}_{label}"` if labeled, `"{date}"` if unlabeled
- `to_dict()` omits `"label"` key when empty (backward compat)
- Old JSON files without `"label"` key are treated as `label=""`

### loader.py
**Purpose:** Tag parsing utilities

**Contents:**
- `parse_tags(tag_string)` - Parse tag format (e.g., "louvor(5),prelúdio") into dict of {moment: weight}

**Note:** Data loading functions have been replaced by the repository pattern. Use `get_repositories()` for loading songs and history.

### labeler.py
**Purpose:** Setlist label management (add, rename, remove labels)

**Contents:**
- `relabel_setlist(setlist_dict, new_label)` - Create a new Setlist from a source dict with a different label

**When to modify:**
- Changing label transformation logic
- Adding label validation at the library level

**Usage:**
```python
from library import relabel_setlist

# All three operations are the same transformation
new_setlist = relabel_setlist(source_dict, "evening")  # Add label
new_setlist = relabel_setlist(source_dict, "night")    # Rename label
new_setlist = relabel_setlist(source_dict, "")         # Remove label
```

**Design notes:**
- Uses `copy.deepcopy()` on moments (immutable data pattern)
- Returns a `Setlist` object (not a dict)
- Validation (source exists, target doesn't conflict) lives in the CLI layer

### repositories/
**Purpose:** Data access abstraction layer

**Structure:**
```
repositories/
├── __init__.py         # Public exports + get_repositories()
├── protocols.py        # Protocol definitions (interfaces)
├── factory.py          # RepositoryFactory + RepositoryContainer
├── filesystem/         # Default backend (CSV + JSON)
│   ├── __init__.py     # FilesystemRepositoryContainer
│   ├── songs.py        # FilesystemSongRepository
│   ├── history.py      # FilesystemHistoryRepository
│   ├── config.py       # FilesystemConfigRepository
│   └── output.py       # FilesystemOutputRepository
└── postgres/           # Optional backend (requires psycopg)
    ├── __init__.py     # PostgresRepositoryContainer
    ├── connection.py   # create_pool() — shared connection pool
    ├── songs.py        # PostgresSongRepository (cached)
    ├── history.py      # PostgresHistoryRepository (no cache)
    └── config.py       # PostgresConfigRepository (cached, fallback to Python constants)
```

**Key Components:**
- `get_repositories()` - Factory function, reads STORAGE_BACKEND env var
- `RepositoryContainer` - Bundles all repository instances
- Protocols: `SongRepository`, `HistoryRepository`, `ConfigRepository`, `OutputRepository`

**Usage:**
```python
from library import get_repositories, SetlistGenerator

# Get repositories (uses STORAGE_BACKEND env var, default: filesystem)
repos = get_repositories()

# Access data through repositories
songs = repos.songs.get_all()
song = repos.songs.get_by_title("Oceanos")
history = repos.history.get_all()
latest = repos.history.get_latest()
config = repos.config.get_moments_config()

# Use with SetlistGenerator
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
setlist = generator.generate("2026-02-15")

# Save through repositories
repos.history.save(setlist)
repos.output.save_markdown(setlist.date, markdown_content)
```

**Environment Configuration:**
```bash
STORAGE_BACKEND=filesystem  # Default (CSV + JSON files)
STORAGE_BACKEND=postgres    # PostgreSQL (requires psycopg, set DATABASE_URL too)
STORAGE_BACKEND=mongodb     # MongoDB (future)
```

**When to modify:**
- Adding new storage backends
- Adding new repository methods
- Changing caching behavior

**PostgreSQL backend details:**
- Install: `uv sync --group postgres` (adds `psycopg[binary,pool]>=3.1`)
- Schema: `scripts/schema.sql` (run with `psql $DATABASE_URL -f scripts/schema.sql`)
- Migration: `python scripts/migrate_to_postgres.py --database-url $DATABASE_URL`
- Songs + tags are cached in memory (same as filesystem); history is NOT cached
- Config falls back to Python constants for missing keys
- Output always uses `FilesystemOutputRepository` (files are always local)
- Connection pool: `create_pool()` in `postgres/connection.py`, shared across all repos
- Optional dep guard: `try/except ImportError` in `repositories/__init__.py`

### selector.py
**Purpose:** Song selection algorithms and usage queries

**Contents:**
- `calculate_recency_scores(songs, history, target_date)` - Time-based decay scoring
- `get_song_usage_history(song_title, history)` - Full usage history for a song (dates + moments)
- `get_days_since_last_use(song_title, history, current_date)` - Days since most recent use (or None)
- `select_songs_for_moment(moment, count, songs, recency_scores, already_selected, overrides)` - Core selection algorithm

**Key algorithm:**
```python
score = weight × (recency + 0.1) + random(0, 0.5)
```

**When to modify:**
- Changing scoring formula
- Adding new selection constraints
- Implementing alternative selection strategies

**Implementation notes:**
- Recency uses exponential decay: `1.0 - exp(-days / DECAY_CONSTANT)`
- Random factor adds variety: `random.uniform(0, 0.5)`
- Overrides bypass scoring (user-specified songs)

### ordering.py
**Purpose:** Energy-based song ordering

**Contents:**
- `apply_energy_ordering(songs_in_moment, moment, songs, override_count)` - Sort songs by energy level

**Algorithm:**
1. Separate override songs (user-specified) from auto-selected
2. Sort auto-selected songs by energy level (ascending/descending based on moment rules)
3. Preserve override order, apply energy ordering to auto-selected

**When to modify:**
- Adding new ordering strategies (e.g., alphabetical, random)
- Changing energy progression rules
- Implementing complex sequencing logic

**Example:**
```python
# Louvor: 1 → 4 (ascending energy)
ENERGY_ORDERING_RULES = {
    "louvor": "ascending",
    # ... other moments
}
```

### transposer.py
**Purpose:** Deterministic chromatic chord transposition

**Contents:**
- `transpose_note(note, semitones, use_flats)` - Shift a single note by N semitones
- `transpose_chord(chord, semitones, use_flats)` - Transpose full chord symbol (root + optional bass)
- `is_chord_line(line)` - Classify a text line as chords vs lyrics
- `transpose_line(line, semitones, use_flats)` - Transpose all chords in a line, preserving column alignment
- `transpose_content(content, semitones, use_flats)` - Transpose entire song markdown (chord lines + heading key)
- `calculate_semitones(from_key, to_key)` - Calculate interval between two keys
- `should_use_flats(target_key)` - Determine sharp/flat convention for target key
- `resolve_target_key(from_key, to_key)` - Preserve minor/major quality from source key

**Key algorithm — column alignment:**
1. Record each chord's start column in the original line
2. Transpose all chords
3. Place each transposed chord at the original column
4. If a longer chord overflows, ensure minimum 1-space gap

**Chord regex** handles all patterns in the codebase:
- Simple: `G`, `Am`, `C#m`, `Bb`
- Slash: `A/C#`, `E/G#`, `Em7(11)/B`
- Extended: `F7M(9)`, `Dm7(9)`, `G4(6)`, `A7M`

**When to modify:**
- Supporting new chord notation patterns
- Changing sharp/flat key conventions
- Adjusting line classification heuristics
- Adding new enharmonic spellings

**Implementation notes:**
- Pure functions only (no dependencies beyond `re`)
- Follows the project convention for stateless algorithm modules (like `ordering.py`)
- Transposition is modular arithmetic: `(note_index + semitones) % 12`
- `resolve_target_key()` infers minor quality: `Bm` + `--to G` → `Gm`

### generator.py
**Purpose:** Orchestrates setlist generation

**Contents:**
- `SetlistGenerator` class - Stateful generator with recency management
- `generate_setlist()` function - Backward-compatible functional API

**SetlistGenerator workflow:**
1. Initialize with songs and history
2. Calculate recency scores for target date
3. For each moment:
   - Apply overrides if provided
   - Select songs using scoring algorithm
   - Apply energy ordering
4. Return Setlist object (with optional `label`)

**When to modify:**
- Adding new generation strategies
- Implementing batch generation
- Adding validation logic

**Example:**
```python
generator = SetlistGenerator(songs, history)
setlist = generator.generate(
    date="2026-02-15",
    overrides={"louvor": ["Oceanos"]},
    label="evening"  # Optional: creates labeled setlist
)
```

### formatter.py
**Purpose:** Output formatting

**Contents:**
- `format_setlist_markdown(setlist, songs)` - Generate markdown with chords

**When to modify:**
- Changing markdown format
- Adding new export formats (HTML, etc.)
- Customizing output templates

**Note:** For saving setlists to history, use the repository pattern: `repos.history.save(setlist)`

### pdf_formatter.py
**Purpose:** PDF generation

**Contents:**
- `generate_setlist_pdf(setlist, songs, output_path)` - Create professional PDF
- Table of contents on page 1
- Each moment on separate page with chords

**Dependencies:**
- `reportlab` library

**When to modify:**
- Changing PDF layout
- Adding new typography
- Customizing page formatting

### paths.py
**Purpose:** Path resolution utilities

**Contents:**
- `get_output_paths(base_path, cli_output_dir, cli_history_dir)` - Resolve output paths with priority
- `OutputPaths` dataclass - Container for resolved paths

**Priority order:**
1. CLI arguments
2. Environment variables
3. Config file defaults
4. Hardcoded fallbacks

**When to modify:**
- Adding new path types
- Changing priority rules
- Implementing path validation

---

## Hybrid Architecture: Functions vs Classes

### When to Use Functions

**Use functions for:**
- Stateless transformations
- Pure algorithms (deterministic output)
- Simple utilities

**Examples:**
```python
# Pure transformation (library/ordering.py)
def apply_energy_ordering(songs_in_moment, moment, songs, override_count):
    """Sort songs by energy level."""
    # No state, just transforms input to output
    pass

# Pure calculation (library/selector.py)
def calculate_recency_scores(songs, history, target_date):
    """Calculate time-based recency scores."""
    # Deterministic based on inputs
    pass

# Pure transformation (library/transposer.py)
def transpose_content(content, semitones, use_flats):
    """Transpose all chords in song content."""
    # Stateless — same inputs always produce same output
    pass

# Simple utility (library/formatter.py)
def format_date(date_str):
    """Format date for display."""
    # Stateless formatting
    pass
```

### When to Use Classes

**Use classes for:**
- Managing state
- Encapsulating complex workflows
- Providing query/command APIs

**Examples:**
```python
# Stateful generator (library/generator.py)
class SetlistGenerator:
    """Manages setlist generation with internal state."""

    def __init__(self, songs, history):
        self.songs = songs
        self.history = history
        self.recency_scores = {}  # State managed internally

    def generate(self, date, overrides=None):
        """Generate setlist (command)."""
        # Complex workflow with state
        pass
```

**Benefits of SetlistGenerator class:**
- ✓ State managed internally (recency_scores)
- ✓ Clear lifecycle (init → generate → return)
- ✓ Easy to test (mock constructor params)
- ✓ Reusable (generate multiple setlists)

---

## Algorithm Implementation Details

### Song Selection Scoring

**Location:** `library/selector.py:select_songs_for_moment()`

**Algorithm:**
```python
def select_songs_for_moment(moment, count, songs, recency_scores, already_selected, overrides):
    """Select songs for a specific moment."""

    # 1. Apply overrides (user-specified songs)
    if overrides:
        return overrides[:count]

    # 2. Build candidate pool
    candidates = []
    for song_name, song in songs.items():
        if song_name in already_selected:
            continue  # Skip already selected
        if moment not in song.tags:
            continue  # Skip songs not tagged for this moment

        weight = song.tags[moment]
        recency = recency_scores.get(song_name, 1.0)

        # Core scoring formula
        score = weight * (recency + 0.1) + random.uniform(0, 0.5)
        candidates.append((song_name, score))

    # 3. Sort by score (descending)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # 4. Take top N
    return [name for name, _ in candidates[:count]]
```

**Key insights:**
- Weight × recency creates strong preference for fresh, high-weight songs
- `+ 0.1` ensures even brand-new songs (recency=0) have some score
- Random factor prevents deterministic selection (adds variety)

### Energy Ordering Algorithm

**Location:** `library/ordering.py:apply_energy_ordering()`

**Algorithm:**
```python
def apply_energy_ordering(songs_in_moment, moment, songs, override_count):
    """Apply energy-based ordering to auto-selected songs."""

    if not ENERGY_ORDERING_ENABLED:
        return songs_in_moment

    rule = ENERGY_ORDERING_RULES.get(moment)
    if not rule:
        return songs_in_moment  # No ordering rule

    # Separate override songs from auto-selected
    override_songs = songs_in_moment[:override_count]
    auto_songs = songs_in_moment[override_count:]

    # Sort auto-selected by energy
    reverse = (rule == "descending")
    auto_songs_sorted = sorted(
        auto_songs,
        key=lambda name: songs[name].energy,
        reverse=reverse
    )

    # Preserve override order, apply ordering to auto-selected
    return override_songs + auto_songs_sorted
```

**Key insights:**
- Preserves user intent (overrides maintain exact order)
- Only reorders auto-selected songs
- Supports ascending (1→4) and descending (4→1) rules

### Recency Calculation

**Location:** `library/selector.py:calculate_recency_scores()`

**Algorithm:**
```python
def calculate_recency_scores(songs, history, target_date):
    """Calculate time-based recency scores using exponential decay."""

    recency_scores = {}
    target = datetime.strptime(target_date, "%Y-%m-%d")

    # Build last-used map (scan all history)
    last_used = {}
    for entry in history:
        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
        if entry_date >= target:
            continue  # Skip future dates

        for moment, song_list in entry["moments"].items():
            for song in song_list:
                if song not in last_used:
                    last_used[song] = entry_date

    # Calculate scores using exponential decay
    for song_name in songs:
        if song_name not in last_used:
            recency_scores[song_name] = 1.0  # Never used
        else:
            days_since = (target - last_used[song_name]).days
            decay_constant = RECENCY_DECAY_DAYS

            # Exponential decay formula
            score = 1.0 - math.exp(-days_since / decay_constant)
            recency_scores[song_name] = score

    return recency_scores
```

**Key insights:**
- Considers FULL history (not just last 3 services)
- Time-aware: 21 days ≠ 49 days
- Smooth decay curve (no sharp cutoffs)
- Score → 1.0 as time → ∞

### Replacement Logic

**Location:** `library/replacer.py`

**Key functions:**

1. **`find_target_setlist(history, target_date, target_label="")`**
   - Locates setlist by date and optional label
   - Raises ValueError if not found

2. **`derive_setlist(base_setlist_dict, songs, history, replace_count=None)`**
   - Creates a variant by replacing songs from a base setlist
   - `replace_count=None` → random number; `replace_count=0` → exact copy; integer → that many
   - Uses `replace_songs_batch()` internally with auto-selection
   - Returns new setlist dict (caller sets `label`)

3. **`validate_replacement_request(setlist, moment, position, replacement_song, songs)`**
   - Validates moment exists
   - Validates position in range
   - Validates manual song exists and has required tag
   - Raises ValueError with descriptive message

3. **`select_replacement_song(moment, setlist, position, songs, history, manual_replacement)`**
   - Auto mode: Uses `select_songs_for_moment()` with exclusion set
   - Manual mode: Validates and returns user-specified song
   - Returns: Song title (str)

4. **`replace_song_in_setlist(setlist_dict, moment, position, replacement_song, songs, reorder_energy)`**
   - Single replacement with energy reordering
   - Creates new setlist dict (immutable pattern)
   - Calls `apply_energy_ordering()` if enabled
   - Preserves `"label"` key from input dict

**Auto-selection algorithm:**
```python
# Build exclusion set: all songs EXCEPT the one being replaced
exclusion_set = set()
for m, song_list in setlist["moments"].items():
    for i, song in enumerate(song_list):
        if m == moment and i == position:
            continue  # Don't exclude replacement target
        exclusion_set.add(song)

# Select replacement (avoids duplicates)
recency_scores = calculate_recency_scores(songs, history, setlist["date"])
replacement = select_songs_for_moment(
    moment=moment,
    count=1,
    songs=songs,
    recency_scores=recency_scores,
    already_selected=exclusion_set,
    overrides=None
)[0]
```

**Key insight:** By excluding all songs EXCEPT the replacement target, the selection algorithm can "re-pick" for that position while avoiding duplicates.

---

## Reusable Components

### Core Selection Components
```python
from library import (
    get_repositories,
    calculate_recency_scores,
    select_songs_for_moment,
    apply_energy_ordering,
)

# Load data via repositories
repos = get_repositories()
songs = repos.songs.get_all()
history = repos.history.get_all()

# Calculate recency
recency_scores = calculate_recency_scores(songs, history, "2026-02-15")

# Select songs
selected = select_songs_for_moment(
    moment="louvor",
    count=4,
    songs=songs,
    recency_scores=recency_scores,
    already_selected=set(),
    overrides=None
)

# Apply ordering
ordered = apply_energy_ordering(selected, "louvor", songs, override_count=0)
```

### Generation Components
```python
from library import SetlistGenerator, get_repositories

# Using repositories (recommended)
repos = get_repositories()
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
setlist = generator.generate(date="2026-02-15")
labeled = generator.generate(date="2026-02-15", label="evening")

# Or direct initialization
generator = SetlistGenerator(songs_dict, history_list)
setlist = generator.generate(date="2026-02-15")
```

### Derivation Components
```python
from library import derive_setlist, get_repositories

repos = get_repositories()
songs = repos.songs.get_all()
history = repos.history.get_all()
base = repos.history.get_by_date("2026-03-01")

# Derive with random N replacements
derived = derive_setlist(base, songs, history)

# Derive with exact count
derived = derive_setlist(base, songs, history, replace_count=3)

# Derive with zero changes (exact copy)
derived = derive_setlist(base, songs, history, replace_count=0)
```

### Transposition Components
```python
from library import transpose_content, calculate_semitones, should_use_flats, resolve_target_key

# Transpose a song from Bm to G (auto-resolves to Gm)
effective_key = resolve_target_key("Bm", "G")  # "Gm"
semitones = calculate_semitones("Bm", effective_key)  # 8
use_flats = should_use_flats(effective_key)  # True

transposed = transpose_content(song.content, semitones, use_flats)
```

### Formatting Components
```python
from library import get_repositories, format_setlist_markdown, generate_setlist_pdf
from pathlib import Path

repos = get_repositories()
songs = repos.songs.get_all()

# Generate markdown
markdown = format_setlist_markdown(setlist, songs)
output_path = Path("output/2026-02-15.md")
output_path.write_text(markdown)

# Save history via repository
repos.history.save(setlist)

# Generate PDF
pdf_path = Path("output/2026-02-15.pdf")
generate_setlist_pdf(setlist, songs, pdf_path)
```

---

## Error Handling Patterns

### Validation with Descriptive Errors
```python
def validate_replacement_request(setlist, moment, position, replacement_song, songs):
    """Validate replacement request, raise ValueError with clear message."""

    # Validate moment
    if moment not in MOMENTS_CONFIG:
        valid_moments = ", ".join(MOMENTS_CONFIG.keys())
        raise ValueError(
            f"Invalid moment '{moment}'. "
            f"Valid moments: {valid_moments}"
        )

    # Validate position
    moment_songs = setlist["moments"].get(moment, [])
    if position < 0 or position >= len(moment_songs):
        raise ValueError(
            f"Invalid position {position + 1} for moment '{moment}'. "
            f"Valid range: 1-{len(moment_songs)}"
        )

    # Validate manual song
    if replacement_song:
        if replacement_song not in songs:
            raise ValueError(f"Song '{replacement_song}' not found in database")

        if moment not in songs[replacement_song].tags:
            raise ValueError(
                f"Song '{replacement_song}' is not tagged for moment '{moment}'"
            )
```

**Pattern:** Clear, actionable error messages with context

### Graceful Fallbacks
```python
def calculate_recency_scores(songs, history, target_date):
    """Calculate recency scores with fallback for never-used songs."""

    recency_scores = {}
    for song_name in songs:
        if song_name not in last_used:
            recency_scores[song_name] = 1.0  # Fallback: treat as never used
        else:
            # ... calculate decay
            pass

    return recency_scores
```

**Pattern:** Default to safe values when data is missing

### Immutable Data Patterns
```python
def replace_song_in_setlist(setlist_dict, moment, position, replacement_song, songs, reorder_energy):
    """Replace song, return NEW setlist dict (immutable)."""

    # Create new dict (don't mutate input)
    new_setlist = {
        "date": setlist_dict["date"],
        "moments": {
            m: list(songs)  # Copy lists
            for m, songs in setlist_dict["moments"].items()
        }
    }

    # Modify copy
    new_setlist["moments"][moment][position] = replacement_song

    # Apply ordering (returns new list)
    if reorder_energy:
        new_setlist["moments"][moment] = apply_energy_ordering(
            new_setlist["moments"][moment],
            moment,
            songs,
            override_count=0
        )

    return new_setlist  # Return new object
```

**Pattern:** Create new objects instead of mutating inputs

---

## Testing Patterns

### Unit Testing Functions
```python
def test_recency_calculation():
    """Test time-based recency calculation."""
    songs = {"Oceanos": Song(...)}
    history = [
        {"date": "2026-01-01", "moments": {"louvor": ["Oceanos"]}}
    ]

    scores = calculate_recency_scores(songs, history, "2026-02-15")

    # 45 days later (decay constant)
    assert 0.6 < scores["Oceanos"] < 0.7  # ~0.63 expected
```

### Unit Testing Classes
```python
def test_setlist_generator():
    """Test SetlistGenerator class."""
    songs = load_test_songs()
    history = load_test_history()

    generator = SetlistGenerator(songs, history)
    setlist = generator.generate(date="2026-02-15")

    assert setlist.date == "2026-02-15"
    assert len(setlist.moments["louvor"]) == 4
```

### Integration Testing
```bash
# Test full workflow
songbook generate --date 2026-02-15 --no-save
songbook view-setlist --date 2026-02-15

# Verify output files created
test -f output/2026-02-15.md
```

---

## Performance Considerations

### Lazy Loading
Songs are loaded lazily:
- Database parsed once on startup
- Chord content loaded only when needed (for output)

### Caching Opportunities
```python
# Cache recency scores for batch operations
generator = SetlistGenerator(songs, history)
generator._calculate_recency_scores("2026-02-15")  # Cached

# Generate multiple setlists (reuses cache)
setlist1 = generator.generate(date="2026-02-15")
setlist2 = generator.generate(date="2026-02-15", overrides={...})
```

### Algorithm Complexity
- Song selection: O(n) where n = songs tagged for moment
- Energy ordering: O(m log m) where m = songs in moment
- Recency calculation: O(h × s) where h = history size, s = songs per service

**Optimization opportunities:**
- Index songs by moment tag (O(1) lookup instead of O(n) filter)
- Cache last-used dates (avoid re-scanning history)
- Use binary search for date-based history queries

---

## Extending the System

### Adding New Selection Strategies
```python
# Create new selector function
def select_by_popularity(moment, count, songs, play_counts, already_selected):
    """Select most popular songs."""
    candidates = [
        (name, play_counts.get(name, 0))
        for name, song in songs.items()
        if moment in song.tags and name not in already_selected
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in candidates[:count]]

# Integrate into generator
class PopularityGenerator(SetlistGenerator):
    def _select_for_moment(self, moment, count):
        return select_by_popularity(
            moment, count, self.songs, self.play_counts, self.already_selected
        )
```

### Adding New Output Formats
```python
# Create new formatter
def format_setlist_html(setlist, songs):
    """Generate HTML output."""
    html = "<html><body>"
    for moment, song_list in setlist.moments.items():
        html += f"<h2>{moment}</h2><ul>"
        for song_name in song_list:
            html += f"<li>{song_name}</li>"
        html += "</ul>"
    html += "</body></html>"
    return html

# Register in CLI
@click.command()
def export_html():
    """Export setlist as HTML."""
    repos = get_repositories()
    songs = repos.songs.get_all()
    latest = repos.history.get_latest()
    html = format_setlist_html(latest, songs)
    Path("output/latest.html").write_text(html)
```

### Adding New Data Sources
```python
# Create new loader
def load_songs_from_api(api_url):
    """Load songs from REST API."""
    response = requests.get(api_url)
    data = response.json()

    songs = {}
    for item in data["songs"]:
        songs[item["name"]] = Song(
            name=item["name"],
            key=item["key"],
            tags=parse_tags(item["tags"]),
            energy=item["energy"],
            chords=item["chords"]
        )
    return songs

# Use in generator
songs = load_songs_from_api("https://api.example.com/songs")
generator = SetlistGenerator(songs, history)
```