"""Pure identity typography normalization shared by storage and comparison.

Does not collapse distinct item names or strip meaningful modifiers.
"""

import unicodedata


def normalize_name(value):
    """Normalize typography, not item identity or meaningful modifiers."""
    value = unicodedata.normalize('NFKC', str(value)).casefold().replace('\u2019', "'")
    return ' '.join(value.split())
