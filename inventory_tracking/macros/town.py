"""One planned town visit (macros/town-plan.md §2): the types, and the stash stop's plan. Pure: no input, no reads.

The player, 2026-10-18 12:55: "when we're putting items to shared stash, we just brute forcing each tab, despite we
could exactly know where we can put items"; "we visit the stash only ONE time". The stash is read from memory in town
(world.py `StashView`: every page's rows, every resource stack's count), so where each item goes is planned before a
click: a resource onto its tab only while its stack has room (never a full stack's Ctrl + click), a keeper onto the page
whose free cells fit it (`place`, shared 3, 4, 5, 2, 1, then personal: no page tried and refused), a
cube keeper out through the room the inventory's keepers leave, the cube's junk out for Jamella as the room allows, a
full stack's material put down (no vendor buys one: the player, 10:37, "there is no use for it").

Step 1 of the plan's migration: the stash stop (`stash_stop`). Step 3: the trigger's room (TRADE_ROOM), the stacks no
longer kept (`sold_full`), the gems sold (`surplus`), the gold deposited (`deposit_to`), the staff topped up (`tops_up`)
and what a visit leaves (`contract`): macros/visit.py `visit` walks the stops once and checks it.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import dataclass, replace
from enum import Enum
from typing import Literal

from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros.cube import (
    BIG_BLOCK,
    CUBE_CLASS,
    KEY_CLASS,
    Move,
    fits,
    inventory_rows,
    largest_block,
    loot,
    perfect_of,
    room_for,
    rune_recipe,
    taken,
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
from inventory_tracking.macros.world import STACK_MOST, Carried, Pack, Page, StashView, Teleport


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
CUBE_SIZE = (3, 4)
# The trade (routes/lower-kurast-loop-plan.md §15; the player, 2026-10-17: "we need to perform mass identify at decard
# cain -> stash good -> sell junk -> return to loop"; then "probably we need to trade not by 2 junk items, but by
# remaining free slots"): the loop's unidentified items and its junk wait, in the inventory and the cube, until fewer
# than TRADE_ROOM cells are free in both together (a 2 x 4 shield, the largest candidate, fits nowhere); then the whole
# visit at once (macros/visit.py). (Counted by items before, 3 then 4 to Cain, 2 then 3 to her: Cain nearly every game
# for one item, the trade ~6.8 s a cycle, 12:00-12:30 on 2026-10-17.)
TRADE_ROOM = 8
# A full stash stack's flawless gems the loop keeps for the cube: at most GEMS_A_KIND of a kind (one transmute's) and
# GEMS_KEPT in all; the rest are sold at Jamella, but only once the perfect gem's stack is full too (the player, 09:51
# on 2026-10-18: "we don't need to do gem sale until we have 99 pgems of type and we must cube them up first").
# Kept with no bound, all seven kinds full, they filled the cube: no transmute had the room to empty it, a trade
# session every game, then the loop stood by a Flawless Sapphire and a Grand Charm with no room for either (09:22-09:45)
GEMS_A_KIND = 3
GEMS_KEPT = 6
DEPOSIT_NEAR = 2 * SALE_MOST  # gold this near the cap is deposited at the stash (macros/stash.py `deposit`)
DEPOSIT_ROOM = 250_000  # down to the cap less this: room for a session's sales, Teleport still on (loop.py TELEPORT_ON)
REPAIR_SHARE = 1.2  # the deposit leaves the expected repair and this share over it carried (repairs from carried gold)
# The stash as a buffer inside its stop (the player, 16:50 on 2026-10-18: "junk can be temporarily stored in stash, but
# sold after"): the inventory's junk that holds the only block a cube keeper could come out through is put onto a
# shared page with room, the keeper taken out and stashed, the junk taken back before the stash closes and sold at
# Jamella. A set Battle Boots (2 x 2) stayed in the cube three visits (16:30-16:35) behind a junk unique Fuscina
# (2 x 4); 15:06, 15:14 and 15:20 the same class
PARK_JUNK = True
# A cube keeper the visit cannot get out (room on a page, none in the inventory to come out through, even with a park)
# waits in the cube for the next visit: an accepted outcome, named on the contract as deferred, not a miss (the player,
# 17:50 on 2026-10-18: "keeper can wait in cube"). Not a keeper no page has room for: the stash is full, and the loop
# stops (`Contract.stash_full`)
KEEPER_IN_CUBE = True
# The 99 rune stacks (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower"; Tal Rune at 99 since 2026-10-17):
# at the stash stop, three runes of a stack over RUNES_AIM out to the cube and transmuted into the next rune
# (cubemain.txt by cube.py `rune_recipe`: El to Ort need no gem; Thul to Lem take one more, a chipped or flawed gem,
# taken from its stack on the Gems tab: the player, 18:31, "yes, loop should use required gems + runes"; Pul up take
# two runes, not handled), the rune made put onto its stack; the fullest stack first, at most RUNE_TRANSMUTES a visit;
# never a Ber Rune (BER). The gem transmute's log lines (`Macro: cube:
# three ...`, 12 of 2026-10-18 04:53-09:13) came 1.9 to 4.0 s after the stash stop's line, 2.8 s the median, the
# inventory and the cube opened and closed each time; this one stays in the open stash (a right click, the button, a
# Ctrl + Shift + click): 3 a visit is at most ~8 s and likely ~5 s, and takes 9 runes off: a 99 stack is at 80 within
# three visits, while the loop brings fewer than one rune of a kind a visit (10 Tal, 19 Ort in 122 visits on 10-18)
RUNES_AIM = 80
RUNE_TRANSMUTES = 3
RUNES_A_TAKE = 3  # what a Ctrl + Shift + right click on a stack moves into the cube (the player, 14:28 on 2026-10-18)
# Ber Runes are kept for Enigma (the player, 2026-10-09): no transmute ever takes one, whatever the data says
BER = next(txt for txt, row in RUNE_CLASSES.items() if row['name'] == 'Ber Rune')


@dataclass(frozen=True)
class Needs:
    """What the visit leaves the character with, from the build and the run kind: the inventory's free block (the
    Warlock's 2 x 4: the player, 2026-10-18, "for warlock: this is 2x4 continuous space"), the keys (Kind.keys: LK 24,
    Andariel 12), how Town Portal is cast, the Tome of Identify's charges and a resource stack's room."""

    block: tuple[int, int] = BIG_BLOCK
    keys: int = 24
    portals: PortalSource = FROM_TOME
    identifies: int = 20
    stack_room: int = STACK_ROOM


@dataclass(frozen=True)
class Holdings:
    """What is carried: the pack, the player's own items (`Loop.own`), the loop's items judged `vendor` after Cain
    (unit ids) and those still unidentified."""

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
    """An item into the stash: from the inventory (a Ctrl + click) or the cube (a resource by Ctrl + Shift on a
    resource tab; another out through the inventory first), onto page `to` (0 personal, 1..5 shared) or, negative, a
    resource tab (-2 Gems, -3 Materials, -4 Runes)."""

    item: Carried
    source: Literal['inventory', 'cube']
    to: int

    @property
    def tab(self) -> bool:
        return self.to < 0


@dataclass(frozen=True)
class RuneCube:
    """One transmute at the stash's cube (RUNES_AIM): RUNES_A_TAKE runes of class `txt` taken from its stack into the
    cube, with one gem of class `gem` from its stack when the recipe takes one, transmuted into one rune of class
    `into`, which goes onto its own stack."""

    txt: int
    into: int
    gem: int | None = None


@dataclass(frozen=True)
class StashStop:
    """The stash stop's plan: the puts grouped (the tabs, the personal page, the shared pages ascending), the cube's
    junk to the inventory for Jamella while the stash is open, the full stacks' materials put down, the gold to keep
    when depositing; `shuffles`: the inventory's
    junk and key stacks moved within it, in order, each to the cell given (its top-left), to free the block a cube
    keeper comes out into; `into_cube`: junk that finds no cell for it put into the cube instead (sold from there at
    Jamella), both in the interlude before the cube's keepers come out (`stash_stop` (iv)); `stranded`: the cube's
    keepers neither gets out, which the inventory's junk sold first would let out; `parks`: the inventory's junk put
    onto a shared page (`Put.to`) before the moves aside, so such a keeper comes out, and taken back into the inventory
    once the keepers are in, before the stash closes (PARK_JUNK); `full`: the keepers no page has room for (the stash is
    full: the loop stops, the player at 16:50 on 2026-10-18); `waits`: the cube's keepers with room on a page that stay
    in the cube (no way out, even with a park), for the next visit (KEEPER_IN_CUBE); `runes`: the rune transmutes made
    last, the cube empty, and `rune_puts`: the loop's runes whose stack had no room before them, onto it after
    (RUNES_AIM)."""

    puts: tuple[Put, ...] = ()
    out_for_sale: tuple[Carried, ...] = ()
    drops: tuple[Carried, ...] = ()
    deposit_to: int | None = None
    shuffles: tuple[Move, ...] = ()
    into_cube: tuple[Carried, ...] = ()
    # The cube's keepers with room on a page that no block, move aside or junk into the cube gets out of it, but the
    # inventory's junk once sold would: Jamella before the stash (macros/visit.py `visit`; 15:05:53 on 2026-10-18)
    stranded: tuple[Carried, ...] = ()
    parks: tuple[Put, ...] = ()
    full: tuple[Carried, ...] = ()
    waits: tuple[Carried, ...] = ()
    runes: tuple[RuneCube, ...] = ()
    rune_puts: tuple[Put, ...] = ()

    @property
    def idle(self) -> bool:
        """Whether the stop has nothing to do: no walk to the stash."""
        busy = self.puts or self.out_for_sale or self.drops or self.runes
        return not busy and self.deposit_to is None

    def pages(self) -> tuple[int, ...]:
        """The pages the puts go to, in storage priority (the tabs not among them)."""
        used = {put.to for put in self.puts if not put.tab}
        return tuple(page for page in PAGE_PRIORITY if page in used)


@dataclass(frozen=True)
class Contract:
    """What a visit leaves (§2.2 6): checked after it, its misses logged. `stash_full`: the keepers no stash page had
    room for, named (empty when the stash took all it was given): the loop stops on it (the player, 16:50 on 2026-10-18:
    "if stash is full - we need to stop loop"). Not the stranded case (room on a page, none in the inventory for the
    keeper to come out through), which a park of the junk makes (PARK_JUNK). `in_stash`: the junk a park left on a
    page (never meant to happen: a miss). `deferred`: the cube's keepers the visit could not get out, named, waiting in
    the cube for the next visit (KEEPER_IN_CUBE): neither a miss nor the stash full; their cells are the cube's, which
    the loop's room counts."""

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


