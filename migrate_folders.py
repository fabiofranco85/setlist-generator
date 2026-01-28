#!/usr/bin/env python3
"""
One-time migration script to restructure output folders.

Migrates from:
  setlists/        (mixed JSON + markdown)

To:
  output/          (markdown only)
  history/         (JSON only)

Usage:
    python migrate_folders.py
"""

from pathlib import Path
import shutil

def main():
    base = Path(".")
    old_dir = base / "setlists"
    output_dir = base / "output"
    history_dir = base / "history"

    # Check if old directory exists
    if not old_dir.exists():
        print(f"❌ Source directory '{old_dir}' does not exist")
        print("Migration may have already been completed or setlists folder is missing.")
        return

    print(f"Migrating from '{old_dir}' to '{output_dir}' and '{history_dir}'...")
    print()

    # Create new directories
    output_dir.mkdir(exist_ok=True)
    print(f"✅ Created directory: {output_dir}")

    history_dir.mkdir(exist_ok=True)
    print(f"✅ Created directory: {history_dir}")
    print()

    # Move markdown files
    md_files = list(old_dir.glob("*.md"))
    if md_files:
        print(f"📄 Moving {len(md_files)} markdown file(s)...")
        for md_file in md_files:
            dest = output_dir / md_file.name
            shutil.move(str(md_file), str(dest))
            print(f"  ✓ {md_file.name} → output/")
        print()
    else:
        print("ℹ️  No markdown files found to migrate")
        print()

    # Move JSON files
    json_files = list(old_dir.glob("*.json"))
    if json_files:
        print(f"📊 Moving {len(json_files)} JSON file(s)...")
        for json_file in json_files:
            dest = history_dir / json_file.name
            shutil.move(str(json_file), str(dest))
            print(f"  ✓ {json_file.name} → history/")
        print()
    else:
        print("ℹ️  No JSON files found to migrate")
        print()

    # Move backup folder if it exists
    bkp_dir = old_dir / "bkp"
    if bkp_dir.exists():
        dest_bkp = output_dir / "bkp"
        shutil.move(str(bkp_dir), str(dest_bkp))
        print(f"📦 Moved bkp/ → output/bkp/")
        print()

    # Check if old directory is empty
    remaining_files = list(old_dir.iterdir())
    if not remaining_files:
        old_dir.rmdir()
        print(f"🗑️  Removed empty directory: {old_dir}")
        print()
        print("=" * 60)
        print("✅ Migration complete!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  • Markdown files: {output_dir}")
        print(f"  • JSON history: {history_dir}")
        print(f"  • Old directory removed: {old_dir}")
    else:
        print(f"⚠️  Warning: '{old_dir}' not empty")
        print(f"   Remaining files: {[f.name for f in remaining_files]}")
        print()
        print("=" * 60)
        print("⚠️  Migration partially complete")
        print("=" * 60)
        print()
        print("Please manually remove or move the remaining files, then delete the setlists/ folder.")

if __name__ == "__main__":
    main()
