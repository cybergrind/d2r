"""Act 2 desert levels: the dungeon entrance in each, the Dark Elder ruin and the Canyon tombs.

Unconfirmed (from D2MOO DrlgOutDesr, 2026-10-01; no evidence yet). DRLGOUTDESR_AddExits gives each
level one exit preset: Dry Hills 'Desert Tomb 1' (Halls of the Dead; Rocky Waste has its own
handler), Far Oasis 'Desert Lair 1' (Maggot Lair), Lost City 'Desert Ruins Sewer' (Ancient
Tunnels), Valley of Snakes 'Desert Tomb 2' (Claw Viper Temple). Lost City may also place 'Desert
Ruins Elder', the Dark Elder's ruin. The Canyon of the Magi (DRLGOUTDESR_PlaceTombEntriesInCanyon)
has seven 'Desert Cliff … King Tomb' entrances (which one is the true tomb isn't in the room
data) and 'Desert Valley Warp' in the centre, taken to be the waypoint. Act 2 border presets
have no open variant and the outdoor waypoints are objects, not presets, so neither is marked.
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
