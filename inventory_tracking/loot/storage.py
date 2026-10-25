"""Layer 4 of the loot design (loot/design.md §1, §7 M3): where the loop's things go. Pure: no input, no reads, no
clock.

- the cube: which of the loop's items go where in it (`plan`), whether some fit nowhere (`overflow`), the key stack
  moved to free a block (`keys_move`);
- the stash stop's plan (`stash_stop`: resource tabs, pages by `place`, cube keepers out by `_make_way`, junk parked,
  rune transmutes) and the visit simulated (`after`); the flawless gems sold (`surplus`);
- the loop's room: its count (`room`), whether a town visit is due for room (`room_low`), the share its items take
  (`occupied`).

Moved here on 2026-10-20 from macros/cube.py and macros/town.py (and the stash's page order and resource tabs from
macros/stash.py, which this layer needs and which import the cube), each re-exported there; the recorded visits plan
byte for byte as before (tests/inventory_tracking/loot/test_storage_replay.py). Evidence for the tuned numbers:
macros/history/town.md.
"""

import functools
import json
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence, Set
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from inventory_tracking.game.records import Carried, Pack, Page, StashView
from inventory_tracking.game.stash import RUNES_AIM, STACK_MOST
from inventory_tracking.items.grid import CUBE_SIZE, INVENTORY_SIZE, Grid
from inventory_tracking.items.metadata import item_base, metadata
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES


__all__ = [
    'BER',
    'BIG_BLOCK',
    'CUBE_CLASS',
    'GEMS_A_KIND',
    'GEMS_KEPT',
    'INVENTORY_CELLS',
    'KEPT',
    'KEY_CLASS',
    'MATERIALS_TAB',
    'PAGE_PRIORITY',
    'PARK_JUNK',
    'RESOURCES',
    'RUNES_AIM',
    'RUNES_A_TAKE',
    'RUNES_TAB',
    'RUNE_TRANSMUTES',
    'SHARED_PRIORITY',
    'SURE_BLOCK',
    'TRADE_ROOM',
    'Cell',
    'Holdings',
    'Move',
    'Put',
    'Room',
    'RuneCube',
    'RuneRecipe',
    'StashStop',
    'Storage',
    'after',
    'cells_low',
    'is_potion',
    'keys_move',
    'loot',
    'occupied',
    'out_now',
    'overflow',
    'perfect_of',
    'place',
    'plan',
    'resource_classes',
    'resource_tabs',
    'room',
    'room_low',
    'roomed',
    'rune_cube',
    'rune_recipe',
    'rune_transmutes',
    'stash_stop',
    'surplus',
    'uncubed',
    'unread_way_for_cube',
    'volatile_rows',
]

DATA = Path(__file__).resolve().parents[1] / 'macros' / 'data'  # stash_tabs.json, rune_cube.json

Cell = tuple[int, int, int]  # an item's class and cell, as `Loop.own` tells the player's
Move = tuple[Carried, tuple[int, int]]  # an item and the cell its top-left goes to

# Item classes (items metadata, 2026-10-16)
CUBE_CLASS = 564  # Horadric Cube
KEY_CLASS = 558  # Key (macros/shop.py KEY)
# Never moved: the cube, the tomes, the keys (Horadric Cube, Tome of Town Portal, Tome of Identify, Key)
KEPT = frozenset((CUBE_CLASS, 533, 534, 558))
# A key stack on a volatile cell (inside the loop's block) may go onto a free protected cell when only that frees the
# block (`keys_move`): the 02:06 state on 2026-10-25, the keys at (3, 3) in the 2 x 4 block and (2, 2), the cell they
# had held, empty. The keys are kept by class (`loot` never returns them), so on a protected cell they cost the
# player nothing a key stack did not cost before, and they fill the empty protected cell a pickup would land on and
# be read as the player's (macros/volatile.py `empty`); the player's own moves are never undone (a stack on a
# protected cell never moves). Never for a larger block alone, never into a hole larger than 1 x 1 (a charm the player
# took out by hand may come back there). False: keys only onto free volatile cells
KEYS_ONTO_PROTECTED = True

# A Grand Charm's block (across, down), the tallest sure valuable: room is a block, not a cell count (9 cells free in
# pieces left one on the ground, 2026-10-17 21:00:03)
SURE_BLOCK = (1, 3)
# The largest item's cells (an armour, a polearm): the room a session leaves (the player, 2026-10-18)
BIG_BLOCK = (2, 4)
INVENTORY_CELLS = INVENTORY_SIZE[0] * INVENTORY_SIZE[1]

# The stash. The player's priority, 2026-10-18: shared 3 > 4 > 5 > 2 > 1 > personal (page 0)
PAGE_PRIORITY = (3, 4, 5, 2, 1, 0)
SHARED_PRIORITY = PAGE_PRIORITY[:-1]
RUNES_TAB = 4  # `resource_tabs`: 2 Gems, 3 Materials, 4 Runes
MATERIALS_TAB = 3  # `resource_tabs`: the essences, shards, keys and the rest

