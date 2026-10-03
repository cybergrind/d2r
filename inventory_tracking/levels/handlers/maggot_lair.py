"""Maggot Lair 1-3: the stairs down, Coldworm's room and the way back.

Levels 1-2 unconfirmed (D2MOO DRLGMAZE_PlaceAct2LairStuff, 2026-10-01): 'Lair Prev' and 'Lair Next'.
Level 3 places 'Lair Prev', 'Lair Tight Spot S' (MagQueen.ds1: Coldworm the Burrower and the
Staff of Kings chest) and 'Lair Treasure W' (a treasure room). Coldworm confirmed 2026-10-01: the
user pressed Win+C standing at Coldworm, in the Tight Spot room (fixture maggot_lair_3_coldworm).
The first version pointed at Treasure W.
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
