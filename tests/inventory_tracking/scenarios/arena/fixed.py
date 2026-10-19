"""Moments chosen without looking at what happens next (architecture.md §6.2.2).

Every other kind of moment (moments.py, stuck.py) is found by its OUTCOME: a death, a burst of damage,
a run of potions, a long fight. Such windows are the unlucky ones or the quiet ones, so an average over
them is biased (scenes cut for damage read 0.30 of the recordings' loss in the arena, scenes cut for
length 2.4). The kind `fixed` is for averages: the times are a grid, `offset`, `offset + every`, ... seconds
into the take, and a time is kept by the frame AT it (the last frame at or before that second) alone:
the character's vitals are read and it is alive, and at least HOSTILES live hostiles are within `reach`
units of it, so the sample is "moments of being in a fight". Nothing after that frame is read: the same
frames give the same moments whatever follows them (test_fixed.py cuts a take short and rewrites its
future). The scene starts AT the moment (no lead): what the arena is asked is how a fight like this goes
on, from a point nobody chose for its trouble.

Which of the qualifying times are cut is decided by `spread` and `strides` (build_scenes.py `--fixed`):
within a take the kept ones are spread evenly over its length (of 9 qualifying times and 2 allowed, the
3rd and the 6th), and across takes ALL takes are gone over, oldest first, with a stride (of 80 takes with
a qualifying time and 40 wanted, every other one, from the second), so the kept set spans the dates and
areas of the recordings, not the newest evening.
"""

from bisect import bisect_right
from math import hypot

from inventory_tracking.macros.routines import DEAD
from inventory_tracking.takes.takes import Take, monsters_of, player_of
from tests.inventory_tracking.scenarios.arena.moments import LONG_GAP, Moment


HOSTILES = 3  # live hostiles within `reach` for a time to count
STALE = LONG_GAP  # seconds: a frame older than this at the time (the recorder paused) is no frame at it


def fixed(take: Take, *, every: float = 20.0, offset: float = 5.0, reach: float = 30.0) -> list[Moment]:
    """The times `offset`, `offset + every`, ... seconds into the take at which the character is in a fight.

    The decision at a time reads only the frame at it (see the module); the result is the same for a take
    cut short after that frame. `Moment.at` is the time, `Moment.frame` the frame at it."""
    frames = take.frames
    if not frames or every <= 0:
        return []
    start = frames[0]['t']
    rel = [frame['t'] - start for frame in frames]
    found: list[Moment] = []
    at = offset
    while at <= rel[-1]:
        index = bisect_right(rel, at) - 1
        if index >= 0 and at - rel[index] <= STALE and (note := fight(frames[index], reach)) is not None:
            found.append(Moment(index, 'fixed', at, note))
        at += every
    return found


def fight(frame: dict, reach: float) -> str | None:
    """The note for a frame that is a fight worth playing, else None."""
    player = player_of(frame)
    if player is None or player.life is None or not player.max_life or not player.life or player.mode in DEAD:
        return None
    near = sum(
        1
        for monster in monsters_of(frame)
        if monster.hostile and hypot(monster.x - player.x, monster.y - player.y) <= reach
    )
    if near < HOSTILES:
        return None
    return f'{near} hostiles within {reach:.0f}, life {player.life}/{player.max_life}'


def spread(count: int, keep: int) -> list[int]:
    """`keep` of `count` positions, evenly: of 9 and 2 the 3rd and the 6th (indices 2 and 5); all when
    `keep` reaches `count`."""
    if keep >= count:
        return list(range(count))
    return [(i + 1) * count // (keep + 1) - 1 for i in range(keep)] if keep > 0 else []


def strides(count: int, keep: int) -> list[int]:
    """`keep` of `count` takes by a fixed stride over the whole list, the middle of each stretch:
    of 80 and 40 every other one from the second; all when `keep` reaches `count`."""
    if keep >= count:
        return list(range(count))
    return [(2 * i + 1) * count // (2 * keep) for i in range(keep)] if keep > 0 else []
