"""Kurast Sewers 1: the drain down, the chest and the four ladders up (which leads where isn't known)."""

from inventory_tracking.levels.handler import Handler, PoiSpec
from inventory_tracking.levels.model import SUPER_CHEST


SEWER = 'Act 3 - Sewer'

HANDLERS = [
    Handler(
        'Sewers 1',
        frozenset({92}),
        (
            PoiSpec('Sewers 2', rf'{SEWER} Drain [NSEW]', 'stairs', family=SEWER),
            PoiSpec('Chest', rf'{SEWER} Chest [NSEW]', family=SEWER, thing=SUPER_CHEST),
            PoiSpec('Way up', rf'{SEWER} Prev (SW|SE|NW|NE)', 'previous', family=SEWER, each=True),
        ),
    )
]
