# Church Worship Setlist Generator

An intelligent setlist generator for church worship services that automatically selects songs based on service structure, song preferences, and performance history.

## 🎵 Features

- **Smart Song Selection**: Automatically picks songs based on configurable weights and preferences
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
- [Output Files](#output-files)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## 🚀 Installation

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

## ⚡ Quick Start

Generate a setlist for today:

```bash
python generate_setlist.py
```

This will:
1. Load all songs from `tags.csv` and `chords/` directory
2. Analyze the last 3 setlists to avoid repetition
3. Generate a new setlist with songs for each service moment
4. Save the output to `setlists/YYYY-MM-DD.md` (markdown with chords)
5. Save history to `setlists/YYYY-MM-DD.json` (for tracking)

## 🎯 How It Works

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

The system uses a **smart scoring algorithm** that considers:

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

### Example Selection

For the "louvor" moment, if we have:
- **Oceanos**: weight=5, last used 3 services ago → high score
- **Santo Pra Sempre**: weight=4, used last service → low score
- **A Casa é Sua**: weight=3, never used → medium-high score

The generator will likely pick: Oceanos, A Casa é Sua, and two other high-scoring songs.

## 📖 Usage Guide

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
python generate_setlist.py --output ~/Desktop/next-sunday.md
```

### Getting Help

```bash
python generate_setlist.py --help
```

## 🎼 Managing Songs

### Song Database: `tags.csv`

This file maps songs to service moments with optional weights.

**Format**: `song;tags`

#### Basic Tag Format

```csv
song;tags
Oceanos;louvor
Deus Cuida de Mim;louvor
Fico Feliz;crianças
Tributo a Jehovah;ofertório
```

#### Weighted Tags

Add `(weight)` after a moment to increase selection probability (1-10 scale):

```csv
song;tags
Oceanos;louvor(5)           # Very likely to be selected for louvor
Santo Pra Sempre;louvor(4)  # More likely than default
A Casa é Sua;louvor(2)      # Less likely than default
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
song;tags
Autoridade e Poder;prelúdio,poslúdio
Brilha Jesus;saudação(4),poslúdio(2)
Estamos de Pé;prelúdio(5),poslúdio(3)
```

This means:
- "Autoridade e Poder" can be used as prelúdio OR poslúdio (weight 3 for both)
- "Brilha Jesus" works great for saudação (weight 4) or okay for poslúdio (weight 2)

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

1. **Add to `tags.csv`**:
   ```csv
   Nova Canção;louvor(3),prelúdio
   ```

2. **Create chord file** `chords/Nova Canção.md`:
   ```markdown
   # Nova Canção (G)

   ```
   G              D
   Letra da música...
   ```
   ```

3. **Run generator** - the song is now in the pool!

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

## ⚙️ Configuration

Advanced users can modify the generator's behavior by editing `generate_setlist.py`.

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

## 📁 Output Files

### Markdown Setlist (`setlists/YYYY-MM-DD.md`)

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

### History File (`setlists/YYYY-MM-DD.json`)

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

## 💡 Examples

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
  - Oceanos
  - Santo Pra Sempre
  - Aos Pés da Cruz
  - Consagração

POSLÚDIO:
  - Vou Seguir Com Fé

Markdown saved to: setlists/2026-02-15.md
History saved to: setlists/2026-02-15.json
```

### Example 2: Themed Service (Prayer Focus)

Force prayer-focused songs:

```bash
python generate_setlist.py \
  --date 2026-02-22 \
  --override "louvor:Lugar Secreto,Mais Que Uma Voz,Jesus Em Tua Presença"
```

The system will:
- Use your 3 specified louvor songs
- Pick 1 more louvor song automatically
- Fill all other moments with smart selection

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

## 🔧 Troubleshooting

### Problem: Song not appearing in setlists

**Possible causes:**

1. **Song was recently used**
   - Check `setlists/*.json` files for recent usage
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

### Weight Strategy

Start conservative with weights (mostly 3s), then adjust based on experience:

```csv
# Initial setup - everything at default
Oceanos;louvor
Santo Pra Sempre;louvor
Hosana;louvor

# After a few months - adjust based on congregation response
Oceanos;louvor(5)         # Everyone loves this
Santo Pra Sempre;louvor(4)  # Popular
Hosana;louvor(2)         # Less familiar, use less often
```

### History Management

The system automatically manages history in `setlists/*.json`. These files are small and should be kept for accurate variety tracking.

If you want to reset history (new year, etc.):
```bash
# Backup first
cp -r setlists setlists_backup

# Clear history (keep only markdown files)
rm setlists/*.json
```

## 🎪 Advanced Workflows

### Workflow 1: Planning Multiple Services

```bash
# Plan next 4 Sundays
for date in 2026-02-01 2026-02-08 2026-02-15 2026-02-22; do
  python generate_setlist.py --date $date
done

# Review all setlists
cat setlists/2026-02-*.md
```

### Workflow 2: Seasonal Adjustments

For Christmas season, increase weights on Christmas songs:

```csv
# Before
Noite de Paz;louvor,prelúdio

# During December
Noite de Paz;louvor(7),prelúdio(6)

# After Christmas, reduce again
Noite de Paz;louvor(2),prelúdio(2)
```

### Workflow 3: Testing New Songs

Add new songs with low weights initially:

```csv
New Song;louvor(1)  # Start low
```

After congregation learns it:
```csv
New Song;louvor(3)  # Increase to normal
```

## 📞 Support

For issues or questions:
1. Check this README's Troubleshooting section
2. Review `CLAUDE.md` for technical details
3. Check the generated output files for clues

## 📄 License

This tool is provided as-is for church worship planning purposes.

---

**Made with ❤️ for worship teams**
