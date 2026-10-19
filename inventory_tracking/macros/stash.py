"""The loop's items into the stash at the end of every game that picked something up (the KP_6 loop's last leg).

The player, 2026-10-17: "probably we need to train how to put resources (stones/runes/gems) into stash: opened stash +
ctrl+ click on item - move it to stash; if we open any item where cube contents is visible (eg. gems tab) - we can
press ctrl + shift + item click - to move it from cube inventory directly into the stash"; later that night: "to
effectively farm - we need to unload inventory into our stash", every game with loot, into any free space (personal,
then the shared pages, among the player's own things). The cube holds 12 cells and was full by the ninth game of 23:39
on 2026-10-16.

What goes: everything in the cube (the loop's bag) and the loop's items in the inventory (cube.py `loot`: neither the
player's, as the loop's first look found them, nor the cube, the tomes and the keys).

The steps (`unload`), in Pandemonium Fortress before Save and Exit: the stash (objects.txt `Bank`, world.py BANK)
clicked as the waypoint is (teleport.py `use_thing`), which opens it with the inventory; a resource tab clicked once, on
which the stash shows the cube's grid, and each cube item sent by a Ctrl + Shift + click; then each inventory resource
(`RESOURCES`: the codes the resource tabs name, data/stash_tabs.json) by a Ctrl + click, which puts it onto its own
tab's stack whatever tab is shown (the player, 2026-10-18), its tab shown only after a refusal; then the
Personal tab and each other item by a Ctrl + click; on a page with no room for it the Shared tab, then its right
arrow, page after page (SHARED_PAGES at most); each move checked in memory (the item has left its grid, and is not on
the pointer); Escape. Where to click is the game's layout (`bankexpansionlayouthd.json`, read 2026-10-17): the stash
is the left panel, as the cube's; its tabs 195 x 72 from (82, 146), the cube's grid at (431, 784) on a resource tab,
the shared pages' arrows in StashNavigation at (369, 1211). The player's screenshot of 23:59 that day put the Gems tab
and the cube's cells where these say. Not yet seen in a game: where a cube item no resource tab takes goes on a
Ctrl + Shift + click, the shared pages' arrow.
"""

import functools
import json
import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.items.metadata import metadata
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import (
    INVENTORY,
    PANEL_SECONDS,
    REFERENCE_HEIGHT,
    _until,  # the one wait for the carried items (act.py `until`), as charms.py and visit.py import it from here
    cell_point,
    loot,
    unpack,
)
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.shop import WALK_SECONDS, WALKING, walk_until
from inventory_tracking.macros.teleport import use_thing
from inventory_tracking.macros.waypoint import panel_point
from inventory_tracking.macros.world import BANK, Carried, Pack, World
from inventory_tracking.native.layout import TILE_UNITS


__all__ = [
    'RESOURCES',
    'STASH_PAGE',
    'Pages',
    'close_stash',
    'crowded',
    'occupied',
    'open_stash',
    'resources',
    'unload',
]

STASH_CUBE = ((0.0, 0.397), (236, -651), (431, 784))  # the cube's grid on a resource tab, as cube.py's grids
# A page's 10 x 10 grid: `bankexpansionlayouthd.json` `basicstash_container` `grid` at (89, 219) (read 2026-10-18)
STASH_PAGE = ((0.0, 0.397), (236, -651), (89, 219))


def tab_point(tab: int) -> tuple[float, float]:
    """The middle of the stash's `tab`-th tab (0 Personal, 1 Shared, 2 Gems, 3 Materials, 4 Runes), in layout units
    of the left panel: the tab bar at (82, 146), each tab 195 x 72."""
    return 82 + tab * 195 + 195 / 2, 146 + 72 / 2


PERSONAL_TAB, SHARED_TAB, GEMS_TAB = tab_point(0), tab_point(1), tab_point(2)
# The shared pages' right arrow: StashNavigation at (369, 1211), the arrow 64 x 64 at (327, 13) in it
SHARED_RIGHT = (369 + 327 + 32, 1211 + 13 + 32)
SHARED_LEFT = (369 + 29 + 32, 1211 + 13 + 32)  # both where the player's screenshot of 01:46 on 2026-10-17 has them
STASH_SEEN = (0.2, 0.8, 0.2, 0.75)  # window fractions the stash is walked to be drawn within
SHARED_PAGES = 5  # the shared pages ("Page 1 / 5", the player's screenshot of 01:46 on 2026-10-17)
TAB_SETTLE = 0.4
# The player's stash priority, 2026-10-18: shared 3 > 4 > 5 > 2 > 1 > personal.
# Page 0 is personal; resource items still go to their dedicated tabs.
PAGE_PRIORITY = (3, 4, 5, 2, 1, 0)
SHARED_PRIORITY = PAGE_PRIORITY[:-1]


