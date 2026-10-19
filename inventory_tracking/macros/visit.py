"""The town visit's executor (macros/town-plan.md §2.1): `visit` walks the itinerary once (step 3), the stash stop by
plan (`stash_stop`, step 2) its second stop.

`visit`, the loop's one TOWN leg (the player, 2026-10-18 12:55: "identify everything with cain; move to the shared
stash; put all items that we need to keep in stash ... after stash visit we should carry only junk/sell items in our
inventory or cube; visit store and sell junk items from inventory and cube; refill the consumables; if we need to repair
things - repair things; go to waypoint; continue activity"): Deckard Cain for every unidentified item, inventory and
cube (none: no walk to him); the appraisal's junk told (`Hands.judge`, the full gem stacks' surplus); one stash stop,
planned from the stash as read, the cube's keepers and its junk out in it; the full gem stacks' transmutes standing
there, the stop planned again for the perfect gems (no walk); Jamella, the inventory's and the cube's junk sold and the
keys bought to the run kind's (`Needs.keys`), skipped with nothing to sell and nothing short; Halbu only when a repair
is due, after her (before her only when the gold is still too near its cap for a sale: no sale is made then); a key
stack moved out of the build's free block; the exit: the waypoint walked to from her or him (`Exit.WAYPOINT`,
`Exit.PORTAL`: the next leg takes the waypoint), no walk when the game is left from here (`Exit.LEAVE`). Then the
contract (town.py `contract`), logged with each stop's seconds. Every stop is planned from memory read at it: a visit
cut by the player's hand and made again does only what is left.

`stash_stop` makes a stop `town.stash_stop` planned from the stash as read (world.py `StashView`): one walk to the
stash, each put clicked once, onto the page planned and no other. The steps: the cube's keepers that fit the inventory
now come out first (cube.py `unpack`), with the cube's junk for Jamella when no keeper waits for room; the stash opened
(stash.py `open_stash`); the cube's resources by Ctrl + Shift on a resource tab, the inventory's by Ctrl + click (each
onto its own tab whatever tab is shown: the player, 2026-10-18); the keepers onto their pages, the Personal tab, then
the Shared tab at its first planned page (stash.py `_shared`), its right arrow to each next one; the full stacks'
materials put down between the panels; the gold deposited; Escape.

A cube keeper the inventory had no room for before the stash took its keepers goes through the room they left: whether a
Ctrl + click on a cube item in the stash's resource view sends it to the inventory is not known (the plan's probe P1),
so the stash is closed, the cube's items taken out (`unpack`), and the stash opened again where the character stands
(no walk), then those keepers put in. Where the inventory's junk or keys hold the only block such a keeper fits, they
are moved aside first, the stash still open (`_aside`), and junk with no cell left goes into the cube for Jamella
(`_into_cube`) before the keepers come out (town.py `stash_stop` (iv); 14:28 on 2026-10-18). Where no move frees
one, the inventory's junk in the way is parked on a shared page with the stash still open (`_park`), and taken back
into the inventory once the keepers are in, before the stash closes (`_unpark`): sold at Jamella after (the player,
16:50 on 2026-10-18: "junk can be temporarily stored in stash, but sold after"; town.py PARK_JUNK).

Each put is checked: the item left the grid (stash.py `_sent`: one taken onto the pointer is put back and the stop
aborts), and the stash read again shows the page it landed on. The Shared tab shows the page last looked at, kept
between stops (`Remembered`): a stop goes to it with no arrow when it is the page planned. A put refused there is tried
again from the tab's first page; one that lands on another page is in the stash all the same, and that page is the one
shown for the next puts (§5). A put still refused goes to today's scan (`stash.unload`) for that item only, with the
stash closed first.
"""

from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from inventory_tracking.common import LOG
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros import townplan, visitlog
from inventory_tracking.macros.act import until
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cain import CAIN
from inventory_tracking.macros.cube import (
    CUBE_CLASS,
    GEMS_A_TRANSMUTE,
    INVENTORY,
    PANEL_SECONDS,
    PARK_POINT,
    TRANSMUTE_SECONDS,
    arrange_keys,
    cell_point,
    drop_item,
    keys_move,
    loot,
    open_inventory,
    perfect_of,
    rune_slot,
    stash_transmute,
    unpack,
)
from inventory_tracking.macros.engine import Run, protected
from inventory_tracking.macros.junk import MAGIC
from inventory_tracking.macros.repair import (
    HALBU,
    RETRY_GAMES,
    WAYPOINT_SEEN,
    affordable,
    due,
    expected,
    gold,
    repair,
)
from inventory_tracking.macros.shop import JAMELLA, SALE_MOST, _waypoint, gold_cap, restock, short, walk_until
from inventory_tracking.macros.stash import (
    FORTRESS,
    PAGE_PRIORITY,
    PERSONAL_TAB,
    SHARED_LEFT,
    SHARED_RIGHT,
    SHARED_TAB,
    STASH_CUBE,
    STASH_PAGE,
    TAB_SETTLE,
    USUAL,
    Pages,
    _name,
    _sent,
    _shared,
    _tab,
    _until,
    close_stash,
    deposit,
    is_potion,
    open_stash,
    tab_point,
    unload,
)
from inventory_tracking.macros.town import (
    BER,
    KEEPER_IN_CUBE,
    PARK_JUNK,
    RUNES_A_TAKE,
    RUNES_AIM,
    RUNES_TAB,
    Cell,
    Contract,
    Exit,
    Holdings,
    Needs,
    Put,
    StashStop,
    contract,
    deposit_to,
    named,
    out_now,
    sold_full,
    stash_stop as plan_stop,
    surplus,
    tops_up,
    uncubed,
    unread_way_for_cube,
)
from inventory_tracking.macros.travel import cut
from inventory_tracking.macros.visitlog import Recorder, Snapshot
from inventory_tracking.macros.waypoint import panel_point
from inventory_tracking.macros.world import Carried, Pack, StashView


__all__ = ['FORTRESS_MAP', 'Hands', 'Remembered', 'TownMap', 'Visited', 'note_view', 'stash_stop', 'visit']

Rect = tuple[int, int, int, int]


@dataclass
class Remembered:
    """What the runner keeps between stops: the game whose stash view was logged (`note_view`), and the shared page the
    Shared tab showed last (the tab shows the page last looked at: stash.py `_shared`), None not known (a restart)."""

    game: str | None = None
    shared: int | None = None


def note_view(run: Run, noted: Remembered) -> None:
    """Log the stash as read, once a game in Pandemonium Fortress (the plan's step 0: `Macro: stash view: pages free
    0:n 1:n …; full stacks …`), to measure the view against what the stash stop finds."""
    if run.stash_view is None:
        return
    world = run.world()
    if not world.in_game or world.player is None or world.player.area != FORTRESS or noted.game == world.game_name:
        return
    noted.game = world.game_name
    view = run.stash_view()
    LOG.info('Macro: stash view: %s', view.said() if view is not None else 'unread')


