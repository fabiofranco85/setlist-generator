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
songbook --verbose <command>         # Enable debug logging (also -v)
songbook generate --date 2026-02-15  # Generate setlist
songbook generate --label evening    # Derive labeled variant from primary
songbook generate --label evening --replace 3  # Derive replacing 3 songs
songbook generate -e youth           # Generate for event type
songbook view-setlist --keys         # View setlist with keys
songbook view-setlist --label evening  # View labeled setlist
songbook view-song "Oceanos"         # View song details
songbook view-song                   # Interactive song picker
songbook info "Oceanos"              # Song statistics and history
songbook info                        # Interactive picker → statistics
songbook edit "Oceanos"              # Open chord file in $EDITOR (default: vim)
songbook edit                        # Interactive picker → editor
songbook replace --moment louvor --position 2  # Replace song (re-applies energy order)
songbook replace --moment louvor --position 2 --pick  # Interactive picker
songbook replace --moment louvor --position 2 --keep-position  # Pin to position, no reorder
songbook replace --moment louvor --position 2 --label evening  # Replace in labeled
songbook remove --moment louvor --position 2  # Remove a single song from a setlist
songbook remove --moment crianças --all       # Remove an entire moment (all songs)
songbook label --date 2026-03-01 --to evening  # Add label to setlist
songbook label --date 2026-03-01 --label evening --to night  # Rename label
songbook delete --date 2026-02-15 --yes  # Delete a setlist (skip confirmation)
songbook delete --date 2026-03-01 -l evening --yes  # Delete a labeled variant
songbook weights                     # Interactive weights editor (pick moment, then song)
songbook weights --moment louvor     # Jump straight to the louvor weights table
songbook transpose "Oceanos" --to G  # Transpose chords (preview)
songbook view-song "Oceanos" -t G    # View transposed (display-only)
songbook pdf --date 2026-02-15       # Generate PDF (with chords)
songbook pdf --date 2026-02-15 --no-chords  # Lyrics-only PDF (singers/non-musicians)
songbook pdf --label evening         # Generate PDF for labeled setlist
songbook markdown --date 2026-02-15  # Regenerate markdown from history
songbook youtube --date 2026-02-15   # Create YouTube playlist from setlist
songbook list-moments                # List available moments
songbook list-moments -e youth       # List moments for event type
songbook event-type list             # List event types
songbook event-type add youth --name "Youth Service"  # Add event type
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

# Also generate a lyrics-only PDF variant (no chords) for singers
songbook generate --date 2026-02-15 --pdf --no-chords

# Generate for a specific event type
songbook generate -e youth --date 2026-03-20
songbook generate --event-type youth --pdf

# Derive labeled variant (from existing primary setlist)
songbook generate --date 2026-03-01 --label evening
songbook generate --label evening --replace 3      # Replace exactly 3 songs
songbook generate --label evening --replace all    # Replace all songs

# Combine event type + label
songbook generate -e youth --label evening --date 2026-03-20

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
- `--event-type TEXT` or `-e` - Event type slug (e.g., "youth"). Uses the type's moments config and filters songs
- `--label TEXT` or `-l` - Setlist label for multiple setlists per date (e.g., "evening", "morning")
- `--replace N` or `-r` - Songs to replace when deriving (number or "all", default: random). Only valid with `--label`
- `--override "moment:song1,song2"` - Force specific songs for a moment (can be used multiple times)
- `--pdf` - Generate PDF output in addition to markdown
- `--no-chords` - When combined with `--pdf`, generate a lyrics-only PDF (no chord lines, no key suffixes) for non-musicians. Filename gets a `_lyrics` suffix
- `--no-save` - Dry run mode, don't save to history
- `--output PATH` - Custom output filename for the markdown file
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

**Event type behavior:**
- When `-e youth` is specified, uses the youth event type's moments config and filters songs
- Output files route to `output/youth/` and `history/youth/` subdirectories
- Event type name appears in markdown header, PDF subtitle, and YouTube playlist title
- Event type and label are orthogonal — can be combined freely

**Output:**
- Terminal: Summary with song titles
- `output/[<event-type>/]YYYY-MM-DD[_label].md`: Full markdown with chords (subdirectory for non-default types)
- `output/[<event-type>/]YYYY-MM-DD[_label].pdf`: PDF setlist (if `--pdf` flag used)
- History record saved to configured backend (unless `--no-save`)

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

