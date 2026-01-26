# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **setlist generator** for church worship services. It intelligently selects songs based on:
- **Moments/Tags**: Songs are categorized into service moments (prelúdio, louvor, ofertório, saudação, crianças, poslúdio)
- **Weighted preferences**: Each song-moment association can have a weight (1-10, default 3)
- **Recency tracking**: Avoids recently used songs by tracking performance history
- **Manual overrides**: Allows forcing specific songs for any moment

## Key Commands

### Generate Setlist
```bash
# Generate for today
python generate_setlist.py

# Generate for specific date
python generate_setlist.py --date 2026-02-15

# Override specific moments
python generate_setlist.py --override "louvor:Oceanos,Santo Pra Sempre"
python generate_setlist.py --override "prelúdio:Estamos de Pé" --override "louvor:Oceanos"

# Dry run (don't save to history)
python generate_setlist.py --no-save
```

### Running with uv
```bash
uv run generate_setlist.py [options]
```

## Architecture

### Core Algorithm

The song selection algorithm (`select_songs_for_moment`) uses a **composite scoring system**:

```
score = weight × (recency + 0.1) + random(0, 0.5)
```

Where:
- **weight**: From tags.csv (e.g., `louvor(5)` → weight=5)
- **recency**: Penalty factor based on last 3 performances (0.0 = just used, 1.0 = never used)
- **random factor**: Adds variety to avoid deterministic selection

### Data Flow

1. **Load songs** from `tags.csv` + `chords/*.md` files
2. **Load history** from `setlists/*.json` (sorted by date, most recent first)
3. **Calculate recency scores** for all songs based on last 3 performances
4. **Generate setlist** by selecting songs for each moment in order
5. **Output**:
   - Terminal summary (song titles only)
   - `setlists/YYYY-MM-DD.md` (full markdown with chords)
   - `setlists/YYYY-MM-DD.json` (history tracking)

### File Structure

```
.
├── tags.csv                 # Song database: "song;tags"
├── chords/                  # Individual song files with chords
│   └── <Song Name>.md       # Format: "# Song (Key)\n```\nchords...\n```"
├── setlists/                # Generated outputs and history
│   ├── YYYY-MM-DD.json      # History tracking (moments → song lists)
│   └── YYYY-MM-DD.md        # Human-readable setlist with full chords
└── generate_setlist.py      # Main generator script
```

### Moments Configuration

Defined in `MOMENTS_CONFIG` (generate_setlist.py:31-38):

| Moment      | Count | Description                 |
|-------------|-------|-----------------------------|
| prelúdio    | 1     | Opening/introductory song   |
| ofertório   | 1     | Offering song               |
| saudação    | 1     | Greeting/welcome song       |
| crianças    | 1     | Children's song             |
| louvor      | 4     | Main worship block          |
| poslúdio    | 1     | Closing song                |

### Tags Format

In `tags.csv`:
- Basic: `song;moment` (uses default weight 3)
- Weighted: `song;moment(5)` (weight 5)
- Multiple: `song;moment1,moment2(4)` (moment1 uses weight 3, moment2 uses weight 4)

Examples:
```csv
Oceanos;louvor(5)
Autoridade e Poder;prelúdio,poslúdio
Brilha Jesus;saudação(4),poslúdio(2)
```

### Recency Penalty System

`RECENCY_PENALTY_PERFORMANCES = 3` (generate_setlist.py:41)

Songs are penalized based on how recently they were used:
- **Used in last setlist**: recency = 0.0 (heavily penalized)
- **Used 2 setlists ago**: recency = 0.33
- **Used 3 setlists ago**: recency = 0.67
- **Not used in last 3**: recency = 1.0 (no penalty)

This ensures variety while still allowing high-weight songs to appear relatively frequently.

## Modifying Song Selection Behavior

### Change moment counts
Edit `MOMENTS_CONFIG` in generate_setlist.py:31-38

### Change recency window
Edit `RECENCY_PENALTY_PERFORMANCES` in generate_setlist.py:41 (default: 3)

### Change default weight
Edit `DEFAULT_WEIGHT` in generate_setlist.py:40 (default: 3)

### Adjust randomization
Edit the random factor in generate_setlist.py:186:
```python
candidates.sort(key=lambda x: x[1] + random.uniform(0, 0.5), reverse=True)
```

## Adding New Songs

1. Add entry to `tags.csv`:
   ```csv
   New Song Title;louvor(4),prelúdio
   ```

2. Create `chords/New Song Title.md`:
   ```markdown
   # New Song Title (G)

   ```
   G               D
   Verse lyrics...
   ```
   ```

3. Run generator - new song will be automatically included in selection pool

## Dependencies

- Python 3.12+
- Standard library only (no external dependencies)
- Optional: `uv` for package management