RESOURCE_TAB = -1  # `Tally.shown`: a resource tab, the cube's grid with it
GEMS_INDEX = 2  # the Gems tab (stash.py `resource_tabs`: 2 Gems, 3 Materials, 4 Runes)


@dataclass
class Tally:
    """What a stop has done so far: the items put in, those left for the scan, the tab or page shown."""

    memory: Remembered
    moved: int = 0
    missed: list[Carried] = field(default_factory=list)
    shown: int | None = None  # 0 personal, 1..5 a shared page, RESOURCE_TAB; None: not known (just opened)
    guessed: bool = False  # the shared page shown is the one remembered, not yet seen to take an item

    def miss(self, item: Carried) -> None:
        if all(i.unit_id != item.unit_id for i in self.missed):
            self.missed.append(item)


def stash_stop(
    run: Run, stop: StashStop, *, inventory_key: str | None, own: frozenset[Cell], memory: Remembered | None = None
) -> int:
    """Make the planned stash stop (the module text); how many items went into the stash. Mouse mode only. `Abort`
    with the panels closed when the stash does not open or a click takes an item onto the pointer."""
    if run.pad is not None:
        raise Abort('the stash needs mouse mode')
    pack = run.reads.carried()
    if pack is None or stop.idle:
        LOG.info("Macro: stash: by the view: nothing of the loop's to put in")
        return 0
    began = run.clock()
    # In `unpack`'s order, the tallest first: in the puts' order (by page) a Ring for page 2 took the first cell of the
    # only 2 x 3 a Serpentskin Armor for page 5 came out into, and the armor waited for a second opening (the 15:14
    # replay on 2026-10-18), where `unpack` would have taken both out at once
    cube_keepers = sorted(
        (put.item for put in stop.puts if put.source == 'cube' and not put.tab),
        key=lambda i: (-i.size[1], -i.size[0] * i.size[1]),
    )
    if inventory_key is None:
        cube_keepers = []  # no key opens the inventory: the cube's keepers stay
    first = out_now(pack.inventory, cube_keepers)
    later = [item for item in cube_keepers if item not in first]
    sale = list(stop.out_for_sale) if inventory_key is not None else []
    out = first if later else out_now(pack.inventory, [*first, *sale])
    if out and inventory_key is not None:
        unpack(run, inventory_key, out)  # before the stash: what the room takes now
    tally, openings, dropped = Tally(memory if memory is not None else Remembered()), 1, 0
    parked: list[tuple[Carried, int]] = []  # the junk on a page for the stop, not yet taken back
    rect = open_stash(run)
    try:
        _tabs(run, rect, [put for put in stop.puts if put.tab], tally)
        through = {item.unit_id for item in first}
        ready = [p for p in stop.puts if not p.tab and (p.source == 'inventory' or p.item.unit_id in through)]
        _pages(run, rect, ready, tally)
        dropped = _drops(run, rect, stop.drops)
        if later and inventory_key is not None:
            # The inventory's keepers have made the room: the cube's out through it, the stash opened again in place
            # (probe P1 unknown: whether a Ctrl + click on a cube item in the stash's resource view takes it out). The
            # junk and keys in the way moved aside first, with the stash still open (no opening more); junk with no
            # cell for it into the cube, which the stash's panels hide (14:28 on 2026-10-18: a set Amulet kept for
            # Jamella held the one 2 x 3 a unique Embossed Plate needed, and the plate stayed in the cube); junk no
            # move makes room for parked on a page first, taken back once the keepers are in (16:35: a junk Fuscina
            # held the only 2 x 2 a set Battle Boots could come out into, three visits)
            _park(run, rect, stop.parks, tally, later, parked)
            _aside(run, rect, stop.shuffles, later)
            close_stash(run)
            if stop.into_cube:
                _into_cube(run, inventory_key, stop.into_cube, later)
            unpack(run, inventory_key, [*later, *sale])
            rect = open_stash(run)
            openings += 1
            tally.shown = None
            ids = {item.unit_id for item in later}
            _pages(run, rect, [put for put in stop.puts if put.item.unit_id in ids], tally)
            parked = _unpark(run, rect, parked, tally)
        if stop.runes:
            # The 99 rune stacks down to RUNES_AIM (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower"), the
            # cube empty now and the stash open: no walk, no opening more
            _cube_runes(run, rect, stop, tally)
        if stop.deposit_to is not None:
            deposit(run, rect, stop.deposit_to)
    except Abort as error:
        if parked and not cut(run, error):
            parked = _rescue(run, parked, tally)  # never junk left in the stash: taken back before the stop gives up
        raise
    finally:
        close_stash(run)
        if parked:
            LOG.warning('Macro: stash: %d junk left parked in the stash: %s', len(parked),
                        ', '.join(f'{_name(item)} on page {page}' for item, page in parked))  # fmt: skip
    LOG.info('Macro: stash: by the view: %d items put in (pages %s), %d dropped, %d left for the scan, %d openings, '
             '%.1fs', tally.moved, ','.join(map(str, stop.pages())) or '-', dropped, len(tally.missed), openings,
             run.clock() - began)  # fmt: skip
    if tally.missed:
        tally.moved += _scan(run, tally.missed, inventory_key, own)
    run.say(f'Stash: {tally.moved} item{"s" if tally.moved != 1 else ""} put in')
    return tally.moved


def _now(run: Run, unit_id: int) -> tuple[Carried | None, bool]:
    """The unit's item in the inventory as read now (None: not there), and whether the unit is in the cube."""
    pack = run.reads.carried()
    if pack is None:
        return None, False
    return next((i for i in pack.items if i.unit_id == unit_id), None), unit_id in pack.cube_items


def _gone(item: Carried):
    return lambda p: all(c.unit_id != item.unit_id for c in p.items)


def _tabs(run: Run, rect: Rect, puts: Sequence[Put], tally: Tally) -> None:
    """The resources onto their tabs: the cube's by Ctrl + Shift with a resource tab shown (the cube's grid there),
    then the inventory's by Ctrl + click, each onto its own tab whatever tab is shown."""
    for put in sorted(puts, key=lambda p: p.source != 'cube'):
        held, in_cube = _now(run, put.item.unit_id)
        if put.source == 'cube':
            if not in_cube:
                continue
            if tally.shown != RESOURCE_TAB:
                _tab(run, rect, tab_point(-put.to))
                tally.shown = RESOURCE_TAB
            item = put.item
            run.actuator.move(*cell_point(rect, STASH_CUBE, (item.x, item.y), item.size), scatter=(6, 6))
            run.actuator.click('Control_L', 'Shift_L')
            if _sent(run, rect, item, STASH_CUBE, lambda p, i=item: i.unit_id not in p.cube_items):
                tally.moved += 1
            else:
                LOG.info("Macro: stash: the cube's %s did not go onto its tab", _name(item))
                tally.miss(item)
        elif held is not None:
            run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            if _sent(run, rect, held, INVENTORY, _gone(held)):
                tally.moved += 1
            else:
                LOG.info('Macro: stash: the %s did not go onto its tab', _name(held))
                tally.miss(held)


