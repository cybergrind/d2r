"""Rules for clicking at things, from the targeting study of 2026-10-21 (rca/2026-10-21/targeting-findings.md).

The study measured the world-to-screen projection right (64,789 Teleport hops landed a median 0.4 world units off
their aim; a lone item's label was under the (0, -24) aim 96.5 % of the time, wherever on the screen). The clicks that
failed did so for other reasons, and this module holds the rules that answer them, each behind its own switch:

- a door whose entrance is an object, not a warp tile (the Durance of Hate, the Kurast temples): the object under the
  pointer is the door (`door_hover`, OBJECT_DOORS);
- the game's record of the unit under the pointer names nothing: such an aim is no door, and is clicked only after
  the aims that showed something (`door_hover`, HOVER_NOTHING; game/memory.py `GameMemory.nothing_hovered`);
- a door's entry spot is learnt by its distance from the door's warp unit, not only from the mark (`entry_learnable`,
  ENTRY_FROM_WARP: Flayer Dungeon 1's spot lies 11.4 units from its mark);
- a click on a townsperson that brought no menu is known once the character stands, not after MENU_SECONDS
  (`menu_or_stand`, MENU_STAND), and a menu that opened as the character still walked is kept when the view moved
  under half a menu line before it stood (`keep_mid_walk`, MENU_KEEP_MID_WALK);
- the item labels hidden for a click by the Show Items key, and shown again after it whatever came of it
  (`labels_hidden`; the pile pickup of macros/pile.py, as stash.py LABELS_OFF_AT_THE_STASH does at the stash).
"""

import math
from collections.abc import Collection, Iterator, Sequence
from contextlib import contextmanager

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import ITEM_UNIT, MONSTER_UNIT, OBJECT_UNIT, TILE_UNIT
from inventory_tracking.game.records import Warp, World
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import screen_fraction


Point = tuple[float, float]

# The Durance of Hate (10 entries) and the six Kurast temples (15) of 2026-10-19/21: the hover names the entrance as an
# object, (2, id), never a warp tile. `walk_into` took an object under the pointer for "not the door" and looked again
# (LOOKS), while the (0, 0) aim with nothing under it was clicked at once and walked the character to the mark's
# ground: 45 clicks that did not take, 2.0-3.8 s an entry against 0.29 s for a stairs (targeting-findings.md §1.1).
# True: with no warp tile within the door's reach of the mark, an object under the pointer is the door. False: as before
OBJECT_DOORS = True
# 35 of the 106 door clicks that did not take on 2026-10-19/21 had nothing under the pointer: GameMemory.hovered gives
# None for an unreadable record and for one that names nothing alike, and `walk_into` clicked both as "unread".
# True: an aim the record says has nothing under it is clicked only after the aims that showed something. False: as
# before
HOVER_NOTHING = True
# World units from the door's warp unit within which a spot the level changed at is the door's own entry, however far
# from the mark: Flayer Dungeon 1's took at (-9, -7) from its mark, 11.4 away, in 7 entries out of 7 and was never
# remembered (ENTRY_MAX 6 from the mark), so each entry repeated a click that walked 6 units and stopped (1.8 s)
ENTRY_FROM_WARP = True
ENTRY_FAR = 14.0  # world units from the mark: no spot further off is a door's entry, the warp unit's distance or not
# 2026-10-21 08:10:04: a click with Deckard Cain under the pointer walked the character 3.6 units; Cain walked on and no
# menu opened, and the step waited MENU_SECONDS (5 s) for it. True: the click is a miss once the character has stood
# MENU_GRACE with no menu (7 such clicks in 722 on 2026-10-19/21). False: the whole wait, as before
MENU_STAND = True
MENU_GRACE = 0.8  # seconds standing, after the walk the click made or after the click, before it counts as a miss
MENU_POLL = 0.04
# 121 of 722 menus opened as the character still walked up (2026-10-19/21) and each was closed and opened again
# standing (~0.6 s). From the open to the stand the view moved a median 4 classic pixels up or down, 72 % under half a
# line (targeting-findings.md §4.3). True: kept when under half a line. False: closed and opened again, as before
MENU_KEEP_MID_WALK = True
LABELS_SECONDS = 0.6  # for a press of Show Items to show in its byte (routines.py SHOW_ITEMS_WAIT)

CLICK, WAIT, LATER, EMPTY = 'click', 'wait', 'later', 'empty'
IN_THE_WAY = frozenset((MONSTER_UNIT, ITEM_UNIT))  # as teleport.py IN_THE_WAY: the click would go to that unit


def object_door(warps: Sequence[Warp] | None, door: Point, near: float) -> bool:
    """Whether the door at `door` (world units) has its entrance as an object: the game shows no warp tile within
    `near` of it (OBJECT_DOORS). An unread list of warps (None) says nothing: no."""
    if not OBJECT_DOORS or warps is None:
        return False
    return not any(math.dist((warp.x, warp.y), door) <= near for warp in warps)


