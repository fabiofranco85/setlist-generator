# Church Worship Setlist Generator

An intelligent setlist generator for church worship services that automatically selects songs based on service structure, song preferences, and performance history.

## 🎵 Features

- **Smart Song Selection**: Automatically picks songs based on configurable weights and preferences
- **Energy-Based Sequencing**: Creates emotional arcs by ordering songs from upbeat to contemplative worship
- **Variety Guaranteed**: Tracks song history and avoids repeating songs too frequently
- **Service Structure**: Organizes songs into worship moments (prelúdio, louvor, ofertório, etc.)
- **Manual Overrides**: Force specific songs when needed while letting the system fill the rest
- **Full Chord Sheets**: Generates complete setlists with chords and lyrics for musicians
- **History Tracking**: Maintains a database of past setlists for long-term variety

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Usage Guide](#usage-guide)
- [Managing Songs](#managing-songs)
- [Configuration](#configuration)
- [Programmatic Usage](#programmatic-usage)
- [Output Files](#output-files)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Installation

### Requirements

- Python 3.12 or higher
- No external dependencies needed (uses Python standard library only)

### Setup

1. Clone or download this repository
2. Ensure Python 3.12+ is installed:
   ```bash
   python --version  # Should show 3.12 or higher
   ```

That's it! The script is ready to use.

### Optional: Using uv

If you have [uv](https://github.com/astral-sh/uv) installed:
```bash
uv run generate_setlist.py
```

## Quick Start

Generate a setlist for today:

```bash
python generate_setlist.py
```

This will:
1. Load all songs from `tags.csv` and `chords/` directory
2. Analyze the last 3 setlists to avoid repetition
3. Generate a new setlist with songs for each service moment
4. Save the output to `output/YYYY-MM-DD.md` (markdown with chords)
5. Save history to `history/YYYY-MM-DD.json` (for tracking)

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

2. **Recency Penalty**: Songs used recently are penalized
   - Just used → heavily penalized
   - Used 2 services ago → moderately penalized
   - Used 3 services ago → lightly penalized
   - Not used in last 3 services → no penalty

3. **Randomization**: Adds variety to prevent the exact same order each time

**Formula**: `score = weight × recency + small_random_factor`

#### Phase 2: Ordering (Energy-Based)

After selecting songs, the system orders them by energy level to create emotional arcs:

- **Energy Scale**: Each song has an energy value (1-4)
  - **1** = High energy, upbeat, celebratory
  - **2** = Moderate-high, engaging, rhythmic
  - **3** = Moderate-low, reflective, slower
  - **4** = Deep worship, contemplative, intimate

- **Louvor Progression**: Songs are ordered 1→4 (upbeat to worship)
  - Example: Hosana (1) → Oceanos (2) → Perfeito Amor (3) → Lugar Secreto (4)

- **Override Preservation**: Manually specified songs maintain your exact order

### Example Selection

For the "louvor" moment, if we have:
- **Oceanos**: weight=5, last used 3 services ago → high score
- **Santo Pra Sempre**: weight=4, used last service → low score
- **A Casa é Sua**: weight=3, never used → medium-high score

The generator will likely pick: Oceanos, A Casa é Sua, and two other high-scoring songs.

## Usage Guide

### Basic Usage

```bash
# Generate setlist for today
python generate_setlist.py

# Generate for a specific date
python generate_setlist.py --date 2026-02-15

# Generate for next Sunday
python generate_setlist.py --date 2026-02-02
```

### Using Overrides

Sometimes you want to force specific songs (e.g., themed service, special requests):

```bash
# Force "Oceanos" for one of the louvor songs
python generate_setlist.py --override "louvor:Oceanos"

# Force multiple songs for louvor
python generate_setlist.py --override "louvor:Oceanos,Santo Pra Sempre,Hosana"

# Override multiple moments
python generate_setlist.py \
  --override "prelúdio:Estamos de Pé" \
  --override "louvor:Oceanos,Hosana" \
  --override "poslúdio:Autoridade e Poder"
```

**How overrides work:**
- System uses your specified songs first
- Then fills remaining slots with smart selection
- Example: If louvor needs 4 songs and you override with 2, the system picks 2 more

### Dry Run (Preview)

Preview a setlist without saving to history:

```bash
python generate_setlist.py --no-save
```

Useful for:
- Testing song combinations
- Planning future services without affecting history
- Experimenting with different dates

### Custom Output Location

```bash
# Custom file path for markdown output
python generate_setlist.py --output ~/Desktop/next-sunday.md

# Custom directories for all output
python generate_setlist.py --output-dir custom/output --history-dir custom/history
```

### Getting Help

```bash
python generate_setlist.py --help
```

## Managing Songs

### Song Database: `tags.csv`

This file maps songs to service moments with energy levels and optional weights.

**Format**: `song;energy;tags`

#### Basic Format with Energy

```csv
song;energy;tags
Hosana;1;louvor
Oceanos;2;louvor
Perfeito Amor;3;louvor
Lugar Secreto;4;louvor
Fico Feliz;1;crianças
Tributo a Jehovah;2;ofertório
```

**Energy column (1-4 scale):**
- **1**: High energy, upbeat, celebratory (e.g., Hosana, Santo Pra Sempre)
- **2**: Moderate-high, engaging, rhythmic (e.g., Oceanos, Grande É o Senhor)
- **3**: Moderate-low, reflective, slower (e.g., Perfeito Amor, Consagração)
- **4**: Deep worship, contemplative, intimate (e.g., Lugar Secreto, Tudo é Perda)

#### Weighted Tags

Add `(weight)` after a moment to increase selection probability (1-10 scale):

```csv
song;energy;tags
Oceanos;2;louvor(5)           # High weight, moderate energy
Santo Pra Sempre;1;louvor(4)  # Medium-high weight, high energy
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
song;energy;tags
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
| **1** | High energy, upbeat, celebratory | Fast | Hosana, Santo Pra Sempre, Estamos de Pé |
| **2** | Moderate-high, engaging, rhythmic | Medium-fast | Oceanos, Ousado Amor, Grande É o Senhor |
| **3** | Moderate-low, reflective, thoughtful | Medium-slow | Perfeito Amor, Consagração, Jesus Em Tua Presença |
| **4** | Deep worship, contemplative, intimate | Slow | Tudo é Perda, Lugar Secreto, Aos Pés da Cruz |

#### How Energy Affects Setlists

**For multi-song moments (louvor - 4 songs):**
- Songs are automatically ordered by energy: **1 → 2 → 3 → 4**
- This creates a natural emotional arc from celebration to intimacy
- Example progression:
  1. Santo Pra Sempre (energy 1) - upbeat celebration
  2. Oceanos (energy 2) - engaging worship
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

**File naming**: Must exactly match the song name in `tags.csv`
- `tags.csv`: `Oceanos;louvor`
- File: `chords/Oceanos.md`

**Format**:

```markdown
# Song Title (Key)

```
[Chord notation with lyrics]
```
```

**Example** (`chords/Oceanos.md`):

```markdown
# Oceanos (Bm)

```
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
```

### Adding a New Song

1. **Classify the song's energy** (1-4):
   - Listen to the song and assess its tempo, intensity, and mood
   - Use the energy scale guide above
   - When in doubt, use 2 or 3 (moderate energy)

2. **Add to `tags.csv`** with energy and tags:
   ```csv
   Nova Canção;2;louvor(3),prelúdio
   ```
   - Format: `song_name;energy;tags`
   - Energy: 1 (upbeat) to 4 (contemplative)
   - Tags: Moments with optional weights

3. **Create chord file** `chords/Nova Canção.md`:
   ```markdown
   # Nova Canção (G)

   ```
   G              D
   Letra da música...
   ```
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

1. Delete or comment out the line in `tags.csv`:
   ```csv
   # Old Song;louvor  ← This song won't be selected anymore
   ```

2. Optionally delete `chords/Old Song.md`

### Updating Song Tags/Weights

Edit `tags.csv`:

```csv
# Before
Oceanos;louvor(3)

# After - increase weight because congregation loves it
Oceanos;louvor(5)
```

Changes take effect immediately on the next generation.

## Configuration

Advanced users can modify the generator's behavior through various configuration methods.

### Output Paths

The generator supports flexible output path configuration with the following priority (highest to lowest):

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

**3. Configuration File:**
Edit `setlist/config.py`:
```python
DEFAULT_OUTPUT_DIR = "output"    # Markdown files
DEFAULT_HISTORY_DIR = "history"  # JSON tracking
```

**4. Defaults:**
If no configuration is provided:
- Markdown files → `output/`
- JSON history → `history/`

**Examples:**
```bash
# Use defaults (output/ and history/)
python generate_setlist.py

# Custom directories via CLI
python generate_setlist.py --output-dir /mnt/setlists --history-dir /mnt/tracking

# Custom directories via environment
export SETLIST_OUTPUT_DIR=$HOME/worship/output
export SETLIST_HISTORY_DIR=$HOME/worship/history
python generate_setlist.py
```

### Change Songs Per Moment

Edit `MOMENTS_CONFIG` (line 31):

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

Edit energy configuration (lines 44-48):

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

### Change Recency Window

Edit `RECENCY_PENALTY_PERFORMANCES` (line 41):

```python
RECENCY_PENALTY_PERFORMANCES = 3  # Change to 4 or 5 for more variety
```

- `3` = avoid repeating songs used in last 3 services
- `5` = avoid repeating songs used in last 5 services

### Change Default Weight

Edit `DEFAULT_WEIGHT` (line 40):

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

2. Add songs with the new tag in `tags.csv`:
   ```csv
   Lugar Secreto;meditação
   ```

## Programmatic Usage

The setlist generator can be used as a Python library in your own scripts, allowing you to integrate setlist generation into custom workflows, web applications, or automation tools.

### Using the SetlistGenerator Class (Recommended)

The object-oriented API provides better state management and is recommended for new code:

```python
from setlist import SetlistGenerator, load_songs, load_history
from pathlib import Path

# Load songs and history
songs = load_songs(Path("."))
history = load_history(Path("./history"))

# Create generator instance
generator = SetlistGenerator(songs, history)

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

# Generate multiple setlists with same instance
setlist2 = generator.generate("2026-03-22")
setlist3 = generator.generate("2026-03-29")
```

**Benefits:**
- ✓ State managed internally (recency scores calculated once)
- ✓ Reusable (generate multiple setlists efficiently)
- ✓ Easy to test and extend

### Using the Functional API (Backward Compatible)

The functional API is still available and works identically:

```python
from setlist import load_songs, load_history, generate_setlist
from pathlib import Path

songs = load_songs(Path("."))
history = load_history(Path("./history"))

setlist = generate_setlist(
    songs=songs,
    history=history,
    date="2026-03-15",
    overrides={"louvor": ["Oceanos"]}
)
```

Both APIs produce identical results. Choose based on your needs:
- **SetlistGenerator class**: Better for complex workflows, testing, or multiple generations
- **generate_setlist() function**: Simpler for one-off script usage

### Custom Formatting and Saving

```python
from setlist import SetlistGenerator, load_songs, load_history
from setlist import format_setlist_markdown, save_setlist_history
from pathlib import Path

# Generate setlist
songs = load_songs(Path("."))
history = load_history(Path("./history"))
generator = SetlistGenerator(songs, history)
setlist = generator.generate("2026-03-15")

# Format as markdown
markdown = format_setlist_markdown(setlist, songs)

# Save to custom location
output_path = Path("~/Desktop/next-service.md").expanduser()
with open(output_path, "w", encoding="utf-8") as f:
    f.write(markdown)

# Save to history (optional)
save_setlist_history(setlist, Path("./history"))
```

### Batch Generation

Generate multiple setlists programmatically:

```python
from setlist import SetlistGenerator, load_songs, load_history
from pathlib import Path
from datetime import datetime, timedelta

songs = load_songs(Path("."))
history = load_history(Path("./history"))
generator = SetlistGenerator(songs, history)

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
from setlist import SetlistGenerator, load_songs, load_history
from pathlib import Path

app = Flask(__name__)

# Initialize once at startup
songs = load_songs(Path("."))
history = load_history(Path("./history"))
generator = SetlistGenerator(songs, history)

@app.route('/generate/<date>')
def generate_setlist_api(date):
    setlist = generator.generate(date)
    return jsonify({
        "date": setlist.date,
        "moments": setlist.moments,
        "total_songs": sum(len(s) for s in setlist.moments.values())
    })

if __name__ == '__main__':
    app.run(debug=True)
```

## Output Files

### Markdown Setlist (`output/YYYY-MM-DD.md`)

Human-readable setlist with full chords and lyrics for musicians.

**Structure**:
```markdown
# Setlist - 2026-02-15

## Prelúdio

# Estamos de Pé (G)

```
G              D
Estamos de pé...
```

---

## Louvor

# Oceanos (Bm)
...
```

**Use cases**:
- Print for musicians
- Display on tablet/screen during rehearsal
- Share via email/WhatsApp

### History File (`history/YYYY-MM-DD.json`)

Machine-readable format for tracking which songs were used.

**Structure**:
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

**Purpose**: The generator reads these files to avoid repeating songs too soon.

## Examples

### Example 1: Regular Sunday Service

```bash
python generate_setlist.py --date 2026-02-15
```

**Output**:
```
Loading songs...
Loaded 54 songs
Loading history...
Found 12 historical setlists

Generating setlist...

==================================================
SETLIST FOR 2026-02-15
==================================================

PRELÚDIO:
  - Abra os olhos do meu coração

OFERTÓRIO:
  - Agradeço

SAUDAÇÃO:
  - Corpo e Família

CRIANÇAS:
  - Deus Grandão

LOUVOR:
  - Santo Pra Sempre
  - Oceanos
  - Consagração
  - Aos Pés da Cruz

POSLÚDIO:
  - Vou Seguir Com Fé

Markdown saved to: output/2026-02-15.md
History saved to: history/2026-02-15.json
```

**Note**: The louvor songs are automatically ordered by energy level:
- Santo Pra Sempre (energy 1) - upbeat celebration
- Oceanos (energy 2) - engaging worship
- Consagração (energy 3) - reflective
- Aos Pés da Cruz (energy 4) - deep worship

This creates a natural emotional arc from high energy to intimate worship.

### Example 2: Themed Service (Prayer Focus)

Force prayer-focused songs:

```bash
python generate_setlist.py \
  --date 2026-02-22 \
  --override "louvor:Lugar Secreto,Mais Que Uma Voz,Jesus Em Tua Presença"
```

The system will:
- Use your 3 specified louvor songs **in the exact order you provided**
- Pick 1 more louvor song automatically (sorted by energy with other auto-selected songs)
- Fill all other moments with smart selection

**Example output:**
```
LOUVOR:
  - Lugar Secreto      (your override - energy 4)
  - Mais Que Uma Voz   (your override - energy 3)
  - Jesus Em Tua Presença (your override - energy 3)
  - Oceanos            (auto-selected - energy 2)
```

**Note**: Your override songs (first 3) maintain the exact order you specified, even though they're not energy-sorted. Only the auto-selected song (Oceanos) follows energy ordering rules.

### Example 3: Special Music Request

Someone requested "Oceanos" for their birthday:

```bash
python generate_setlist.py \
  --date 2026-03-01 \
  --override "louvor:Oceanos"
```

The system ensures Oceanos is included while selecting 3 other louvor songs automatically.

### Example 4: Preview Next Month

Plan ahead without affecting history:

```bash
python generate_setlist.py --date 2026-03-15 --no-save
```

Review the output, and if you don't like it, run again for a different selection. When satisfied, run without `--no-save`.

### Example 5: Back-to-Back Services

Generate multiple services:

```bash
python generate_setlist.py --date 2026-02-15
python generate_setlist.py --date 2026-02-22
python generate_setlist.py --date 2026-03-01
```

Each service will automatically avoid songs used in previous services.

## Troubleshooting

### Problem: Song not appearing in setlists

**Possible causes:**

1. **Song was recently used**
   - Check `history/*.json` files for recent usage
   - Wait 3 services or use `--override` to force it

2. **Tag/weight issue**
   - Verify song is in `tags.csv`
   - Check if weight is too low (try increasing to 4-5)

3. **Wrong moment tag**
   - Ensure the moment tag matches: `prelúdio`, `ofertório`, `saudação`, `crianças`, `louvor`, `poslúdio`

4. **Not enough songs in that moment**
   - Check if you have enough songs tagged for that moment in `tags.csv`

### Problem: Error "File not found: chords/Song.md"

The song is in `tags.csv` but the chord file is missing or misnamed.

**Solution:**
- Create `chords/Song Name.md` with exact spelling
- Check for typos in file name vs. `tags.csv` entry
- Ensure file extension is `.md` not `.txt`

### Problem: Same songs appearing repeatedly

**Solutions:**

1. **Increase recency window** (line 41 in `generate_setlist.py`):
   ```python
   RECENCY_PENALTY_PERFORMANCES = 5  # Instead of 3
   ```

2. **Add more songs** to `tags.csv` for variety

3. **Adjust weights** - lower weights on overused songs:
   ```csv
   # Before
   Oceanos;louvor(5)

   # After
   Oceanos;louvor(3)
   ```

### Problem: Too many/few songs for a moment

Edit `MOMENTS_CONFIG` in `generate_setlist.py` (line 31):

```python
MOMENTS_CONFIG = {
    "prelúdio": 1,
    "ofertório": 1,
    "saudação": 1,
    "crianças": 1,
    "louvor": 5,      # Changed from 4 to 5
    "poslúdio": 1,
}
```

### Problem: Songs in the wrong energy order

If you want to disable energy ordering and use score-based order only:

Edit `generate_setlist.py` (line 44):
```python
ENERGY_ORDERING_ENABLED = False  # Disable energy ordering
```

Or if energy classifications seem wrong, update individual songs in `tags.csv`:
```csv
# Before
Hosana;3;louvor  # Classified as reflective (wrong!)

# After
Hosana;1;louvor  # Corrected to upbeat (right!)
```

### Problem: Override songs are being re-ordered

This is expected behavior! Override songs maintain **your exact order**, but you might be seeing auto-selected songs sorted by energy.

**Example:**
```bash
--override "louvor:Lugar Secreto,Hosana"
# Output: Lugar Secreto, Hosana, [auto-song-1], [auto-song-2]
# ✓ Your overrides stay in order
# ✓ Auto-selected songs are energy-sorted
```

If you want complete control over order, override all songs for that moment:
```bash
--override "louvor:Song1,Song2,Song3,Song4"  # All 4 louvor songs
```

### Problem: Wrong date in output

The script uses today's date by default. Always specify the date:

```bash
python generate_setlist.py --date 2026-02-15
```

### Problem: Encoding errors (special characters)

This project uses UTF-8 encoding for Portuguese characters (ã, ç, é, etc.).

Ensure your editor/terminal supports UTF-8:
- VSCode: Check bottom-right corner shows "UTF-8"
- Terminal: Should support UTF-8 by default on macOS/Linux

## 📝 Notes

### Song Naming Conventions

- Use exact titles as they appear on official recordings
- Include accents: "Tributo a Jehovah" not "Tributo a Jehovah"
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
Oceanos;2;louvor
Santo Pra Sempre;1;louvor
Hosana;1;louvor
Lugar Secreto;4;louvor

# After a few months - adjust weights based on congregation response
Oceanos;2;louvor(5)         # Everyone loves this (energy unchanged)
Santo Pra Sempre;1;louvor(4)  # Popular (energy unchanged)
Hosana;1;louvor(2)         # Less familiar, use less often (energy unchanged)
Lugar Secreto;4;louvor(5)    # Powerful worship moment (energy unchanged)
```

**Remember:**
- **Energy** = What the song **is** (musical character)
- **Weight** = How often we **want** it (selection preference)

### History Management

The system automatically manages history in `history/*.json`. These files are small and should be kept for accurate variety tracking.

If you want to reset history (new year, etc.):
```bash
# Backup first
cp -r history history_backup

# Clear history
rm history/*.json
```

## Advanced Workflows

### Workflow 1: Planning Multiple Services

```bash
# Plan next 4 Sundays
for date in 2026-02-01 2026-02-08 2026-02-15 2026-02-22; do
  python generate_setlist.py --date $date
done

# Review all setlists
cat output/2026-02-*.md
```

### Workflow 2: Seasonal Adjustments

For the Christmas season, increase weights on Christmas songs:

```csv
# Before
Noite de Paz;4;louvor,prelúdio

# During December (increase weight, keep energy)
Noite de Paz;4;louvor(7),prelúdio(6)

# After Christmas, reduce weight again
Noite de Paz;4;louvor(2),prelúdio(2)
```

**Note**: Energy levels (column 2) typically stay the same as they reflect the song's intrinsic character, not seasonal preference. Adjust weights (in tags) to change selection frequency.

### Workflow 3: Testing New Songs

Add new songs with low weights initially:

```csv
# New upbeat song - start with low weight
New Song;1;louvor(1)  # Energy 1 (upbeat), weight 1 (rarely selected)
```

After the congregation learns it, increase weight:
```csv
# Congregation knows it now - increase weight
New Song;1;louvor(3)  # Energy stays 1, weight now 3 (normal selection)
```

After it becomes a favorite:
```csv
# Everyone loves it - increase weight more
New Song;1;louvor(5)  # Energy still 1, weight now 5 (frequent selection)
```

**Key principle**: Energy (column 2) defines the song's character and rarely changes. Weight (in tags) controls selection frequency and can be adjusted based on congregation familiarity.

## Support

For issues or questions:
1. Check this README's Troubleshooting section
2. Review `CLAUDE.md` for technical details
3. Check the generated output files for clues

## License

This tool is provided as-is for church worship planning purposes.

---

**Made with ❤️ for worship teams**
