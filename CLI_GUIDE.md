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
  - [label](#label---manage-setlist-labels)
  - [info](#info---song-statistics)
  - [transpose](#transpose---transpose-chords)
  - [list-moments](#list-moments---list-service-moments)
  - [event-type](#event-type---manage-event-types)
- [Output Commands](#output-commands)
  - [pdf](#pdf---generate-pdf-from-setlist)
  - [markdown](#markdown---regenerate-markdown-from-setlist)
  - [youtube](#youtube---create-youtube-playlist)
- [Examples and Workflows](#examples-and-workflows)
- [Data Maintenance Commands](#data-maintenance-commands)
  - [cleanup](#cleanup---check-data-quality)
  - [fix-punctuation](#fix-punctuation---normalize-punctuation)
  - [import-history](#import-history---import-external-data)
- [Troubleshooting](#troubleshooting)
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

# Generate for a specific event type
songbook generate -e youth --date 2026-03-20

# View the latest setlist
songbook view-setlist --keys

# View a specific song
songbook view-song "Oceanos"

# Manage event types
songbook event-type list
songbook event-type add youth --name "Youth Service"

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

**Event Type Generation:**

Generate setlists for different service types (e.g., youth, Christmas):

```bash
# Generate for a specific event type
songbook generate -e youth --date 2026-03-20

# Combine event type with label
songbook generate -e youth --label evening --date 2026-03-20

# Generate with PDF for event type
songbook generate -e youth --pdf
```

When using `-e`, the generator:
- Uses the event type's custom moments config (instead of global `MOMENTS_CONFIG`)
- Filters songs to only include unbound songs + songs bound to that event type
- Saves files to subdirectories (`history/youth/`, `output/youth/`)
- Includes the event type name in markdown header and PDF subtitle

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Service date (default: today) |
| `--event-type TEXT`, `-e` | Event type slug (e.g., "youth"). Uses that type's moments and filters songs |
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
| `--event-type TEXT`, `-e` | Event type slug |
| `--label TEXT`, `-l` | Setlist label |
| `--keys`, `-k` | Show song keys alongside titles |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

---

### `view-song` - View Individual Songs

View a specific song's lyrics and chords without opening files.

**Usage:**

```bash
# Interactive picker (when no song name given)
songbook view-song

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
- **Interactive picker**: When called without a song name, opens a searchable menu (type `/` to search, arrow keys to navigate, `Esc`/`q` to cancel)
- Displays full chord notation and lyrics
- Shows song metadata (tags, energy level)
- Smart search: suggests similar songs if name not found
- List all songs with `--list` flag
- Transpose to any key with `--transpose` (display-only, never modifies files)
- Falls back to a numbered list when the terminal is non-interactive (e.g., piped input)

**Use cases:**
- Quickly reference chords during practice
- Browse and select songs without knowing exact names
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

**Interactive Picker (`--pick`):**

Browse and select a replacement from a searchable menu, filtered to the target moment:

```bash
# Open picker filtered to louvor songs
songbook replace --moment louvor --position 2 --pick
songbook replace --moment louvor --position 2 -p
```

The picker:
- Only shows songs tagged for the target moment
- Excludes songs already in the setlist
- Supports `/` to search, arrow keys to navigate, `Esc`/`q` to cancel
- Cannot be combined with `--with` or `--positions`

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

**Data Updated:**
- `output/YYYY-MM-DD.md` — markdown with chords (always filesystem)
- Setlist history record (filesystem: `history/YYYY-MM-DD.json`; postgres: `setlists` table)

Both are completely regenerated to reflect the updated setlist.

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Target specific date (default: latest) |
| `--event-type TEXT`, `-e` | Event type slug |
| `--label TEXT`, `-l` | Setlist label |
| `--moment MOMENT` | Service moment to modify (required) |
| `--position N` | Position to replace (1-indexed, default: 1) |
| `--positions N,M,..` | Replace multiple positions (auto mode only) |
| `--with "SONG"` | Manual replacement with specific song |
| `--pick`, `-p` | Interactively pick replacement song (single position only) |
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
- Solution: Use `songbook view-setlist` to list available dates, or check `history/` directory (filesystem backend)

---

### `label` - Manage Setlist Labels

Add, rename, or remove labels on existing setlists. Labels allow multiple setlists per date (e.g., morning and evening services). This command safely renames all associated files (history JSON, output markdown) and regenerates the markdown header.

**Add a Label:**

Turn an unlabeled setlist into a labeled one:

```bash
songbook label --date 2026-03-01 --to evening
```

This renames:
- `history/2026-03-01.json` → `history/2026-03-01_evening.json`
- `output/2026-03-01.md` → `output/2026-03-01_evening.md`

**Rename a Label:**

Change an existing label:

```bash
songbook label --date 2026-03-01 --label evening --to night
```

**Remove a Label:**

Strip the label from a setlist, making it unlabeled:

```bash
songbook label --date 2026-03-01 --label evening --remove
```

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Target date (required) |
| `--event-type TEXT`, `-e` | Event type slug |
| `--label TEXT`, `-l` | Source label to operate on (omit for unlabeled) |
| `--to TEXT` | New label to assign |
| `--remove` | Remove the label (make unlabeled) |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

**How It Works:**

1. Validates inputs (`--to` and `--remove` are mutually exclusive; one is required)
2. Loads the source setlist
3. Checks the target label doesn't already exist for the same date
4. **Write-first, delete-second** (crash-safe):
   - Saves new history JSON with updated label
   - Regenerates and saves markdown with updated header
   - Deletes old history JSON
   - Deletes old output files (markdown and PDF if present)
5. If an old PDF was deleted, prints a note suggesting `songbook pdf` to regenerate

**Validation:**
- Labels must be lowercase alphanumeric with hyphens/underscores
- Labels must start with a letter or digit, max 30 characters
- Source and target labels cannot be the same
- Cannot remove a label from an already unlabeled setlist

**Example Workflow:**

```bash
# Generate an unlabeled setlist
songbook generate --date 2026-03-01

# Realize it's for morning service, add a label
songbook label --date 2026-03-01 --to morning

# Generate an evening variant
songbook generate --date 2026-03-01 --label evening

# Rename "evening" to "night"
songbook label --date 2026-03-01 --label evening --to night

# View the renamed setlist
songbook view-setlist --date 2026-03-01 --label night
```

**Troubleshooting:**

**"A setlist already exists for date with label..."**
- The target label is already taken for that date
- Solution: Delete or rename the existing setlist first

**"--remove requires --label"**
- Cannot remove a label from an already unlabeled setlist
- Solution: Use `--label` to specify which labeled setlist to make unlabeled

---

### `info` - Song Statistics

View detailed statistics for any song, including metadata, recency score, and full usage history.

**Usage:**

```bash
# Interactive picker (when no song name given)
songbook info

# View statistics for a specific song
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
- **Interactive picker**: When called without a song name, opens a searchable menu (type `/` to search, arrow keys to navigate, `Esc`/`q` to cancel)
- Shows song key, energy level, and moment tags with weights
- Displays recency score (0.00 = just used, 1.00 = never used / very long ago)
- Lists every date the song was used and in which moment
- Smart search: suggests similar songs if name not found
- Falls back to a numbered list when the terminal is non-interactive

**Use cases:**
- Browse songs and check their statistics without knowing exact names
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
# Show global moments config
songbook list-moments

# Show moments for a specific event type
songbook list-moments -e youth
```

**Options:**

| Option | Description |
|--------|-------------|
| `--event-type TEXT`, `-e` | Event type slug (shows that type's moments instead of global) |

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
- Viewing a specific event type's moments config

---

### `event-type` - Manage Event Types

Manage event types for different service formats (e.g., main Sunday service, youth service, Christmas).

**Subcommands:**

#### `event-type list`

List all configured event types with their moments config.

```bash
songbook event-type list
```

#### `event-type add`

Create a new event type. Copies moments from the default type unless custom moments are set afterward.

```bash
songbook event-type add youth --name "Youth Service"
songbook event-type add youth --name "Youth Service" --description "Friday evening"
```

| Option | Description |
|--------|-------------|
| `<slug>` | Event type slug (required) |
| `--name TEXT` | Display name (required) |
| `--description TEXT` | Description |

#### `event-type edit`

Edit an existing event type's metadata.

```bash
songbook event-type edit youth --name "Friday Youth" --description "Every Friday"
```

| Option | Description |
|--------|-------------|
| `<slug>` | Event type slug (required) |
| `--name TEXT` | New display name |
| `--description TEXT` | New description |

#### `event-type moments`

View or set the moments configuration for an event type.

```bash
# View current moments
songbook event-type moments youth

# Set custom moments
songbook event-type moments youth --set "louvor=5,prelúdio=1,poslúdio=1"
```

| Option | Description |
|--------|-------------|
| `<slug>` | Event type slug (required) |
| `--set "moment=count,..."` | Set moments config (replaces all moments) |

#### `event-type remove`

Remove an event type. Cannot remove the default type (`main`).

```bash
songbook event-type remove youth
```

#### `event-type default`

View or edit the default event type's display name and description.

```bash
# View default type info
songbook event-type default

# Update default type name
songbook event-type default --name "Sunday Worship"
songbook event-type default --description "Main Sunday service"
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New display name for default type |
| `--description TEXT` | New description for default type |

**Slug validation:**
- Lowercase alphanumeric and hyphens only (e.g., `youth`, `christmas-eve`)
- 1-30 characters, must start with a letter or number
- Automatically lowercased on input

**Event Type Workflow:**

```bash
# 1. Create the event type
songbook event-type add youth --name "Youth Service"

# 2. Set custom moments (fewer moments, more louvor)
songbook event-type moments youth --set "louvor=5,prelúdio=1,poslúdio=1"

# 3. Generate setlists
songbook generate -e youth --date 2026-03-20

# 4. View, replace, output
songbook view-setlist -e youth --date 2026-03-20 --keys
songbook replace -e youth --moment louvor --position 2
songbook pdf -e youth --date 2026-03-20
songbook youtube -e youth --date 2026-03-20
```

**Storage:**
- Filesystem: `event_types.json` at project root (auto-created on first access)
- PostgreSQL: `event_types` table

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

The `pdf` command reads the song list from history and uses current chord data. This means if you transpose a song or edit a chord sheet, you can regenerate the PDF without re-running the selection algorithm.

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
| `--event-type TEXT`, `-e` | Event type slug |
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

The `markdown` command reads the song list from history and uses current chord data. This means if you transpose a song or edit a chord sheet, you can regenerate the markdown without re-running the selection algorithm.

**Use cases:**
- Update setlist after transposing a song
- Regenerate after editing chord files
- Fix formatting issues without changing song selection

**Options:**

| Option | Description |
|--------|-------------|
| `--date YYYY-MM-DD` | Regenerate markdown for specific date (default: latest) |
| `--event-type TEXT`, `-e` | Event type slug |
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

1. Reads setlist from history (via the configured storage backend)
2. Extracts YouTube video IDs from the song database
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
| `--event-type TEXT`, `-e` | Event type slug |
| `--label TEXT`, `-l` | Setlist label |
| `--output-dir DIR` | Custom output directory |
| `--history-dir DIR` | Custom history directory |

**Troubleshooting:**

- **Missing credentials**: See YOUTUBE.md for OAuth setup
- **Song missing URL**: Add YouTube URL to database.csv (fourth column)
- **Invalid URL**: Must be valid YouTube URL (youtube.com/watch?v=... or youtu.be/...)

---

## Examples and Workflows

### Regular Sunday Service

```bash
# Generate markdown only
songbook generate --date 2026-02-15

# Generate markdown + PDF
songbook generate --date 2026-02-15 --pdf
```

### Themed Service (Prayer Focus)

Force prayer-focused songs:

```bash
songbook generate \
  --date 2026-02-22 \
  --override "louvor:Lugar Secreto,Mais Que Uma Voz,Jesus Em Tua Presença"
```

The system will:
- Use your 3 specified louvor songs **in the exact order you provided**
- Pick 1 more louvor song automatically (sorted by energy with other auto-selected songs)
- Fill all other moments with smart selection

### Special Music Request

Someone requested "Oceanos" for their birthday:

```bash
songbook generate \
  --date 2026-03-01 \
  --override "louvor:Oceanos"
```

The system ensures Oceanos is included while selecting 3 other louvor songs automatically.

### Preview Next Month

Plan ahead without affecting history:

```bash
songbook generate --date 2026-03-15 --no-save
```

Review the output, and if you don't like it, run again for a different selection. When satisfied, run without `--no-save`.

### Back-to-Back Services

Generate multiple services:

```bash
songbook generate --date 2026-02-15
songbook generate --date 2026-02-22
songbook generate --date 2026-03-01
```

Each service will automatically avoid songs used in previous services.

### Planning Multiple Services (Batch)

```bash
# Plan next 4 Sundays
for date in 2026-02-01 2026-02-08 2026-02-15 2026-02-22; do
  songbook generate --date $date
done

# Review all setlists
songbook view-setlist --date 2026-02-01
songbook view-setlist --date 2026-02-08
```

### Event-Type-Specific Service

Generate setlists for a youth service with a custom moments config:

```bash
# Set up the event type (one-time)
songbook event-type add youth --name "Youth Service"
songbook event-type moments youth --set "louvor=5,prelúdio=1,poslúdio=1"

# Generate setlist
songbook generate -e youth --date 2026-03-20

# View, replace, generate PDF
songbook view-setlist -e youth --date 2026-03-20 --keys
songbook replace -e youth --moment louvor --position 3
songbook pdf -e youth --date 2026-03-20
```

Output files are saved to subdirectories:
- `history/youth/2026-03-20.json`
- `output/youth/2026-03-20.md`
- `output/youth/2026-03-20.pdf`

### Multiple Services on the Same Day (Labels)

When you have morning and evening services on the same date:

```bash
# Generate the primary (morning) setlist
songbook generate --date 2026-03-01

# Derive an evening variant (replaces some songs automatically)
songbook generate --date 2026-03-01 --label evening

# Derive replacing exactly 3 songs
songbook generate --date 2026-03-01 --label evening --replace 3

# Derive replacing all songs
songbook generate --date 2026-03-01 --label evening --replace all
```

This creates two separate files:
- `history/2026-03-01.json` (primary/morning)
- `history/2026-03-01_evening.json` (evening variant)

View or manage labeled setlists by adding `--label`:
```bash
songbook view-setlist --date 2026-03-01 --label evening
songbook replace --moment louvor --position 2 --date 2026-03-01 --label evening
songbook pdf --date 2026-03-01 --label evening
```

Rename or remove labels after creation:
```bash
songbook label --date 2026-03-01 --label evening --to night  # Rename
songbook label --date 2026-03-01 --label night --remove      # Remove
```

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

## Troubleshooting

### Problem: Song not appearing in setlists

**Possible causes:**

1. **Song was recently used**
   - Check recent usage with `songbook info "Song Name"`
   - Songs used within the last 30-45 days are heavily penalized
   - Use `--override` to force it if needed

2. **Tag/weight issue**
   - Verify song is in `database.csv`
   - Check if weight is too low (try increasing to 4-5)

3. **Wrong moment tag**
   - Ensure the moment tag matches: `prelúdio`, `ofertório`, `saudação`, `crianças`, `louvor`, `poslúdio`

4. **Not enough songs in that moment**
   - Check if you have enough songs tagged for that moment in `database.csv`

### Problem: Error "File not found: chords/Song.md"

The song is in `database.csv` but the chord file is missing or misnamed.

**Solution:**
- Create `chords/Song Name.md` with exact spelling
- Check for typos in file name vs. `database.csv` entry
- Ensure file extension is `.md` not `.txt`

### Problem: Same songs appearing repeatedly

**Solutions:**

1. **Increase recency decay period** in `library/config.py`:
   ```python
   RECENCY_DECAY_DAYS = 60  # Instead of 45 (slower cycling)
   # Or even 90 for maximum variety
   ```

2. **Add more songs** to `database.csv` for variety

3. **Adjust weights** - lower weights on overused songs:
   ```csv
   # Before
   Oceanos;3;louvor(5)

   # After
   Oceanos;3;louvor(3)
   ```

### Problem: Too many/few songs for a moment

Edit `MOMENTS_CONFIG` in `library/config.py`:

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

Edit `library/config.py`:
```python
ENERGY_ORDERING_ENABLED = False
```

Or if energy classifications seem wrong, update individual songs in `database.csv`:
```csv
# Before
Hosana;1;louvor  # Classified as upbeat (wrong!)

# After
Hosana;3;louvor  # Corrected to reflective (right!)
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
songbook generate --date 2026-02-15
```

### Problem: Encoding errors (special characters)

This project uses UTF-8 encoding for Portuguese characters (ã, ç, é, etc.).

Ensure your editor/terminal supports UTF-8:
- VSCode: Check bottom-right corner shows "UTF-8"
- Terminal: Should support UTF-8 by default on macOS/Linux

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
