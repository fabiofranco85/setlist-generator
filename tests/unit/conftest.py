"""Unit-specific fixtures.

Unit tests should be fast and isolated — no file I/O, no network, no database.
Prefer in-memory data structures and the fixtures from the root conftest.
"""

import random

import pytest


@pytest.fixture()
def fixed_random_seed():
    """Seed the random module for deterministic selection tests."""
    random.seed(42)
    yield
    # Restore randomness after test
    random.seed()
