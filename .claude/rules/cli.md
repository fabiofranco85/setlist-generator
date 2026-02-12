---
paths:
  - "cli/**/*.py"
  - "pyproject.toml"
---

# CLI Documentation

This document describes all available `songbook` commands and their usage. This documentation is loaded when working on CLI-related code.

## Unified CLI

The project uses a unified `songbook` command for all operations. All commands are available through `songbook <command>`, similar to tools like `git`, `docker`, and `aws-cli`.

**Installation:**
```bash
# Install everything with uv (recommended)
uv sync

# Alternative: Using pip
pip install -e .
```

**Quick reference:**
```bash
songbook --help                      # Main help
songbook generate --date 2026-02-15  # Generate setlist
songbook generate --label evening    # Derive labeled variant from primary
songbook generate --label evening --replace 3  # Derive replacing 3 songs
songbook view-setlist --keys         # View setlist with keys
songbook view-setlist --label evening  # View labeled setlist
songbook view-song "Oceanos"         # View song details
songbook info "Oceanos"              # Song statistics and history
songbook replace --moment louvor --position 2  # Replace song
songbook replace --moment louvor --position 2 --label evening  # Replace in labeled
songbook transpose "Oceanos" --to G  # Transpose chords (preview)
songbook view-song "Oceanos" -t G    # View transposed (display-only)
songbook pdf --date 2026-02-15       # Generate PDF
songbook pdf --label evening         # Generate PDF for labeled setlist
songbook markdown --date 2026-02-15  # Regenerate markdown from history
songbook youtube --date 2026-02-15   # Create YouTube playlist from setlist
songbook list-moments                # List available moments
songbook cleanup                     # Data quality checks
```

## Commands

### songbook generate

Generate a new setlist for a specific date, or derive a labeled variant from an existing one.

**Usage:**
```bash
# Generate for today
songbook generate

# Generate for specific date
songbook generate --date 2026-02-15

# Generate with PDF output
songbook generate --pdf
songbook generate --date 2026-02-15 --pdf

# Derive labeled variant (from existing primary setlist)
songbook generate --date 2026-03-01 --label evening
songbook generate --label evening --replace 3      # Replace exactly 3 songs
songbook generate --label evening --replace all    # Replace all songs

# Override specific moments
songbook generate --override "louvor:Oceanos,Santo Pra Sempre"
songbook generate --override "prelúdio:Estamos de Pé" --override "louvor:Oceanos"

# Dry run (don't save to history)
songbook generate --no-save

# Custom output directories
songbook generate --output-dir custom/output --history-dir custom/history
```

**Options:**
- `--date YYYY-MM-DD` - Target date (default: today)
- `--label TEXT` or `-l` - Setlist label for multiple setlists per date (e.g., "evening", "morning")
- `--replace N` or `-r` - Songs to replace when deriving (number or "all", default: random). Only valid with `--label`
- `--override "moment:song1,song2"` - Force specific songs for a moment (can be used multiple times)
- `--pdf` - Generate PDF output in addition to markdown
- `--no-save` - Dry run mode, don't save to history
- `--output-dir PATH` - Custom output directory for markdown files
- `--history-dir PATH` - Custom history directory for JSON tracking

**Label behavior:**
- When `--label` is provided and a base setlist exists for the date: **derives** from the base by replacing songs
- When `--label` is provided but no base exists: generates from scratch with the label
- Labels are validated: lowercase alphanumeric, hyphens, underscores, max 30 chars
- `--replace` without `--label` produces an error

**Override Format:**
- Single song: `--override "prelúdio:Estamos de Pé"`
- Multiple songs: `--override "louvor:Oceanos,Santo Pra Sempre,Hosana"`
- Multiple moments: Use multiple `--override` flags

**Output:**
- Terminal: Summary with song titles
- `output/YYYY-MM-DD[_label].md`: Full markdown with chords
- `output/YYYY-MM-DD[_label].pdf`: PDF setlist (if `--pdf` flag used)
- `history/YYYY-MM-DD[_label].json`: History tracking (unless `--no-save`)

---

### songbook view-setlist