# View an event-type-specific setlist
songbook view-setlist --date 2026-03-20 -e youth

# View with song keys
songbook view-setlist --keys
songbook view-setlist --date 2026-02-15 --keys

# Custom history directory
songbook view-setlist --history-dir custom/history
```

**Options:**
- `--date YYYY-MM-DD` - View specific date (default: latest)
- `--event-type TEXT` or `-e` - Event type slug
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

View a specific song's lyrics, chords, and metadata. When called without a song name, opens an interactive picker.

**Usage:**
```bash
# Interactive picker (when no song name given)
songbook view-song

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
- Interactive picker when called without a song name (searchable menu with `/`, arrow keys, `Esc` to cancel)
- Falls back to numbered list when terminal is non-interactive
- Smart search: If song not found, suggests similar songs based on partial name match
- Fuzzy matching for typos and partial names
- Transposition preserves chord-lyric column alignment
- Minor/major quality inferred from original key (e.g., `--transpose G` on a Bm song transposes to Gm)

---

### songbook info

Show detailed statistics for a song: metadata, recency score, and full usage history. When called without a song name, opens an interactive picker.

**Usage:**
```bash
# Interactive picker (when no song name given)
songbook info

# View statistics for a song
songbook info "Oceanos"

# Fuzzy search on partial match
songbook info "ocean"
```

**Arguments:**
- `SONG_NAME` - Optional. Name of the song to look up (supports tab completion). Opens interactive picker if omitted.

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

### songbook edit

Open a song's chord file in the editor of your choice — saving the time of
finding `chords/<Song>.md` and opening it manually.

**Usage:**
```bash
# Interactive picker (when no song name given)
songbook edit

# Edit a specific song
songbook edit "Oceanos"

# Override the editor for this invocation
songbook edit "Oceanos" --editor nano
songbook edit "Oceanos" --editor "code --wait"

# Use environment variables (standard Unix convention)
EDITOR=nano songbook edit "Oceanos"
VISUAL=vim songbook edit "Oceanos"
```

**Arguments:**
- `SONG_NAME` - Optional. Title of the song to edit (supports tab completion). Opens the interactive picker if omitted.

**Options:**
- `--editor TEXT` - Editor command (may include flags, e.g. `"code --wait"`). Overrides `$VISUAL` and `$EDITOR`. Default: `vim`.

**Editor resolution priority:**
1. `--editor` CLI option
2. `$VISUAL` environment variable
3. `$EDITOR` environment variable
4. `vim`

**Behavior:**
- **Filesystem backend (default):** Opens `chords/<title>.md` *in place*. After the editor exits, the song cache is invalidated so subsequent commands (`view-song`, `transpose`, `pdf`, ...) immediately see the changes.
- **Other backends (postgres, supabase):** Round-trips the current content through a temporary file, then writes it back via `repos.songs.update_content()`.
- **Missing chord file:** If the song exists in `database.csv` but has no chord file yet, a stub `### Title ()\n\n` heading is created so the editor opens on a real file. The CLI prints a "Created" notice in that case.
- **No changes:** If the file is saved unchanged, the CLI prints `No changes made.` and exits cleanly.
- **Unknown editor:** If the editor command is not on `PATH`, the CLI prints a helpful error and exits with status 1.

**GUI editors auto-block:**
GUI editors detach from the terminal by default — their CLI binary tells an
existing window to open the file and exits immediately. Without a wait flag
the CLI would interpret that immediate exit as "no changes" before the user
could type a single character. To fix this, `edit` auto-injects the
appropriate wait flag (`--wait` for VS Code-family editors, `-w` for
TextMate) for the following known editors:

| Editor command           | Injected flag |
|--------------------------|---------------|
| `cursor`                 | `--wait`      |
| `code`, `code-insiders`  | `--wait`      |
| `windsurf`, `zed`        | `--wait`      |
| `subl` (Sublime Text)    | `--wait`      |
| `atom`                   | `--wait`      |
| `mate` (TextMate)        | `-w`          |

When a GUI editor is launched, the CLI prints "Opening `<file>` in `<editor>`.
Close the editor tab/window to continue..." so it's obvious the CLI is
blocked on the editor.

If you already pass a wait flag (or a synonym like `-w` / `-W`) the CLI
won't double-inject it:

