"""Durance of Hate 1-2: stairs down, plus the Durance 2 waypoint when present.

Confirmed 2026-09-30 on Durance 2 (fixture durance_of_hate_2; the user checked the direction).

d2data gives these levels LevelType "Act 3 - Kurast", but their rooms are the "Act 3 -
Mephisto" family. Durance 3 is one fixed room (Mephisto Complex) and has no room-level POI.
"""

from inventory_tracking.levels.handler import stairs_down, waypoint


HANDLERS = [
    stairs_down(
        'Durance of Hate 1-2',
        areas={100, 101},
        family='Act 3 - Mephisto',
        extra=[waypoint('Act 3 - Mephisto')],
        confirmed=True,
    )
]
