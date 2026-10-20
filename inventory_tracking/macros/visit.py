"""The town visit's executor (macros/town-plan.md §2.1): `visit` is the loop's one town leg, `stash_stop` its stash.

`visit`, in the player's order (2026-10-18: "identify everything with cain; move to the shared stash; put all items
that we need to keep in stash ... visit store and sell junk"): Cain for the unidentified (inventory and cube); the junk
judged; one stash stop (keepers in, the cube's junk out, full gem stacks transmuted there); Jamella sells the junk and
buys keys (Halbu first when the gold is near its cap); Halbu when a repair is due; a key stack out of the free block;
the walk to the waypoint unless the game is left; then the contract (town.py `contract`). Each stop is planned from
memory read at it, so a visit cut and made again does only what is left.

`stash_stop`: one walk, each put clicked once onto its planned page and checked; a refused put goes to the scan
(`stash.unload`). Cube keepers with no room yet come out through the room the inventory's keepers leave (stash closed,
`unpack`, reopened in place); junk in the way is moved aside, put into the cube, or parked on a page and taken back
before the stash closes. Rulings and evidence: history/visit.md.
"""

from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack, StashView
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros import visitlog
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


__all__ = ['FORTRESS_MAP', 'Hands', 'Remembered', 'TownMap', 'Visited', 'note_view', 'stash_stop', 'visit']

Rect = tuple[int, int, int, int]


# A new game's Shared tab opens on its first page, not on the one shown last in the game before: the Spiked Shield
# went onto page 1, planned 3 (remembered 3 from the visit of 02:23), at 02:36:57 on 2026-10-19, the stash opened once;
# 39 such landings that day (to 21:55), 31 onto page 1 and 8 onto page 2 after one arrow
FIRST_SHARED = 1


@dataclass
class Remembered:
    """Kept between stops: the game whose stash view was logged, and the shared page the Shared tab showed last
    (`shared`, in the game `shared_game`; the tab reopens on it within that game; None: not known)."""

    game: str | None = None
    shared: int | None = None
    shared_game: str | None = None

    def shared_in(self, game: str | None) -> int | None:
        """The page the Shared tab opens on in `game`: the one shown last in it, FIRST_SHARED in a later game."""
        if self.shared is not None and game is not None and self.shared_game is not None and game != self.shared_game:
            return FIRST_SHARED
        return self.shared

    def saw(self, game: str | None, page: int) -> None:
        self.shared, self.shared_game = page, game


def note_view(run: Run, noted: Remembered) -> None:
    """Log the stash as read once a game in Pandemonium Fortress, to measure the view against what the stop finds."""
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
    landed: dict[int, int] = field(default_factory=dict)  # unit id -> the page a put went onto, as read after it

    def miss(self, item: Carried) -> None:
        if all(i.unit_id != item.unit_id for i in self.missed):
            self.missed.append(item)