def _arrows(run: Run, rect: Rect, steps: int) -> None:
    """The shared pages' right arrow `steps` times, the left one for negative steps."""
    for _ in range(abs(steps)):
        run.actuator.move(*panel_point(rect, *(SHARED_RIGHT if steps > 0 else SHARED_LEFT)), scatter=(8, 8))
        run.actuator.click()
        run.pace.sleep(TAB_SETTLE)


def _show(run: Run, rect: Rect, page: int, tally: Tally) -> None:
    """Show `page`: the Personal tab; a shared page by the arrows from the shared page shown, or the Shared tab and the
    arrows from the page it showed last (remembered: from page 5 to page 5 no arrow), else from its first page
    (stash.py `_shared`: the left arrow to the first, then the right one)."""
    if tally.shown == page:
        return
    if page == 0:
        _tab(run, rect, PERSONAL_TAB)
    elif tally.shown is not None and tally.shown >= 1:
        _arrows(run, rect, page - tally.shown)
    elif tally.memory.shared is not None:
        _tab(run, rect, SHARED_TAB)
        _arrows(run, rect, page - tally.memory.shared)
        tally.guessed = True
    else:
        _shared(run, rect, page)
    tally.shown = page
    if page >= 1:
        tally.memory.shared = page


def _pages(run: Run, rect: Rect, puts: Sequence[Put], tally: Tally) -> None:
    """The keepers onto their planned pages in priority order, each by a Ctrl + click with its page shown; each checked
    on the page by the stash read again. One refused on a page told by memory is tried again from the Shared tab's
    first page;
    refused there too, it goes to the scan. One that lands on another page is in the stash all the same: that page is
    the one shown (learned for the next puts: §5)."""
    for put in sorted(puts, key=lambda p: PAGE_PRIORITY.index(p.to)):
        held, _in_cube = _now(run, put.item.unit_id)
        if held is None:
            continue  # not in the inventory (a cube keeper that did not come out): it stays
        _show(run, rect, put.to, tally)
        sent = False
        for _ in range(2):
            run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            sent = _sent(run, rect, held, INVENTORY, _gone(held))
            if sent or not tally.guessed or put.to == 0:
                break
            LOG.info('Macro: stash: page %d (remembered) refused the %s: the Shared tab from its first page', put.to,
                     _name(held))  # fmt: skip
            tally.guessed = False
            _shared(run, rect, put.to)
        if not sent:
            LOG.info('Macro: stash: page %d refused the %s at (%d, %d): the scan for it', put.to, _name(held), held.x,
                     held.y)  # fmt: skip
            tally.miss(held)
            continue
        tally.moved += 1
        tally.guessed = False
        view = run.reads.stash_view()
        landed = view.page_of(held.unit_id) if view is not None else None
        if landed is not None and landed != put.to:
            LOG.warning('Macro: stash: the %s went onto page %d, planned %d: page %d is the one shown', _name(held),
                        landed, put.to, landed)  # fmt: skip
            tally.shown = landed
            if landed >= 1:
                tally.memory.shared = landed


def _keepers(items: Sequence[Carried]) -> str:
    return ', '.join(_name(i) for i in items)


def _aside(run: Run, rect: Rect, moves: Sequence[tuple[Carried, tuple[int, int]]], later: Sequence[Carried]) -> int:
    """The planned moves aside within the inventory (`StashStop.shuffles`), the stash open: each item taken up by a
    click and put down by a click on its new cell, checked in memory (as cube.py `arrange_keys` moves a key stack, 14
    times live by 2026-10-18); put back where it was if it does not land there, `Abort` if it stays on the pointer.
    How many moved."""
    moved = 0
    for item, (x, y) in moves:
        held, _in_cube = _now(run, item.unit_id)
        if held is None or (held.x, held.y) == (x, y):
            continue
        run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(4, 4))
        run.actuator.click()
        if not _until(run, lambda p, i=held: p.pointer == i.unit_id):
            pack = run.reads.carried()
            if pack is not None and pack.pointer is not None:
                run.actuator.click()  # something else taken up: put down where it was, the pointer not moved
                _until(run, lambda p: p.pointer is None)
            LOG.info('Macro: stash: the %s at (%d, %d) was not taken up to move aside', _name(held), held.x, held.y)
            continue
        landed = None
        for at in ((x, y), (held.x, held.y)):  # its new cell, else back where it was
            run.actuator.move(*cell_point(rect, INVENTORY, at, held.size), scatter=(4, 4))
            run.actuator.click()
            if _until(run, lambda p, a=at, i=held: p.pointer is None and any(
                c.unit_id == i.unit_id and (c.x, c.y) == a for c in p.items
            )):  # fmt: skip
                landed = at
                break
        if landed is None:
            raise Abort(f'the {_name(held)} is still on the pointer')
        moved += landed == (x, y)
        LOG.info('Macro: stash: the %s %s (%d, %d) to (%d, %d): room for the cube\'s %s', _name(held),
                 'moved aside' if landed == (x, y) else 'not moved', held.x, held.y, x, y, _keepers(later))  # fmt: skip
    return moved


def _park(
    run: Run,
    rect: Rect,
    parks: Sequence[Put],
    tally: Tally,
    later: Sequence[Carried],
    parked: list[tuple[Carried, int]],
) -> None:
    """The inventory's junk planned onto a shared page for the stop (`StashStop.parks`), the stash open: each by a
    Ctrl + click with its page shown, as a keeper is put (`_pages`), checked to have left the grid; the page it lies on
    as read again. Never into the scan: one refused stays carried (the keeper it made room for then stays in the cube).
    Each one parked added to `parked` with its page at once (a stop that gives up after takes it back)."""
    for put in parks:
        held, _in_cube = _now(run, put.item.unit_id)
        if held is None:
            continue
        _show(run, rect, put.to, tally)
        sent = False
        for _ in range(2):
            run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            sent = _sent(run, rect, held, INVENTORY, _gone(held))
            if sent or not tally.guessed:
                break
            tally.guessed = False
            _shared(run, rect, put.to)
        if not sent:
            LOG.info('Macro: stash: page %d refused the %s to park: it stays carried', put.to, _name(held))
            continue
        tally.guessed = False
        view = run.reads.stash_view()
        landed = view.page_of(held.unit_id) if view is not None else None
        page = landed if landed is not None else put.to
        if landed is not None and landed != put.to:
            tally.shown = landed
        parked.append((held, page))
        LOG.info("Macro: stash: the %s (junk) parked on page %d for the stop: room for the cube's %s", _name(held),
                 page, _keepers(later))  # fmt: skip


