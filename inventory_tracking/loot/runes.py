"""Bundled rune class IDs and names (data/runes.json, built by build_runes.py from d2data)."""

import json
from pathlib import Path


_TABLE = json.loads((Path(__file__).parent / 'data' / 'runes.json').read_text())['runes']
RUNES: dict[int, dict[str, str]] = {int(class_id): row for class_id, row in _TABLE.items()}
_BY_CODE = {row['code']: class_id for class_id, row in RUNES.items()}


def rune_name(class_id: int) -> str:
    return RUNES[class_id]['name']


def is_valuable_rune(class_id: int, *, minimum: str) -> bool:
    """A rune at or above `minimum` (a code such as 'r21' = Pul; runes are ordered by class ID)."""
    return class_id in RUNES and class_id >= _BY_CODE[minimum]
