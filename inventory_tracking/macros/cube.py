"""The loop's loot into the Horadric Cube between games (routes/lower-kurast-loop-plan.md phase 9).

The player, 2026-10-16: "we need to move items to cube from time to time, to have more run loops without
interactions", then "probably move items between games". Loot to Cube is the controller's (macros/pad.py) and the
macros never switch the game's input mode, so the items are moved by the mouse, as the player moved them by hand in
Pandemonium Fortress at 21:03 and 21:15 that day (takes 20261016T180313Z-103, 181510Z-103: `inventory`, `cube`): the
inventory opened by its key, the cube by a right click on it, then each item sent into the cube by a Ctrl + click on it
(the player: "we can move faster items to cube - open and ctrl+click on item"), each checked in memory (the item's
unit lies in the cube's grid), and the panels closed.

What moves is the loop's: an item that was not in the inventory when the loop began (`Loop.own`, by class and cell:
the cells of a carried item stay from game to game), or that an earlier loop left there (`Loop.mine`, kept on disk),
never the cube, a tome or the keys. The player's charms, kept in the inventory for their stats, were there when the
loop began, so they stay. Smaller items first, each into the first free block (row by row) that fits it; one that fits
nowhere stays, and the HUD says so: the cube holds 12 cells, a grand charm takes 3. Each reason nothing moves is logged
(`Macro: cube: …`): from game 8 to 17 of 22:50 on 2026-10-16 nothing moved and nothing said why.

Where to click is the game's own layout (`data/global/ui/layouts/playerinventoryoriginallayouthd.json`,
`horadriccubelayouthd.json`, `_profilehd.json`, read on 2026-10-16; a layout unit is 1/2160 of the window's height,
as for the waypoint panel): the inventory's 10 x 4 grid at (93, 897) of `$RightPanelRect` (-1394, -651) anchored at
(1.0, 0.397); the cube's 3 x 4 grid at (431, 534) of `$LeftPanelRect` (236, -651) at (0.0, 0.397); 98 units a cell. The
player's screenshot of 21:16 put the inventory's first column and row where this says, within 2 pixels.
"""

import functools
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from inventory_tracking.collection.capture import GRID_CONTAINERS
from inventory_tracking.common import LOG
from inventory_tracking.items.metadata import item_base, metadata
from inventory_tracking.macros.act import until
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pickmode import MAGIC, RARE, SKILLED
from inventory_tracking.macros.world import CUBE_GRID, INVENTORY_GRID, Carried, Pack


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
# A Grand Charm's block (across, down): the tallest of the sure valuables the run stops by when it has no room (charms
# are taken whatever their worth). Room counted in cells alone had none left for one: 9 cells free in pieces, a Grand
# Charm left on the ground and the loop stopped (21:00:03 on 2026-10-17)
SURE_BLOCK = (1, 3)
DROP_POINT = (0.3, 0.5)  # a click on the ground left of the inventory's panel: what the pointer holds falls at the feet
# With the cube's panel open on the left as well: a click on the ground between the two panels, below the character
# ($LeftPanelRect ends near 0.36 of a 16:9 window, $RightPanelRect begins near 0.64)
PARK_POINT = (0.5, 0.7)

Move = tuple[Carried, tuple[int, int]]  # an item and the cube's cell its top-left goes to
# The cube's Transmute button (`horadriccubelayouthd.json`, ButtonWidget "convert", read 2026-10-18): its top-left at
# (520, 969) of `$LeftPanelRect`, below the grid (which ends at 534 + 4 x 98 = 926); clicked TRANSMUTE_INSIDE units in
TRANSMUTE = (520, 969)
TRANSMUTE_INSIDE = 35
GEMS_A_TRANSMUTE = 3  # the cube's recipe: three flawless gems of a kind into one perfect gem of it
TRANSMUTE_SECONDS = 1.5  # for the perfect gem to show in the cube after the click


def own_of(items: Iterable[Carried]) -> frozenset[tuple[int, int, int]]:
    """The inventory as the player keeps it: each item's class and cell."""
    return frozenset((item.txt, item.x, item.y) for item in items)


