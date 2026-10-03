"""Sewers 1 (Kurast): the drain down to Sewers 2, the chest room and every way up.

Unconfirmed (D2MOO DrlgMaze, 2026-10-01; no evidence yet). Sewers 1 replaces its SW, SE, NW and NE
rooms with 'Sewer Prev …' (the four ladders up: two into Kurast Bazaar, two into Upper Kurast;
which is which isn't known), then places one 'Sewer Drain' (to Sewers 2) and one 'Sewer Chest'.
Sewers 2 (Khalim's Heart) is one 'Sewer Treasure X' preset covering the level: no handler.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec


SEWER = 'Act 3 - Sewer'

HANDLERS = [
    Handler(
        'Sewers 1',
        frozenset({92}),
        (
            PoiSpec('Sewers 2', rf'{SEWER} Drain [NSEW]', 'stairs', family=SEWER),
            PoiSpec('Chest', rf'{SEWER} Chest [NSEW]', family=SEWER),
            PoiSpec('Way up', rf'{SEWER} Prev (SW|SE|NW|NE)', 'previous', family=SEWER, each=True),
        ),
    )
]
