"""Spider Forest, Great Marsh and Flayer Jungle: the waypoint clearing.

Clearing files 0 and 1 hold the cave warps, so file 2 is taken to be the waypoint (D2MOO DrlgOutJung).
Great Marsh has no caves: every clearing is marked.
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
