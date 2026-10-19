"""Cold Plains: the Cave and the border gaps to Stony Field, the Burial Grounds and Blood Moor.

A gap shows as 'Exit' until the player has been near it: its far level is read from Room2 neighbours.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Cold Plains',
        frozenset({3}),
        (PoiSpec('Cave', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),),
        exits=(Exit(4, 'Stony Field'), Exit(17, 'Burial Grounds', 'target'), Exit(2, 'Blood Moor', 'previous')),
    )
]
