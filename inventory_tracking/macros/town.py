"""One planned town visit (macros/town-plan.md §2): the types, the stash stop's plan, the trade trigger's room, the
gems sold, the gold deposited, the staff topped up and what a visit leaves (`contract`). Pure: no input, no reads;
macros/visit.py `visit` walks the stops. The stash is read from memory (`StashView`), so every put is planned before a
click: "we visit the stash only ONE time" (the player, 2026-10-18). Evidence for the tuned numbers: history/town.md.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import dataclass, replace
from enum import Enum
from typing import Literal

from inventory_tracking.game.layout import STACK_MOST
from inventory_tracking.game.records import Carried, Pack, Page, StashView, Teleport
from inventory_tracking.items.grid import CUBE_SIZE, INVENTORY_SIZE, Grid
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros.cube import (
    BIG_BLOCK,
    CUBE_CLASS,
    KEY_CLASS,
    Move,
    loot,
    perfect_of,
    rune_recipe,
)
from inventory_tracking.macros.portal import FROM_TOME, PortalSource
from inventory_tracking.macros.shop import MIN_STOCK, SALE_MOST
from inventory_tracking.macros.stash import (
    MATERIALS_TAB,
    PAGE_PRIORITY,
    RESOURCES,
    SHARED_PRIORITY,
    is_potion,
    resource_tabs,
)


__all__ = [
    'STACK_MOST',
    'STACK_ROOM',
    'TRADE_ROOM',
    'Cell',
    'Contract',
    'Exit',
    'Holdings',
    'Needs',
    'Page',
    'Put',
    'RuneCube',
    'StashStop',
    'StashView',
    'after',
    'contract',
    'deposit_to',
    'kept_gem',
    'named',
    'out_now',
    'place',
    'rune_transmutes',
    'sold_full',
    'stash_stop',
    'surplus',
    'tops_up',
    'uncubed',
]

Cell = tuple[int, int, int]  # an item's class and cell, as `Loop.own` tells the player's
STACK_ROOM = 20  # the player, 2026-10-18: "at least 20 free slots" on a resource stack (step 5)
RUNES_TAB = 4  # stash.py `resource_tabs`: 2 Gems, 3 Materials, 4 Runes
# The loop's unidentified and junk wait until fewer than this many cells are free in the inventory and cube together,
# then one whole visit: "trade ... by remaining free slots" (the player, 2026-10-17). A 2 x 4 fits nowhere below it.
TRADE_ROOM = 8
# A full stack's flawless gems kept for the cube: at most GEMS_A_KIND of a kind, GEMS_KEPT in all (unbounded, they
# filled the cube); the rest sold only once the perfect stack is full too: "we must cube them up first" (2026-10-18).
GEMS_A_KIND = 3
GEMS_KEPT = 6
DEPOSIT_NEAR = 2 * SALE_MOST  # gold this near the cap is deposited at the stash (macros/stash.py `deposit`)
DEPOSIT_ROOM = 250_000  # down to the cap less this: room for a session's sales, Teleport still on (loop.py TELEPORT_ON)
REPAIR_SHARE = 1.2  # the deposit leaves the expected repair and this share over it carried (repairs from carried gold)
# Junk holding the only block a cube keeper could come out through is parked on a shared page and taken back before
# the stash closes: "junk can be temporarily stored in stash, but sold after" (the player, 2026-10-18).
PARK_JUNK = True
# A cube keeper the visit cannot get out (room on a page, none in the inventory) waits for the next visit, named as
# deferred, not a miss: "keeper can wait in cube" (the player, 2026-10-18). No page with room: the loop stops.
KEEPER_IN_CUBE = True
# Rune stacks over RUNES_AIM: three runes out to the cube and transmuted into the next (cube.py `rune_recipe`; Thul to
# Lem take a gem from the Gems tab, Pul up take two runes: not handled), the fullest first, at most RUNE_TRANSMUTES a
# visit, never a Ber Rune: "cubed, aim to 80 or lower" (the player, 2026-10-18). Timing evidence: history/town.md.
RUNES_AIM = 80
RUNE_TRANSMUTES = 3
RUNES_A_TAKE = 3  # what a Ctrl + Shift + right click on a stack moves into the cube (the player, 14:28 on 2026-10-18)
# Ber Runes are kept for Enigma (the player, 2026-10-09)
BER = next(txt for txt, row in RUNE_CLASSES.items() if row['name'] == 'Ber Rune')


@dataclass(frozen=True)
class Needs:
    """What the visit leaves the character with: the inventory's free block ("for warlock: this is 2x4 continuous
    space", the player, 2026-10-18), the keys (Kind.keys), how Town Portal is cast, Identify charges, a stack's room."""

    block: tuple[int, int] = BIG_BLOCK
    keys: int = 24
    portals: PortalSource = FROM_TOME
    identifies: int = 20
    stack_room: int = STACK_ROOM


