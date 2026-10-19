"""Den of Evil, Underground Passage 1, Hole 1, the Crypt and the Mausoleum.

The Underground Passage's 'Cave Next' is taken to be Vis1 (Dark Wood), 'Cave Prev' Vis0.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous, stairs_down
from inventory_tracking.levels.model import SUPER_CHEST


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
        (
            PoiSpec('Chest', rf'{CRYPT} Chest [NSEW]', family=CRYPT, thing=SUPER_CHEST),
            previous(CRYPT, 'Burial Grounds'),
        ),
    ),
]
