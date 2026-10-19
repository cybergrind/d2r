"""Act 2 desert levels: the dungeon entrance in each, the Dark Elder ruin and the Canyon tombs.

All seven Canyon tombs are marked: the true one isn't in the room data (D2MOO DrlgOutDesr).
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, target


def entrance(name, area, label, preset):
    return target(name, areas={area}, label=label, preset=preset, kind='stairs')


HANDLERS = [
    entrance('Dry Hills', 42, 'Halls of the Dead', r'Act 2 - Desert Tomb 1'),
    entrance('Far Oasis', 43, 'Maggot Lair', r'Act 2 - Desert Lair 1'),
    Handler(
        'Lost City',
        frozenset({44}),
        (
            PoiSpec('Ancient Tunnels', r'Act 2 - Desert Ruins Sewer', 'stairs'),
            PoiSpec('Dark Elder', r'Act 2 - Desert Ruins Elder', optional=True),
        ),
    ),
    entrance('Valley of Snakes', 45, 'Claw Viper Temple', r'Act 2 - Desert Tomb 2'),
    Handler(
        'Canyon of the Magi',
        frozenset({46}),
        (
            PoiSpec('Tomb', r'Act 2 - Desert Cliff (Right|Left|Top) King Tomb', 'stairs', each=True),
            PoiSpec('Waypoint', r'Act 2 - Desert Valley Warp', 'waypoint', optional=True),
        ),
    ),
]