@dataclass(frozen=True)
class Holdings:
    """What is carried: the pack, the player's own items, the loop's junk after Cain and the unidentified (unit ids)."""

    pack: Pack
    own: frozenset[Cell]
    junk: frozenset[int] = frozenset()
    unknown: frozenset[int] = frozenset()


class Exit(Enum):
    """How a visit ends: the waypoint (a game's start), none (Save and Exit follows), the portal back (a trip)."""

    WAYPOINT = 'waypoint'
    LEAVE = 'leave'
    PORTAL = 'portal'


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
    loop stops); `waits`: cube keepers left for the next visit (KEEPER_IN_CUBE); `runes`: transmutes made last, the cube
    empty; `rune_puts`: runes onto stacks the transmutes made room on."""

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


@dataclass(frozen=True)
class Contract:
    """What a visit leaves (§2.2 6), checked after it, its misses logged. `stash_full`: keepers no page had room for;
    the loop stops: "if stash is full - we need to stop loop" (the player, 2026-10-18). `in_stash`: junk a park left on
    a page (a miss). `deferred`: cube keepers waiting for the next visit (KEEPER_IN_CUBE), not a miss."""

    cube: int
    block_free: bool
    loop_items: int
    junk_left: int
    keys: int | None
    portals: str
    parked_on_ground: int
    misses: tuple[str, ...] = ()
    stash_full: tuple[str, ...] = ()
    in_stash: int = 0
    deferred: tuple[str, ...] = ()


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


NEEDS = Needs()  # the Warlock's in the Lower Kurast loop


def stash_stop(
    h: Holdings,
    view: StashView,
    needs: Needs = NEEDS,
    *,
    deposit_to: int | None = None,
    park: bool | None = None,
) -> StashStop:
    """The stash stop's plan (§2.2 2): which of the loop's items goes onto which tab or page. Junk and unidentified stay
    (Jamella's, Cain's); the player's own are never touched.

    (i, ii) a resource onto its tab while its stack has room, each counted; a full stack's material is put down, its
    rune or gem stays. (iii) inventory keepers onto `place`'s pages. (iv) cube keepers out through the room left, by
    moves aside, junk into the cube, or (`park`, default PARK_JUNK) junk parked on a page; else stranded. (v) the cube's
    junk and full stacks out for Jamella as room allows (none with a park). (vii) the key stack moved to free
    `needs.block`."""
    stop = _planned(h, view, needs, deposit_to, ())
    assert stop is not None  # nothing parked: always planned
    if not ((PARK_JUNK if park is None else park) and stop.stranded):
        return stop
    # Try each junk item alone, the largest first, then all: the most cube keepers out, then the fewest parked
    junk = [i for i in loot(h.pack, h.own) if i.unit_id in h.junk and i.unit_id not in h.unknown]
    tries = [(i,) for i in _largest_first(junk)] + ([tuple(junk)] if len(junk) > 1 else [])
    best, rank = stop, (-_through(stop), 0)
    for parked in tries:
        trial = _planned(h, view, needs, deposit_to, parked)
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
    h: Holdings, view: StashView, needs: Needs, deposit_to: int | None, parked: Sequence[Carried]
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
    keys = {i.unit_id for i in staying.items if i.txt == KEY_CLASS and i.size == (1, 1)}
    cube_then: Grid | None = None
    if any(i.txt == CUBE_CLASS for i in pack.items):
        # The cube with its keepers still in, its resources out
        tabbed = {put.item.unit_id for put in tab_puts if put.source == 'cube'}
        cube_then = Grid.from_items((i for i in pack.in_cube if i.unit_id not in tabbed), CUBE_SIZE)
    shuffles, into_cube, stranded, homeless = _make_way(
        staying.items, cube_keepers, rows, loop_junk | keys | waiting, loop_junk, cube_then, needs.block
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


def rune_transmutes(counts: Mapping[int, int], most: int = RUNE_TRANSMUTES) -> tuple[RuneCube, ...]:
    """Up to `most` rune transmutes from the stacks' counts (class -> count, gems too): one at a time, the fullest stack
    over RUNES_AIM first (the smaller rune on a tie), each allowed by `_cubed`."""
    counts = Counter(counts)
    made: list[RuneCube] = []
    while len(made) < most:
        ready = [txt for txt in sorted(counts) if counts[txt] > RUNES_AIM and _cubed(txt, counts) is not None]
        if not ready:
            break
        txt = max(ready, key=lambda t: (counts[t], -t))
        step = _cubed(txt, counts)
        assert step is not None
        counts[txt] -= RUNES_A_TAKE
        counts[step.into] += 1
        if step.gem is not None:
            counts[step.gem] -= 1
        made.append(step)
    return tuple(made)


def _cubed(txt: int, counts: Mapping[int, int]) -> RuneCube | None:
    """The transmute of `txt` (cubemain.txt via `rune_recipe`), None when `_why_not` names a reason."""
    return _why_not(txt, counts)[0]


def _why_not(txt: int, counts: Mapping[int, int]) -> tuple[RuneCube | None, str]:
    recipe = rune_recipe(txt) if txt in RUNE_CLASSES else None
    if recipe is None:
        return None, 'no recipe'
    if txt == BER or BER in recipe.gems:
        return None, 'Ber Runes are kept for Enigma'
    if recipe.runes != RUNES_A_TAKE or len(recipe.gems) > 1:
        return None, f'its recipe takes other than three runes and a gem ({recipe.description})'
    gem = recipe.gems[0] if recipe.gems else None
    if gem is not None and counts.get(gem, 0) < 1:
        return None, f'no {_class_name(gem)} in the stash for its recipe ({recipe.description})'
    if counts.get(recipe.into, 0) >= STACK_MOST:
        return None, 'the stack it makes is full'
    return RuneCube(txt, recipe.into, gem), ''


def _class_name(txt: int) -> str:
    from inventory_tracking.items.metadata import metadata  # late: only the log's

    return metadata()['bases'].get(str(txt), {}).get('name', str(txt))


def uncubed(counts: Mapping[int, int]) -> tuple[tuple[int, str], ...]:
    """The rune stacks over RUNES_AIM no transmute takes down, each with why (for the log)."""
    found = []
    for txt, count in sorted(counts.items()):
        if txt not in RUNE_CLASSES or count <= RUNES_AIM or rune_recipe(txt) is None:
            continue
        step, why = _why_not(txt, counts)
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


def sold_full(full: Set[int]) -> frozenset[int]:
    """The full stacks' classes not picked up: runes (transmuted down, RUNES_AIM) and materials, never a potion: "just
    stop picking it up, there is no use for it" (the player, 2026-10-18). A full stack's gem is still picked up and
    kept for the cube: "we just left flawlest amethyst ... something is wrong" (2026-10-17)."""
    return frozenset(
        txt for txt in full if txt in RUNE_CLASSES or (resource_tabs().get(txt) == MATERIALS_TAB and not is_potion(txt))
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


def deposit_to(coins: int | None, cap: int | None, repair: int = 0) -> int | None:
    """The carried gold kept when depositing, None for no deposit (§2.3): near the cap a sale drops the excess on the
    ground. Never below REPAIR_SHARE of the expected repair (paid from carried gold only)."""
    if coins is None or cap is None or coins < cap - DEPOSIT_NEAR:
        return None
    return max(cap - DEPOSIT_ROOM, round(REPAIR_SHARE * repair))


def tops_up(staff: Teleport | None, in_session: bool, reported: bool) -> bool:
    """Whether a visit recharges the staff: "we must go to LK with all refilled" (the player, 2026-10-17), but once a
    session (`reported`): a second trip to Halbu for 5 charges cost ~8 s."""
    return staff is not None and in_session and not reported and staff.charges < staff.maximum


def kept_gem(item: Carried, full: Set[int]) -> bool:
    """A full stack's flawless gem, kept carried for the cube (`surplus`): no keeper the stash missed."""
    return item.txt in full and item.txt not in sold_full(full) and perfect_of(item.txt) is not None