def _spot(rows: Sequence[str], size: tuple[int, int]) -> tuple[int, int] | None:
    """The first cell (row by row) whose block of `size` is free in `rows`."""
    return next(((x, y) for y in range(len(rows)) for x in range(len(rows[0])) if fits(rows, (x, y), size)), None)


def _largest_first(items: Iterable[Carried]) -> list[Carried]:
    return sorted(items, key=lambda i: (-_cells(i), -i.size[1], i.y, i.x, i.unit_id))


def _place(rows: dict[int, tuple[str, ...]], items: Iterable[Carried]) -> dict[int, int]:
    """`items` largest first, each onto the first priority page with a block for it; `rows` updated."""
    placed: dict[int, int] = {}
    for item in _largest_first(items):
        for index in PAGE_PRIORITY:
            if index not in rows:
                continue
            lines = rows[index]
            spot = _spot(lines, item.size)
            if spot is not None:
                rows[index] = taken(lines, spot, item.size)
                placed[item.unit_id] = index
                break
    return placed


def place(pages: Sequence[Page], items: Sequence[Carried]) -> dict[int, int]:
    """The page each item goes onto (unit id -> page index): the largest first, with a free block on shared pages
    3, 4, 5, 2, 1, then personal. One with no room anywhere stays where it is."""
    return _place({page.index: page.rows for page in pages}, items)


