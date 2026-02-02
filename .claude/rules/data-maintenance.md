---
paths:
  - "songbook/commands/maintenance.py"
  - "migrate_folders.py"
  - "test_*.py"
---

# Data Maintenance Utilities

This document describes the data quality and maintenance tools available in the project. This documentation is loaded when working on maintenance scripts.

## Overview

The project includes several utility scripts for maintaining data quality and importing external data. These tools help ensure consistency between the song database and historical performance records.

## songbook cleanup

**Purpose:** Automated data quality checker and fixer for history files.

**Module:** `songbook/commands/maintenance.py` (cleanup command)

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

**Usage:**
```bash
songbook cleanup
```

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

### Implementation Details

**Algorithm:**
1. Load canonical song names from `database.csv`
2. Scan all `history/*.json` files
3. For each song in history:
   - Check exact match with database
   - If no match, try case-insensitive match (capitalization fix)
   - If still no match, mark as missing and suggest similar songs (fuzzy matching)
4. Create timestamped backup of history directory
5. Apply capitalization fixes to history files
6. Report missing songs to user

**Backup Strategy:**
- Creates `history_backup_YYYYMMDD_HHMMSS/` directory
- Copies all history files before making changes
- Preserves original state for rollback if needed

**Fuzzy Matching:**
Uses string similarity (difflib) to suggest similar song names:
```python
from difflib import get_close_matches

suggestions = get_close_matches(
    missing_song,
    canonical_songs,
    n=3,          # Top 3 suggestions
    cutoff=0.6    # 60% similarity threshold
)
```

---

## fix-punctuation

**Purpose:** Normalize punctuation differences in history files to match canonical song names.

**What it does:**
- Fixes punctuation variants (commas, hyphens) to match database.csv
- Handles common variations like "Em Espírito, Em Verdade" → "Em Espírito Em Verdade"
- Updates history files in place

**When to use:**
- After running `songbook cleanup` and finding punctuation mismatches
- When importing data with inconsistent punctuation
- As a follow-up to manual history edits

**Usage:**
```bash
songbook fix-punctuation
```

**Implementation:**
```python
PUNCTUATION_FIXES = {
    "Em Espírito, Em Verdade": "Em Espírito Em Verdade",
    "Santo, Santo, Santo": "Santo Santo Santo",
    # Add more mappings as needed
}

# Apply fixes to all history files
for history_file in history_dir.glob("*.json"):
    data = json.loads(history_file.read_text())
    for moment, songs in data["moments"].items():
        data["moments"][moment] = [
            PUNCTUATION_FIXES.get(song, song)
            for song in songs
        ]
    history_file.write_text(json.dumps(data, indent=2))
```

**Note:** This script has a predefined mapping of punctuation variants. Edit the `PUNCTUATION_FIXES` dictionary to add new mappings.

**Best Practice:** Run `songbook cleanup` first to identify punctuation mismatches, then add them to `PUNCTUATION_FIXES` mapping.

---

## import-history

**Purpose:** Import external setlist data and convert it to the internal history format.

**Module:** `songbook/commands/maintenance.py` (import-history command)

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

**Usage:**
1. Edit the `raw_data` dictionary in the script with your data
2. Run: `songbook import-history`

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
      ],
      "Oferta": [{"title": "Offering Song", "key": "A"}],
      "Comunhão": [{"title": "Communion Song", "key": "E"}],
      "Crianças": [{"title": "Children's Song", "key": "C"}],
      "Poslúdio": [{"title": "Closing Song", "key": "F"}]
    }
  }
}
```

**Moment Name Mapping:**
```python
MOMENT_MAPPING = {
    "Prelúdio": "prelúdio",
    "Louvor": "louvor",
    "Oferta": "ofertório",
    "Comunhão": "saudação",
    "Crianças": "crianças",
    "Poslúdio": "poslúdio",
}
```

**Output Format:**
Creates `history/YYYY-MM-DD.json` files:
```json
{
  "date": "2025-12-28",
  "moments": {
    "prelúdio": ["Song Name"],
    "louvor": ["Song 1", "Song 2"],
    "ofertório": ["Offering Song"],
    "saudação": ["Communion Song"],
    "crianças": ["Children's Song"],
    "poslúdio": ["Closing Song"]
  }
}
```

**Implementation Details:**

```python
def import_history(raw_data):
    """Import external setlist data to internal format."""
    # Clear existing history
    for old_file in history_dir.glob("*.json"):
        old_file.unlink()

    # Process each date
    for date_str, entry in raw_data.items():
        if entry.get("format") != "setlist_with_moments":
            print(f"⚠️  Skipping {date_str}: unsupported format")
            continue

        # Map moment names and extract song titles
        moments = {}
        for external_moment, songs in entry["service_moments"].items():
            internal_moment = MOMENT_MAPPING.get(external_moment)
            if not internal_moment:
                print(f"⚠️  Unknown moment: {external_moment}")
                continue

            moments[internal_moment] = [song["title"] for song in songs]

        # Save to history
        output_file = history_dir / f"{date_str}.json"
        output_file.write_text(json.dumps({
            "date": date_str,
            "moments": moments
        }, indent=2, ensure_ascii=False))

        print(f"✓ Imported {date_str}")
