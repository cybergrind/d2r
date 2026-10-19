"""Catacombs 1-3: the next level, the Catacombs 2 waypoint and the way back.

Confirmed 2026-09-30 (fixtures catacombs_2, _3). Catacombs 4 is in boss_lairs.py.
"""

from inventory_tracking.levels.handler import previous, stairs_down, waypoint


CATACOMBS = 'Act 1 - Catacombs'

HANDLERS = [
    stairs_down('Catacombs 1', areas={34}, family=CATACOMBS, extra=[previous(CATACOMBS, 'Cathedral')], confirmed=True),
    stairs_down(
        'Catacombs 2',
        areas={35},
        family=CATACOMBS,
        extra=[waypoint(CATACOMBS), previous(CATACOMBS, 'Catacombs 1')],
        confirmed=True,
    ),
    stairs_down(
        'Catacombs 3', areas={36}, family=CATACOMBS, extra=[previous(CATACOMBS, 'Catacombs 2')], confirmed=True
    ),
]
