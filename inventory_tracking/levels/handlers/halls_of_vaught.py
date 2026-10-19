"""Halls of Vaught: Nihlathak, on the side the layout variant names (NihlE/N/S/W; confirmed 2026-09-30).

The mark is off his pack (user, 2026-10-11: "position our last jump somewhere off the main mob pack");
measurements in history/handlers_halls_of_vaught.md.
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target(
        'Halls of Vaught',
        areas={124},
        label='Nihlathak',
        preset=r'Act 5 - Temple Final Room',
        sides=('E', 'N', 'S', 'W'),
        inset=0.06,
        stand=(3, -1),
        confirmed=True,
    )
]
