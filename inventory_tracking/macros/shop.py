"""Town Portal scrolls and keys from Jamella (routes/lower-kurast-loop-plan.md phase 8).

The player, 2026-10-16: "we need, from time to time, buy portal scrolls and keys - when we visit shop for keys we still
buy scrolls and vice versa. keep 3+ of each before run". So when the loop is in Pandemonium Fortress with fewer than
MIN_STOCK keys or Town Portal charges, one visit to Jamella buys both up (`restock`).

The evidence (the plan's phase 8 section): Jamella stands about (5083, 5058), 38 units from where a game starts and
below the window from there, so the character walks toward her until she is drawn well inside it (`walk_until`). A click
on her, aimed where she is drawn at that moment (she walks about), opens her menu (`npc_interact`). Its Trade line is
TRADE_ABOVE of the window's height above where she is drawn (the player's two clicks of 21:03 and 21:15 on 2026-10-16:
0.2155 and 0.2214, the lines 0.0226 apart), and it opens her trade window (`npc_shop`). Gamble is the next line and its
window is a vendor panel too, so a miss is never tried again on another line, and nothing is bought unless her stock in
memory holds a key and a scroll (`GameMemory.stock`). The Misc tab and the stock's cells are the layout's
(`vendorpanellayouthd.json`: tabs from (82, 162) 249 x 75, the grid from (91, 233), 98 a cell, in the left panel as the
waypoint's). A Shift + right click fills the key stack or the tome, made only where there is room and checked by the
count in memory (`BUYS`). Then the window is closed and the character walks back until the waypoint is on the screen, as
the waypoint step clicks it from where it stands.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import cell_point
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import screen_fraction
from inventory_tracking.macros.waypoint import panel_point
from inventory_tracking.macros.world import MONSTER_UNIT, TOME_CHARGES, Monster, Pack, Stocked, World


__all__ = ['MIN_STOCK', 'restock', 'short']

JAMELLA = 405  # monstats *hcIdx (shop/capture.py VENDORS)
KEY, SCROLL = 558, 544  # Key, Scroll of Town Portal (items metadata, 2026-10-16)
MIN_STOCK = 3  # the player: "keep 3+ of each before run"
TRADE_ABOVE = 0.218  # window heights from her drawn point up to the middle of her menu's Trade line
MISC_TAB = (82 + 3 * 249 + 249 / 2, 162 + 75 / 2)  # layout units in the left panel: the fourth tab's middle
VENDOR = ((0.0, 0.397), (236, -651), (91, 233))  # the stock grid, as cube.py's grids
# Window fractions she is drawn within before she is clicked: her menu (up to TRADE_ABOVE and a line higher) and her
# feet inside the window, the bottom bar's controls clear
SEEN = (0.1, 0.9, TRADE_ABOVE + 0.06, 0.8)
STEP = 12.0  # units a walk click goes toward a place
WALK_CLICKS = 8  # walk clicks at most toward a place
WALK_SECONDS = 1.6  # for one walk to end
MENU_SECONDS = 5.0  # from the click on her to her menu: the game walks the character to her
PANEL_SECONDS = 2.5
BOUGHT_SECONDS = 1.5
TAB_SETTLE = 0.4
AIMS = (0.0, 0.03, 0.06)  # window heights above her drawn point the pointer is put at, her body up
BODY = 0.04  # window heights above her drawn point: her body's middle, clicked when no aim was named hers
HOVER_SECONDS = 0.25  # for the game's record of what is under the pointer to name her
FOLLOW = 0.5  # units she walks before the pointer is put on her again
FOLLOW_POLL = 0.04
MENU_CLICKS = 2
BUY_CLICKS = 2  # Shift + right clicks on one item at most, each checked by the count
WALKING = (2, 3, 6)  # the character's walk, run and town walk: the view moves with it


def short(pack: Pack | None) -> bool:
    """Whether the keys or the Town Portal charges are under MIN_STOCK (an unread count says nothing)."""
    if pack is None:
        return False
    return (pack.keys is not None and pack.keys < MIN_STOCK) or (pack.portals is not None and pack.portals < MIN_STOCK)


def _drawn(world: World, place: tuple[float, float], aspect: float) -> tuple[float, float] | None:
    player = world.player
    return None if player is None else screen_fraction(player, *place, aspect)


def _inside(point: tuple[float, float] | None, bounds: tuple[float, float, float, float]) -> bool:
    return point is not None and bounds[0] <= point[0] <= bounds[1] and bounds[2] <= point[1] <= bounds[3]


def walk_until(run: Run, place: Callable[[World], tuple[float, float] | None], bounds, what: str) -> World:
    """Walk toward `place(world)` until it is drawn within `bounds` (window fractions); the world then. `Abort`."""
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    aspect = rect[2] / rect[3]
    for _ in range(WALK_CLICKS + 1):
        world = run.world()
        player, there = world.player, place(world)
        if player is None or there is None:
            raise Abort(f'{what} is not in sight')
        if _inside(_drawn(world, there, aspect), bounds):
            return world
        away = math.dist((player.x, player.y), there)
        ratio = min(1.0, STEP / away) if away else 0.0
        toward = (player.x + (there[0] - player.x) * ratio, player.y + (there[1] - player.y) * ratio)
        run.actuator.move(*screen_fraction(player, *toward, aspect), scatter=(4, 4))
        run.actuator.click()
        began = (player.x, player.y)

        def walked(w: World, b=began) -> bool:
            return w.player is not None and math.dist((w.player.x, w.player.y), b) >= STEP * 0.6

        run.seen(walked, WALK_SECONDS)
    raise Abort(f'{what} not reached by walking')


def _jamella(world: World) -> tuple[float, float] | None:
    her = _her(world)
    return (her.x, her.y) if her is not None else None


def _waypoint(run: Run) -> Callable[[World], tuple[float, float] | None]:
    def place(world: World) -> tuple[float, float] | None:
        shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
        return (shown[0].x, shown[0].y) if shown else None

    return place


def restock(run: Run) -> None:
    """One visit to Jamella that buys keys and Town Portal scrolls (the module text). Mouse mode only. `Abort` with her
    windows closed when a step does not take."""
    if run.pad is not None:
        raise Abort('the shop needs mouse mode')
    if run.carried is None or run.stock is None:
        raise Abort('the shop cannot be read')
    before = run.carried()
    if before is None or before.keys is None or before.portals is None:
        raise Abort('the keys and the Town Portal charges are not read')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    aspect = rect[2] / rect[3]
    run.say(f'Shop: {before.keys} keys, {before.portals} portals')
    walk_until(run, _jamella, SEEN, 'Jamella')
    run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)  # the view still
    try:
        _open_trade(run, aspect)
        stock = {item.txt: item for item in run.stock(JAMELLA) if item.tab == 3}
        if KEY not in stock or SCROLL not in stock:
            raise Abort('not her trade window: no key and no scroll in it')
        run.actuator.move(*panel_point(rect, *MISC_TAB), scatter=(15, 5))
        run.actuator.click()
        run.pace.sleep(TAB_SETTLE)
        for what in BUYS:
            _buy(run, rect, stock[what.txt], what)
    finally:
        if {'npc_shop', 'npc_interact', 'inventory'} & set(run.world().open_panels):
            run.actuator.tap('Escape')  # with nothing open it opens the game's menu instead
            run.seen(lambda w: not {'npc_shop', 'npc_interact'} & set(w.open_panels), PANEL_SECONDS)
    after = run.carried()
    keys = after.keys if after is not None else None
    portals = after.portals if after is not None else None
    LOG.info('Macro: shop: keys %s -> %s, portals %s -> %s', before.keys, keys, before.portals, portals)
    run.say(f'Shop: {keys} keys, {portals} portals')
    walk_until(run, _waypoint(run), (0.15, 0.85, 0.15, 0.8), 'the waypoint')


@dataclass(frozen=True)
class Buy:
    """What a visit buys: its class, its count in the inventory and whether there is room for more of it."""

    txt: int
    name: str
    count: Callable[[Pack], int | None]
    room: Callable[[Pack], bool]


# The player, 2026-10-16: "when you buy tp scrolls or keys: check inventory number. you can bulk buy with
# (shift+right click)": one Shift + right click fills the key stack or the tome, so it is made only where there is room
# (a full stack's keys would take a new cell), and the count in memory says whether it took
BUYS = (
    Buy(KEY, 'keys', lambda p: p.keys, lambda p: p.key_room is not False),
    Buy(SCROLL, 'portals', lambda p: p.portals, lambda p: p.portals is None or p.portals < TOME_CHARGES),
)


def _buy(run: Run, rect, item: Stocked, what: Buy) -> None:
    """Fill `what` from her stock's `item` by Shift + right clicks (BUY_CLICKS at most), each checked by the count."""
    assert run.carried is not None
    for _ in range(BUY_CLICKS):
        pack = run.carried()
        if pack is None:
            raise Abort('the inventory is not read')
        had = what.count(pack)
        if not what.room(pack):
            LOG.info('Macro: shop: %s: %s carried, no room for more', what.name, had)
            return
        run.actuator.move(*cell_point(rect, VENDOR, (item.x, item.y)), scatter=(5, 5))
        run.actuator.tap('Shift_L', 'Button3')

        def came(w: World, h=had) -> bool:
            p = run.carried() if run.carried is not None else None
            return p is not None and what.count(p) != h

        if run.seen(came, BOUGHT_SECONDS) is not None:
            return
        LOG.info('Macro: shop: %s: still %s after the Shift + right click', what.name, had)


