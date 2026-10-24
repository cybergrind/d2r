"""Vendor visits: Jamella's restock of keys, Town Portal and Identify scrolls with the junk sold first (`restock`),
and the shared steps for any vendor or Cain: walking up (`walk_until`), opening the menu, clicking a menu line at a
learned lift (`menu_line`). "keep 3+ of each before run" (the player, 2026-10-16). Nothing is bought unless her stock
in memory holds a key and a scroll (Gamble's window is a vendor panel too). Layout from `vendorpanellayouthd.json`.
Evidence for the numbers: history/shop.md.
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
from inventory_tracking.config import BELT
from inventory_tracking.game.layout import (
    GOLD_PER_LEVEL,
    GOLD_STAT,
    ITEM_UNIT,
    KEY_STACK,
    LEVEL_STAT,
    MONSTER_UNIT,
    OBJECT_UNIT,
    TOME_CHARGES,
)
from inventory_tracking.game.records import Carried, Loot, Monster, Pack, Player, Stocked, Thing, World
from inventory_tracking.items.metadata import item_base
from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.levels.model import PORTAL, TOWN_PORTAL
from inventory_tracking.loot.api import reserve_short
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point
from inventory_tracking.macros.engine import Run, protected
from inventory_tracking.macros.junk import named
from inventory_tracking.macros.portal import FROM_TOME, PortalSource, portal_source
from inventory_tracking.macros.routines import screen_fraction
from inventory_tracking.macros.targeting import keep_mid_walk, labels_hidden, menu_drift, menu_or_stand
from inventory_tracking.macros.teleport import ground_fraction, in_view
from inventory_tracking.macros.waypoint import panel_point
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS
from inventory_tracking.shop.capture import VENDORS
from inventory_tracking.tracking.belt import UNSEEN, column_shortages, lowest, potion_kind


__all__ = ['BUY_POTIONS', 'MIN_STOCK', 'potions_wanted', 'restock', 'short']

JAMELLA = 405  # monstats *hcIdx (shop/capture.py VENDORS)
NAMES = {**VENDORS, 246: 'Deckard Cain'}  # the ones served, for the log: the vendors and Cain (macros/cain.py CAIN)
KEY, SCROLL = 558, 544  # Key, Scroll of Town Portal (items metadata, 2026-10-16)
IDENTIFY_SCROLL = 545  # Scroll of Identify (items metadata, 2026-10-17): the Tome of Identify's (macros/junk.py)
MIN_STOCK = 3  # the player: "keep 3+ of each before run"
TRADE_ABOVE = 0.229  # window heights from her drawn point up to the middle of her menu's Trade line
TABS, TAB_SIZE = (82, 162), (249, 75)  # layout units in the left panel: the vendor's tabs' corner and each tab's size


def tab_point(tab: int) -> tuple[float, float]:
    """The middle of tab `tab` (0 the first), in layout units from the panel's corner."""
    return TABS[0] + tab * TAB_SIZE[0] + TAB_SIZE[0] / 2, TABS[1] + TAB_SIZE[1] / 2


