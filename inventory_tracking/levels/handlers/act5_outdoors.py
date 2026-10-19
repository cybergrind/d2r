"""Bloody Foothills, Frigid Highlands, Arreat Plateau and Frozen Tundra.

'Barricade Entrance/Exit' are plain exits: which neighbour each leads to isn't known.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec


SIZE = '(32x16|16x32)'
EXITS = PoiSpec('Exit', rf'Act 5 - Barricade (Entrance|Exit) {SIZE}', 'exit', each=True)


def portal(label):
    return PoiSpec(label, r'Act 5 - Barricade Hell Portal [NW]', optional=True)


HANDLERS = [
    Handler(
        'Bloody Foothills',
        frozenset({110}),
        (
            PoiSpec('Frigid Highlands', r'Act 5 - Siege To Barricade', 'stairs'),
            PoiSpec('Harrogath', r'Act 5 - Siege To Town', 'previous'),
        ),
    ),
    Handler(
        'Frigid Highlands',
        frozenset({111}),
        (EXITS, portal('Abaddon'), PoiSpec('Bloody Foothills', r'Act 5 - Barricade To Siege', 'previous')),
    ),
    Handler(
        'Arreat Plateau',
        frozenset({112}),
        (
            PoiSpec('Crystalline Passage', rf'Act 5 - Barricade To Cave {SIZE}', 'stairs'),
            EXITS,
            portal('Pit of Acheron'),
            PoiSpec('Waypoint', r'Act 5 - Barricade Waypoint Dirt', 'waypoint', optional=True),
        ),
    ),
    Handler(
        'Frozen Tundra',
        frozenset({117}),
        (
            PoiSpec("Ancients' Way", rf'Act 5 - Barricade To Cave {SIZE} Snow', 'stairs'),
            EXITS,
            portal('Infernal Pit'),
            PoiSpec('Waypoint', r'Act 5 - Barricade Waypoint Snow', 'waypoint', optional=True),
            PoiSpec('Glacial Trail', rf'Act 5 - Barricade From Cave {SIZE} Snow', 'previous'),
        ),
    ),
]