def fits(rows: Sequence[str], at: tuple[int, int], size: tuple[int, int]) -> bool:
    x, y = at
    across, down = size
    if y + down > len(rows) or x + across > len(rows[0]):
        return False
    return all(rows[y + dy][x + dx] == '.' for dy in range(down) for dx in range(across))


def inventory_rows(pack: Pack) -> tuple[str, ...]:
    """The carried inventory's 10 x 4 grid as rows ('.' a free cell), from its items' cells and sizes."""
    width, height = GRID_CONTAINERS[INVENTORY_GRID][1:]
    rows: tuple[str, ...] = ('.' * width,) * height
    for item in pack.items:
        rows = taken(rows, (item.x, item.y), item.size)
    return rows


def room_for(rows: Sequence[str], size: tuple[int, int]) -> bool:
    """Whether a block of `size` is free anywhere in `rows`."""
    return any(fits(rows, (x, y), size) for y in range(len(rows)) for x in range(len(rows[0])))


def taken(rows: Sequence[str], at: tuple[int, int], size: tuple[int, int]) -> tuple[str, ...]:
    x, y = at
    across, down = size
    return tuple(
        ''.join('#' if y <= row < y + down and x <= col < x + across else cell for col, cell in enumerate(line))
        for row, line in enumerate(rows)
    )


def roomed(pack: Pack) -> Pack:
    """`pack` with a carried cube whose grid was not read as an empty one. An empty cube has no cells to its grid, and
    the grids read leave such a grid out: every game of 23:28 on 2026-10-16 said "the cube's grid is not read" with
    the cube empty (the player: "still we don't use cube and it is empty"). Each item's move is still checked in
    memory, in the grid it then has."""
    if pack.cube is not None or all(item.txt != CUBE_CLASS for item in pack.items):
        return pack
    width, height = GRID_CONTAINERS[CUBE_GRID][1:]
    return replace(pack, cube=('.' * width,) * height)


def overflow(pack: Pack, own: frozenset[tuple[int, int, int]]) -> bool:
    """Whether some of the loop's items in `pack` fit nowhere in the cube."""
    pack = roomed(pack)
    return len(plan(pack, own)) < len(loot(pack, own))


def loot(pack: Pack, own: frozenset[tuple[int, int, int]]) -> list[Carried]:
    """The loop's items in `pack`: neither the player's (`own`) nor KEPT."""
    return [item for item in pack.items if item.txt not in KEPT and (item.txt, item.x, item.y) not in own]


def plan(pack: Pack, own: frozenset[tuple[int, int, int]]) -> list[Move]:
    """The loop's items in `pack` and the cube's cell each goes to, each in the first free block that fits it: larger
    first, or smaller first where that places more. Smaller first alone left a 2 x 2 Antlers out of an empty cube
    after a rune and a 1 x 3 Stilleto took the first blocks, and the room read as low sent the loop to a whole trade
    session one game after the last (16:39:01 on 2026-10-17)."""
    if pack.cube is None:
        return []
    items = loot(pack, own)
    larger = _placed(pack.cube, sorted(items, key=lambda i: (-i.size[0] * i.size[1], -i.size[1], i.y, i.x)))
    smaller = _placed(pack.cube, sorted(items, key=lambda i: (i.size[0] * i.size[1], i.y, i.x)))
    return larger if len(larger) >= len(smaller) else smaller


def _placed(rows: Sequence[str], items: Sequence[Carried]) -> list[Move]:
    """`items` in their order, each into the first free block of `rows` that fits it."""
    moves: list[Move] = []
    for item in items:
        spot = next(
            ((x, y) for y in range(len(rows)) for x in range(len(rows[0])) if fits(rows, (x, y), item.size)), None
        )
        if spot is not None:
            moves.append((item, spot))
            rows = taken(rows, spot, item.size)
    return moves


KEY_CLASS = 558  # Key (items metadata, 2026-10-16; macros/shop.py KEY)


def largest_block(rows: Sequence[str]) -> int:
    """The cells of the largest free rectangle in `rows`."""
    height, width = len(rows), len(rows[0]) if rows else 0
    return max(
        (
            across * down
            for y in range(height)
            for x in range(width)
            for down in range(1, height - y + 1)
            for across in range(1, width - x + 1)
            if fits(rows, (x, y), (across, down))
        ),
        default=0,
    )


