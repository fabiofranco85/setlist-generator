#!/usr/bin/env python3
"""
Fix punctuation differences in history files.

This script handles songs that have the same words but different punctuation
(commas, hyphens, etc.) by replacing them with the canonical version from tags.csv.
"""

import json
from pathlib import Path

# Manual mapping of punctuation variants to canonical names
PUNCTUATION_FIXES = {
    "Em Espírito, Em Verdade": "Em Espírito Em Verdade",
    "Espírito, Enche a Minha Vida": "Espírito Enche a Minha Vida",
    "Venho, Senhor, Minha Vida Oferecer": "Venho Senhor Minha Vida Oferecer",
}


def main():
    print("=" * 70)
    print("  FIXING PUNCTUATION DIFFERENCES")
    print("=" * 70)
    print()

    fixed_count = 0
    files_changed = 0

    for hist_file in sorted(Path("history").glob("*.json")):
        with open(hist_file, encoding="utf-8") as f:
            data = json.load(f)

        changes_made = []
        modified = False

        # Update song names in the data
        for moment, songs in data["moments"].items():
            for i, song in enumerate(songs):
                if song in PUNCTUATION_FIXES:
                    old_name = song
                    new_name = PUNCTUATION_FIXES[song]
                    data["moments"][moment][i] = new_name
                    changes_made.append(f"'{old_name}' → '{new_name}'")
                    fixed_count += 1
                    modified = True

        if modified:
            # Save updated file
            with open(hist_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            files_changed += 1
            print(f"  📝 {hist_file.name}")
            for change in changes_made:
                print(f"     • {change}")

    print()
    print("=" * 70)
    if fixed_count > 0:
        print(f"✅ Fixed {fixed_count} punctuation issue(s) in {files_changed} file(s)")
    else:
        print("✅ No punctuation issues found - all songs use canonical names!")
    print("=" * 70)


if __name__ == "__main__":
    main()
