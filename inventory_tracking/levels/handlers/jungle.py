"""Spider Forest, Great Marsh and Flayer Jungle: every clearing.

Unconfirmed (from D2MOO DrlgOutJung/DrlgOutPlace, 2026-10-01; no evidence yet). A jungle level is
a column of 32x32 'Jungle …' presets; its special spots are up to three clearings ('Clearing
Webby' in Spider Forest, 'Boggy' in Great Marsh, 'Pygmy' in Flayer Jungle), each given a
different DS1 file (0, 1, 2) by a seeded permutation. The cave entrances (Spider Cave and
Spider Cavern; Swampy Pit and Flayer Dungeon) and the waypoint are in those clearings, but which
file holds which is not known without evidence, so every clearing is marked the same way.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec


def clearings(name, area, kind, label):
    return Handler(name, frozenset({area}), (PoiSpec(label, rf'Act 3 - Clearing {kind} [NSEW]+', 'stairs', each=True),))


HANDLERS = [
    clearings('Spider Forest', 76, 'Webby', 'Cave or waypoint'),
    clearings('Great Marsh', 77, 'Boggy', 'Clearing'),
    clearings('Flayer Jungle', 78, 'Pygmy', 'Dungeon or waypoint'),
]