def out_now(rows: Sequence[str], items: Sequence[Carried]) -> tuple[Carried, ...]:
    """Those of `items` (in their order) that come out of the cube into an inventory of `rows` together, each into the
    first free block (as `cube.unpack` takes them out)."""
    lines, out = tuple(rows), []
    for item in items:
        spot = _spot(lines, item.size)
        if spot is not None:
            lines = taken(lines, spot, item.size)
            out.append(item)
    return tuple(out)


def _without(pack: Pack, gone: Iterable[Carried]) -> Pack:
    units = {item.unit_id for item in gone}
    return replace(pack, items=tuple(i for i in pack.items if i.unit_id not in units))


def _rows_of(items: Iterable[Carried]) -> tuple[str, ...]:
    return inventory_rows(Pack(tuple(items)))


def _over(item: Carried, at: tuple[int, int], size: tuple[int, int]) -> bool:
    """Whether `item` takes a cell of the block of `size` at `at`."""
    return (
        item.x < at[0] + size[0]
        and at[0] < item.x + item.size[0]
        and item.y < at[1] + size[1]
        and at[1] < item.y + item.size[1]
    )


def _settled(
    work: tuple[str, ...],
    movers: Sequence[Carried],
    stay: Sequence[Carried],
    cube: tuple[str, ...] | None,
    block: tuple[int, int],
    junk: Set[int],
) -> tuple[list[Move], list[Carried], tuple[str, ...] | None, tuple[str, ...]] | None:
    """Where each of `movers` goes, the largest first, in the inventory `work` (the block to free already taken): a key
    stack to the cell that leaves the build's block free once the junk is sold (`stay`: what the visit ends with), else
    its largest free block, as `keys_move` scores; a junk item to its first free block, else into the first block of
    `cube` (None: no cube to take it); an unidentified item to its first free block (it stays carried, for Cain: never
    into the cube). The moves, the junk into the cube, the cube's rows and the inventory as the visit ends; None when
    one finds no room."""
    moves: list[Move] = []
    into: list[Carried] = []
    kept: list[Carried] = []  # the keys and the unidentified at their new cells: the visit ends with them
    for item in _largest_first(movers):
        spots = [(x, y) for y in range(len(work)) for x in range(len(work[0])) if fits(work, (x, y), item.size)]
        if item.txt == KEY_CLASS and spots:
            spot = max(
                spots,
                key=lambda at, i=item: (
                    room_for(final := _rows_of([*stay, *kept, replace(i, x=at[0], y=at[1])]), block),
                    largest_block(final),
                    -at[1],
                    -at[0],
                ),
            )
        elif spots:
            spot = spots[0]
        elif item.unit_id in junk and cube is not None and (inside := _spot(cube, item.size)) is not None:
            cube = taken(cube, inside, item.size)
            into.append(item)
            continue
        else:
            return None
        if item.unit_id not in junk:
            kept.append(replace(item, x=spot[0], y=spot[1]))
        moves.append((item, spot))
        work = taken(work, spot, item.size)
    return moves, into, cube, _rows_of([*stay, *kept])


