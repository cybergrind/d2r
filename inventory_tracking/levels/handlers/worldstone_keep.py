"""Worldstone Keep 1-3 (Baal): the next level, the WSK 2 waypoint and the way back.

Evidence (Win+C dumps, fixtures worldstone_keep_2 and _3, 2026-09-30): one 'Baal Next',
one 'Baal Prev' and, in WSK 2, one 'Baal Waypoint', each a 16x16 preset in four 8x8 chunks.
WSK 3's stairs down lead to the Throne of Destruction, a single whole-level preset
('Act 5 - ThroneRoom', like the Worldstone Chamber). Confirmed in game
2026-09-30 by the user (WSK 1 has no fixture of its own yet).

Throne of Destruction (131): the mark is the hall before Baal's throne, so teleport steps rush
there (user, 2026-10-10 night). The layout file (expansion/baallair/wthrone.ds1, read from the
install 2026-10-10) seats `baalthrone` at (90, 11) units from the preset's origin, at the head of a
hall whose torches stand at x 89 and 99 from y 24 to 64; the mark is the hall's middle, (94, 40).
In the two runs of that night the waves were fought from (74 to 102, 26 to 50). Unconfirmed: the
level has no dump yet, so how its rooms read (one block or not) is not known.
"""

from inventory_tracking.levels.handler import previous, stairs_down, target, waypoint


BAAL = 'Act 5 - Baal'
THRONE_HALL = (94, 40)

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
    target('Throne of Destruction', areas={131}, label='Throne', preset=r'Act 5 - ThroneRoom', at=THRONE_HALL),
]
