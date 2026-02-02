# Migration Guide: Unified Songbook CLI

## Overview

The songbook project now provides a unified CLI command (`songbook`) that consolidates all functionality into a single entry point, similar to tools like `git`, `docker`, and `aws-cli`.

## Quick Start

### Installation

```bash
# Install in editable mode (recommended for development)
uv pip install -e .

# Or use pip
pip install -e .
```

This creates a `songbook` command in your PATH.

### Basic Usage

```bash
# Main help
songbook --help

# Command-specific help
songbook generate --help

# Generate a setlist
songbook generate --date 2026-02-15 --pdf

# View setlists
songbook view-setlist --keys
songbook view-song "Oceanos"

# Manage setlists
songbook replace --moment louvor --position 2
songbook pdf --date 2026-02-15
```

## Command Mapping

| Old Script | New Command | Description |
|------------|-------------|-------------|
| `python generate_setlist.py` | `songbook generate` | Generate new setlist |
| `python view_setlist.py` | `songbook view-setlist` | View generated setlist |
| `python view_song.py <name>` | `songbook view-song <name>` | View song details |
| `python replace_song.py` | `songbook replace` | Replace song in setlist |
| `python generate_pdf.py` | `songbook pdf` | Generate PDF |
| `python list_moments.py` | `songbook list-moments` | List moments |
| `python cleanup_history.py` | `songbook cleanup` | Data quality checks |
| `python fix_punctuation.py` | `songbook fix-punctuation` | Fix punctuation |
| `python import_real_history.py` | `songbook import-history` | Import history |

## Example Migrations

### Generate Setlist

**Old way:**
```bash
python generate_setlist.py --date 2026-02-15 --pdf
python generate_setlist.py --override "louvor:Oceanos,Santo Pra Sempre"
```

**New way:**
```bash
songbook generate --date 2026-02-15 --pdf
songbook generate --override "louvor:Oceanos,Santo Pra Sempre"
```

### View Commands

**Old way:**
```bash
python view_setlist.py --keys
python view_song.py "Oceanos"
python list_moments.py
```

**New way:**
```bash
songbook view-setlist --keys
songbook view-song "Oceanos"
songbook list-moments
```

### Replace Songs

**Old way:**
```bash
python replace_song.py --moment louvor --position 2
python replace_song.py --moment louvor --position 2 --with "Oceanos"
```

**New way:**
```bash
songbook replace --moment louvor --position 2
songbook replace --moment louvor --position 2 --with "Oceanos"
```

### PDF Generation

**Old way:**
```bash
python generate_pdf.py --date 2026-02-15
```

**New way:**
```bash
songbook pdf --date 2026-02-15
```

### Maintenance Commands

**Old way:**
```bash
python cleanup_history.py
python fix_punctuation.py
python import_real_history.py
```

**New way:**
```bash
songbook cleanup
songbook fix-punctuation
songbook import-history
```

## Backward Compatibility

### Transition Period

The old scripts continue to work with deprecation warnings:

```bash
$ python generate_setlist.py --date 2026-02-15

DeprecationWarning:
======================================================================
DEPRECATION WARNING
======================================================================
This script is deprecated. Please use 'songbook generate' instead.

Old: python generate_setlist.py [options]
New: songbook generate [options]

This wrapper will be removed in a future version.
======================================================================

Loading songs...
```

### Suppressing Warnings (Not Recommended)

If you need to suppress warnings temporarily:

```bash
python -W ignore::DeprecationWarning generate_setlist.py --date 2026-02-15
```

### Migration Timeline

- **Now - 6 months**: Both interfaces work (old scripts show deprecation warnings)
- **6-12 months**: Old scripts may be removed
- **Action**: Update your scripts and aliases to use `songbook` commands

## Shell Aliases

Update your shell aliases to use the new commands:

```bash
# ~/.bashrc or ~/.zshrc

# Old aliases (remove these)
alias gen-setlist="python generate_setlist.py"
alias view-setlist="python view_setlist.py"

# New aliases
alias gen="songbook generate"
alias view="songbook view-setlist"
alias vsong="songbook view-song"
```

## CI/CD Pipelines

Update your automated scripts:

**Old:**
```bash
#!/bin/bash
python generate_setlist.py --date "$DATE" --pdf --no-save
python view_setlist.py --date "$DATE"
```

**New:**
```bash
#!/bin/bash
songbook generate --date "$DATE" --pdf --no-save
songbook view-setlist --date "$DATE"
```

## Programmatic Usage

The underlying `setlist` package API remains unchanged. If you were importing functions directly, no changes are needed:

```python
# This still works exactly the same
from setlist import load_songs, generate_setlist, load_history
from pathlib import Path

songs = load_songs(Path("."))
history = load_history(Path("./history"))
setlist = generate_setlist(songs, history, "2026-02-15")
```

## Benefits of the New CLI

### Discoverability

```bash
# One command to see all options
songbook --help

# Consistent help system
songbook <command> --help
```

### Consistency

All commands follow the same patterns:
- Common options (`--output-dir`, `--history-dir`) work the same way
- Unified error messages and output formatting
- Professional UX matching industry standards

### Extensibility

Adding new commands is now easier:

1. Create command module in `songbook/commands/`
2. Add command decorator to `songbook/main.py`
3. Done!

## Troubleshooting

### Command not found

```bash
$ songbook --help
songbook: command not found
```

**Solution:** Reinstall the package:
```bash
uv pip install -e .
# or
pip install -e .
```

### Old behavior expected

If you need the exact old behavior temporarily, use the Python scripts directly:

```bash
python generate_setlist.py --date 2026-02-15
```

### Import errors

If you see import errors, ensure Click is installed:

```bash
uv pip install click
# or
pip install click
```

## Questions?

The new CLI is functionally identical to the old scripts - it's just a more convenient interface. All the same options and behaviors are preserved.

For detailed documentation, see:
- `CLAUDE.md` - Full project documentation
- `songbook --help` - CLI help
- `songbook <command> --help` - Command-specific help
