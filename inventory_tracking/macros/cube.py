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

from collections.abc import Iterable, Sequence

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.world import Carried, Pack


__all__ = ['KEPT', 'Move', 'loot', 'own_of', 'plan', 'stash']

REFERENCE_HEIGHT = 2160
CELL = 98  # $ItemCellSize
INVENTORY = ((1.0, 0.397), (-1394, -651), (93, 897))  # anchor, panel origin, grid origin
CUBE = ((0.0, 0.397), (236, -651), (431, 534))
CUBE_CLASS = 564  # Horadric Cube (items metadata, 2026-10-16)
# Never moved: the cube, the tomes, the keys (items metadata: Horadric Cube, Tome of Town Portal, Tome of Identify, Key)
KEPT = frozenset((CUBE_CLASS, 533, 534, 558))
PANEL_SECONDS = 1.5  # for a panel to open or close
ITEM_SECONDS = 1.0  # for an item to leave a grid or land in one

Move = tuple[Carried, tuple[int, int]]  # an item and the cube's cell its top-left goes to


def own_of(items: Iterable[Carried]) -> frozenset[tuple[int, int, int]]:
    """The inventory as the player keeps it: each item's class and cell."""
    return frozenset((item.txt, item.x, item.y) for item in items)


def fits(rows: Sequence[str], at: tuple[int, int], size: tuple[int, int]) -> bool:
    x, y = at
    across, down = size
    if y + down > len(rows) or x + across > len(rows[0]):
        return False
    return all(rows[y + dy][x + dx] == '.' for dy in range(down) for dx in range(across))


def taken(rows: Sequence[str], at: tuple[int, int], size: tuple[int, int]) -> tuple[str, ...]:
    x, y = at
    across, down = size
    return tuple(
        ''.join('#' if y <= row < y + down and x <= col < x + across else cell for col, cell in enumerate(line))
        for row, line in enumerate(rows)
    )


def loot(pack: Pack, own: frozenset[tuple[int, int, int]]) -> list[Carried]:
    """The loop's items in `pack`: neither the player's (`own`) nor KEPT."""
    return [item for item in pack.items if item.txt not in KEPT and (item.txt, item.x, item.y) not in own]


def plan(pack: Pack, own: frozenset[tuple[int, int, int]]) -> list[Move]:
    """The loop's items in `pack` and the cube's cell each goes to: smaller first, the first free block that fits."""
    if pack.cube is None:
        return []
    rows, moves = pack.cube, []
    for item in sorted(loot(pack, own), key=lambda i: (i.size[0] * i.size[1], i.y, i.x)):
        spot = next(
            ((x, y) for y in range(len(rows)) for x in range(len(rows[0])) if fits(rows, (x, y), item.size)), None
        )
        if spot is not None:
            moves.append((item, spot))
            rows = taken(rows, spot, item.size)
    return moves


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
    why = (
        'no cube in the inventory' if cube is None
        else "the cube's grid is not read" if pack.cube is None
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
        run.actuator.move(*cell_point(rect, INVENTORY, (cube.x, cube.y), cube.size), scatter=(8, 8))
        run.actuator.tap('Button3')
        if run.seen(lambda w: 'cube' in w.open_panels, PANEL_SECONDS) is None:
            raise Abort('the cube did not open')
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
        LOG.info("Macro: cube: %d of %d of the loop's items moved in", moved, len(moves))
    run.say(f'Cube: {moved} item{"s" if moved != 1 else ""} put in')
    return moved


def _until(run: Run, holds) -> bool:
    """Whether the carried items come to hold `holds` within ITEM_SECONDS."""
    deadline = run.clock() + ITEM_SECONDS
    while True:
        pack = run.carried() if run.carried is not None else None
        if pack is not None and holds(pack):
            return True
        if run.clock() >= deadline:
            return False
        run.pace.sleep(0.05)
