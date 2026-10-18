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

import json
import math
import subprocess
import time
from collections import Counter
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.junk import named
from inventory_tracking.macros.portal import FROM_TOME, PortalSource, portal_source
from inventory_tracking.macros.routines import screen_fraction
from inventory_tracking.macros.waypoint import panel_point
from inventory_tracking.macros.world import (
    GOLD_STAT,
    KEY_STACK,
    MONSTER_UNIT,
    TOME_CHARGES,
    Carried,
    Monster,
    Pack,
    Stocked,
    World,
)
from inventory_tracking.shop.capture import VENDORS


__all__ = ['MIN_STOCK', 'restock', 'short']

JAMELLA = 405  # monstats *hcIdx (shop/capture.py VENDORS)
KEY, SCROLL = 558, 544  # Key, Scroll of Town Portal (items metadata, 2026-10-16)
IDENTIFY_SCROLL = 545  # Scroll of Identify (items metadata, 2026-10-17): the Tome of Identify's (macros/junk.py)
MIN_STOCK = 3  # the player: "keep 3+ of each before run"
TRADE_ABOVE = 0.229  # window heights from her drawn point, as her menu opened, up to the middle of its Trade line
TABS, TAB_SIZE = (82, 162), (249, 75)  # layout units in the left panel: the vendor's tabs' corner and each tab's size


def tab_point(tab: int) -> tuple[float, float]:
    """The middle of tab `tab` (0 the first), in layout units from the panel's corner."""
    return TABS[0] + tab * TAB_SIZE[0] + TAB_SIZE[0] / 2, TABS[1] + TAB_SIZE[1] / 2


MISC_TAB = tab_point(3)
VENDOR = ((0.0, 0.397), (236, -651), (91, 233))  # the stock grid, as cube.py's grids
# Window fractions she is drawn within before she is clicked: her menu (up to TRADE_ABOVE and a line higher) and her
# feet inside the window, the bottom bar's controls clear
SEEN = (0.1, 0.9, TRADE_ABOVE + 0.06, 0.8)
STEP = 12.0  # units a walk click goes toward a place
# Walk clicks at most toward a place (Kurast Docks' waypoint from its start: about 130 units). 16 ran out 2 units short
# of it after the first clicks there went 4 units each (12:26:25 and 12:26:53 on 2026-10-17: a new game begun in the
# docks after a recovery, three recoveries in a row and the loop stopped), and beside Halbu the turned clicks used them
# all (12:10:04)
WALK_CLICKS = 30
WALK_SECONDS = 1.6  # for one walk to end
TURNS = (40, -40, 80, -80)  # degrees a walk click is turned after clicks that did not move the character
MENU_SECONDS = 5.0  # from the click on her to her menu: the game walks the character to her
PANEL_SECONDS = 2.5
BOUGHT_SECONDS = 1.5
TAB_SETTLE = 0.4
AIMS = (0.0, 0.03, 0.06)  # window heights above her drawn point the pointer is put at, her body up
BODY = 0.04  # window heights above her drawn point: her body's middle, clicked when no aim was named hers
HOVER_SECONDS = 0.25  # for the game's record of what is under the pointer to name her
FOLLOW = 0.5  # units she walks before the pointer is put on her again
FOLLOW_POLL = 0.04
MENU_CLICKS = 3  # one may go to a menu that opened mid-walk, closed and opened again standing
LINE = 0.0226  # window heights from one line of her menu to the next (the player's clicks of 2026-10-16)
LIFTS_FILE = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'menu-lifts.json'  # `learned` lifts by vendor
SERVING = [JAMELLA]  # the vendor visited now (`serving`)
LIFT = TRADE_ABOVE  # the lift that opened her trade window last (`_open_trade`)
STOCK_SECONDS = 2.0  # for her stock to be read after her trade window shows
BUY_CLICKS = 2  # Shift + right clicks on one item that bought nothing, in a row, at most
# Shift + right clicks on one item in all: the second key stack comes 3 keys a click now and then, between clicks that
# buy nothing (2 -> 12, nothing, 15, nothing at 01:47:20 and 01:57:00 on 2026-10-18), so 24 takes up to 8
BUY_MOST = 9
LEVEL_STAT = 12  # itemstatcost.txt 'level'
GOLD_PER_LEVEL = 10_000  # the gold a character carries at most, a level
SALE_MOST = 35_000  # the most a vendor pays for an item (every best sale of 2026-10-17)
GOLD_SECONDS = 1.0  # for the gold carried to settle after a purchase, or to change after a sale
GOLD_SETTLE = 0.25
WALKING = (2, 3, 6)  # the character's walk, run and town walk: the view moves with it