BIG_BLOCK = (
    2,
    4,
)  # the largest item's cells (an armour, a polearm): the room a session leaves (the player, 2026-10-18)


def keys_move(pack: Pack, size: tuple[int, int] = BIG_BLOCK) -> Move | None:
    """A key stack and the free inventory cell it goes to that frees a block of `size`, else makes the largest free
    block larger, the largest first; None when no move does (the player, 2026-10-17 19:10: "move key two cells left to
    make continuous 2x4 space": the second stack, bought at Jamella, landed where it split the free cells). The block
    of `size` first: a 3 x 3 block counted larger than a 2 x 4 and a Unique Brandistock found no room while the loop's
    keys stood in the only 2 x 4 (12:36 on 2026-10-18; the player: "in this particular case we even have all the
    required space to get it inside the inventory")."""
    rows = inventory_rows(pack)

    def score(lines: Sequence[str]) -> tuple[bool, int]:
        return room_for(lines, size), largest_block(lines)

    best, found = score(rows), None
    for key in (item for item in pack.items if item.txt == KEY_CLASS and item.size == (1, 1)):
        without = tuple(
            ''.join('.' if (col, row) == (key.x, key.y) else cell for col, cell in enumerate(line))
            for row, line in enumerate(rows)
        )
        for y, line in enumerate(without):
            for x, cell in enumerate(line):
                if cell != '.' or (x, y) == (key.x, key.y):
                    continue
                block = score(taken(without, (x, y), (1, 1)))
                if block > best:
                    best, found = block, (key, (x, y))
    return found


