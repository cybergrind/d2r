"""Black Marsh: the Forgotten Tower first (user, 2026-10-10), the gaps to Tamoe Highland and Dark Wood.

Exits from D2MOO gAct1MonasteryDrlgLink. The waypoint is an object, not a preset: not marked.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Black Marsh',
        frozenset({6}),
        (PoiSpec('Forgotten Tower', r'Act 1 - Tower 1', 'stairs'),),
        confirmed=True,  # the tower only
        exits=(Exit(7, 'Tamoe Highland'), Exit(5, 'Dark Wood', 'previous')),
        pois_first=True,
    )
]
