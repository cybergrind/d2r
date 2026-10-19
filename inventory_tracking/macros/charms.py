"""Gheed's Fortune is carry-one: no second is picked up while the player's is carried (routes/andariel-loop-plan.md).

The player, 2026-10-18 13:39-13:41: "picking up another gheed principal algo: go to town; put our own gheed into
SHARED tab; go back and pick new one; go to town, identify; check what is better (magic find roll); keep in own
inventory better one"; "you cannot pickup another gheed if you have another in inventory/private tab". In the d2data
dump (`uniqueitems.json`) row 359, Gheed's Fortune, is a Grand Charm (`cm3`) with `carry1` 1001 and `mag%` 20-40; the
Latent Sunder charms that drop (rows 426, 428-432, `cm3` too) have none. On the ground the two are alike: a unique Grand
Charm, its row unread until identified (ItemData +0x34 is 0), so one left on the ground while the player's is carried
tells it (macros/runner.py `_loop_stopped`).

The legs are the loop's (macros/loop.py SWAP_OUT, GHEED_STASH, SWAP_BACK, GHEED_CHOOSE); here the stash's part:
`park` puts the player's charm onto a shared page with room (the stash as read, world.py `StashView`; each shared page
tried when it is unread), never the personal page, which blocks the pickup as the inventory does; `choose` compares the
two Magic Find rolls (itemstatcost.txt `item_magicbonus`, stat 80) once the new one is identified, the better one
carried at the player's cell, the other on a shared page (a tie keeps the player's).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.items.grid import INVENTORY_SIZE, Grid
from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.stash import SHARED_PRIORITY, STASH_PAGE, _sent, _until, close_stash, open_stash
from inventory_tracking.macros.visit import Remembered, Tally, _show
from inventory_tracking.macros.world import Carried, Pack, StashView


__all__ = [
    'GHEEDS_FORTUNE',
    'MAGIC_FIND',
    'UNIQUE',
    'Parked',
    'candidates',
    'choose',
    'gheeds',
    'is_unique_grand_charm',
    'magic_find',
    'newcomers',
    'park',
]

GHEEDS_FORTUNE = 359  # uniqueitems.txt row (d2data dump, 2026-10-18): `cm3`, carry1 1001, mag% 20-40
UNIQUE = 7  # ItemData quality
# itemstatcost.txt `item_magicbonus` *ID 80 (pricing/raw/game-excel/itemstatcost.txt, third-parties/d2data, read
# 2026-10-18): the "mag%" property of Gheed's Fortune
MAGIC_FIND = 80
GRAND_CHARM_SIZE = (1, 3)

Stats = Callable[[int], Mapping[int, int] | None]  # None: unread
Cell = tuple[int, int, int]


def grand_charm() -> int:
    """The Grand Charm's class (items metadata: code `cm3`)."""
    return next(int(cid) for cid, base in metadata()['bases'].items() if base.get('code') == 'cm3')


def is_unique_grand_charm(txt: int | None, quality: int | None) -> bool:
    return txt == grand_charm() and quality == UNIQUE


def gheeds(pack: Pack, own: frozenset[Cell]) -> Carried | None:
    """The player's own Gheed's Fortune in the inventory (identified, its row read), None without one."""
    return next(
        (
            item
            for item in pack.items
            if (item.txt, item.x, item.y) in own
            and is_unique_grand_charm(item.txt, item.quality)
            and item.identified
            and item.unique == GHEEDS_FORTUNE
        ),
        None,
    )


@dataclass(frozen=True)
class Parked:
    """The player's Gheed's Fortune on a shared stash page while the new one is fetched: its unit, the page it went
    onto (None: not read), the inventory cell it was carried at (the player's, `Loop.own`), its Magic Find (%) as read
    while carried (None unread)."""

    unit_id: int
    page: int | None
    cell: Cell
    magic_find: int | None

    def state(self) -> dict:
        return {'unit': self.unit_id, 'page': self.page, 'cell': list(self.cell), 'magic_find': self.magic_find}

    @classmethod
    def restore(cls, state: object) -> Parked | None:
        """From `state` (a restart's, runner.py `resume`); None when it is not one."""
        try:
            assert isinstance(state, dict)
            txt, x, y = (int(v) for v in state['cell'])
            page, found = state.get('page'), state.get('magic_find')
            return cls(
                int(state['unit']),
                int(page) if page is not None else None,
                (txt, x, y),
                int(found) if found is not None else None,
            )
        except AssertionError, KeyError, TypeError, ValueError:
            return None