@dataclass
class Pages:
    """The last page that took an item, for the scan's report. Each item starts at the first priority page again:
    a page passed over for a larger item may still fit a smaller one, and the player can free room between visits."""

    first: int = PAGE_PRIORITY[0]


@functools.cache
def resource_classes() -> frozenset[int]:
    """The item classes the stash's resource tabs hold: their codes (data/stash_tabs.json) by the items' metadata."""
    tabs = json.loads((Path(__file__).parent / 'data' / 'stash_tabs.json').read_text())['tabs']
    codes = {code for names in tabs.values() for code in names}
    return frozenset(int(cid) for cid, base in metadata()['bases'].items() if base.get('code') in codes)


RESOURCES = resource_classes()


@functools.cache
def resource_tabs() -> dict[int, int]:
    """The stash tab (2 Gems, 3 Materials, 4 Runes) each resource class goes onto: a Tal Rune's Ctrl + click with the
    Gems tab shown left it in the inventory (01:28:46 on 2026-10-17)."""
    tabs = json.loads((Path(__file__).parent / 'data' / 'stash_tabs.json').read_text())['tabs']
    index = {'gems': 2, 'materials': 3, 'runes': 4}
    by_code = {code: index[name] for name, codes in tabs.items() for code in codes}
    return {int(cid): by_code[base['code']] for cid, base in metadata()['bases'].items() if base.get('code') in by_code}


FORTRESS = 103
USUAL = (5019.0, 5040.0)  # the stash in Pandemonium Fortress (the takes of 2026-10-17), beside Deckard Cain
STASH_ABOVE = 0.5  # the inventory's share of cells taken over which the loop goes to the stash
INVENTORY_CELLS = 10 * 4


def occupied(pack: Pack, own: frozenset[tuple[int, int, int]] = frozenset()) -> float:
    """The share of the inventory's room the loop's items take: the cells left by the player's own items (`own`, as
    cube.py `loot` tells them) and the kept ones (the cube, the tomes, the keys)."""
    mine = loot(pack, own)
    cells = sum(item.size[0] * item.size[1] for item in mine)
    room = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items) + cells
    return cells / room if room > 0 else 1.0


def crowded(pack: Pack, own: frozenset[tuple[int, int, int]] = frozenset()) -> bool:
    """Whether the loop goes to the stash: its items over STASH_ABOVE of the room the player's own leave (the player,
    2026-10-17: "proabably we don't need to visit stash every game, maybe only when we have more than 50% occupied";
    the player's own items take over half the inventory, so the whole inventory's share sent it every game)."""
    return occupied(pack, own) > STASH_ABOVE


# The inventory's gold button (playerinventoryoriginallayouthd.json `gold_button` at (429, 1347) of the right panel, the
# amount box from x 487): with the stash open it deposits, else it drops the gold on the ground; its dialog opens with
# all the carried gold typed in (the player, 2026-10-17)
GOLD_BUTTON = (429 + 27, 1347 + 24)
GOLD_STAT = 14
BANK_STAT = 15  # itemstatcost.txt `goldbank`: logged with a refused deposit (which tab's gold it is: unverified)
# The gold goes to the tab shown: at 07:38 on 2026-10-19 the Shared/Gems tab was, its gold at 12500000, and it refused
# 181494 twice a visit, ~3 s each (deposit-failed-073808.png, 075352.png); the deposit shows the Personal tab first.
# One refused all the same ends the deposits until the service restarts (REFUSED)
REFUSED: list[int] = []  # the carried gold when a deposit was refused
DIALOG_WAIT = 0.3  # for the gold dialog to show (no flag tells it)
DEPOSIT_SECONDS = 1.5  # for the carried gold to fall after Enter
DIGITS_HELD = 8  # erased first: the prefilled amount (at most 7 digits)
DEPOSIT_LEAST = 50_000  # a deposit smaller is not worth its seconds