# The loop's unidentified and junk wait until fewer than this many cells are free in the inventory and cube together,
# then one whole visit: "trade ... by remaining free slots" (the player, 2026-10-17). A 2 x 4 fits nowhere below it.
TRADE_ROOM = 8
# A full stack's flawless gems kept for the cube: at most GEMS_A_KIND of a kind, GEMS_KEPT in all (unbounded, they
# filled the cube); the rest sold only once the perfect stack is full too: "we must cube them up first" (2026-10-18).
GEMS_A_KIND = 3
GEMS_KEPT = 6
# Junk holding the only block a cube keeper could come out through is parked on a shared page and taken back before
# the stash closes: "junk can be temporarily stored in stash, but sold after" (the player, 2026-10-18).
PARK_JUNK = True
# Rune stacks over RUNES_AIM: three runes out to the cube and transmuted into the next (`rune_recipe`; Thul to Lem take
# a gem from the Gems tab, Pul up take two runes: not handled), the fullest first, at most RUNE_TRANSMUTES a visit,
# never a Ber Rune: the player's aim (game/stash.py RUNES_AIM). Timing evidence: macros/history/town.md.
RUNE_TRANSMUTES = 3
RUNES_A_TAKE = 3  # what a Ctrl + Shift + right click on a stack moves into the cube (the player, 14:28 on 2026-10-18)
# Ber Runes are kept for Enigma (the player, 2026-10-09)
BER = next(txt for txt, row in RUNE_CLASSES.items() if row['name'] == 'Ber Rune')


# Item classes: resources, gems, runes


@functools.cache
def resource_classes() -> frozenset[int]:
    """The item classes the stash's resource tabs hold (macros/data/stash_tabs.json)."""
    tabs = json.loads((DATA / 'stash_tabs.json').read_text())['tabs']
    codes = {code for names in tabs.values() for code in names}
    return frozenset(int(cid) for cid, base in metadata()['bases'].items() if base.get('code') in codes)


RESOURCES = resource_classes()


@functools.cache
def resource_tabs() -> dict[int, int]:
    """The stash tab (2 Gems, 3 Materials, 4 Runes) each resource class goes onto."""
    tabs = json.loads((DATA / 'stash_tabs.json').read_text())['tabs']
    index = {'gems': 2, 'materials': 3, 'runes': 4}
    by_code = {code: index[name] for name, codes in tabs.items() for code in codes}
    return {int(cid): by_code[base['code']] for cid, base in metadata()['bases'].items() if base.get('code') in by_code}


def is_potion(txt: int) -> bool:
    """Whether the class is a potion's (misc.txt types `rpot`, `hpot`, ...)."""
    base = metadata()['bases'].get(str(txt))
    return base is not None and str(base.get('type', '')).endswith('pot')


def perfect_of(txt: int) -> int | None:
    """The perfect gem class three flawless gems of class `txt` transmute into, by the items metadata's names; None
    for any other class."""
    base = item_base(txt)
    name = base['name'] if base is not None else ''
    if not name.startswith('Flawless '):
        return None
    wanted = 'Perfect ' + name.removeprefix('Flawless ')
    return next((int(cid) for cid, other in metadata()['bases'].items() if other['name'] == wanted), None)


@dataclass(frozen=True)
class RuneRecipe:
    """A cube recipe (cubemain.txt via data/rune_cube.json): `runes` of the input's class and the `gems` into one rune
    of class `into`."""

    into: int
    runes: int
    gems: tuple[int, ...] = ()
    description: str = ''


@functools.cache
def rune_cube() -> dict:
    """macros/data/rune_cube.json (built by build_rune_cube.py from the installed game): the recipes, and the resource
    tabs' slots and Transmute button the cube's clicks use (macros/cube.py `rune_slot`, `stash_transmute`)."""
    return json.loads((DATA / 'rune_cube.json').read_text())


def rune_recipe(txt: int) -> RuneRecipe | None:
    """The recipe that takes runes of class `txt` into the next one (built by build_rune_cube.py from the installed
    game); None for no such recipe."""
    row = rune_cube()['recipes'].get(str(txt))
    if row is None:
        return None
    return RuneRecipe(row['into'], row['runes'], tuple(row['gems']), row['description'])


# The cube


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


def volatile_rows(rows: Grid, protected: frozenset[tuple[int, int]]) -> Grid:
    """`rows` (the inventory's) with the protected cells taken: the loop's room (macros/volatile.py)."""
    if not protected:
        return rows
    return Grid(
        ''.join('#' if (col, row) in protected else cell for col, cell in enumerate(line))
        for row, line in enumerate(rows)
    )