def magic_find(stats: Stats | None, unit_id: int) -> int | None:
    """The item's Magic Find roll (%) as memory holds it; None unread (or no such stat: not a Gheed's Fortune)."""
    if stats is None:
        return None
    try:
        found = stats(unit_id)
        return found.get(MAGIC_FIND) if found is not None else None
    except Exception as error:  # a read of memory: never the swap's stop
        LOG.info('Macro: charms: the stats of unit %d are not read: %s', unit_id, error)
        return None


def candidates(pack: Pack, parked: Parked, before: frozenset[int]) -> list[Carried]:
    """The new Gheed's Fortune among the carried items (the inventory and the cube): a unique Grand Charm not carried
    when the player's went away (`before`), unidentified or of Gheed's row."""
    return [
        item
        for item in (*pack.items, *pack.in_cube)
        if is_unique_grand_charm(item.txt, item.quality)
        and item.unit_id != parked.unit_id
        and item.unit_id not in before
        and (not item.identified or item.unique == GHEEDS_FORTUNE)
    ]


def newcomers(pack: Pack, parked: Parked, before: frozenset[int]) -> list[Carried]:
    """The unique Grand Charms in the inventory not carried when the player's went away (`before`) and not of Gheed's
    row as read: a Latent Sunder charm picked up in the swap, or one still unidentified (`choose`'s `others`)."""
    return [
        item
        for item in pack.items
        if is_unique_grand_charm(item.txt, item.quality)
        and item.unit_id != parked.unit_id
        and item.unit_id not in before
        and not (item.identified and item.unique == GHEEDS_FORTUNE)
    ]


def _pack(run: Run) -> Pack:
    pack = run.reads.carried()
    if pack is None:
        raise Abort('the inventory is not read')
    return pack


def _view(run: Run) -> StashView | None:
    return run.reads.stash_view()


def shared_pages(view: StashView | None, size: tuple[int, int]) -> list[int]:
    """The shared pages a block of `size` fits on, in storage priority; every one when the stash is unread."""
    if view is None:
        return list(SHARED_PRIORITY)
    fitting = {page.index for page in view.pages if page.index >= 1 and Grid(page.rows).has_room(size)}
    return [page for page in SHARED_PRIORITY if page in fitting]


def _onto_shared(run: Run, rect, item: Carried, tally: Tally, pages: Sequence[int]) -> int | None:
    """`item` from the inventory onto the first of the shared `pages` that takes it, each shown and Ctrl + clicked; the
    page it lies on (as read again, else the page shown), None when none took it. `Abort` when it went onto the pointer
    (put back first) or onto the personal page (taken back first: it would block a pickup there too)."""
    for page in pages:
        _show(run, rect, page, tally)
        run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(4, 4))
        run.actuator.click('Control_L')
        if not _sent(run, rect, item, INVENTORY, lambda p: all(i.unit_id != item.unit_id for i in p.items)):
            LOG.info("Macro: charms: shared page %d refused the Gheed's Fortune (unit %d)", page, item.unit_id)
            continue
        view = _view(run)
        landed = view.page_of(item.unit_id) if view is not None else None
        if landed == 0:
            _take(run, rect, tally, item.unit_id, None)
            raise Abort("the Gheed's Fortune went onto the personal stash page, not a shared one: taken back")
        if landed is None and view is not None:
            LOG.warning("Macro: charms: the Gheed's Fortune (unit %d) left the inventory and is read on no page: "
                        'shared page %d was shown', item.unit_id, page)  # fmt: skip
        return landed if landed is not None else page
    return None


