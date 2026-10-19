"""The loop's loot into the Horadric Cube between games, by mouse (routes/lower-kurast-loop-plan.md phase 9; the
player, 2026-10-16: "we can move faster items to cube - open and ctrl+click on item"). Also the cube's other inventory
work: key arrangement, drops for room, unpacking for the stash, gem and rune transmutes.

Only the loop's items move (not the player's `own`, never KEPT); each move is checked in memory, panels closed after,
and every reason nothing moved is logged. Click points come from the game's layout files
(`playerinventoryoriginallayouthd.json`, `horadriccubelayouthd.json`, `_profilehd.json`, read 2026-10-16; a layout
unit is 1/2160 of the window height), checked against a screenshot within 2 pixels.
"""

import functools
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.items.grid import CUBE_SIZE, Grid
from inventory_tracking.items.metadata import item_base, metadata
from inventory_tracking.macros.act import until
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run, protected
from inventory_tracking.macros.pickmode import MAGIC, RARE, SKILLED


__all__ = [
    'KEPT',
    'Move',
    'RuneRecipe',
    'loot',
    'overflow',
    'own_of',
    'perfect_of',
    'plan',
    'roomed',
    'rune_recipe',
    'rune_slot',
    'stash',
    'stash_transmute',
    'transmute',
    'unpack',
]

REFERENCE_HEIGHT = 2160
CELL = 98  # $ItemCellSize
INVENTORY = ((1.0, 0.397), (-1394, -651), (93, 897))  # anchor, panel origin, grid origin
CUBE = ((0.0, 0.397), (236, -651), (431, 534))
CUBE_CLASS = 564  # Horadric Cube (items metadata, 2026-10-16)
# Never moved: the cube, the tomes, the keys (items metadata: Horadric Cube, Tome of Town Portal, Tome of Identify, Key)
KEPT = frozenset((CUBE_CLASS, 533, 534, 558))
PANEL_SECONDS = 1.5  # for a panel to open or close
ITEM_SECONDS = 1.0  # for an item to leave a grid or land in one
RETRY_PAUSE = 0.3  # seconds before an item that did not come out is clicked again
# A Grand Charm's block (across, down), the tallest sure valuable: room is a block, not a cell count (9 cells free in
# pieces left one on the ground, 2026-10-17 21:00:03)
SURE_BLOCK = (1, 3)
DROP_POINT = (0.3, 0.5)  # the ground left of the inventory's panel: what the pointer holds falls at the feet
# With the cube's panel open too: the ground between the two panels, below the character
PARK_POINT = (0.5, 0.7)

Move = tuple[Carried, tuple[int, int]]  # an item and the cube's cell its top-left goes to
# The cube's Transmute button's top-left in `$LeftPanelRect` (`horadriccubelayouthd.json` "convert", 2026-10-18),
# clicked TRANSMUTE_INSIDE units in
TRANSMUTE = (520, 969)
TRANSMUTE_INSIDE = 35
GEMS_A_TRANSMUTE = 3  # the cube's recipe: three flawless gems of a kind into one perfect gem of it
TRANSMUTE_SECONDS = 1.5  # for the perfect gem to show in the cube after the click


def own_of(items: Iterable[Carried]) -> frozenset[tuple[int, int, int]]:
    """The inventory as the player keeps it: each item's class and cell."""
    return frozenset((item.txt, item.x, item.y) for item in items)


def roomed(pack: Pack) -> Pack:
    """`pack` with a carried cube whose unread grid is taken as empty (an empty cube's grid is not read)."""
    if pack.cube is not None or all(item.txt != CUBE_CLASS for item in pack.items):
        return pack
    return replace(pack, cube=Grid.empty(CUBE_SIZE))


def overflow(pack: Pack, own: frozenset[tuple[int, int, int]]) -> bool:
    """Whether some of the loop's items in `pack` fit nowhere in the cube."""
    pack = roomed(pack)
    return len(plan(pack, own)) < len(loot(pack, own))


def loot(pack: Pack, own: frozenset[tuple[int, int, int]]) -> list[Carried]:
    """The loop's items in `pack`: neither the player's (`own`) nor KEPT."""
    return [item for item in pack.items if item.txt not in KEPT and (item.txt, item.x, item.y) not in own]