VENDOR = ((0.0, 0.397), (236, -651), (91, 233))  # the stock grid, as cube.py's grids
# Window fractions she is drawn within before she is clicked: her menu and feet inside, the bottom bar clear
SEEN = (0.1, 0.9, TRADE_ABOVE + 0.06, 0.8)
STEP = 12.0  # units a walk click goes toward a place
# Walk clicks at most toward a place (Kurast Docks' waypoint from its start: ~130 units; 16 ran out, 2026-10-17)
WALK_CLICKS = 30
WALK_SECONDS = 1.6  # for one walk to end
# Seconds from a walk click to the character going: 0.03-0.05 in the Docks takes of 2026-10-19 (20261019T174959Z-75)
TAKES = 0.4
WALKED_LEAST = 1.0  # units a walk click is done at, however short
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
# An item label over her (the game names an item under the pointer at every aim): the click on her body would take the
# item up, not open her menu. Deckard Cain walks up to the junk put down by the stash (16:05:00 on 2026-10-21: (4, ...)
# under the pointer at him, the click opened no menu). True: the labels hidden by the Show Items key for the aims and
# the click (targeting.py `labels_hidden`, as stash.py LABELS_OFF_AT_THE_STASH; the level run's `show_items_on` turns
# them on again if the key's second press does not take), 2026-10-23 with visit.py DOWN_GUARDED. False: clicked at her
# body all the same, as before
LABELS_OFF_AT_NPC = True
LINE = 0.0226  # window heights between menu lines (the player's clicks, 2026-10-16)
LIFTS_FILE = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / 'menu-lifts.json'  # `learned` lifts by vendor
HITS_KEPT = 40  # the lifts that took kept by vendor (`hits`): their middle is clicked first (`known`)
SERVING = [JAMELLA]  # the vendor visited now (`serving`)
LIFT = TRADE_ABOVE  # the lift that opened her trade window last (`_open_trade`)
STOCK_SECONDS = 2.0  # for her stock to be read after her trade window shows
BUY_CLICKS = 2  # Shift + right clicks on one item that bought nothing, in a row, at most
# Shift + right clicks on one item in all: the second key stack comes 3 keys a click, between clicks that buy nothing
BUY_MOST = 9
SALE_MOST = 35_000  # the most a vendor pays for an item (every best sale of 2026-10-17)
GOLD_SECONDS = 1.0  # for the gold carried to settle after a purchase, or to change after a sale
GOLD_SETTLE = 0.25
WALKING = (2, 3, 6)  # the character's walk, run and town walk: the view moves with it
# 15:31:35.8 on 2026-10-23 (rca/2026-10-23/visit-portal-findings.md): the visit's first walk click toward Deckard Cain,
# made from beside the Town Portal the character had come through, went to a ground point 4.3 units past the portal's,
# 0.079 window heights over its ground point: inside its picture, and the game's record named it under the pointer
# ((2, 2264798530)). The character walked into it and back to the River of Flame. True: a town walk's click with a way
# out (WAYS_OUT: a portal, a waypoint) under the pointer that is not the walk's own goal (within GOAL_NEAR of its
# place) is turned aside (OFF_WAY_TURNS) to an aim with none under it, and refused (`Abort`) when every turn has one;
# the record is looked at only with a way out within WAY_NEAR of the click's ground. A townsperson's menu click at the
# body is refused the same way. False: clicked where aimed, as before
WALK_OFF_WAYS = True
WAYS_OUT = frozenset((TOWN_PORTAL, PORTAL, *WAYPOINT_CLASSES))
WAY_NEAR = 8.0  # world units from a click's ground to a way out's within which its picture may be under the pointer
GOAL_NEAR = 3.0  # world units from the walk's place within which a way out is the walk's own goal (the portal's walk)
OFF_WAY_TURNS = (30, -30, 60, -60, 90, -90)  # degrees the walk's step is turned to get a way out from under the click
WAY_HOVER_SECONDS = 0.06  # for the record of what is under the pointer to follow it (teleport.py HOVER_SECONDS)
# 2026-10-24 (rca/2026-10-24/stash-amulet-findings.md): at 18:54:22.7 the walk to the stash clicked at the label of the
# Eagle Necklace the loop itself had put down by the stash at 18:50:28 ("Jamella not needed"); the game's record named
# it under the pointer ((4, 2388730699)) 0.18 s before the click, the character walked to it and took it up into the
# 2x4 block ("short of the contract: block 2x4 taken, 1 keepers carried (rare Amulet at (3, 3))"). Seven such pickups
# of the town's junk in the visit snapshots of 2026-10-19..24, three of them walk clicks in the takes; the stash's and
# the townsfolk's own clicks look under the pointer (teleport.py `use_thing`, LABELS_OFF_AT_NPC), the walk's did not.
# True: every town walk click reads the record first (WAY_HOVER_SECONDS each) and one with a ground item under it is
# turned aside as a way out is (OFF_WAY_TURNS); with an item under every turn it is clicked where first aimed, as
# before. False: only a way out is looked for, as before
WALK_OFF_ITEMS = True  # on from the restart after 20:05 on 2026-10-24 (main session: town suites 447 passed on and off)
# Healing potions bought into the belt's healing columns at her trade window (the player, 2026-10-21 ~13:38: "can we
# also add into town routine ability to buy hp potions"; "empty belt = defect"). Only the best healing grade in her
# stock, one plain right click a potion, each checked by the belt read; only while the healing columns are short and
# the carried gold stays over POTIONS_RESERVE (a vendor takes what the carried gold does not cover from the stash's,
# repair.py GOLDBANK: the reserve keeps that from happening). False: none bought, as before
BUY_POTIONS = True
# 2026-10-22 (rca/2026-10-22/belt-refill-findings.md): every visit bought 4 of a belt short 5 or 6 (23:01:10 and
# 23:02:57, the shard game cyberg65), so the belt was low again a burst of the healer later: every plain right click
# after one that bought buys nothing (13 refills of 2026-10-21/22 fit it exactly; keys too, history/shop.md), and the
# clicks were capped at the shortage + BUY_CLICKS. On: the clicks are capped at twice the shortage + BUY_CLICKS (each
# potion may take a click that buys nothing; BUY_CLICKS misses in a row still end it), and after each potion bought
# the next click waits for its cost to leave the carried gold (`_cost_landed`: the game's own end of the purchase).
# False: the shortage + BUY_CLICKS clicks, the next at once, as before
POTIONS_FILL = True
# Healing potions by grade, the weakest first: hp1-hp5, d2data misc.json classid (Minor 602 ... Super 606). Jamella
# and Malah stock hp1-hp4, Ormus hp1-hp3, Lysander and Drognan hp1-hp2, Akara hp1 (misc.json `<Vendor>Min`); in Hell
# each becomes hp5 (misc.json HellUpgrade), so she sells Super Healing there
HEALING_GRADES = (602, 603, 604, 605, 606)
# Carried gold kept after the potions: over what an unread repair quote wants carried (~72k at the 11k staff quote,
# repair.py UNREAD_COVER, UNREAD_EXTRA). The loop carried 214k-950k on 2026-10-20
POTIONS_RESERVE = 100_000
POTION_COST_MOST = 2_000  # gold one potion may cost at most (Super Healing: misc.json cost 500), for the check


def short(pack: Pack | None, source: PortalSource = FROM_TOME) -> bool:
    """Whether keys or Town Portal charges are under MIN_STOCK (unread counts say nothing): a visit for them alone.
    Identify charges were only filled on a visit made anyway ("refill when we have to sell something, and keep bare
    refills at minimum", the player, 2026-10-17); with the field identify on (loot/api.py, M4: "identify with scroll,
    and drop if it is bad", 2026-10-20) the Tome under IDENTIFY_RESERVE charges is short too (loot/design.md §5). With
    the Sling's Town Portal only keys count: "do not track, do not buy" (2026-10-18)."""
    if pack is None:
        return False
    stock = (pack.keys, source.count(pack))
    return any(count is not None and count < MIN_STOCK for count in stock) or reserve_short(pack.identifies)


