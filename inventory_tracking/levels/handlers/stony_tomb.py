"""Rocky Waste → Stony Tomb 1-2: the tomb entrance, the stairs down, the super chest, Creeping Feature.

Unconfirmed (D2MOO DrlgOutDesr/DrlgMaze). 'Tomb Leatherarm' is Creeping Feature (allstrings).
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous, stairs_down, target


TOMB = 'Act 2 - Tomb'

HANDLERS = [
    target('Rocky Waste', areas={41}, label='Stony Tomb', preset=r'Act 2 - Desert Tomb 1', kind='stairs'),
    stairs_down('Stony Tomb 1', areas={55}, family=TOMB, extra=[previous(TOMB, 'Rocky Waste')]),
    Handler(
        'Stony Tomb 2',
        frozenset({59}),
        (
            PoiSpec('Treasure', rf'{TOMB} Treasure [NSEW]', family=TOMB),
            PoiSpec('Creeping Feature', rf'{TOMB} Leatherarm [NSEW]', family=TOMB),
            previous(TOMB, 'Stony Tomb 1'),
        ),
    ),
]
