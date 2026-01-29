# Time-Based Recency Tracking System

## Overview

The setlist generator uses a **time-based exponential decay** algorithm to track song recency. This ensures songs become more likely to be selected the longer it's been since they were last used, considering the **full history** of all services.

## How It Works

### Formula

```
recency_score = 1.0 - exp(-days_since_last_use / DECAY_CONSTANT)
```

Where:
- `days_since_last_use` = actual days between current date and last performance
- `DECAY_CONSTANT` = 45 days (configurable in `setlist/config.py`)
- `recency_score` = 0.0 (just used) to 1.0 (never used)

### Score Interpretation

| Score Range | Meaning | Example |
|-------------|---------|---------|
| 0.0 - 0.2 | Just used, heavily penalized | Used last week |
| 0.2 - 0.5 | Recently used, strong penalty | Used 2-4 weeks ago |
| 0.5 - 0.7 | Getting fresh, moderate penalty | Used 1-2 months ago |
| 0.7 - 0.9 | Quite fresh, light penalty | Used 2-3 months ago |
| 0.9 - 1.0 | Essentially "never used" | Used 3+ months ago or never |

### Example Scores (DECAY_CONSTANT = 45 days)

| Days Since Last Use | Score | Impact |
|---------------------|-------|--------|
| 0 (same day) | 0.000 | Essentially excluded |
| 7 days | 0.144 | Heavy penalty |
| 14 days | 0.267 | Strong penalty |
| 30 days | 0.487 | Moderate penalty |
| 45 days | 0.632 | Getting fresh |
| 60 days | 0.736 | Very fresh |
| 90 days | 0.865 | Almost "never used" |
| 180 days | 0.982 | Treated as "never used" |

## Key Benefits

### 1. **Considers Full History**
Unlike the old system (which only looked at last 3 performances), the new system examines **all history files** to find when each song was last used.

### 2. **Time-Aware**
Songs used 21 days ago get different scores than songs used 49 days ago, even if both are beyond the "last 3 services" window.

**Old system:**
```
Setlist 1 (most recent): score 0.0
Setlist 2: score 0.33
Setlist 3: score 0.67
Setlist 4+: score 1.0 (all treated equally)
```

**New system:**
```
7 days ago: score 0.14
14 days ago: score 0.27
30 days ago: score 0.49
60 days ago: score 0.74
90 days ago: score 0.86
```

### 3. **Smooth, Continuous Scoring**
No sharp cutoffs. Songs gradually become better candidates as time passes.

### 4. **No Configuration Pollution**
Uses existing `history/*.json` files as source of truth. No need to modify `tags.csv` or maintain separate state files.

## Configuration

### RECENCY_DECAY_DAYS

**Location:** `setlist/config.py`

```python
RECENCY_DECAY_DAYS = 45  # Days for a song to feel "fresh" again
```

### How to Choose

| Value | Effect | Best For |
|-------|--------|----------|
| **30 days** | Fast cycling, songs fresh after 1 month | Small libraries (30-40 songs), frequent services (2-3x/week) |
| **45 days** | Balanced, songs fresh after 1.5 months | **Default - most churches** |
| **60 days** | Slower cycling, songs fresh after 2 months | Larger libraries (60+ songs) |
| **90 days** | Very slow, maximum variety | Very large libraries (100+ songs) |

### Score Comparison at Different Decay Constants

| Days Since | 30-day | 45-day | 60-day | 90-day |
|-----------|--------|--------|--------|--------|
| 7 days | 0.21 | 0.15 | 0.12 | 0.08 |
| 14 days | 0.39 | 0.29 | 0.23 | 0.15 |
| 30 days | 0.63 | 0.49 | 0.39 | 0.28 |
| 60 days | 0.86 | 0.74 | 0.63 | 0.49 |
| 90 days | 0.95 | 0.86 | 0.78 | 0.63 |

## Song Selection Algorithm

The final selection score combines **weight** and **recency**:

```python
selection_score = weight × (recency + 0.1) + random(0, 0.5)
```

Where:
- `weight` = from tags.csv (e.g., `louvor(5)` → weight 5, default 3)
- `recency` = time-based decay score (0.0-1.0)
- `random` = small randomness to add variety

### Examples

**High-weight song used recently:**
```
weight = 5, recency = 0.3 (used 30 days ago)
score = 5 × (0.3 + 0.1) + 0.25 = 2.25
```

**Medium-weight song used long ago:**
```
weight = 3, recency = 0.9 (used 4 months ago)
score = 3 × (0.9 + 0.1) + 0.25 = 3.25
```

**Result:** The older song (3.25) beats the recently-used high-weight song (2.25), promoting variety while still respecting weights.

## Testing

### Verify Time Decay Behavior