def _lying(view: StashView | None, unit_id: int) -> tuple[int, Carried] | None:
    """The page and cell the stash item `unit_id` lies at, as read; None when it is not read there."""
    for page in view.pages if view is not None else ():
        for item in page.items:
            if item.unit_id == unit_id:
                return page.index, item
    return None


def _take(run: Run, rect, tally: Tally, unit_id: int, page: int | None) -> Carried:
    """The stash item `unit_id` back into the inventory by a Ctrl + click on its cell, its page shown; as it lies there
    now. `Abort` when its cell is not read or it does not come (it stays in the stash: the log says where)."""
    found = _lying(_view(run), unit_id)
    if found is None:
        where = f'shared page {page}' if page is not None else 'the stash'
        raise Abort(f"the player's Gheed's Fortune (unit {unit_id}) is not read on {where}: it stays there")
    index, lying = found
    _show(run, rect, index, tally)
    run.actuator.move(*cell_point(rect, STASH_PAGE, (lying.x, lying.y), lying.size), scatter=(4, 4))
    run.actuator.click('Control_L')
    if not _until(run, lambda p: any(i.unit_id == unit_id for i in p.items)):
        raise Abort(
            f"the player's Gheed's Fortune did not come back: it lies on stash page {index} at ({lying.x}, {lying.y})"
        )
    return next(i for i in _pack(run).items if i.unit_id == unit_id)


def _free_for(pack: Pack, item: Carried, at: tuple[int, int]) -> bool:
    """Whether `item`'s block at `at` is free in the inventory, the item's own cells counted free."""
    others = (i for i in pack.items if i.unit_id != item.unit_id)
    return Grid.from_items(others, INVENTORY_SIZE).fits(at, item.size)


def settle(run: Run, rect, item: Carried, cell: Cell) -> Carried:
    """`item` (carried, the inventory open) moved to the player's cell `cell` when it is elsewhere and that block is
    free: taken up by a click and put down by a click on the block's middle; as it lies after. Where it does not go it
    is put back where it was, and stays there (the cell then is the player's: `Loop.own`)."""
    at = (cell[1], cell[2])
    if (item.x, item.y) == at or not _free_for(_pack(run), item, at):
        return item
    run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(3, 3))
    run.actuator.click()
    if not _until(run, lambda p: p.pointer == item.unit_id):
        if _pack(run).pointer is not None:
            run.actuator.click()  # something else taken up: put down where it was, the pointer not moved
            _until(run, lambda p: p.pointer is None)
        LOG.info("Macro: charms: the Gheed's Fortune was not taken up to move it to (%d, %d)", *at)
        return next((i for i in _pack(run).items if i.unit_id == item.unit_id), item)
    run.actuator.move(*cell_point(rect, INVENTORY, at, item.size), scatter=(3, 3))
    run.actuator.click()
    if not _until(run, lambda p: p.pointer is None and any(i.unit_id == item.unit_id for i in p.items)):
        run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(3, 3))
        run.actuator.click()
        if not _until(run, lambda p: p.pointer is None):
            raise Abort("the Gheed's Fortune stays on the pointer: it went neither to the player's cell nor back")
    now = next((i for i in _pack(run).items if i.unit_id == item.unit_id), item)
    LOG.info("Macro: charms: the Gheed's Fortune moved from (%d, %d) to (%d, %d) (the player's cell (%d, %d))",
             item.x, item.y, now.x, now.y, *at)  # fmt: skip
    return now


def _make_way(run: Run, rect, tally: Tally, others: Sequence[Carried]) -> None:
    """`others` onto shared pages while the inventory has no Grand Charm's block free for the player's to come back to:
    the swap made with no 1 x 3 free but the player's own cell (the player, 2026-10-18 16:50: "refused grand charm -
    should cause a trip"), which the new charm took. A unique Grand Charm is a keeper: the stash is where a visit puts
    it too."""
    for other in others:
        pack = _pack(run)
        if pack.inventory.has_room(GRAND_CHARM_SIZE):
            return
        lying = next((i for i in pack.items if i.unit_id == other.unit_id), None)
        if lying is None:
            continue
        page = _onto_shared(run, rect, lying, tally, shared_pages(_view(run), lying.size))
        LOG.info("Macro: charms: the new unique Grand Charm (unit %d, %s) from (%d, %d) onto shared page %s: the "
                 "player's Gheed's Fortune comes back to its block", lying.unit_id,
                 f'unique row {lying.unique}' if lying.identified else 'unidentified', lying.x, lying.y,
                 page)  # fmt: skip