```bash
songbook edit "Oceanos" --editor "code --wait --new-window"  # respected as-is
songbook edit "Oceanos" --editor "cursor"                    # → "cursor --wait" automatically
```

Editors not in the list (vim, nano, emacs, …) are left untouched, since
they already block on the terminal.

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

### songbook weights

Interactively edit the per-moment weight of songs.

A song's weight for a moment drives the selection scoring formula
(`score = weight × (recency + 0.1) + random(0, 0.5)`), so raising a song's
weight makes the generator pick it more often for that moment without
removing it from rotation.

**Usage:**
```bash
# Interactive flow: pick a moment, then edit weights for songs tagged in it
songbook weights

# Skip the moment picker
songbook weights --moment louvor
songbook weights -m louvor

# Filter the song pool by event type (uses that type's moments config too)
songbook weights -m louvor -e youth
```

**Options:**
- `--moment TEXT` or `-m` — Pre-select a moment slug (e.g. `louvor`). When
  omitted, the command opens a moment picker.
- `--event-type TEXT` or `-e` — Event type slug. Filters which songs are
  visible (unbound songs are always visible; bound songs only appear when
  the event type matches) and resolves the moments config from that event
  type.

**Flow:**
1. The command lists moments. The user picks one (or `--moment` skips this
   step).
2. The command queries `repos.songs.get_all()`, filters to songs tagged for
   the chosen moment (and bound to the chosen event type, if any), and
   shows a searchable table with each song's current weight, sorted by
   weight descending (then alphabetical).
3. The user picks a row → the CLI prompts for a new integer weight
   (1-10, blank to cancel). Out-of-range or non-integer input re-prompts
   in the same loop.
4. The new weight is saved immediately through `repos.songs.update_tags`.
   The menu re-opens with the refreshed weight ordering until the user
   hits `Esc` / `q`.

**Save semantics:**
- Save-on-each-edit. Every confirmed weight change is committed
  synchronously before the menu re-opens, so closing the terminal or
  hitting `Ctrl+C` never loses prior edits.
- Edits are full-replacement on the song's tag set: the command reads the
  song's current tags, swaps the target moment's weight, and writes the
  whole dict back. Other moments on the same song are preserved.

**Scope (not supported):**
- Adding a song to a moment it isn't tagged for yet. The picker only shows
  songs that already have a tag for the chosen moment. To add a tag, edit
  the song's row in `database.csv` (filesystem backend) or insert into
  `song_tags` directly (Postgres/Supabase).
- Bulk edits across moments. Each invocation operates on one moment.

**Non-interactive mode:**
When stdin/stdout aren't a TTY (CI, redirected input, etc.), the command
falls back to a numbered list and prompts. It exits after a single save —
no infinite loop — to keep automation predictable.

---

### songbook replace

Replace songs in a previously generated setlist.

**Usage:**
```bash
# Auto-select replacement for position 2 in louvor
songbook replace --moment louvor --position 2

# Interactive picker filtered to louvor songs
songbook replace --moment louvor --position 2 --pick
songbook replace --moment louvor --position 2 -p

# Manual replacement with specific song
songbook replace --moment louvor --position 2 --with "Oceanos"

# Replace multiple positions (auto mode)
songbook replace --moment louvor --positions 1,3

# Replace for specific date
songbook replace --date 2026-03-15 --moment louvor --position 2

# Replace in a labeled setlist
songbook replace --moment louvor --position 2 --date 2026-03-01 --label evening

# Replace in an event-type-specific setlist
songbook replace --moment louvor --position 2 -e youth

# Pin replacement to the requested position (skip energy reorder)
songbook replace --moment louvor --position 3 --keep-position
```

**Options:**
- `--moment MOMENT` - Required: Service moment (prelúdio, ofertório, saudação, crianças, louvor, poslúdio)
- `--position N` - Position to replace (1-indexed, default: 1)
- `--positions N,N` - Multiple positions (comma-separated). Cannot be used with `--position`
- `--with SONG` - Manual replacement song (auto-select if omitted)
- `--pick` or `-p` - Interactively pick replacement song (single position only, cannot combine with `--with` or `--positions`)
- `--keep-position` - Skip energy reordering after replacement; the new song stays at the exact requested position
- `--date YYYY-MM-DD` - Target date (default: latest)
- `--event-type TEXT` or `-e` - Event type slug
- `--label TEXT` or `-l` - Setlist label
- `--output-dir PATH` - Custom output directory
- `--history-dir PATH` - Custom history directory