def keys_move(
    pack: Pack, size: tuple[int, int] = BIG_BLOCK, protected: frozenset[tuple[int, int]] = frozenset()
) -> Move | None:
    """A key stack and the free cell to move it to that frees a block of `size`, else grows the largest free block
    most; None when no move does ("move key two cells left to make continuous 2x4 space", the player, 2026-10-17).
    A block of `size` ranks first: a 3 x 3 counted larger than the only 2 x 4 once (2026-10-18 12:36).

    `protected`: the character's protected cells (macros/volatile.py; every live caller passes them, none: as
    before). The blocks are counted on the volatile cells only, the loop's room; a key stack on a protected cell is
    the player's and never moves; a stack on a volatile cell goes onto a free volatile cell, or onto a free protected
    cell only when that frees the block of `size` no volatile cell frees and the cell is a 1 x 1 hole among the
    player's items, never a cell of a larger hole a charm taken out by hand left (KEYS_ONTO_PROTECTED). 01:53:11 on
    2026-10-25: the keys were moved off the protected (2, 2) into the 2 x 4 block in columns 3-4, the only room the
    player leaves the loop ("the loop's space is the 2x4 block in columns 3-4 only", the player, 2026-10-24), and a
    picked Ring then landed on the empty (2, 2) and was read as the player's
    (rca/2026-10-25/keys-protected-findings.md)."""
    rows = pack.inventory

    def score(lines: Grid) -> tuple[bool, int]:
        return lines.has_room(size), lines.largest_block()

    def room(lines: Grid) -> Grid:
        return volatile_rows(lines, protected)

    def hole(x: int, y: int) -> bool:  # a free protected cell no free protected cell touches: a 1 x 1 hole
        near = ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
        return not any(c in protected and 0 <= c[1] < len(rows) and 0 <= c[0] < rows.width and rows[c[1]][c[0]] == '.'
                       for c in near)  # fmt: skip

    best, found = score(room(rows)), None
    keys = [i for i in pack.items if i.txt == KEY_CLASS and i.size == (1, 1) and (i.x, i.y) not in protected]
    # Free volatile cells first; then, only for the block itself, free protected ones
    for onto_protected in (False, True) if protected and KEYS_ONTO_PROTECTED else (False,):
        if onto_protected and best[0]:
            break
        for key in keys:
            without = Grid(
                ''.join('.' if (col, row) == (key.x, key.y) else cell for col, cell in enumerate(line))
                for row, line in enumerate(rows)
            )
            for y, line in enumerate(without):
                for x, cell in enumerate(line):
                    if cell != '.' or (x, y) == (key.x, key.y) or ((x, y) in protected) != onto_protected:
                        continue
                    if onto_protected and not hole(x, y):
                        continue
                    block = score(room(without.take((x, y), (1, 1))))
                    if block > best and (block[0] or not onto_protected):
                        best, found = block, (key, (x, y))
    return found


# The loop's room


@dataclass(frozen=True)
class Storage:
    """The loop's storage as read: the carried pack (its inventory and cube) and the player's own items' cells
    (`Loop.own`). The loop's items are the rest but KEPT (`loot`) and the cube's."""

    pack: Pack
    own: frozenset[Cell] = frozenset()


@dataclass(frozen=True)
class Room:
    """The loop's room as it waits for a town visit (`room`). `inventory`: the inventory's free cells (INVENTORY_CELLS
    less every carried item's); `cube`: the cube's (a carried cube's unread grid counted empty); `free`: the count the
    visit waits on (`room`); `rows`: the cube's rows, () with no cube."""

    inventory: int
    cube: int
    free: int
    rows: tuple[str, ...]

    @property
    def low(self) -> bool:
        return cells_low(self.free)


def cells_low(free: int) -> bool:
    """Whether `free` cells of the loop's room (`Room.free`) are too few: a town visit is due for room."""
    return free < TRADE_ROOM


def room(storage: Storage) -> Room:
    """The loop's room: the inventory's and the cube's free cells together, as the trade waits until both are full;
    the inventory's alone when its count is under TRADE_ROOM and some of the loop's items fit nowhere in the cube (cube
    room in pieces no loop item fits is no room); under TRADE_ROOM whatever the count when neither has a SURE_BLOCK
    free."""
    pack, own = storage.pack, storage.own
    rows = roomed(pack).cube or ()
    in_inventory = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items)
    in_cube = sum(row.count('.') for row in rows)
    free = in_inventory + in_cube
    if in_inventory < TRADE_ROOM and overflow(pack, own):
        free = min(free, in_inventory)
    if not any(lines and Grid(lines).has_room(SURE_BLOCK) for lines in (pack.inventory, rows)):
        free = min(free, TRADE_ROOM - 1)
    return Room(in_inventory, in_cube, free, tuple(rows))


def room_low(storage: Storage) -> bool:
    """Whether a town visit is due for room (`room`): under TRADE_ROOM free cells, or no SURE_BLOCK free (the player's
    rule kept, design §8 Q3). The loop's `visit_due` asks this, with its own route and trip reasons."""
    return room(storage).low


def occupied(storage: Storage) -> float:
    """The share (0..1) of the loop's room its items take: the loop's items in the inventory and everything in the
    cube, of those cells, the inventory's free cells and the cube's. 1.0 with no room at all. For the HUD and the log;
    the visit waits on `room_low`, not on this."""
    pack = storage.pack
    rows = roomed(pack).cube or ()
    mine = sum(item.size[0] * item.size[1] for item in loot(pack, storage.own))
    in_inventory = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items)
    cube_cells = sum(len(row) for row in rows)
    in_cube = sum(row.count('.') for row in rows)
    taken = mine + cube_cells - in_cube
    total = mine + in_inventory + cube_cells
    return taken / total if total > 0 else 1.0


# The stash stop


@dataclass(frozen=True)
class Holdings:
    """What is carried: the pack, the player's own items, the loop's junk after Cain and the unidentified (unit ids)."""

    pack: Pack
    own: frozenset[Cell]
    junk: frozenset[int] = frozenset()
    unknown: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Put:
    """An item into the stash from the inventory or the cube, onto page `to` (0 personal, 1..5 shared) or, negative,
    a resource tab (-2 Gems, -3 Materials, -4 Runes)."""

    item: Carried
    source: Literal['inventory', 'cube']
    to: int

    @property
    def tab(self) -> bool:
        return self.to < 0