def plan(pack: Pack, own: frozenset[tuple[int, int, int]]) -> list[Move]:
    """The loop's items in `pack` and the cube cell each goes to, each in the first free block that fits: larger
    first, or smaller first where that places more (smaller first alone left a 2 x 2 out of an empty cube,
    2026-10-17)."""
    if pack.cube is None:
        return []
    items = loot(pack, own)
    larger = _placed(pack.cube, sorted(items, key=lambda i: (-i.size[0] * i.size[1], -i.size[1], i.y, i.x)))
    smaller = _placed(pack.cube, sorted(items, key=lambda i: (i.size[0] * i.size[1], i.y, i.x)))
    return larger if len(larger) >= len(smaller) else smaller


def _placed(rows: Sequence[str], items: Sequence[Carried]) -> list[Move]:
    """`items` in their order, each into the first free block of `rows` that fits it."""
    moves: list[Move] = []
    grid = Grid(rows)
    for item in items:
        spot = grid.first_spot(item.size)
        if spot is not None:
            moves.append((item, spot))
            grid = grid.take(spot, item.size)
    return moves


KEY_CLASS = 558  # Key (items metadata, 2026-10-16; macros/shop.py KEY)


# The largest item's cells (an armour, a polearm): the room a session leaves (the player, 2026-10-18)
BIG_BLOCK = (2, 4)


def keys_move(pack: Pack, size: tuple[int, int] = BIG_BLOCK) -> Move | None:
    """A key stack and the free cell to move it to that frees a block of `size`, else grows the largest free block
    most; None when no move does ("move key two cells left to make continuous 2x4 space", the player, 2026-10-17).
    A block of `size` ranks first: a 3 x 3 counted larger than the only 2 x 4 once (2026-10-18 12:36)."""
    rows = pack.inventory

    def score(lines: Grid) -> tuple[bool, int]:
        return lines.has_room(size), lines.largest_block()

    best, found = score(rows), None
    for key in (item for item in pack.items if item.txt == KEY_CLASS and item.size == (1, 1)):
        without = Grid(
            ''.join('.' if (col, row) == (key.x, key.y) else cell for col, cell in enumerate(line))
            for row, line in enumerate(rows)
        )
        for y, line in enumerate(without):
            for x, cell in enumerate(line):
                if cell != '.' or (x, y) == (key.x, key.y):
                    continue
                block = score(without.take((x, y), (1, 1)))
                if block > best:
                    best, found = block, (key, (x, y))
    return found


def arrange_keys(run: Run, inventory_key: str) -> bool:
    """Move a key stack as `keys_move` says, put back if it does not land; whether it moved. Mouse mode only; the
    panels closed after."""
    rect = run.actuator.keys.focused_window_rect()
    pack = run.reads.carried()
    move = keys_move(pack) if pack is not None else None
    if move is None or rect is None or run.pad is not None:
        return False
    key, (x, y) = move
    moved = False
    try:
        open_inventory(run, inventory_key)
        run.actuator.move(*cell_point(rect, INVENTORY, (key.x, key.y)), scatter=(4, 4))
        run.actuator.click()
        if not _until(run, lambda p: p.pointer == key.unit_id):
            now = run.reads.carried()
            if now is not None and now.pointer is not None:
                run.actuator.click()  # something else taken up: put down where it was, the pointer not moved
                _until(run, lambda p: p.pointer is None)
            LOG.info('Macro: inventory: the keys at (%d, %d) were not taken up', key.x, key.y)
            return False
        for at in ((x, y), (key.x, key.y)):  # its new cell, else back where it was
            run.actuator.move(*cell_point(rect, INVENTORY, at), scatter=(4, 4))
            run.actuator.click()
            if _until(run, lambda p, a=at: p.pointer is None and any(
                i.unit_id == key.unit_id and (i.x, i.y) == a for i in p.items
            )):  # fmt: skip
                moved = at == (x, y)
                break
        else:
            LOG.warning('Macro: inventory: the keys are still on the pointer')
    finally:
        if 'inventory' in run.world().open_panels:
            run.actuator.tap('Escape')
            run.seen(lambda w: 'inventory' not in w.open_panels, PANEL_SECONDS)
            run.actuator.rebase()
    LOG.info(
        'Macro: inventory: the keys %s (%d, %d) to (%d, %d)', 'moved' if moved else 'not moved', key.x, key.y, x, y
    )
    return moved


