# Shell Completion Guide

This document provides comprehensive documentation for shell completion in the songbook CLI.

## Overview

The songbook CLI supports tab completion for:
- **Commands** - All CLI commands (generate, view-song, replace, etc.)
- **Song names** - Every song in `database.csv`
- **Moment names** - Service moments (prelúdio, louvor, ofertório, saudação, crianças, poslúdio)
- **Musical keys** - For `--to` / `--transpose` (C, C#, Db, …, Bm, F#m)
- **Dates** - Available dates from the history directory (YYYY-MM-DD)
- **Labels** - Labels discovered from filenames in the history directory
- **Options** - All CLI flags and parameters

**Supported shells:** bash, zsh, fish

**Performance:** ~20-50ms completion latency for typical operations

## Installation

### Quick Install (Recommended)

The easiest way to install completion is using the built-in command:

```bash
# Auto-detect shell and install
songbook install-completion

# Or specify shell manually
songbook install-completion --shell bash
songbook install-completion --shell zsh
songbook install-completion --shell fish
```

Then restart your shell or run:
```bash
source ~/.bashrc   # bash
source ~/.zshrc    # zsh
exec fish          # fish
```

### Manual Installation

If you prefer to install manually:

#### Bash

```bash
# Generate completion script
_SONGBOOK_COMPLETE=bash_source songbook > ~/.songbook-complete.bash

# Add to ~/.bashrc
echo 'source ~/.songbook-complete.bash' >> ~/.bashrc

# Activate
source ~/.bashrc
```

#### Zsh

```bash
# Generate completion script
_SONGBOOK_COMPLETE=zsh_source songbook > ~/.songbook-complete.zsh

# Add to ~/.zshrc
echo 'source ~/.songbook-complete.zsh' >> ~/.zshrc

# Activate
source ~/.zshrc
```

#### Fish

```bash
# Generate and install completion script
_SONGBOOK_COMPLETE=fish_source songbook > ~/.config/fish/completions/songbook.fish

# Fish auto-loads completions - just restart
exec fish
```

## Usage Examples

Once installed, you can use TAB completion throughout the CLI:

### Command Completion

```bash
songbook <TAB>
# Shows every registered command: event-type, generate, info, install-completion,
# label, list-moments, markdown, pdf, replace, transpose, view-setlist, view-song,
# youtube (and the developer-only maintenance subcommands).

songbook gen<TAB>
# Completes to: songbook generate
```

### Song Name Completion

```bash
songbook view-song <TAB>
# Shows every song in database.csv, alphabetically

songbook view-song Oce<TAB>
# Completes to: songbook view-song Oceanos

songbook view-song santo<TAB>
# Shows: "Santo Pra Sempre"

# Case-insensitive matching
songbook view-song OU<TAB>
# Completes to: songbook view-song "Ousado Amor"
```

### Moment Name Completion

```bash
songbook replace --moment <TAB>
# Shows: prelúdio louvor ofertório saudação crianças poslúdio

songbook replace --moment lou<TAB>
# Completes to: songbook replace --moment louvor

songbook replace --moment pre<TAB>
# Completes to: songbook replace --moment prelúdio
```

### Date Completion

```bash
songbook view-setlist --date <TAB>
# Shows available dates from history (most recent first):
# 2025-12-28 2025-12-07 2025-11-16 2025-11-09 ...

songbook view-setlist --date 2025-<TAB>
# Shows only 2025 dates

songbook view-setlist --date 2025-12<TAB>
# Shows only December 2025 dates:
# 2025-12-28 2025-12-07

songbook generate --date 2025-11-<TAB>
# Filters to November 2025 dates
```

### Combined Completion

```bash
# Replace command with full completion support
songbook replace --moment <TAB>          # Complete moment
songbook replace --moment louvor --with <TAB>   # Complete song name
songbook replace --moment louvor --with "Oceanos" --date <TAB>  # Complete date
```

## What Gets Completed

### Completion Points

| Command | Parameter | Completion Type | Example |
|---------|-----------|-----------------|---------|
| `info` | `SONG_NAME` | Song names | Oceanos, Hosana |
| `view-song` | `SONG_NAME` | Song names | Oceanos, Hosana |
| `view-song` | `--transpose` / `-t` | Musical keys | G, Bb, F#m |
| `transpose` | `SONG_NAME` | Song names | Oceanos |
| `transpose` | `--to` | Musical keys | G, Bb, F#m |
| `replace` | `--moment` | Moment names | louvor, prelúdio |
| `replace` | `--with` | Song names | Santo Pra Sempre |
| `replace` | `--date` | Dates | 2025-12-25 |
| `replace` | `--label` | Labels | evening |
| `generate` | `--date` | Dates | 2025-11-16 |
| `generate` | `--label` | Labels | evening |
| `view-setlist` | `--date` | Dates | 2025-10-05 |
| `view-setlist` | `--label` | Labels | evening |
| `pdf` | `--date` | Dates | 2025-09-21 |
| `markdown` | `--date` | Dates | 2025-09-21 |
| `youtube` | `--date` | Dates | 2025-09-21 |
| `label` | `--date` | Dates | 2025-09-21 |
| `label` | `--label` | Labels | evening |

### Song Name Completion

- **Source:** `database.csv`
- **Features:**
  - Case-insensitive matching
  - Partial substring matching
  - Alphabetically sorted
- **Example:** "oce" matches "Oceanos", "OU" matches "Ousado Amor"

### Moment Name Completion

- **Source:** `library/config.py` (`MOMENTS_CONFIG`)
- **Values:** `prelúdio`, `louvor`, `ofertório`, `saudação`, `crianças`, `poslúdio`
- **Features:**
  - Case-insensitive matching
  - Exact substring matching

### Musical Key Completion

- **Source:** Static list maintained by `cli/completions.py:complete_key_names`
- **Coverage:** All major and minor roots used in the chord sheets (C, C#, Db, …, Bm, F#m)

### Date Completion

- **Source:** `history/*.json` files (default backend) — for the configured `--history-dir`
- **Format:** YYYY-MM-DD
- **Features:**
  - Sorted descending (most recent first)
  - Prefix filtering (e.g., "2025-12" shows December 2025)
  - Respects `--history-dir` / `SETLIST_HISTORY_DIR`

### Label Completion

- **Source:** Suffixes parsed from `history/YYYY-MM-DD_<label>.json` filenames
- **Use:** Wherever `--label` / `-l` is accepted (`view-setlist`, `generate`, `replace`, `pdf`, `markdown`, `youtube`, `label`)

### Command Completion

- **Source:** Click CLI framework (built-in)
- **Coverage:** Every subcommand registered in `cli/main.py`

## Troubleshooting

### Completion Not Working

**Symptom:** TAB key doesn't show completions

**Solutions:**

1. **Verify installation:**
   ```bash
   # Check if completion script exists
   ls -l ~/.songbook-complete.bash    # bash
   ls -l ~/.songbook-complete.zsh     # zsh
   ls -l ~/.config/fish/completions/songbook.fish  # fish
   ```

2. **Verify rc file has source line:**
   ```bash
   grep songbook ~/.bashrc   # bash
   grep songbook ~/.zshrc    # zsh
   ```

3. **Restart shell:**
   ```bash
   source ~/.bashrc   # bash
   source ~/.zshrc    # zsh
   exec fish          # fish
   ```

4. **Test completion manually:**
   ```bash
   # Bash
   _SONGBOOK_COMPLETE=bash_complete COMP_WORDS="songbook view-song Oce" COMP_CWORD=2 songbook

   # Should output: plain,Oceanos
   ```

### Empty Completion Results

**Symptom:** TAB shows nothing or empty list

**Possible causes:**

1. **Missing database.csv:**
   - Song completion requires database.csv in current directory
   - Run `songbook` from project root

2. **Missing history directory:**
   - Date completion requires history/*.json files
   - Generate at least one setlist first

3. **Permission issues:**
   - Ensure read access to database.csv and history/*.json
   - Check with: `ls -l database.csv history/`

4. **Working directory:**
   - Completion functions use `Path.cwd()` to find files
   - Run `songbook` commands from project root

### Slow Completion

**Symptom:** Noticeable delay when pressing TAB

**Expected latency:** 20-50ms for typical operations

**If slower:**

1. **Check database size:**
   ```bash
   wc -l database.csv
   ```

2. **Check history size:**
   ```bash
   ls -l history/ | wc -l
   ```

3. **Performance should be acceptable up to:**
   - ~200 songs in `database.csv`
   - ~100 history files
   - Beyond that, consider caching optimizations

### Completion Shows Wrong Path

**Symptom:** Date completion shows dates from wrong history directory

**Solution:**

Completion respects --history-dir option and SETLIST_HISTORY_DIR environment variable:

```bash
# Use custom history directory
export SETLIST_HISTORY_DIR=/path/to/custom/history
songbook view-setlist --date <TAB>

# Or use CLI option
songbook view-setlist --history-dir /custom/history --date <TAB>
```

### Accents/Unicode Issues

**Symptom:** Moment names with accents (prelúdio, ofertório) don't complete

**Solution:**

Ensure your shell has UTF-8 encoding enabled:

```bash
# Check current locale
echo $LANG
# Should show: en_US.UTF-8 or similar

# Set UTF-8 if needed (add to ~/.bashrc or ~/.zshrc)
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

## Uninstallation

To remove shell completion:

### Bash

```bash
# Remove completion script
rm ~/.songbook-complete.bash

# Remove source line from ~/.bashrc
# Edit ~/.bashrc and delete the line:
# source /Users/yourname/.songbook-complete.bash
```

### Zsh

```bash
# Remove completion script
rm ~/.songbook-complete.zsh

# Remove source line from ~/.zshrc
# Edit ~/.zshrc and delete the line:
# source /Users/yourname/.songbook-complete.zsh
```

### Fish

```bash
# Remove completion script
rm ~/.config/fish/completions/songbook.fish

# Restart fish
exec fish
```

## Technical Details

### How It Works

1. **Click Framework:** Uses Click 8.3's built-in shell completion system
2. **Environment Variables:** Shell sets `_SONGBOOK_COMPLETE=bash_complete` when TAB is pressed
3. **Completion Functions:** Custom functions in `cli/completions.py` generate suggestions:
   - `complete_song_names()` - Loads `database.csv` and filters by input
   - `complete_moment_names()` - Returns `MOMENTS_CONFIG` keys from `library/config.py`
   - `complete_key_names()` - Returns the static list of supported musical keys
   - `complete_history_dates()` - Globs `history/*.json` files in the configured history dir
   - `complete_history_labels()` - Parses labels from `history/YYYY-MM-DD_<label>.json` filenames
4. **Return Format:** Functions return `CompletionItem` objects
5. **Shell Integration:** Shell-specific scripts parse output and display suggestions

### Error Handling

All completion functions use **graceful degradation:**

```python
try:
    # Load data and generate completions
    ...
except Exception:
    # Return empty list instead of raising exception
    return []
```

**Why:** Completion functions should NEVER crash - they simply return no suggestions on errors. This ensures the CLI remains usable even if completion fails.

### Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Song name completion | ~20ms | Loads `database.csv` (typical 50–100 rows) |
| Moment name completion | <5ms | Static list from config |
| Date completion | ~15ms | Globs the configured history directory |
| Command completion | <5ms | Built-in Click feature |

**Scalability:**
- Database loading: O(n) where n = number of songs
- Song filtering: O(m) where m = matching songs
- Date sorting: O(d log d) where d = number of dates
- Total: O(n + m + d log d) ≈ O(n) for typical workloads

### Dependencies

**Core:**
- Python 3.12+
- Click 8.3+ (already in project)
- Standard library only

**No additional dependencies required.**

## Advanced Usage

### Custom History Directory

Completion respects custom history directories:

```bash
# Environment variable
export SETLIST_HISTORY_DIR=/custom/history
songbook view-setlist --date <TAB>

# CLI option
songbook view-setlist --history-dir /custom/history --date <TAB>
```

### Testing Completion

To test completion functions directly:

```bash
# Generate completion script
_SONGBOOK_COMPLETE=bash_source songbook > /tmp/test-completion.bash

# Source it
source /tmp/test-completion.bash

# Test completion
songbook view-song <TAB>
```

### Debugging Completion

To see raw completion output:

```bash
# Bash
_SONGBOOK_COMPLETE=bash_complete COMP_WORDS="songbook view-song Oce" COMP_CWORD=2 songbook

# Zsh
_SONGBOOK_COMPLETE=zsh_complete COMP_WORDS="songbook view-song Oce" COMP_CWORD=2 songbook

# Fish
_SONGBOOK_COMPLETE=fish_complete COMP_WORDS="songbook view-song Oce" COMP_CWORD=2 songbook
```

### Integration with Other Tools

Completion works seamlessly with:
- **Custom --output-dir / --history-dir:** Completion functions respect CLI options
- **Environment variables:** SETLIST_OUTPUT_DIR and SETLIST_HISTORY_DIR
- **Multiple working directories:** Use `cd` to switch projects; completion uses local files

## FAQ

**Q: Does completion work for all commands?**
A: Yes. Commands are completed by Click (built-in). Song names, moments, and dates use custom completion functions.

**Q: Can I use completion with custom directories?**
A: Yes. Completion respects --output-dir and --history-dir options, plus SETLIST_OUTPUT_DIR and SETLIST_HISTORY_DIR environment variables.

**Q: Does completion work offline?**
A: Yes. All completion data comes from local files (database.csv, history/*.json, config.py).

**Q: What if I have multiple songbook projects?**
A: Completion uses files in the current working directory. Just `cd` to the project directory before using the CLI.

**Q: Can I disable completion?**
A: Yes. Just remove the completion script and source line from your shell's rc file (see Uninstallation section).

**Q: Does it work with command aliases?**
A: No. Shell completion is tied to the command name "songbook". If you create an alias, completion won't work.

**Q: Can I customize completion behavior?**
A: Yes. Edit `cli/completions.py` to modify completion logic. For example, you could filter songs by tag or sort dates differently.

## See Also

- **Project Documentation:** CLAUDE.md
- **CLI Reference:** .claude/rules/cli.md
- **Architecture:** .claude/rules/core-architecture.md
- **Click Completion Docs:** https://click.palletsprojects.com/en/8.1.x/shell-completion/