**Behavior:**
- **Auto mode** (no `--with`, no `--pick`): System selects the best available song based on recency and weights, then reapplies energy ordering so the moment stays in its emotional arc. The new song's final position is dictated by its energy — when that differs from the requested position, the CLI prints a "moved to position N" note. Pass `--keep-position` to pin the new song to the exact requested position.
- **Pick mode** (`--pick`): Opens a searchable menu filtered to the target moment, excluding songs already in the setlist. Once the user selects a song, the explicit pick wins: **energy ordering is skipped and the new song lands at the exact requested position**.
- **Manual mode** (`--with "Song"`): Uses the specified song (validates existence and moment tag). Same as pick mode, the explicit choice wins: **energy ordering is skipped and the new song lands at the exact requested position**.
- **(NEW) marker**: Tracks the new song's *title*, not its position. After energy reordering, the marker follows the song — it never lands on whichever song was bumped into the requested slot.
- **Batch mode** (`--positions`): Always auto (`--with` is rejected for multi-position batches). Energy reorder applies unless `--keep-position` is passed.

**Note:** When neither `--position` nor `--positions` is specified, defaults to position 1.

---

### songbook remove

Remove a song or an entire moment from an existing setlist.

**Usage:**
```bash
# Remove a single song at position 2 of louvor
songbook remove --moment louvor --position 2

# Remove the entire moment (all songs in it)
songbook remove --moment crianças --all

# Operate on a labeled setlist
songbook remove --moment louvor --position 1 --label evening

# Operate on an event-type setlist
songbook remove --moment ofertório --all -e youth --date 2026-03-20

# Operate on a specific date (default: latest)
songbook remove --moment louvor --position 3 --date 2026-02-15
```

**Options:**
- `--moment MOMENT` — Required: moment slug to operate on (must exist in the target setlist; not constrained to the moments_config because old setlists may carry moments no longer configured).
- `--position N` — 1-indexed position of the song to remove. Mutually exclusive with `--all`. Exactly one of the two is required.
- `--all` — Remove the entire moment (all its songs) and drop the moment key from the setlist.
- `--date YYYY-MM-DD` — Target date (default: latest).
- `--label TEXT` or `-l` — Setlist label.
- `--event-type TEXT` or `-e` — Event type slug.
- `--output-dir PATH` — Custom output directory.
- `--history-dir PATH` — Custom history directory.

**Behavior:**
- **Single-song removal** (`--position N`): drops the song at position N (1-indexed).
- **Cascade rule**: if `--position` removes the *last* song in its moment, the moment itself is dropped from the setlist — empty moments are not a valid stored state, and the CLI prints a heads-up so this doesn't surprise you.
- **Whole-moment removal** (`--all`): drops every song in the moment plus the moment key.
- **No reordering / no algorithm**: removal is purely structural. Energy ordering is not re-applied (there's nothing to balance), and the recency system is unaffected because the change applies to a stored setlist, not to the song database.
- **History is the source of truth**: history JSON is overwritten first, then markdown is regenerated. If markdown regeneration fails for any reason, the history JSON is still correct.
- **PDF staleness**: if a PDF exists for the setlist, it is **not** auto-deleted — the CLI prints a notice that it's stale so you can regenerate via `songbook pdf`. The hint always names the resolved date explicitly (never the user's original `--date` flag), because by the time the user runs the suggested command, "latest" may resolve to a different setlist than the one that was just modified. The PDF is intentionally left in place because the user may have already printed or shared it; overwriting an opened file is worse than leaving a stale one. (Note: `songbook replace` mutates setlists too but does **not** currently emit this notice — `remove` is more communicative on purpose.)
- **Empty setlists are allowed**: if every moment is removed, the setlist is saved with `"moments": {}`. Use `songbook delete` to discard it.
- **Validation errors** (missing setlist, unknown moment, position out of range, conflicting `--position`/`--all`) exit non-zero before any file is touched.

**Routing:**
- Labeled setlists round-trip through `<setlist_id>_<label>.json`.
- Event-type setlists route through `history/<event-type>/` and `output/<event-type>/` subdirectories — the same routing every other setlist command uses.

---

### songbook label

Add, rename, or remove a setlist label.

