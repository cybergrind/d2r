"""City of the Damned: the stairs down to the River of Flame and the gap back to the Plains.

Unconfirmed (from D2MOO DrlgOutdoors and d2data, 2026-10-01; no evidence yet). 'Act 4 - Mesa
Warp' (8x8, WarpLava*.ds1) is spawned only in this level: the stairs to the River of Flame
(levels.json Vis1 = 107, Warp1 = 69). The Plains link is an open Act 4 border gap (file 3),
named by elimination while unread. The waypoint (levels.json Waypoint 28) has no named
preset, so it isn't marked.
"""

from inventory_tracking.levels.handler import ACT4_GAP, Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'City of the Damned',
        frozenset({106}),
        (PoiSpec('River of Flame', r'Act 4 - Mesa Warp', 'stairs'),),
        exits=(Exit(105, 'Plains of Despair', 'previous'),),
        gap=ACT4_GAP,
        gap_variants=(3,),
    )
]