def _drawn(world: World, place: tuple[float, float], aspect: float) -> tuple[float, float] | None:
    player = world.player
    return None if player is None else screen_fraction(player, *place, aspect)


def _inside(point: tuple[float, float] | None, bounds: tuple[float, float, float, float]) -> bool:
    return point is not None and bounds[0] <= point[0] <= bounds[1] and bounds[2] <= point[1] <= bounds[3]


def walk_until(
    run: Run,
    place: Callable[[World], tuple[float, float] | None],
    bounds,
    what: str,
    *,
    until: Callable[[World], bool] | None = None,
    clicks: int = WALK_CLICKS,
    to_npc: bool = True,
) -> World:
    """Walk toward `place(world)` until it is drawn within `bounds` (window fractions); the world then. `Abort`.
    With `until` the walk ends when `until(world)` holds instead (the walk out of a town, macros/townexit.py), and a
    panel a click opened on the way (townsfolk, the stash) is closed and the next click turned. `to_npc` False (the
    waypoint): an open townsfolk menu is not the walk's end but closed the same way (2026-10-22 20:27, Rogue
    Encampment: a menu open at the arrival ended each of three waypoint walks at once, and the loop stopped)."""
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    aspect = rect[2] / rect[3]
    stuck = 0  # clicks in a row that did not move the character (TURNS)
    for _ in range(clicks + 1):
        world = run.world()
        if until is not None and until(world):
            return world
        player, there = world.player, place(world)
        if player is None or there is None:
            raise Abort(f'{what} is not in sight')
        if until is None and (
            _inside(_drawn(world, there, aspect), bounds) or (to_npc and 'npc_interact' in world.open_panels)
        ):
            return world  # a click landed on her and opened her menu: a walk click would close it
        if not to_npc and 'waypoint' in world.open_panels:
            return world  # a walk click landed on the waypoint: its panel is the goal
        if (until is not None or not to_npc) and world.open_panels:
            LOG.info('Macro: walk: %s: %s opened on the way: closed', what, ', '.join(world.open_panels))
            run.actuator.tap('Escape')
            run.seen(lambda w: not w.open_panels, PANEL_SECONDS)
            stuck += 1
            continue
        away = math.dist((player.x, player.y), there)
        ratio = min(1.0, STEP / away) if away else 0.0
        toward = (player.x + (there[0] - player.x) * ratio, player.y + (there[1] - player.y) * ratio)
        toward = _along(run, (player.x, player.y), there, toward)
        if stuck:
            # Turned aside, one way then the other, wider each time (stuck beside Halbu, 2026-10-17)
            angle = math.radians(TURNS[(stuck - 1) % len(TURNS)])
            dx, dy = toward[0] - player.x, toward[1] - player.y
            toward = (
                player.x + dx * math.cos(angle) - dy * math.sin(angle),
                player.y + dx * math.sin(angle) + dy * math.cos(angle),
            )
        # On the ground point, not lifted onto a body: the lift put Kurast Docks' first clicks into the wall by the
        # start, and each stood WALK_SECONDS (20:49-20:51 on 2026-10-19, games 9-11); off a way out (WALK_OFF_WAYS)
        _aim_walk(run, player, there, toward, aspect, what)
        run.actuator.click()
        began = (player.x, player.y)
        # A short click (a corner, the last steps) is done once 0.6 of its own way is walked, not of STEP's
        need = max(WALKED_LEAST, 0.6 * min(STEP, math.dist(began, toward)))

        def going(w: World, b=began) -> bool:
            return w.player is not None and (w.player.mode in WALKING or math.dist((w.player.x, w.player.y), b) >= 0.5)

        def walked(w: World, b=began, n=need) -> bool:
            return w.player is not None and math.dist((w.player.x, w.player.y), b) >= n

        # A click not taken (no walk TAKES after it) is turned at once, not stood WALK_SECONDS
        taken = run.seen(going, TAKES) is not None
        stuck = 0 if taken and run.seen(walked, WALK_SECONDS) is not None else stuck + 1
    if until is not None and until(world := run.world()):
        return world
    raise Abort(f'{what} not reached by walking')


def ways_out(run: Run, goal: tuple[float, float] | None = None) -> tuple[Thing, ...]:
    """The ways out of town shown (WAYS_OUT: portals, waypoints) but one at `goal` (within GOAL_NEAR: a walk's own)."""
    things = run.things() if run.things is not None else ()
    return tuple(
        t for t in things if t.txt_id in WAYS_OUT and (goal is None or math.dist((t.x, t.y), goal) > GOAL_NEAR)
    )


def way_under(run: Run, ways: Sequence[Thing]) -> Thing | None:
    """The one of `ways` the game's record names under the pointer now (after WAY_HOVER_SECONDS); None: none of them,
    or no record."""
    if run.hovered is None or not ways:
        return None
    run.pace.sleep(WAY_HOVER_SECONDS)
    over = run.hovered()
    if over is None or over[0] != OBJECT_UNIT:
        return None
    return next((t for t in ways if t.unit_id == over[1]), None)