def short(pack: Pack | None, source: PortalSource = FROM_TOME) -> bool:
    """Whether the keys or the Town Portal charges are under MIN_STOCK (an unread count says nothing): a visit for them
    alone. The Tome of Identify's charges are filled on a visit made anyway (Cain identifies: macros/cain.py), and so
    are the others (the player, 2026-10-17: "refill when we have to sell something, and keep bare refills at
    minimum"). With the Sling's Town Portal (`source`, macros/portal.py) the portals are no stock: the keys alone (the
    player, 2026-10-18: "when we have sling ring equipped - we don't need to run any logic in regard of town portal (do
    not track, do not buy)"), the tome carried or not."""
    if pack is None:
        return False
    return any(count is not None and count < MIN_STOCK for count in (pack.keys, source.count(pack)))


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
    stuck = 0  # clicks in a row that did not move the character: the next is turned aside (TURNS)
    for _ in range(WALK_CLICKS + 1):
        world = run.world()
        player, there = world.player, place(world)
        if player is None or there is None:
            raise Abort(f'{what} is not in sight')
        if _inside(_drawn(world, there, aspect), bounds) or 'npc_interact' in world.open_panels:
            return world  # in view, or a click landed on her and opened her menu: a walk click would close it
        away = math.dist((player.x, player.y), there)
        ratio = min(1.0, STEP / away) if away else 0.0
        toward = (player.x + (there[0] - player.x) * ratio, player.y + (there[1] - player.y) * ratio)
        toward = _along(run, (player.x, player.y), there, toward)
        if stuck:
            # Beside Halbu at (5082, 5033) every click toward the waypoint moved the character a unit and back, 32 s
            # (02:00:17-49 on 2026-10-17): turned aside, one way then the other, wider each time
            angle = math.radians(TURNS[(stuck - 1) % len(TURNS)])
            dx, dy = toward[0] - player.x, toward[1] - player.y
            toward = (
                player.x + dx * math.cos(angle) - dy * math.sin(angle),
                player.y + dx * math.sin(angle) + dy * math.cos(angle),
            )
        run.actuator.move(*screen_fraction(player, toward[0], toward[1], aspect), scatter=(4, 4))
        run.actuator.click()
        began = (player.x, player.y)

        def walked(w: World, b=began) -> bool:
            return w.player is not None and math.dist((w.player.x, w.player.y), b) >= STEP * 0.6

        stuck = 0 if run.seen(walked, WALK_SECONDS) is not None else stuck + 1
    raise Abort(f'{what} not reached by walking')


def _along(run: Run, here: tuple[float, float], there: tuple[float, float], straight: tuple[float, float]):
    """Where a walk click toward `there` goes: `straight` on a clear line, else the furthest point within STEP of the
    shortest walk over the level's ground (travel.py `walked_way`) a clear line reaches. Kurast Docks' waypoint, from
    where a game begins there, is behind the dock's walls: the straight clicks took one step (01:26 on 2026-10-17)."""
    from inventory_tracking.combat.stance import no_footing
    from inventory_tracking.macros.travel import clear_line, walked_way

    ground = run.ground() if run.ground is not None else None
    if ground is None or clear_line(ground, (), here, straight):
        return straight
    barred = no_footing(ground, ())
    path = walked_way(barred, here, there) if barred is not None else []
    if not path:
        return straight
    near = [point for point in path if math.dist(here, point) <= STEP and clear_line(ground, (), here, point)]
    return near[-1] if near else path[0]


