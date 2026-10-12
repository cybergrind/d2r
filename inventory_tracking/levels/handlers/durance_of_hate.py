"""Durance of Hate 1-2: stairs down, plus the Durance 2 waypoint when present; Mephisto on level 3.

Confirmed 2026-09-30 on Durance 2 (fixture durance_of_hate_2; the user checked the direction).

d2data gives these levels LevelType "Act 3 - Kurast", but their rooms are the "Act 3 -
Mephisto" family.

Durance 3 is one preset, 'Mephisto Complex', covering the whole level, so the preset itself gives
no direction. It has one layout (Act3/Travincal/MephComp.ds1, read from the install 2026-10-11),
which places the monster `mephisto` at (40, 65) units from the preset's origin: the level's first
mark, so the teleport step goes to him (user, 2026-10-11). Unconfirmed: the level has no dump yet.
The same file places the red portal to act 4 (`HellGate`, on the bridge at (102, 69)): the second
mark, for the routes (routes.md, 2026-10-12).
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
