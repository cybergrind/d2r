"""Dark Wood: the Underground Passage and the gap to Black Marsh; the Tree of Inifuss is not marked."""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Dark Wood',
        frozenset({5}),
        (PoiSpec('Underground Passage', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),),
        exits=(Exit(6, 'Black Marsh'),),
    )
]
