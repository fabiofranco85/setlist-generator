# Song Replacement Feature - Implementation Summary

## Overview

Implemented a comprehensive song replacement feature that allows users to replace individual songs in already-generated setlists without regenerating the entire setlist.

## Files Created

### 1. `setlist/replacer.py` (~300 lines)
Core replacement logic module with the following functions:

- **`find_target_setlist()`** - Locates setlist by date (latest or specific)
- **`validate_replacement_request()`** - Validates moment, position, and manual song
- **`select_replacement_song()`** - Auto or manual song selection
- **`replace_song_in_setlist()`** - Single replacement with energy reordering
- **`replace_songs_batch()`** - Multiple replacements at once

### 2. `replace_song.py` (~250 lines)
CLI script providing user-friendly interface for song replacement with:

- Auto-selection mode (system picks best replacement)
- Manual selection mode (user specifies exact song)
- Single or batch replacement support
- Date-specific replacement
- Custom output directory support
- Comprehensive error handling and validation

## Files Modified

### 1. `setlist/__init__.py`
Added exports for all replacer functions

### 2. `README.md`
Added comprehensive "Replacing Songs" section

### 3. `CLAUDE.md`
Added technical documentation for replacement feature

## Key Features

### Two Replacement Modes

**Auto Mode:**
```bash
python replace_song.py --moment louvor --position 2
```

**Manual Mode:**
```bash
python replace_song.py --moment louvor --position 2 --with "Oceanos"
```

### Batch Replacement
```bash
python replace_song.py --moment louvor --positions 1,3
```

### Date-Specific Replacement
```bash
python replace_song.py --date 2026-03-15 --moment louvor --position 2
```

## Testing Results

All test cases passed:

✅ Single auto replacement
✅ Single manual replacement
✅ Batch replacement (multiple positions)
✅ Date-specific replacement
✅ Comprehensive error handling

## Integration

Reuses existing modules:
- `select_songs_for_moment()` - Core selection algorithm
- `apply_energy_ordering()` - Energy-based ordering
- `calculate_recency_scores()` - Time-based decay scoring
- `format_setlist_markdown()` - Markdown generation
- `save_setlist_history()` - JSON history saving