```bash
python test_recency_decay.py
```

Shows recency scores at different time intervals (7 days, 14 days, 30 days, etc.)

### Compare with Actual History

```bash
python test_comparison.py
```

Shows:
- Most recently used songs (the highest penalty)
- Never-used songs (score = 1.0)
- Songs in the "getting fresh" range (score 0.5-0.8)

### Generate Multiple Setlists

```bash
python generate_setlist.py --date 2026-03-01 --no-save
python generate_setlist.py --date 2026-03-08 --no-save
python generate_setlist.py --date 2026-03-15 --no-save
```

Verify good variety without excessive repetition.

## Tuning Process

1. **Start with default (45 days)**
2. **Generate 8-10 test setlists** using future dates
3. **Observe patterns:**
   - Songs repeating too quickly? → Increase to 60-90 days
   - Songs taking too long to reappear? → Decrease to 30 days
   - Some songs never appearing? → Check their weights in tags.csv
4. **Monitor congregation feedback** after real services
5. **Adjust gradually** (e.g., 45 → 60, not 45 → 90)

## Implementation Details

### Files Modified

1. **`setlist/config.py`** - Added `RECENCY_DECAY_DAYS = 45`
2. **`setlist/selector.py`** - Replaced position-based with time-based algorithm
3. **`setlist/generator.py`** - Moved recency calculation to `generate()` method
4. **`setlist/__init__.py`** - Exported new config constant

### Backward Compatibility

- ✅ No data migration required
- ✅ Uses existing `history/*.json` files unchanged
- ✅ `tags.csv` format unchanged
- ✅ Functional API (`generate_setlist()`) still works
- ✅ `RECENCY_PENALTY_PERFORMANCES` kept for backward compatibility (unused)

### Edge Cases Handled

- **Malformed dates in history:** Skipped gracefully
- **Missing date field:** Setlist ignored
- **Same-day generation:** Score = 0.0 (excluded)
- **Future dates in history:** Handled as 0.0 score
- **Never-used songs:** Score = 1.0 (maximum)

## Comparison with Old System

### Old System (Position-Based)

**Pros:**
- Simple to understand
- Fast calculation (only 3 setlists examined)

**Cons:**
- ❌ Ignores time elapsed (3 weeks = 3 months)
- ❌ Sharp cutoff at 3 performances
- ❌ Songs beyond window treated as "never used"
- ❌ Can't distinguish frequency patterns

### New System (Time-Based)

**Pros:**
- ✅ Considers full history
- ✅ Time-aware (30 days ≠ 90 days)
- ✅ Smooth, continuous scoring
- ✅ More sophisticated and fair
- ✅ Tunable to congregation preferences

**Cons:**
- ⚠️ Slightly more complex calculation
- ⚠️ Requires date parsing from all history files

**Verdict:** Benefits far outweigh complexity. The calculation overhead is negligible (<100ms for typical history sizes).

## Troubleshooting

### Songs Repeating Too Quickly

**Symptom:** Same songs appearing every 2-3 weeks

**Solutions:**
1. Increase `RECENCY_DECAY_DAYS` to 60-90 days
2. Check song weights - reduce weights of over-represented songs
3. Add more songs to tags.csv

### Songs Taking Too Long to Reappear

**Symptom:** Good songs not seen for 4+ months

**Solutions:**
1. Decrease `RECENCY_DECAY_DAYS` to 30 days
2. Increase weights of desired songs in tags.csv
3. Check if song has appropriate moment tags

### Some Songs Never Selected

**Symptom:** Songs with score 1.0 never appearing

**Possible causes:**
1. **Low weight:** Song has default weight (3) competing with high-weight songs
2. **Wrong moments:** Song tagged for moments where high-weight songs dominate
3. **Energy mismatch:** Energy ordering placing song in an unfavorable position

**Solutions:**
1. Increase weight: `louvor(5)` instead of `louvor`
2. Add moment tags: `louvor,prelúdio` gives more opportunities
3. Check energy level matches typical moment needs

## Future Enhancements

Possible improvements (not currently implemented):

1. **Frequency weighting:** Penalize songs used multiple times in history more than once-used songs
2. **Moment-specific recency:** Track last use per moment (e.g., allow "Oceanos" in prelúdio even if recently used in louvor)
3. **Seasonal adjustments:** Different decay constants for different times of year
4. **User preferences:** Per-user decay constants or exclude lists
5. **Performance metrics:** Track which songs get strong congregation response

## References

- **Algorithm:** Exponential decay: `1.0 - exp(-x/k)`
- **Inspiration:** Similar to cache eviction algorithms (LRU with time decay)
- **Implementation:** `setlist/selector.py` (lines 10-70)
- **Configuration:** `setlist/config.py` (line 16)