# Where each one the loop visits in Pandemonium Fortress stands most (the takes of 2026-10-15 to 17): walked toward when
# out of the units' reach, as Jamella is from Cain's place, 70 units west ("Jamella is not in sight", 12:01:23 on
# 2026-10-17); she is found on the way
USUAL = {405: (5083.5, 5058.5), 257: (5089.5, 5024.5), 246: (5022.8, 5032.7)}  # Jamella, Halbu, Deckard Cain
FORTRESS = 103


def whereabouts(world: World) -> tuple[float, float] | None:
    """Where the one visited (`SERVING`) is: as the game shows them, else, in the fortress, their usual place
    (USUAL)."""
    her = _her(world)
    if her is not None:
        return her.x, her.y
    if world.player is not None and world.player.area == FORTRESS:
        return USUAL.get(SERVING[0])
    return None


def _jamella(world: World) -> tuple[float, float] | None:
    return whereabouts(world)


def _settled(run: Run) -> int | None:
    """The gold carried once two reads GOLD_SETTLE apart agree (within GOLD_SECONDS): a purchase's cost lands late."""
    last, began = _gold(run), run.clock()
    while run.clock() - began < GOLD_SECONDS:
        run.pace.sleep(GOLD_SETTLE)
        now = _gold(run)
        if now == last:
            return now
        last = now
    return last


def gold_cap(run: Run) -> int | None:
    """The gold the character may carry: its level x GOLD_PER_LEVEL (stat 12 of its stats); None unread."""
    loot = run.loot() if run.loot is not None else None
    level = dict(loot.stats).get(LEVEL_STAT) if loot is not None and loot.stats else None
    return level * GOLD_PER_LEVEL if level else None


def _gold(run: Run) -> int | None:
    """The gold carried (stat 14), None unread: what the sales brought, for the repair (macros/junk.py)."""
    loot = run.loot() if run.loot is not None else None
    return dict(loot.stats).get(GOLD_STAT) if loot is not None and loot.stats else None


def _waypoint(run: Run) -> Callable[[World], tuple[float, float] | None]:
    def place(world: World) -> tuple[float, float] | None:
        shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
        return (shown[0].x, shown[0].y) if shown else None

    return place


