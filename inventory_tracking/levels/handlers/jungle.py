"""Spider Forest, Great Marsh and Flayer Jungle: the waypoint clearing.

Unconfirmed (from D2MOO DrlgOutJung/DrlgOutPlace, 2026-10-01). A jungle level is a column of 32x32
'Jungle …' presets; its special spots are up to three clearings ('Clearing Webby' in Spider
Forest, 'Boggy' in Great Marsh, 'Pygmy' in Flayer Jungle), each given a different DS1 file
(0, 1, 2) by a seeded permutation. In Spider Forest and Flayer Jungle files 0 and 1 hold the cave
warps (Spider Cave and Spider Cavern; Swampy Pit and Flayer Dungeon; levels/data/preset_warps.json),
which the generic rule names (levels/exits.py, 2026-10-06); file 2 has no warp and is taken to be
the waypoint clearing. Great Marsh has no caves, so which of its clearings holds the waypoint is
not known: every clearing is marked.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec


def clearing(kind):
    return rf'Act 3 - Clearing {kind} [NSEW]+'


def caves(name, area, kind):
    spec = PoiSpec('Waypoint', clearing(kind), 'waypoint', optional=True, variants=(2,))
    return Handler(name, frozenset({area}), (spec,))


HANDLERS = [
    caves('Spider Forest', 76, 'Webby'),
    Handler('Great Marsh', frozenset({77}), (PoiSpec('Clearing', clearing('Boggy'), each=True),)),
    caves('Flayer Jungle', 78, 'Pygmy'),
]