def _unpark(run: Run, rect: Rect, parked: Sequence[tuple[Carried, int]], tally: Tally) -> list[tuple[Carried, int]]:
    """The parked junk back into the inventory, the largest first (as town.py `after` has them come back): each found
    on its page as read, that page shown, a Ctrl + click on its cell, checked to be carried again. Those still in the
    stash."""
    left: list[tuple[Carried, int]] = []
    for item, page in sorted(parked, key=lambda p: (-p[0].size[0] * p[0].size[1], -p[0].size[1], p[0].unit_id)):
        view = run.reads.stash_view()
        lying = next(((p.index, i) for p in (view.pages if view else ()) for i in p.items if i.unit_id == item.unit_id),
                     None)  # fmt: skip
        if lying is None:
            LOG.info('Macro: stash: the parked %s is not read on page %d', _name(item), page)
            left.append((item, page))
            continue
        index, there = lying
        back = False
        for _ in range(2):
            _show(run, rect, index, tally)
            run.actuator.move(*cell_point(rect, STASH_PAGE, (there.x, there.y), there.size), scatter=(4, 4))
            run.actuator.click('Control_L')
            back = bool(_until(run, lambda p, i=item: any(c.unit_id == i.unit_id for c in p.items)))
            if back or not tally.guessed:
                break
            tally.guessed = False
            _shared(run, rect, index)
            tally.shown = tally.memory.shared = index
        if back:
            tally.guessed = False
            LOG.info('Macro: stash: the parked %s taken back from page %d for Jamella', _name(item), index)
        else:
            LOG.info('Macro: stash: the parked %s did not come back from page %d (%d, %d)', _name(item), index,
                     there.x, there.y)  # fmt: skip
            left.append((item, index))
    return left


def _rescue(run: Run, parked: Sequence[tuple[Carried, int]], tally: Tally) -> list[tuple[Carried, int]]:
    """The parked junk taken back when the stop gives up after the park (the stash opened again where it stands);
    those still in the stash. Never raises."""
    try:
        close_stash(run)
        rect = open_stash(run)
        tally.shown = None
        return _unpark(run, rect, parked, tally)
    except Abort as error:
        LOG.info('Macro: stash: the parked junk not taken back: %s', error)
        return list(parked)


def _into_cube(run: Run, inventory_key: str, items: Sequence[Carried], later: Sequence[Carried]) -> int:
    """The junk with no cell to move aside to put into the cube (`StashStop.into_cube`), sold from there at Jamella
    (`visit`'s passes take the cube's junk out): the inventory and the cube opened, a Ctrl + click on each (as cube.py
    `stash` puts the loop's items in), checked in memory; the panels closed after. How many went in."""
    rect = run.actuator.keys.focused_window_rect()
    pack = run.reads.carried()
    cube = next((item for item in pack.items if item.txt == CUBE_CLASS), None) if pack is not None else None
    if not items or rect is None or cube is None:
        return 0
    put = 0
    try:
        open_inventory(run, inventory_key)
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
        run.actuator.rebase()
        for item in items:
            held, _in_cube = _now(run, item.unit_id)
            if held is None:
                continue
            run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            if _until(run, lambda p, i=held: i.unit_id in p.cube_items):
                put += 1
            else:
                LOG.info('Macro: cube: the %s at (%d, %d) did not go in', _name(held), held.x, held.y)
    finally:
        if {'inventory', 'cube'} & set(run.world().open_panels):
            run.actuator.tap('Escape')
            run.seen(lambda w: not {'inventory', 'cube'} & set(w.open_panels), PANEL_SECONDS)
            run.actuator.rebase()
    LOG.info("Macro: cube: %d of %d junk items put in for Jamella: room for the cube's %s", put, len(items),
             _keepers(later))  # fmt: skip
    return put


def _cube_runes(run: Run, rect: Rect, stop: StashStop, tally: Tally) -> int:
    """The stop's rune transmutes (`StashStop.runes`, town.py RUNES_AIM), the stash open: the Runes tab shown, for each
    a Ctrl + Shift + right click on the stack's slot (three of it into the cube: the player, 14:28 on 2026-10-18,
    "ctrl + shift + right click on resource => move 3 of item to the cube"; live from 18:27), checked to put exactly
    RUNES_A_TAKE of the class in the cube and nothing else; for a recipe that takes a gem (the player, 18:31: "yes,
    loop should use required gems + runes") the Gems tab shown and a Ctrl + Shift + left click on the gem's stack, one
    of it into the cube (the player, 18:48: "ctrl + shift + left - moves 1 item"), the cube checked to hold the three
    runes and the one gem alone;
    the tab's Transmute button, checked to leave one rune of the class made; that rune onto its stack by a Ctrl + Shift
    + click (proven: a cube resource onto its stack, 2026-10-17). Then the loop's runes the stacks had no room for
    (`StashStop.rune_puts`), each by a Ctrl + click as the stash read now gives its stack room; one refused stays
    carried (never the scan). Anything unexpected ends the transmutes, the runes and gems taken back onto their stacks
    first: none is ever left in the cube by them. Never a Ber Rune (town.py BER). How many were made."""
    pack = run.reads.carried()
    if pack is None or pack.in_cube or all(i.txt != CUBE_CLASS for i in pack.items):
        LOG.info('Macro: stash: no rune transmute: %s', 'the inventory is not read' if pack is None
                 else f'the cube holds {len(pack.in_cube)} items' if pack.in_cube else 'no cube carried')  # fmt: skip
        return 0
    began, made, shown = run.clock(), 0, None
    for rune in stop.runes:
        slot = rune_slot(rune.txt)
        gem_slot = rune_slot(rune.gem) if rune.gem is not None else None
        if slot is None or rune.txt == BER or rune.gem == BER or (rune.gem is not None and gem_slot is None):
            break
        if shown != RUNES_TAB:
            _tab(run, rect, tab_point(RUNES_TAB))
            tally.shown, shown = RESOURCE_TAB, RUNES_TAB
        run.actuator.move(*panel_point(rect, *slot), scatter=(6, 6))
        run.actuator.tap('Control_L', 'Shift_L', 'Button3')
        if not _until(run, lambda p, t=rune.txt: _holds_only(p, {t: RUNES_A_TAKE})):
            inside = _inside(run)
            LOG.info('Macro: stash: a Ctrl + Shift + right click on the %s stack put %s into the cube, not %d of it: '
                     'no rune transmute', _rune(rune.txt), ', '.join(_name(i) for i in inside) or 'nothing',
                     RUNES_A_TAKE)  # fmt: skip
            _runes_back(run, rect, [i for i in inside if i.txt == rune.txt])
            break
        if rune.gem is not None and gem_slot is not None:
            gem = rune.gem
            _tab(run, rect, tab_point(GEMS_INDEX))
            shown = GEMS_INDEX
            # One gem by a Ctrl + Shift + left click (the player, 18:48 on 2026-10-18: "when cubing runes and we need
            # to move only 1 gem, we don't need to do right click (moves 3 items), ctrl + shift + left - moves 1 item")
            run.actuator.move(*panel_point(rect, *gem_slot), scatter=(6, 6))
            run.actuator.click('Control_L', 'Shift_L')
            if not _until(run, lambda p, t=rune.txt, g=gem: _holds_only(p, {t: RUNES_A_TAKE, g: 1})):
                inside = _inside(run)
                LOG.info('Macro: stash: the %s for three %s not taken into the cube (it holds %s): no rune transmute',
                         _rune(gem), _rune(rune.txt), ', '.join(_name(i) for i in inside) or 'nothing')  # fmt: skip
                _runes_back(run, rect, [i for i in inside if i.txt in (rune.txt, gem)])
                break
        run.actuator.move(*panel_point(rect, *stash_transmute()), scatter=(3, 3))
        run.actuator.click()
        if (
            until(run, lambda p, t=rune.into: _holds_only(p, {t: 1}), TRANSMUTE_SECONDS, read=lambda: _carried(run))
            is None
        ):
            inside = _inside(run)
            LOG.info('Macro: stash: three %s not transmuted: the cube holds %s', _rune(rune.txt),
                     ', '.join(_name(i) for i in inside) or 'nothing')  # fmt: skip
            _runes_back(run, rect, [i for i in inside if i.txt in (rune.txt, rune.gem)])
            break
        if not _runes_back(run, rect, _inside(run)):
            break
        made += 1
        view = run.reads.stash_view()
        LOG.info('Macro: cube: three %s%s into a %s at the stash (stacks %s)', _rune(rune.txt),
                 f' and a {_rune(rune.gem)}' if rune.gem is not None else '', _rune(rune.into),
                 f'{view.count(rune.txt)} and {view.count(rune.into)}' if view is not None else 'unread')  # fmt: skip
    late = 0
    for put in stop.rune_puts:
        held, _in_cube = _now(run, put.item.unit_id)
        view = run.reads.stash_view()
        if held is None or view is None or view.room(held.txt) <= 0:
            continue
        run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(6, 6))
        run.actuator.click('Control_L')
        if _sent(run, rect, held, INVENTORY, _gone(held)):
            tally.moved += 1
            late += 1
        else:
            LOG.info('Macro: stash: the %s did not go onto its stack: it stays carried', _name(held))
    LOG.info('Macro: stash: runes cubed: %d of %d planned, %d carried runes put after, %.1fs', made, len(stop.runes),
             late, run.clock() - began)  # fmt: skip
    if made:
        run.say(f'Cube: {made} rune transmute{"s" if made != 1 else ""}')
    return made


