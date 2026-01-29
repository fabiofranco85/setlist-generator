#!/usr/bin/env python3
"""
Cleanup history data to ensure song names match tags.csv exactly.

This script:
1. Finds all songs in history that don't match tags.csv
2. Fixes capitalization mismatches automatically
3. Reports songs that need to be added to tags.csv
4. Creates backups before making changes
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def load_tags_songs() -> dict[str, str]:
    """
    Load song names from tags.csv.

    Returns:
        Dict mapping lowercase song names to proper capitalization
    """
    songs = {}
    with open("tags.csv", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(";")
            if len(parts) >= 1:
                song_name = parts[0].strip()
                songs[song_name.lower()] = song_name

    return songs


def analyze_history(tags_songs: dict[str, str]) -> tuple[dict, dict, list]:
    """
    Analyze history files and categorize issues.

    Returns:
        Tuple of (capitalization_fixes, missing_songs, all_history_data)
    """
    capitalization_fixes = {}  # file -> {old_name: new_name}
    missing_songs = set()
    all_history_data = []

    for hist_file in sorted(Path("history").glob("*.json")):
        with open(hist_file, encoding="utf-8") as f:
            data = json.load(f)

        all_history_data.append((hist_file, data))
        file_fixes = {}

        for moment, songs in data["moments"].items():
            for song in songs:
                # Check if song matches exactly
                if song in tags_songs.values():
                    continue  # Perfect match

                # Check if it's a capitalization issue
                if song.lower() in tags_songs:
                    correct_name = tags_songs[song.lower()]
                    file_fixes[song] = correct_name
                else:
                    # Song not found at all
                    missing_songs.add(song)

        if file_fixes:
            capitalization_fixes[hist_file] = file_fixes

    return capitalization_fixes, missing_songs, all_history_data


def apply_fixes(history_data: list, capitalization_fixes: dict):
    """
    Apply capitalization fixes to history files.
    """
    print("Step 2: Applying capitalization fixes...")
    print()

    fixed_count = 0

    for hist_file, data in history_data:
        if hist_file not in capitalization_fixes:
            continue

        fixes = capitalization_fixes[hist_file]
        changes_made = []

        # Update song names in the data
        for moment, songs in data["moments"].items():
            for i, song in enumerate(songs):
                if song in fixes:
                    old_name = song
                    new_name = fixes[song]
                    data["moments"][moment][i] = new_name
                    changes_made.append(f"'{old_name}' → '{new_name}'")
                    fixed_count += 1

        if changes_made:
            # Save updated file
            with open(hist_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"  📝 {hist_file.name}")
            for change in changes_made:
                print(f"     • {change}")

    print()
    print(f"  ✓ Fixed {fixed_count} capitalization issue(s) across {len(capitalization_fixes)} file(s)")
    print()


def report_missing_songs(missing_songs: set, tags_songs: dict):
    """
    Report songs that need to be added to tags.csv.
    """
    if not missing_songs:
        print("  ✅ No missing songs - all history songs exist in tags.csv!")
        return

    print("Step 3: Songs that need to be added to tags.csv")
    print()
    print(f"  Found {len(missing_songs)} song(s) in history not present in tags.csv:")
    print()

    for song in sorted(missing_songs):
        # Try to find similar names (fuzzy match)
        similar = []
        song_lower = song.lower()
        for tag_song_lower, tag_song in tags_songs.items():
            # Check if words match (ignoring punctuation differences)
            song_words = set(song_lower.replace(",", "").replace("-", " ").split())
            tag_words = set(tag_song_lower.replace(",", "").replace("-", " ").split())

            if song_words == tag_words:
                similar.append(tag_song)

        if similar:
            print(f"  ⚠️  '{song}'")
            print(f"      → Possibly same as: {similar[0]}")
            print(f"      → Suggested action: Fix history to use '{similar[0]}'")
        else:
            print(f"  ❌ '{song}'")
            print(f"      → Not found in tags.csv")
            print(f"      → Suggested action: Add to tags.csv with energy and moment tags")
        print()


def create_backup():
    """
    Create backup of history directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"history_backup_{timestamp}")

    if Path("history").exists():
        shutil.copytree("history", backup_dir)
        print(f"  ✓ Created backup: {backup_dir}")
        return backup_dir

    return None


def main():
    print("=" * 70)
    print("  HISTORY DATA CLEANUP")
    print("=" * 70)
    print()

    # Step 0: Create backup
    print("Step 0: Creating backup...")
    backup_dir = create_backup()
    print()

    # Step 1: Analyze
    print("Step 1: Analyzing history files...")
    tags_songs = load_tags_songs()
    print(f"  ✓ Loaded {len(tags_songs)} songs from tags.csv")

    capitalization_fixes, missing_songs, all_history_data = analyze_history(tags_songs)

    total_issues = sum(len(fixes) for fixes in capitalization_fixes.values()) + len(missing_songs)
    print(f"  ✓ Found {total_issues} issue(s):")
    print(f"    • {sum(len(fixes) for fixes in capitalization_fixes.values())} capitalization mismatches")
    print(f"    • {len(missing_songs)} missing songs")
    print()

    # Step 2: Apply fixes
    if capitalization_fixes:
        apply_fixes(all_history_data, capitalization_fixes)
    else:
        print("Step 2: No capitalization fixes needed")
        print()

    # Step 3: Report missing
    report_missing_songs(missing_songs, tags_songs)

    # Summary
    print("=" * 70)
    print("  CLEANUP COMPLETE")
    print("=" * 70)
    print()

    if capitalization_fixes:
        print(f"✅ Fixed {sum(len(fixes) for fixes in capitalization_fixes.values())} capitalization issues")

    if missing_songs:
        print(f"⚠️  {len(missing_songs)} songs still need attention (see above)")
        print()
        print("Next steps:")
        print("  1. Review the missing songs list above")
        print("  2. Either:")
        print("     a) Add them to tags.csv with proper energy and moment tags")
        print("     b) Fix history files to use existing song names")
        print("     c) Remove them from history if they were mistakes")
    else:
        print("✅ All songs in history match tags.csv perfectly!")

    print()
    if backup_dir:
        print(f"Backup saved to: {backup_dir}")
        print("(Delete backup after verifying changes)")


if __name__ == "__main__":
    main()
