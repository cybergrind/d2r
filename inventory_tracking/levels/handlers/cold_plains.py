"""Cold Plains: the border gaps toward Stony Field, the Burial Grounds and back to Blood Moor.

Unconfirmed (2026-09-30). Evidence: five entries, three variant-3 'Wild Border' gaps each time
(Blood Moor north, Stony Field west, Burial Grounds east in that game). The level behind a gap
is read from its Room2 neighbours, which are only readable after the player has been near that
edge, so unknown gaps show as 'Exit' (handler.ExitsHandler). Area IDs from d2data levels.
The Cave entrance ('Act 1 - Cave Entrance' at 1120,1032 in that game) is marked after the exits.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Cold Plains',
        frozenset({3}),
        # The Cave: one 'Cave Entrance' (or a cliff cave, as in Tamoe Highland; D2MOO DrlgOutWild).
        (PoiSpec('Cave', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),),
        exits=(Exit(4, 'Stony Field'), Exit(17, 'Burial Grounds', 'target'), Exit(2, 'Blood Moor', 'previous')),
    )
]
