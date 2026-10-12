"""Palace Cellar 1: the waypoint room.

Unconfirmed (D2MOO DRLGMAZE_PickRoomPreset, 2026-10-01; no evidence yet). The Harem 2 and Palace
Cellar levels are built only from the four diagonal presets ('Corrupt Harem'/'Basement' NE, SE,
SW, NW), so their stairs aren't separate rooms. In Palace Cellar 1 the 'Basement NW' room uses
DS1 file 2 (CelNWWaypoint.ds1). Harem 1 is one fixed preset; Palace Cellar 3's NW/SE rooms use a
file 3: the SE one holds the Arcane portal (below); the NW one's content isn't known.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec
from inventory_tracking.levels.model import ARCANE_PORTAL


HANDLERS = [
    Handler(
        'Palace Cellar 1',
        frozenset({52}),
        (PoiSpec('Waypoint', r'Act 2 - Basement NW', 'waypoint', optional=True, variants=(2,)),),
    ),
    # The portal to the Arcane Sanctuary: the 'Basement SE' room of DS1 file 3 holds it at (73, 73)
    # (levels/data/preset_objects.json, 2026-10-12). Unconfirmed.
    Handler(
        'Palace Cellar 3',
        frozenset({54}),
        (PoiSpec('Arcane Sanctuary', r'Act 2 - Basement SE', 'stairs', variants=(3,), thing=ARCANE_PORTAL),),
    ),
]