def _carried_gold(run: Run, stat: int = GOLD_STAT) -> int | None:
    loot = run.loot() if run.loot is not None else None
    return dict(loot.stats).get(stat) if loot is not None and loot.stats else None


def deposit(run: Run, rect, down_to: int) -> int:
    """Put the carried gold over `down_to` into the stash, which is open (the player, 2026-10-17: "probably we need to
    move extra gold to our cube [stash]": over the cap a sale drops it on the ground); the gold put in, 0 with none.

    The dialog sets no panel flag the reads see: it is given DIALOG_WAIT, the prefilled amount erased and the amount
    typed, then Enter; checked by the carried gold falling by it, else Escape (with no dialog the digits would drink the
    belt's potions and Enter open the chat: the stash is checked open before the click and after)."""
    world = run.world()
    coins = _carried_gold(run)
    if coins is None or coins - down_to < DEPOSIT_LEAST or 'stash' not in world.open_panels:
        return 0
    if REFUSED:
        return 0
    amount = coins - down_to
    _tab(run, rect, PERSONAL_TAB)
    (anchor_x, anchor_y), (panel_x, panel_y), _ = INVENTORY
    scale = rect[3] / REFERENCE_HEIGHT
    at = (
        (anchor_x * rect[2] + (panel_x + GOLD_BUTTON[0]) * scale) / rect[2],
        (anchor_y * rect[3] + (panel_y + GOLD_BUTTON[1]) * scale) / rect[3],
    )
    if 'stash' not in run.world().open_panels:  # the same button drops the gold with the stash shut
        return 0
    run.actuator.move(*at, scatter=(3, 3))
    run.actuator.click()
    # The dialog sets no flag among the panels read (0x40 bytes): it showed, all the gold typed in, in the picture of
    # 16:02:26 on 2026-10-17 with none set; the click there opens it with the stash open, so its time is waited
    run.pace.sleep(DIALOG_WAIT)
    if 'stash' not in run.world().open_panels:
        return 0
    for _ in range(DIGITS_HELD):
        run.actuator.tap('BackSpace')
    for digit in str(amount):
        run.actuator.tap(digit)
    run.actuator.tap('Return')
    if run.seen(lambda _w: (_carried_gold(run) or coins) <= coins - amount + 1, DEPOSIT_SECONDS) is None:
        LOG.info('Macro: stash: %d gold to deposit, the carried gold still %s (stat 15: %s): no deposit again until '
                 'a restart', amount, _carried_gold(run), _carried_gold(run, BANK_STAT))  # fmt: skip
        REFUSED.append(coins)
        _picture('deposit-failed')
        run.actuator.tap('Escape')  # the dialog, or the chat a Return opened with none: closed
        run.pause('key')
        return 0
    LOG.info('Macro: stash: %d gold deposited, %s carried', amount, _carried_gold(run))
    return amount


def _picture(what: str) -> None:
    """A screenshot beside the runs (runs/alt-d/<what>-HHMMSS.png), as the shop pictures a vendor's menu."""
    path = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d' / f'{what}-{time.strftime("%H%M%S")}.png'
    try:
        subprocess.run(['grim', str(path)], timeout=3, check=True, capture_output=True)
        LOG.info('Macro: stash: pictured: %s', path)
    except (OSError, subprocess.SubprocessError) as error:
        LOG.info('Macro: stash: not pictured: %s', error)


def resources(pack: Pack, own: frozenset[tuple[int, int, int]]) -> tuple[list[Carried], list[Carried]]:
    """The resources to put in the stash: the loop's in the inventory, and all in the cube."""
    return (
        [item for item in loot(pack, own) if item.txt in RESOURCES],
        [item for item in pack.in_cube if item.txt in RESOURCES],
    )


