"""Tal Rasha's Tombs: the Orifice in the true tomb, Kaa or a chest in the others, the way back.

All optional: only the staff tomb has the Talrasha room (D2MOO DrlgMaze; fixture tal_rasha_true_tomb).
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous


TOMB = 'Act 2 - Tomb'

HANDLERS = [
    Handler(
        "Tal Rasha's Tombs",
        frozenset(range(66, 73)),
        (
            PoiSpec('Orifice', rf'{TOMB} Talrasha [NSEW]', optional=True, family=TOMB),
            PoiSpec('Ancient Kaa', rf'{TOMB} Kaa [NSEW]', optional=True, family=TOMB),
            PoiSpec('Chest', rf'{TOMB} Chest [NSEW]', optional=True, family=TOMB),
            previous(TOMB, 'Canyon of the Magi'),
        ),
        confirmed=True,
    )
]
