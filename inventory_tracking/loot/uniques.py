"""Which expensive unique or set item a unique- or set-quality drop can be, by its base item (data/uniques.json,
built by build_uniques.py from the dated ask table and the item decoder's tables)."""

import json
from pathlib import Path


_TABLE = json.loads((Path(__file__).parent / 'data' / 'uniques.json').read_text())
BASES: dict[int, dict] = {int(class_id): base for class_id, base in _TABLE['bases'].items()}
ASKS_DATE = _TABLE['date']
SET_QUALITY, UNIQUE_QUALITY = 5, 7
KINDS = {SET_QUALITY: ('sets', 'Set'), UNIQUE_QUALITY: ('uniques', 'Unique')}


def unique_drop(
    class_id: int,
    *,
    minimum: float,
    table_id: int | None = None,
    identified: bool = False,
    quality: int = UNIQUE_QUALITY,
) -> str | None:
    """The row label for a unique- or set-quality item of this base, or None when it is not worth a mark.

    Worth a mark: some unique (set item, for set quality) of the base asks `minimum` Ist or more
    for a good roll. `table_id`
    (ItemData +0x34) names the unique only when it is one of this base; unidentified, it never
    hides a mark, because that field is unconfirmed before identification.
    """
    base = BASES.get(class_id)
    if base is None or quality not in KINDS:
        return None
    key, word = KINDS[quality]
    uniques = base[key]
    if not uniques:
        return None
    exact = next((unique for unique in uniques if unique['id'] == table_id), None)
    if identified and exact is not None:
        return exact['name'] if (exact['high'] or 0) >= minimum else None
    dearest = max(uniques, key=lambda unique: unique['high'] or 0)
    if (dearest['high'] or 0) < minimum:
        return None
    if exact is not None:
        return exact['name']
    return dearest['name'] if len(uniques) == 1 else f'{word} {base["name"]} ({dearest["name"]}?)'
