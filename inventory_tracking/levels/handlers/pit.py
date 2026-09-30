"""Tamoe Highland → Pit 1 → Pit 2: the cave mouth, the stairs down and the way back.

Confirmed by the user in game 2026-09-30 (from D2MOO DrlgOutWild/DrlgMaze and d2data levels). A wilderness
level places one cave exit: 'Cave Entrance', or a cliff cave ('Wild Cliff Cave Left/Right') when
its grid has a cliff spot. Pit 1's stairs down are 'Cave Down' (Act 1 caves use 'Next' only in
the Underground Passage). Pit 2 is one fixed preset ('Cave Treasure 5', DrlgType 2) covering the
level, like the Countess's: no handler.
"""

from inventory_tracking.levels.handler import previous, stairs_down, target


CAVE = 'Act 1 - Cave'

HANDLERS = [
    target(
        'Tamoe Highland',
        areas={7},
        label='Pit',
        preset=r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))',
        kind='stairs',
        confirmed=True,
    ),
    stairs_down(
        'Pit Level 1', areas={12}, family=CAVE, word='Down', extra=[previous(CAVE, 'Tamoe Highland')], confirmed=True
    ),
]
