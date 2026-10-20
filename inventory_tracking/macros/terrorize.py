"""A Worldstone Shard used in town: one shard out of the stash's Materials tab into the inventory, a right click on it,
its act terrorized for the game (routes/act-terrorize-plan.md §3 S1-S4; rca/2026-10-20/act-terrorize-findings.md).

The player, 2026-10-20 ~18:50: "terrorize with worldstone shards whole act and go whole act, zone by zone ... right now
let's assume that we can use any stone with 90+ quantity". The request `terrorize` (request.py) makes it by hand; the
act loop (macros/actloop.py) makes it at a game's start.

- `choose_shard`: pure. The most-held shard whose Materials-tab stack is SHARD_FLOOR or more, ties to the cheaper; an
  act asked for (the Act 4 kind) takes only its shard. Never one from a stack under the floor.
- `terrorize`: the clicks, behind CLICKS (off until the player's in-game test answers the findings' §6 checks 2-4:
  which click takes one shard out, whether the right click works with the stash open, whether one is consumed, whether
  the client's terror list names the act). With CLICKS off it reads and says what it would do, and clicks nothing.
- Confirmed (`Used.confirmed`): the shard's unit gone from the carried items and the stack one lower; `listed`
  whether the tracker then reads every grouped level of the act terrorized (None: not looked at).
"""

from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack, StashView
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.storage import MATERIALS_TAB
from inventory_tracking.macros.act import until
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import INVENTORY, cell_point, close, open_inventory, rune_slot
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.stash import open_stash, tab_point
from inventory_tracking.macros.waypoint import panel_point
from inventory_tracking.native.layout import TOWN_IDS
from inventory_tracking.routes.tz_groups import manual_zone


# Item class -> the act its right click terrorizes (misc.txt xa1-xa5 `calc1`; the classes from
# items/data/item_metadata.json, checked 2026-10-20): Western, Eastern, Southern, Deep, Northern Worldstone Shard
SHARDS = {674: 1, 675: 2, 676: 3, 677: 4, 678: 5}
# A shard is used only from a stack of this many or more (the player, 2026-10-20: "any stone with 90+ quantity")
SHARD_FLOOR = 90
# Ties to the cheaper (Traderie SC/NL/PC asks of 2026-09-18: Western 0.03, Eastern 0.03, Southern 0.05, Deep 0.12,
# Northern 0.17 Ist; findings §3)
SHARD_ORDER = (674, 675, 676, 677, 678)
# The clicks (take out, use): False until the player's in-game test (findings §6 checks 2-4). False: the request reads
# the stash, chooses and says, and clicks nothing
CLICKS = False
# How one shard leaves its stack for the inventory (findings §6 check 2, unknown until the test): CTRL a Ctrl + left
# click on the stack; CURSOR a plain left click (one onto the pointer), then a click on a free inventory cell
CTRL, CURSOR = 'ctrl', 'cursor'
TAKE_OUT = CTRL
# The right click made with the stash still open (check 3); False: the stash closed, the inventory opened first
USE_WITH_STASH_OPEN = True
ITEM_SECONDS = 1.5  # for a shard to land in the inventory, or to be gone after its right click
# For the tracker to read the act's levels terrorized after the use (findings §1 #13: the client's list; whether it
# names a shard's act is check 4)
CONFIRM_SECONDS = 5.0
SLOT_SCATTER = (8, 8)
TAB_SETTLE = 0.4


@dataclass(frozen=True)
class Used:
    """A shard's use: its class, act, the stack before and after (None unread), whether its unit is gone from the
    carried items, and whether the act's grouped levels read terrorized after (None: not looked at)."""

    shard: int
    act: int
    before: int
    after: int | None
    gone: bool
    listed: bool | None = None

    @property
    def confirmed(self) -> bool:
        """The shard used: gone from the inventory and its stack one lower (findings §1 #4: one shard a use)."""
        return self.gone and self.after == self.before - 1


def name_of(shard: int) -> str:
    base = metadata()['bases'].get(str(shard))
    return base['name'] if base is not None else f'item {shard}'


def choose_shard(view: StashView | None, act: int | None = None) -> int | None:
    """The shard to use: of `act`'s only when one is asked for, else any; its stack SHARD_FLOOR or more; the most-held
    first, ties by SHARD_ORDER (the cheaper). None with the stash unread or no stack at the floor."""
    if view is None:
        return None
    wanted = [shard for shard in SHARD_ORDER if act is None or SHARDS[shard] == act]
    held = [shard for shard in wanted if view.count(shard) >= SHARD_FLOOR]
    if not held:
        return None
    return max(held, key=lambda shard: (view.count(shard), -SHARD_ORDER.index(shard)))


def stacks_said(view: StashView | None) -> str:
    """`Western 97, Eastern 12, …` for the log; 'unread' with no stash read."""
    if view is None:
        return 'the stash unread'
    return ', '.join(f'{name_of(shard).split()[0]} {view.count(shard)}' for shard in SHARD_ORDER)