def _opening(
    lines: tuple[str, ...],
    items: Sequence[Carried],
    movable: Set[int],
    junk: Set[int],
    size: tuple[int, int],
    cube: tuple[str, ...] | None,
    block: tuple[int, int],
) -> tuple[list[Move], list[Carried], tuple[str, ...] | None] | None:
    """The cheapest way to free a block of `size` in the inventory `lines` (`items` in it, and cells already planned
    for the cube's keepers) by moving only `movable` items aside (`_settled`; `junk` among them sold at Jamella, the
    rest carried on): none into the cube when moves within the inventory do it, then the build's block free at the
    visit's end, then the fewest moves; None when no block can be freed so."""
    best: tuple[tuple[int, bool, int, int, int, int], list[Move], list[Carried], tuple[str, ...] | None] | None = None
    for y in range(len(lines) - size[1] + 1):
        for x in range(len(lines[0]) - size[0] + 1):
            movers = [i for i in items if _over(i, (x, y), size)]
            if not movers or any(i.unit_id not in movable for i in movers):
                continue
            freed = lines
            for item in movers:
                freed = tuple(
                    ''.join(
                        '.' if item.x <= col < item.x + item.size[0] and item.y <= row < item.y + item.size[1] else cell
                        for col, cell in enumerate(line)
                    )
                    for row, line in enumerate(freed)
                )
            if not fits(freed, (x, y), size):
                continue  # a cell of it is a keeper's planned before, not an item's
            stay = [i for i in items if i not in movers and i.unit_id not in junk]
            settled = _settled(taken(freed, (x, y), size), movers, stay, cube, block, junk)
            if settled is None:
                continue
            moves, into, after_cube, final = settled
            rank = (len(into), not room_for(final, block), len(moves) + len(into), -largest_block(final), y, x)
            if best is None or rank < best[0]:
                best = (rank, moves, into, after_cube)
    return None if best is None else best[1:]


def unread_way_for_cube(pack: Pack, keeper: Carried, junk: Set[int], block: tuple[int, int]) -> tuple[Move, ...]:
    """Inventory-only junk moves that let an unread-stash scan take a cube keeper out (visit.py `_stash`).

    No stash page is predicted here. The caller tries the actual page after moving the junk, and keeps the junk
    carried for Jamella. The cube is excluded as temporary space so the keeper's space is not consumed by junk.
    """
    if room_for(inventory_rows(pack), keeper.size):
        return ()
    found = _opening(inventory_rows(pack), pack.items, junk, junk, keeper.size, None, block)
    return tuple(found[0]) if found is not None and not found[1] else ()