def way_name(thing: Thing) -> str:
    kind = 'Town Portal' if thing.txt_id == TOWN_PORTAL else 'portal' if thing.txt_id == PORTAL else 'waypoint'
    return f'the {kind} ({thing.unit_id})'


def _aim_walk(
    run: Run,
    player: Player,
    there: tuple[float, float],
    toward: tuple[float, float],
    aspect: float,
    what: str,
) -> None:
    """The pointer put on the ground at `toward`, a walk click's on the way to `there`; with WALK_OFF_WAYS, off any way
    out of town but the walk's own (`ways_out`), and with WALK_OFF_ITEMS off any ground item: at the first turn of the
    step about the character (OFF_WAY_TURNS) with none under it. `Abort` when every turn has one and the first aim a
    way out; with an item there (no way out), the first aim is clicked all the same, as before."""
    ways = ways_out(run, there) if WALK_OFF_WAYS else ()

    def aimed(point: tuple[float, float]) -> tuple[str, bool] | None:
        """The pointer put at `point`'s ground; (what is under it, whether a way out), None with nothing in the way
        (or no way out near it and WALK_OFF_ITEMS off)."""
        run.actuator.move(*ground_fraction(player, point[0], point[1], aspect), scatter=(4, 4))
        near_way = any(math.dist(point, (t.x, t.y)) <= WAY_NEAR for t in ways)
        if run.hovered is None or not (near_way or WALK_OFF_ITEMS):
            return None
        run.pace.sleep(WAY_HOVER_SECONDS)
        over = run.hovered()
        if over is None:
            return None
        way = next((t for t in ways if t.unit_id == over[1]), None) if near_way and over[0] == OBJECT_UNIT else None
        if way is not None:
            return way_name(way), True
        if WALK_OFF_ITEMS and over[0] == ITEM_UNIT:
            return f'the ground item ({over[1]})', False
        return None

    under = aimed(toward)
    if under is None:
        return
    dx, dy = toward[0] - player.x, toward[1] - player.y
    tried = [f'{toward[0]:.1f}, {toward[1]:.1f}']
    for degrees in OFF_WAY_TURNS:
        angle = math.radians(degrees)
        turned = (
            player.x + dx * math.cos(angle) - dy * math.sin(angle),
            player.y + dx * math.sin(angle) + dy * math.cos(angle),
        )
        if not in_view(ground_fraction(player, turned[0], turned[1], aspect)):
            continue
        if aimed(turned) is None:
            LOG.info('Macro: walk: %s: %s under the click at (%s): turned %+d degrees to (%.1f, %.1f)', what,
                     under[0], tried[0], degrees, *turned)  # fmt: skip
            return
        tried.append(f'{turned[0]:.1f}, {turned[1]:.1f}')
    if under[1]:
        raise Abort(f'{what}: {under[0]} under every walk click tried ({"; ".join(tried)}): not clicked')
    run.actuator.move(*ground_fraction(player, toward[0], toward[1], aspect), scatter=(4, 4))
    LOG.info('Macro: walk: %s: %s under the click at (%s) and a ground item or a way out under every turn: clicked '
             'where first aimed', what, under[0], tried[0])  # fmt: skip


def _along(run: Run, here: tuple[float, float], there: tuple[float, float], straight: tuple[float, float]):
    """Where a walk click toward `there` goes: `straight` on a clear line, else the furthest point within STEP of the
    shortest walk (travel.py `walked_way`) a clear line reaches (Kurast Docks' waypoint is behind walls)."""
    from inventory_tracking.combat.stance import no_footing
    from inventory_tracking.macros.travel import clear_line, walked_way

    ground = run.reads.ground()
    if ground is None or clear_line(ground, (), here, straight):
        return straight
    barred = no_footing(ground, ())
    path = walked_way(barred, here, there) if barred is not None else []
    if not path:
        return straight
    near = [point for point in path if math.dist(here, point) <= STEP and clear_line(ground, (), here, point)]
    return near[-1] if near else path[0]


# Where each NPC in Pandemonium Fortress usually stands (takes of 2026-10-15 to 17): walked toward when out of reach
USUAL = {405: (5083.5, 5058.5), 257: (5089.5, 5024.5), 246: (5022.8, 5032.7)}  # Jamella, Halbu, Deckard Cain
FORTRESS = 103


def whereabouts(world: World) -> tuple[float, float] | None:
    """Where the one visited (`SERVING`) is: as the game shows them, else, in the fortress, USUAL."""
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
    loot = run.reads.loot()
    level = dict(loot.stats).get(LEVEL_STAT) if loot is not None and loot.stats else None
    return level * GOLD_PER_LEVEL if level else None


def _gold(run: Run) -> int | None:
    """The gold carried (stat 14), None unread: what the sales brought, for the repair (macros/junk.py)."""
    loot = run.reads.loot()
    return dict(loot.stats).get(GOLD_STAT) if loot is not None and loot.stats else None


def _waypoint(run: Run) -> Callable[[World], tuple[float, float] | None]:
    def place(world: World) -> tuple[float, float] | None:
        shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
        return (shown[0].x, shown[0].y) if shown else None

    return place


