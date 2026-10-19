"""Worldstone Keep 1-3: the next level, the WSK 2 waypoint and the way back; the Throne of Destruction.

The Throne mark is where to fight the waves from (user, 2026-10-11: "west-north off actual throne");
measurements in history/handlers_worldstone_keep.md.
"""

from inventory_tracking.levels.handler import PoiSpec, previous, stairs_down, target, waypoint
from inventory_tracking.levels.model import THRONE_PORTAL


BAAL = 'Act 5 - Baal'
THRONE_STAND = (82, 14)

HANDLERS = [
    stairs_down('Worldstone Keep 1', areas={128}, family=BAAL, extra=[previous(BAAL, 'Arreat Summit')], confirmed=True),
    stairs_down(
        'Worldstone Keep 2',
        areas={129},
        family=BAAL,
        extra=[waypoint(BAAL), previous(BAAL, 'Worldstone Keep 1')],
        confirmed=True,
    ),
    stairs_down(
        'Worldstone Keep 3', areas={130}, family=BAAL, extra=[previous(BAAL, 'Worldstone Keep 2')], confirmed=True
    ),
    target(
        'Throne of Destruction',
        areas={131},
        label='Throne',
        preset=r'Act 5 - ThroneRoom',
        at=THRONE_STAND,
        # The portal Baal leaves by (`FinalPortal`): the routes' way on (routes.md).
        extra=[PoiSpec('Worldstone Chamber', r'Act 5 - ThroneRoom', thing=THRONE_PORTAL)],
    ),
]