def park(run: Run, item: Carried, stats: Stats | None, memory: Remembered | None = None) -> Parked:
    """`item`, the player's Gheed's Fortune, from the inventory onto a shared stash page with room (the stash open, at
    the stash in sight); where it lies. `Abort` when no shared page has room or none takes it: it stays carried."""
    found = magic_find(stats, item.unit_id)
    pages = shared_pages(_view(run), item.size)
    if not pages:
        raise Abort("no shared stash page has room for the player's Gheed's Fortune: it stays carried")
    rect = open_stash(run)
    try:
        page = _onto_shared(run, rect, item, Tally(memory if memory is not None else Remembered()), pages)
    finally:
        close_stash(run)
    if page is None:
        raise Abort(f"no shared page of {pages} took the player's Gheed's Fortune: it stays carried")
    LOG.info("Macro: charms: the player's Gheed's Fortune (unit %d, magic find %s%%) from the inventory at (%d, %d) "
             'onto shared page %d', item.unit_id, found if found is not None else '?', item.x, item.y,
             page)  # fmt: skip
    return Parked(item.unit_id, page, (item.txt, item.x, item.y), found)


def choose(
    run: Run,
    parked: Parked,
    new: Carried | None,
    stats: Stats | None,
    memory: Remembered | None = None,
    others: Sequence[Carried] = (),
) -> Carried:
    """The better of the player's Gheed's Fortune (`parked`) and the `new` one (identified, carried; None: no new one
    of Gheed's row) by their Magic Find rolls, a tie the player's: the better carried at the player's cell where it is
    free, the other on a shared page (the player's old one stays there only when the new one is better); the carried
    one, the player's from now on. `others` (`newcomers`: a Latent Sunder charm picked up in the swap) go onto a shared
    page when the player's has no block in the inventory to come back to. `Abort` when a move fails (the log says where
    each lies)."""
    mine = magic_find(stats, parked.unit_id)
    mine = mine if mine is not None else parked.magic_find
    theirs = magic_find(stats, new.unit_id) if new is not None else None
    rect = open_stash(run)
    tally = Tally(memory if memory is not None else Remembered())
    try:
        if new is not None and theirs is not None and mine is not None and theirs > mine:
            kept = settle(run, rect, new, parked.cell)
            LOG.info("Macro: charms: the new Gheed's Fortune is better: magic find %d%% against the player's %d%%: it "
                     "stays carried at (%d, %d) as the player's; the player's old one stays on shared page %s",
                     theirs, mine, kept.x, kept.y, parked.page)  # fmt: skip
            return kept
        if new is not None:
            if theirs is None or mine is None:
                LOG.info("Macro: charms: a magic find roll is unread (the player's %s, the new one's %s): the "
                         "player's is kept", mine, theirs)  # fmt: skip
            pages = shared_pages(_view(run), new.size)
            page = _onto_shared(run, rect, new, tally, pages) if pages else None
            if page is None:
                raise Abort("no shared page took the new Gheed's Fortune: the player's stays in the stash")
            LOG.info("Macro: charms: the player's Gheed's Fortune is kept: magic find %s%% against the new one's %s%%; "
                     'the new one (unit %d) onto shared page %d', mine if mine is not None else '?',
                     theirs if theirs is not None else '?', new.unit_id, page)  # fmt: skip
        else:
            LOG.info("Macro: charms: no new Gheed's Fortune to compare: the player's back")
        _make_way(run, rect, tally, others)
        back = _take(run, rect, tally, parked.unit_id, parked.page)
        back = settle(run, rect, back, parked.cell)
    finally:
        close_stash(run)
    LOG.info("Macro: charms: the player's Gheed's Fortune back in the inventory at (%d, %d)", back.x, back.y)
    return back
