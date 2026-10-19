"""Tamoe Highland → Pit 1: the cave mouth, the stairs down and the way back (D2MOO DrlgOutWild/DrlgMaze).

Tamoe's one open gap is Black Marsh; the Monastery Gate side is plain terrain levels/exits.py marks
(14 evidence entries, 2026-10-06).
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec, previous, stairs_down


CAVE = 'Act 1 - Cave'

HANDLERS = [
    ExitsHandler(
        'Tamoe Highland',
        frozenset({7}),
        (PoiSpec('Pit', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),),
        confirmed=True,  # the Pit entrance only
        exits=(Exit(6, 'Black Marsh', 'previous'),),
    ),
    stairs_down(
        'Pit Level 1', areas={12}, family=CAVE, word='Down', extra=[previous(CAVE, 'Tamoe Highland')], confirmed=True
    ),
]
