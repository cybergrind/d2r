"""Which levels a route may start in and which touch each other without a door.

WAYPOINTS: levels.txt `Waypoint` (d2data levels.json, read 2026-10-12). BORDERS: outdoor levels
joined edge to edge, which levels.txt's Vis slots (levels/presets.py LEVEL_LINKS) do not list:
the act's first level beside its town, and the pairs the handlers name by border gap or border
rooms (levels/handlers/cold_plains.py, pit.py, desert.py, kurast.py, outer_steppes.py,
act5_outdoors.py). Only the pairs a route uses are here.
"""

from inventory_tracking.levels.presets import LEVEL_LINKS


TOWNS = frozenset((1, 40, 75, 103, 109))
WAYPOINTS = frozenset((
    *TOWNS, 3, 4, 5, 6, 27, 29, 32, 35, 42, 43, 44, 46, 48, 52, 57, 74, 76, 77, 78, 79, 80, 81, 83, 101,
    106, 107, 111, 112, 113, 115, 117, 118, 123, 129,
))  # fmt: skip
BORDERS = frozenset(
    frozenset(pair)
    for pair in (
        (1, 2), (3, 17), (26, 7), (40, 41), (44, 45), (75, 76), (81, 82), (82, 83), (103, 104), (104, 105),
        (109, 110), (110, 111),
    )
)  # fmt: skip


def linked(area: int, to: int) -> bool:
    """Whether level `to` is entered straight from `area`: by a door (levels.txt) or across a border."""
    return to in LEVEL_LINKS.get(area, ()) or frozenset((area, to)) in BORDERS