def stash_stop(
    run: Run, stop: StashStop, *, inventory_key: str | None, own: frozenset[Cell], memory: Remembered | None = None
) -> int:
    """Make the planned stash stop; how many items went in. Mouse mode only. `Abort` (panels closed) when the stash
    does not open or a click takes an item onto the pointer."""
    if run.pad is not None:
        raise Abort('the stash needs mouse mode')
    pack = run.reads.carried()
    if pack is None or stop.idle:
        LOG.info("Macro: stash: by the view: nothing of the loop's to put in")
        return 0
    began = run.clock()
    # Tallest first, as `unpack` orders them: in page order a Ring took an armor's cell (replay 2026-10-18 15:14)
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
            # The cube's keepers out through the room the inventory's left, the stash reopened in place (probe P1
            # unknown). Junk in the way: moved aside, into the cube, or parked and taken back (history/visit.md)
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
            # Rune stacks down to RUNES_AIM (the player, 2026-10-18: "cubed, aim to 80 or lower"), the stash still open
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
    # The pages the puts went onto as read after each, not as planned (21:55:27 on 2026-10-19: planned 3, onto 1)
    went = tuple(page for page in PAGE_PRIORITY if page in set(tally.landed.values()))
    LOG.info('Macro: stash: by the view: %d items put in (pages %s), %d dropped, %d left for the scan, %d openings, '
             '%.1fs', tally.moved, ','.join(map(str, went)) or '-', dropped, len(tally.missed), openings,
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
    """Show `page`: the Personal tab; a shared page by arrows from the page shown, or from the remembered one, else
    from the tab's first page (stash.py `_shared`)."""
    if tally.shown == page:
        return
    if page == 0:
        _tab(run, rect, PERSONAL_TAB)
    elif tally.shown is not None and tally.shown >= 1:
        _arrows(run, rect, page - tally.shown)
    elif (opens := tally.memory.shared_in(_game(run))) is not None:
        _tab(run, rect, SHARED_TAB)
        _arrows(run, rect, page - opens)
        tally.guessed = True
    else:
        _shared(run, rect, page)
    tally.shown = page
    if page >= 1:
        tally.memory.saw(_game(run), page)


def _game(run: Run) -> str | None:
    return run.world().game_name or None


def _pages(run: Run, rect: Rect, puts: Sequence[Put], tally: Tally) -> None:
    """The keepers onto their planned pages in priority order, by Ctrl + click, the landed page re-read. One refused on
    a remembered page is tried again from the tab's first page, then goes to the scan; one landing elsewhere makes that
    page the one shown (town-plan.md §5)."""
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
        tally.landed[held.unit_id] = landed if landed is not None else put.to
        if landed is not None and landed != put.to:
            LOG.warning('Macro: stash: the %s went onto page %d, planned %d: page %d is the one shown', _name(held),
                        landed, put.to, landed)  # fmt: skip
            tally.shown = landed
            if landed >= 1:
                tally.memory.saw(_game(run), landed)


def _keepers(items: Sequence[Carried]) -> str:
    return ', '.join(_name(i) for i in items)


def _aside(run: Run, rect: Rect, moves: Sequence[tuple[Carried, tuple[int, int]]], later: Sequence[Carried]) -> int:
    """The planned moves within the inventory (`StashStop.shuffles`), the stash open: click up, click down on the new
    cell, checked in memory; put back if it does not land, `Abort` if it stays on the pointer. How many moved."""
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
    """The junk planned onto a shared page for the stop (`StashStop.parks`), put as `_pages` puts a keeper. Never into
    the scan: one refused stays carried. Each parked one goes into `parked` at once, so a stop that gives up takes it
    back."""
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
            if landed >= 1:
                tally.memory.saw(_game(run), landed)
        parked.append((held, page))
        LOG.info("Macro: stash: the %s (junk) parked on page %d for the stop: room for the cube's %s", _name(held),
                 page, _keepers(later))  # fmt: skip


def _unpark(run: Run, rect: Rect, parked: Sequence[tuple[Carried, int]], tally: Tally) -> list[tuple[Carried, int]]:
    """The parked junk back into the inventory, largest first (as town.py `after` plans it), each found on its page as
    read. Returns those still in the stash."""
    left: list[tuple[Carried, int]] = []
    for item, page in sorted(parked, key=lambda p: (-p[0].size[0] * p[0].size[1], -p[0].size[1], p[0].unit_id)):
        # Found by its unit id on whichever page it lies, the one planned or not
        view = run.reads.stash_view() or until(run, lambda _view: True, REREAD_SECONDS, read=run.reads.stash_view)
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
            tally.shown = index
            tally.memory.saw(_game(run), index)
        if back:
            tally.guessed = False
            LOG.info('Macro: stash: the parked %s taken back from page %d for Jamella', _name(item), index)
        else:
            LOG.info('Macro: stash: the parked %s did not come back from page %d (%d, %d)', _name(item), index,
                     there.x, there.y)  # fmt: skip
            left.append((item, index))
    return left


def _rescue(run: Run, parked: Sequence[tuple[Carried, int]], tally: Tally) -> list[tuple[Carried, int]]:
    """The parked junk taken back when the stop gives up (the stash reopened in place); those left. Never raises."""
    try:
        close_stash(run)
        rect = open_stash(run)
        tally.shown = None
        return _unpark(run, rect, parked, tally)
    except Abort as error:
        LOG.info('Macro: stash: the parked junk not taken back: %s', error)
        return list(parked)


def _into_cube(run: Run, inventory_key: str, items: Sequence[Carried], later: Sequence[Carried]) -> int:
    """The junk with no cell to move aside to into the cube (`StashStop.into_cube`), sold from there at Jamella: a
    Ctrl + click each with the cube open, checked in memory. How many went in."""
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
    """The stop's rune transmutes (`StashStop.runes`, town.py RUNES_AIM), the stash open: Ctrl + Shift + right click
    moves 3 runes into the cube, Ctrl + Shift + left click 1 gem when the recipe takes one (the player, 2026-10-18),
    each checked; Transmute; the rune made onto its stack by Ctrl + Shift + click. Then the carried runes the stacks
    had no room for (`StashStop.rune_puts`); one refused stays carried. Anything unexpected ends the transmutes with
    the cube emptied back onto the stacks. Never a Ber (town.py BER). How many were made."""
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
            # One gem (the player, 2026-10-18: "ctrl + shift + left - moves 1 item")
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
    """The full stacks' materials put down between the panels (no vendor buys one: the player, 2026-10-18, "there is
    no use for it"); put back, then `Abort`, if one does not fall. How many fell."""
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
    """The runner's closures a visit takes: the inventory key; Cain's identify (appraisals waited for); the junk among
    identified items (junk.py `junk_of`); the stash as read (None unread); the full gem stacks' transmutes (cube.py
    `transmute`): perfect gems made and units left on the ground."""

    inventory_key: Callable[[], str | None]
    identify: Callable[[Sequence[Carried]], object]
    judge: Callable[[list[Carried]], list[Carried]]
    view: Callable[[], StashView | None]
    transmute: Callable[[frozenset[int]], tuple[int, int]] | None = None


@dataclass(frozen=True)
class TownMap:
    """A town's places for a visit: level, waypoint, stash, and the identifier's, vendor's and repairer's units."""

    area: int
    waypoint: tuple[float, float]
    stash: tuple[float, float]
    cain: int
    vendor: int
    repairer: int


FORTRESS_MAP = TownMap(FORTRESS, (5044.0, 5019.0), USUAL, CAIN, JAMELLA, HALBU)
SELL_PASSES = 4  # the cube's junk out and sold, pass after pass, as the inventory's room allows
# The loop's junk no sale takes (the gold at its cap, the stash's gold full) is put down in town, not carried: 4 items
# kept took the 2x4 block (09:19:05 on 2026-10-20). The player, 2026-10-20 ~08:42: "we don't need money from selling
# these items"; "we can just pickup or appraise these items and drop if ther aren't good enough". False: kept as before
DROP_CAPPED_JUNK = True
STOPS = ('cain', 'stash', 'jamella', 'halbu', 'walk')


@dataclass(frozen=True)
class Visited:
    """What a visit did: its contract, the stash's full stacks after its stop (potions excluded), whether a repair
    failed (not tried again for RETRY_GAMES games), and each stop's seconds."""

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


# Most unread views are a momentary bad read: one short re-read before the scan, page after page (the player,
# 2026-10-19: "a quick re-read; the page-by-page scan stays as the fallback but should rarely run")
REREAD_SECONDS = 0.2  # about five game frames


def _reread(run: Run, hands: Hands) -> StashView | None:
    """The stash view read again within REREAD_SECONDS; None: still unread."""
    view = until(run, lambda _view: True, REREAD_SECONDS, read=hands.view)
    said = 'read on the second try' if view is not None else 'still unread: page by page'
    LOG.info('Macro: stash: the view %s', said)
    return view


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
    """The stash stop planned from the stash as read, else the scan (stash.py `unload`): the loop's items but the junk
    and the unidentified. Returns the full stacks after it. `record` is told the gold and the view; `plans` gets the
    stop's plan."""
    pack = _pack(run)
    waiting = frozenset(i.unit_id for i in _unknown(pack, own))
    staff = run.reads.teleport()
    cost = expected(staff.maximum - staff.charges) if staff is not None else None
    coins, cap = gold(run), gold_cap(run)
    if record is not None:
        record.gold(coins, cap)
    gold_to = deposit_to(coins, cap, cost or 0)
    view = hands.view()
    stay = (
        waiting
        | junk
        | frozenset(i.unit_id for i in (*pack.items, *pack.in_cube) if i.txt in full and i.txt not in sold_full(full))
    )
    nothing = all(i.unit_id in stay for i in (*loot(pack, own), *pack.in_cube)) and gold_to is None
    try:
        if view is None and not nothing:
            view = _reread(run, hands)
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
            if nothing:
                return full
            LOG.info('Macro: town visit: the stash is not read: the scan, page after page')
            tried = set(sold_full(full))
            pages = Pages()
            unload(run, own, key, tried, stay, gold_to, pages)
            after = _pack(run)
            remaining = [i for i in after.in_cube if i.unit_id not in stay]
            if key is not None and remaining:
                # Inventory junk blocking a cube keeper is moved aside here, before Jamella: one stash walk even
                # with the stash unread (2026-10-18 21:03:47)
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
                # A refusal with the stash unread is a guess, never a full stack: kept carried, not in FULL_FILE
                # (the player, 2026-10-19: "we need to track this correctly")
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
    """The full stacks' materials put down (no vendor buys one)."""
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


# The visit's snapshots (rca/2026-10-18/arch-town-planning.md §4): no clicks, no reads, never raise. The shadow planner
# (townplan.py) that replayed them was removed 2026-10-19 (the player: "delete it"; 87 of 88 matched)


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
    """A snapshot of the visit at `stop` (visitlog.py), the rest as at its `start`; never raises."""
    if not record.active or pack is None:
        return
    try:
        record.note(replace(start, stop=stop, pack=pack, view=view, full=full, misses=misses, at=''))
    except Exception as error:  # never into the visit
        record.failed = True
        LOG.info('Macro: visit snapshot: not made: %s', error)


# Jamella before the stash for a cube keeper stranded by junk: off until the player rules (asked 2026-10-18 15:06)
JAMELLA_FIRST = False


def _stranded(run: Run, hands: Hands, own: frozenset[Cell], junk: frozenset[int], needs: Needs) -> tuple[Carried, ...]:
    """The cube keepers the planned stop leaves in that selling the junk first would let out; none with the stash
    unread."""
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
    """One town visit: Cain, the stash, Jamella, Halbu, the exit, each once and only with something to do. `full`: the
    full stacks last known, for an unread stash; `waited`: a repair may be tried. Mouse mode only. `Abort` from a stop
    that cannot go on."""
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
    # The best copy of a set or unique item is kept (the player, 2026-10-18; copies.py)
    from inventory_tracking.macros.copies import sold

    judged = sold(hands.judge([i for i in carried if i.identified]), visitlog.session_directory())
    junk = frozenset(i.unit_id for i in (*judged, *surplus(carried, stacks)))
    # The player's items and stat keepers are never junk (engine.py `protected`)
    spared = [(i, why) for i in carried if i.unit_id in junk and (why := protected(run, i))]
    if spared:
        LOG.info('Macro: town visit: %s: kept, not sold', ', '.join(f'{_name(i)} ({why})' for i, why in spared))
        junk -= {i.unit_id for i, _why in spared}
    LOG.info('Macro: town visit (%s): %d of the loop\'s items, %d identified at Cain, %d junk; full stacks %d',
             exit.value, len(carried), len(unknown), len(junk), len(stacks))  # fmt: skip
    record = Recorder(visitlog.session_directory())
    start = Snapshot('start', pack, own, needs, exit, view, junk, frozenset(i.unit_id for i in _unknown(pack, own)),
                     stacks)  # fmt: skip
    record.note(start)
    failed, repaired = False, False

    def jamella(stacks: frozenset[int], *, stock: bool) -> bool:
        """3. Jamella (Halbu first at the gold's cap): junk sold, full materials put down, keys bought (`stock`: also
        when nothing is sold and a stock is short). Whether she was visited."""
        nonlocal failed, repaired
        # A full stack's runes are cubed, not sold (the player, 2026-10-18: "cubed, aim to 80 or lower")
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
            # No sale is made near the gold cap: the repair first makes room (2026-10-17 15:33:27)
            with _timed(run, took, 'halbu'):
                failed, repaired = _halbu(run), True
        with _timed(run, took, 'jamella'):
            for passes in range(1 + SELL_PASSES):
                # The cube's junk out and sold as the sales make room (the player: "both from cube and inventory")
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
            left = selling(_pack(run))
            coins, cap = gold(run), gold_cap(run)
            if (
                DROP_CAPPED_JUNK
                and left
                and key is not None
                and coins is not None
                and cap is not None
                and coins + SALE_MOST > cap
            ):
                for item in left:
                    drop_item(run, key, item, 'in town: the gold is at its cap and no sale is made')
        return True

    # Jamella before the stash when a cube keeper gets out only once the junk is sold (JAMELLA_FIRST; history/visit.md).
    # Never near the gold cap: the deposit is the stash's
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
            # Full flawless stacks cubed into perfect gems at the stash, then the stop again for them (no walk)
            made, parked_left = hands.transmute(stacks)
            if made:
                stacks = _stash(run, hands, key, own, junk, needs, stacks, memory, plans=plans)
        # A keeper no page has room for: the stash is full and the loop stops (the player, 2026-10-18: "if stash is
        # full - we need to stop loop"; runner.py reads `Contract.stash_full`)
        homeless = tuple(dict.fromkeys(name for planned in plans for name in named(planned.full)))
        if homeless:
            LOG.info('Macro: stash: full: %s', ', '.join(homeless))
    # 3. Jamella after the stash (again only with something left to sell)
    late = jamella(stacks, stock=not early)
    shop = early or late
    if not repaired and _repair_due(run, waited):
        with _timed(run, took, 'halbu'):
            failed, repaired = _halbu(run), True
    # A key stack out of the free block (the player, 2026-10-18: "we should have 2x4 inventory space")
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
    if junk:
        # Junk on a stash page, by its unit id (a park not taken back, wherever it landed): junk left, a miss
        after = hands.view()
        in_stash = [i for page in (after.pages if after is not None else ()) for i in page.items if i.unit_id in junk]
    # A cube keeper with no way out waits for the next visit, named, not a miss (the player, 2026-10-18: "keeper can
    # wait in cube")
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
    run.say(f'Town: cube {done.cube}, junk left {done.junk_left}, keys {done.keys}')
    return Visited(done, stacks, failed, tuple((stop, took[stop]) for stop in STOPS if stop in took))