def _make_way(
    items: Sequence[Carried],
    keepers: Sequence[Carried],
    pages: dict[int, tuple[str, ...]],
    movable: Set[int],
    junk: Set[int],
    cube: tuple[str, ...] | None,
    block: tuple[int, int],
) -> tuple[tuple[Move, ...], tuple[Carried, ...], tuple[Carried, ...], tuple[Carried, ...]]:
    """Step (iv)'s moves aside: for each cube keeper (in `keepers`' order) with room on a page but no free block in the
    inventory as the stash's puts leave it (`items`), the moves of `movable` items (the loop's junk, the key stacks,
    the unidentified) within it that free one, else the junk into the cube (`cube`: its rows while its keepers are
    still in it). The moves in order, the junk into the cube, the keepers neither frees a block for that one would have
    once the inventory's junk is sold (`StashStop.stranded`), and those no page has room for (`StashStop.full`)."""
    trial = dict(pages)
    now = list(items)
    planned: list[tuple[tuple[int, int], tuple[int, int]]] = []  # the keepers' blocks, as `out_now` takes them
    moves: list[Move] = []
    into: list[Carried] = []
    stranded: list[Carried] = []
    homeless: list[Carried] = []

    def lines(sold: bool = False) -> tuple[str, ...]:
        rows = _rows_of(i for i in now if not (sold and i.unit_id in junk))
        for at, size in planned:
            rows = taken(rows, at, size)
        return rows

    for keeper in keepers:
        if not _place(dict(trial), [keeper]):
            homeless.append(keeper)
            continue  # no page has room for it: it stays in the cube, nothing moved for it
        spot = _spot(lines(), keeper.size)
        if spot is None:
            found = _opening(lines(), now, movable, junk, keeper.size, cube, block)
            if found is None:
                if _spot(lines(sold=True), keeper.size) is not None:
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
            spot = _spot(lines(), keeper.size)
            if spot is None:
                continue
        planned.append((spot, keeper.size))
        _place(trial, [keeper])
    return tuple(moves), tuple(into), tuple(stranded), tuple(homeless)


def _shuffled(pack: Pack, stop: StashStop) -> Pack:
    """`pack` with the stop's moves aside made: each moved item at its new cell, the junk into the cube gone from the
    inventory (`after` puts it in the cube)."""
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
    """The stash stop's plan (§2.2 2): which of the loop's items goes onto which tab or page, from what is carried and
    the stash as read. The junk and the unidentified stay (Jamella's, Cain's); the player's own are never among them.

    (i), (ii) a resource onto its tab while its stack has room, each one counted (two Tal Runes onto a stack of 98: one
    goes); a full stack's is never clicked: a material is put down (none buys one), a rune stays for Jamella, a gem
    stays for the cube's transmutes, a potion is never full (the belt's) and stays. (iii) the inventory's keepers onto
    the pages `place` chooses. (iv) the cube's keepers out through the room the inventory's leave (the drops' cells
    too), onto the pages' room still left; one with no room on a page stays in the cube (`full`); one with room on a
    page but no block in the inventory gets one by moves aside of the loop's junk, key stacks and unidentified items
    within it (`shuffles`), else by that junk into the cube (`into_cube`), else (`park`) by that junk parked on a shared
    page for the stop (`parks`); no block freed so, it stays in the cube (`stranded`). (v) the cube's junk, full runes
    and full materials out to the inventory, as the room left after (iv) allows, for Jamella (none with a park: they
    wait in the cube for her passes, the room kept for the parked junk to come back). (vii) the key stack's move that
    frees `needs.block` in the inventory as the stop leaves it. `park` None: PARK_JUNK."""
    stop = _planned(h, view, needs, deposit_to, ())
    assert stop is not None  # nothing parked: always planned
    if not ((PARK_JUNK if park is None else park) and stop.stranded):
        return stop
    # The park (PARK_JUNK): each of the inventory's junk alone, the largest first, then all of it; the one that lets
    # the most cube keepers out, then the fewest parked. Never a keeper, the unidentified or the player's own
    junk = [i for i in loot(h.pack, h.own) if i.unit_id in h.junk and i.unit_id not in h.unknown]
    tries = [(i,) for i in _largest_first(junk)] + ([tuple(junk)] if len(junk) > 1 else [])
    best, rank = stop, (-_through(stop), 0)
    for parked in tries:
        trial = _planned(h, view, needs, deposit_to, parked)
        if trial is not None and (-_through(trial), len(trial.parks)) < rank:
            best, rank = trial, (-_through(trial), len(trial.parks))
    return best