def _carried(run: Run) -> Pack | None:
    return run.reads.carried()


def _inside(run: Run) -> tuple[Carried, ...]:
    pack = _carried(run)
    return pack.in_cube if pack is not None else ()


def _holds_only(pack: Pack | None, wanted: dict[int, int]) -> bool:
    """Whether the cube holds exactly `wanted` (class -> count) and nothing else."""
    if pack is None:
        return False
    return Counter(i.txt for i in pack.in_cube) == Counter(wanted) and len(pack.cube_items) == sum(wanted.values())


def _runes_back(run: Run, rect: Rect, items: Sequence[Carried]) -> bool:
    """The cube's runes onto their stacks, a Ctrl + Shift + click each with a resource tab shown; whether all went."""
    went = True
    for item in items:
        run.actuator.move(*cell_point(rect, STASH_CUBE, (item.x, item.y), item.size), scatter=(6, 6))
        run.actuator.click('Control_L', 'Shift_L')
        if not _sent(run, rect, item, STASH_CUBE, lambda p, i=item: i.unit_id not in p.cube_items):
            LOG.info("Macro: stash: the cube's %s did not go onto its stack", _name(item))
            went = False
    return went


def _rune(txt: int | None) -> str:
    """A rune's or a gem's name."""
    if txt in RUNE_CLASSES:
        return RUNE_CLASSES[txt]['name']
    base = metadata()['bases'].get(str(txt))
    return base['name'] if base is not None else str(txt)


def _drops(run: Run, rect: Rect, items: Sequence[Carried]) -> int:
    """The full stacks' materials put down between the panels (no vendor buys one: the player, 10:37 on 2026-10-18,
    "there is no use for it"): taken up by a click, let fall by a click on the ground; put back where it was if it does
    not fall, then `Abort`. How many fell."""
    fell = 0
    for item in items:
        if why := protected(run, item):
            LOG.info('Macro: stash: the %s is %s: never put down', _name(item), why)
            continue
        held, _in_cube = _now(run, item.unit_id)
        if held is None:
            continue
        run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(4, 4))
        run.actuator.click()
        if not _until(run, lambda p, i=held: p.pointer == i.unit_id):
            pack = run.reads.carried()
            if pack is not None and pack.pointer is not None:
                run.actuator.click()  # something else taken up: put down where it was, the pointer not moved
                _until(run, lambda p: p.pointer is None)
            LOG.info('Macro: stash: the %s was not taken up to put down', _name(held))
            continue
        run.actuator.move(*PARK_POINT, scatter=(4, 4))
        run.actuator.click()
        if not _until(run, lambda p, i=held: p.pointer is None and _gone(i)(p)):
            run.actuator.move(*cell_point(rect, INVENTORY, (held.x, held.y), held.size), scatter=(4, 4))
            run.actuator.click()
            _until(run, lambda p: p.pointer is None)
            raise Abort(f'the {_name(held)} did not fall')
        LOG.info('Macro: stash: the %s put down: its stack is full and no vendor buys it', _name(held))
        fell += 1
    return fell


def _scan(run: Run, missed: Sequence[Carried], inventory_key: str | None, own: frozenset[Cell]) -> int:
    """Today's scan (stash.py `unload`) for the items a put missed, and only them."""
    pack = run.reads.carried()
    if pack is None:
        return 0
    ids = {item.unit_id for item in missed}
    keep = frozenset(i.unit_id for i in (*pack.items, *pack.in_cube) if i.unit_id not in ids)
    LOG.info('Macro: stash: %d items by the scan, page after page', len(ids))
    return unload(run, own, inventory_key, None, keep, None, Pages())


# The town visit (step 3)


@dataclass
class Hands:
    """The runner's closures a visit takes: the key that opens the inventory; Cain's identify (the tome the fallback),
    the appraisals waited for; the junk among identified items (macros/junk.py `junk_of`); the stash as read (world.py
    `StashView`, None unread); the full gem stacks' transmutes (cube.py `transmute`, what it puts down picked up
    again): how many perfect gems were made and how many units it left on the ground."""

    inventory_key: Callable[[], str | None]
    identify: Callable[[Sequence[Carried]], object]
    judge: Callable[[list[Carried]], list[Carried]]
    view: Callable[[], StashView | None]
    transmute: Callable[[frozenset[int]], tuple[int, int]] | None = None


@dataclass(frozen=True)
class TownMap:
    """A town's places for a visit: its level, its waypoint, its stash, and the units of the one who identifies, the
    vendor, the one who repairs (each stop's routine walks to its own: shop.py USUAL)."""

    area: int
    waypoint: tuple[float, float]
    stash: tuple[float, float]
    cain: int
    vendor: int
    repairer: int


FORTRESS_MAP = TownMap(FORTRESS, (5044.0, 5019.0), USUAL, CAIN, JAMELLA, HALBU)
SELL_PASSES = 4  # the cube's junk out and sold, pass after pass, as the inventory's room allows
STOPS = ('cain', 'stash', 'jamella', 'halbu', 'walk')


