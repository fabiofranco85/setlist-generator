"""Integration-specific fixtures.

Integration tests may touch the filesystem (via ``tmp_project``) or exercise
the full repository stack.  They should still avoid real network calls.
"""