def restock(run: Run, sell: Sequence[Carried] = (), back: bool = True, keys: int | None = None) -> None:
    """One visit to Jamella that buys keys and Town Portal scrolls (the module text), and sells `sell` (the junk, never
    a rune). Mouse mode only. `Abort` with her windows closed when a step does not take."""
    if run.pad is not None:
        raise Abort('the shop needs mouse mode')
    # No rune is sold (the player, 17:50 on 2026-10-18: the full stacks "cubed, aim to 80 or lower", macros/town.py
    # RUNES_AIM; a full stack's Tal Runes were sold here since 2026-10-17): one given is kept, whoever asks
    runes = [each for each in sell if each.txt in RUNE_CLASSES]
    if runes:
        LOG.info('Macro: shop: %d runes not sold: %s', len(runes), ', '.join(named(each) for each in runes))
        sell = [each for each in sell if each.txt not in RUNE_CLASSES]
    if run.carried is None or run.stock is None:
        raise Abort('the shop cannot be read')
    before = run.carried()
    source = portal_source(run)  # the Sling's Town Portal: no scrolls, nothing counted (macros/portal.py)
    if before is None or before.keys is None or (source.stocked and before.portals is None):
        raise Abort('the keys and the Town Portal charges are not read')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    aspect = rect[2] / rect[3]
    run.say(f'Shop: {before.keys} keys, {source.said(before)}')
    walk_until(run, _jamella, SEEN, 'Jamella')
    run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)  # the view still
    try:
        stock = _open_trade(run, aspect)
        # Sold first, then bought: a purchase's cost lands late and was read as a sale's (-140 gold, 11:41:38 and
        # 11:44:38 on 2026-10-17). Nothing bought yet, the gold is still: read at once (a settling wait made the
        # first sale 2.9 s after her stock, the visits of 12:33-12:57)
        coins = first = _gold(run) if sell else None
        cap = gold_cap(run) if sell else None
        for each in sell:
            # Gold over the cap a character carries (its level x 10,000) falls to the ground at a sale (the player,
            # 2026-10-17: "selling things over this gold limit - just drops extra gold on the ground"): no sale that may
            # bring more than the room left; what stays is sold at a later visit
            if cap is None or coins is None or coins + SALE_MOST > cap:
                LOG.info('Macro: shop: gold %s carried, %s at most: no sale over the cap (%d items kept)', coins, cap,
                         len(sell) - sell.index(each))  # fmt: skip
                break
            # Only the item still where the look saw it (the player's items are never sold: the player, 2026-10-17,
            # "we shouldn't sell our own equipment or valuable items")
            now = run.carried()
            if now is None or all((c.unit_id, c.x, c.y) != (each.unit_id, each.x, each.y) for c in now.items):
                LOG.info('Macro: shop: the item %d is no longer at (%d, %d): not sold', each.txt, each.x, each.y)
                continue
            if run.players_item is not None and run.players_item(each):
                LOG.info("Macro: shop: the %s at (%d, %d) is the player's by its stats: never sold", named(each),
                         each.x, each.y)  # fmt: skip
                continue
            others = {c.unit_id for c in now.items} - {each.unit_id}
            # A Ctrl + click on an inventory item with her trade window open sells it; checked by its leaving
            run.actuator.move(*cell_point(rect, INVENTORY, (each.x, each.y), each.size), scatter=(5, 5))
            run.actuator.click('Control_L')

            def sold(w: World, i=each) -> bool:
                p = run.carried() if run.carried is not None else None
                return p is not None and all(c.unit_id != i.unit_id for c in p.items)

            took = run.seen(sold, BOUGHT_SECONDS) is not None
            had = coins
            if took and had is not None:  # the gold stat follows the item's leaving
                run.seen(lambda _w, h=had: (_gold(run) or h) != h, GOLD_SECONDS)
            coins = _gold(run)
            brought = f' for {coins - had} gold' if took and had is not None and coins is not None else ''
            LOG.info('Macro: shop: %s the item %d at (%d, %d)%s: %s', 'sold' if took else 'could not sell', each.txt,
                     each.x, each.y, brought, named(each))  # fmt: skip
            after = run.carried()
            if after is not None and others - {c.unit_id for c in after.items}:
                raise Abort(f'an item other than the one sold left the inventory at ({each.x}, {each.y})')
        if sell:
            LOG.info('Macro: shop: carried gold %s -> %s after the sales', first, _gold(run))
        for what in buys(source, KEYS_WANTED if keys is None else keys):
            item = stock.get(what.txt)
            if item is None:
                LOG.info('Macro: shop: no %s in her stock', what.name)
                continue
            # Full already: no tab click and no wait for it (0.7 s a kind: the Tome of Identify at every visit, all
            # three on a second pass, 14:38:57-58 on 2026-10-17)
            now = run.carried()
            if now is not None and not what.room(now):
                LOG.info('Macro: shop: %s: %s carried, no room for more', what.name, what.count(now))
                continue
            run.actuator.move(*panel_point(rect, *tab_point(item.tab)), scatter=(15, 5))
            run.actuator.click()  # the tab it is on (Misc, the fourth, by the shop of 2026-10-16)
            run.pace.sleep(TAB_SETTLE)
            _buy(run, rect, item, what)
    finally:
        _close(run)
    after = run.carried()
    keys = after.keys if after is not None else None
    portals = after.portals if after is not None else None
    LOG.info('Macro: shop: keys %s -> %s, portals %s -> %s%s, identifies %s -> %s', before.keys, keys, before.portals,
             portals, '' if source.stocked else f' (Town Portal from {source.name}: none bought)', before.identifies,
             after.identifies if after is not None else None)  # fmt: skip
    run.say(f'Shop: {keys} keys, {source.said(after)}')
    if back:  # toward the chests: the waypoint; before Save and Exit there is no need (macros/loop.py)
        walk_until(run, _waypoint(run), (0.15, 0.85, 0.15, 0.8), 'the waypoint')


