"""The loop's items and surplus gold into the stash in Pandemonium Fortress (the KP_6 loop's last leg).

The player, 2026-10-17: "to effectively farm - we need to unload inventory into our stash". What goes: the cube's
items and the loop's in the inventory (cube.py `loot`), never the player's own, the tomes or the keys.

`unload`: the stash opened (teleport.py `use_thing`); cube items unpacked or sent by Ctrl + Shift + click from a
resource tab; resources by Ctrl + click onto their own tab's stack; other items onto the pages in PAGE_PRIORITY; each
move checked in memory. Click points are the game's `bankexpansionlayouthd.json` (read 2026-10-17), the stash being
the left panel. Design notes: history/stash.md.
"""

import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import BANK
from inventory_tracking.game.records import Carried, Pack, World
from inventory_tracking.items.metadata import metadata
from inventory_tracking.levels.model import Target

# The stash's page order and resource tabs are the loot storage layer's (loot/design.md §7 M3, 2026-10-20), which the
# stash stop's plan needs without this module's clicks; re-exported here for every importer
from inventory_tracking.loot.storage import (
    INVENTORY_CELLS,
    MATERIALS_TAB as MATERIALS_TAB,
    PAGE_PRIORITY,
    RESOURCES,
    SHARED_PRIORITY as SHARED_PRIORITY,
    is_potion as is_potion,
    resource_classes as resource_classes,
    resource_tabs,
)
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
    """The middle of the `tab`-th tab (0 Personal, 1 Shared, 2 Gems, 3 Materials, 4 Runes), left-panel layout units."""
    return 82 + tab * 195 + 195 / 2, 146 + 72 / 2


PERSONAL_TAB, SHARED_TAB, GEMS_TAB = tab_point(0), tab_point(1), tab_point(2)
# The shared pages' arrows: StashNavigation at (369, 1211), each arrow 64 x 64
SHARED_RIGHT = (369 + 327 + 32, 1211 + 13 + 32)
SHARED_LEFT = (369 + 29 + 32, 1211 + 13 + 32)
STASH_SEEN = (0.2, 0.8, 0.2, 0.75)  # window fractions the stash is walked to be drawn within
SHARED_PAGES = 5  # the shared pages ("Page 1 / 5")
TAB_SETTLE = 0.4


@dataclass
class Pages:
    """The last page that took an item, for the report. Each item starts at the first priority page again: a page
    passed over for a larger item may fit a smaller one."""

    first: int = PAGE_PRIORITY[0]


FORTRESS = 103
USUAL = (5019.0, 5040.0)  # the stash in Pandemonium Fortress, beside Deckard Cain
STASH_ABOVE = 0.5  # the share of the room the loop's items take over which the loop goes to the stash


def occupied(pack: Pack, own: frozenset[tuple[int, int, int]] = frozenset()) -> float:
    """The share of the room left by the player's own and the kept items (cube, tomes, keys) the loop's items take."""
    mine = loot(pack, own)
    cells = sum(item.size[0] * item.size[1] for item in mine)
    room = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items) + cells
    return cells / room if room > 0 else 1.0


def crowded(pack: Pack, own: frozenset[tuple[int, int, int]] = frozenset()) -> bool:
    """Whether the loop goes to the stash (the player, 2026-10-17: "maybe only when we have more than 50% occupied")."""
    return occupied(pack, own) > STASH_ABOVE


# The inventory's gold button (playerinventoryoriginallayouthd.json `gold_button` at (429, 1347) of the right panel):
# with the stash open it deposits, else it drops the gold on the ground
GOLD_BUTTON = (429 + 27, 1347 + 24)
GOLD_STAT = 14
BANK_STAT = 15  # itemstatcost.txt `goldbank`: logged with a refused deposit (which tab's gold it is: unverified)
# Gold goes to the tab shown, and a full one refuses it (2026-10-19 07:38): Personal is shown first. One refusal ends
# deposits until a restart
REFUSED: list[int] = []  # the carried gold when a deposit was refused
DIALOG_WAIT = 0.3  # for the gold dialog to show (no flag tells it)
DEPOSIT_SECONDS = 1.5  # for the carried gold to fall after Enter
DIGITS_HELD = 8  # erased first: the prefilled amount (at most 7 digits)
DEPOSIT_LEAST = 50_000  # a deposit smaller is not worth its seconds


