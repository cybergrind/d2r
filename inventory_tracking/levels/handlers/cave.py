"""Cold Plains → Cave 1 → Cave 2: the stairs down, Coldcrow and the way back.

Confirmed 2026-09-30 (fixture cave_1; the user walked the whole level). From D2MOO DrlgMaze: Every Act 1 cave places one
'Cave Prev' room and one 'Cave Down' room (Den of Evil and the Underground Passage differ);
Cave 1 also places 'Cave Coldcrow'. Cave 2 is one fixed preset ('Cave Treasure 2', DrlgType 2)
covering the level, like Pit 2: no handler.
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