@dataclass(frozen=True)
class RuneCube:
    """One rune transmute at the stash (RUNES_AIM): RUNES_A_TAKE of `txt` plus an optional `gem` into one `into`."""

    txt: int
    into: int
    gem: int | None = None


@dataclass(frozen=True)
class StashStop:
    """The stash stop's plan.

    `puts`: tabs first, then pages in priority; `out_for_sale`: the cube's junk out for Jamella; `drops`: full stacks'
    materials put down; `shuffles`: inventory moves (item, top-left cell) freeing a block for a cube keeper;
    `into_cube`: junk with no cell left, into the cube; `stranded`: cube keepers only selling the junk first would let
    out; `parks`: junk parked on a shared page and taken back (PARK_JUNK); `full`: keepers no page has room for (the
    loop stops); `waits`: cube keepers left for the next visit (macros/town.py KEEPER_IN_CUBE); `runes`: transmutes
    made last, the cube empty; `rune_puts`: runes onto stacks the transmutes made room on."""

    puts: tuple[Put, ...] = ()
    out_for_sale: tuple[Carried, ...] = ()
    drops: tuple[Carried, ...] = ()
    deposit_to: int | None = None
    shuffles: tuple[Move, ...] = ()
    into_cube: tuple[Carried, ...] = ()
    stranded: tuple[Carried, ...] = ()
    parks: tuple[Put, ...] = ()
    full: tuple[Carried, ...] = ()
    waits: tuple[Carried, ...] = ()
    runes: tuple[RuneCube, ...] = ()
    rune_puts: tuple[Put, ...] = ()

    @property
    def idle(self) -> bool:
        busy = self.puts or self.out_for_sale or self.drops or self.runes
        return not busy and self.deposit_to is None

    def pages(self) -> tuple[int, ...]:
        """The pages the puts go to, in priority (no tabs)."""
        used = {put.to for put in self.puts if not put.tab}
        return tuple(page for page in PAGE_PRIORITY if page in used)


def _cells(item: Carried) -> int:
    return item.size[0] * item.size[1]


def _largest_first(items: Iterable[Carried]) -> list[Carried]:
    return sorted(items, key=lambda i: (-_cells(i), -i.size[1], i.y, i.x, i.unit_id))


def _place(rows: dict[int, tuple[str, ...]], items: Iterable[Carried]) -> dict[int, int]:
    placed: dict[int, int] = {}
    for item in _largest_first(items):
        for index in PAGE_PRIORITY:
            if index not in rows:
                continue
            lines = Grid(rows[index])
            spot = lines.first_spot(item.size)
            if spot is not None:
                rows[index] = lines.take(spot, item.size)
                placed[item.unit_id] = index
                break
    return placed


def place(pages: Sequence[Page], items: Sequence[Carried]) -> dict[int, int]:
    """The page each item goes onto (unit id -> page index), the largest first, by PAGE_PRIORITY; no room: absent."""
    return _place({page.index: page.rows for page in pages}, items)


def out_now(rows: Sequence[str], items: Sequence[Carried]) -> tuple[Carried, ...]:
    """Those of `items`, in order, that fit together into `rows`, each at its first free block (as `cube.unpack`)."""
    lines, out = Grid(rows), []
    for item in items:
        spot = lines.first_spot(item.size)
        if spot is not None:
            lines = lines.take(spot, item.size)
            out.append(item)
    return tuple(out)


def _without(pack: Pack, gone: Iterable[Carried]) -> Pack:
    units = {item.unit_id for item in gone}
    return replace(pack, items=tuple(i for i in pack.items if i.unit_id not in units))


def _over(item: Carried, at: tuple[int, int], size: tuple[int, int]) -> bool:
    return (
        item.x < at[0] + size[0]
        and at[0] < item.x + item.size[0]
        and item.y < at[1] + size[1]
        and at[1] < item.y + item.size[1]
    )


def _settled(
    work: Grid,
    movers: Sequence[Carried],
    stay: Sequence[Carried],
    cube: Grid | None,
    block: tuple[int, int],
    junk: Set[int],
) -> tuple[list[Move], list[Carried], Grid | None, Grid] | None:
    """Where each of `movers` goes in `work` (the block to free already taken), the largest first: a key stack where
    the build's block stays free once the junk is sold (`stay`: what the visit ends with); junk at its first free block,
    else into `cube`; the unidentified at its first free block, never into the cube (Cain's). Returns the moves, the
    junk into the cube, the cube's rows and the final inventory; None when one finds no room."""
    moves: list[Move] = []
    into: list[Carried] = []
    kept: list[Carried] = []  # keys and unidentified at their new cells
    for item in _largest_first(movers):
        spots = list(work.spots(item.size))
        if item.txt == KEY_CLASS and spots:

            def rank(at: tuple[int, int], i: Carried = item) -> tuple[bool, int, int, int]:
                final = Grid.from_items([*stay, *kept, replace(i, x=at[0], y=at[1])], INVENTORY_SIZE)
                return final.has_room(block), final.largest_block(), -at[1], -at[0]

            spot = max(spots, key=rank)
        elif spots:
            spot = spots[0]
        elif item.unit_id in junk and cube is not None and (inside := cube.first_spot(item.size)) is not None:
            cube = cube.take(inside, item.size)
            into.append(item)
            continue
        else:
            return None
        if item.unit_id not in junk:
            kept.append(replace(item, x=spot[0], y=spot[1]))
        moves.append((item, spot))
        work = work.take(spot, item.size)
    return moves, into, cube, Grid.from_items([*stay, *kept], INVENTORY_SIZE)


