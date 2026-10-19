"""Halls of Anguish and Pain: the whole stairs-down quadrant and the waypoint quadrant (confirmed 2026-09-30)."""

from inventory_tracking.levels.handler import PoiSpec, target


HANDLERS = [
    target(
        'Halls of Anguish/Pain',
        areas={122, 123},
        label='Next level',
        preset=r'Act 5 - Temple (NE|NW|SW) Down',
        kind='stairs',
        extra=[PoiSpec('Waypoint', r'Act 5 - Temple [NS][EW] Waypoint', 'waypoint', optional=True)],
        confirmed=True,
    )
]