def _through(stop: StashStop) -> int:
    """How many of the cube's keepers the stop puts onto a page."""
    return sum(1 for put in stop.puts if put.source == 'cube' and not put.tab)


def _lands(rows: dict[int, tuple[str, ...]], puts: Iterable[tuple[Carried, int]]) -> bool:
    """Whether each of `puts`, in order, finds a block on its page of `rows` (the game's Ctrl + click: its first free
    block on the page shown); `rows` updated."""
    for item, index in puts:
        spot = _spot(rows[index], item.size) if index in rows else None
        if spot is None:
            return False
        rows[index] = taken(rows[index], spot, item.size)
    return True


def _park_pages(
    pages: dict[int, tuple[str, ...]], before: Sequence[Put], later: Sequence[Put], parked: Sequence[Carried]
) -> tuple[Put, ...] | None:
    """The shared page each of `parked` goes onto (the largest first, the first priority page that takes it), as the
    stop makes its clicks: the puts `before` (the inventory's keepers, the cube's out before the stash), the parks,
    then the cube keepers `later` out through the room the parks made, each into the first free block of its page;
    a park never takes the block a later keeper's put needs. None when one finds no such page."""
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
    """`stash_stop`'s plan with `parked` (the inventory's junk) out of the inventory for the stop; None when they find
    no page, or no room to come back into the inventory once the keepers are in."""
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
            # A full material out, then put down (loop.py SHOP `discard`); a full rune out too, no longer for Jamella
            # (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower"): the cube emptied for the rune transmutes,
            # it goes onto its stack once they make room (`rune_puts`)
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
    # One with no free block in the inventory the puts leave: the loop's junk (sold at Jamella, after the stash) and its
    # key stacks moved aside within it, else that junk into the cube, to be sold from there. At 14:28 on 2026-10-18 a
    # unique Embossed Plate (2 x 3) stayed in the cube: the inventory's one 2 x 3 held a set Amulet judged junk (4, 2),
    # kept for Jamella, and the plan gave the plate no put (rca/2026-10-18/town-remaining-findings.md §1). Never the
    # player's own (the player, 2026-10-17: "we shouldn't sell our own equipment"); the unidentified moved within the
    # inventory only (the player, 16:50 on 2026-10-18: "shuffle can move unid items"), never into the cube
    loop_junk = {i.unit_id for i in loot(staying, h.own) if i.unit_id in h.junk and i.unit_id not in h.unknown}
    waiting = {i.unit_id for i in loot(staying, h.own) if i.unit_id in h.unknown}
    keys = {i.unit_id for i in staying.items if i.txt == KEY_CLASS and i.size == (1, 1)}
    cube_then: tuple[str, ...] | None = None
    if any(i.txt == CUBE_CLASS for i in pack.items):
        cube_then = ('.' * CUBE_SIZE[0],) * CUBE_SIZE[1]  # the cube while its keepers are in it: its resources out
        tabbed = {put.item.unit_id for put in tab_puts if put.source == 'cube'}
        for item in (i for i in pack.in_cube if i.unit_id not in tabbed):
            cube_then = taken(cube_then, (item.x, item.y), item.size)
    shuffles, into_cube, stranded, homeless = _make_way(
        staying.items, cube_keepers, rows, loop_junk | keys | waiting, loop_junk, cube_then, needs.block
    )
    moved = _shuffled(staying, StashStop(shuffles=shuffles, into_cube=into_cube))
    left = inventory_rows(moved)
    trial = dict(rows)
    paged = _place(trial, out_now(left, cube_keepers))
    through = out_now(left, [i for i in cube_keepers if i.unit_id in paged])
    on_pages |= _place(rows, through)
    for item in through:
        spot = _spot(left, item.size)
        if spot is not None:
            left = taken(left, spot, item.size)
    junk = [i for i in pack.in_cube if i.unit_id in h.junk]
    out_for_sale = () if parked else out_now(left, sorted([*junk, *sale], key=lambda i: (-i.size[1], -_cells(i))))
    by_page = sorted(
        [Put(i, 'inventory', on_pages[i.unit_id]) for i in keepers if i.unit_id in on_pages]
        + [Put(i, 'cube', on_pages[i.unit_id]) for i in through],
        key=lambda put: (PAGE_PRIORITY.index(put.to), put.source != 'inventory', -_cells(put.item), -put.item.size[1]),
    )
    parks: tuple[Put, ...] = ()
    if parked:
        # The parks clicked between the puts made with the stash's first opening and the cube keepers' after it (macros/
        # visit.py `stash_stop`: those out before the stash as the inventory was, the tallest first)
        tallest = sorted(through, key=lambda i: (-i.size[1], -_cells(i)))
        early = {i.unit_id for i in out_now(inventory_rows(pack), tallest)}
        before = [put for put in by_page if put.source == 'inventory' or put.item.unit_id in early]
        later = [put for put in by_page if put.source == 'cube' and put.item.unit_id not in early]
        found = _park_pages(first_rows, before, later, parked)
        if found is None or len(out_now(inventory_rows(moved), _largest_first(parked))) < len(parked):
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
    """`stop` with the rune transmutes (RUNES_AIM) on the stacks as its tab puts leave them, made last with the cube
    empty as the stop leaves it (none otherwise: what else the cube holds would join the recipe), and the loop's runes
    the stacks had no room for onto them after, as the transmutes leave room."""
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
    """The rune transmutes a stash stop makes (RUNES_AIM), from the stacks' counts (class -> count, the gems' too): one
    at a time, the fullest stack over RUNES_AIM first (the smaller rune on a tie) whose recipe (cube.py `rune_recipe`,
    the game's cubemain.txt) takes RUNES_A_TAKE runes and at most one gem, that gem's stack holding one, while the stack
    it makes has room; never a Ber Rune; `most` at most."""
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
    """The transmute of three runes of class `txt`, None when there is no recipe, it takes other than RUNES_A_TAKE runes
    or more than one gem, its gem's stack is empty, the stack it makes is full, or a Ber Rune would go into it."""
    return _why_not(txt, counts)[0]


