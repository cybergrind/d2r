"""Cathedral → Catacombs 1-3 → Andariel: the next level, the Catacombs 2 waypoint and the way back.

Confirmed 2026-09-30: the user checked the arrows in game; fixtures catacombs_2 and _3 come
from automatic evidence (Catacombs 1 uses the same helpers, no fixture of its own yet).
'Catacombs Prev EW/NS' are the stairs up; 'Prev NSEW' (CatNSEWExit) is Catacombs 1's exit to
the Cathedral. Catacombs 4 is one fixed preset ('Act 1 - Andariel', the whole level): no handler.
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
