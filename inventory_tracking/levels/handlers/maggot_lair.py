"""Maggot Lair 1-3: the stairs down, Coldworm's room and the way back.

Coldworm is in 'Lair Tight Spot S', not 'Treasure W' (fixture maggot_lair_3_coldworm).
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous, stairs_down


LAIR = 'Act 2 - Lair'

HANDLERS = [
    stairs_down('Maggot Lair 1', areas={62}, family=LAIR, extra=[previous(LAIR, 'Far Oasis')]),
    stairs_down('Maggot Lair 2', areas={63}, family=LAIR, extra=[previous(LAIR, 'Maggot Lair 1')]),
    Handler(
        'Maggot Lair 3',
        frozenset({64}),
        (
            PoiSpec('Coldworm', rf'{LAIR} Tight Spot S', family=LAIR),
            PoiSpec('Treasure room', rf'{LAIR} Treasure W', optional=True, family=LAIR),
            previous(LAIR, 'Maggot Lair 2'),
        ),
        confirmed=True,
    ),
]