@dataclass(frozen=True)
class Visited:
    """What a visit did: its contract, the stash's full stacks as read after its stop (no potion: the belt's; unread:
    what was known, and what the scan's refusals taught), whether a repair raised nothing (none tried again for
    RETRY_GAMES games), and each stop's seconds."""

    contract: Contract
    full: frozenset[int] = frozenset()
    repair_failed: bool = False
    seconds: tuple[tuple[str, float], ...] = ()


def _pack(run: Run) -> Pack:
    pack = run.reads.carried()
    if pack is None:
        raise Abort('the inventory is not read')
    return pack


def _full_of(view: StashView) -> frozenset[int]:
    return frozenset(txt for txt in view.full() if not is_potion(txt))


def _unknown(pack: Pack, own: frozenset[Cell]) -> list[Carried]:
    return [i for i in (*loot(pack, own), *pack.in_cube) if not i.identified and i.quality >= MAGIC]


@contextmanager
def _timed(run: Run, took: dict[str, float], stop: str) -> Iterator[None]:
    began = run.clock()
    try:
        yield
    finally:
        took[stop] = took.get(stop, 0.0) + run.clock() - began


def _cubable(carried: Sequence[Carried], full: frozenset[int]) -> bool:
    """A transmute's worth of a full flawless stack's gems carried, its perfect stack not full (§2.3)."""
    kinds = Counter(i.txt for i in carried if i.txt in full and perfect_of(i.txt) not in (None, *full))
    return any(count >= GEMS_A_TRANSMUTE for count in kinds.values())


def _stash(
    run: Run,
    hands: Hands,
    key: str | None,
    own: frozenset[Cell],
    junk: frozenset[int],
    needs: Needs,
    full: frozenset[int],
    memory: Remembered,
    record: Recorder | None = None,
    plans: list[StashStop] | None = None,
) -> frozenset[int]:
    """The stash stop, planned from the stash as read (`stash_stop`), else today's scan (stash.py `unload`): the loop's
    items but the junk and the unidentified. The full stacks after it, as read (or learned by the scan's refusals).
    `record`: the visit's snapshots, told the gold and the stash as read here (no read more); `plans`: the stop's plan
    added to it (the keepers no page takes, the junk parked)."""
    pack = _pack(run)
    waiting = frozenset(i.unit_id for i in _unknown(pack, own))
    staff = run.reads.teleport()
    cost = expected(staff.maximum - staff.charges) if staff is not None else None
    coins, cap = gold(run), gold_cap(run)
    if record is not None:
        record.gold(coins, cap)
    gold_to = deposit_to(coins, cap, cost or 0)
    view = hands.view()
    try:
        if view is not None:
            planned = plan_stop(Holdings(pack, own, junk, waiting), view, needs, deposit_to=gold_to)
            if plans is not None:
                plans.append(planned)
            backlog = uncubed(dict(view.stacks))
            if backlog:
                LOG.info('Macro: stash: rune stacks over %d not cubed: %s', RUNES_AIM, '; '.join(
                    f'{_rune(txt)} {view.count(txt)}: {why}' for txt, why in backlog))  # fmt: skip
            if planned.idle:
                LOG.info("Macro: town visit: the stash: nothing of the loop's to put in")
                return full
            stash_stop(run, planned, inventory_key=key, own=own, memory=memory)
        else:
            stay = (
                waiting
                | junk
                | frozenset(
                    i.unit_id for i in (*pack.items, *pack.in_cube) if i.txt in full and i.txt not in sold_full(full)
                )
            )
            if all(i.unit_id in stay for i in (*loot(pack, own), *pack.in_cube)) and gold_to is None:
                return full
            LOG.info('Macro: town visit: the stash is not read: the scan, page after page')
            tried = set(sold_full(full))
            pages = Pages()
            unload(run, own, key, tried, stay, gold_to, pages)
            after = _pack(run)
            remaining = [i for i in after.in_cube if i.unit_id not in stay]
            if key is not None and remaining:
                # The first scan often frees a keeper's block. If the remaining obstruction is inventory junk,
                # shift that junk within the inventory here, before Jamella. This keeps the player's one-stash-walk
                # order even with an unread stash (21:03:47 on 2026-10-18: two rings blocked Humongous).
                blocked = next((i for i in remaining if not after.inventory.has_room(i.size)), None)
                moves = unread_way_for_cube(after, blocked, junk, needs.block) if blocked is not None else ()
                if moves:
                    rect = run.actuator.keys.focused_window_rect()
                    if rect is not None:
                        run.actuator.tap(key)
                        if run.seen(lambda w: 'inventory' in w.open_panels, PANEL_SECONDS) is not None:
                            try:
                                _aside(run, rect, moves, remaining)
                            finally:
                                run.actuator.tap('Escape')
                                run.seen(lambda w: 'inventory' not in w.open_panels, PANEL_SECONDS)
                after = _pack(run)
                if any(after.inventory.has_room(i.size) for i in remaining):
                    LOG.info('Macro: stash: inventory room freed for a cube keeper: the scan again in place')
                    unload(run, own, key, tried, stay, None, pages)
            guessed = sorted(tried - set(sold_full(full)) - set(full))
            if guessed:
                # A refusal with the stash unread is a guess, never a full stack: kept carried, neither put down nor
                # kept in FULL_FILE (the Deep Worldstone Shards "full" at 83 dropped and left, 22:14 on 2026-10-18 and
                # 01:59 on 2026-10-19; the player: "we need to track this correctly")
                LOG.info('Macro: stash: refused with the stash unread, kept carried, not counted full: %s',
                         ', '.join(_class_name(txt) for txt in guessed))  # fmt: skip
            return full
    except Abort as stop:
        if cut(run, stop):
            raise
        LOG.info('Macro: stash: %s: the visit goes on', stop)
    after = hands.view()
    if record is not None:
        record.view = after
    return _full_of(after) if after is not None else full


def _class_name(txt: int) -> str:
    return metadata()['bases'].get(str(txt), {}).get('name', f'item {txt}')


def _drop(run: Run, key: str | None, items: Sequence[Carried]) -> None:
    """The full stacks' materials put down (no vendor buys one, and the stack has no room: the player, 10:37 on
    2026-10-18, "there is no use for it")."""
    for item in items:
        if key is not None:
            drop_item(run, key, item, 'in town: its stack is full and no vendor buys it')


def _halbu(run: Run) -> bool:
    """Halbu's Repair All; whether it failed for want of something other than gold (not tried again for a while)."""
    try:
        return not repair(run) and affordable(gold(run))
    except Abort as stop:
        if cut(run, stop):
            raise
        LOG.info('Macro: repair: %s: not tried again for %d games', stop, RETRY_GAMES)
        return True


def _repair_due(run: Run, waited: bool) -> bool:
    staff = run.reads.teleport()
    wear = run.reads.wear()
    return due(staff, wear, gold(run), top_up=tops_up(staff, True, False), waited=waited)


# The visit's snapshots and its plan in shadow (rca/2026-10-18/arch-town-planning.md §4, steps M0 and M1): no click is
# made by them, no game read added, nothing raised into the visit


