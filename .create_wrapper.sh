#!/bin/bash
# Helper script to create backward-compatible wrappers

create_wrapper() {
    local old_script=$1
    local command=$2
    local description=$3

    cat > "$old_script" << 'WRAPPER_EOF'
#!/usr/bin/env python3
"""
DEPRECATED: This script is deprecated. Use 'songbook COMMAND' instead.

This wrapper is maintained for backward compatibility.
Future versions may remove this file.

Usage:
    python OLD_SCRIPT [options]

New usage:
    songbook COMMAND [options]

Examples:
    Old: python OLD_SCRIPT [options]
    New: songbook COMMAND [options]
"""

import sys
import warnings

# Show deprecation warning
warnings.warn(
    "\n"
    "=" * 70 + "\n"
    "DEPRECATION WARNING\n"
    "=" * 70 + "\n"
    "This script is deprecated. Please use 'songbook COMMAND' instead.\n"
    "\n"
    "Old: python OLD_SCRIPT [options]\n"
    "New: songbook COMMAND [options]\n"
    "\n"
    "This wrapper will be removed in a future version.\n"
    "=" * 70,
    DeprecationWarning,
    stacklevel=2
)

# Import and run the new CLI
from songbook import cli

if __name__ == "__main__":
    # Prepend "COMMAND" to arguments
    sys.argv.insert(1, "COMMAND")
    cli()
WRAPPER_EOF

    # Replace placeholders
    sed -i '' "s/OLD_SCRIPT/$old_script/g" "$old_script"
    sed -i '' "s/COMMAND/$command/g" "$old_script"

    echo "Created wrapper for $old_script -> songbook $command"
}

# Create all wrappers
create_wrapper "view_setlist.py" "view-setlist" "View generated setlist"
create_wrapper "view_song.py" "view-song" "View song details"
create_wrapper "replace_song.py" "replace" "Replace song in setlist"
create_wrapper "generate_pdf.py" "pdf" "Generate PDF"
create_wrapper "list_moments.py" "list-moments" "List moments"
create_wrapper "cleanup_history.py" "cleanup" "Data quality checks"
create_wrapper "fix_punctuation.py" "fix-punctuation" "Fix punctuation"
create_wrapper "import_real_history.py" "import-history" "Import history"

echo "All wrappers created!"
