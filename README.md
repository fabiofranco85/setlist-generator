# Church Worship Setlist Generator

An intelligent setlist generator for church worship services that automatically selects songs based on service structure, song preferences, and performance history.

## 🎵 Features

- **Smart Song Selection**: Automatically picks songs based on configurable weights and preferences
- **Event Types**: Different service formats (main, youth, Christmas) with independent moment configs and song pools
- **Energy-Based Sequencing**: Creates emotional arcs by ordering songs from upbeat to contemplative worship
- **Variety Guaranteed**: Tracks song history and avoids repeating songs too frequently
- **Service Structure**: Organizes songs into worship moments (prelúdio, louvor, ofertório, etc.)
- **Manual Overrides**: Force specific songs when needed while letting the system fill the rest
- **Full Chord Sheets**: Generates complete setlists with chords and lyrics for musicians
- **Chord Transposition**: Transpose any song to a different key with preview and save modes
- **History Tracking**: Maintains a database of past setlists for long-term variety

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Commands](#cli-commands)
- [How It Works](#how-it-works)
- [Event Types](#event-types)
- [Managing Songs](#managing-songs)
- [Configuration](#configuration)
- [Storage Backends](#storage-backends)
- [Programmatic Usage](#programmatic-usage)
- [Output Files](#output-files)
- [Notes](#-notes)

## Installation

### Requirements

- Python 3.12 or higher
- Package manager: [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Quick Setup (Recommended - Using uv)

1. **Clone or download this repository**

2. **Ensure Python 3.12+ is installed:**
   ```bash
   python --version  # Should show 3.12 or higher
   ```

3. **Install everything in one command:**
   ```bash
   uv sync
   ```

   This single command:
   - ✓ Reads dependencies from `pyproject.toml`
   - ✓ Creates/updates `uv.lock` for reproducible installs
   - ✓ Installs all dependencies
   - ✓ Installs the songbook package in editable mode
   - ✓ Creates an isolated virtual environment

   For PostgreSQL backend support, add `--group postgres` (see [Storage Backends](./STORAGE_BACKENDS.md)).

That's it! The `songbook` command is now available.

### Alternative Setup (Using pip)

If you prefer pip or don't have uv installed:

```bash
# Install the package and its dependencies
pip install -e .
```

This reads `pyproject.toml` and installs everything needed.

### Installing uv (Optional)

If you don't have uv yet and want to use it:

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

### For Developers: Adding New Dependencies

If you're contributing to the project and need to add dependencies:

```bash
# Add a runtime dependency
uv add package-name

# Add a development dependency
uv add --dev pytest black ruff
```

This automatically updates both `pyproject.toml` and `uv.lock`.

## Quick Start

Generate a setlist for today:

```bash
songbook generate
```

This will:
1. Load all songs from the configured [storage backend](#storage-backends) (default: `database.csv` + `chords/`)
2. Analyze **all historical setlists** to calculate time-based recency scores
3. Generate a new setlist with songs for each service moment
4. Save the output to `output/YYYY-MM-DD.md` (markdown with chords)
5. Save history for recency tracking

For a full list of commands and usage examples, see the **[CLI Command Reference](./CLI_GUIDE.md)**.

## CLI Commands

For complete documentation of all CLI commands, options, and examples, see:

**📖 [CLI Command Reference (CLI_GUIDE.md)](./CLI_GUIDE.md)**

The CLI guide covers:
- All commands in detail (`generate`, `view-setlist`, `view-song`, `replace`, `label`, `info`, `transpose`, etc.)
- Command options and flags
- Usage examples and workflows
- Shell completion setup
- Data maintenance commands
- Troubleshooting tips

## How It Works

### Service Moments

Each worship service is divided into moments, and the generator picks songs for each:

| Moment    | Songs | Purpose                          |
|-----------|-------|----------------------------------|
| Prelúdio  | 1     | Opening/introductory worship     |
| Ofertório | 1     | During offering collection       |
| Saudação  | 1     | Greeting/welcome                 |
| Crianças  | 1     | Children's ministry              |
| Louvor    | 4     | Main worship block               |
| Poslúdio  | 1     | Closing/sending song             |

**Total: 9 songs per service**

### Song Selection Algorithm

The system uses a **two-phase approach**:

#### Phase 1: Selection (Score-Based)

The system picks songs using a smart scoring algorithm:

1. **Tag Weights**: Songs can have preference weights (1-10) for each moment
   - Example: A powerful worship song might have `louvor(5)` → higher chance of selection
   - Default weight is 3 if not specified

2. **Time-Based Recency**: Songs used recently are penalized based on actual days elapsed
   - Used 7 days ago → heavily penalized (score: 0.14)
   - Used 30 days ago → moderately penalized (score: 0.49)
   - Used 60 days ago → lightly penalized (score: 0.74)
   - Used 90+ days ago → almost no penalty (score: 0.86+)
   - **Considers full history**, not just recent services

3. **Randomization**: Adds variety to prevent the exact same order each time

**Formula**: `score = weight × (recency + 0.1) + random(0, 0.5)`

#### Phase 2: Ordering (Energy-Based)

After selecting songs, the system orders them by energy level to create emotional arcs:

- **Energy Scale**: Each song has an energy value (1-4)
  - **1** = High energy, upbeat, celebratory
  - **2** = Moderate-high, engaging, rhythmic
  - **3** = Moderate-low, reflective, slower
  - **4** = Deep worship, contemplative, intimate

- **Louvor Progression**: Songs are ordered 1→4 (upbeat to worship)
  - Example: Santo de Deus (1) → Hosana (3) → Perfeito Amor (3) → Lugar Secreto (4)

- **Override Preservation**: Manually specified songs maintain your exact order

### Example Selection

For the "louvor" moment, if we have:
- **Oceanos**: weight=5, last used 3 services ago → high score
- **Santo Pra Sempre**: weight=4, used last service → low score
- **A Casa é Sua**: weight=3, never used → medium-high score

The generator will likely pick: Oceanos, A Casa é Sua, and two other high-scoring songs.

## Event Types

Event types let you run different service formats (e.g., main Sunday service, youth service, Christmas celebration) with independent moment configurations and song pools.

For CLI commands to create and manage event types, see the **[CLI Command Reference](./CLI_GUIDE.md#event-type---manage-event-types)**.

### How It Works

- **Default event type** (`main`): Uses the global `MOMENTS_CONFIG`. With the filesystem backend, data is stored at the root level (e.g., `history/` and `output/`).
- **Non-default types** (e.g., `youth`): Have their own moments config. Data is stored under the event type name (e.g., `history/youth/` and `output/youth/` with the filesystem backend).
- **Song binding**: By default, all songs are available for all event types. You can restrict songs to specific types by adding an `event_types` column to `database.csv`.
- **Global recency**: Song recency is computed across ALL event types, so a song used in the youth service affects its freshness for the main service too.
- **Labels still work**: Event type and label are orthogonal — you can combine them.

### Binding Songs to Event Types

To restrict a song to specific event types, add an `event_types` column to `database.csv`:

```csv
song;energy;tags;youtube;event_types
Youth Song;1;louvor(4);;youth
Christmas Carol;3;louvor(5);;christmas
General Song;2;louvor(3);;
```

- Empty `event_types` = song available for all types (unbound)
- `event_types=youth` = only available for youth type
- `event_types=youth,christmas` = available for both

## Managing Songs

### Song Database: `database.csv`

This file maps songs to service moments with energy levels and optional weights.

**Format**: `song;energy;tags;youtube`

The `youtube` column is optional — rows without a YouTube URL simply omit the fourth field.

#### Basic Format with Energy

```csv
song;energy;tags;youtube
Santo de Deus;1;louvor
Hosana;3;louvor
Perfeito Amor;3;louvor
Lugar Secreto;4;louvor
Fico Feliz;1;crianças
Tributo a Jehovah;2;ofertório
```

**Energy column (1-4 scale):**
- **1**: High energy, upbeat, celebratory (e.g., Eu Te Busco, Santo de Deus)
- **2**: Moderate-high, engaging, rhythmic (e.g., Grande É o Senhor)
- **3**: Moderate-low, reflective, slower (e.g., Perfeito Amor, Consagração)
- **4**: Deep worship, contemplative, intimate (e.g., Lugar Secreto, Tudo é Perda)

#### Weighted Tags

Add `(weight)` after a moment to increase selection probability (1-10 scale):

```csv
song;energy;tags;youtube
Oceanos;3;louvor(5)           # High weight, moderate-low energy
Santo Pra Sempre;4;louvor(4)  # Medium-high weight, deep worship energy
Lugar Secreto;4;louvor(3)     # Default weight, deep worship energy
```

**Weight Guidelines:**
- `1-2`: Use sparingly (new songs, seasonal)
- `3`: Default (most songs)
- `4-5`: Congregation favorites
- `6-7`: Exceptional songs (use rarely)
- `8-10`: Reserved for special occasions

#### Multiple Moments

Songs can work in different moments with different weights:

```csv
song;energy;tags;youtube
Autoridade e Poder;1;prelúdio,poslúdio
Brilha Jesus;2;saudação(4),poslúdio(2)
Estamos de Pé;1;prelúdio(5),poslúdio(3)
```

This means:
- "Autoridade e Poder" (energy 1) can be used as prelúdio OR poslúdio (weight 3 for both)
- "Brilha Jesus" (energy 2) works great for saudação (weight 4) or okay for poslúdio (weight 2)

### Song Energy Levels

Each song has an **intrinsic energy level** (1-4) that defines its musical character and helps create emotional arcs during worship.

#### Energy Scale Definitions

| Energy | Musical Character | Tempo | Examples |
|--------|------------------|-------|----------|
| **1** | High energy, upbeat, celebratory | Fast | Eu Te Busco, Santo de Deus |
| **2** | Moderate-high, engaging, rhythmic | Medium-fast | Grande É o Senhor |
| **3** | Moderate-low, reflective, thoughtful | Medium-slow | Hosana, Oceanos, Perfeito Amor |
| **4** | Deep worship, contemplative, intimate | Slow | Lugar Secreto, Santo Pra Sempre, Tudo é Perda |

#### How Energy Affects Setlists

**For multi-song moments (louvor - 4 songs):**
- Songs are automatically ordered by energy: **1 → 2 → 3 → 4**
- This creates a natural emotional arc from celebration to intimacy
- Example progression:
  1. Santo de Deus (energy 1) - upbeat celebration
  2. Hosana (energy 3) - reflective
  3. Perfeito Amor (energy 3) - reflective
  4. Lugar Secreto (energy 4) - deep, intimate worship

**Override behavior:**
- If you manually specify songs using `--override`, your order is preserved
- Only auto-selected songs are ordered by energy
- Example: `--override "louvor:Lugar Secreto,Hosana"` keeps them in that exact order

**Default for missing energy:**
- Songs without energy values default to 2.5 (neutral/middle)
- This maintains backward compatibility with older song entries

#### Choosing Energy Levels

When adding new songs, classify them by these characteristics:

**Energy 1 (Upbeat):**
- ✓ Fast tempo, driving rhythm
- ✓ Celebratory, joyful lyrics
- ✓ High intensity instrumentation
- ✓ Congregation movement/clapping songs

**Energy 2 (Moderate-High):**
- ✓ Moderate tempo, steady rhythm
- ✓ Engaging but not frantic
- ✓ Good balance of energy and reflection
- ✓ Most "standard" worship songs

**Energy 3 (Reflective):**
- ✓ Slower tempo
- ✓ Thoughtful, meditative lyrics
- ✓ Softer instrumentation
- ✓ Transitioning from engagement to intimacy

**Energy 4 (Deep Worship):**
- ✓ Very slow, gentle tempo
- ✓ Intimate, personal lyrics
- ✓ Minimal instrumentation
- ✓ Prayer-like, contemplative atmosphere

### Song Files: `chords/*.md`

Each song has a markdown file with chords and lyrics.

**File naming**: Must exactly match the song name in `database.csv`
- `database.csv`: `Oceanos;2;louvor`
- File: `chords/Oceanos.md`

**Format**:

```markdown
### Song Title (Key)

[Chord notation with lyrics]
```

**Example** (`chords/Oceanos.md`):

```markdown
### Oceanos (Bm)

Bm                   A/C#    D
   Tua voz me chama sobre as águas
         A              G
Onde os meus pés podem falhar

[Refrão]

G         D       A
  Ao Teu nome clamarei
G            D        A
  E além das ondas olharei
```

### Adding a New Song

1. **Classify the song's energy** (1-4):
   - Listen to the song and assess its tempo, intensity, and mood
   - Use the energy scale guide above
   - When in doubt, use 2 or 3 (moderate energy)

2. **Add to `database.csv`** with energy, tags, and optional YouTube URL:
   ```csv
   Nova Canção;2;louvor(3),prelúdio;https://youtu.be/VIDEO_ID
   ```
   - Format: `song_name;energy;tags;youtube`
   - Energy: 1 (upbeat) to 4 (contemplative)
   - Tags: Moments with optional weights
   - YouTube: Optional video URL (omit if not available)

3. **Create chord file** `chords/Nova Canção.md`:
   ```markdown
   ### Nova Canção (G)

   G              D
   Letra da música...
   ```

4. **Run generator** - the song is now in the pool!

**Example additions:**

```csv
# High-energy praise song
Celebração;1;louvor(4),prelúdio(3)

# Moderate worship song
Rendição;2;louvor(3)

# Reflective song
Silêncio;3;louvor(3),ofertório(2)

# Deep worship ballad
Intimidade;4;louvor(5)
```

### Removing a Song

1. Delete or comment out the line in `database.csv`:
   ```csv
   # Old Song;2;louvor  ← This song won't be selected anymore
   ```

2. Optionally delete `chords/Old Song.md`

### Updating Song Tags/Weights

Edit `database.csv`:

```csv
# Before
Oceanos;2;louvor(3)

# After - increase weight because congregation loves it
Oceanos;2;louvor(5)
```

Changes take effect immediately on the next generation.

## Configuration

Advanced users can modify the generator's behavior through various configuration methods.

### Output Paths

The generator supports flexible output path configuration with the following priority (highest to lowest):

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

**3. Configuration File:**
Edit `library/config.py`:
```python
DEFAULT_OUTPUT_DIR = "output"    # Markdown and PDF files
DEFAULT_HISTORY_DIR = "history"  # JSON tracking
```

**4. Defaults:**
If no configuration is provided:
- Markdown and PDF files → `output/`
- JSON history → `history/`

**Examples:**
```bash
# Use defaults (output/ and history/)
songbook generate

# Custom directories via CLI
songbook generate --output-dir /mnt/setlists --history-dir /mnt/tracking

# Custom directories via environment
export SETLIST_OUTPUT_DIR=$HOME/worship/output
export SETLIST_HISTORY_DIR=$HOME/worship/history
songbook generate
```

### Change Songs Per Moment

Edit `MOMENTS_CONFIG` in `library/config.py`:

```python
MOMENTS_CONFIG = {
    "prelúdio": 1,
    "ofertório": 1,
    "saudação": 1,
    "crianças": 1,
    "louvor": 4,      # Change to 5 for longer worship
    "poslúdio": 1,
}
```

### Energy-Based Ordering

Edit energy configuration in `library/config.py`:

```python
# Enable/disable energy ordering
ENERGY_ORDERING_ENABLED = True  # Set to False to disable

# Configure ordering rules per moment
ENERGY_ORDERING_RULES = {
    "louvor": "ascending",  # 1→4 (upbeat to worship)
    # Add more moments as needed:
    # "ofertório": "descending",  # 4→1 (worship to upbeat)
}

# Default energy for songs without energy value
DEFAULT_ENERGY = 2.5  # Neutral/middle energy
```

**Options:**
- `ENERGY_ORDERING_ENABLED`: Toggle energy ordering on/off
- `"ascending"`: Low to high energy (1→4) - upbeat to contemplative
- `"descending"`: High to low energy (4→1) - contemplative to upbeat
- `DEFAULT_ENERGY`: Fallback for songs missing energy values (2.5 = neutral)

### Change Recency Decay Rate

Edit `RECENCY_DECAY_DAYS` in `library/config.py`:

```python
RECENCY_DECAY_DAYS = 45  # Days for a song to feel "fresh" again
```

**Tuning options:**
- `30` = Faster cycling (songs fresh after 1 month)
- `45` = Balanced (default - songs fresh after 1.5 months)
- `60` = Slower cycling (songs fresh after 2 months)
- `90` = Maximum variety (songs fresh after 3 months)

**How it works:** The system uses exponential decay based on actual days elapsed since last use, considering the **full history** of all services. See [`RECENCY_SYSTEM.md`](./RECENCY_SYSTEM.md) for details.

### Change Default Weight

Edit `DEFAULT_WEIGHT` in `library/config.py`:

```python
DEFAULT_WEIGHT = 3  # Default weight when not specified in tags
```

### Add New Moments

1. Add to `MOMENTS_CONFIG`:
   ```python
   MOMENTS_CONFIG = {
       # ... existing moments ...
       "meditação": 1,  # New moment
   }
   ```

2. Add songs with the new tag in `database.csv`:
   ```csv
   Lugar Secreto;4;meditação
   ```

## Storage Backends

By default, the generator stores all data as local files (CSV, JSON, markdown). For team or server deployments, a **PostgreSQL backend** is available.

| Backend | Data Storage | Best For |
|---------|-------------|----------|
| `filesystem` (default) | CSV + JSON + `.md` files | Local use, single user |
| `postgres` | PostgreSQL database | Teams, servers, web apps |

**Quick setup (PostgreSQL):**

```bash
uv sync --group postgres
psql $DATABASE_URL -f scripts/schema.sql
python scripts/migrate_to_postgres.py --database-url $DATABASE_URL
STORAGE_BACKEND=postgres DATABASE_URL=... songbook generate
```

For complete setup instructions, see **[Storage Backends Guide (STORAGE_BACKENDS.md)](./STORAGE_BACKENDS.md)**.

## Programmatic Usage

The setlist generator can be used as a Python library in your own scripts, allowing you to integrate setlist generation into custom workflows, web applications, or automation tools.

### Using the Repository Pattern (Recommended)

The repository pattern provides a clean abstraction for data access, enabling backend flexibility (see [Storage Backends](./STORAGE_BACKENDS.md)):

```python
from library import get_repositories, SetlistGenerator

# Get repositories (uses STORAGE_BACKEND env var, default: filesystem)
repos = get_repositories()

# Create generator from repositories
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)

# Generate setlist
setlist = generator.generate(
    date="2026-03-15",
    overrides={"louvor": ["Oceanos", "Santo Pra Sempre"]}
)

# Access results
print(f"Setlist for {setlist.date}:")
for moment, song_list in setlist.moments.items():
    print(f"\n{moment.upper()}:")
    for song in song_list:
        print(f"  - {song}")

# Save through repositories
repos.history.save(setlist)

# Generate multiple setlists with same instance
setlist2 = generator.generate("2026-03-22")
setlist3 = generator.generate("2026-03-29")
```

**Benefits:**
- ✓ Backend-agnostic (swap filesystem for database without code changes)
- ✓ State managed internally (recency scores calculated once)
- ✓ Reusable (generate multiple setlists efficiently)
- ✓ Easy to test and extend

**Repository methods:**
- `repos.songs.get_all()` - Get all songs
- `repos.songs.get_by_title(title)` - Get single song
- `repos.songs.search(query)` - Search by title
- `repos.history.get_all()` - Get all history (most recent first, all event types)
- `repos.history.get_by_date(date, label="", event_type="")` - Get specific setlist
- `repos.history.get_by_date_all(date)` - Get all setlists for a date (all labels/types)
- `repos.history.save(setlist)` - Save new setlist (routes by event_type)
- `repos.history.exists(date, label="", event_type="")` - Check if setlist exists
- `repos.history.delete(date, label="", event_type="")` - Delete a setlist
- `repos.config.get_moments_config()` - Get service moments
- `repos.output.save_markdown(date, content, label="", event_type="")` - Save markdown
- `repos.output.delete_outputs(date, label="", event_type="")` - Delete md + pdf files
- `repos.event_types.get_all()` - Get all event types
- `repos.event_types.get(slug)` - Get event type by slug
- `repos.event_types.add(event_type)` - Add new event type

### Custom Formatting and Saving

```python
from library import get_repositories, SetlistGenerator, format_setlist_markdown
from pathlib import Path

# Get repositories and generate setlist
repos = get_repositories()
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
setlist = generator.generate("2026-03-15")

# Format as markdown
songs = repos.songs.get_all()
markdown = format_setlist_markdown(setlist, songs)

# Save to custom location
output_path = Path("~/Desktop/next-service.md").expanduser()
with open(output_path, "w", encoding="utf-8") as f:
    f.write(markdown)

# Save to history through repository
repos.history.save(setlist)

# Or use the output repository for standard locations
repos.output.save_markdown(setlist.date, markdown)
```

### Batch Generation

Generate multiple setlists programmatically:

```python
from library import get_repositories, SetlistGenerator
from datetime import datetime, timedelta

repos = get_repositories()
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)

# Generate setlists for next 4 Sundays
start_date = datetime(2026, 3, 1)
for i in range(4):
    service_date = start_date + timedelta(weeks=i)
    date_str = service_date.strftime("%Y-%m-%d")

    setlist = generator.generate(date_str)
    print(f"\n{date_str}: {sum(len(songs) for songs in setlist.moments.values())} songs")
```

### Integration Example: Web API

```python
from flask import Flask, jsonify
from library import get_repositories, SetlistGenerator

app = Flask(__name__)

# Initialize once at startup
repos = get_repositories()
generator = SetlistGenerator.from_repositories(repos.songs, repos.history)

@app.route('/generate/<date>')
def generate_setlist_api(date):
    setlist = generator.generate(date)
    return jsonify({
        "date": setlist.date,
        "moments": setlist.moments,
        "total_songs": sum(len(s) for s in setlist.moments.values())
    })

@app.route('/songs')
def list_songs():
    songs = repos.songs.get_all()
    return jsonify([{"title": s.title, "energy": s.energy} for s in songs.values()])

if __name__ == '__main__':
    app.run(debug=True)
```

## Output Files

Files use `YYYY-MM-DD` for unlabeled setlists and `YYYY-MM-DD_label` for labeled ones (e.g., `2026-03-01_evening.md`).

### Markdown Setlist (`output/YYYY-MM-DD[_label].md`)

Human-readable setlist with full chords and lyrics for musicians.

### PDF Setlist (`output/YYYY-MM-DD[_label].pdf`)

Professional PDF setlist for print or digital use (generated with `--pdf` flag).

**Page 1 - Table of Contents:**
- Large "Setlist" title
- Portuguese date (e.g., "Domingo, 25 de Janeiro de 2026")
- Complete song list organized by service moments
- Song keys and page numbers for quick navigation

**Content Pages:**
- Each service moment starts on a new page
- Moment name as header (Prelúdio, Oferta, Comunhão, etc.)
- Song title with musical key
- Full chord notation in monospace font (Courier)
- Clean, professional typography

**Moment Name Mapping:**
The PDF uses church-specific terminology:
- `prelúdio` → "Prelúdio"
- `ofertório` → "Oferta"
- `saudação` → "Comunhão"
- `crianças` → "Crianças"
- `louvor` → "Louvor"
- `poslúdio` → "Poslúdio"

### Markdown Setlist (Detailed)

**Structure** (unlabeled):
```markdown
# Setlist - 2026-02-15

## Prelúdio

### Estamos de Pé (G)

G              D
Estamos de pé...

---

## Louvor

### Oceanos (Bm)
...
```

**Labeled setlists** include the label in the header:
```markdown
# Setlist - 2026-03-01 (evening)
```

**Use cases**:
- Print for musicians
- Display on tablet/screen during rehearsal
- Share via email/WhatsApp

### History File (`history/YYYY-MM-DD[_label].json`)

Machine-readable format for tracking which songs were used.

**Structure** (unlabeled):
```json
{
  "date": "2026-02-15",
  "moments": {
    "prelúdio": ["Estamos de Pé"],
    "ofertório": ["Tributo a Jehovah"],
    "saudação": ["Rio de Vida"],
    "crianças": ["Fico Feliz"],
    "louvor": ["Oceanos", "Santo Pra Sempre", "Hosana", "Creio que Tu És a Cura"],
    "poslúdio": ["Autoridade e Poder"]
  }
}
```

**Labeled setlists** include the `"label"` key:
```json
{
  "date": "2026-03-01",
  "label": "evening",
  "moments": { ... }
}
```

**Purpose**: The generator reads this history to avoid repeating songs too soon. Both labeled and unlabeled setlists contribute to recency scoring. With the filesystem backend, history is stored as JSON files; with PostgreSQL, it's stored in the `setlists` table.

For usage examples, common workflows, and troubleshooting, see the **[CLI Command Reference](./CLI_GUIDE.md#examples-and-workflows)**.

## 📝 Notes

### Song Naming Conventions

- Use exact titles as they appear on official recordings
- Include accents: "Te agradeço" not "Te agradeco"
- Be consistent: Once you name a song, use that exact spelling everywhere

### Energy & Weight Strategy

**Energy classification** (rarely changes):
- Classify songs by their intrinsic musical character
- Energy values typically don't change over time
- If reclassifying, test the worship flow with `--no-save` first

**Weight strategy** (adjust frequently):
- Start conservative with weights (mostly 3s)
- Adjust based on congregation familiarity and response

```csv
# Initial setup - classify energy, use default weights
Oceanos;3;louvor
Santo Pra Sempre;4;louvor
Hosana;3;louvor
Lugar Secreto;4;louvor

# After a few months - adjust weights based on congregation response
Oceanos;3;louvor(5)         # Everyone loves this (energy unchanged)
Santo Pra Sempre;4;louvor(4)  # Popular (energy unchanged)
Hosana;3;louvor(2)         # Less familiar, use less often (energy unchanged)
Lugar Secreto;4;louvor(5)    # Powerful worship moment (energy unchanged)
```

**Remember:**
- **Energy** = What the song **is** (musical character)
- **Weight** = How often we **want** it (selection preference)

### History Management

The system automatically manages setlist history for accurate variety tracking.

**Filesystem backend:** History is stored in `history/*.json`. To reset:
```bash
# Backup first
cp -r history history_backup

# Clear history
rm history/*.json
```

**PostgreSQL backend:** History is stored in the `setlists` table. To reset:
```bash
psql $DATABASE_URL -c "DELETE FROM setlists"
```

### Seasonal Weight Adjustments

For the Christmas season, increase weights on Christmas songs:

```csv
# Before
Noite de Paz;4;louvor,prelúdio

# During December (increase weight, keep energy)
Noite de Paz;4;louvor(7),prelúdio(6)

# After Christmas, reduce weight again
Noite de Paz;4;louvor(2),prelúdio(2)
```

Energy levels (column 2) typically stay the same as they reflect the song's intrinsic character, not seasonal preference. Adjust weights (in tags) to change selection frequency.

### Testing New Songs

Add new songs with low weights initially, then increase as the congregation learns them:

```csv
# New song - start low
New Song;1;louvor(1)  # Energy 1 (upbeat), weight 1 (rarely selected)

# Congregation knows it - normal weight
New Song;1;louvor(3)  # Energy stays 1, weight now 3

# Becomes a favorite - high weight
New Song;1;louvor(5)  # Energy still 1, weight now 5
```

**Key principle**: Energy (column 2) defines the song's character and rarely changes. Weight (in tags) controls selection frequency and can be adjusted based on congregation familiarity.

## Support

For issues or questions:
1. Check the [CLI Troubleshooting guide](./CLI_GUIDE.md#troubleshooting)
2. Review this README's configuration and song management sections
3. Check the generated output files for clues

## License

This tool is provided as-is for church worship planning purposes.

---

**Made with ❤️ for worship teams**
