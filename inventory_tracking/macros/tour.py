"""The order to explore a level's rooms in (macros/hunt.py's seek step): a short tour of places to
stand so that every unexplored room is seen. Standing in a room shows it and the rooms touching it
(terror/tracker.py `explore`), so the stops are a cover of the unexplored rooms and the tour a short
path through them from where the character stands.

The rule before (the unexplored room nearest by the way, a turn counted as some tiles more) left
strips behind and crossed the explored ground again to fetch them: Far Oasis, 02:16 on 2026-10-11,
eight hops back from the south-east corner to the middle, and fourteen across the whole map for the
last three rooms (user: "too many back-and-forward iterations"). Replayed with nothing to fight from
four starts on each of four recorded layouts (Far Oasis, Black Marsh, Catacombs 2, Tower Cellar 3;
hops of 5.5 tiles): that rule 612 hops, this tour 442, planned anew at every hop in 1 to 4 ms.

Distances are straight lines between room centres: a teleport crosses what a walk goes around, and
the hop itself is planned over the real ground (macros/teleport.py).
"""

import math
from collections.abc import Collection, Sequence
from functools import lru_cache


Bounds = tuple[int, int, int, int]  # a room's x, y, width, height in tiles
Point = tuple[float, float]
ROUNDS = 3  # passes of dropping and shifting stops, each followed by a reordering
# The tour is planned anew at every step, from where the fights left the character. The one before is
# kept while a new one is not this many tiles shorter (a room's side): two tours as long that start
# opposite ways would else take a step each in turn.
KEEP_TILES = 8.0


def centre(room: Bounds) -> Point:
    return room[0] + room[2] / 2, room[1] + room[3] / 2


@lru_cache(maxsize=4)
def shown(rooms: tuple[Bounds, ...]) -> tuple[int, ...]:
    """For each room, the rooms a character standing in it sees: itself and the ones touching it,
    corners too, as bits by position in `rooms`."""
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
    """The rooms to stand in, in order, to see every unexplored room one of `standable` (all, when
    not given) shows; `here` in tiles. Empty when nothing of that kind is left. `before` is the tour
    of the last step: what is left of it is the answer unless the new one is KEEP_TILES shorter."""
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