def _opening(
    lines: Grid,
    items: Sequence[Carried],
    movable: Set[int],
    junk: Set[int],
    size: tuple[int, int],
    cube: Grid | None,
    block: tuple[int, int],
) -> tuple[list[Move], list[Carried], Grid | None] | None:
    """The cheapest way to free a block of `size` in `lines` by moving only `movable` items (`_settled`): fewest into
    the cube, then the build's block free at the end, then fewest moves; None when none frees one."""
    best: tuple[tuple[int, bool, int, int, int, int], list[Move], list[Carried], Grid | None] | None = None
    for y in range(len(lines) - size[1] + 1):
        for x in range(len(lines[0]) - size[0] + 1):
            movers = [i for i in items if _over(i, (x, y), size)]
            if not movers or any(i.unit_id not in movable for i in movers):
                continue
            freed = lines
            for item in movers:
                freed = Grid(
                    ''.join(
                        '.' if item.x <= col < item.x + item.size[0] and item.y <= row < item.y + item.size[1] else cell
                        for col, cell in enumerate(line)
                    )
                    for row, line in enumerate(freed)
                )
            if not freed.fits((x, y), size):
                continue  # a cell of it is a keeper's planned before, not an item's
            stay = [i for i in items if i not in movers and i.unit_id not in junk]
            settled = _settled(freed.take((x, y), size), movers, stay, cube, block, junk)
            if settled is None:
                continue
            moves, into, after_cube, final = settled
            rank = (len(into), not final.has_room(block), len(moves) + len(into), -final.largest_block(), y, x)
            if best is None or rank < best[0]:
                best = (rank, moves, into, after_cube)
    return None if best is None else best[1:]


def unread_way_for_cube(pack: Pack, keeper: Carried, junk: Set[int], block: tuple[int, int]) -> tuple[Move, ...]:
    """Inventory-only junk moves that let an unread-stash scan take a cube keeper out (visit.py `_stash`). No page is
    predicted; the cube is not used as room, so junk never takes the keeper's space."""
    if pack.inventory.has_room(keeper.size):
        return ()
    found = _opening(pack.inventory, pack.items, junk, junk, keeper.size, None, block)
    return tuple(found[0]) if found is not None and not found[1] else ()


def _make_way(
    items: Sequence[Carried],
    keepers: Sequence[Carried],
    pages: dict[int, tuple[str, ...]],
    movable: Set[int],
    junk: Set[int],
    cube: Grid | None,
    block: tuple[int, int],
) -> tuple[tuple[Move, ...], tuple[Carried, ...], tuple[Carried, ...], tuple[Carried, ...]]:
    """Step (iv): for each cube keeper with room on a page but no block in the inventory `items`, the moves of
    `movable` items that free one, else junk into `cube`. Returns the moves, the junk into the cube, the stranded and
    the homeless keepers (`StashStop.stranded`, `StashStop.full`)."""
    trial = dict(pages)
    now = list(items)
    planned: list[tuple[tuple[int, int], tuple[int, int]]] = []  # the keepers' blocks, as `out_now` takes them
    moves: list[Move] = []
    into: list[Carried] = []
    stranded: list[Carried] = []
    homeless: list[Carried] = []

    def lines(sold: bool = False) -> Grid:
        rows = Grid.from_items((i for i in now if not (sold and i.unit_id in junk)), INVENTORY_SIZE)
        for at, size in planned:
            rows = rows.take(at, size)
        return rows

    for keeper in keepers:
        if not _place(dict(trial), [keeper]):
            homeless.append(keeper)
            continue
        spot = lines().first_spot(keeper.size)
        if spot is None:
            found = _opening(lines(), now, movable, junk, keeper.size, cube, block)
            if found is None:
                if lines(sold=True).has_room(keeper.size):
                    stranded.append(keeper)
                continue
            made, went, cube = found
            moves += made
            into += went
            cells = {item.unit_id: cell for item, cell in made}
            gone = {item.unit_id for item in went}
            now = [
                replace(i, x=cells[i.unit_id][0], y=cells[i.unit_id][1]) if i.unit_id in cells else i
                for i in now
                if i.unit_id not in gone
            ]
            spot = lines().first_spot(keeper.size)
            if spot is None:
                continue
        planned.append((spot, keeper.size))
        _place(trial, [keeper])
    return tuple(moves), tuple(into), tuple(stranded), tuple(homeless)


def _shuffled(pack: Pack, stop: StashStop) -> Pack:
    """`pack` with the stop's moves aside made and its junk into the cube gone (`after` puts it in the cube)."""
    items = list(pack.items)
    for moved, (x, y) in stop.shuffles:
        items = [replace(i, x=x, y=y) if i.unit_id == moved.unit_id else i for i in items]
    into = {i.unit_id for i in stop.into_cube}
    return replace(pack, items=tuple(i for i in items if i.unit_id not in into))