def _stock(run: Run) -> dict[int, Stocked]:
    """Her stock's items by class (any tab), once a key and a scroll are among them or STOCK_SECONDS have passed:
    her stock comes a moment after her window shows (23:57:55 and 23:58:04 on 2026-10-16: read 0.05 and 0.1 s after
    the window opened, it held neither, and the loop stopped on "not her trade window")."""
    assert run.stock is not None
    found: dict[int, Stocked] = {}

    def stocked(_: World) -> bool:
        assert run.stock is not None
        found.clear()
        found.update((item.txt, item) for item in reversed(run.stock(JAMELLA)))  # the first of each class kept
        return KEY in found and SCROLL in found

    began = run.clock()
    run.seen(stocked, STOCK_SECONDS)
    assert run.stock is not None
    every = run.stock(JAMELLA)
    LOG.info(
        'Macro: shop: her stock read %.2fs after her window: %d items by tab %s, key %s, scroll %s',
        run.clock() - began, len(every), dict(sorted(Counter(item.tab for item in every).items())),
        found.get(KEY), found.get(SCROLL),
    )  # fmt: skip
    return found


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
# Two stacks of keys (one more cell): with ~2.5 a game opened, one stack sent the loop to Jamella every 4 games, each
# errand a whole session (the player, 2026-10-17: "probably we need to carry 2 sets of keys, instead of 12 => 24")
KEYS_WANTED = 2 * KEY_STACK
# One stack where no chest is opened (Andariel's run: the player, 2026-10-18, "probably we don't need 2x sets of keys
# for non LK loop"): the second stack's cell stays free
KEYS_ONE_STACK = KEY_STACK
BUYS = (
    Buy(KEY, 'keys', lambda p: p.keys, lambda p: p.keys is None or p.keys < KEYS_WANTED),
    Buy(SCROLL, 'portals', lambda p: p.portals, lambda p: p.portals is None or p.portals < TOME_CHARGES),
    # the Tome of Identify's charges (macros/junk.py): only into a tome carried, a scroll of its own would take a cell
    Buy(
        IDENTIFY_SCROLL, 'identifies', lambda p: p.identifies, lambda p: p.identifies is not None and p.identifies < 20
    ),
)


def buys(source: PortalSource, keys: int = KEYS_WANTED) -> tuple[Buy, ...]:
    """What a visit buys: every BUYS but the scrolls when Town Portal is the Sling's (macros/portal.py): with no tome to
    take them a Shift + right click would put a scroll in a cell, and nothing casts it; the keys up to `keys`."""
    found = BUYS if source.stocked else tuple(what for what in BUYS if what.txt != SCROLL)
    if keys == KEYS_WANTED:
        return found
    return tuple(
        replace(what, room=lambda p, most=keys: p.keys is None or p.keys < most) if what.txt == KEY else what
        for what in found
    )


def _buy(run: Run, rect, item: Stocked, what: Buy) -> None:
    """Fill `what` from her stock's `item` by Shift + right clicks, each checked by the count, while there is room: a
    second key stack came 3 keys a click (12 -> 15, 17:31:59 on 2026-10-17). BUY_CLICKS that took nothing at most, and
    BUY_MOST in all."""
    assert run.carried is not None
    missed = 0
    for _ in range(BUY_MOST):
        if missed >= BUY_CLICKS:
            return
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
            missed = 0  # bought: again while there is room
            continue
        missed += 1
        LOG.info('Macro: shop: %s: still %s after the Shift + right click', what.name, had)


def _note(run: Run, aspect: float, what: str) -> None:
    """The shop's step for the log (the player, 2026-10-17: "add all required log"): the panels open, the character
    and her places and where she is drawn, the pointer, and what the game's record names under it."""
    world = run.world()
    her, me = _her(world), world.player
    drawn = _drawn(world, (her.x, her.y), aspect) if her is not None else None
    pointer = run.actuator.keys.pointer()
    rect = run.actuator.keys.focused_window_rect()
    at = (
        ((pointer[0] - rect[0]) / rect[2], (pointer[1] - rect[1]) / rect[3])
        if pointer is not None and rect is not None
        else None
    )
    LOG.info(
        'Macro: shop: %s: panels %s; the character %s mode %s; Jamella %s drawn %s; pointer %s; under it %s',
        what, list(world.open_panels),
        None if me is None else (round(me.x, 1), round(me.y, 1)), None if me is None else me.mode,
        None if her is None else (round(her.x, 1), round(her.y, 1)),
        None if drawn is None else (round(drawn[0], 4), round(drawn[1], 4)),
        None if at is None else (round(at[0], 4), round(at[1], 4)),
        run.hovered() if run.hovered is not None else 'unread',
    )  # fmt: skip


