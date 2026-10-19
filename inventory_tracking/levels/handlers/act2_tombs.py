"""Halls of the Dead 1-3 and Claw Viper Temple 1: stairs, waypoint, the Horadric Cube, the way back.

Unconfirmed (D2MOO DRLGMAZE_PlaceAct2TombStuff). Claw Viper Temple 2 is in boss_lairs.py.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous, stairs_down, waypoint


TOMB = 'Act 2 - Tomb'

HANDLERS = [
    stairs_down('Halls of the Dead 1', areas={56}, family=TOMB, extra=[previous(TOMB, 'Dry Hills')]),
    stairs_down(
        'Halls of the Dead 2', areas={57}, family=TOMB, extra=[waypoint(TOMB), previous(TOMB, 'Halls of the Dead 1')]
    ),
    Handler(
        'Halls of the Dead 3',
        frozenset({60}),
        (PoiSpec('Horadric Cube', rf'{TOMB} Cube [NSEW]', family=TOMB), previous(TOMB, 'Halls of the Dead 2')),
    ),
    stairs_down('Claw Viper Temple 1', areas={58}, family=TOMB, extra=[previous(TOMB, 'Valley of Snakes')]),
]