def restock(run: Run, sell: Sequence[Carried] = (), back: bool = True, keys: int | None = None) -> None:
    """One visit to Jamella: sells `sell` (never a rune), then buys keys and scrolls. Mouse mode only. `Abort` with
    her windows closed when a step does not take."""
    if run.pad is not None:
        raise Abort('the shop needs mouse mode')
    # No rune is sold: full stacks are "cubed, aim to 80 or lower" (the player, 2026-10-18; town.py RUNES_AIM)
    runes = [each for each in sell if each.txt in RUNE_CLASSES]
    if runes:
        LOG.info('Macro: shop: %d runes not sold: %s', len(runes), ', '.join(named(each) for each in runes))
        sell = [each for each in sell if each.txt not in RUNE_CLASSES]
    if run.carried is None or run.stock is None:
        raise Abort('the shop cannot be read')
    before = run.carried()
    source = portal_source(run)  # the Sling's Town Portal: no scrolls counted (macros/portal.py)
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
        # Sold first, then bought: a purchase's cost lands late and was read as a sale's. Nothing bought yet, so the
        # gold is read at once
        coins = first = _gold(run) if sell else None
        cap = gold_cap(run) if sell else None
        for each in sell:
            # "selling things over this gold limit - just drops extra gold on the ground" (the player, 2026-10-17)
            if cap is None or coins is None or coins + SALE_MOST > cap:
                LOG.info('Macro: shop: gold %s carried, %s at most: no sale over the cap (%d items kept)', coins, cap,
                         len(sell) - sell.index(each))  # fmt: skip
                break
            # Only the item still where the look saw it: "we shouldn't sell our own equipment" (the player, 2026-10-17)
            now = run.carried()
            if now is None or all((c.unit_id, c.x, c.y) != (each.unit_id, each.x, each.y) for c in now.items):
                LOG.info('Macro: shop: the item %d is no longer at (%d, %d): not sold', each.txt, each.x, each.y)
                continue
            if why := protected(run, each):
                LOG.info('Macro: shop: the %s at (%d, %d) is %s: never sold', named(each), each.x, each.y, why)
                continue
            others = {c.unit_id for c in now.items} - {each.unit_id}
            # A Ctrl + click on an inventory item with her trade window open sells it; checked by its leaving
            run.actuator.move(*cell_point(rect, INVENTORY, (each.x, each.y), each.size), scatter=(5, 5))
            run.actuator.click('Control_L')

            def sold(w: World, i=each) -> bool:
                p = run.reads.carried()
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
            # Full already: no tab click and no wait (0.7 s a kind)
            now = run.carried()
            if now is not None and not what.room(now):
                LOG.info('Macro: shop: %s: %s carried, no room for more', what.name, what.count(now))
                continue
            run.actuator.move(*panel_point(rect, *tab_point(item.tab)), scatter=(15, 5))
            run.actuator.click()  # its tab (Misc, the fourth)
            run.pace.sleep(TAB_SETTLE)
            _buy(run, rect, item, what)
        if BUY_POTIONS:
            _potions(run, rect, stock)
    finally:
        _close(run)
    after = run.carried()
    keys = after.keys if after is not None else None
    portals = after.portals if after is not None else None
    LOG.info('Macro: shop: keys %s -> %s, portals %s -> %s%s, identifies %s -> %s', before.keys, keys, before.portals,
             portals, '' if source.stocked else f' (Town Portal from {source.name}: none bought)', before.identifies,
             after.identifies if after is not None else None)  # fmt: skip
    run.say(f'Shop: {keys} keys, {source.said(after)}')
    if back:  # back to the waypoint; not before Save and Exit
        walk_until(run, _waypoint(run), (0.15, 0.85, 0.15, 0.8), 'the waypoint')


def _stock(run: Run) -> dict[int, Stocked]:
    """Her stock's items by class (any tab), once a key and a scroll are among them or STOCK_SECONDS have passed: the
    stock lands a moment after her window shows."""
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


# A Shift + right click fills the key stack or the tome: made only where there is room (a full stack's keys would take
# a new cell), checked by the count in memory: "you can bulk buy with (shift+right click)" (the player, 2026-10-16).
# Two key stacks: "we need to carry 2 sets of keys, instead of 12 => 24" (2026-10-17)
KEYS_WANTED = 2 * KEY_STACK
# One stack where no chest is opened: "we don't need 2x sets of keys for non LK loop" (2026-10-18)
KEYS_ONE_STACK = KEY_STACK
BUYS = (
    Buy(KEY, 'keys', lambda p: p.keys, lambda p: p.keys is None or p.keys < KEYS_WANTED),
    Buy(SCROLL, 'portals', lambda p: p.portals, lambda p: p.portals is None or p.portals < TOME_CHARGES),
    # Identify: only into a tome carried, a loose scroll would take a cell
    Buy(
        IDENTIFY_SCROLL, 'identifies', lambda p: p.identifies, lambda p: p.identifies is not None and p.identifies < 20
    ),
)


def buys(source: PortalSource, keys: int = KEYS_WANTED) -> tuple[Buy, ...]:
    """What a visit buys: BUYS, without Town Portal scrolls when the Sling casts it (no tome: a scroll would take a
    cell); keys up to `keys`."""
    found = BUYS if source.stocked else tuple(what for what in BUYS if what.txt != SCROLL)
    if keys == KEYS_WANTED:
        return found
    return tuple(
        replace(what, room=lambda p, most=keys: p.keys is None or p.keys < most) if what.txt == KEY else what
        for what in found
    )