```

**Note:** Only processes entries with `format: "setlist_with_moments"`. Other formats are ignored.

---

## Data Quality Best Practices

### 1. Run cleanup regularly
Catches issues early before they accumulate:
```bash
# Monthly health check
songbook cleanup
```

### 2. Verify after imports
Always run cleanup after importing external data:
```bash
songbook import-history
songbook cleanup
```

### 3. Keep backups
The cleanup script creates backups automatically:
- Backup location: `history_backup_YYYYMMDD_HHMMSS/`
- Preserves original state for rollback
- Can be deleted after verifying changes

### 4. Fix root causes
If punctuation issues recur, update data entry processes:
- Standardize punctuation in external sources
- Update import scripts to normalize punctuation
- Document canonical forms in database.csv comments

### 5. Document moment mappings
Keep track of external → internal moment name mappings:
```python
# External system uses Portuguese long-form
EXTERNAL_MOMENTS = {
    "Momento de Adoração": "louvor",
    "Momento de Oferta": "ofertório",
    "Momento de Comunhão": "saudação",
}
```

---

## Workflow: Importing External Data

Complete workflow for importing and validating external setlist data:

```bash
# 1. Prepare your data in the import script
# Edit raw_data dictionary in import_real_history.py

# 2. Run import
songbook import-history

# 3. Check for data quality issues
songbook cleanup

# 4. Fix punctuation if needed (if step 3 found issues)
songbook fix-punctuation

# 5. Verify final state (should show 0 issues)
songbook cleanup

# 6. Test generation with imported data
songbook generate --date 2026-03-01 --no-save

# 7. Verify generated setlist avoids recently used songs
songbook view-setlist --date 2026-03-01 --keys
```

---

## Common Issues and Solutions

### Issue: Capitalization mismatches
**Symptom:** "oceanos" in history, "Oceanos" in database.csv
**Solution:** Run `songbook cleanup` (auto-fixes capitalization)

### Issue: Punctuation variants
**Symptom:** "Em Espírito, Em Verdade" vs "Em Espírito Em Verdade"
**Solution:**
1. Add mapping to `PUNCTUATION_FIXES` dictionary
2. Run `songbook fix-punctuation`

### Issue: Song doesn't exist in database
**Symptom:** Cleanup reports missing song
**Solution:**
1. Check fuzzy matching suggestions
2. Either:
   - Add song to database.csv with energy and tags
   - Fix typo in history file using suggested song name

### Issue: Import fails with unknown moment
**Symptom:** "Unknown moment: XYZ"
**Solution:** Add mapping to `MOMENT_MAPPING` dictionary

### Issue: Imported songs have wrong dates
**Symptom:** History files created with wrong dates
**Solution:** Check date format in raw_data (must be YYYY-MM-DD)

---

## Testing Data Maintenance

### Unit Testing
```python
def test_capitalization_fix():
    """Test that capitalization fixes work correctly."""
    songs = {"Oceanos": Song(...)}
    history = [{"moments": {"louvor": ["oceanos"]}}]

    issues = find_data_issues(songs, history)
    assert issues[0]["type"] == "capitalization"
    assert issues[0]["fix"] == "Oceanos"

def test_fuzzy_matching():
    """Test that similar songs are suggested."""
    songs = {"Oceanos": Song(...)}
    missing = "Oceanos de Fe"  # Typo

    suggestions = find_similar_songs(missing, songs)
    assert "Oceanos" in suggestions
```

### Integration Testing
```bash
# Test full workflow
songbook import-history
songbook cleanup > output.txt
grep "0 issue" output.txt  # Should pass

# Test with intentional errors
# Add bad data to history
echo '{"date":"2026-01-01","moments":{"louvor":["bad song"]}}' > history/2026-01-01.json
songbook cleanup | grep "bad song"  # Should detect issue
```

---

## Migration Scripts

### migrate_folders.py
**Purpose:** Migrate from old folder structure to new structure

**When to use:**
- One-time migration when restructuring project
- Moving from flat structure to organized folders
- Consolidating scattered data files

**Note:** This is typically a one-time operation. After successful migration, the script can be archived or deleted.