def _note(
    record: Recorder,
    start: Snapshot,
    stop: str,
    pack: Pack | None,
    *,
    full: frozenset[int],
    view: StashView | None = None,
    misses: tuple[str, ...] = (),
) -> None:
    """A snapshot of the visit at `stop` into its file (macros/visitlog.py), from what it has read (the player's own,
    the junk, the needs and the exit as at its `start`); never raises."""
    if not record.active or pack is None:
        return
    try:
        record.note(replace(start, stop=stop, pack=pack, view=view, full=full, misses=misses, predicted=None, at=''))
    except Exception as error:  # never into the visit
        record.failed = True
        LOG.info('Macro: visit snapshot: not made: %s', error)


def _predict(start: Snapshot) -> townplan.VisitPlan | None:
    """The whole visit simulated from its start (macros/townplan.py `plan_visit`), the rulings as the visit makes them
    (town.py PARK_JUNK and KEEPER_IN_CUBE, `JAMELLA_FIRST`), its misses logged: `Macro: town plan: predicts <misses
    or none> (variant …)`; never raises."""
    try:
        rulings = townplan.Rulings(park_junk=PARK_JUNK, jamella_first=JAMELLA_FIRST, keeper_in_cube=KEEPER_IN_CUBE)
        plan = townplan.plan_visit(start, rulings)
        if plan is None:
            LOG.info('Macro: town plan: no prediction: the stash is not read')
        else:
            LOG.info('Macro: town plan: predicts %s', plan.said())
        return plan
    except Exception as error:  # never into the visit
        LOG.info('Macro: town plan: failed: %r', error)
        return None


def _matched(plan: townplan.VisitPlan | None, done: Contract) -> None:
    """Whether the contract the visit left has the misses the plan foresaw (the parts it models: townplan.MODELLED):
    `Macro: town plan: matched`, else `differs: predicted …; the visit …`; never raises."""
    if plan is None:
        return
    try:
        modelled = [miss for miss in done.misses if townplan.kind_of(miss) in townplan.MODELLED]
        if townplan.kinds(plan.misses) == townplan.kinds(modelled):
            LOG.info('Macro: town plan: matched')
        else:
            LOG.info('Macro: town plan: differs: predicted %s; the visit %s', '; '.join(plan.misses) or 'none',
                     '; '.join(modelled) or 'none')  # fmt: skip
    except Exception as error:  # never into the visit
        LOG.info('Macro: town plan: not compared: %r', error)


# Jamella before the stash for a cube keeper stranded by the junk (`visit`): off until the player rules on the order
# (the ruled order is the stash, then her; asked at 15:06 on 2026-10-18)
JAMELLA_FIRST = False


def _stranded(run: Run, hands: Hands, own: frozenset[Cell], junk: frozenset[int], needs: Needs) -> tuple[Carried, ...]:
    """The cube's keepers the stash stop as planned now leaves in the cube that the inventory's junk sold first would
    let out (town.py `StashStop.stranded`); none with the stash unread."""
    view = hands.view()
    pack = run.reads.carried()
    if view is None or pack is None:
        return ()
    waiting = frozenset(i.unit_id for i in _unknown(pack, own))
    return plan_stop(Holdings(pack, own, junk, waiting), view, needs).stranded