def _her(world: World) -> Monster | None:
    """The vendor the visit is to (`SERVING`: Jamella, or Halbu for a repair, macros/repair.py)."""
    return next((m for m in world.monsters if m.txt_id == SERVING[0]), None)


@contextmanager
def serving(vendor: int) -> Generator[None]:
    """The visit within is to `vendor` (monstats *hcIdx): `_her` and the steps that follow her find that one."""
    was = SERVING[0]
    SERVING[0] = vendor
    try:
        yield
    finally:
        SERVING[0] = was


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
                raise Abort(f'{VENDORS.get(SERVING[0], "the vendor")} is not in sight')
            if aimed is None or math.dist(aimed, (her.x, her.y)) > FOLLOW:
                run.actuator.move(drawn[0], drawn[1] - lift, scatter=(3, 3))
                aimed = (her.x, her.y)
            if run.hovered is None or run.hovered() == (MONSTER_UNIT, her.unit_id):
                return True
            if run.clock() >= deadline:
                break
            run.pace.sleep(FOLLOW_POLL)
    return False


def _open_trade(run: Run, aspect: float) -> dict[int, Stocked]:
    """Her trade window, and its Misc tab's stock: her menu (`_open_menu`), then a click on its Trade line, taken as the
    trade window only when its stock holds a key and a scroll. Gamble, the next line down, opens a vendor panel too: at
    00:37:00 on 2026-10-17 the click TRADE_ABOVE over her drawn point opened it (the player: "it has opened gamble
    window, not trade", "maybe clicks a few pixels off"), where at 23:57-00:01 the day before the player's own clicks
    on Trade were 0.212 to 0.226 over it. So each lift of `lifts()` is tried in turn, the window that is not hers
    closed between, and the lift that opened it is kept for the next visit (`LIFT`)."""
    global LIFT
    for lift in lifts():
        drawn = _open_menu(run, aspect)
        run.actuator.move(drawn[0], drawn[1] - lift, scatter=(6, 1))
        _note(run, aspect, f'the Trade line clicked {lift:.4f} over her')
        run.actuator.click()
        shown = run.seen(lambda w: 'npc_shop' in w.open_panels, PANEL_SECONDS)
        _note(run, aspect, 'after the Trade click')
        if shown is not None:
            stock = _stock(run)
            if KEY in stock and SCROLL in stock:
                LIFT = lift
                learned(JAMELLA, lift)
                return stock
            LOG.info('Macro: shop: the window %.4f over her is not her trade window (no key, no scroll): closed', lift)
        _close(run)
    raise Abort('her trade window did not open at any line tried')


def lifts() -> tuple[float, ...]:
    """The lifts over her drawn point the Trade line is clicked at, in turn: the one that opened it last, then the
    measured one, then a quarter of a line (LINE) higher and lower, then half a line higher. The clicks of 00:42 and
    01:10 on 2026-10-17 put the line between Trade and Gamble 0.218 over her: Trade's middle is 0.229."""
    last = known(JAMELLA) or LIFT
    tried = (last, TRADE_ABOVE, TRADE_ABOVE + LINE / 4, TRADE_ABOVE - LINE / 4, TRADE_ABOVE + LINE / 2)
    return tuple(dict.fromkeys(round(lift, 4) for lift in tried))


def _close(run: Run) -> None:
    if {'npc_shop', 'npc_interact', 'inventory'} & set(run.world().open_panels):
        run.actuator.tap('Escape')  # with nothing open it opens the game's menu instead
        run.seen(lambda w: not {'npc_shop', 'npc_interact'} & set(w.open_panels), PANEL_SECONDS)


def _drawn_now(run: Run, aspect: float) -> tuple[float, float]:
    world = run.world()
    her = _her(world)
    drawn = _drawn(world, (her.x, her.y), aspect) if her is not None else None
    if drawn is None:
        raise Abort(f'{VENDORS.get(SERVING[0], "the vendor")} is not in sight')
    return drawn


