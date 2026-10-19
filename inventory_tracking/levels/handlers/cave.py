"""Cave 1: the stairs down, Coldcrow and the way back (confirmed 2026-09-30, fixture cave_1; D2MOO DrlgMaze).

Cave 2 is in treasure_levels.py.
"""

from inventory_tracking.levels.handler import PoiSpec, previous, stairs_down


CAVE = 'Act 1 - Cave'

HANDLERS = [
    stairs_down(
        'Cave Level 1',
        areas={9},
        family=CAVE,
        word='Down',
        extra=[PoiSpec('Coldcrow', rf'{CAVE} Coldcrow [NSEW]', family=CAVE), previous(CAVE, 'Cold Plains')],
        confirmed=True,
    )
]
