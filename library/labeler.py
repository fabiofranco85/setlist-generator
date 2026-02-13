"""Setlist label management.

Provides relabeling functionality for setlists — adding, renaming,
or removing labels. All three operations are the same transformation:
construct a new Setlist from a source dict with a different label value.
"""

import copy

from .models import Setlist


def relabel_setlist(setlist_dict: dict, new_label: str) -> Setlist:
    """Create a new Setlist from a source dict with a different label.

    This handles all three label operations:
    - Add label: source has no label, new_label is non-empty
    - Rename label: source has a label, new_label is different
    - Remove label: source has a label, new_label is empty

    Args:
        setlist_dict: Source setlist dictionary (not mutated)
        new_label: The new label to assign (empty string to remove)

    Returns:
        New Setlist object with the updated label
    """
    return Setlist(
        date=setlist_dict["date"],
        moments=copy.deepcopy(setlist_dict["moments"]),
        label=new_label,
    )