def _carried_gold(run: Run, stat: int = GOLD_STAT) -> int | None:
    loot = run.reads.loot()
    return dict(loot.stats).get(stat) if loot is not None and loot.stats else None


def deposit(run: Run, rect, down_to: int) -> int:
    """Put the carried gold over `down_to` into the open stash (over the cap a sale drops it); the gold put in.

    The dialog sets no panel flag: waited for DIALOG_WAIT, prefill erased, amount typed, Enter, checked by the carried
    gold falling. The stash is checked open around the click: with no dialog the digits drink potions."""
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
    """A screenshot beside the runs (runs/alt-d/<what>-HHMMSS.png)."""
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
    """Empty the cube and the loop's inventory items into the stash; how many went. Mouse mode only. `Abort` with the
    panels closed when the stash does not open or a click takes an item up. `keep`: units that stay (waiting for
    Cain, junk.py's). `full`: resource kinds whose stack refused, grown here. `pages`: where the room was found."""
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
        # Only stackables go from the cube by Ctrl + Shift + click; the rest out to the inventory first (the player,
        # 2026-10-17)
        unpack(run, inventory_key, cubed_out)
        pack = carried() or pack
    rect = run.actuator.keys.focused_window_rect()

    def place(world: World) -> tuple[float, float] | None:
        shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id == BANK]
        if world.player is not None and not shown and world.player.area == FORTRESS:
            return USUAL  # out of sight: toward where it stands
        if world.player is None or not shown:
            return None
        here = (world.player.x, world.player.y)
        thing = min(shown, key=lambda t: math.dist((t.x, t.y), here))
        return thing.x, thing.y

    if rect is None or place(run.world()) is None:
        LOG.info("Macro: stash: no stash in sight: the loop's items stay where they are")
        return 0
    # Walked to until drawn well inside the window (from the waypoint no aim reaches it), then stood still: aims
    # while the view moves miss
    world = walk_until(run, place, STASH_SEEN, 'the stash')
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
        # The cube first, from a resource tab, which shows its grid
        shown_tab = None
        cubed = {item.unit_id for item in pack.in_cube}
        for item in pack.in_cube:
            if item.txt not in RESOURCES or item.unit_id in keep:
                continue  # stays: a Ctrl + Shift + click does not send it
            if shown_tab is None:
                # Any resource tab will do: the item goes onto its own tab (the player, 2026-10-18)
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
                left += 1  # its kind's stack refused earlier this visit: not tried again (~1.3 s each)
                continue
            # A resource goes onto its own tab whatever tab is shown (the player, 2026-10-18): that tab is shown only
            # after a refusal, which there means a full stack
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
                    # Its stack holds 99: a rune's then sold at Jamella, a gem's cubed (loop.py `sold_full`,
                    # cube.py `transmute`)
                    full.add(item.txt)
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
    """Walk to the stash and open it with the inventory, as `unload` does; the window's rect. `Abort` when not seen or
    not opened."""
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
    """The Shared tab at its `page`-th page: it reopens on the page last shown, so back to the first, then on."""
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
    pack = run.reads.carried()
    if pack is not None and pack.pointer is not None:
        run.actuator.move(*cell_point(rect, grid, (item.x, item.y), item.size), scatter=(4, 4))
        run.actuator.click()
        raise Abort(f'the {_name(item)} went onto the pointer, not into the stash')
    return True


def _potion(item: Carried) -> bool:
    """Whether the item is a potion: the belt's supply, never marked a full stack's kind."""
    base = metadata()['bases'].get(str(item.txt))
    return base is not None and str(base.get('type', '')).endswith('pot')


def _name(item: Carried) -> str:
    base = metadata()['bases'].get(str(item.txt))
    return base['name'] if base is not None else f'item {item.txt}'
