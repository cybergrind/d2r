"""Halls of Anguish and Halls of Pain (Death's Calling): the stairs-down quadrant.

Confirmed 2026-09-30 in Halls of Pain (fixtures halls_of_pain_nw_down, halls_of_pain_live; the
user checked the direction in game).

Each level is four 40x40 Temple quadrants (NE, SE up, NW/SW Down, SW/NE Waypoint), each
split into 25 8x8 Room2 chunks; the POI is the whole 'Down' quadrant (dump
20260930T082324Z-9fecf33f). The Temple family has no "Next" preset.
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target(
        'Halls of Anguish/Pain',
        areas={122, 123},
        label='Next level',
        preset=r'Act 5 - Temple (NE|NW|SW) Down',
        kind='stairs',
        confirmed=True,
    )
]