def unload(
    run: Run,
    own: frozenset[tuple[int, int, int]],
    inventory_key: str | None = None,
    full: set[int] | None = None,
    keep: frozenset[int] = frozenset(),
    gold_to: int | None = None,
    pages: Pages | None = None,
) -> int:
    """Empty the cube and the loop's items in the inventory into the stash (the module text); how many went. Mouse
    mode only. `Abort` with the panels closed when the stash does not open or a click takes an item up instead.
    `keep`: the units that stay where they are (the loop's items waiting for Cain, and its junk: macros/junk.py).
    `pages`: where to start among the pages, and where the room was found (`Pages`)."""
    if run.pad is not None:
        raise Abort('the stash needs mouse mode')
    carried = run.carried
    pack = carried() if carried is not None else None
    if carried is None or pack is None:
        return 0
    cubed_out = [item for item in pack.in_cube if item.unit_id not in keep]
    if not cubed_out and not [item for item in loot(pack, own) if item.unit_id not in keep] and gold_to is None:
        LOG.info("Macro: stash: nothing of the loop's to put in")
        return 0
    if cubed_out and inventory_key is not None:
        # The cube's items come out into the inventory first (cube.py `unpack`), then go with the inventory's: the
        # player, 2026-10-17: "you can move only stackable items/materials/gems runes with shift-ctrl click on cubed
        # item; to move items to other spaces - you need to move them to inventory (ctrl+click) and then move back to
        # stash tab (ctrl-click)"; a Tal Rune stayed in the cube on a Ctrl + Shift + click too (01:31:48)
        unpack(run, inventory_key, cubed_out)
        pack = carried() or pack
    rect = run.actuator.keys.focused_window_rect()

    def place(world: World) -> tuple[float, float] | None:
        shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id == BANK]
        if world.player is not None and not shown and world.player.area == FORTRESS:
            return USUAL  # out of sight (from Jamella's place, 12:13:16 on 2026-10-17): toward where it stands
        if world.player is None or not shown:
            return None
        here = (world.player.x, world.player.y)
        thing = min(shown, key=lambda t: math.dist((t.x, t.y), here))
        return thing.x, thing.y

    if rect is None or place(run.world()) is None:
        LOG.info("Macro: stash: no stash in sight: the loop's items stay where they are")
        return 0
    # Walked to until drawn well inside the window: from the waypoint it is 33 units off, out of view, and no aim
    # at it was clicked (01:07:41 on 2026-10-17, "the stash is not under the pointer at any aim")
    world = walk_until(run, place, STASH_SEEN, 'the stash')
    # Stood still before the aims: clicked while the walk still moved the view, no aim had it under the pointer, from 3
    # units off too (01:28:48 and 01:35:40 on 2026-10-17)
    world = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS) or run.world()
    player = world.player
    shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id == BANK]
    if player is None or not shown:
        raise Abort('the stash is not in sight')
    thing = min(shown, key=lambda t: math.dist((t.x, t.y), (player.x, player.y)))
    mark = Target(player.area, (), (thing.x / TILE_UNITS, thing.y / TILE_UNITS), 'the stash', 'stash', use=BANK)
    moved, stuffed, left = 0, False, 0
    try:
        use_thing(run, mark, player, thing, rect[2] / rect[3])
        if run.seen(lambda w: {'stash', 'inventory'} <= set(w.open_panels), PANEL_SECONDS) is None:
            raise Abort('the stash did not open with the inventory')
        run.actuator.rebase()
        # The cube first, from a resource tab, where the stash shows its grid: a Ctrl + Shift + click sends a cube
        # item into the stash (the player, 2026-10-17); one the stash has no tab for may land in the inventory, which
        # the next steps empty
        shown_tab = None
        cubed = {item.unit_id for item in pack.in_cube}
        for item in pack.in_cube:
            if item.txt not in RESOURCES or item.unit_id in keep:
                continue  # stays: a Ctrl + Shift + click does not send it (01:28:34 on 2026-10-17)
            if shown_tab is None:
                # Any resource tab shows the cube's grid, and the item goes onto its own tab by itself (the player,
                # 2026-10-18: "you don't need to open appropriate tab. these items automatically gets to correct tab")
                shown_tab = resource_tabs()[item.txt]
                _tab(run, rect, tab_point(shown_tab))
            run.actuator.move(*cell_point(rect, STASH_CUBE, (item.x, item.y), item.size), scatter=(6, 6))
            run.actuator.click('Control_L', 'Shift_L')
            if _sent(run, rect, item, STASH_CUBE, lambda p, i=item: i.unit_id not in p.cube_items):
                moved += 1
            else:
                left += 1
                LOG.info("Macro: stash: the cube's %s at (%d, %d) did not leave it", _name(item), item.x, item.y)
        pack = carried() or pack
        held = [item for item in loot(pack, own) if item.unit_id not in keep]
        spilled = [item for item in held if item.unit_id in cubed]
        moved -= len(spilled)  # out of the cube into the inventory: counted where it goes next
        if spilled:
            LOG.info("Macro: stash: %d of the cube's items came to the inventory", len(spilled))
        # Resources by Ctrl + click onto their tabs' stacks, then keepers onto pages in PAGE_PRIORITY.
        if full:
            kept = [item for item in held if item.txt in full]
            if kept:
                LOG.info('Macro: stash: %d items of full stacks stay for Jamella', len(kept))
            held = [item for item in held if item.txt not in full]
        ordered = [item for item in held if item.txt in RESOURCES] + [
            item for item in held if item.txt not in RESOURCES
        ]
        pages = pages if pages is not None else Pages()
        shown_page: int | None = None

        def show_page(page: int) -> None:
            nonlocal shown_page
            if page == shown_page:
                return
            if page == 0:
                _tab(run, rect, PERSONAL_TAB)
            elif shown_page is None or shown_page == 0:
                _shared(run, rect, page)
            else:
                steps = page - shown_page
                arrow = SHARED_RIGHT if steps > 0 else SHARED_LEFT
                for _ in range(abs(steps)):
                    run.actuator.move(*panel_point(rect, *arrow), scatter=(8, 8))
                    run.actuator.click()
                    run.pace.sleep(TAB_SETTLE)
            shown_page = page

        for item in ordered:
            page = PAGE_PRIORITY[0]
            if full is not None and item.txt in full and not _potion(item):
                # Its kind refused earlier this visit: the stack is full, the rest of the kind is not tried (seven
                # flawless gems of four full stacks, ~1.3 s each, at 06:08:50-55 on 2026-10-18)
                left += 1
                continue
            # A resource goes onto its own tab whatever tab is shown (the player, 2026-10-18): its tab is shown only
            # after a refusal, which on its own tab is a full stack. The refusal that once had every tab shown first, a
            # Tal Rune at 01:28:46 on 2026-10-17, was the Tal Runes' full stack
            if item.txt not in RESOURCES:
                show_page(page)
            while True:
                run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(6, 6))
                run.actuator.click('Control_L')
                if _sent(run, rect, item, INVENTORY, lambda p, i=item: all(c.unit_id != i.unit_id for c in p.items)):
                    moved += 1
                    if item.txt not in RESOURCES:
                        pages.first = page
                    break
                if item.txt in RESOURCES and shown_tab != resource_tabs()[item.txt]:
                    shown_tab = resource_tabs()[item.txt]
                    LOG.info('Macro: stash: the %s did not go: its own tab shown, and again', _name(item))
                    _tab(run, rect, tab_point(shown_tab))
                    shown_page = None
                    continue
                if item.txt in RESOURCES and full is not None and not _potion(item):
                    full.add(item.txt)  # its tab shown and refused: the stack holds 99 (the Tal Runes, 2026-10-17)
                    # a rune's then sold at Jamella; a gem's kept and cubed into perfect ones (macros/loop.py
                    # `sold_full`, macros/cube.py `transmute`)
                    LOG.info('Macro: stash: the %s stack is full', _name(item))
                if item.txt in RESOURCES or page == PAGE_PRIORITY[-1]:
                    left += 1
                    stuffed = stuffed or item.txt not in RESOURCES
                    LOG.info('Macro: stash: no room for the %s at (%d, %d)', _name(item), item.x, item.y)
                    break
                previous = page
                page = PAGE_PRIORITY[PAGE_PRIORITY.index(page) + 1]
                LOG.info('Macro: stash: page %d is full: next priority page %d', previous, page)
                show_page(page)
        if gold_to is not None:
            deposit(run, rect, gold_to)
    finally:
        if {'stash', 'inventory', 'cube'} & set(run.world().open_panels):
            run.actuator.tap('Escape')  # with nothing open it opens the game's menu instead
            run.seen(lambda w: not {'stash', 'inventory', 'cube'} & set(w.open_panels), PANEL_SECONDS)
            run.actuator.rebase()
        LOG.info('Macro: stash: %d items put in, %d left%s', moved, left, ': the stash is full' if stuffed else '')
    run.say(f'Stash: {moved} item{"s" if moved != 1 else ""} put in' + (f', {left} left' if left else ''))
    return moved


