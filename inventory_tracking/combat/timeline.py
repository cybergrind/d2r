"""Game ticks for a take: the recorder's sample counter `n` goes up by one per sample, but samples come late
sometimes, so the simulator needs the game frame each sample really belongs to. Also the stays in an area
and the mouse buttons. Covers review.md finding 6.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Any

from inventory_tracking.combat.takes import player_of


GAME_RATE = 25.0  # game frames a second
HOLD_TICKS = 12  # ticks a sample's values are held through when the next one came late (about half a second)
LATE_SLACK = 0.75  # ticks a sample may lag its tick before a tick is skipped for it


def ticks(frames: Sequence[dict[str, Any]], rate: float = GAME_RATE) -> dict[int, int]:
    """Map each frame's sample counter `n` to a game tick, from the timestamps `t`.

    The first frame keeps its own `n`. A later frame advances by one tick, plus one for each whole tick it
    is late by (beyond LATE_SLACK).
    """
    if not frames:
        return {}
    first_t = frames[0]['t']
    first_tick = frames[0]['n']
    out = {first_tick: first_tick}
    previous = first_tick
    for frame in frames[1:]:
        owed = (frame['t'] - first_t) * rate - (previous - first_tick)
        previous += 1 + max(0, math.floor(owed - LATE_SLACK))
        out[frame['n']] = previous
    return out


def visits(frames: Sequence[dict[str, Any]], area: int) -> list[tuple[int, int]]:
    """The contiguous stays in `area`, as `(first n, last n)`. A frame with no player neither ends a stay
    nor belongs to one."""
    out: list[tuple[int, int]] = []
    current: list[int] | None = None
    for frame in frames:
        player = player_of(frame)
        if player is None:
            continue
        if player.area == area:
            if current is None:
                current = [frame['n'], frame['n']]
            else:
                current[1] = frame['n']
        elif current is not None:
            out.append((current[0], current[1]))
            current = None
    if current is not None:
        out.append((current[0], current[1]))
    return out


def longest_visit(frames: Sequence[dict[str, Any]], area: int) -> tuple[int, int] | None:
    """The visit to `area` with the most frames in it (the earliest on a tie), or None when there is none."""
    counts = [frame['n'] for frame in frames]
    best: tuple[int, int] | None = None
    best_count = -1
    for first, last in visits(frames, area):
        count = sum(first <= n <= last for n in counts)
        if count > best_count:
            best, best_count = (first, last), count
    return best


def button_down(frame: Mapping[str, Any], button: int) -> bool:
    """Whether mouse `button` is down in the frame's pointer record (`in`)."""
    record = frame.get('in')
    if not record or record[2] is None:
        return False
    return bool(record[2] & (1 << (7 + button)))
