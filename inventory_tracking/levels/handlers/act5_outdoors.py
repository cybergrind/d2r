"""Bloody Foothills, Frigid Highlands, Arreat Plateau and Frozen Tundra.

Unconfirmed (D2MOO DrlgOutSiege, 2026-10-01; no evidence yet). Bloody Foothills is a row of 16x48
siege strips from 'Siege To Town' (Harrogath) to 'Siege To Barricade' (Frigid Highlands).
Frigid Highlands starts at 'Barricade To Siege'. Barricade levels place 'Barricade Entrance/
Exit' presets on their level-link edges (which neighbour each leads to isn't known, so they
are plain exits), may place a hell portal ('Barricade Hell Portal N/W': Abaddon, the Pit of
Acheron, the Infernal Pit) and a waypoint preset (Arreat Plateau dirt, Frozen Tundra snow;
the Frigid Highlands waypoint has no preset of its own). Arreat Plateau's 'Barricade To Cave'
leads to the Crystalline Passage; Frozen Tundra's snow 'From Cave' is the Glacial Trail side
and 'To Cave' the Ancients' Way.
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