def open_stash(run: Run) -> tuple[int, int, int, int]:
    """Walk to the stash in sight (or the Fortress's own place) and open it with the inventory, as `unload` does; the
    window's rect. `Abort` with none in sight or when it does not open."""
    if run.pad is not None:
        raise Abort('the stash needs mouse mode')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')

    def place(world: World) -> tuple[float, float] | None:
        shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id == BANK]
        if world.player is not None and not shown and world.player.area == FORTRESS:
            return USUAL
        if world.player is None or not shown:
            return None
        here = (world.player.x, world.player.y)
        thing = min(shown, key=lambda t: math.dist((t.x, t.y), here))
        return thing.x, thing.y

    if place(run.world()) is None:
        raise Abort('no stash in sight')
    walk_until(run, place, STASH_SEEN, 'the stash')
    world = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS) or run.world()
    player = world.player
    shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id == BANK]
    if player is None or not shown:
        raise Abort('the stash is not in sight')
    thing = min(shown, key=lambda t: math.dist((t.x, t.y), (player.x, player.y)))
    mark = Target(player.area, (), (thing.x / TILE_UNITS, thing.y / TILE_UNITS), 'the stash', 'stash', use=BANK)
    use_thing(run, mark, player, thing, rect[2] / rect[3])
    if run.seen(lambda w: {'stash', 'inventory'} <= set(w.open_panels), PANEL_SECONDS) is None:
        raise Abort('the stash did not open with the inventory')
    run.actuator.rebase()
    return rect