def nothing_under(run: Run) -> bool:
    """Whether the game's record says nothing is under the pointer, not that it is unread (`Run.hover_nothing`)."""
    return run.hover_nothing is not None and run.hover_nothing()


def door_hover(over: tuple[int, int] | None, *, nothing: bool, objects: bool) -> str:
    """What `walk_into` does with an aim that has `over` under it: CLICK it (a warp tile, the door's object, or an
    unread record), WAIT for the others (a monster or an item: the click would go to it), LATER (another object: look
    again), EMPTY (nothing under it by the record: after the rest, HOVER_NOTHING)."""
    if over is None:
        return EMPTY if HOVER_NOTHING and nothing else CLICK
    if over[0] == TILE_UNIT or (objects and over[0] == OBJECT_UNIT):
        return CLICK
    if over[0] in IN_THE_WAY:
        return WAIT
    return LATER


def nearest_warp(warps: Sequence[Warp] | None, door: Point, near: float) -> Point | None:
    """The warp unit nearest `door` within `near` of it, as world units from it; None without one."""
    found = [warp for warp in warps or () if math.dist((warp.x, warp.y), door) <= near]
    if not found:
        return None
    warp = min(found, key=lambda each: math.dist((each.x, each.y), door))
    return warp.x - door[0], warp.y - door[1]


def entry_learnable(offset: Point, warp: Point | None, entry_max: float) -> bool:
    """Whether the spot `offset` (world units from the mark) is the door's own entry: within `entry_max` of the mark
    as before, or (ENTRY_FROM_WARP) within it of the door's warp unit `warp` (from the mark) and ENTRY_FAR of the
    mark."""
    if math.hypot(*offset) <= entry_max:
        return True
    if not ENTRY_FROM_WARP or warp is None:
        return False
    return math.dist(offset, warp) <= entry_max and math.hypot(*offset) <= ENTRY_FAR


def menu_or_stand(run: Run, panel: str, seconds: float, walking: Collection[int]) -> World | None:
    """The world once `panel` (a townsperson's menu) is open after a click on them, or None: `seconds` gone by, or
    (MENU_STAND) the character stood MENU_GRACE with no menu, after the walk the click made or after the click."""
    if not MENU_STAND:
        return run.seen(lambda w: panel in w.open_panels, seconds)
    began = run.clock()
    deadline, last, since = began + seconds, None, began
    while True:
        world = run.world()
        if panel in world.open_panels:
            return world
        me, now = world.player, run.clock()
        place = None if me is None else (round(me.x, 1), round(me.y, 1))
        if place != last or (me is not None and me.mode in walking):
            last, since = place, now
        if now - since >= MENU_GRACE:
            LOG.info('Macro: no menu %.2fs after the click: the character stood %.2fs at %s', now - began, now - since,
                     place)  # fmt: skip
            return None
        if now >= deadline:
            return None
        run.pace.sleep(MENU_POLL)


def menu_drift(opened: World, stood: World, place: Point, aspect: float) -> float | None:
    """How far up or down the screen (window heights) the townsperson at `place` was drawn when the character stood
    (`stood`) against when the menu opened (`opened`); None without the character in either."""
    if opened.player is None or stood.player is None:
        return None
    then = screen_fraction(opened.player, *place, aspect)
    now = screen_fraction(stood.player, *place, aspect)
    return abs(now[1] - then[1])


def keep_mid_walk(drift: float | None, line: float) -> bool:
    """Whether a menu that opened mid-walk is kept (MENU_KEEP_MID_WALK): the view moved under half a `line` since."""
    return MENU_KEEP_MID_WALK and drift is not None and drift < line / 2


@contextmanager
def labels_hidden(run: Run, why: str) -> Iterator[bool]:
    """Within, the item labels hidden by the Show Items key; whether they are. Shown again after it whatever came of
    it (the level run's `routines.show_items_on` looks again before the next run). No key, or the labels not shown:
    nothing pressed, False."""
    key = run.show_items_key
    if key is None or run.world().show_items is not True:
        yield False
        return
    LOG.info('Macro: %s: item labels hidden by %s', why, key)
    run.actuator.tap(key)
    hidden = run.seen(lambda w: w.show_items is False, LABELS_SECONDS) is not None
    if not hidden:
        LOG.info('Macro: %s: Show Items did not go off', why)
    try:
        yield hidden
    finally:
        if run.world().show_items is False:
            run.actuator.tap(key)
            on = run.seen(lambda w: w.show_items is True, LABELS_SECONDS) is not None
            LOG.info('Macro: %s: item labels shown again%s', why, '' if on else ': not yet (the level run checks it)')
