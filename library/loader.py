"""Tag parsing utilities.

This module provides the parse_tags() function for parsing tag strings
from the database.csv format into dictionaries.

For loading songs and history, use the repository pattern:

    >>> from library import get_repositories
    >>> repos = get_repositories()
    >>> songs = repos.songs.get_all()
    >>> history = repos.history.get_all()
"""

import re

from .config import DEFAULT_WEIGHT


def parse_tags(tags_str: str) -> dict[str, int]:
    """
    Parse tags string into dict of {moment: weight}.

    Supports formats:
    - 'louvor' (uses default weight)
    - 'louvor(5)' (explicit weight)
    - 'louvor,prelúdio(3)' (multiple tags with mixed weights)

    Args:
        tags_str: Comma-separated tags string from database.csv

    Returns:
        Dictionary mapping moment names to weights

    Examples:
        >>> parse_tags('louvor')
        {'louvor': 3}
        >>> parse_tags('louvor(5),prelúdio')
        {'louvor': 5, 'prelúdio': 3}
    """
    if not tags_str.strip():
        return {}

    tags = {}
    for tag in tags_str.split(","):
        tag = tag.strip()
        if not tag:
            continue

        # Check for weight in parentheses: tag(weight)
        match = re.match(r"^(.+?)\((\d+)\)$", tag)
        if match:
            moment = match.group(1).strip()
            weight = int(match.group(2))
        else:
            moment = tag
            weight = DEFAULT_WEIGHT

        tags[moment] = weight

    return tags