View a previously generated setlist without opening files.

**Usage:**
```bash
# View the latest generated setlist
songbook view-setlist

# View a specific date
songbook view-setlist --date 2026-02-15

# View a labeled setlist
songbook view-setlist --date 2026-03-01 --label evening

# View with song keys
songbook view-setlist --keys
songbook view-setlist --date 2026-02-15 --keys

# Custom history directory
songbook view-setlist --history-dir custom/history
```

**Options:**
- `--date YYYY-MM-DD` - View specific date (default: latest)
- `--label TEXT` or `-l` - Setlist label
- `--keys` - Show song keys alongside titles
- `--history-dir PATH` - Custom history directory

**Output:**
Displays:
- Service date (formatted in English)
- All songs organized by moment
- Optional: Song keys (with `--keys` flag)
- File paths and existence status (markdown, PDF, history JSON)

---

### songbook view-song

View a specific song's lyrics, chords, and metadata.

**Usage:**
```bash
# View a specific song's lyrics and chords
songbook view-song "Oceanos"

# List all available songs
songbook view-song --list

# View without metadata (tags, energy)
songbook view-song "Hosana" --no-metadata

# View transposed to a different key (display-only, never modifies files)
songbook view-song "Oceanos" --transpose G
songbook view-song "Oceanos" -t D
```

**Options:**
- `--list` or `-l` - List all available songs
- `--no-metadata` - Hide tags and energy information
- `--transpose KEY` or `-t KEY` - Transpose to target key (display-only)

**Output:**
Displays:
- Song title and key (shows `[original: Bm]` when transposed)
- Tags (moment assignments with weights)
- Energy level and description
- Full chord notation and lyrics
- When target key matches original: "Already in X — showing original."

**Features:**
- Smart search: If song not found, suggests similar songs based on partial name match
- Fuzzy matching for typos and partial names
- Transposition preserves chord-lyric column alignment
- Minor/major quality inferred from original key (e.g., `--transpose G` on a Bm song transposes to Gm)

---

### songbook info

Show detailed statistics for a song: metadata, recency score, and full usage history.

**Usage:**
```bash
# View statistics for a song
songbook info "Oceanos"

# Fuzzy search on partial match
songbook info "ocean"
```

**Arguments:**
- `SONG_NAME` - Name of the song to look up (supports tab completion)

**Output:**
Displays:
- Song title and key (extracted from chord file heading)
- Energy level and description
- Tags with weights
- Recency score (0.00 = just used, 1.00 = never used)
- Days since last use (or "never")
- Full usage history with dates and moments

**Example output:**
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

**Edge cases:**
- **Song not found**: Shows fuzzy-match suggestions, exits with code 1
- **No chord file**: Title shown without key
- **Never used**: Score = 1.00, "Last used: never", "(no usage history)"
- **No history directory**: Treated as "never used"

---

### songbook transpose

Transpose a song's chords to a different key.

**Usage:**
```bash
# Preview transposition (display-only, no files modified)
songbook transpose "Oceanos" --to G

# Persist transposed chords to the chord file
songbook transpose "Oceanos" --to G --save

# Flat key conventions are handled automatically
songbook transpose "Hosana" --to Bb

# Complex chords (F7M(9), Em7(11)/B, etc.) are fully supported
songbook transpose "Lugar Secreto" --to A
```