**Usage:**
```bash
# Add label to an unlabeled setlist
songbook label --date 2026-03-01 --to evening

# Rename an existing label
songbook label --date 2026-03-01 --label evening --to night

# Remove a label (make unlabeled)
songbook label --date 2026-03-01 --label evening --remove

# Label an event-type-specific setlist
songbook label --date 2026-03-20 -e youth --to evening
```

**Options:**
- `--date YYYY-MM-DD` - Required: Target date
- `--event-type TEXT` or `-e` - Event type slug
- `--label TEXT` or `-l` - Source label (omit for unlabeled setlist)
- `--to TEXT` - New label to assign
- `--remove` - Remove the label (make unlabeled)
- `--output-dir PATH` - Custom output directory
- `--history-dir PATH` - Custom history directory

**Behavior:**
- `--to` and `--remove` are mutually exclusive; one is required
- Renames both history JSON and output markdown files
- Regenerates markdown with the new label in the header
- If the old setlist had a PDF, it is removed with a note to regenerate
- **Crash-safe ordering**: new files are written before old files are deleted
- Labels are validated: lowercase alphanumeric, hyphens, underscores, max 30 chars
- Errors if the target label already exists for the same date

---

### songbook delete

Delete a setlist's history record and all output files.

**Usage:**
```bash
# Prompt to confirm, then delete
songbook delete --date 2026-02-15

# Skip the confirmation prompt
songbook delete --date 2026-02-15 --yes
songbook delete --date 2026-02-15 -y

# Delete a labeled variant (leaves the unlabeled primary untouched)
songbook delete --date 2026-03-01 --label evening --yes

# Delete an event-type setlist
songbook delete --date 2026-03-20 -e youth --yes
```

**Options:**
- `--date YYYY-MM-DD` — **Required.** Target date. There is no "latest"
  default for delete — that would make accidentally nuking the most recent
  service one tab-complete away.
- `--label TEXT` or `-l` — Setlist label (omit for the unlabeled primary).
- `--event-type TEXT` or `-e` — Event type slug.
- `--yes` or `-y` — Skip the confirmation prompt.
- `--output-dir PATH` — Custom output directory.
- `--history-dir PATH` — Custom history directory.

**Behavior:**
- Removes the history JSON record.
- Removes every output variant tied to the setlist: `<setlist_id>.md`,
  `<setlist_id>.pdf`, and `<setlist_id>_lyrics.pdf` (the lyrics-only
  variant produced by `--no-chords`).
- Routes through the event-type subdirectory the same way every other
  setlist command does — `history/youth/2026-03-20.json` for non-default
  event types.
- **Labels and event types are independent** — deleting the unlabeled
  primary leaves `2026-02-15_evening.md` and friends alone, and vice
  versa. The deletion key is the full setlist_id, not the date prefix.
- **Confirmation prompt** is the default for safety: deletion is
  destructive and unreviewable. Pass `--yes` to scripts/automation.
- Errors with a clear message if no matching setlist exists; the
  filesystem is not touched in that case.

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

# Generate PDF for an event-type-specific setlist
songbook pdf --date 2026-03-20 -e youth

# Generate a lyrics-only PDF (singers/non-musicians)
songbook pdf --date 2026-02-15 --no-chords
```

**Options:**
- `--date YYYY-MM-DD` - Target date (default: latest)
- `--event-type TEXT` or `-e` - Event type slug
- `--label TEXT` or `-l` - Setlist label
- `--no-chords` - Generate a lyrics-only PDF (chord lines stripped, no key suffix in titles or TOC); written with a `_lyrics` filename suffix so it coexists with the regular PDF
- `--output-dir PATH` - Custom output directory
- `--history-dir PATH` - Custom history directory

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

# Regenerate for an event-type-specific setlist
songbook markdown --date 2026-03-20 -e youth
```

**Options:**
- `--date YYYY-MM-DD` - Target date (default: latest)
- `--event-type TEXT` or `-e` - Event type slug
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

# Create playlist for an event-type-specific setlist
songbook youtube --date 2026-03-20 -e youth
```

**Options:**
- `--date YYYY-MM-DD` - Target date (default: latest)
- `--event-type TEXT` or `-e` - Event type slug
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
# Show global moments config
songbook list-moments

# Show moments for a specific event type
songbook list-moments -e youth
songbook list-moments --event-type youth
```

