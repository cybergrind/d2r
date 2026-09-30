"""Worldstone Keep 1-3 (Baal): the next level, the WSK 2 waypoint and the way back.

Evidence (Win+C dumps, fixtures worldstone_keep_2 and _3, 2026-09-30): one 'Baal Next',
one 'Baal Prev' and, in WSK 2, one 'Baal Waypoint', each a 16x16 preset in four 8x8 chunks.
WSK 3's stairs down lead to the Throne of Destruction, a single whole-level preset
('Act 5 - ThroneRoom', like the Worldstone Chamber): no handler there. Confirmed in game
2026-09-30 by the user (WSK 1 has no fixture of its own yet).
"""

from inventory_tracking.levels.handler import previous, stairs_down, waypoint


BAAL = 'Act 5 - Baal'

HANDLERS = [
    stairs_down('Worldstone Keep 1', areas={128}, family=BAAL, extra=[previous(BAAL, 'Arreat Summit')], confirmed=True),
    stairs_down(
        'Worldstone Keep 2',
        areas={129},
        family=BAAL,
        extra=[waypoint(BAAL), previous(BAAL, 'Worldstone Keep 1')],
        confirmed=True,
    ),
    stairs_down(
        'Worldstone Keep 3', areas={130}, family=BAAL, extra=[previous(BAAL, 'Worldstone Keep 2')], confirmed=True
    ),
]
