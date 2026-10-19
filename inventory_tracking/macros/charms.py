"""Gheed's Fortune is carry-one: no second is picked up while the player's is carried (routes/andariel-loop-plan.md).
"You cannot pickup another gheed if you have another in inventory/private tab" (the player, 2026-10-18).

On the ground Gheed's (uniqueitems row 359, `cm3`, carry1) and the Latent Sunder charms are alike: a unique Grand Charm,
its row unread until identified, so one left on the ground while the player's is carried tells it (runner.py
`_loop_stopped`). The legs are the loop's (loop.py SWAP_OUT, GHEED_STASH, SWAP_BACK, GHEED_CHOOSE); here the stash's
part: `park` puts the player's charm on a shared page (never the personal one, which blocks the pickup too); `choose`
keeps the better Magic Find roll at the player's cell, the other on a shared page (a tie keeps the player's).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack, StashView
from inventory_tracking.items.grid import INVENTORY_SIZE, Grid
from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.stash import SHARED_PRIORITY, STASH_PAGE, _sent, _until, close_stash, open_stash
from inventory_tracking.macros.visit import Remembered, Tally, _show


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
# itemstatcost.txt `item_magicbonus` (game-excel, d2data, 2026-10-18): Gheed's "mag%"
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
    """The player's Gheed's Fortune parked on a shared page (None: unread) while the new one is fetched; `cell` the
    player's inventory cell (`Loop.own`); `magic_find` as read while carried."""

    unit_id: int
    page: int | None
    cell: Cell
    magic_find: int | None

    def state(self) -> dict:
        return {'unit': self.unit_id, 'page': self.page, 'cell': list(self.cell), 'magic_find': self.magic_find}

    @classmethod
    def restore(cls, state: object) -> Parked | None:
        """From a restart's `state`; None when malformed."""
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
    """The item's Magic Find roll (%); None unread or absent."""
    if stats is None:
        return None
    try:
        found = stats(unit_id)
        return found.get(MAGIC_FIND) if found is not None else None
    except Exception as error:  # a read of memory: never the swap's stop
        LOG.info('Macro: charms: the stats of unit %d are not read: %s', unit_id, error)
        return None


def candidates(pack: Pack, parked: Parked, before: frozenset[int]) -> list[Carried]:
    """Carried unique Grand Charms new since `before`, unidentified or of Gheed's row."""
    return [
        item
        for item in (*pack.items, *pack.in_cube)
        if is_unique_grand_charm(item.txt, item.quality)
        and item.unit_id != parked.unit_id
        and item.unit_id not in before
        and (not item.identified or item.unique == GHEEDS_FORTUNE)
    ]


def newcomers(pack: Pack, parked: Parked, before: frozenset[int]) -> list[Carried]:
    """Inventory unique Grand Charms new since `before` and not read as Gheed's (`choose`'s `others`)."""
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
    """Ctrl+click `item` onto the first shared page of `pages` that takes it; the page, None if none did. `Abort`
    (taken back first) when it lands on the personal page: it would block a pickup there too."""
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
    """The page and item of stash unit `unit_id`; None when not read."""
    for page in view.pages if view is not None else ():
        for item in page.items:
            if item.unit_id == unit_id:
                return page.index, item
    return None


def _take(run: Run, rect, tally: Tally, unit_id: int, page: int | None) -> Carried:
    """Ctrl+click stash unit `unit_id` back into the inventory; the item as it lies now. `Abort` when unread or it
    does not come."""
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
    """Whether `item`'s block at `at` is free, its own cells counted free."""
    others = (i for i in pack.items if i.unit_id != item.unit_id)
    return Grid.from_items(others, INVENTORY_SIZE).fits(at, item.size)


def settle(run: Run, rect, item: Carried, cell: Cell) -> Carried:
    """Move carried `item` to the player's `cell` when that block is free; the item as it lies after. If it does not
    go it is put back where it was."""
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
    """Stash `others` until a Grand Charm block is free for the player's to come back to ("refused grand charm -
    should cause a trip", the player, 2026-10-18)."""
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
    """Put the player's Gheed's Fortune on a shared page with room (stash in sight); where it lies. `Abort` when
    none takes it: it stays carried."""
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
    """Carry the better Magic Find roll of `parked` and `new` (a tie keeps the player's) at the player's cell, the
    other on a shared page; the carried one. `others` are stashed when the player's has no block to come back to.
    `Abort` when a move fails."""
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