def stash_stop(
    h: Holdings,
    view: StashView,
    block: tuple[int, int] = BIG_BLOCK,
    *,
    deposit_to: int | None = None,
    park: bool | None = None,
) -> StashStop:
    """The stash stop's plan (macros/town-plan.md §2.2 2): which of the loop's items goes onto which tab or page. Junk
    and unidentified stay (Jamella's, Cain's); the player's own are never touched. `block`: the inventory's block the
    visit leaves free (macros/town.py `Needs.block`).

    (i, ii) a resource onto its tab while its stack has room, each counted; a full stack's material is put down, its
    rune or gem stays. (iii) inventory keepers onto `place`'s pages. (iv) cube keepers out through the room left, by
    moves aside, junk into the cube, or (`park`, default PARK_JUNK) junk parked on a page; else stranded. (v) the cube's
    junk and full stacks out for Jamella as room allows (none with a park). (vii) the key stack moved to free
    `block`."""
    stop = _planned(h, view, block, deposit_to, ())
    assert stop is not None  # nothing parked: always planned
    if not ((PARK_JUNK if park is None else park) and stop.stranded):
        return stop
    # Try each junk item alone, the largest first, then all: the most cube keepers out, then the fewest parked
    junk = [i for i in loot(h.pack, h.own) if i.unit_id in h.junk and i.unit_id not in h.unknown]
    tries = [(i,) for i in _largest_first(junk)] + ([tuple(junk)] if len(junk) > 1 else [])
    best, rank = stop, (-_through(stop), 0)
    for parked in tries:
        trial = _planned(h, view, block, deposit_to, parked)
        if trial is not None and (-_through(trial), len(trial.parks)) < rank:
            best, rank = trial, (-_through(trial), len(trial.parks))
    return best


def _through(stop: StashStop) -> int:
    return sum(1 for put in stop.puts if put.source == 'cube' and not put.tab)


def _lands(rows: dict[int, tuple[str, ...]], puts: Iterable[tuple[Carried, int]]) -> bool:
    """Whether each of `puts`, in order, finds its first free block on its page (as a Ctrl + click); `rows` updated."""
    for item, index in puts:
        spot = Grid(rows[index]).first_spot(item.size) if index in rows else None
        if spot is None:
            return False
        rows[index] = Grid(rows[index]).take(spot, item.size)
    return True


def _park_pages(
    pages: dict[int, tuple[str, ...]], before: Sequence[Put], later: Sequence[Put], parked: Sequence[Carried]
) -> tuple[Put, ...] | None:
    """The shared page each of `parked` goes onto, in click order (`before`, the parks, `later`), so no park takes a
    block a later keeper's put needs; None when one finds no page."""
    parks: list[Put] = []
    for item in _largest_first(parked):
        for index in SHARED_PRIORITY:
            if index not in pages:
                continue
            trial = [*parks, Put(item, 'inventory', index)]
            seq = [(p.item, p.to) for p in (*before, *trial, *later)]
            if _lands(dict(pages), seq):
                parks = trial
                break
        else:
            return None
    return tuple(parks)


