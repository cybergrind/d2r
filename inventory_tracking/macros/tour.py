"""The order to explore a level's rooms in (the hunt's seek step): a short tour of rooms to stand in so every unexplored
room is seen (a room shows itself and its neighbours, terror/tracker.py `explore`). Distances are straight lines
between room centres: a teleport crosses what a walk goes around. History: history/tour.md.
"""

import math
from collections.abc import Collection, Sequence
from functools import lru_cache

from inventory_tracking.levels.geometry import Point


Bounds = tuple[int, int, int, int]  # a room's x, y, width, height in tiles
ROUNDS = 3  # passes of dropping and shifting stops, each followed by a reordering
# Tiles a new tour must save to replace the last one (a room's side): equal tours starting opposite ways would
# otherwise alternate.
KEEP_TILES = 8.0


def centre(room: Bounds) -> Point:
    return room[0] + room[2] / 2, room[1] + room[3] / 2


@lru_cache(maxsize=4)
def shown(rooms: tuple[Bounds, ...]) -> tuple[int, ...]:
    """Per room, the bitmask (by position in `rooms`) of itself and the rooms touching it, corners too."""
    masks = []
    for x, y, width, height in rooms:
        mask = 0
        for index, other in enumerate(rooms):
            if (
                other[0] <= x + width
                and x <= other[0] + other[2]
                and other[1] <= y + height
                and y <= other[1] + other[3]
            ):
                mask |= 1 << index
        masks.append(mask)
    return tuple(masks)


def length(here: Point, stops: Sequence[Bounds]) -> float:
    """Tiles from `here` through the stops' centres in order."""
    total, at = 0.0, here
    for stop in stops:
        total += math.dist(at, centre(stop))
        at = centre(stop)
    return total


def reordered(here: Point, stops: list[Bounds]) -> list[Bounds]:
    """The stops in a shorter order, while turning a stretch around or moving one stop shortens it."""
    improved = True
    while improved:
        improved = False
        least = length(here, stops)
        for first in range(len(stops) - 1):
            for last in range(first + 1, len(stops)):
                tried = stops[:first] + stops[first : last + 1][::-1] + stops[last + 1 :]
                if length(here, tried) < least - 1e-9:
                    stops, least, improved = tried, length(here, tried), True
        for taken in range(len(stops)):
            for put in range(len(stops)):
                if taken == put:
                    continue
                tried = stops[:taken] + stops[taken + 1 :]
                tried.insert(put, stops[taken])
                if length(here, tried) < least - 1e-9:
                    stops, least, improved = tried, length(here, tried), True
    return stops


def tour(
    rooms: Sequence[Bounds],
    here: Point,
    explored: Collection[Bounds],
    standable: Collection[Bounds] | None = None,
    before: Sequence[Bounds] = (),
) -> list[Bounds]:
    """The rooms to stand in, in order, to see every unexplored room a `standable` room shows; `here` in tiles.
    What is left of `before` (the last tour) wins unless the new one is KEEP_TILES shorter."""
    rooms = tuple(rooms)
    sees = shown(rooms)
    index = {room: at for at, room in enumerate(rooms)}
    allowed = [at for at, room in enumerate(rooms) if standable is None or room in standable]
    if not allowed:
        return []
    reachable = 0
    for at in allowed:
        reachable |= sees[at]
    wanted = sum(1 << at for at, room in enumerate(rooms) if room not in explored) & reachable
    if not wanted:
        return []

    def covered(stops: list[Bounds]) -> bool:
        seen = 0
        for stop in stops:
            seen |= sees[index[stop]]
        return wanted & ~seen == 0

    # The stops: the room that shows the most new rooms first, the nearer of two as good.
    stops: list[Bounds] = []
    unseen = wanted
    while unseen:
        best = max(allowed, key=lambda at: ((sees[at] & unseen).bit_count(), -math.dist(here, centre(rooms[at]))))
        stops.append(rooms[best])
        unseen &= ~sees[best]
    # Their order: the nearest next, then shortened.
    ordered: list[Bounds] = []
    spot = here
    while stops:
        nearest = min(stops, key=lambda stop: math.dist(spot, centre(stop)))
        stops.remove(nearest)
        ordered.append(nearest)
        spot = centre(nearest)
    stops = reordered(here, ordered)
    for _ in range(ROUNDS):
        changed = False
        least = length(here, stops)
        for place in range(len(stops)):
            without = stops[:place] + stops[place + 1 :]
            if covered(without) and length(here, without) < least - 1e-9:
                stops, changed = without, True
                break
            better: tuple[float, list[Bounds]] | None = None
            for other in allowed:  # the stop moved to a room beside it
                if other == index[stops[place]] or not sees[index[stops[place]]] >> other & 1:
                    continue
                tried = [*stops[:place], rooms[other], *stops[place + 1 :]]
                shorter = length(here, tried)
                if shorter < (least - 1e-9 if better is None else better[0]) and covered(tried):
                    better = (shorter, tried)
            if better is not None:
                least, stops, changed = *better, True
        if not changed:
            break
        stops = reordered(here, stops)
    kept = [stop for stop in before if stop in index and index[stop] in allowed and sees[index[stop]] & wanted]
    if kept and covered(kept) and length(here, kept) < length(here, stops) + KEEP_TILES:
        return kept
    return stops
