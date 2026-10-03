"""Den of Evil, Underground Passage 1, Hole 1, the Crypt and the Mausoleum.

Unconfirmed (D2MOO DrlgMaze, 2026-10-01; no evidence yet). Every Act 1 cave places 'Cave Prev';
the Den of Evil adds 'Cave Den Of Evil' (Corpsefire's room) instead of stairs down; the others
place 'Cave Down'; the Underground Passage also places 'Cave Next', its second way up. Its two
ways up lead to Stony Field (levels.json Vis0) and the Dark Wood (Vis1); 'Prev' is taken to be
Vis0 and 'Next' Vis1. The Crypt places 'Crypt Prev' and 'Crypt Bonebreak', the Mausoleum
'Crypt Prev' and 'Crypt Chest'. Level 2s (Cave 2, Hole 2, Pit 2, Underground Passage 2) are
single fixed presets: no handler.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous, stairs_down


CAVE = 'Act 1 - Cave'
CRYPT = 'Act 1 - Crypt'

HANDLERS = [
    Handler(
        'Den of Evil',
        frozenset({8}),
        (PoiSpec('Corpsefire', rf'{CAVE} Den Of Evil [NSEW]', family=CAVE), previous(CAVE, 'Blood Moor')),
    ),
    Handler(
        'Underground Passage 1',
        frozenset({10}),
        (
            PoiSpec('Level 2', rf'{CAVE} Down [NSEW]', 'stairs', family=CAVE),
            PoiSpec('Dark Wood', rf'{CAVE} Next [NSEW]', 'stairs', family=CAVE),
            previous(CAVE, 'Stony Field'),
        ),
    ),
    stairs_down('Hole 1', areas={11}, family=CAVE, word='Down', extra=[previous(CAVE, 'Black Marsh')]),
    Handler(
        'Crypt',
        frozenset({18}),
        (PoiSpec('Bonebreak', rf'{CRYPT} Bonebreak [NSEW]', family=CRYPT), previous(CRYPT, 'Burial Grounds')),
    ),
    Handler(
        'Mausoleum',
        frozenset({19}),
        (PoiSpec('Chest', rf'{CRYPT} Chest [NSEW]', family=CRYPT), previous(CRYPT, 'Burial Grounds')),
    ),
]
