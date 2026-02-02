"""
Maintenance commands - data quality and import utilities.
"""

from pathlib import Path


def run_cleanup(history_dir):
    """
    Run data quality checks on history files.

    Args:
        history_dir: Custom history directory
    """
    import sys
    import cleanup_history

    # Change to the correct directory if needed
    if history_dir:
        print(f"Note: Custom history directory specified: {history_dir}")
        print("Cleanup script currently uses hardcoded './history' path")
        print("Consider updating cleanup_history.py to accept --history-dir")
        print()

    # Run the cleanup script's main function
    cleanup_history.main()


def run_fix_punctuation(history_dir):
    """
    Normalize punctuation in history files.

    Args:
        history_dir: Custom history directory
    """
    import sys
    import fix_punctuation

    # Change to the correct directory if needed
    if history_dir:
        print(f"Note: Custom history directory specified: {history_dir}")
        print("Fix punctuation script currently uses hardcoded './history' path")
        print("Consider updating fix_punctuation.py to accept --history-dir")
        print()

    # Run the fix punctuation script's main function
    fix_punctuation.main()


def run_import():
    """
    Import external setlist data.

    Note: This command requires editing the script to add your data first.
    """
    import sys
    import import_real_history

    print("=" * 70)
    print("IMPORT EXTERNAL HISTORY")
    print("=" * 70)
    print()
    print("This command will import external setlist data into the history format.")
    print()
    print("IMPORTANT:")
    print("1. Edit import_real_history.py and add your data to the raw_data dict")
    print("2. Review the moment name mappings")
    print("3. Run this command to import")
    print()

    response = input("Have you edited import_real_history.py with your data? (y/n): ")
    if response.lower() != "y":
        print("\nCancelled. Please edit import_real_history.py first.")
        return

    print()
    # Run the import script's main function
    import_real_history.main()