def _buy(run: Run, rect, item: Stocked, what: Buy) -> None:
    """Fill `what` from her stock's `item` by Shift + right clicks while there is room, each checked by the count;
    BUY_CLICKS misses in a row at most, BUY_MOST in all."""
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
            p = run.reads.carried()
            return p is not None and what.count(p) != h

        if run.seen(came, BOUGHT_SECONDS) is not None:
            missed = 0
            continue
        missed += 1
        LOG.info('Macro: shop: %s: still %s after the Shift + right click', what.name, had)


def healing_short(loot: Loot | None) -> int | None:
    """Healing potions the belt's healing columns miss (tracking/belt.py `column_shortages`); None for an unread belt
    (macros/supply.py `unread`)."""
    from inventory_tracking.macros.supply import unread

    if loot is None or unread(loot):
        return None
    return column_shortages(loot.belt, loot.columns, BELT.layout)[1]


def affordable_potions(coins: int | None) -> bool:
    """Whether the carried gold buys a potion and keeps POTIONS_RESERVE; unread gold buys none."""
    return coins is not None and coins >= POTIONS_RESERVE + POTION_COST_MOST


def potions_wanted(loot: Loot | None, coins: int | None, least: int = 1) -> int:
    """The healing potions a stop at her would buy (BUY_POTIONS): the healing columns' shortage when it is `least` or
    more and the carried gold `coins` affords them; else 0."""
    short = healing_short(loot)
    if not BUY_POTIONS or not short or short < least or not affordable_potions(coins):
        return 0
    return short


def healing_columns(loot: Loot) -> frozenset[int]:
    """The belt columns (0-3) a healing potion belongs in: the configured layout's (config BELT, the player's 2026-10-13
    layout), else the kind each column last held (`Loot.columns`), as `column_shortages` reads an empty one."""
    if BELT.layout is not None:
        return frozenset(c for c, kind in enumerate(BELT.layout) if kind is PotionType.HEALING)
    kinds = loot.columns.kinds if loot.columns is not None else (None,) * BELT_COLUMNS
    found = set()
    for column in range(BELT_COLUMNS):
        first = lowest(loot.belt, column)
        kind = potion_kind(first) if first is not None else (kinds[column] or UNSEEN)
        if kind is PotionType.HEALING:
            found.add(column)
    return frozenset(found)


def _loose_potions(run: Run) -> frozenset[int]:
    pack = run.reads.carried()
    return frozenset(i.unit_id for i in pack.items if i.txt in HEALING_GRADES) if pack is not None else frozenset()


def _potions(run: Run, rect, stock: dict[int, Stocked]) -> None:
    """The belt's healing columns topped up from her stock (BUY_POTIONS): the best grade she has, a plain right click a
    potion, each checked by the belt read. Stops at a full belt, the gold at POTIONS_RESERVE, BUY_CLICKS clicks in a
    row that bought nothing, or a potion that landed elsewhere than a healing column (the inventory, a rejuvenation
    column): never more than one is bought past what the belt takes."""
    loot = run.reads.loot()
    before = healing_short(loot)
    if not before or loot is None:
        return  # full or unread: no tab click
    grade = max((txt for txt in stock if txt in HEALING_GRADES), default=None)
    if grade is None:
        LOG.info('Macro: shop: potions: belt short %d, none bought: no healing potion in her stock', before)
        return
    name = (item_base(grade) or {}).get('name', f'potion {grade}')
    first = _gold(run)
    if not affordable_potions(first):
        LOG.info('Macro: shop: potions: belt short %d, none bought: carried gold %s, %d kept', before, first,
                 POTIONS_RESERVE)  # fmt: skip
        return
    item, columns = stock[grade], healing_columns(loot)
    run.actuator.move(*panel_point(rect, *tab_point(item.tab)), scatter=(15, 5))
    run.actuator.click()  # its tab
    run.pace.sleep(TAB_SETTLE)
    bought, missed, clicks, dry, why = 0, 0, 0, 0, ''
    most = potion_clicks(before)
    for _ in range(most):
        now = run.reads.loot()
        short = healing_short(now)
        if now is None or not short:
            break
        coins = _gold(run)
        if not affordable_potions(coins):
            why = f': carried gold {coins}, {POTIONS_RESERVE} kept'
            break
        if missed >= BUY_CLICKS:
            why = f': {missed} clicks bought nothing'
            break
        loose = _loose_potions(run)
        run.actuator.move(*cell_point(rect, VENDOR, (item.x, item.y)), scatter=(5, 5))
        run.actuator.tap('Button3')  # a plain right click buys one (Shift would fill every column the game picks)
        clicks += 1

        def came(_w: World, b=now.belt, held=loose) -> bool:
            after = run.reads.loot()
            return (after is not None and after.belt_read and after.belt != b) or _loose_potions(run) != held

        if run.seen(came, BOUGHT_SECONDS) is None:
            missed += 1
            dry += 1
            continue
        missed = 0
        if POTIONS_FILL:
            _cost_landed(run, coins)
        if _loose_potions(run) - loose:
            bought += 1
            why = ': one landed in the inventory'
            break
        after = run.reads.loot()
        cells = [c for c, (was, is_now) in enumerate(zip(now.belt, after.belt if after else now.belt, strict=True))
                 if is_now in HEALING_GRADES and was != is_now]  # fmt: skip
        if not cells:
            continue
        bought += 1
        if cells[0] % BELT_COLUMNS not in columns:
            why = f': one landed in belt column {cells[0] % BELT_COLUMNS + 1}, not a healing column'
            break
    else:
        if healing_short(run.reads.loot()):
            why = f': {most} clicks made'
    spent = (first - last) if (last := _settled(run)) is not None and first is not None else None
    LOG.info('Macro: shop: potions: belt short %d -> %s, bought %d %s for %s gold%s (%d clicks, %d bought nothing)',
             before, healing_short(run.reads.loot()), bought, name, spent, why, clicks, dry)  # fmt: skip


