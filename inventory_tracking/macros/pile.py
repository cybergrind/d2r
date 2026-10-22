"""A drop in a pile whose label no aim found: the item itself clicked with the labels hidden, else a sweep of the pile's
labels with the game's record of what is under the pointer read every frame.

In a pile the game lays the item labels out in a stack, so the drop's own label lies wherever the stack put it. The
first aim (0, -24) had the drop under it 96.5 % of the time alone, 77 % with two drops within 4 units, 52 % with three
(2026-10-19/21, 4,707 pickups); 201 pickups ran out of time with the label under no aim, 162 of them gold. 09:19:21-26
on 2026-10-21: a Magic Sun Spirit among 12 drops, 26 aims in three tries, the potions' labels under every one of them
(rca/2026-10-21/targeting-findings.md §1.2, §4.1).

`pile_take` is `pickup._take`'s stage after its first look in a pile: with PILE_LABELS_OFF the labels are hidden by the
Show Items key (`targeting.labels_hidden`) and SPRITE_AIMS look for the item's own picture on its ground; with
PILE_SWEEP the labels are swept, the pointer moved SWEEP_STEP pixels a poll up SWEEP_COLUMNS above the drop. Either
clicks only with a wanted drop under the pointer, as every pickup aim does: never an unwanted item.
"""

import math
from collections.abc import Callable, Mapping

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import ITEM_UNIT
from inventory_tracking.game.records import Drop
from inventory_tracking.game.view import UNIT_PIXELS
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.targeting import labels_hidden
from inventory_tracking.macros.teleport import HOVER_SECONDS, ground_fraction, in_view


# True: a drop no first aim found in a pile is looked for with the labels hidden (Show Items off for the look and its
# clicks, on again after). False: as before (the labels' aims alone)
PILE_LABELS_OFF = True
# True: then the labels swept, the record read at every step. False: as before
PILE_SWEEP = True
# Classic pixels (600 high; across, down) from the drop's ground where its picture is looked for with the labels hidden:
# an item lies drawn on its ground, the larger ones reaching a little above it (UNVERIFIED in the game: the first live
# pile pickup with the labels hidden logs every aim and what was under it)
SPRITE_AIMS = ((0, -6), (0, 0), (0, -12), (-8, -6), (8, -6), (0, 6), (0, -18), (-14, -2), (14, -2))
SWEEP_COLUMNS = (0, -40, 40, -80, 80)  # classic pixels across: a label 40 or more wide is crossed by one of them
SWEEP_STEP = 8  # classic pixels down a column between two reads: a label is ~13 high
SWEEP_POLL = 0.03  # seconds at a sweep point before the record is read (a frame is 0.04)
SWEPT: dict[int, int] = {}  # drop unit -> sweep points done: the next try goes on from there
SWEPT_MOST = 64
CLICKS = 2  # clicks on an aim with the drop under it (pickup.CLICKS)
MOVED_UNITS = 1.0  # the character this far from where it stood: a click walked it, the aim is on other ground


def sweep_path(crowd: int) -> tuple[tuple[int, int], ...]:
    """The sweep's points (classic pixels from the drop's ground): each column of SWEEP_COLUMNS from just above the
    ground up as high as `crowd` other drops stack their labels (`pickup.pile_aims`' top)."""
    top = -64 - 10 * min(crowd, 12)
    return tuple((across, down) for across in SWEEP_COLUMNS for down in range(-14, top - 1, -SWEEP_STEP))


def _point(run: Run, drop: Drop, aim: tuple[int, int]) -> tuple[float, float] | None:
    """Where `aim` is for `drop` now, as window fractions; None out of view or with no character or window."""
    player = run.world().player
    rect = run.actuator.keys.focused_window_rect()
    if player is None or rect is None:
        raise Abort('not in a game')
    aspect = rect[2] / rect[3]
    across, down = ground_fraction(player, drop.x, drop.y, aspect)
    where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
    return where if in_view(where) else None


def _wanted(over: tuple[int, int] | None, serves: Mapping[int, Drop]) -> Drop | None:
    return serves.get(over[1]) if over is not None and over[0] == ITEM_UNIT else None


