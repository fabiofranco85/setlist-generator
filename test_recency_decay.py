#!/usr/bin/env python3
"""Test script to verify time-based recency decay behavior."""

from datetime import date, timedelta
from setlist.selector import calculate_recency_scores
from setlist.models import Song

def test_time_decay():
    """Test recency scoring at different time intervals."""

    # Create test songs
    songs = {
        "Test Song": Song("Test Song", {"louvor": 3}, 2.5, "")
    }

    # Reference date for testing
    today = date(2026, 2, 15)

    test_cases = [
        (0, "Today (same day)"),
        (7, "1 week ago"),
        (14, "2 weeks ago"),
        (30, "1 month ago"),
        (45, "1.5 months ago (decay constant)"),
        (60, "2 months ago"),
        (90, "3 months ago"),
        (120, "4 months ago"),
        (180, "6 months ago"),
    ]

    print("=" * 70)
    print(f"RECENCY DECAY TEST (DECAY_CONSTANT = 45 days)")
    print("=" * 70)
    print(f"{'Time Since Last Use':<40s} {'Score':>8s} {'Impact':>15s}")
    print("-" * 70)

    for days_ago, label in test_cases:
        history_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        history = [{
            "date": history_date,
            "moments": {"louvor": ["Test Song"]}
        }]

        scores = calculate_recency_scores(songs, history, "2026-02-15")
        score = scores['Test Song']

        # Interpret score impact
        if score < 0.2:
            impact = "Heavy penalty"
        elif score < 0.4:
            impact = "Strong penalty"
        elif score < 0.6:
            impact = "Moderate penalty"
        elif score < 0.8:
            impact = "Light penalty"
        else:
            impact = "Almost none"

        print(f"{label:<40s} {score:>8.3f} {impact:>15s}")

    print("-" * 70)
    print("\nInterpretation:")
    print("  • Score 0.0 = Just used (essentially excluded)")
    print("  • Score 0.5 = Getting fresh")
    print("  • Score 1.0 = Never used (or very long ago)")
    print("\nConclusion:")
    print(f"  Songs feel 'fresh' after ~45-60 days (score > 0.6)")
    print(f"  Songs almost like 'never used' after ~90 days (score > 0.85)")

if __name__ == "__main__":
    test_time_decay()