def potion_clicks(short: int) -> int:
    """The plain right clicks one top-up of a belt `short` healing potions makes at most: POTIONS_FILL, room for a click
    that buys nothing beside each potion (each click after one that bought bought nothing on 2026-10-21/22), else the
    shortage + BUY_CLICKS as before."""
    return (2 * short if POTIONS_FILL else short) + BUY_CLICKS


def _cost_landed(run: Run, coins: int | None) -> None:
    """After a potion bought: until its cost has left the carried gold `coins` (read before its click), GOLD_SECONDS at
    most; at once with the gold unread. The next click is made after it, as the game ends the purchase."""
    if coins is None:
        return
    run.seen(lambda _w: (_gold(run) or coins) != coins, GOLD_SECONDS)


def _note(run: Run, aspect: float, what: str) -> None:
    """Log the step: open panels, the character's and her places, where she is drawn, the pointer, what is hovered."""
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
        'Macro: shop: %s: panels %s; the character %s mode %s; %s %s drawn %s; pointer %s; under it %s',
        what, list(world.open_panels),
        None if me is None else (round(me.x, 1), round(me.y, 1)), None if me is None else me.mode,
        NAMES.get(SERVING[0], 'the vendor'), None if her is None else (round(her.x, 1), round(her.y, 1)),
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
    """Put the pointer on her at each of AIMS, following her walk, until the hover record names her; whether it did
    (an unreadable record counts as named)."""
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
    """Her trade window's stock: each of `lifts()` tried on the Trade line until a window with a key and a scroll
    opens (Gamble's window is a vendor panel too: "it has opened gamble window, not trade", 2026-10-17); the lift that
    took is kept in `LIFT`."""
    global LIFT
    found: list[dict[int, Stocked]] = []

    def took(lift: float) -> bool:
        shown = run.seen(lambda w: 'npc_shop' in w.open_panels, PANEL_SECONDS)
        _note(run, aspect, 'after the Trade click')
        if shown is None:
            return False
        stock = _stock(run)
        if KEY in stock and SCROLL in stock:
            found.append(stock)
            return True
        LOG.info('Macro: shop: the window %.4f over her is not her trade window (no key, no scroll): closed', lift)
        return False

    try:
        LIFT = menu_line(run, aspect, 'Trade', lifts(), took)
    except Abort:
        raise Abort('her trade window did not open at any line tried') from None
    return found[-1]


def lifts() -> tuple[float, ...]:
    """The lifts the Trade line is tried at, in turn: the learned or last one, TRADE_ABOVE, a quarter LINE higher and
    lower, half a line higher."""
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
    """A screenshot of the open menu while the vendor's line is not learned, or `always`, to verify the geometry
    ("probably you need to verify geometry coordinates", the player, 2026-10-17)."""
    if known(SERVING[0]) is not None and not always:
        return
    path = LIFTS_FILE.parent / f'menu-{SERVING[0]}-{time.strftime("%H%M%S")}.png'
    try:
        subprocess.run(['grim', str(path)], timeout=3, check=True, capture_output=True)
        LOG.info('Macro: shop: the menu of %s pictured: %s', NAMES.get(SERVING[0]), path)
    except (OSError, subprocess.SubprocessError) as error:
        LOG.info('Macro: shop: the menu not pictured: %s', error)


def hits(vendor: int) -> list[float]:
    """The lifts that took on `vendor`'s line, the latest last (LIFTS_FILE)."""
    try:
        kept = json.loads(LIFTS_FILE.read_text()).get(str(vendor))
    except OSError, ValueError, AttributeError:
        return []
    return [float(lift) for lift in kept] if isinstance(kept, list) else []


def known(vendor: int) -> float | None:
    """Where `vendor`'s line is clicked first: the middle of the lifts that took (`hits`), None not learned. The last
    hit alone sat on an edge of the line and missed now and then (9 of 212 Cain visits, 2026-10-18/19)."""
    took = hits(vendor)
    return round((min(took) + max(took)) / 2, 4) if took else None


def learned(vendor: int, lift: float) -> None:
    """`lift` took on `vendor`'s line: kept in LIFTS_FILE among the last HITS_KEPT."""
    try:
        kept = json.loads(LIFTS_FILE.read_text()) if LIFTS_FILE.exists() else {}
        before = known(vendor)
        kept[str(vendor)] = [*hits(vendor), round(lift, 4)][-HITS_KEPT:]
        LIFTS_FILE.write_text(json.dumps(kept))
        if known(vendor) != before:
            LOG.info('Macro: shop: %s line learned: %.4f over the drawn point (%.4f took)', NAMES.get(vendor),
                     known(vendor), lift)  # fmt: skip
    except (OSError, ValueError, AttributeError) as error:
        LOG.info('Macro: shop: the lift not kept: %s', error)