def _why_not(txt: int, counts: Mapping[int, int]) -> tuple[RuneCube | None, str]:
    """`_cubed`'s transmute, else why there is none (for the log)."""
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
    """The rune stacks over RUNES_AIM no transmute takes down, each with why (for the log): the gem its recipe takes is
    not in the stash, the stack it makes is full, a Ber Rune, a recipe of two runes."""
    found = []
    for txt, count in sorted(counts.items()):
        if txt not in RUNE_CLASSES or count <= RUNES_AIM or rune_recipe(txt) is None:
            continue
        step, why = _why_not(txt, counts)
        if step is None:
            found.append((txt, why))
    return tuple(found)


def after(pack: Pack, stop: StashStop) -> Pack:
    """`pack` as the stop leaves it, simulated: the puts and the drops gone, the moves aside made, the cube's junk in
    the inventory (each in the first free block, the tallest first), the junk put into the cube in its first free block
    as the cube was then (its resources out, its keepers still in), the parked junk back in the inventory (each in the
    first free block, the largest first), the cube's rows of what is left in it."""
    out = {item.unit_id for item in stop.out_for_sale}
    gone = {put.item.unit_id for put in (*stop.puts, *stop.rune_puts)} | {item.unit_id for item in stop.drops}
    parked = {put.item.unit_id for put in stop.parks}
    shuffled = _shuffled(pack, stop)
    items = [i for i in shuffled.items if i.unit_id not in gone | parked]
    rows = inventory_rows(replace(pack, items=tuple(items)))
    for item in (*stop.out_for_sale, *_largest_first(put.item for put in stop.parks)):
        spot = _spot(rows, item.size)
        if spot is not None:
            rows = taken(rows, spot, item.size)
            items.append(replace(item, x=spot[0], y=spot[1]))
    in_cube = tuple(i for i in pack.in_cube if i.unit_id not in gone | out)
    if stop.into_cube:
        tabbed = {put.item.unit_id for put in stop.puts if put.source == 'cube' and put.tab}
        then: tuple[str, ...] = ('.' * CUBE_SIZE[0],) * CUBE_SIZE[1]
        for item in (i for i in pack.in_cube if i.unit_id not in tabbed):
            then = taken(then, (item.x, item.y), item.size)
        for item in stop.into_cube:
            spot = _spot(then, item.size)
            if spot is not None:
                then = taken(then, spot, item.size)
                in_cube += (replace(item, x=spot[0], y=spot[1]),)
    cube: tuple[str, ...] = ('.' * CUBE_SIZE[0],) * CUBE_SIZE[1]
    for item in in_cube:
        cube = taken(cube, (item.x, item.y), item.size)
    return replace(
        pack,
        items=tuple(items),
        in_cube=in_cube,
        cube_items=frozenset(i.unit_id for i in in_cube),
        cube=cube if pack.cube is not None or in_cube else pack.cube,
    )