def visit(
    run: Run,
    hands: Hands,
    needs: Needs,
    own: frozenset[Cell],
    exit: Exit,
    town: TownMap = FORTRESS_MAP,
    *,
    full: frozenset[int] = frozenset(),
    waited: bool = True,
    memory: Remembered | None = None,
) -> Visited:
    """One town visit (the module text): Cain, the stash, Jamella, Halbu, the exit, each once and only when it has
    something to do; what it left (`Visited`). `full`: the stash's full stacks as last known (FULL_FILE), for a stash
    that cannot be read; `waited`: a repair may be tried (none for RETRY_GAMES games after one that raised nothing).
    Mouse mode only. `Abort` from a stop that cannot go on (Jamella's, the stash's for the player's hand)."""
    if run.pad is not None:
        raise Abort('the town visit needs mouse mode')
    world = run.world()
    if world.player is None or world.player.area != town.area:
        raise Abort('the town visit is not in its town')
    began, took = run.clock(), dict[str, float]()
    memory = memory if memory is not None else Remembered()
    key = hands.inventory_key()
    # 1. Cain: every unidentified magic-or-better item, the cube's too, then the appraisal's verdicts
    pack = _pack(run)
    unknown = _unknown(pack, own)
    if unknown:
        with _timed(run, took, 'cain'):
            hands.identify(tuple(unknown))
        pack = _pack(run)
    view = hands.view()
    stacks = _full_of(view) if view is not None else frozenset(full)
    carried = [*loot(pack, own), *pack.in_cube]
    # The best copy of a set or unique item first (the player, 16:50 on 2026-10-18): a copy kept is no junk, so the
    # stash stop takes it as a keeper (macros/copies.py)
    from inventory_tracking.macros.copies import sold

    judged = sold(hands.judge([i for i in carried if i.identified]), visitlog.session_directory())
    junk = frozenset(i.unit_id for i in (*judged, *surplus(carried, stacks)))
    # The player's items and the keepers by their stats are never junk, whatever the appraisal (engine.py `protected`)
    spared = [(i, why) for i in carried if i.unit_id in junk and (why := protected(run, i))]
    if spared:
        LOG.info('Macro: town visit: %s: kept, not sold', ', '.join(f'{_name(i)} ({why})' for i, why in spared))
        junk -= {i.unit_id for i, _why in spared}
    LOG.info('Macro: town visit (%s): %d of the loop\'s items, %d identified at Cain, %d junk; full stacks %d',
             exit.value, len(carried), len(unknown), len(junk), len(stacks))  # fmt: skip
    record = Recorder(visitlog.session_directory())
    start = Snapshot('start', pack, own, needs, exit, view, junk, frozenset(i.unit_id for i in _unknown(pack, own)),
                     stacks)  # fmt: skip
    predicted = _predict(start)
    record.note(replace(start, predicted=predicted.misses if predicted is not None else None))
    failed, repaired = False, False

    def jamella(stacks: frozenset[int], *, stock: bool) -> bool:
        """3. Jamella (Halbu first at the gold's cap): the junk sold, the full materials put down; the keys bought
        (`stock`: also when nothing is sold and a stock is short). Whether she was visited."""
        nonlocal failed, repaired
        # A full stack's runes are no longer sold (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower"; sold
        # here since 2026-10-17, "probably we better just sell them"): the stash stop transmutes the stack down
        # (town.py RUNES_AIM) and puts them on it after
        material = frozenset(txt for txt in sold_full(stacks) if txt not in RUNE_CLASSES)

        def selling(p: Pack) -> list[Carried]:
            return [i for i in loot(p, own) if i.unit_id in junk]

        def cubed(p: Pack) -> list[Carried]:
            return [i for i in p.in_cube if i.unit_id in junk or i.txt in material]

        pack = _pack(run)
        _drop(run, key, [i for i in loot(pack, own) if i.txt in material])
        pack = _pack(run)
        if not (selling(pack) or cubed(pack) or (stock and short(pack, needs.portals))):
            return False
        coins, cap = gold(run), gold_cap(run)
        capped = coins is not None and cap is not None and coins + SALE_MOST > cap
        if not repaired and capped and (selling(pack) or cubed(pack)) and _repair_due(run, waited):
            # The gold near its cap, no sale is made: the repair first, its cost the sales' room (15:33:27 on
            # 2026-10-17)
            with _timed(run, took, 'halbu'):
                failed, repaired = _halbu(run), True
        with _timed(run, took, 'jamella'):
            for passes in range(1 + SELL_PASSES):
                # The cube's junk the stash stop left (no room then, or the stash unread) out as the room takes it, then
                # sold too (the player: "both from cube and inventory"), pass after pass as the sales make room
                out = cubed(_pack(run))
                if out and key is not None:
                    unpack(run, key, out)
                    _drop(run, key, [i for i in loot(_pack(run), own) if i.txt in material])
                sell = selling(_pack(run))
                if passes and not sell:
                    break
                restock(run, sell, back=False, keys=needs.keys)
                if not sell or not cubed(_pack(run)):
                    break
        return True

    # Jamella before the stash when a cube keeper gets out only once the inventory's junk is sold: at 15:05:53 on
    # 2026-10-18 a junk Fuscina (2 x 4) held the inventory's only room and the cube was full, so the set Boots (2 x 2)
    # had no way out and stayed in the cube ("short of the contract: cube 1 items"); she is on the way (about 35 units
    # of walk more, the walk from her to the waypoint saved), not a second walk to the stash. Never with the gold near
    # its cap: the deposit is the stash's
    early = False
    stranded = _stranded(run, hands, own, junk, needs) if JAMELLA_FIRST else ()
    if stranded:
        coins, cap = gold(run), gold_cap(run)
        if coins is not None and cap is not None and coins + SALE_MOST > cap:
            LOG.info("Macro: town visit: the cube's %s has no room until the junk is sold; the gold is near its cap: "
                     'the stash first', _keepers(stranded))  # fmt: skip
        else:
            LOG.info("Macro: town visit: Jamella before the stash: the cube's %s has no room until the junk is sold",
                     _keepers(stranded))  # fmt: skip
            early = jamella(stacks, stock=True)
    # 2. The stash, once: the keepers from the inventory and the cube, the cube's junk out for her
    with _timed(run, took, 'stash'):
        plans: list[StashStop] = []
        stacks = _stash(run, hands, key, own, junk, needs, stacks, memory, record, plans)
        parked_left = 0
        now = _pack(run) if hands.transmute is not None else None
        if now is None and record.active:
            now = run.reads.carried()  # no transmute (a test): read for the snapshot
        _note(record, start, 'stash', now, view=record.view, full=stacks)
        if hands.transmute is not None and now is not None and _cubable([*loot(now, own), *now.in_cube], stacks):
            # The full flawless stacks three at a time into a perfect one, standing at the stash; its stop again for
            # the perfect gems (no walk)
            made, parked_left = hands.transmute(stacks)
            if made:
                stacks = _stash(run, hands, key, own, junk, needs, stacks, memory, plans=plans)
        # A keeper no page has room for, after every move: the stash is full, and the loop stops on it (the player,
        # 16:50 on 2026-10-18: "if stash is full - we need to stop loop"; runner.py reads `Contract.stash_full`). Not
        # the stranded keeper (room on a page, none to come out through), which the park makes
        homeless = tuple(dict.fromkeys(name for planned in plans for name in named(planned.full)))
        if homeless:
            LOG.info('Macro: stash: full: %s', ', '.join(homeless))
    # 3. Jamella after the stash (again only with something left to sell)
    late = jamella(stacks, stock=not early)
    shop = early or late
    if not repaired and _repair_due(run, waited):
        with _timed(run, took, 'halbu'):
            failed, repaired = _halbu(run), True
    # The build's free block: a key stack out of it (the player, 2026-10-18: "we should have 2x4 inventory space")
    pack = _pack(run)
    _note(record, start, 'shops', pack, full=stacks)
    if key is not None and not pack.inventory.has_room(needs.block) and keys_move(pack, needs.block):
        try:
            arrange_keys(run, key)
        except Abort as stop:
            if cut(run, stop):
                raise
            LOG.info('Macro: inventory: the keys not arranged: %s', stop)
    # 4. The exit: the waypoint walked to from Jamella's or Halbu's (out of its sight there); none when the game is left
    if exit != Exit.LEAVE and (late or repaired):
        with _timed(run, took, 'walk'):
            try:
                walk_until(run, _waypoint(run), WAYPOINT_SEEN, 'the waypoint')
            except Abort as stop:
                if cut(run, stop):
                    raise
                LOG.info('Macro: town visit: toward the waypoint: %s', stop)
    pack = _pack(run)
    in_stash: list[Carried] = []
    if any(planned.parks for planned in plans):
        # The junk a park left on a page, as the stash reads now (`stash_stop` takes every one back, or names it)
        after = hands.view()
        in_stash = [i for page in (after.pages if after is not None else ()) for i in page.items if i.unit_id in junk]
    # A cube keeper the stop could not get out (room on a page, no way out even with a park) waits in the cube for the
    # next visit (the player, 17:50 on 2026-10-18: "keeper can wait in cube"): named, not a miss; one no page has room
    # for is the stash full, never this
    homeless_units = {i.unit_id for planned in plans for i in planned.full}
    waits = {i.unit_id for planned in plans for i in planned.waits} - homeless_units
    deferred = [i for i in pack.in_cube if i.unit_id in waits] if KEEPER_IN_CUBE else []
    for name in named(deferred):
        LOG.info('Macro: town visit: %s waits in the cube for the next visit', name)
    done = contract(pack, own, needs, junk=junk, full=stacks, restocked=shop, parked_left=parked_left,
                    stash_full=homeless, in_stash=in_stash, deferred=deferred)  # fmt: skip
    _note(record, start, 'end', pack, full=stacks, misses=done.misses)
    staff = run.reads.teleport()
    free = sum(row.count('.') for row in pack.inventory)
    LOG.info(
        'Macro: trade session done%s: cube %d items, block %dx%d %s, %d inventory cells free, junk left %d, keys %s, '
        'portals %s, staff %s, ground %s, %.1f s (%s)',
        f' (short of the contract: {", ".join(done.misses)})' if done.misses else '',
        done.cube, *needs.block, 'free' if done.block_free else 'taken', free, done.junk_left, done.keys,
        done.portals, f'{staff.charges}/{staff.maximum}' if staff is not None else '?',
        'clear' if not done.parked_on_ground else f'{done.parked_on_ground} left', run.clock() - began,
        ', '.join(f'{stop} {took[stop]:.1f}' if stop in took else f'{stop} -' for stop in STOPS),
    )  # fmt: skip
    _matched(predicted, done)
    run.say(f'Town: cube {done.cube}, junk left {done.junk_left}, keys {done.keys}')
    return Visited(done, stacks, failed, tuple((stop, took[stop]) for stop in STOPS if stop in took))