def cells(item: Carried) -> int:
    return item.size[0] * item.size[1]


def droppable(pack: Pack, own: frozenset[tuple[int, int, int]], size: tuple[int, int]) -> Carried | None:
    """The smallest of the loop's unidentified identify candidates (pickmode.py `candidate`) whose cells free a block
    of `size`; None where none does, or the block is free already."""
    if pack.inventory.has_room(size):
        return None
    found = [
        item
        for item in loot(pack, own)
        if not item.identified
        and item.quality in (MAGIC, RARE)
        and (base := item_base(item.txt)) is not None
        and base['type'] in SKILLED
        and replace(pack, items=tuple(i for i in pack.items if i is not item)).inventory.has_room(size)
    ]
    return min(found, key=cells) if found else None


def drop_for(
    run: Run, inventory_key: str, own: frozenset[tuple[int, int, int]], size: tuple[int, int]
) -> Carried | None:
    """Drop the item `droppable` names, for a sure valuable with no block of `size`, after the cube took what it
    could. The item dropped, or None. Mouse mode only; the panels closed after."""
    pack = run.reads.carried()
    item = droppable(pack, own, size) if pack is not None else None
    if item is None:
        return None
    return item if drop_item(run, inventory_key, item, f'for a {size[0]}x{size[1]} block') else None


def drop_item(run: Run, inventory_key: str, item: Carried, why: str) -> bool:
    """Drop the inventory's `item` at the character's feet, put back if it does not fall; whether it fell. Never a
    protected item. Mouse mode only; the panels closed after."""
    if spared := protected(run, item):
        LOG.info('Macro: inventory: %s (%d) at (%d, %d) is %s: never dropped', item.txt, item.unit_id, item.x, item.y,
                 spared)  # fmt: skip
        return False
    rect = run.actuator.keys.focused_window_rect()
    if rect is None or run.pad is not None:
        return False
    dropped = False
    try:
        open_inventory(run, inventory_key)
        run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(4, 4))
        run.actuator.click()
        if not _until(run, lambda p: p.pointer == item.unit_id):
            now = run.reads.carried()
            if now is not None and now.pointer is not None:
                run.actuator.click()  # something else taken up: put down where it was, the pointer not moved
                _until(run, lambda p: p.pointer is None)
            return False
        run.actuator.move(*DROP_POINT, scatter=(4, 4))
        run.actuator.click()
        dropped = _until(run, lambda p: p.pointer is None and all(i.unit_id != item.unit_id for i in p.items))
        if not dropped:
            run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(4, 4))
            run.actuator.click()
            _until(run, lambda p: p.pointer is None)
    finally:
        if 'inventory' in run.world().open_panels:
            run.actuator.tap('Escape')
            run.seen(lambda w: 'inventory' not in w.open_panels, PANEL_SECONDS)
            run.actuator.rebase()
    LOG.info('Macro: inventory: %s (%d) at (%d, %d) %s %s',
             item.txt, item.unit_id, item.x, item.y, 'dropped' if dropped else 'not dropped', why)  # fmt: skip
    return dropped


def cell_point(
    rect: tuple[int, int, int, int], grid: tuple, at: tuple[int, int], size: tuple[int, int] = (1, 1)
) -> tuple[float, float]:
    """The window fraction of the middle of a block of `size` cells at `at` in the grid (`INVENTORY`, `CUBE`)."""
    (anchor_x, anchor_y), (panel_x, panel_y), (grid_x, grid_y) = grid
    width, height = rect[2], rect[3]
    scale = height / REFERENCE_HEIGHT
    x = panel_x + grid_x + (at[0] + size[0] / 2) * CELL
    y = panel_y + grid_y + (at[1] + size[1] / 2) * CELL
    return (anchor_x * width + x * scale) / width, (anchor_y * height + y * scale) / height


