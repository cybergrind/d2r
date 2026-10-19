"""The whole town visit simulated before its first click (rca/2026-10-18/arch-town-planning.md §3 B, step M1). Pure: no
input, no reads.

From a visit's snapshot (macros/visitlog.py `Snapshot`, the `start` one: after Cain and the verdicts) `plan_visit` runs
the visit's stops in the ruled order (the player, 2026-10-18 12:55: Cain, the stash, Jamella, Halbu when due, the exit)
over the inventory, the cube, the stash pages and the resource stacks, and returns the ordered moves, the predicted end
state and the contract's misses it foresees, named (town.py `contract`). The stops are filled by today's helpers, as
visit.py makes them: the stash stop by town.py `stash_stop` and `after`, Jamella by the passes of visit.py `jamella`
(the inventory's junk sold, the cube's junk out as the room allows and sold, pass after pass), the keys moved out of
the build's block as visit.py does after her. Cain has nothing left to do in a `start` snapshot (the unidentified stay
unidentified: no verdict is guessed); Halbu and the exit move no item.

The variants behind the player's rulings are `Rulings` (§5 of the study):

1. `park_junk`, on (the player, 16:50 on 2026-10-18: "junk can be temporarily stored in stash, but sold after"):
   inside the stash stop, the inventory's junk that holds a cube keeper's block put onto a shared page with room and
   taken back before the stash closes (the cube's junk then waits in it for Jamella's passes). town.py `stash_stop`
   plans it itself (PARK_JUNK), so the ruled order is simulated with it, as visit.py makes it;
2. `jamella_first`, off: Jamella before the stash when a cube keeper gets out only once the junk is sold (visit.py
   `JAMELLA_FIRST`);
3. `drop_junk`, off: such junk put down in town, its gold given up;
4. `keeper_in_cube`, on (the player, 17:50 on 2026-10-18: "keeper can wait in cube"): a cube keeper with room on a page
   that the visit cannot get out is left in the cube for the next visit, not a miss (named `deferred`, as town.py
   `contract` names it: KEEPER_IN_CUBE); one no page has room for is the stash full, still a miss.

With a variant's ruling on, it is simulated beside the ruled order and the one with the fewest misses (then the fewest
moves) is the plan. In shadow (step M1) visit.py logs the prediction at the visit's start and whether the contract
matched it at the end; no click is made by it.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from inventory_tracking.items.grid import CUBE_SIZE, Grid
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.macros.cube import KEY_CLASS, keys_move, loot
from inventory_tracking.macros.shop import short
from inventory_tracking.macros.stash import is_potion
from inventory_tracking.macros.town import (
    RUNES_A_TAKE,
    Cell,
    Contract,
    Holdings,
    Needs,
    after,
    contract,
    place,
    sold_full,
    stash_stop,
)
from inventory_tracking.macros.visitlog import Snapshot
from inventory_tracking.macros.world import Carried, Pack, Page, StashView


__all__ = [
    'MODELLED',
    'RULED',
    'Rulings',
    'State',
    'Step',
    'VisitPlan',
    'kind_of',
    'kinds',
    'plan_visit',
    'simulate',
]

SELL_PASSES = 4  # visit.py SELL_PASSES: the cube's junk out and sold, pass after pass
# The contract's parts the plan models (town.py `contract`); the keys bought (where a new stack lands, whether her stock
# has room), the portals and the units parked on the ground are not (the study's §1.2, row 13)
MODELLED = ('cube', 'block', 'junk', 'keepers', 'parked')


@dataclass(frozen=True)
class Rulings:
    """The variants the player rules on (the module text): the park on (16:50 on 2026-10-18), a keeper waiting in the
    cube on (17:50), the rest off."""

    park_junk: bool = True
    jamella_first: bool = False
    drop_junk: bool = False
    keeper_in_cube: bool = True


RULED = Rulings()  # the player's, 16:50 and 17:50 on 2026-10-18


@dataclass(frozen=True)
class Step:
    """One move of the plan: its stop, what is done (`tab`, `page`, `aside`, `into cube`, `out`, `park`, `unpark`,
    `drop`, `sell`, `keys`, `runes`: a rune transmute, the item its input's class, `to` the class made), the item, and
    where it goes (a page or, negative, a resource tab; an inventory cell)."""

    stop: str
    verb: str
    item: Carried
    to: int | tuple[int, int] | None = None


@dataclass(frozen=True)
class State:
    """The visit's world as simulated: the pack (inventory and cube), the stash's pages and stacks, the player's own
    cells, the junk and the unidentified; what was sold, put down (`ground`), left on a page by a park (`parked`:
    page, item), and whether Jamella was visited (`shopped`: the contract's `restocked`)."""

    pack: Pack
    pages: tuple[Page, ...]
    stacks: tuple[tuple[int, int], ...]
    own: frozenset[Cell]
    junk: frozenset[int] = frozenset()
    unknown: frozenset[int] = frozenset()
    sold: tuple[Carried, ...] = ()
    ground: tuple[Carried, ...] = ()
    parked: tuple[tuple[int, Carried], ...] = ()
    shopped: bool = False

    @property
    def view(self) -> StashView:
        return StashView(self.pages, self.stacks)

    @property
    def full(self) -> frozenset[int]:
        """The full stacks, no potion (visit.py `_full_of`)."""
        return frozenset(txt for txt in self.view.full() if not is_potion(txt))

    @classmethod
    def of(cls, snapshot: Snapshot) -> State | None:
        """The state a snapshot holds; None with the stash unread (the visit scans it: nothing to plan)."""
        if snapshot.view is None:
            return None
        return cls(snapshot.pack, snapshot.view.pages, snapshot.view.stacks, snapshot.own, snapshot.junk,
                   snapshot.unknown)  # fmt: skip


@dataclass(frozen=True)
class VisitPlan:
    """The plan of a visit: the variant chosen, its moves in order, the end state, the contract on it, the misses
    foreseen (named, the modelled parts only) and the keepers left in the cube by ruling (`deferred`)."""

    variant: str
    steps: tuple[Step, ...]
    end: State
    contract: Contract
    misses: tuple[str, ...]
    deferred: tuple[Carried, ...] = ()

    def said(self) -> str:
        """`<misses or none> (variant <name>, <n> moves)` for the log."""
        return f'{"; ".join(self.misses) or "none"} (variant {self.variant}, {len(self.steps)} moves)'


def kind_of(miss: str) -> str:
    """The contract's part a miss of town.py `contract` names: cube, block, junk, keepers, keys, portals, ground; a
    park's `parked`."""
    for prefix, kind in (('cube ', 'cube'), ('block ', 'block'), ('junk left', 'junk'), ('keys ', 'keys'),
                         ('portals ', 'portals')):  # fmt: skip
        if miss.startswith(prefix):
            return kind
    if 'keepers carried' in miss:
        return 'keepers'
    if 'left on the ground' in miss:
        return 'ground'
    if 'parked on a page' in miss:
        return 'parked'
    return miss


def kinds(misses: Iterable[str]) -> tuple[str, ...]:
    """The modelled parts among `misses`, sorted (what a prediction and a contract are compared by)."""
    return tuple(sorted({kind_of(m) for m in misses} & set(MODELLED)))


# The stops


def _tallest_first(items: Iterable[Carried]) -> list[Carried]:
    """cube.py `unpack`'s order."""
    return sorted(items, key=lambda i: (-i.size[1], -i.size[0] * i.size[1]))


def _pack(pack: Pack, items: Iterable[Carried], in_cube: Iterable[Carried]) -> Pack:
    """`pack` with these items and cube items, the cube's rows and units told again."""
    cubed = tuple(in_cube)
    rows = Grid.from_items(cubed, CUBE_SIZE) if pack.cube is not None or cubed else pack.cube
    return replace(pack, items=tuple(items), in_cube=cubed, cube_items=frozenset(i.unit_id for i in cubed), cube=rows)


def _without(pack: Pack, gone: Iterable[Carried]) -> Pack:
    units = {i.unit_id for i in gone}
    return _pack(pack, (i for i in pack.items if i.unit_id not in units), pack.in_cube)


def _unpacked(pack: Pack, items: Sequence[Carried]) -> tuple[Pack, list[Carried]]:
    """`items` out of the cube (cube.py `unpack`: the tallest first, each one the inventory has a block for, into its
    first free block, the game's Ctrl + click as everywhere: §1.2); the pack after, and those that came out at their
    new cells."""
    rows, held, out = pack.inventory, list(pack.items), []
    units: set[int] = set()
    for item in _tallest_first(items):
        spot = rows.first_spot(item.size)
        if spot is None:
            continue
        rows = rows.take(spot, item.size)
        moved = replace(item, x=spot[0], y=spot[1])
        held.append(moved)
        out.append(moved)
        units.add(item.unit_id)
    return _pack(pack, held, (i for i in pack.in_cube if i.unit_id not in units)), out


def _put_on_pages(pages: tuple[Page, ...], puts: Iterable[tuple[Carried, int]]) -> tuple[Page, ...]:
    """The pages with each item put on its page at its first free block (where none: as planned, not placed)."""
    by_index = {page.index: page for page in pages}
    for item, index in puts:
        page = by_index.get(index)
        if page is None:
            continue
        spot = Grid(page.rows).first_spot(item.size)
        if spot is None:
            continue
        by_index[index] = replace(
            page,
            rows=Grid(page.rows).take(spot, item.size),
            units=page.units | {item.unit_id},
            items=(*page.items, replace(item, x=spot[0], y=spot[1])),
        )
    return tuple(by_index[page.index] for page in pages)


def _stash(state: State, needs: Needs, *, park: bool = True, drop: Sequence[Carried] = ()) -> tuple[State, list[Step]]:
    """The stash stop (town.py `stash_stop`, `after`), the puts made on the pages and the stacks, in the order
    visit.py `stash_stop` clicks them. `drop`: junk put down first (ruling 3); `park`: the stop's park of the junk that
    holds a cube keeper's way out (ruling 1, town.py PARK_JUNK): onto a page before the moves aside, back into the
    inventory once the keepers are in; one with no room back stays on its page (`State.parked`)."""
    steps = [Step('stash', 'drop', item) for item in drop]
    pack = _without(state.pack, drop)
    stop = stash_stop(Holdings(pack, state.own, state.junk, state.unknown), state.view, needs, park=park)
    end = after(pack, stop)
    page_puts = [(put.item, put.to) for put in stop.puts if not put.tab]
    carried = {i.unit_id: i for i in end.items}
    parked = [(put.to, put.item) for put in stop.parks if put.item.unit_id not in carried]
    pages = _put_on_pages(state.pages, [*page_puts, *((item, index) for index, item in parked)])
    stacks = dict(state.stacks)
    for put in stop.puts:
        if put.tab:
            stacks[put.item.txt] = stacks.get(put.item.txt, 0) + 1
    for rune in stop.runes:  # the rune transmutes (town.py RUNES_AIM), then the carried runes onto the room they made
        stacks[rune.txt] = stacks.get(rune.txt, 0) - RUNES_A_TAKE
        stacks[rune.into] = stacks.get(rune.into, 0) + 1
        if rune.gem is not None:  # the gem its recipe takes (the player, 18:31: "use required gems + runes")
            stacks[rune.gem] = stacks.get(rune.gem, 0) - 1
    for put in stop.rune_puts:
        stacks[put.item.txt] = stacks.get(put.item.txt, 0) + 1
    steps += [Step('stash', 'tab', put.item, put.to) for put in stop.puts if put.tab]
    steps += [Step('stash', 'page', put.item, put.to) for put in stop.puts if not put.tab and put.source == 'inventory']
    steps += [Step('stash', 'drop', item) for item in stop.drops]
    steps += [Step('stash', 'park', put.item, put.to) for put in stop.parks]
    steps += [Step('stash', 'aside', item, cell) for item, cell in stop.shuffles]
    steps += [Step('stash', 'into cube', item) for item in stop.into_cube]
    steps += [Step('stash', 'page', put.item, put.to) for put in stop.puts if not put.tab and put.source == 'cube']
    steps += [Step('stash', 'out', item) for item in stop.out_for_sale]
    steps += [
        Step('stash', 'unpark', back, (back.x, back.y))
        for put in stop.parks
        if (back := carried.get(put.item.unit_id)) is not None
    ]
    steps += [Step('stash', 'runes', Carried(0, rune.txt, 0, 0, (1, 1)), rune.into) for rune in stop.runes]
    steps += [Step('stash', 'tab', put.item, put.to) for put in stop.rune_puts]
    return replace(
        state,
        pack=end,
        pages=pages,
        stacks=tuple(sorted(stacks.items())),
        ground=(*state.ground, *drop, *stop.drops),
        parked=(*state.parked, *parked),
    ), steps


def _jamella(state: State, needs: Needs, *, stock: bool) -> tuple[State, list[Step]]:
    """Jamella (visit.py `jamella`): the full materials put down, the inventory's junk sold, the cube's out as the room
    allows and sold, pass after pass; skipped with nothing to sell and nothing short (`stock`). No rune sold (the
    player, 17:50 on 2026-10-18: a full stack is cubed down instead, town.py RUNES_AIM)."""
    full = state.full
    material = frozenset(txt for txt in sold_full(full) if txt not in RUNE_CLASSES)
    own, junk = state.own, state.junk
    steps: list[Step] = []
    ground = list(state.ground)

    def selling(p: Pack) -> list[Carried]:
        return [i for i in loot(p, own) if i.unit_id in junk]

    def cubed(p: Pack) -> list[Carried]:
        return [i for i in p.in_cube if i.unit_id in junk or i.txt in material]

    def put_down(p: Pack) -> Pack:
        down = [i for i in loot(p, own) if i.txt in material]
        steps.extend(Step('jamella', 'drop', i) for i in down)
        ground.extend(down)
        return _without(p, down)

    pack = put_down(state.pack)
    if not (selling(pack) or cubed(pack) or (stock and short(pack, needs.portals))):
        return replace(state, pack=pack, ground=tuple(ground)), steps
    sold = list(state.sold)
    for passes in range(1 + SELL_PASSES):
        out = cubed(pack)
        if out:
            pack, came = _unpacked(pack, out)
            steps.extend(Step('jamella', 'out', i, (i.x, i.y)) for i in came)
            pack = put_down(pack)
        sell = selling(pack)
        if passes and not sell:
            break
        steps.extend(Step('jamella', 'sell', i) for i in sell)
        sold += sell
        pack = _without(pack, sell)
        if not sell or not cubed(pack):
            break
    return replace(state, pack=pack, ground=tuple(ground), sold=tuple(sold), shopped=True), steps


def _keys(state: State, needs: Needs) -> tuple[State, list[Step]]:
    """The key stack moved out of the build's block when it holds it (visit.py after her, cube.py `arrange_keys`)."""
    pack = state.pack
    if pack.inventory.has_room(needs.block):
        return state, []
    move = keys_move(pack, needs.block)
    if move is None:
        return state, []
    key, (x, y) = move
    items = [replace(i, x=x, y=y) if i.unit_id == key.unit_id and i.txt == KEY_CLASS else i for i in pack.items]
    return replace(state, pack=_pack(pack, items, pack.in_cube)), [Step('keys', 'keys', key, (x, y))]


def simulate(
    state: State,
    needs: Needs,
    *,
    jamella_first: bool = False,
    park: bool = True,
    drop: Sequence[Carried] = (),
) -> tuple[State, tuple[Step, ...]]:
    """The visit's stops over `state`, in the ruled order (Cain: nothing left; the stash; Jamella; Halbu and the exit:
    no item moved; the keys out of the block), or Jamella first (`jamella_first`); `park`, `drop` as `_stash` takes
    them. The end state and the moves in order."""
    steps: list[Step] = []
    early = False
    if jamella_first:
        state, made = _jamella(state, needs, stock=True)
        early = state.shopped
        steps += made
    state, made = _stash(state, needs, park=park, drop=drop)
    steps += made
    shopped = state.shopped
    state, made = _jamella(replace(state, shopped=False), needs, stock=not early)
    state = replace(state, shopped=shopped or state.shopped)
    steps += made
    state, made = _keys(state, needs)
    steps += made
    return state, tuple(steps)


def _keepers_in_cube(state: State) -> tuple[Carried, ...]:
    """The cube's keepers as the visit leaves it: identified, not junk, not a kept gem or a full stack's (the contract's
    keepers)."""
    full = state.full
    return tuple(
        i
        for i in state.pack.in_cube
        if i.unit_id not in state.junk and i.identified and i.txt not in sold_full(full) and i.txt not in full
    )


def _planned(variant: str, end: State, steps: tuple[Step, ...], needs: Needs, rulings: Rulings) -> VisitPlan:
    # Deferred: a cube keeper some page has room for (the stash stop's `waits`); one none has is the stash full, a miss
    deferred = tuple(i for i in _keepers_in_cube(end) if place(end.pages, [i])) if rulings.keeper_in_cube else ()
    done = contract(end.pack, end.own, needs, junk=end.junk, full=end.full, restocked=end.shopped, deferred=deferred)
    misses = [m for m in done.misses if kind_of(m) in MODELLED]
    if end.parked:
        misses.append(f'{len(end.parked)} junk parked on a page')
    return VisitPlan(variant, steps, end, done, tuple(misses), deferred)


def _blockers(state: State) -> list[tuple[Carried, ...]]:
    """The junk sets a drop tries: each inventory junk item alone, the largest first, then all of them."""
    items = [i for i in loot(state.pack, state.own) if i.unit_id in state.junk and i.unit_id not in state.unknown]
    alone: list[tuple[Carried, ...]] = [
        (i,) for i in sorted(items, key=lambda i: (-i.size[0] * i.size[1], -i.size[1], i.unit_id))
    ]
    return alone + ([tuple(items)] if len(items) > 1 else [])


def plan_visit(snapshot: Snapshot, rulings: Rulings = RULED) -> VisitPlan | None:
    """The visit's plan from its `start` snapshot (the module text): the ruled order, and each variant a ruling allows
    when the ruled order leaves a keeper in the cube; the one with the fewest misses, then the fewest keepers deferred,
    then the fewest moves, the ruled order on a tie. None with the stash unread."""
    state = State.of(snapshot)
    if state is None:
        return None
    needs, park = snapshot.needs, rulings.park_junk
    ruled = simulate(state, needs, park=park)
    plans = [_planned('ruled', *ruled, needs, rulings)]
    if _keepers_in_cube(ruled[0]):
        tries: list[tuple[str, tuple[State, tuple[Step, ...]]]] = []
        if rulings.jamella_first:
            tries.append(('jamella first', simulate(state, needs, jamella_first=True, park=park)))
        if rulings.drop_junk:
            tries += [('drop junk', simulate(state, needs, drop=items, park=park)) for items in _blockers(state)]
        plans += [_planned(name, *made, needs, rulings) for name, made in tries]
    return min(enumerate(plans), key=lambda p: (len(p[1].misses), len(p[1].deferred), len(p[1].steps), p[0]))[1]