def menu_line(
    run: Run, aspect: float, line: str, lifts: Sequence[float], took: Callable[[float], bool], picture: bool = False
) -> float:
    """Open the menu of the one served (`SERVING`) and click its `line` at each of `lifts` over their drawn point until
    `took(lift)`; that lift is learned and returned. Every vendor's and Cain's menu line goes through here ("make sure
    that we have generic code", the player, 2026-10-19); each miss is logged and the menu reopened. `picture`: picture
    the menu once a lift missed. `Abort` when none took."""
    name = NAMES.get(SERVING[0], 'the vendor')
    for tried, lift in enumerate(lifts):
        drawn = _open_menu(run, aspect)
        if picture and tried == 1:
            _picture(run, always=True)  # the first lift missed
        run.actuator.move(drawn[0], drawn[1] - lift, scatter=(6, 1))
        _note(run, aspect, f'the {line} line clicked {lift:.4f} over {name}')
        run.actuator.click()
        if took(lift):
            learned(SERVING[0], lift)
            return lift
        LOG.info('Macro: shop: menu line missed: %s, %s %.4f over the drawn point (try %d)', name, line, lift,
                 tried + 1)  # fmt: skip
        _close(run)
    raise Abort(f"{name}'s {line} line did not take at any line tried")


def _at_her_body(run: Run, aspect: float) -> None:
    """The pointer put at her body's middle (BODY), where she is drawn now. `Abort` out of sight."""
    world = run.world()
    her = _her(world)
    drawn = _drawn(world, (her.x, her.y), aspect) if her is not None else None
    if drawn is None:
        raise Abort(f'{VENDORS.get(SERVING[0], "the vendor")} is not in sight')
    run.actuator.move(drawn[0], drawn[1] - BODY, scatter=(3, 3))


def _labelled(run: Run, aspect: float) -> bool:
    """The pointer put on her (`_point_at_her`, else at her body); whether an item's label is what the game names under
    it with the labels shown and a key to hide them (LABELS_OFF_AT_NPC): the click then goes with them hidden."""
    if _point_at_her(run, aspect):
        return False
    under = run.reads.hovered()
    LOG.info('Macro: shop: the game names %s under the pointer, not %s', under, NAMES.get(SERVING[0], 'the vendor'))
    labelled = (
        LABELS_OFF_AT_NPC
        and under is not None
        and under[0] == ITEM_UNIT
        and run.show_items_key is not None
        and run.world().show_items is True
    )
    if not labelled:
        LOG.info('Macro: shop: clicked at her all the same')
        _at_her_body(run, aspect)
        _no_way_under(run)
    return labelled


def _no_way_under(run: Run) -> None:
    """WALK_OFF_WAYS: `Abort` with a way out of town (`ways_out`) under the pointer put at her body, before a click."""
    if not WALK_OFF_WAYS:
        return
    way = way_under(run, ways_out(run))
    if way is not None:
        raise Abort(f'{NAMES.get(SERVING[0], "the vendor")}: {way_name(way)} under the pointer at her: not clicked')


def _open_unlabelled(run: Run, aspect: float) -> World | None:
    """LABELS_OFF_AT_NPC: the aims and the click on her with the item labels hidden; her menu or None
    (`menu_or_stand`)."""
    with labels_hidden(run, f'shop: {NAMES.get(SERVING[0], "the vendor")}: an item label in the way'):
        if not _point_at_her(run, aspect):
            _at_her_body(run, aspect)
            _no_way_under(run)
        run.actuator.click()
        return menu_or_stand(run, 'npc_interact', MENU_SECONDS, WALKING)


def _open_menu(run: Run, aspect: float) -> tuple[float, float]:
    """Open her menu by a click on her; returns where she was drawn as it opened (the menu stays there while the view
    may still move). Vendors walk about ("they are moving", the player, 2026-10-16), so each aim is where she is drawn
    now; if the hover record never names her the click is made at her body anyway, and the menu opening tells it took
    (MENU_CLICKS tries)."""
    for _ in range(MENU_CLICKS):
        _note(run, aspect, 'before her menu')
        if 'npc_interact' in run.world().open_panels:
            # Opened mid-walk by a walk click on her: lines aimed later miss it, so close and reopen standing
            _close(run)
            run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
            continue
        if _labelled(run, aspect):
            opened = _open_unlabelled(run, aspect)
        else:
            run.actuator.click()
            # Her menu, or None once the character stands with none (targeting.MENU_STAND: not MENU_SECONDS of waiting)
            opened = menu_or_stand(run, 'npc_interact', MENU_SECONDS, WALKING)
        if opened is not None and opened.player is not None and opened.player.mode in WALKING:
            # Opened as the character still walked up: drawn elsewhere once it stands, by as far as the view moves;
            # kept when that is under half a line (targeting.MENU_KEEP_MID_WALK), else closed and opened again standing
            her = _her(opened)
            stood = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
            drift = None if her is None or stood is None else menu_drift(opened, stood, (her.x, her.y), aspect)
            if stood is not None and 'npc_interact' in stood.open_panels and keep_mid_walk(drift, LINE):
                _note(run, aspect, f'her menu opened mid-walk: kept, the view moved {drift:.4f} by the stand')
                _picture(run)
                return _drawn_now(run, aspect)
            _note(run, aspect, 'her menu opened mid-walk: opened again standing')
            _close(run)
            continue
        if opened is not None:
            _note(run, aspect, 'her menu open')
            _picture(run)
            return _drawn_now(run, aspect)
        _note(run, aspect, 'the click on her opened no menu')
        run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
    raise Abort('her menu did not open')