def stash(run: Run, inventory_key: str, own: frozenset[tuple[int, int, int]]) -> int:
    """Move the loop's items into the cube; how many moved. Mouse mode only. `Abort` with the panels closed when a
    panel does not open or an item is not where it should be."""
    if run.pad is not None:
        raise Abort('the cube needs mouse mode')
    carried = run.carried
    pack = carried() if carried is not None else None
    if carried is None or pack is None:
        LOG.info("Macro: cube: the inventory is not read: the loop's items stay where they are")
        return 0
    loop = loot(pack, own)
    if not loop:
        return 0
    cube = next((item for item in pack.items if item.txt == CUBE_CLASS), None)
    rect = run.actuator.keys.focused_window_rect()
    pack = roomed(pack)
    why = (
        'no cube in the inventory' if cube is None
        else 'no game window' if rect is None
        else None
    )  # fmt: skip
    if why is not None or rect is None or cube is None:
        LOG.info("Macro: cube: %s: the loop's %d items stay where they are", why, len(loop))
        return 0
    moves = plan(pack, own)
    if len(moves) < len(loop):
        LOG.info('Macro: cube: %d of the loop\'s %d items fit nowhere in it (%s)', len(loop) - len(moves), len(loop),
                 '/'.join(pack.cube or ()))  # fmt: skip
        run.say(f"Cube full: {len(loop) - len(moves)} of the loop's items stay in the inventory")
    if not moves:
        return 0
    moved = 0
    try:
        open_inventory(run, inventory_key)
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
        run.actuator.rebase()
        for item, _spot in moves:
            # Ctrl + click sends it into the open cube wherever the game finds room; `plan` made sure it fits
            run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            if not _until(run, lambda p, i=item: i.unit_id in p.cube_items):
                pack = carried()
                if pack is not None and all(c.unit_id != item.unit_id for c in pack.items):
                    # On the pointer after all: put back where it was
                    run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(4, 4))
                    run.actuator.click()
                raise Abort(f'the item at ({item.x}, {item.y}) did not go into the cube')
            moved += 1
    finally:
        if {'inventory', 'cube'} & set(run.world().open_panels):
            run.actuator.tap('Escape')  # with nothing open it opens the game's menu instead
            run.seen(lambda w: not {'inventory', 'cube'} & set(w.open_panels), PANEL_SECONDS)
            run.actuator.rebase()
        LOG.info("Macro: cube: %d of %d of the loop's items moved in", moved, len(moves))
    run.say(f'Cube: {moved} item{"s" if moved != 1 else ""} put in')
    return moved


def stash_only(
    run: Run, inventory_key: str, own: frozenset[tuple[int, int, int]], wanted: Callable[[Carried], bool]
) -> int:
    """`stash` for only the loop's items `wanted` picks (the others counted the player's); how many moved."""
    pack = run.reads.carried()
    if pack is None or not any(wanted(item) for item in loot(pack, own)):
        return 0
    return stash(run, inventory_key, own | own_of(item for item in pack.items if not wanted(item)))


