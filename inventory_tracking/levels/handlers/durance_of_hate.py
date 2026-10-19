"""Durance of Hate 1-2: stairs down and the waypoint; on level 3 Mephisto first (user, 2026-10-11), then the red portal.

Rooms are the "Act 3 - Mephisto" family, though d2data's LevelType says Kurast.
"""

from inventory_tracking.levels.handler import PoiSpec, stairs_down, target, waypoint
from inventory_tracking.levels.model import HELL_GATE


MEPHISTO = (40, 65)

HANDLERS = [
    stairs_down(
        'Durance of Hate 1-2',
        areas={100, 101},
        family='Act 3 - Mephisto',
        extra=[waypoint('Act 3 - Mephisto')],
        confirmed=True,
    ),
    target(
        'Durance of Hate 3',
        areas={102},
        label='Mephisto',
        preset=r'Act 3 - Mephisto Complex',
        at=MEPHISTO,
        extra=[PoiSpec('Red portal', r'Act 3 - Mephisto Complex', thing=HELL_GATE)],
    ),
]