def close_stash(run: Run) -> None:
    """Escape out of the stash's panels, if open."""
    if {'stash', 'inventory', 'cube'} & set(run.world().open_panels):
        run.actuator.tap('Escape')
        run.seen(lambda w: not {'stash', 'inventory', 'cube'} & set(w.open_panels), PANEL_SECONDS)
        run.actuator.rebase()


def _shared(run: Run, rect, page: int) -> None:
    """The Shared tab at its `page`-th page: the tab shows the page last looked at, so back to the first, then on."""
    _tab(run, rect, SHARED_TAB)
    for _ in range(SHARED_PAGES - 1):
        run.actuator.move(*panel_point(rect, *SHARED_LEFT), scatter=(8, 8))
        run.actuator.click()
        run.pace.sleep(TAB_SETTLE / 2)
    for _ in range(page - 1):
        run.actuator.move(*panel_point(rect, *SHARED_RIGHT), scatter=(8, 8))
        run.actuator.click()
        run.pace.sleep(TAB_SETTLE)


def _tab(run: Run, rect, tab: tuple[float, float]) -> None:
    """Show the stash's `tab` (layout units in the left panel)."""
    run.actuator.move(*panel_point(rect, *tab), scatter=(15, 5))
    run.actuator.click()
    run.pace.sleep(TAB_SETTLE)


def _sent(run: Run, rect, item: Carried, grid, gone) -> bool:
    """Whether the click sent `item` away (`gone` came to hold); `Abort` when it took the item onto the pointer
    instead, after putting it back where it was."""
    if not _until(run, gone):
        return False
    pack = run.carried() if run.carried is not None else None
    if pack is not None and pack.pointer is not None:
        run.actuator.move(*cell_point(rect, grid, (item.x, item.y), item.size), scatter=(4, 4))
        run.actuator.click()
        raise Abort(f'the {_name(item)} went onto the pointer, not into the stash')
    return True


MATERIALS_TAB = 3  # `resource_tabs`: the essences, shards, keys and the rest


def is_potion(txt: int) -> bool:
    """Whether the class is a potion's (misc.txt types `rpot`, `hpot`, ...)."""
    base = metadata()['bases'].get(str(txt))
    return base is not None and str(base.get('type', '')).endswith('pot')


def _potion(item: Carried) -> bool:
    """Whether the item is a potion (misc.txt types `rpot`, `hpot`, ...): the belt's supply, never a full stack's kind
    not picked up or sold (a Full Rejuvenation Potion was marked so at 03:35:18 on 2026-10-17)."""
    base = metadata()['bases'].get(str(item.txt))
    return base is not None and str(base.get('type', '')).endswith('pot')


def _name(item: Carried) -> str:
    base = metadata()['bases'].get(str(item.txt))
    return base['name'] if base is not None else f'item {item.txt}'
