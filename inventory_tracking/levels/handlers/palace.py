"""Palace Cellar 1's waypoint room and Palace Cellar 3's Arcane portal (D2MOO DRLGMAZE_PickRoomPreset).

The cellars' stairs aren't separate rooms: they are built only from four diagonal presets. Unconfirmed.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec
from inventory_tracking.levels.model import ARCANE_PORTAL


HANDLERS = [
    Handler(
        'Palace Cellar 1',
        frozenset({52}),
        (PoiSpec('Waypoint', r'Act 2 - Basement NW', 'waypoint', optional=True, variants=(2,)),),
    ),
    Handler(
        'Palace Cellar 3',
        frozenset({54}),
        (PoiSpec('Arcane Sanctuary', r'Act 2 - Basement SE', 'stairs', variants=(3,), thing=ARCANE_PORTAL),),
    ),
]
