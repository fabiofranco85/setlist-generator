#!/usr/bin/env python3
"""
DEPRECATED: This script is deprecated. Use 'songbook view-setlist' instead.

This wrapper is maintained for backward compatibility.
Future versions may remove this file.

Usage:
    python view_setlist.py [options]

New usage:
    songbook view-setlist [options]

Examples:
    Old: python view_setlist.py --keys
    New: songbook view-setlist --keys
"""

import sys
import warnings

# Show deprecation warning
warnings.warn(
    "\n"
    "=" * 70 + "\n"
    "DEPRECATION WARNING\n"
    "=" * 70 + "\n"
    "This script is deprecated. Please use 'songbook view-setlist' instead.\n"
    "\n"
    "Old: python view_setlist.py [options]\n"
    "New: songbook view-setlist [options]\n"
    "\n"
    "This wrapper will be removed in a future version.\n"
    "=" * 70,
    DeprecationWarning,
    stacklevel=2
)

# Import and run the new CLI
from songbook import cli

if __name__ == "__main__":
    # Prepend "view-setlist" to arguments
    sys.argv.insert(1, "view-setlist")
    cli()
