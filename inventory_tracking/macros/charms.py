"""Gheed's Fortune is carry-one: no second is picked up while the player's is carried (routes/andariel-loop-plan.md).

The player, 2026-10-18: "we cannot pickup it while having another gheed charm in our inventory; to pickup another - we
need to go to the shared stash tab and put our current charm there, then go back and pickup another gheed charm. go to
shared stash tab, put new there and bring our's back." In the d2data dump (`uniqueitems.json`) row 359, Gheed's
Fortune, is a Grand Charm (`cm3`) with `carry1` 1001; the Latent Sunder charms that drop (rows 426, 428-432, `cm3` too)
have none. On the ground the two are alike: a unique Grand Charm, its row unread until identified (ItemData +0x34 is
0), so a refused pickup tells it (macros/runner.py `_loop_stopped`).

The player's charm is put on the personal stash page, whose grid the macros read (world.py `Pack.stashed`, grid 6), so
the place it went to is known and it is taken back from there by a Ctrl + click on its cell; a shared page's contents
are not read by the macros: with no room on the personal page the swap is refused (`Abort`), the charm left carried.
The new one goes onto the personal page too (or the next shared one with room: it is the loop's, any place is good).
"""

from inventory_tracking.common import LOG
from inventory_tracking.items.metadata import metadata
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point, room_for
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.stash import (
    PERSONAL_TAB,
    SHARED_TAB,
    STASH_PAGE,
    _tab,
    _until,
    close_stash,
    open_stash,
)
from inventory_tracking.macros.world import Carried, Pack


__all__ = ['GHEEDS_FORTUNE', 'UNIQUE', 'gheeds', 'is_unique_grand_charm', 'put_away', 'take_back']

GHEEDS_FORTUNE = 359  # uniqueitems.txt row (d2data dump, 2026-10-18): `cm3`, carry1 1001
UNIQUE = 7  # ItemData quality


def grand_charm() -> int:
    """The Grand Charm's class (items metadata: code `cm3`)."""
    return next(int(cid) for cid, base in metadata()['bases'].items() if base.get('code') == 'cm3')


def is_unique_grand_charm(txt: int | None, quality: int | None) -> bool:
    return txt == grand_charm() and quality == UNIQUE


def gheeds(pack: Pack, own: frozenset[tuple[int, int, int]]) -> Carried | None:
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


def _pack(run: Run) -> Pack:
    pack = run.carried() if run.carried is not None else None
    if pack is None:
        raise Abort('the inventory is not read')
    return pack


def put_away(run: Run, item: Carried) -> Carried:
    """`item` (the player's Gheed's Fortune) from the inventory onto the personal stash page; where it lies there.
    `Abort` with no room for it there, or when it does not go: it stays carried."""
    pack = _pack(run)
    if pack.stash is None or not room_for(pack.stash, item.size):
        raise Abort("no room on the personal stash page for the player's Gheed's Fortune")
    rect = open_stash(run)
    try:
        _tab(run, rect, PERSONAL_TAB)
        run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(4, 4))
        run.actuator.click('Control_L')
        if not _until(run, lambda p: any(s.unit_id == item.unit_id for s in p.stashed)):
            raise Abort("the player's Gheed's Fortune did not go onto the personal stash page")
    finally:
        close_stash(run)
    placed = next(s for s in _pack(run).stashed if s.unit_id == item.unit_id)
    LOG.info("Macro: charms: the player's Gheed's Fortune from (%d, %d) onto the stash page at (%d, %d)",
             item.x, item.y, placed.x, placed.y)  # fmt: skip
    return placed


def take_back(run: Run, mine: Carried, new: int | None) -> Carried:
    """The new Gheed's Fortune (unit `new`, the loop's) into the stash, and the player's (`mine`, as it lies on the
    personal page) back into the inventory; the player's as it lies there now. `Abort` when the player's does not
    come back (it stays in the stash: the log says where)."""
    rect = open_stash(run)
    try:
        _tab(run, rect, PERSONAL_TAB)
        carried = _pack(run).items
        found = next((i for i in carried if i.unit_id == new), None) if new is not None else None
        if found is not None:
            run.actuator.move(*cell_point(rect, INVENTORY, (found.x, found.y), found.size), scatter=(4, 4))
            run.actuator.click('Control_L')
            if not _until(run, lambda p: all(i.unit_id != new for i in p.items)):
                _tab(run, rect, SHARED_TAB)  # the personal page full: the shared page shown takes it
                run.actuator.move(*cell_point(rect, INVENTORY, (found.x, found.y), found.size), scatter=(4, 4))
                run.actuator.click('Control_L')
                _until(run, lambda p: all(i.unit_id != new for i in p.items))
                _tab(run, rect, PERSONAL_TAB)
        lying = next((s for s in _pack(run).stashed if s.unit_id == mine.unit_id), mine)
        run.actuator.move(*cell_point(rect, STASH_PAGE, (lying.x, lying.y), lying.size), scatter=(4, 4))
        run.actuator.click('Control_L')
        if not _until(run, lambda p: any(i.unit_id == mine.unit_id for i in p.items)):
            raise Abort(
                f"the player's Gheed's Fortune did not come back: it lies on the personal stash page at "
                f'({lying.x}, {lying.y})'
            )
    finally:
        close_stash(run)
    back = next(i for i in _pack(run).items if i.unit_id == mine.unit_id)
    LOG.info("Macro: charms: the player's Gheed's Fortune back in the inventory at (%d, %d)", back.x, back.y)
    return back
