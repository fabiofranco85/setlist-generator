"""
Songbook: Church worship setlist generator

Unified CLI for managing worship service setlists.
"""

from .main import cli

__version__ = "1.0.0"
__all__ = ["cli"]


# Entry point for console_scripts
def main():
    """Main entry point for the songbook command."""
    cli()