def _planned(
    h: Holdings, view: StashView, block: tuple[int, int], deposit_to: int | None, parked: Sequence[Carried]
) -> StashStop | None:
    """`stash_stop`'s plan with `parked` junk out of the inventory; None when one finds no page or no room back."""
    pack, keep = h.pack, h.junk | h.unknown
    mine = [i for i in loot(pack, h.own) if i.unit_id not in keep]
    cubed = [i for i in pack.in_cube if i.unit_id not in keep]
    tabs = resource_tabs()
    took: Counter[int] = Counter()

    def room(item: Carried) -> bool:
        if view.room(item.txt) - took[item.txt] > 0:
            took[item.txt] += 1
            return True
        return False

    tab_puts: list[Put] = []
    drops: list[Carried] = []
    sale: list[Carried] = []
    for item in (i for i in cubed if i.txt in RESOURCES):
        if room(item):
            tab_puts.append(Put(item, 'cube', -tabs[item.txt]))
        elif tabs[item.txt] in (RUNES_TAB, MATERIALS_TAB) and not is_potion(item.txt):
            # Out of the cube: a material to be put down, a rune onto its stack after the transmutes
            sale.append(item)
    for item in (i for i in mine if i.txt in RESOURCES):
        if room(item):
            tab_puts.append(Put(item, 'inventory', -tabs[item.txt]))
        elif tabs[item.txt] == MATERIALS_TAB and not is_potion(item.txt):
            drops.append(item)
    first_rows = {page.index: page.rows for page in view.pages}
    rows = dict(first_rows)
    keepers = [i for i in mine if i.txt not in RESOURCES]
    on_pages = _place(rows, keepers)
    gone = [put.item for put in tab_puts if put.source == 'inventory'] + drops
    gone += [i for i in keepers if i.unit_id in on_pages]
    staying = _without(pack, [*gone, *parked])
    # The cube's keepers come out together, the tallest first (cube.py `unpack`), and only where a page has room
    cube_keepers = sorted((i for i in cubed if i.txt not in RESOURCES), key=lambda i: (-i.size[1], -_cells(i)))
    # Movable aside: the loop's junk, key stacks and the unidentified (rca/2026-10-18/town-remaining-findings.md §1).
    # Never the player's own: "we shouldn't sell our own equipment" (2026-10-17); "shuffle can move unid items"
    # (2026-10-18), but never into the cube
    loop_junk = {i.unit_id for i in loot(staying, h.own) if i.unit_id in h.junk and i.unit_id not in h.unknown}
    waiting = {i.unit_id for i in loot(staying, h.own) if i.unit_id in h.unknown}
    # A key stack on the player's cells (`h.own`: the protected cells, macros/volatile.py) is the player's: never moved
    # aside (2026-10-25, rca/2026-10-25/keys-protected-findings.md)
    keys = {
        i.unit_id
        for i in staying.items
        if i.txt == KEY_CLASS and i.size == (1, 1) and (i.txt, i.x, i.y) not in h.own
    }  # fmt: skip
    cube_then: Grid | None = None
    if any(i.txt == CUBE_CLASS for i in pack.items):
        # The cube with its keepers still in, its resources out
        tabbed = {put.item.unit_id for put in tab_puts if put.source == 'cube'}
        cube_then = Grid.from_items((i for i in pack.in_cube if i.unit_id not in tabbed), CUBE_SIZE)
    shuffles, into_cube, stranded, homeless = _make_way(
        staying.items, cube_keepers, rows, loop_junk | keys | waiting, loop_junk, cube_then, block
    )
    moved = _shuffled(staying, StashStop(shuffles=shuffles, into_cube=into_cube))
    left = moved.inventory
    trial = dict(rows)
    paged = _place(trial, out_now(left, cube_keepers))
    through = out_now(left, [i for i in cube_keepers if i.unit_id in paged])
    on_pages |= _place(rows, through)
    for item in through:
        spot = left.first_spot(item.size)
        if spot is not None:
            left = left.take(spot, item.size)
    junk = [i for i in pack.in_cube if i.unit_id in h.junk]
    out_for_sale = () if parked else out_now(left, sorted([*junk, *sale], key=lambda i: (-i.size[1], -_cells(i))))
    by_page = sorted(
        [Put(i, 'inventory', on_pages[i.unit_id]) for i in keepers if i.unit_id in on_pages]
        + [Put(i, 'cube', on_pages[i.unit_id]) for i in through],
        key=lambda put: (PAGE_PRIORITY.index(put.to), put.source != 'inventory', -_cells(put.item), -put.item.size[1]),
    )
    parks: tuple[Put, ...] = ()
    if parked:
        # Parks are clicked between the first puts and the cube keepers that come out after them (visit.py)
        tallest = sorted(through, key=lambda i: (-i.size[1], -_cells(i)))
        early = {i.unit_id for i in out_now(pack.inventory, tallest)}
        before = [put for put in by_page if put.source == 'inventory' or put.item.unit_id in early]
        later = [put for put in by_page if put.source == 'cube' and put.item.unit_id not in early]
        found = _park_pages(first_rows, before, later, parked)
        if found is None or len(out_now(moved.inventory, _largest_first(parked))) < len(parked):
            return None  # no page for one, or no room for it back: never left in the stash
        parks = found
    stop = StashStop(
        tuple(sorted(tab_puts, key=lambda put: put.source != 'cube')) + tuple(by_page),
        out_for_sale,
        tuple(drops),
        deposit_to=deposit_to,
        shuffles=shuffles,
        into_cube=into_cube,
        stranded=stranded,
        parks=parks,
        full=tuple(i for i in keepers if i.unit_id not in on_pages) + homeless,
        waits=tuple(i for i in cube_keepers if i.unit_id not in on_pages and i not in homeless),
    )
    return _runes(stop, h, view, took)


def _runes(stop: StashStop, h: Holdings, view: StashView, took: Mapping[int, int]) -> StashStop:
    """`stop` with its rune transmutes (RUNES_AIM), only when the stop leaves the cube empty (anything else in it would
    join the recipe), and the loop's runes onto the stacks the transmutes made room on."""
    if all(i.txt != CUBE_CLASS for i in h.pack.items):
        return stop
    left = after(h.pack, stop)
    if left.in_cube:
        return stop
    counts = Counter(dict(view.stacks))
    counts.update(took)
    runes = rune_transmutes(counts)
    if not runes:
        return stop
    for made in runes:
        counts[made.txt] -= RUNES_A_TAKE
        counts[made.into] += 1
        if made.gem is not None:
            counts[made.gem] -= 1
    waiting = h.junk | h.unknown
    late: list[Put] = []
    for item in loot(left, h.own):
        if item.txt in RUNE_CLASSES and item.unit_id not in waiting and counts[item.txt] < STACK_MOST:
            counts[item.txt] += 1
            late.append(Put(item, 'inventory', -RUNES_TAB))
    return replace(stop, runes=runes, rune_puts=tuple(late))


Recipes = Callable[[int], RuneRecipe | None]  # a rune class's recipe (`rune_recipe`)