def open_inventory(run: Run, inventory_key: str) -> None:
    """Open the inventory; its key is tapped only when closed (a tap on an open one closes it)."""
    if 'inventory' not in run.world().open_panels:
        run.actuator.tap(inventory_key)
        if run.seen(lambda w: 'inventory' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the inventory did not open')
    run.actuator.rebase()


def unpack(run: Run, inventory_key: str, items: Sequence[Carried]) -> int:
    """Take `items` out of the cube into the inventory by Ctrl + click; how many came out. For the stash, which takes
    from the cube only what a resource tab holds. One that does not come out after two clicks is passed over. Mouse
    mode only; the panels closed after."""
    rect = run.actuator.keys.focused_window_rect()
    pack = run.reads.carried()
    cube = next((item for item in pack.items if item.txt == CUBE_CLASS), None) if pack is not None else None
    if not items or rect is None or cube is None or run.pad is not None:
        return 0
    out = 0
    try:
        open_inventory(run, inventory_key)
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
        run.actuator.rebase()
        # The tallest first, then the largest: a 1 x 3 found no free column once smaller ones were out (2026-10-17)
        for item in sorted(items, key=lambda i: (-i.size[1], -i.size[0] * i.size[1])):
            # No block for it: not clicked (the session's second stash takes it)
            now = run.reads.carried()
            if now is not None and not now.inventory.has_room(item.size):
                LOG.info('Macro: cube: no room in the inventory for the item %d at (%d, %d)', item.txt, item.x, item.y)
                continue
            # Tried twice; one that does not come out is passed over, not the end ("we had space to move more item and
            # sell them all", the player, 2026-10-17)
            for _ in range(2):
                run.actuator.move(*cell_point(rect, CUBE, (item.x, item.y), item.size), scatter=(6, 6))
                run.actuator.click('Control_L')
                if _until(run, lambda p, i=item: i.unit_id not in p.cube_items):
                    out += 1
                    break
                run.pace.sleep(RETRY_PAUSE)
            else:
                LOG.info('Macro: cube: the item %d at (%d, %d) did not come out', item.txt, item.x, item.y)
    finally:
        if {'inventory', 'cube'} & set(run.world().open_panels):
            run.actuator.tap('Escape')
            run.seen(lambda w: not {'inventory', 'cube'} & set(w.open_panels), PANEL_SECONDS)
            run.actuator.rebase()
        LOG.info('Macro: cube: %d of %d items taken out', out, len(items))
    return out


def perfect_of(txt: int) -> int | None:
    """The perfect gem class three flawless gems of class `txt` transmute into, by the items metadata's names; None
    for any other class."""
    base = item_base(txt)
    name = base['name'] if base is not None else ''
    if not name.startswith('Flawless '):
        return None
    wanted = 'Perfect ' + name.removeprefix('Flawless ')
    return next((int(cid) for cid, other in metadata()['bases'].items() if other['name'] == wanted), None)


def transmute(run: Run, inventory_key: str, txt: int, park: Callable[[int], None] | None = None) -> bool:
    """Three flawless gems of class `txt` into one perfect gem ("for gems - we need to cube 3 flawless -> perfect",
    the player, 2026-10-17), for a gem whose stash stack is full. Transmute is clicked only when the cube holds
    exactly the three gems (no other recipe can take anything); whether one perfect gem came. Mouse mode only; the
    panels closed after. `park(unit)`: told before an item with no inventory room is put down at the feet ("drop on
    the ground then pickup and move to cube", the player, 2026-10-18); the caller picks it up again."""
    perfect = perfect_of(txt)
    rect = run.actuator.keys.focused_window_rect()
    pack = run.reads.carried()
    cube = next((item for item in pack.items if item.txt == CUBE_CLASS), None) if pack is not None else None
    if perfect is None or pack is None or rect is None or cube is None or run.pad is not None:
        return False
    if sum(item.txt == txt for item in (*pack.items, *pack.in_cube)) < GEMS_A_TRANSMUTE:
        return False
    made = False
    try:
        open_inventory(run, inventory_key)
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
        run.actuator.rebase()
        # Everything but three of the gems out of the cube
        inside = [item for item in pack.in_cube if item.txt == txt][:GEMS_A_TRANSMUTE]
        for item in [i for i in pack.in_cube if i not in inside]:
            now = run.reads.carried()
            if now is None:
                raise Abort('the inventory is not read')
            if not now.inventory.has_room(item.size):
                if park is None:
                    raise Abort(
                        f'no room in the inventory for the item {item.txt} the cube must be emptied of', cause='room'
                    )
                _park(run, rect, item, park)
                continue
            run.actuator.move(*cell_point(rect, CUBE, (item.x, item.y), item.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            if not _until(run, lambda p, i=item: i.unit_id not in p.cube_items):
                raise Abort(f'the item {item.txt} did not come out of the cube')
        # Then the gems from the inventory until three are in
        now = (run.reads.carried()) or pack
        for item in [i for i in now.items if i.txt == txt][: GEMS_A_TRANSMUTE - len(inside)]:
            run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            if not _until(run, lambda p, i=item: i.unit_id in p.cube_items):
                raise Abort(f'the gem at ({item.x}, {item.y}) did not go into the cube')
            inside.append(item)
        now = run.reads.carried()
        three = {item.unit_id for item in inside}
        if now is None or set(now.cube_items) != three or len(three) != GEMS_A_TRANSMUTE:
            raise Abort('the cube does not hold exactly the three gems: Transmute is not clicked')
        (anchor_x, anchor_y), (panel_x, panel_y), _grid = CUBE
        scale = rect[3] / REFERENCE_HEIGHT
        at = (
            (anchor_x * rect[2] + (panel_x + TRANSMUTE[0] + TRANSMUTE_INSIDE) * scale) / rect[2],
            (anchor_y * rect[3] + (panel_y + TRANSMUTE[1] + TRANSMUTE_INSIDE) * scale) / rect[3],
        )
        run.actuator.move(*at, scatter=(3, 3))
        run.actuator.click()
        deadline = run.clock() + TRANSMUTE_SECONDS
        while not made and run.clock() < deadline:
            after = run.reads.carried()
            made = (
                after is not None and len(after.cube_items) == 1
                and len(after.in_cube) == 1 and after.in_cube[0].txt == perfect
            )  # fmt: skip
            if not made:
                run.pace.sleep(0.05)
    except Abort as stop:
        LOG.info('Macro: cube: no transmute of %s: %s', _gem_name(txt), stop)
        if run.stops(stop):
            raise
    finally:
        if {'inventory', 'cube'} & set(run.world().open_panels):
            run.actuator.tap('Escape')
            run.seen(lambda w: not {'inventory', 'cube'} & set(w.open_panels), PANEL_SECONDS)
            run.actuator.rebase()
    LOG.info('Macro: cube: three %s %s', _gem_name(txt), f'into a {_gem_name(perfect)}' if made else 'not transmuted')
    if made:
        run.say(f'Cube: a {_gem_name(perfect)} made')
    return made


def _park(run: Run, rect: tuple[int, int, int, int], item: Carried, park: Callable[[int], None]) -> None:
    """Put the cube's `item` down at the character's feet; put back and `Abort` if it does not fall."""
    if why := protected(run, item):
        raise Abort(f'the item {item.txt} is {why}: never put down')
    park(item.unit_id)  # before it lies on the ground: never read as the player's (game/kept.py `PutDown`)
    run.actuator.move(*cell_point(rect, CUBE, (item.x, item.y), item.size), scatter=(4, 4))
    run.actuator.click()
    if not _until(run, lambda p: p.pointer == item.unit_id):
        now = run.reads.carried()
        if now is not None and now.pointer is not None:
            run.actuator.click()  # something else taken up: put down where it was, the pointer not moved
            _until(run, lambda p: p.pointer is None)
        raise Abort(f'the item {item.txt} was not taken up out of the cube')
    run.actuator.move(*PARK_POINT, scatter=(4, 4))
    run.actuator.click()
    if not _until(run, lambda p: p.pointer is None and item.unit_id not in p.cube_items):
        run.actuator.move(*cell_point(rect, CUBE, (item.x, item.y), item.size), scatter=(4, 4))
        run.actuator.click()
        _until(run, lambda p: p.pointer is None)
        raise Abort(f'the item {item.txt} did not fall')
    LOG.info('Macro: cube: %s (%d) put down for the transmute, to be picked up again', _gem_name(item.txt),
             item.unit_id)  # fmt: skip


@dataclass(frozen=True)
class RuneRecipe:
    """A cube recipe (cubemain.txt via data/rune_cube.json): `runes` of the input's class and the `gems` into one rune
    of class `into`."""

    into: int
    runes: int
    gems: tuple[int, ...] = ()
    description: str = ''


@functools.cache
def _rune_cube() -> dict:
    return json.loads((Path(__file__).parent / 'data' / 'rune_cube.json').read_text())


def rune_recipe(txt: int) -> RuneRecipe | None:
    """The recipe that takes runes of class `txt` into the next one (built by build_rune_cube.py from the installed
    game); None for no such recipe."""
    row = _rune_cube()['recipes'].get(str(txt))
    if row is None:
        return None
    return RuneRecipe(row['into'], row['runes'], tuple(row['gems']), row['description'])


def rune_slot(txt: int) -> tuple[float, float] | None:
    """The middle of the Runes or Gems tab's stack of class `txt` (the layout's `AdvancedStashSlotWidget`), in layout
    units of the left panel; None for a class neither tab has a slot for."""
    rect = _rune_cube()['slots'].get(str(txt))
    return None if rect is None else (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)


def stash_transmute() -> tuple[float, float]:
    """The cube's Transmute button on a resource tab (`advancedstash_horadriccube/convert`), clicked TRANSMUTE_INSIDE
    units in as cube mode's, in layout units of the left panel."""
    x, y = _rune_cube()['convert']
    return x + TRANSMUTE_INSIDE, y + TRANSMUTE_INSIDE


def _gem_name(txt: int) -> str:
    base = item_base(txt)
    return base['name'] if base is not None else str(txt)


def _until(run: Run, holds: Callable[[Pack], bool]) -> bool:
    """Whether the carried items come to hold `holds` within ITEM_SECONDS."""
    return until(run, holds, ITEM_SECONDS, read=lambda: run.reads.carried()) is not None
