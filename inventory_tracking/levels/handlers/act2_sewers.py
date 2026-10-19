"""Lut Gholein sewers 1-3 and the Ancient Tunnels: stairs, waypoint, Radament, the chest, the way back.

Unconfirmed (D2MOO DRLGMAZE_ScanReplaceSpecialAct2SewersPresets).
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous, stairs_down, waypoint
from inventory_tracking.levels.model import SUPER_CHEST


SEWER = 'Act 2 - Sewer'

HANDLERS = [
    stairs_down(
        'Sewers 1',
        areas={47},
        family=SEWER,
        extra=[PoiSpec('Lut Gholein', rf'{SEWER} Prev (E|NS)', 'previous', family=SEWER, each=True)],
    ),
    stairs_down('Sewers 2', areas={48}, family=SEWER, extra=[waypoint(SEWER), previous(SEWER, 'Sewers 1')]),
    Handler(
        'Sewers 3',
        frozenset({49}),
        (PoiSpec('Radament', rf"{SEWER} Radament's Lair [NSEW]", family=SEWER), previous(SEWER, 'Sewers 2')),
    ),
    Handler(
        'Ancient Tunnels',
        frozenset({65}),
        (PoiSpec('Chest', rf'{SEWER} Chest [NSEW]', family=SEWER, thing=SUPER_CHEST), previous(SEWER, 'Lost City')),
    ),
]
