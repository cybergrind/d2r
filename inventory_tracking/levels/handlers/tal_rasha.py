"""Tal Rasha's Tombs (areas 66-72): the Orifice in the true tomb, the way back in every tomb.

Confirmed 2026-09-30 with Win+C dump 20260930T154636Z-55eebd5c (fixture tal_rasha_true_tomb,
area 70): the true tomb holds 'Act 2 - Tomb Talrasha S' (16x16), and the orifice object
(objects.json 152) stood in it. D2MOO DrlgMaze places the Talrasha room only in the staff tomb
(so the Orifice is optional: the six false tombs are quiet), and a 'Tomb Prev' room, the way back
to the Canyon of the Magi, in every tomb.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous


TOMB = 'Act 2 - Tomb'

HANDLERS = [
    Handler(
        "Tal Rasha's Tombs",
        frozenset(range(66, 73)),
        (
            PoiSpec('Orifice', rf'{TOMB} Talrasha [NSEW]', optional=True, family=TOMB),
            previous(TOMB, 'Canyon of the Magi'),
        ),
        confirmed=True,
    )
]
