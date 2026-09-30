"""River of Flame: Hephasto at the Hellforge, the bridge to the Chaos Sanctum and the way back.

Unconfirmed (from D2MOO DRLGMAZE_PlaceAct4Lava and d2data, 2026-10-01; no evidence yet). A Lava
maze of 24x24 presets: 'Lava Warp N' leads up to the City of the Damned, 'Bridge 1' starts the
bridge north to the Chaos Sanctum (then two 'Bridge 2'), and one 'Lava W' or 'Lava E' room is
replaced by 'Lava Forge W/E', the Hellforge where Hephasto stands. No preset is named for the
waypoint (levels.json Waypoint 29), so it isn't marked.
"""

from inventory_tracking.levels.handler import PoiSpec, target


HANDLERS = [
    target(
        'River of Flame',
        areas={107},
        label='Hephasto',
        preset=r'Act 4 - Lava Forge [WE]',
        extra=[
            PoiSpec('Chaos Sanctum', r'Act 4 - Bridge 1', 'stairs'),
            PoiSpec('City of the Damned', r'Act 4 - Lava Warp N', 'previous'),
        ],
    )
]