def rune_transmutes(
    counts: Mapping[int, int], most: int = RUNE_TRANSMUTES, recipe: Recipes = rune_recipe
) -> tuple[RuneCube, ...]:
    """Up to `most` rune transmutes from the stacks' counts (class -> count, gems too): one at a time, the fullest stack
    over RUNES_AIM first (the smaller rune on a tie), each allowed by `_cubed`."""
    counts = Counter(counts)
    made: list[RuneCube] = []
    while len(made) < most:
        ready = [txt for txt in sorted(counts) if counts[txt] > RUNES_AIM and _cubed(txt, counts, recipe) is not None]
        if not ready:
            break
        txt = max(ready, key=lambda t: (counts[t], -t))
        step = _cubed(txt, counts, recipe)
        assert step is not None
        counts[txt] -= RUNES_A_TAKE
        counts[step.into] += 1
        if step.gem is not None:
            counts[step.gem] -= 1
        made.append(step)
    return tuple(made)


def _cubed(txt: int, counts: Mapping[int, int], recipe: Recipes) -> RuneCube | None:
    """The transmute of `txt` (cubemain.txt via `rune_recipe`), None when `_why_not` names a reason."""
    return _why_not(txt, counts, recipe)[0]


def _why_not(txt: int, counts: Mapping[int, int], recipe: Recipes) -> tuple[RuneCube | None, str]:
    found = recipe(txt) if txt in RUNE_CLASSES else None
    if found is None:
        return None, 'no recipe'
    if txt == BER or BER in found.gems:
        return None, 'Ber Runes are kept for Enigma'
    if found.runes != RUNES_A_TAKE or len(found.gems) > 1:
        return None, f'its recipe takes other than three runes and a gem ({found.description})'
    gem = found.gems[0] if found.gems else None
    if gem is not None and counts.get(gem, 0) < 1:
        return None, f'no {_class_name(gem)} in the stash for its recipe ({found.description})'
    if counts.get(found.into, 0) >= STACK_MOST:
        return None, 'the stack it makes is full'
    return RuneCube(txt, found.into, gem), ''


def _class_name(txt: int) -> str:
    return metadata()['bases'].get(str(txt), {}).get('name', str(txt))


def uncubed(counts: Mapping[int, int], recipe: Recipes = rune_recipe) -> tuple[tuple[int, str], ...]:
    """The rune stacks over RUNES_AIM no transmute takes down, each with why (for the log)."""
    found = []
    for txt, count in sorted(counts.items()):
        if txt not in RUNE_CLASSES or count <= RUNES_AIM or recipe(txt) is None:
            continue
        step, why = _why_not(txt, counts, recipe)
        if step is None:
            found.append((txt, why))
    return tuple(found)


def after(pack: Pack, stop: StashStop) -> Pack:
    """`pack` as the stop leaves it, simulated: puts and drops gone, moves aside made, the cube's junk and the parked
    junk back in the inventory at first free blocks, the junk into the cube placed as the cube was then."""
    out = {item.unit_id for item in stop.out_for_sale}
    gone = {put.item.unit_id for put in (*stop.puts, *stop.rune_puts)} | {item.unit_id for item in stop.drops}
    parked = {put.item.unit_id for put in stop.parks}
    shuffled = _shuffled(pack, stop)
    items = [i for i in shuffled.items if i.unit_id not in gone | parked]
    rows = Grid.from_items(items, INVENTORY_SIZE)
    for item in (*stop.out_for_sale, *_largest_first(put.item for put in stop.parks)):
        spot = rows.first_spot(item.size)
        if spot is not None:
            rows = rows.take(spot, item.size)
            items.append(replace(item, x=spot[0], y=spot[1]))
    in_cube = tuple(i for i in pack.in_cube if i.unit_id not in gone | out)
    if stop.into_cube:
        tabbed = {put.item.unit_id for put in stop.puts if put.source == 'cube' and put.tab}
        then = Grid.from_items((i for i in pack.in_cube if i.unit_id not in tabbed), CUBE_SIZE)
        for item in stop.into_cube:
            spot = then.first_spot(item.size)
            if spot is not None:
                then = then.take(spot, item.size)
                in_cube += (replace(item, x=spot[0], y=spot[1]),)
    cube = Grid.from_items(in_cube, CUBE_SIZE)
    return replace(
        pack,
        items=tuple(items),
        in_cube=in_cube,
        cube_items=frozenset(i.unit_id for i in in_cube),
        cube=cube if pack.cube is not None or in_cube else pack.cube,
    )


def surplus(carried: Sequence[Carried], full: StashView | Set[int]) -> tuple[Carried, ...]:
    """The flawless gems of `carried` sold at Jamella: only kinds whose flawless and perfect stacks are both full, less
    GEMS_A_KIND a kind and GEMS_KEPT in all kept for the cube (the kinds with the most first)."""
    full = full.full() if isinstance(full, StashView) else full
    kinds = Counter(i.txt for i in carried if i.txt in full and perfect_of(i.txt) in full)
    kept: dict[int, int] = {}
    room = GEMS_KEPT
    for txt, count in sorted(kinds.items(), key=lambda kind: (-kind[1], kind[0])):
        kept[txt] = min(count, GEMS_A_KIND, room)
        room -= kept[txt]
    sold = []
    for item in carried:
        if item.txt not in kept:
            continue
        if kept[item.txt] > 0:
            kept[item.txt] -= 1
        else:
            sold.append(item)
    return tuple(sold)
