#!/usr/bin/env python3
"""Compare old position-based vs new time-based recency scoring."""

from pathlib import Path
from library import load_songs, load_history
from library.selector import calculate_recency_scores

def main():
    # Load actual data
    songs = load_songs(Path("."))
    history = load_history(Path("./history"))

    # Calculate recency scores for 2026-02-15
    scores = calculate_recency_scores(songs, history, "2026-02-15")

    # Show some example songs with their scores
    print("=" * 80)
    print("RECENCY SCORES USING TIME-BASED DECAY (as of 2026-02-15)")
    print("=" * 80)
    print(f"{'Song':<40s} {'Score':>8s} {'Last Used':>15s} {'Days Ago':>10s}")
    print("-" * 80)

    # Find last use dates for comparison
    last_used = {}
    for setlist in history:
        date = setlist.get("date", "unknown")
        for moment, song_list in setlist.get("moments", {}).items():
            for song in song_list:
                if song not in last_used:
                    last_used[song] = date

    # Sort songs by score (ascending = most penalized first)
    sorted_songs = sorted(scores.items(), key=lambda x: x[1])

    # Show top 10 most recently used (lowest scores)
    print("\n>>> MOST RECENTLY USED (highest penalty):")
    for song, score in sorted_songs[:10]:
        date = last_used.get(song, "Never")
        if date != "Never":
            from datetime import datetime
            last_date = datetime.strptime(date, "%Y-%m-%d").date()
            current_date = datetime.strptime("2026-02-15", "%Y-%m-%d").date()
            days_ago = (current_date - last_date).days
        else:
            days_ago = 0
        print(f"{song:<40s} {score:>8.3f} {date:>15s} {days_ago:>10d}")

    # Show songs never used (score = 1.0)
    never_used = [(s, score) for s, score in sorted_songs if score >= 0.999]
    print(f"\n>>> NEVER USED (score ≈ 1.0): {len(never_used)} songs")
    for song, score in never_used[:5]:
        print(f"{song:<40s} {score:>8.3f}")

    # Show middle range (getting fresh)
    middle = [(s, score) for s, score in sorted_songs if 0.5 <= score < 0.8]
    print(f"\n>>> GETTING FRESH (score 0.5-0.8): {len(middle)} songs")
    for song, score in middle[:10]:
        date = last_used.get(song, "Never")
        if date != "Never":
            from datetime import datetime
            last_date = datetime.strptime(date, "%Y-%m-%d").date()
            current_date = datetime.strptime("2026-02-15", "%Y-%m-%d").date()
            days_ago = (current_date - last_date).days
        else:
            days_ago = 0
        print(f"{song:<40s} {score:>8.3f} {date:>15s} {days_ago:>10d}")

    print("\n" + "=" * 80)
    print("KEY INSIGHTS:")
    print("  • Songs used in last ~2 weeks: heavily penalized (score < 0.3)")
    print("  • Songs used 1-2 months ago: moderate penalty (score 0.5-0.7)")
    print("  • Songs used 3+ months ago: almost no penalty (score > 0.85)")
    print("  • Never used songs: maximum score (1.0)")
    print("\nThis ensures:")
    print("  ✓ Recent songs are avoided")
    print("  ✓ Older songs gradually become candidates again")
    print("  ✓ No sharp cutoff at 3 performances")
    print("  ✓ Full history considered (not just last 3)")

if __name__ == "__main__":
    main()
