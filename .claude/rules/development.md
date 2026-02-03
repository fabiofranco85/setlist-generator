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
- `Setlist` dataclass - Represents a generated setlist with date and moments

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
```

### loader.py
**Purpose:** Data loading from files

**Contents:**
- `load_songs(base_path)` - Load songs from database.csv and chords/*.md
- `load_history(history_dir)` - Load historical setlists from JSON
- `parse_tags(tag_string)` - Parse tag format (e.g., "louvor(5),prelúdio")

**When to modify:**
- Changing database format
- Adding new data sources
- Optimizing load performance

**Implementation notes:**
- Uses CSV for database (semicolon-separated)
- Uses JSON for history (one file per date)
- Lazy loads chords content (only when needed)

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
4. Return Setlist object

**When to modify:**
- Adding new generation strategies
- Implementing batch generation
- Adding validation logic

**Example:**
```python
generator = SetlistGenerator(songs, history)
setlist = generator.generate(
    date="2026-02-15",
    overrides={"louvor": ["Oceanos"]}
)
```

### formatter.py
**Purpose:** Output formatting

**Contents:**
- `format_setlist_markdown(setlist, songs)` - Generate markdown with chords
- `save_setlist_history(setlist, history_dir)` - Save JSON history
- `format_date(date_str)` - Format date for display

**When to modify:**
- Changing markdown format
- Adding new export formats (HTML, etc.)
- Customizing output templates

**Implementation notes:**
- Markdown includes full chord notation
- JSON history only stores song titles (lightweight)
- Date formatting uses locale-aware formatting

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

1. **`find_target_setlist(history, target_date)`**
   - Locates setlist by date (latest or specific)
   - Raises ValueError if not found

2. **`validate_replacement_request(setlist, moment, position, replacement_song, songs)`**
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
    load_songs,
    load_history,
    calculate_recency_scores,
    select_songs_for_moment,
    apply_energy_ordering,
)

# Load data
songs = load_songs(Path("."))
history = load_history(Path("./history"))

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
from library import SetlistGenerator

# Object-oriented API
generator = SetlistGenerator(songs, history)
setlist = generator.generate(date="2026-02-15")

# OR functional API (backward compatible)
from library import generate_setlist
setlist = generate_setlist(songs, history, date="2026-02-15")
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
from library import format_setlist_markdown, save_setlist_history

# Generate markdown
markdown = format_setlist_markdown(setlist, songs)
output_path = Path("output/2026-02-15.md")
output_path.write_text(markdown)

# Save history
save_setlist_history(setlist, Path("./history"))

# Generate PDF
from library import generate_setlist_pdf
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
    setlist = load_latest_setlist()
    songs = load_songs(Path("."))
    html = format_setlist_html(setlist, songs)
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