**Options:**
- `--event-type TEXT` or `-e` - Event type slug (shows that type's moments config instead of global)

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

### songbook event-type

Manage event types for different service formats.

**Usage:**
```bash
# List all event types
songbook event-type list

# Add a new event type
songbook event-type add youth --name "Youth Service"
songbook event-type add youth --name "Youth Service" --description "Friday evening"

# Edit an existing event type
songbook event-type edit youth --name "Friday Youth" --description "Every Friday"

# Configure moments for an event type
songbook event-type moments youth                              # View current moments
songbook event-type moments youth --set "louvor=5,prelúdio=1,poslúdio=1"  # Set moments

# Remove an event type (cannot remove default)
songbook event-type remove youth

# View/edit the default event type
songbook event-type default                              # Show default type info
songbook event-type default --name "Sunday Worship"      # Update default name
songbook event-type default --description "Main service" # Update default description
```

**Subcommands:**

- `list` - Display all configured event types with their moments
- `add <slug>` - Add a new event type (copies moments from default unless `--moments` specified)
  - `--name TEXT` - Required: Display name
  - `--description TEXT` - Optional: Description
- `edit <slug>` - Edit an existing event type
  - `--name TEXT` - New display name
  - `--description TEXT` - New description
- `moments <slug>` - View or set moment configuration
  - `--set "moment=count,..."` - Set moments (replaces all moments)
- `remove <slug>` - Remove an event type (cannot remove the default type)
- `default` - View or edit the default event type
  - `--name TEXT` - New display name for default type
  - `--description TEXT` - New description for default type

**Slug validation:**
- Lowercase alphanumeric and hyphens only (e.g., `youth`, `christmas-eve`)
- 1-30 characters, must start with a letter or number
- Automatically lowercased on input

**Notes:**
- The default event type (`main`) cannot be removed
- New event types copy the default type's moments config unless `--set` is used with `moments`
- Event types are stored in `event_types.json` (filesystem) or `event_types` table (PostgreSQL)

> **Note on maintenance commands.** The legacy `cleanup`, `fix-punctuation`, and `import-history` subcommands are documented in `.claude/rules/data-maintenance.md` for developer context. They are currently broken at runtime (helper modules are missing from the repo) and are not surfaced to end users.

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
songbook label --date 2026-03-01 --label evening --to night  # Rename label
songbook pdf --date 2026-03-01 --label night                 # Generate PDF
songbook delete --date 2026-03-01 --label night --yes        # Discard the variant
```

**Discard a stale setlist:**
```bash
songbook delete --date 2026-02-15                            # Prompts to confirm
songbook delete --date 2026-02-15 --yes                      # Skip prompt
```

**Replace and regenerate PDF:**
```bash
songbook replace --moment louvor --position 2 --with "Oceanos"
songbook pdf --date 2026-02-15
```

**Remove a song or moment from a setlist:**
```bash
songbook remove --moment louvor --position 2                    # Drop one louvor song
songbook remove --moment crianças --all                         # Drop the entire moment
songbook pdf --date 2026-02-15                                   # Refresh the (now stale) PDF
```

**Event type workflows:**
```bash
songbook event-type add youth --name "Youth Service"          # Create event type
songbook event-type moments youth --set "louvor=5,prelúdio=1" # Set custom moments
songbook generate -e youth --date 2026-03-20                  # Generate
songbook view-setlist -e youth --date 2026-03-20 --keys       # Review
songbook pdf -e youth --date 2026-03-20                       # Generate PDF
songbook replace -e youth --moment louvor --position 2        # Replace song
```

**Check song statistics:**
```bash
songbook info                        # Interactive picker → statistics
songbook info "Oceanos"              # Recency, history, metadata
```

**Edit chords/lyrics and refresh outputs:**
```bash
songbook edit "Oceanos"                      # Open chords/Oceanos.md in $EDITOR
songbook markdown --date 2026-02-15          # Regenerate markdown with new chords
songbook pdf --date 2026-02-15               # Regenerate PDF with new chords
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

### Top-level Options

- `--verbose` / `-v` (on the `songbook` group itself, before the subcommand) - Switch the observability log level from WARNING to DEBUG. Threaded into `replace` and `generate` via `ctx.obj["verbose"]`. See `.claude/rules/observability.md` for the underlying ports-and-adapters layer.
- `--version` - Print the songbook version.

```bash
songbook -v generate --date 2026-02-15   # Verbose generation
songbook --verbose replace --moment louvor --position 2
```

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
- `edit SONG_NAME` - autocomplete song names
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