def arrange_keys(run: Run, inventory_key: str) -> bool:
    """Move a key stack where the inventory's free cells make the largest block (`keys_move`): picked up by a click,
    put down by a click on its cell, each checked in memory; put back where it was if it does not land. Whether it
    moved. Mouse mode only; the panels closed after."""
    rect = run.actuator.keys.focused_window_rect()
    pack = run.carried() if run.carried is not None else None
    move = keys_move(pack) if pack is not None else None
    if move is None or rect is None or run.pad is not None:
        return False
    key, (x, y) = move
    moved = False
    try:
        run.actuator.tap(inventory_key)
        if run.seen(lambda w: 'inventory' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the inventory did not open')
        run.actuator.rebase()
        run.actuator.move(*cell_point(rect, INVENTORY, (key.x, key.y)), scatter=(4, 4))
        run.actuator.click()
        if not _until(run, lambda p: p.pointer == key.unit_id):
            now = run.carried() if run.carried is not None else None
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
    """The loop's item in the inventory to drop for a block of `size`: one taken only to identify it (a magic or rare
    item of a type that rolls skills, unidentified: pickmode.py `candidate`, whose loss costs a game nothing) whose
    cells free such a block; the smallest. None where none does, or the block is free already."""
    rows = inventory_rows(pack)
    if room_for(rows, size):
        return None
    found = [
        item
        for item in loot(pack, own)
        if not item.identified
        and item.quality in (MAGIC, RARE)
        and (base := item_base(item.txt)) is not None
        and base['type'] in SKILLED
        and room_for(inventory_rows(replace(pack, items=tuple(i for i in pack.items if i is not item))), size)
    ]
    return min(found, key=cells) if found else None


def drop_for(
    run: Run, inventory_key: str, own: frozenset[tuple[int, int, int]], size: tuple[int, int]
) -> Carried | None:
    """Drop the loop's item `droppable` names at the character's feet: room for a sure valuable the inventory has no
    block of `size` for, after the cube took what it could (the loop stopped by a Grand Charm, 21:00:03 on
    2026-10-17). The item dropped, or None. Mouse mode only; the panels closed after."""
    pack = run.carried() if run.carried is not None else None
    item = droppable(pack, own, size) if pack is not None else None
    if item is None:
        return None
    return item if drop_item(run, inventory_key, item, f'for a {size[0]}x{size[1]} block') else None


def drop_item(run: Run, inventory_key: str, item: Carried, why: str) -> bool:
    """Drop the inventory's `item` at the character's feet: picked up by a click, dropped by a click on the ground left
    of the panel, checked in memory; put back where it was if it does not fall. Whether it fell. Mouse mode only; the
    panels closed after."""
    rect = run.actuator.keys.focused_window_rect()
    if rect is None or run.pad is not None:
        return False
    dropped = False
    try:
        run.actuator.tap(inventory_key)
        if run.seen(lambda w: 'inventory' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the inventory did not open')
        run.actuator.rebase()
        run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(4, 4))
        run.actuator.click()
        if not _until(run, lambda p: p.pointer == item.unit_id):
            now = run.carried() if run.carried is not None else None
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
    """Move the loop's items into the cube (the module text); how many were moved. Mouse mode only. `Abort` with the
    panels closed when a panel does not open or an item is not where it should be."""
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
        # Each game left with them is a game played with less room: the player empties the cube
        LOG.info('Macro: cube: %d of the loop\'s %d items fit nowhere in it (%s)', len(loop) - len(moves), len(loop),
                 '/'.join(pack.cube or ()))  # fmt: skip
        run.say(f"Cube full: {len(loop) - len(moves)} of the loop's items stay in the inventory")
    if not moves:
        return 0
    moved = 0
    try:
        run.actuator.tap(inventory_key)
        if run.seen(lambda w: 'inventory' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the inventory did not open')
        run.actuator.rebase()
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
        run.actuator.rebase()
        for item, _spot in moves:
            # A Ctrl + click sends the item into the open cube, wherever the game finds room (the player, 2026-10-16:
            # "we can move faster items to cube - open and ctrl+click on item"); `plan` has made sure it fits
            run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            if not _until(run, lambda p, i=item: i.unit_id in p.cube_items):
                pack = carried()
                if pack is not None and all(c.unit_id != item.unit_id for c in pack.items):
                    # On the pointer after all: put back where it was taken from, nothing left on the pointer
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


def unpack(run: Run, inventory_key: str, items: Sequence[Carried]) -> int:
    """Take `items` out of the cube into the inventory, by a Ctrl + click on each with the cube open; how many came
    out. For the stash (macros/stash.py), which takes from the cube's grid only what a resource tab holds: a charm,
    a ring, a jewel stayed in the cube on a Ctrl + Shift + click (01:28:34 on 2026-10-17). One that does not come out
    after two clicks is passed over. Mouse mode only; the panels closed after."""
    rect = run.actuator.keys.focused_window_rect()
    pack = run.carried() if run.carried is not None else None
    cube = next((item for item in pack.items if item.txt == CUBE_CLASS), None) if pack is not None else None
    if not items or rect is None or cube is None or run.pad is not None:
        return 0
    out = 0
    try:
        run.actuator.tap(inventory_key)
        if run.seen(lambda w: 'inventory' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the inventory did not open')
        run.actuator.rebase()
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
        run.actuator.rebase()
        # The tallest first, then the largest: a 1 x 3 Blade found no free column once smaller ones were out (13:11:52
        # on 2026-10-17), and stayed in the cube after the trade session
        for item in sorted(items, key=lambda i: (-i.size[1], -i.size[0] * i.size[1])):
            # One the inventory has no block for is not clicked: three such were tried for 3 s each with two cells
            # free, before the stash (14:51:04-14 on 2026-10-17); the session's second stash takes them
            now = run.carried() if run.carried is not None else None
            if now is not None and not room_for(inventory_rows(now), item.size):
                LOG.info('Macro: cube: no room in the inventory for the item %d at (%d, %d)', item.txt, item.x, item.y)
                continue
            # Each item tried twice, and one that does not come out is passed over, not the end: at 12:54:10 on
            # 2026-10-17 the second of four did not, the inventory had room (the player: "we had space to move more
            # item and sell them all"), and the other two stayed
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
    """The class of the perfect gem three flawless gems of class `txt` transmute into (the names of the items
    metadata, never a code from memory); None for any other class."""
    base = item_base(txt)
    name = base['name'] if base is not None else ''
    if not name.startswith('Flawless '):
        return None
    wanted = 'Perfect ' + name.removeprefix('Flawless ')
    return next((int(cid) for cid, other in metadata()['bases'].items() if other['name'] == wanted), None)


def transmute(run: Run, inventory_key: str, txt: int, park: Callable[[int], None] | None = None) -> bool:
    """Three flawless gems of class `txt` into one perfect gem by the cube (the player, 2026-10-17: "for gems - we need
    to cube 3 flawless -> perfect"): for a gem whose stash stack is full (99), which the loop keeps and never sells
    (macros/loop.py `sold_full`). The cube must hold nothing else when Transmute is clicked, so no other recipe can
    take what is in it: what else is in it comes out first, then three of the gems go in, the cube's units are read
    again and must be exactly those three, and only then is the button clicked; one perfect gem of the kind must be all
    it holds after. Whether it was made. Mouse mode only; the panels closed after; what was not made stays where it is
    (all of it the loop's). `park(unit)`: what the inventory has no room for is put down at the character's feet
    instead, `park` told first (the player, 09:53 on 2026-10-18: "drop on the ground then pickup and move to cube");
    the caller picks it up again."""
    perfect = perfect_of(txt)
    rect = run.actuator.keys.focused_window_rect()
    pack = run.carried() if run.carried is not None else None
    cube = next((item for item in pack.items if item.txt == CUBE_CLASS), None) if pack is not None else None
    if perfect is None or pack is None or rect is None or cube is None or run.pad is not None:
        return False
    if sum(item.txt == txt for item in (*pack.items, *pack.in_cube)) < GEMS_A_TRANSMUTE:
        return False
    made = False
    try:
        run.actuator.tap(inventory_key)
        if run.seen(lambda w: 'inventory' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the inventory did not open')
        run.actuator.rebase()
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
        run.actuator.rebase()
        # What else is in the cube, and gems past three, out into the inventory
        inside = [item for item in pack.in_cube if item.txt == txt][:GEMS_A_TRANSMUTE]
        for item in [i for i in pack.in_cube if i not in inside]:
            now = run.carried() if run.carried is not None else None
            if now is None:
                raise Abort('the inventory is not read')
            if not room_for(inventory_rows(now), item.size):
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
        now = (run.carried() if run.carried is not None else None) or pack
        for item in [i for i in now.items if i.txt == txt][: GEMS_A_TRANSMUTE - len(inside)]:
            run.actuator.move(*cell_point(rect, INVENTORY, (item.x, item.y), item.size), scatter=(6, 6))
            run.actuator.click('Control_L')
            if not _until(run, lambda p, i=item: i.unit_id in p.cube_items):
                raise Abort(f'the gem at ({item.x}, {item.y}) did not go into the cube')
            inside.append(item)
        now = run.carried() if run.carried is not None else None
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
            after = run.carried() if run.carried is not None else None
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
    """The cube's `item` put down at the character's feet (`transmute`): taken up by a click, dropped by a click on
    the ground between the panels, checked in memory; put back where it was if it does not fall, then `Abort`."""
    park(item.unit_id)  # before it lies on the ground: never read as the player's (world.py `PutDown`)
    run.actuator.move(*cell_point(rect, CUBE, (item.x, item.y), item.size), scatter=(4, 4))
    run.actuator.click()
    if not _until(run, lambda p: p.pointer == item.unit_id):
        now = run.carried() if run.carried is not None else None
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
    """A Horadric Cube recipe of the game's data (cubemain.txt, data/rune_cube.json): `runes` of the input's class and
    the `gems` (classes) into one rune of class `into`."""

    into: int
    runes: int
    gems: tuple[int, ...] = ()
    description: str = ''


@functools.cache
def _rune_cube() -> dict:
    return json.loads((Path(__file__).parent / 'data' / 'rune_cube.json').read_text())


def rune_recipe(txt: int) -> RuneRecipe | None:
    """The cube's recipe that takes runes of class `txt` into the next one (cubemain.txt, built by build_rune_cube.py
    from the installed game: never from memory); None for no rune or no such recipe."""
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
    """Whether the carried items come to hold `holds` within ITEM_SECONDS (act.py `until`, which stash.py's copy of
    this became too on 2026-10-18; charms.py and visit.py import it from stash.py)."""
    return until(run, holds, ITEM_SECONDS, read=lambda: run.carried() if run.carried is not None else None) is not None