def _clicks(
    run: Run, under: Drop, aim: tuple[int, int], over: tuple[int, int], click: Callable[..., bool], looked: list[str]
) -> bool:
    """CLICKS clicks with `under` under the pointer; whether it left the ground. A click that walked the character
    ends them: a second one there walks it further off."""
    before = run.world().player
    for _ in range(CLICKS):
        looked[-1] += ' clicked'
        if click(run, under, aim, over):
            return True
        now = run.world().player
        if before is None or now is None or math.dist((before.x, before.y), (now.x, now.y)) > MOVED_UNITS:
            return False
    return False


def look_hidden(
    run: Run, drop: Drop, serves: Mapping[int, Drop], looked: list[str], click: Callable[..., bool]
) -> Drop | None:
    """With the labels hidden: SPRITE_AIMS looked at, each with a wanted drop under it clicked; the drop picked up."""
    assert run.hovered is not None
    for aim in SPRITE_AIMS:
        where = _point(run, drop, aim)
        if where is None:
            continue
        run.actuator.aim(*where, scatter=(1, 1))
        run.pace.sleep(HOVER_SECONDS)
        over = run.hovered()
        under = _wanted(over, serves)
        looked.append(f'{aim} labels hidden {"wanted" if under is not None else over}')
        if under is not None and over is not None and _clicks(run, under, aim, over, click, looked):
            return under
    return None


def sweep(
    run: Run, drop: Drop, serves: Mapping[int, Drop], crowd: int, looked: list[str], click: Callable[..., bool]
) -> Drop | None:
    """The labels swept (`sweep_path`) from where the last try left off: at the first point the record names a wanted
    drop that point and the one before are looked at again (the record may lag a frame), and clicked with it under
    them; the drop picked up."""
    assert run.hovered is not None
    path = sweep_path(crowd)
    if len(SWEPT) > SWEPT_MOST:
        SWEPT.clear()
    start = SWEPT.get(drop.unit_id, 0) % len(path)
    before: tuple[int, int] | None = None
    for index in range(start, len(path)):
        aim = path[index]
        SWEPT[drop.unit_id] = index + 1
        where = _point(run, drop, aim)
        if where is None:
            before = None
            continue
        run.actuator.jump(*where, scatter=(1, 1))
        run.pace.sleep(SWEEP_POLL)
        if _wanted(run.hovered(), serves) is None:
            before = aim
            continue
        for again in (aim, before):
            spot = None if again is None else _point(run, drop, again)
            if again is None or spot is None:
                continue
            run.actuator.aim(*spot, scatter=(1, 1))
            run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            under = _wanted(over, serves)
            looked.append(f'{again} swept {"wanted" if under is not None else over}')
            if under is not None and over is not None:
                SWEPT.pop(drop.unit_id, None)
                if _clicks(run, under, again, over, click, looked):
                    return under
                return None  # under the pointer and not taken: the caller's misses count it
        before = aim
    SWEPT.pop(drop.unit_id, None)  # the whole path done: the next try sweeps it again
    return None


def pile_take(
    run: Run, drop: Drop, serves: Mapping[int, Drop], crowd: int, looked: list[str], click: Callable[..., bool]
) -> Drop | None:
    """The drop of `serves` picked up in a pile of `crowd` others, or None: with the labels hidden (PILE_LABELS_OFF,
    the Show Items key known and the labels shown), then a sweep of the labels (PILE_SWEEP). `click(run, drop, aim,
    over)` is the pickup's own click (`pickup.click`): whether the drop left the ground."""
    if run.hovered is None:
        return None
    if PILE_LABELS_OFF and run.show_items_key is not None:
        with labels_hidden(run, f'pickup of {drop.label} in a pile of {crowd}') as hidden:
            if hidden:
                found = look_hidden(run, drop, serves, looked, click)
                if found is not None:
                    return found
    if PILE_SWEEP:
        found = sweep(run, drop, serves, crowd, looked, click)
        if found is not None:
            LOG.info('Macro: pickup: %s found by the sweep of the pile', found.label)
            return found
    return None