def named(items: Iterable[Carried]) -> tuple[str, ...]:
    """Each item by quality, base name and cell, for the contract and the log: `set Battle Boots at (0, 0)`."""
    from inventory_tracking.items.metadata import metadata  # late: only the log's

    bases = metadata()['bases']
    return tuple(
        f'{QUALITY_WORDS.get(i.quality, "")} {bases.get(str(i.txt), {}).get("name", i.txt)} at ({i.x}, {i.y})'.strip()
        for i in items
    )


def _names(items: Sequence[Carried]) -> str:
    return ', '.join(named(items))


QUALITY_WORDS = {2: 'normal', 3: 'superior', 4: 'magic', 5: 'set', 6: 'rare', 7: 'unique', 8: 'crafted'}


def contract(
    pack: Pack,
    own: frozenset[Cell],
    needs: Needs,
    *,
    junk: Set[int] = frozenset(),
    full: Set[int] = frozenset(),
    restocked: bool = False,
    parked_left: int = 0,
    stash_full: Sequence[str] = (),
    in_stash: Sequence[Carried] = (),
    deferred: Sequence[Carried] = (),
) -> Contract:
    """What a visit left (§2.2 6), from the pack read after it. `misses` names each part short of the player's
    contract ("after the loop we must have: empty cube, all designated free space cells are free in the inventory",
    2026-10-18): cube items, the block taken, junk unsold, a keeper not stashed, keys or portals short, units on the
    ground, junk parked on a page. `stash_full` and `deferred` are named apart from the misses."""
    later = {i.unit_id for i in deferred if i.unit_id in pack.cube_items}
    # A full stack's flawless gem kept in the cube for its transmute is no miss either
    later |= {i.unit_id for i in pack.in_cube if kept_gem(i, full)}
    items = [*loot(pack, own), *pack.in_cube]
    junk_left = sum(1 for i in items if i.unit_id in junk)
    keepers = [
        i
        for i in items
        if i.unit_id not in junk | later and i.identified and not kept_gem(i, full) and i.txt not in sold_full(full)
    ]
    block = pack.inventory.has_room(needs.block)
    misses: list[str] = []
    cubed = [i for i in pack.in_cube if i.unit_id not in later]
    if cubed:
        misses.append(f'cube {len(cubed)} items ({_names(cubed)})')
    if not block:
        misses.append(f'block {needs.block[0]}x{needs.block[1]} taken')
    if junk_left:
        misses.append(f'junk left {junk_left}')
    if keepers:
        misses.append(f'{len(keepers)} keepers carried ({_names(keepers)})')  # named: what the stash stop missed
    keys = pack.keys
    if keys is not None and (keys < MIN_STOCK or (restocked and keys < needs.keys)):
        misses.append(f'keys {keys} of {needs.keys}')
    portals = needs.portals.count(pack)
    if portals is not None and portals < MIN_STOCK:
        misses.append(f'portals {portals}')
    if parked_left:
        misses.append(f'{parked_left} left on the ground')
    if in_stash:
        misses.append(f'{len(in_stash)} junk parked on a page ({_names(in_stash)})')
    said = str(portals) if needs.portals.stocked else f'from {needs.portals.name}'
    waiting = named(i for i in pack.in_cube if i.unit_id in later)
    return Contract(len(pack.in_cube), block, len(items), junk_left, keys, said, parked_left, tuple(misses),
                    tuple(stash_full), len(in_stash), waiting)  # fmt: skip