def sold_full(full: Set[int]) -> frozenset[int]:
    """The full stacks' classes that are not picked up: the runes and the materials. The ruling was the runes' ("other
    runes that will have 99"); a Flawless Amethyst whose stack was full was left on the ground twice, the player: "we
    just left flawlest amethyst and left the game. something is wrong" (15:19 on 2026-10-17). A gem of a full stack is
    picked up and kept carried, not sold, until the player rules on it. The materials too (the Materials tab: essences,
    shards, keys; the player, 10:37 on 2026-10-18: "essensies are stacking to 99, when we have full stash cell - just
    stop picking it up, there is no use for it"), never a potion (the belt's); no vendor buys a material: put down.
    A full stack's rune is no longer sold (the player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower"): the stash stop
    transmutes its stack down (RUNES_AIM), and one carried waits for the room that makes (`StashStop.rune_puts`)."""
    return frozenset(
        txt for txt in full if txt in RUNE_CLASSES or (resource_tabs().get(txt) == MATERIALS_TAB and not is_potion(txt))
    )


def surplus(carried: Sequence[Carried], full: StashView | Set[int]) -> tuple[Carried, ...]:
    """The flawless gems among `carried` (the loop's items, the cube's too) sold at Jamella, by the `full` stacks (a
    view's, or the classes): only of a kind whose flawless and perfect stacks are both full; GEMS_A_KIND of a kind and
    GEMS_KEPT in all stay for the cube, the kinds with the most first, those nearest a transmute."""
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
    """The carried gold kept when depositing, None for no deposit (§2.3): near the cap a sale drops the gold over it on
    the ground (the player, 2026-10-17: "probably we need to move extra gold to our cube [stash]"); never below
    `REPAIR_SHARE` of the expected repair (repairs are paid from carried gold only)."""
    if coins is None or cap is None or coins < cap - DEPOSIT_NEAR:
        return None
    return max(cap - DEPOSIT_ROOM, round(REPAIR_SHARE * repair))


def tops_up(staff: Teleport | None, in_session: bool, reported: bool) -> bool:
    """Whether a visit repairs any charge missing (the player, 2026-10-17: "we must go to LK with all refilled"): only
    until it is done (`reported`); one done at a game's start sent the loop to Halbu again at the game's end for 5
    charges, ~8 s (15:48:43 on 2026-10-17)."""
    return staff is not None and in_session and not reported and staff.charges < staff.maximum


def kept_gem(item: Carried, full: Set[int]) -> bool:
    """A full stack's flawless gem, kept carried for the cube (`surplus`): no keeper the stash missed."""
    return item.txt in full and item.txt not in sold_full(full) and perfect_of(item.txt) is not None


def named(items: Iterable[Carried]) -> tuple[str, ...]:
    """Each item by quality, base name and cell, for the contract and the log (14:28:27 on 2026-10-18: "1 keepers
    carried", which one unknown): `set Battle Boots at (0, 0)`."""
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
    """What a visit left (§2.2 6), from the pack read after it; `misses` names each part short of the player's
    contract (2026-10-18 12:55: "after the loop we must have: empty cube, all designated free space cells are free in
    the inventory"; 2026-10-17: "we must go to LK with all refilled"): the cube's items, the block taken, junk unsold,
    a keeper not stashed (the unidentified, the full stacks' kept gems aside), the keys under the run kind's (after
    Jamella) or under MIN_STOCK, the Town Portal charges short (none with the Sling), units left on the ground, junk a
    park left on a stash page (`in_stash`, read there after the visit). `stash_full`: the keepers no page had room for
    (`StashStop.full`), told apart from the misses: the loop stops on them. `deferred`: the cube's keepers that wait in
    it for the next visit (`StashStop.waits`, KEEPER_IN_CUBE): named, neither the cube's miss nor a keeper's."""
    later = {i.unit_id for i in deferred if i.unit_id in pack.cube_items}
    # A full stack's flawless gem kept in the cube for its transmute waits there too (the player, 09:51 on 2026-10-18:
    # "we must cube them up first"; "cube 1 items (normal Flawless Amethyst at (1, 1))" at 06:18 on 2026-10-19)
    later |= {i.unit_id for i in pack.in_cube if kept_gem(i, full)}
    items = [*loot(pack, own), *pack.in_cube]
    junk_left = sum(1 for i in items if i.unit_id in junk)
    keepers = [
        i
        for i in items
        if i.unit_id not in junk | later and i.identified and not kept_gem(i, full) and i.txt not in sold_full(full)
    ]
    block = room_for(inventory_rows(pack), needs.block)
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
