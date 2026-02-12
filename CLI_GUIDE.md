# CLI Command Reference

Complete guide to all `songbook` CLI commands.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Commands](#core-commands)
  - [generate](#generate---generate-setlists)
  - [view-setlist](#view-setlist---view-generated-setlists)
  - [view-song](#view-song---view-individual-songs)
  - [replace](#replace---replace-songs-in-setlists)
  - [info](#info---song-statistics)
  - [transpose](#transpose---transpose-chords)
  - [list-moments](#list-moments---list-service-moments)
- [Output Commands](#output-commands)
  - [pdf](#pdf---generate-pdf-from-setlist)
  - [markdown](#markdown---regenerate-markdown-from-setlist)
  - [youtube](#youtube---create-youtube-playlist)
- [Data Maintenance Commands](#data-maintenance-commands)
  - [cleanup](#cleanup---check-data-quality)
  - [fix-punctuation](#fix-punctuation---normalize-punctuation)
  - [import-history](#import-history---import-external-data)
- [Shell Completion](#shell-completion)

## Installation

### Requirements

- Python 3.12 or higher
- Package manager: [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Quick Setup (Recommended - Using uv)

```bash
# Install everything in one command
uv sync
```

This single command:
- ✓ Reads dependencies from `pyproject.toml`
- ✓ Creates/updates `uv.lock` for reproducible installs
- ✓ Installs all dependencies
- ✓ Installs the songbook package in editable mode
- ✓ Creates an isolated virtual environment

That's it! The `songbook` command is now available.

### Alternative Setup (Using pip)

```bash
pip install -e .
```

## Quick Start

```bash
# Generate setlist for today
songbook generate

# Generate with PDF
songbook generate --pdf

# View the latest setlist
songbook view-setlist --keys

# View a specific song
songbook view-song "Oceanos"

# Get help
songbook --help
songbook generate --help
```

---

## Core Commands

### `generate` - Generate Setlists

Generate a new setlist for a worship service.

**Basic Usage:**

```bash
# Generate setlist for today (markdown only)
songbook generate

# Generate for a specific date
songbook generate --date 2026-02-15

# Generate with PDF output
songbook generate --pdf
songbook generate --date 2026-02-15 --pdf
```

**Using Overrides:**

Force specific songs for any moment:

```bash
# Force "Oceanos" for one of the louvor songs
songbook generate --override "louvor:Oceanos"

# Force multiple songs for louvor
songbook generate --override "louvor:Oceanos,Santo Pra Sempre,Hosana"

# Override multiple moments
songbook generate \
  --override "prelúdio:Estamos de Pé" \
  --override "louvor:Oceanos,Hosana" \
  --override "poslúdio:Autoridade e Poder"
```

**How overrides work:**
- System uses your specified songs first
- Then fills remaining slots with smart selection
- Example: If louvor needs 4 songs and you override with 2, the system picks 2 more

**Dry Run (Preview):**

Preview a setlist without saving to history:

```bash
songbook generate --no-save
```

Useful for:
- Testing song combinations
- Planning future services without affecting history
- Experimenting with different dates

**Custom Output Location:**

```bash
# Custom file path for markdown output
songbook generate --output ~/Desktop/next-sunday.md

# Custom directories for all output
songbook generate --output-dir custom/output --history-dir custom/history
```

**Labeled Setlists (Multiple Services Per Day):**

Derive a variant setlist from an existing one for the same date:

```bash
# Generate primary setlist first
songbook generate --date 2026-03-01

# Derive evening variant (replaces random songs)
songbook generate --date 2026-03-01 --label evening

# Derive replacing exactly 3 songs
songbook generate --date 2026-03-01 --label evening --replace 3

# Derive replacing all songs
songbook generate --date 2026-03-01 --label evening --replace all
```

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Service date (default: today) |
| `--label TEXT`, `-l` | Setlist label for multiple setlists per date (e.g., "evening") |
| `--replace N`, `-r` | Songs to replace when deriving (number or "all"). Requires `--label` |
| `--override MOMENT:SONGS` | Force specific songs (can be used multiple times) |
| `--pdf` | Generate PDF in addition to markdown |
| `--no-save` | Preview mode - don't save to history |
| `--output PATH` | Custom output file path |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

**Example Output:**

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

LOUVOR:
  - Santo Pra Sempre
  - Oceanos
  - Consagração
  - Aos Pés da Cruz

...

Markdown saved to: output/2026-02-15.md
History saved to: history/2026-02-15.json
```

---

### `view-setlist` - View Generated Setlists

Quickly view generated setlists without opening files.

**Usage:**

```bash
# View the latest setlist
songbook view-setlist

# View a specific date
songbook view-setlist --date 2026-02-15

# View a labeled setlist
songbook view-setlist --date 2026-03-01 --label evening

# Include song keys in the output
songbook view-setlist --keys
songbook view-setlist --date 2026-02-15 --keys
```

**Example Output:**

```
============================================================
SETLIST FOR 2026-02-08
Sunday, February 08, 2026
============================================================

PRELÚDIO:
  - Abra os olhos do meu coração (E)

OFERTÓRIO:
  - Venho Senhor Minha Vida Oferecer (G)

LOUVOR:
  - Tudo é Perda (E)
  - Deus Cuida de Mim (E)
  - Me Derramar (G)
  - Livre Acesso (G)

...

FILES:
  Markdown: output/2026-02-08.md ✓
  PDF:      output/2026-02-08.pdf ✓
  History:  history/2026-02-08.json ✓
```

**Useful for:**
- Quickly checking what was generated without opening files
- Reviewing past setlists
- Verifying output files exist
- Getting song keys at a glance

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | View specific date (default: latest) |
| `--label TEXT`, `-l` | Setlist label |
| `--keys`, `-k` | Show song keys alongside titles |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

---

### `view-song` - View Individual Songs

View a specific song's lyrics and chords without opening files.

**Usage:**

```bash
# View a specific song
songbook view-song "Oceanos"

# List all available songs
songbook view-song --list

# View without metadata (tags, energy)
songbook view-song "Hosana" --no-metadata

# View transposed to a different key (display-only)
songbook view-song "Oceanos" --transpose G
songbook view-song "Oceanos" -t D
```

**Example Output:**

```
======================================================================
Oceanos (Bm)
======================================================================

Tags:   louvor(2)
Energy: 3.0 - Moderate-low, reflective, slower

----------------------------------------------------------------------

Bm                   A/C#    D
   Tua voz me chama sobre as águas
         A              G
Onde os meus pés podem falhar
Bm                    A/C#  D
   E ali Te encontro no mistério
        A            G
Em meio ao mar, confiarei

[Refrão]

G         D       A
  Ao Teu nome clamarei
...
```

**Features:**
- Displays full chord notation and lyrics
- Shows song metadata (tags, energy level)
- Smart search: suggests similar songs if name not found
- List all songs with `--list` flag
- Transpose to any key with `--transpose` (display-only, never modifies files)

**Use cases:**
- Quickly reference chords during practice
- Check song key before rehearsal
- Review lyrics without opening files
- Find songs by partial name match
- Preview how a song looks in a different key

**Options:**

| Option | Description |
|--------|-------------|
| `--list`, `-l` | List all available songs with their keys and tags |
| `--no-metadata` | Hide tags and energy information |
| `--transpose KEY`, `-t KEY` | Transpose chords to target key (display-only) |

---

### `replace` - Replace Songs in Setlists

Replace individual songs in a generated setlist without regenerating the entire setlist.

**Simplified Usage (Position Defaults to 1):**

For single-song moments (prelúdio, ofertório, saudação, crianças, poslúdio), you can omit the position:

```bash
# Replace prelúdio song (defaults to position 1)
songbook replace --moment prelúdio

# Same as:
songbook replace --moment prelúdio --position 1
```

**When to omit position:**
- ✅ Single-song moments (5 out of 6 moments)
- ✅ When replacing the first song in louvor
- ❌ Don't omit for louvor positions 2-4 (be explicit)

**Basic Replacement (Auto Mode):**

Let the system pick the best replacement:

```bash
# Replace song at position 2 in louvor
songbook replace --moment louvor --position 2
```

The system will:
- Apply all selection rules (weights, recency, energy)
- Exclude songs already in the setlist
- Choose the next best candidate
- Reorder by energy to maintain emotional arc

**Manual Replacement:**

Specify exactly which song to use:

```bash
# Replace with "Oceanos"
songbook replace --moment louvor --position 2 --with "Oceanos"
```

**Requirements for manual replacement:**
- Song must exist in `database.csv`
- Song must be tagged for the target moment
- Song must not already be in the setlist

**Replace Multiple Songs:**

```bash
# Replace positions 1 and 3 (both auto-selected)
songbook replace --moment louvor --positions 1,3
```

**Note:** When replacing multiple positions, all replacements use auto-selection mode (you cannot use `--with` for batch replacements).

**Replace for Specific Date:**

By default, replaces in the most recent setlist. To target a specific date:

```bash
songbook replace --date 2026-03-15 --moment louvor --position 2
```

**Position Indexing:**

Positions are **1-indexed** for user convenience:
- Prelúdio, Ofertório, Saudação, Crianças, Poslúdio: Position 1 only
- Louvor: Positions 1-4

**Examples:**

```bash
# View current setlist
cat output/2026-03-15.md

# Replace prelúdio song (auto mode)
songbook replace --moment prelúdio --position 1

# Replace louvor position 3 with specific song
songbook replace --moment louvor --position 3 --with "Grande É o Senhor"

# Replace multiple louvor positions
songbook replace --moment louvor --positions 2,4

# Replace for a past service
songbook replace --date 2025-12-25 --moment louvor --position 1
```

**How It Works:**

**Auto Mode:**
1. Calculates recency scores for all songs (same date as original setlist)
2. Builds exclusion set (all songs currently in setlist EXCEPT the one being replaced)
3. Uses same selection algorithm as generation (weight × (recency + 0.1) + randomization)
4. Reorders moment by energy to maintain emotional arc

**Manual Mode:**
1. Validates song exists and has required moment tag
2. Validates song not already in setlist
3. Replaces song at specified position
4. Reorders by energy

**Files Updated:**
- `output/YYYY-MM-DD.md` (markdown with chords)
- `history/YYYY-MM-DD.json` (history tracking)

Both files are completely regenerated to reflect the updated setlist.

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Target specific date (default: latest) |
| `--label TEXT`, `-l` | Setlist label |
| `--moment MOMENT` | Service moment to modify (required) |
| `--position N` | Position to replace (1-indexed, default: 1) |
| `--positions N,M,..` | Replace multiple positions (auto mode only) |
| `--with "SONG"` | Manual replacement with specific song |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

**Troubleshooting:**

**"No available replacement songs"**
- All eligible songs for that moment are already in the setlist
- Solution: Use manual mode to specify a song, or remove one of the existing songs first

**"Song not tagged for moment"**
- The song doesn't have the required moment tag in `database.csv`
- Solution: Add the moment tag to the song, or choose a different song

**"Position out of range"**
- Position must be within valid range for that moment
- Louvor: 1-4, Others: usually 1
- Solution: Check the setlist to see valid positions

**"Setlist for date not found"**
- The specified date doesn't exist in history
- Solution: Check `history/` directory for available dates

---

### `info` - Song Statistics

View detailed statistics for any song, including metadata, recency score, and full usage history.

**Usage:**

```bash
songbook info "Oceanos"
```

**Example Output:**

```
============================================================
Oceanos (Bm)
============================================================

Energy:  3 - Moderate-low, reflective, slower
Tags:    louvor(2)

------------------------------------------------------------
RECENCY
------------------------------------------------------------
Score:          0.99
Last used:      191 day(s) ago

------------------------------------------------------------
USAGE HISTORY (2 time(s))
------------------------------------------------------------
  2025-05-31  louvor
  2025-07-27  louvor
```

**Features:**
- Shows song key, energy level, and moment tags with weights
- Displays recency score (0.00 = just used, 1.00 = never used / very long ago)
- Lists every date the song was used and in which moment
- Smart search: suggests similar songs if name not found

**Use cases:**
- Check when a song was last used before adding it to an override
- Understand why a song keeps or doesn't keep appearing in setlists
- Review a song's full performance history

---

### `transpose` - Transpose Chords

Transpose any song's chords to a different key. Useful when a vocalist needs a different key, or when adapting songs for different instruments.

**Preview Transposition (Default):**

By default, transposition only displays the result without modifying any files:

```bash
# Preview "Oceanos" transposed from Bm to G
songbook transpose "Oceanos" --to G
```

**Example Output:**

```
======================================================================
Oceanos (Gm)  [original: Bm]
======================================================================

Tags:   louvor(2)
Energy: 3.0 - Moderate-low, reflective, slower

----------------------------------------------------------------------

Gm                   F/A     Bb
   Tua voz me chama sobre as águas
         F              Eb
Onde os meus pés podem falhar
...
```

You can also preview transpositions using the `view-song` command, which is always display-only:

```bash
songbook view-song "Oceanos" --transpose G
songbook view-song "Oceanos" -t D
```

**Save Transposed Chords:**

To permanently update the chord file with transposed chords, use `--save`:

```bash
songbook transpose "Oceanos" --to G --save
```

This overwrites `chords/Oceanos.md` with the transposed content. The heading key is updated too (`### Oceanos (Gm)`).

**To undo:** simply transpose back to the original key with `--save`:
```bash
songbook transpose "Oceanos" --to B --save
```

**How It Works:**

- **Chromatic transposition**: Uses modular arithmetic on the 12-semitone scale
- **Sharp/flat conventions**: Automatically uses flats for flat keys (Bb, Eb, Gm, Dm, etc.) and sharps for sharp keys (A, E, F#m, etc.)
- **Minor key inference**: If a song is in Bm and you type `--to G`, the system infers Gm (preserving the minor quality) and uses the correct accidentals
- **Column alignment**: Chord positions are preserved relative to lyrics underneath. When a transposed chord is wider (e.g., `G` → `F#`), subsequent chords shift minimally to maintain readability
- **All chord types supported**: Simple (`Am`), slash (`A/C#`), extended (`F7M(9)`, `Em7(11)/B`, `G4(6)`)

**Examples:**

```bash
# Preview transposition to a flat key
songbook transpose "Hosana" --to Bb

# Complex chords (F7M(9), G4(6), etc.) are fully supported
songbook transpose "Lugar Secreto" --to A

# Same key detection
songbook transpose "Oceanos" --to Bm
# Output: "Already in Bm — showing original."

# Save permanently
songbook transpose "Hosana" --to C --save
```

**Options:**

| Option | Description |
|--------|-------------|
| `--to KEY` | Target key (required) |
| `--save` | Permanently update the chord file (default: preview only) |

---

### `list-moments` - List Service Moments

Display all available service moments and their descriptions.

**Usage:**

```bash
songbook list-moments
```

**Output:**

```
============================================================
AVAILABLE SERVICE MOMENTS
============================================================

Moment          Songs    Description
------------------------------------------------------------
prelúdio        1        Opening/introductory worship
ofertório       1        During offering collection
saudação        1        Greeting/welcome
crianças        1        Children's ministry
louvor          4        Main worship block
poslúdio        1        Closing/sending song
```

**Useful for:**
- Knowing what moment names to use with `--moment` in the replace command
- Knowing what moments to use with `--override` in the generate command
- Understanding how many songs each moment requires

---

## Output Commands

### `pdf` - Generate PDF from Setlist

Generate a professional PDF setlist from an existing setlist in history.

**Usage:**

```bash
# Generate PDF for the latest setlist
songbook pdf

# Generate PDF for specific date
songbook pdf --date 2026-01-25
```

**PDF Features:**
- 📄 **Page 1**: Table of contents with all songs, keys, and page numbers
- 📖 **Page 2+**: Each service moment on a separate page with full chord notation
- 🎼 **Monospace chords**: Perfect alignment for guitar/piano notation
- 🇧🇷 **Portuguese formatting**: "Domingo, 25 de Janeiro de 2026"
- 🏛️ **Church terminology**: Uses "Oferta" and "Comunhão" instead of internal names

**How it works:**

The `pdf` command reads the song list from `history/YYYY-MM-DD.json` and uses current chord files from `chords/*.md`. This means if you transpose a song or edit a chord sheet, you can regenerate the PDF without re-running the selection algorithm.

**Moment Name Mapping:**

The PDF uses church-specific terminology:
- `prelúdio` → "Prelúdio"
- `ofertório` → "Oferta"
- `saudação` → "Comunhão"
- `crianças` → "Crianças"
- `louvor` → "Louvor"
- `poslúdio` → "Poslúdio"

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Generate PDF for specific date (default: latest) |
| `--label TEXT`, `-l` | Setlist label |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

---

### `markdown` - Regenerate Markdown from Setlist

Regenerate markdown output from an existing setlist in history.

**Usage:**

```bash
# Regenerate markdown for the latest setlist
songbook markdown

# Regenerate markdown for specific date
songbook markdown --date 2026-01-25
```

**How it works:**

The `markdown` command reads the song list from `history/YYYY-MM-DD.json` and uses current chord files from `chords/*.md`. This means if you transpose a song or edit a chord sheet, you can regenerate the markdown without re-running the selection algorithm.

**Use cases:**
- Update setlist after transposing a song
- Regenerate after editing chord files
- Fix formatting issues without changing song selection

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Regenerate markdown for specific date (default: latest) |
| `--label TEXT`, `-l` | Setlist label |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

---

### `youtube` - Create YouTube Playlist

Create an unlisted YouTube playlist from an existing setlist.

**Usage:**

```bash
# Create playlist from the latest setlist
songbook youtube

# Create playlist for a specific date
songbook youtube --date 2026-02-15
```

**Prerequisites:**

1. **YouTube URLs in database.csv**: Songs must have YouTube URLs in the fourth column
2. **Google OAuth credentials**: Must have `client_secrets.json` in project root

See [`YOUTUBE.md`](./YOUTUBE.md) for full setup instructions.

**How it works:**

1. Reads setlist from `history/YYYY-MM-DD.json`
2. Extracts YouTube video IDs from `database.csv`
3. Creates an unlisted playlist with format: "Culto DD.MM.YY" (e.g., "Culto 15.02.26")
4. Adds videos in setlist order
5. Returns the playlist URL

**Example Output:**

```
Loading songs and history...
Loaded 54 songs from database.csv
Found setlist for 2026-02-15

Authenticating with YouTube...
✓ Authenticated as user@example.com

Creating playlist: "Culto 15.02.26"
✓ Playlist created

Adding videos to playlist...
  ✓ Abra os olhos do meu coração
  ✓ Venho Senhor Minha Vida Oferecer
  ⊘ Tudo é Perda (no YouTube URL)
  ✓ Deus Cuida de Mim
...

Playlist created successfully!
URL: https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxx
```

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Create playlist for specific date (default: latest) |
| `--label TEXT`, `-l` | Setlist label |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

**Troubleshooting:**

- **Missing credentials**: See YOUTUBE.md for OAuth setup
- **Song missing URL**: Add YouTube URL to database.csv (fourth column)
- **Invalid URL**: Must be valid YouTube URL (youtube.com/watch?v=... or youtu.be/...)

---

## Data Maintenance Commands

### `cleanup` - Check Data Quality

Verify that all history files match your song database.

**Usage:**

```bash
songbook cleanup
```

**What it checks:**
- ✓ Song names match exactly between history and database.csv
- ✓ Capitalization is consistent
- ✓ No missing songs in the database

**What it fixes automatically:**
- Capitalization mismatches (e.g., "deus grandão" → "Deus Grandão")
- Creates backups before making changes

**Example Output:**

```
Step 1: Analyzing history files...
  ✓ Loaded 57 songs from database.csv
  ✓ Found 0 issue(s)

CLEANUP COMPLETE
✅ All songs in history match database.csv perfectly!
```

**When to run:**
- After importing external data
- Monthly as a health check
- When songs seem to be repeating unexpectedly
- Before making major changes to database.csv

---

### `fix-punctuation` - Normalize Punctuation

Normalize punctuation variations in song names across history files.

**Usage:**

```bash
songbook fix-punctuation
```

**What it fixes:**

Removes commas from song titles to match database.csv format:
- "Em Espírito, Em Verdade" → "Em Espírito Em Verdade"
- "Espírito, Enche a Minha Vida" → "Espírito Enche a Minha Vida"

**Use case:**

After running `cleanup`, if it reports punctuation differences, use this command to normalize them.

---

### `import-history` - Import External Data

Import historical setlist data from another system.

**Note:** This command requires an `import_real_history.py` script in the project root with your data. Create the script first, then run the import.

**Usage:**

1. **Create** `import_real_history.py` with your data (see format below)
2. **Run the import:**
   ```bash
   songbook import-history
   ```
3. **Check data quality:**
   ```bash
   songbook cleanup
   ```

**Data format required:**

```json
{
  "2025-12-28": {
    "format": "setlist_with_moments",
    "service_moments": {
      "Prelúdio": [{"title": "Song Name", "key": "D"}],
      "Louvor": [
        {"title": "Song 1", "key": "G"},
        {"title": "Song 2", "key": "C"}
      ]
    }
  }
}
```

**Moment name mapping:**

The import script automatically converts external names to internal format:
- "Oferta" → "ofertório"
- "Comunhão" → "saudação"
- "Prelúdio" → "prelúdio" (no change)
- "Louvor" → "louvor" (no change)
- "Crianças" → "crianças" (no change)
- "Poslúdio" → "poslúdio" (no change)

Unsupported moments (like "Ceia", "Intercessão") are skipped with a warning.

**Complete Import Workflow:**

```bash
# Step 1: Create import_real_history.py with your data
# (Define a main() function and a raw_data dictionary)

# Step 2: Run the import
songbook import-history

# Step 3: Verify data quality
songbook cleanup

# Step 4: Fix punctuation if needed
songbook fix-punctuation

# Step 5: Final verification
songbook cleanup
# Should show: "✅ All songs in history match database.csv perfectly!"

# Step 6: Test generation with real data
songbook generate --date 2026-03-01 --no-save
```

---

## Shell Completion

Enable tab completion for faster command entry.

**Quick Install:**

```bash
# Auto-detects your shell
songbook install-completion

# Or specify shell manually
songbook install-completion --shell bash
songbook install-completion --shell zsh
songbook install-completion --shell fish
```

Then restart your shell or run `source ~/.bashrc` (bash) / `source ~/.zshrc` (zsh).

**Features:**
- Tab-complete commands: `songbook gen<TAB>` → `songbook generate`
- Tab-complete song names: `songbook view-song Oce<TAB>` → `songbook view-song Oceanos`
- Tab-complete moments: `songbook replace --moment lou<TAB>` → `songbook replace --moment louvor`
- Tab-complete dates: `songbook view-setlist --date 2025-<TAB>` → shows available dates
- Tab-complete labels: `songbook view-setlist --label eve<TAB>` → `songbook view-setlist --label evening`

See [Shell Completion Guide](./.claude/SHELL_COMPLETION.md) for detailed documentation.

---

## Getting Help

```bash
# Main help
songbook --help

# Command-specific help
songbook generate --help
songbook replace --help
songbook transpose --help
```

---

**Made with ❤️ for worship teams**