def _her(world: World) -> Monster | None:
    return next((m for m in world.monsters if m.txt_id == JAMELLA), None)


def _point_at_her(run: Run, aspect: float) -> bool:
    """Put the pointer on her body at each of AIMS in turn, following her as she walks, until the game's record of what
    is under the pointer names her; whether it did (an unreadable record counts as named)."""
    for lift in AIMS:
        deadline, aimed = run.clock() + HOVER_SECONDS, None
        while True:
            world = run.world()
            her = _her(world)
            drawn = _drawn(world, (her.x, her.y), aspect) if her is not None else None
            if her is None or drawn is None:
                raise Abort('Jamella is not in sight')
            if aimed is None or math.dist(aimed, (her.x, her.y)) > FOLLOW:
                run.actuator.move(drawn[0], drawn[1] - lift, scatter=(3, 3))
                aimed = (her.x, her.y)
            if run.hovered is None or run.hovered() == (MONSTER_UNIT, her.unit_id):
                return True
            if run.clock() >= deadline:
                break
            run.pace.sleep(FOLLOW_POLL)
    return False


def _open_trade(run: Run, aspect: float) -> None:
    """Her menu by a click on her, then her trade window by its Trade line.

    The vendors walk about (the player, 2026-10-16: "they are moving, so you cannot expect to find them at the same
    location"), so each aim is where she is drawn at that moment. At 23:07:04 that day the game's record never named
    her at any of the three aims (she stood still, 11 units off) and the loop stopped without a click; the click is now
    made all the same, at her body's middle, and her menu opening is what tells it took (MENU_CLICKS tries, each from
    where the character then stands: a click beside her walks it toward her)."""
    for _ in range(MENU_CLICKS):
        if not _point_at_her(run, aspect):
            LOG.info('Macro: shop: the game names %s under the pointer, not Jamella: clicked at her all the same',
                     run.hovered() if run.hovered is not None else None)  # fmt: skip
            world = run.world()
            her = _her(world)
            drawn = _drawn(world, (her.x, her.y), aspect) if her is not None else None
            if drawn is None:
                raise Abort('Jamella is not in sight')
            run.actuator.move(drawn[0], drawn[1] - BODY, scatter=(3, 3))
        run.actuator.click()
        if run.seen(lambda w: 'npc_interact' in w.open_panels, MENU_SECONDS) is not None:
            break
        run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
    else:
        raise Abort('her menu did not open')
    world = run.world()
    her = _her(world)
    drawn = _drawn(world, (her.x, her.y), aspect) if her is not None else None
    if drawn is None:
        raise Abort('Jamella is not in sight')
    run.actuator.move(drawn[0], drawn[1] - TRADE_ABOVE, scatter=(8, 2))
    run.actuator.click()
    if run.seen(lambda w: 'npc_shop' in w.open_panels, PANEL_SECONDS) is None:
        raise Abort('her trade window did not open')