def _picture(run: Run, always: bool = False) -> None:
    """A screenshot of the open menu while the vendor's line is not learned (`known`), or `always` (a learned line
    that missed), for its geometry: the player, 2026-10-17, "looks like clicks were off ... probably you need to verify
    geometry coordinates"."""
    if known(SERVING[0]) is not None and not always:
        return
    path = LIFTS_FILE.parent / f'menu-{SERVING[0]}-{time.strftime("%H%M%S")}.png'
    try:
        subprocess.run(['grim', str(path)], timeout=3, check=True, capture_output=True)
        LOG.info('Macro: shop: the menu of %s pictured: %s', VENDORS.get(SERVING[0]), path)
    except (OSError, subprocess.SubprocessError) as error:
        LOG.info('Macro: shop: the menu not pictured: %s', error)


def known(vendor: int) -> float | None:
    """The lift that opened `vendor`'s vendor panel last (LIFTS_FILE), None not learned."""
    try:
        return json.loads(LIFTS_FILE.read_text()).get(str(vendor))
    except OSError, ValueError, AttributeError:
        return None


def learned(vendor: int, lift: float) -> None:
    """`lift` opened `vendor`'s vendor panel: kept in LIFTS_FILE."""
    try:
        kept = json.loads(LIFTS_FILE.read_text()) if LIFTS_FILE.exists() else {}
        if kept.get(str(vendor)) != lift:
            kept[str(vendor)] = lift
            LIFTS_FILE.write_text(json.dumps(kept))
            LOG.info('Macro: shop: %s line learned: %.4f over the drawn point', VENDORS.get(vendor), lift)
    except (OSError, ValueError, AttributeError) as error:
        LOG.info('Macro: shop: the lift not kept: %s', error)


def _open_menu(run: Run, aspect: float) -> tuple[float, float]:
    """Her menu by a click on her; where she was drawn as it opened: the menu stays where the game put it then, and the
    view can still move after (the character walking up to her: 01:38:35 on 2026-10-17).

    The vendors walk about (the player, 2026-10-16: "they are moving, so you cannot expect to find them at the same
    location"), so each aim is where she is drawn at that moment. At 23:07:04 that day the game's record never named
    her at any of the three aims (she stood still, 11 units off) and the loop stopped without a click; the click is now
    made all the same, at her body's middle, and her menu opening is what tells it took (MENU_CLICKS tries, each from
    where the character then stands: a click beside her walks it toward her)."""
    for _ in range(MENU_CLICKS):
        _note(run, aspect, 'before her menu')
        if 'npc_interact' in run.world().open_panels:
            # Open already: a walk click toward her that landed on her opens it as the game walks the character there
            # (23:57:48 on 2026-10-16), and a click on her then closed it again. It stays where she was drawn as it
            # opened, mid-walk, and lines aimed from where she is drawn after missed it (Halbu, 17:21:57 on
            # 2026-10-17): closed, and opened again with the character standing
            _close(run)
            run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
            continue
        if not _point_at_her(run, aspect):
            LOG.info('Macro: shop: the game names %s under the pointer, not Jamella: clicked at her all the same',
                     run.hovered() if run.hovered is not None else None)  # fmt: skip
            world = run.world()
            her = _her(world)
            drawn = _drawn(world, (her.x, her.y), aspect) if her is not None else None
            if drawn is None:
                raise Abort(f'{VENDORS.get(SERVING[0], "the vendor")} is not in sight')
            run.actuator.move(drawn[0], drawn[1] - BODY, scatter=(3, 3))
        run.actuator.click()
        opened = run.seen(lambda w: 'npc_interact' in w.open_panels, MENU_SECONDS)
        if opened is not None and opened.player is not None and opened.player.mode in WALKING:
            # Opened as the character still walked up (mode 3, 17:22:00 on 2026-10-17): drawn elsewhere once it stands
            _note(run, aspect, 'her menu opened mid-walk: opened again standing')
            _close(run)
            run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
            continue
        if opened is not None:
            _note(run, aspect, 'her menu open')
            _picture(run)
            return _drawn_now(run, aspect)
        _note(run, aspect, 'the click on her opened no menu')
        run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
    raise Abort('her menu did not open')