**Options:**
- `--to KEY` - Required: Target key (e.g. G, Bb, F#m)
- `--save` - Overwrite `chords/<song>.md` with transposed content

**Behavior:**
- **Default (no `--save`)**: Preview mode — shows transposed output without modifying files
- **With `--save`**: Overwrites the chord file in place with transposed content
- **Same key**: Detects when song is already in target key, shows "Already in X" message
- **Quality inference**: If original key is minor (Bm) and target is major (G), automatically transposes to the minor equivalent (Gm) to preserve sharp/flat conventions
- **Column alignment**: Chord positions are preserved relative to lyrics; longer chords get minimum 1-space gap

**Supported chord patterns:**
- Simple: `G`, `Am`, `C#m`, `Bb`
- Slash: `A/C#`, `E/G#`, `Em7(11)/B`
- Extended: `F7M(9)`, `Dm7(9)`, `G4(6)`, `A7M`, `C#7(9+)`, `B7(13-)`
- Section markers (`[Intro]`, `[Refrão]`, etc.) are preserved

---

### songbook replace

Replace songs in a previously generated setlist.

**Usage:**
```bash
# Auto-select replacement for position 2 in louvor
songbook replace --moment louvor --position 2

# Manual replacement with specific song
songbook replace --moment louvor --position 2 --with "Oceanos"

# Replace multiple positions (auto mode)
songbook replace --moment louvor --positions 1,3

# Replace for specific date
songbook replace --date 2026-03-15 --moment louvor --position 2

# Replace in a labeled setlist
songbook replace --moment louvor --position 2 --date 2026-03-01 --label evening
```

**Options:**
- `--moment MOMENT` - Required: Service moment (prelúdio, ofertório, saudação, crianças, louvor, poslúdio)
- `--position N` - Position to replace (1-indexed, default: 1)
- `--positions N,N` - Multiple positions (comma-separated). Cannot be used with `--position`
- `--with SONG` - Manual replacement song (auto-select if omitted)
- `--date YYYY-MM-DD` - Target date (default: latest)
- `--label TEXT` or `-l` - Setlist label
- `--output-dir PATH` - Custom output directory
- `--history-dir PATH` - Custom history directory

**Behavior:**
- **Auto mode** (no `--with`): System selects best available song based on recency and weights
- **Manual mode** (`--with "Song"`): Uses specified song (validates existence and moment tag)
- **Energy reordering**: Always reapplied after replacement to maintain emotional arc
- **Batch mode** (`--positions`): Replaces multiple songs at once, ensures no duplicates

**Note:** When neither `--position` nor `--positions` is specified, defaults to position 1.

---

### songbook pdf

Generate PDF from an existing setlist.

**Usage:**
```bash
# Generate PDF from existing setlist
songbook pdf
songbook pdf --date 2026-02-15

# Generate PDF for a labeled setlist
songbook pdf --date 2026-03-01 --label evening
```

**Options:**
- `--date YYYY-MM-DD` - Target date (default: today)
- `--label TEXT` or `-l` - Setlist label

**PDF Format:**
- **Page 1**: Table of contents with song list and page numbers
- **Page 2+**: Each moment on separate page with full chord notation
- **Typography**: Professional fonts, monospace chords
- **Date Format**: Portuguese (e.g., "Domingo, 25 de Janeiro de 2026")
- **Moment Names**: Mapped to church terminology
  - `prelúdio` → **Prelúdio**
  - `ofertório` → **Oferta**
  - `saudação` → **Comunhão**
  - `crianças` → **Crianças**
  - `louvor` → **Louvor**
  - `poslúdio` → **Poslúdio**

**Dependencies:**
Requires `reportlab` (included in `pyproject.toml`):

```bash
# Install all dependencies with uv
uv sync

# Or add reportlab specifically
uv add reportlab

# Or using pip
pip install reportlab
```

---

### songbook markdown

Regenerate markdown output from an existing setlist.

**Usage:**
```bash
# Regenerate markdown for the latest setlist
songbook markdown

# Regenerate for a specific date
songbook markdown --date 2026-02-15

# Regenerate for a labeled setlist
songbook markdown --date 2026-03-01 --label evening
```

**Options:**
- `--date YYYY-MM-DD` - Target date (default: latest)
- `--label TEXT` or `-l` - Setlist label
- `--output-dir PATH` - Custom output directory
- `--history-dir PATH` - Custom history directory

**Behavior:**
- Reads the song list from history (does NOT re-run the selection algorithm)
- Uses current chord files (picks up any transpositions or edits)
- Overwrites the existing `output/{date}[_label].md` file

**When to use:**
- After transposing a song with `songbook transpose --save`
- After manually editing a chord file in `chords/`
- When the markdown output is out of sync with chord files

---

### songbook youtube

Create a YouTube playlist from an existing setlist.

**Usage:**
```bash
# Create playlist from the latest setlist
songbook youtube

# Create playlist for a specific date
songbook youtube --date 2026-02-15

# Create playlist for a labeled setlist
songbook youtube --date 2026-03-01 --label evening
```

**Options:**
- `--date YYYY-MM-DD` - Target date (default: latest)
- `--label TEXT` or `-l` - Setlist label
- `--output-dir PATH` - Custom output directory
- `--history-dir PATH` - Custom history directory

**Behavior:**
- Reads setlist from history (same as `pdf` and `markdown` commands)
- Maps songs to YouTube video IDs via the `youtube` column in `database.csv`
- Creates an unlisted playlist on YouTube with songs in exact setlist order
- Songs without YouTube links are skipped with a warning
- If ALL songs lack YouTube links, the command errors out

**Prerequisites:**
- YouTube URLs in `database.csv`'s `youtube` column
- Google OAuth credentials (`client_secrets.json` in project root)
- See `YOUTUBE.md` for full setup instructions

**Dependencies:**
Requires `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2` (included in `pyproject.toml`):

```bash
# Install all dependencies with uv
uv sync
```

---

### songbook list-moments

Display all available service moments.

**Usage:**
```bash
songbook list-moments
```

**Output:**
Shows all available moments with their song counts and descriptions. Useful for knowing what values to use with `--moment` arguments in other commands.

Example output:
```
Available service moments:
  prelúdio    (1 song)  - Opening/introductory song
  ofertório   (1 song)  - Offering song
  saudação    (1 song)  - Greeting/welcome song
  crianças    (1 song)  - Children's song
  louvor      (4 songs) - Main worship block
  poslúdio    (1 song)  - Closing song
```

---

### songbook cleanup

Automated data quality checker and fixer for history files.

**Usage:**
```bash
songbook cleanup
```

**What it does:**
- Analyzes all history files for inconsistencies with database.csv
- Automatically fixes capitalization mismatches (e.g., "deus grandão" → "Deus Grandão")
- Identifies songs in history that don't exist in database.csv
- Provides fuzzy matching suggestions for similar song names
- Creates timestamped backups before making changes

**When to use:**
- After importing external data
- When you suspect data quality issues
- As a periodic health check (monthly/quarterly)
- Before major changes to database.csv

**Output:**
- Shows capitalization fixes applied
- Lists missing songs with suggestions
- Creates backup directory (e.g., `history_backup_20260129_105330`)

**Example output:**
```
Step 1: Analyzing history files...
  ✓ Loaded 57 songs from database.csv
  ✓ Found 11 issue(s)

Step 2: Applying capitalization fixes...
  📝 2025-08-31.json
     • 'Reina em mim' → 'Reina em Mim'

Step 3: Songs that need to be added to database.csv
  ❌ 'New Song Title'
      → Not found in database.csv
      → Suggested action: Add to database.csv with energy and moment tags
```

---

### songbook fix-punctuation

Normalize punctuation differences in history files to match canonical song names.

**Usage:**
```bash
songbook fix-punctuation
```

**What it does:**
- Fixes punctuation variants (commas, hyphens) to match database.csv
- Handles common variations like "Em Espírito, Em Verdade" → "Em Espírito Em Verdade"
- Updates history files in place

**When to use:**
- After running `songbook cleanup` and finding punctuation mismatches
- When importing data with inconsistent punctuation
- As a follow-up to manual history edits

**Note:** This script has a predefined mapping of punctuation variants. Edit the `PUNCTUATION_FIXES` dictionary in `fix_punctuation.py` to add new mappings.

---

### songbook import-history

Import external setlist data and convert it to the internal history format.

**Usage:**
```bash
songbook import-history
```

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

**Data format expected:**
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

**Note:** Only processes entries with `format: "setlist_with_moments"`. Other formats are ignored.

---

## CLI Best Practices

### Error Handling
- All commands validate inputs before processing
- Clear error messages with actionable suggestions
- Position validation (1-indexed user input, 0-indexed internal)

### Path Configuration Priority
1. CLI arguments (highest priority)
2. Environment variables
3. Configuration file (library/config.py)
4. Hardcoded defaults

### Common Workflows

**Generate and review:**
```bash
songbook generate --date 2026-02-15
songbook view-setlist --date 2026-02-15 --keys
```

**Multiple services same day (labels):**
```bash
songbook generate --date 2026-03-01                          # Primary
songbook generate --date 2026-03-01 --label evening          # Derive variant
songbook generate --date 2026-03-01 --label evening --replace 3  # Replace exactly 3
songbook view-setlist --date 2026-03-01 --label evening      # Review variant
songbook pdf --date 2026-03-01 --label evening               # Generate PDF
```

**Replace and regenerate PDF:**
```bash
songbook replace --moment louvor --position 2 --with "Oceanos"
songbook pdf --date 2026-02-15
```

**Data quality maintenance:**
```bash
songbook import-history      # Import external data
songbook cleanup             # Check for issues
songbook fix-punctuation     # Fix punctuation
songbook cleanup             # Verify (should show 0 issues)
```

**Check song statistics:**
```bash
songbook info "Oceanos"              # Recency, history, metadata
```

**Transpose and regenerate outputs:**
```bash
songbook transpose "Oceanos" --to G --save   # Persist to file
songbook markdown --date 2026-02-15          # Regenerate markdown with new chords
songbook pdf --date 2026-02-15               # Regenerate PDF with new chords
```

**Transpose a song:**
```bash
songbook transpose "Oceanos" --to G          # Preview
songbook transpose "Oceanos" --to G --save   # Persist to file
songbook view-song "Oceanos" -t D            # Quick preview via view-song
```

**Preview without saving:**
```bash
songbook generate --date 2026-03-01 --no-save
```

---

## Implementation Notes

### CLI Framework
- Uses Click library for command-line interface
- Subcommands organized in `cli/commands/`
- Entry point: `cli/main.py`

### Command Registration
All commands are registered in `cli/main.py` using Click's group system:
```python
@click.group()
def cli():
    """Setlist generator for church worship services."""
    pass

cli.add_command(generate)
cli.add_command(view_setlist)
# ... etc
```

### Path Resolution
Uses `library/paths.py` module for consistent path handling across all commands.

### User Experience
- Colored output for better readability (when terminal supports it)
- Progress indicators for long-running operations
- Clear success/error messages
- Helpful suggestions when commands fail

---

## Shell Completion

Enable tab completion for commands, song names, moments, and dates:

```bash
# Auto-install (detects your shell)
songbook install-completion

# Or manually specify shell
songbook install-completion --shell bash
songbook install-completion --shell zsh
songbook install-completion --shell fish
```

Then restart your shell or run `source ~/.bashrc` (bash) / `source ~/.zshrc` (zsh).

**What gets completed:**
- Command names (generate, view-song, replace, transpose, etc.)
- Song names (from database.csv)
- Moment names (prelúdio, louvor, ofertório, etc.)
- Musical key names (C, C#, Db, ..., Bm, F#m — for `--to` and `--transpose`)
- Dates (from history directory, including labeled setlists)
- Labels (from history directory filenames)
- Option names (--date, --moment, --with, --to, --label, etc.)

**Completion points:**
- `info SONG_NAME` - autocomplete song names
- `view-song SONG_NAME` - autocomplete song names
- `view-song --transpose` - autocomplete key names
- `transpose SONG_NAME` - autocomplete song names
- `transpose --to` - autocomplete key names
- `replace --moment` - autocomplete moment names
- `replace --with` - autocomplete song names
- All `--date` options - autocomplete available dates from history
- All `--label` options - autocomplete known labels from history

**Features:**
- Case-insensitive song name matching
- Dates sorted by most recent first
- Graceful error handling (no crashes on missing files)
- Respects --history-dir and SETLIST_HISTORY_DIR

**Examples:**
```bash
songbook view-song Oce<TAB>              # Completes to "Oceanos"
songbook replace --moment lou<TAB>       # Completes to "louvor"
songbook view-setlist --date 2025-<TAB>  # Shows all 2025 dates
```

See `.claude/SHELL_COMPLETION.md` for detailed documentation and troubleshooting.