def terrorize(
    run: Run,
    inventory_key: str | None,
    act: int | None = None,
    terrorized: Callable[[int], bool | None] | None = None,
) -> Used | None:
    """One shard (`choose_shard`, of `act` when given) taken out of the Materials tab and right-clicked, in town; the
    use, or None when nothing was used (no shard at the floor, CLICKS off, a click that did not do what it should).
    `terrorized`: the tracker's read (routes/progress.py `wanted`), looked at for CONFIRM_SECONDS after. Panels are
    closed after, through a cancel too. `Abort` out of town or with no game window."""
    world = run.world()
    player = world.player
    if player is None or player.area not in TOWN_IDS:
        raise Abort('a Worldstone Shard is used in town')
    view = run.reads.stash_view()
    shard = choose_shard(view, act)
    wanted = f'act {act}' if act is not None else 'any act'
    if shard is None:
        LOG.info('Macro: terrorize: no shard for %s at %d or more (%s)', wanted, SHARD_FLOOR, stacks_said(view))
        run.say(f'Terrorize: no shard at {SHARD_FLOOR}+')
        return None
    assert view is not None
    shard_act, before = SHARDS[shard], view.count(shard)
    if not CLICKS:
        LOG.info('Macro: terrorize: %s chosen for act %d (stack %d; %s): the clicks are off (terrorize.CLICKS) until '
                 "the player's test", name_of(shard), shard_act, before, stacks_said(view))  # fmt: skip
        run.say(f'Terrorize: {name_of(shard)} ({before}) would be used: clicks off')
        return None
    if inventory_key is None:
        raise Abort('no inventory key read')
    try:
        rect = run.actuator.keys.focused_window_rect() if 'stash' in world.open_panels else open_stash(run)
        if rect is None:
            raise Abort('no game window')
        taken = _take_out(run, rect, shard)
        if taken is None:
            return None
        if not USE_WITH_STASH_OPEN:
            close(run, ('stash', 'inventory', 'cube'))
            open_inventory(run, inventory_key)
        run.actuator.move(*cell_point(rect, INVENTORY, (taken.x, taken.y), taken.size), scatter=(4, 4))
        run.actuator.tap('Button3')

        def gone_from(p: Pack, unit: int = taken.unit_id) -> bool:
            return all(i.unit_id != unit for i in p.items)

        gone = until(run, gone_from, ITEM_SECONDS, read=run.reads.carried)
    finally:
        close(run, ('stash', 'inventory', 'cube'))
    after_view = run.reads.stash_view()
    used = Used(shard, shard_act, before, after_view.count(shard) if after_view is not None else None, gone is not None)
    if not used.gone:
        LOG.info('Macro: terrorize: the right click on the %s at (%d, %d) did not use it: it stays carried',
                 name_of(shard), taken.x, taken.y)  # fmt: skip
        run.say(f'Terrorize: the {name_of(shard)} was not used')
        return used
    listed = _listed(run, shard_act, terrorized)
    used = Used(used.shard, used.act, used.before, used.after, used.gone, listed)
    LOG.info(
        'Macro: terrorize: %s used for act %d (stack %d -> %s)%s; the act %s',
        name_of(shard), shard_act, before, used.after if used.after is not None else 'unread',
        '' if used.confirmed else ': the stack is not one lower',
        'not looked at' if listed is None else 'read terrorized' if listed else 'not read terrorized',
    )  # fmt: skip
    run.say(f'Terrorize: act {shard_act} by a {name_of(shard)}')
    return used


def _take_out(run: Run, rect: tuple[int, int, int, int], shard: int) -> Carried | None:
    """One `shard` from its Materials-tab stack into the inventory by TAKE_OUT (the stash open); the shard carried, or
    None (said) when no new one landed there. A shard left on the pointer is put back onto its stack."""
    slot = rune_slot(shard)  # the resource tabs' slots, the Materials tab's too (build_rune_cube.py)
    pack = run.reads.carried()
    if slot is None or pack is None:
        LOG.info('Macro: terrorize: %s', 'no Materials-tab slot for the shard' if slot is None else 'nothing read')
        return None
    held = {item.unit_id for item in pack.items}
    run.actuator.move(*panel_point(rect, *tab_point(MATERIALS_TAB)), scatter=(15, 5))
    run.actuator.click()
    run.pace.sleep(TAB_SETTLE)
    run.actuator.move(*panel_point(rect, *slot), scatter=SLOT_SCATTER)
    if TAKE_OUT == CTRL:
        run.actuator.click('Control_L')
    else:
        run.actuator.click()
        lifted = until(run, lambda p: p.pointer is not None, ITEM_SECONDS, read=run.reads.carried)
        spot = pack.inventory.first_spot((1, 1))
        if lifted is None or spot is None:
            _back(run, rect, slot)
            LOG.info(
                'Macro: terrorize: %s', 'no shard onto the pointer' if lifted is None else 'no free inventory cell'
            )
            return None
        run.actuator.move(*cell_point(rect, INVENTORY, spot), scatter=(4, 4))
        run.actuator.click()

    def landed(p: Pack) -> bool:
        return any(i.txt == shard and i.unit_id not in held and i.unit_id not in p.cube_items for i in p.items)

    now = until(run, landed, ITEM_SECONDS, read=run.reads.carried)
    if now is None:
        _back(run, rect, slot)
        LOG.info('Macro: terrorize: a %s click on the %s stack put no shard in the inventory', TAKE_OUT, name_of(shard))
        run.say('Terrorize: no shard taken out')
        return None
    return next(i for i in now.items if i.txt == shard and i.unit_id not in held and i.unit_id not in now.cube_items)


def _back(run: Run, rect: tuple[int, int, int, int], slot: tuple[float, float]) -> None:
    """Whatever the take-out left on the pointer put back: a click on the stack it came from."""
    pack = run.reads.carried()
    if pack is not None and pack.pointer is not None:
        run.actuator.move(*panel_point(rect, *slot), scatter=SLOT_SCATTER)
        run.actuator.click()
        until(run, lambda p: p.pointer is None, ITEM_SECONDS, read=run.reads.carried)


def _listed(run: Run, act: int, terrorized: Callable[[int], bool | None] | None) -> bool | None:
    """Whether every grouped level of `act` reads terrorized within CONFIRM_SECONDS; None with no read handed."""
    zone = manual_zone(act)
    if terrorized is None or zone is None:
        return None
    return (
        until(run, lambda _: all(terrorized(area) for area in zone.core), CONFIRM_SECONDS, read=lambda: True)
        is not None
    )
