"""Tamoe Highland → Pit 1 → Pit 2: the cave mouth, the stairs down and the way back.

Confirmed by the user in game 2026-09-30 (from D2MOO DrlgOutWild/DrlgMaze and d2data levels). A wilderness
level places one cave exit: 'Cave Entrance', or a cliff cave ('Wild Cliff Cave Left/Right') when
its grid has a cliff spot. Pit 1's stairs down are 'Cave Down' (Act 1 caves use 'Next' only in
the Underground Passage). Pit 2 is one fixed preset ('Cave Treasure 5', DrlgType 2) covering the
level, like the Countess's: no handler.
Tamoe's border gaps (2026-10-01, unconfirmed): D2MOO gAct1MonasteryDrlgLink links Tamoe to the
Monastery Gate (26) and Black Marsh (6) to Tamoe; borders come from the same
DRLGOUTPLACE_PlaceAct1245OutdoorBorders as Black Marsh and Cold Plains (handler.ExitsHandler).
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec, previous, stairs_down


CAVE = 'Act 1 - Cave'

HANDLERS = [
    ExitsHandler(
        'Tamoe Highland',
        frozenset({7}),
        (PoiSpec('Pit', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),),
        confirmed=True,  # the Pit entrance; the exits are unconfirmed
        exits=(Exit(26, 'Monastery Gate'), Exit(6, 'Black Marsh', 'previous')),
    ),
    stairs_down(
        'Pit Level 1', areas={12}, family=CAVE, word='Down', extra=[previous(CAVE, 'Tamoe Highland')], confirmed=True
    ),
]
