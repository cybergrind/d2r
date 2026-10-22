"""One planned town visit (macros/town-plan.md §2): the visit's types, the trade trigger's room, the gems sold, the
gold deposited, the staff topped up and what a visit leaves (`contract`). Pure: no input, no reads; macros/visit.py
`visit` walks the stops. The stash is read from memory (`StashView`), so every put is planned before a click: "we
visit the stash only ONE time" (the player, 2026-10-18). Evidence for the tuned numbers: history/town.md.

The stash stop's plan (`stash_stop`, `place`, `after`, `surplus`, the rune transmutes) lives in loot/storage.py
(loot/design.md §7 M3, 2026-10-20) and is re-exported here; `stash_stop`, `rune_transmutes` and `uncubed` stay thin
wrappers so this module's NEEDS, PARK_JUNK and `rune_recipe` still decide them.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import dataclass, replace
from enum import Enum

from inventory_tracking.game.records import Carried, Pack, Page, StashView, Teleport
from inventory_tracking.game.stash import STACK_MOST, STACK_ROOM
from inventory_tracking.loot import storage
from inventory_tracking.loot.api import reserve_short
from inventory_tracking.loot.runes import RUNES as RUNE_CLASSES
from inventory_tracking.loot.storage import (
    BER,
    BIG_BLOCK,
    CUBE_CLASS,
    GEMS_A_KIND,
    GEMS_KEPT,
    PARK_JUNK,
    RUNE_TRANSMUTES,
    RUNES_A_TAKE,
    RUNES_AIM,
    RUNES_TAB,
    TRADE_ROOM,
    Cell,
    Holdings,
    Put,
    RuneCube,
    RuneRecipe,
    StashStop,
    after,
    loot,
    out_now,
    perfect_of,
    place,
    rune_cube,
    rune_recipe,
    surplus,
    unread_way_for_cube,
)
from inventory_tracking.macros.portal import FROM_TOME, PortalSource
from inventory_tracking.macros.shop import MIN_STOCK, SALE_MOST
from inventory_tracking.macros.stash import MATERIALS_TAB, is_potion, resource_tabs


__all__ = [
    'BER',
    'GEMS_A_KIND',
    'GEMS_KEEP_FLAWLESS',
    'GEMS_KEPT',
    'GEMS_TAB',
    'GEM_TRANSMUTES',
    'PARK_JUNK',
    'RUNES_AIM',
    'RUNES_A_TAKE',
    'RUNES_TAB',
    'RUNE_TRANSMUTES',
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
    'gem_recipe',
    'gem_transmutes',
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
    'unread_way_for_cube',
]

DEPOSIT_NEAR = 2 * SALE_MOST  # gold this near the cap is deposited at the stash (macros/stash.py `deposit`)
DEPOSIT_ROOM = 250_000  # down to the cap less this: room for a session's sales, Teleport still on (loop.py TELEPORT_ON)
REPAIR_SHARE = 1.2  # the deposit leaves the expected repair and this share over it carried (repairs from carried gold)
# A cube keeper the visit cannot get out (room on a page, none in the inventory) waits for the next visit, named as
# deferred, not a miss: "keeper can wait in cube" (the player, 2026-10-18). No page with room: the loop stops.
KEEPER_IN_CUBE = True
# Flawless gems kept on the Gems tab, at least this many of each kind (Amethyst, Diamond, Emerald, Ruby, Sapphire,
# Topaz, Skull); every flawless gem over it is cubed at the stash stop, three from its stack (Ctrl + Shift + right
# click) into the perfect one (cubemain.txt via build_rune_cube.py, data/rune_cube.json `gems`), the perfect gem onto
# its stack. The player, 2026-10-21 ~14:45: "could we also cube gems, probably I's like to keep 15 flawless gems";
# then 14:56: "I wand to keep flawless very low (if we can have perfect)": 0, only the remainder (0-2 a kind) stays.
# A number the player can raise. None: the rule before it (a flawless gem cubed only once its stack is full, from the
# carried ones: `kept_gem`, cube.py `transmute`; the Flawless Amethyst stack sat at 99 from ~14:10 with one made).
GEMS_KEEP_FLAWLESS: int | None = 0
# At most this many gem transmutes a visit, the rest the next: one is a right click, Transmute and the perfect gem
# back, about 2 s (three rune transmutes with a gem each took 7.3 s at 18:54 on 2026-10-18, history/visit.md), so
# about 10 s a visit. A backlog (the Flawless Amethyst stack at 99: 33 transmutes; the other kinds 46 to 82: ~150
# in all) goes down over visits; a game's few flawless gems need one or two.
GEM_TRANSMUTES = 5
GEMS_TAB = 2  # `resource_tabs`: 2 Gems, 3 Materials, 4 Runes


@dataclass(frozen=True)
class Needs:
    """What the visit leaves the character with: the inventory's free block ("for warlock: this is 2x4 continuous
    space", the player, 2026-10-18), the keys (Kind.keys), how Town Portal is cast, Identify charges, a stack's room."""

    block: tuple[int, int] = BIG_BLOCK
    keys: int = 24
    portals: PortalSource = FROM_TOME
    identifies: int = 20
    stack_room: int = STACK_ROOM


class Exit(Enum):
    """How a visit ends: the waypoint (a game's start), none (Save and Exit follows), the portal back (a trip)."""

    WAYPOINT = 'waypoint'
    LEAVE = 'leave'
    PORTAL = 'portal'


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


NEEDS = Needs()  # the Warlock's in the Lower Kurast loop


def stash_stop(
    h: Holdings,
    view: StashView,
    needs: Needs = NEEDS,
    *,
    deposit_to: int | None = None,
    park: bool | None = None,
    gems: int = GEM_TRANSMUTES,
) -> StashStop:
    """The stash stop's plan (§2.2 2; loot/storage.py `stash_stop`) leaving `needs.block` free; `park` None: this
    module's PARK_JUNK. Then up to `gems` gem transmutes (GEMS_KEEP_FLAWLESS) after its rune transmutes."""
    stop = storage.stash_stop(h, view, needs.block, deposit_to=deposit_to, park=PARK_JUNK if park is None else park)
    return _gems(stop, h, view, gems)


def gem_recipe(txt: int) -> RuneRecipe | None:
    """The recipe taking flawless gems of class `txt` into the perfect one (data/rune_cube.json `gems`, from the
    installed game's cubemain.txt: the gem alone, nothing else); `runes` is its gem count. None for any other class,
    a perfect gem's too."""
    row = rune_cube().get('gems', {}).get(str(txt))
    if row is None or perfect_of(txt) != row['into']:
        return None
    return RuneRecipe(row['into'], row['gems'], (), row['description'])


def gem_transmutes(
    counts: Mapping[int, int], keep: int | None = GEMS_KEEP_FLAWLESS, most: int = GEM_TRANSMUTES
) -> tuple[RuneCube, ...]:
    """Up to `most` gem transmutes from the stacks' counts (class -> count): one at a time, the fullest flawless stack
    first (the smaller class on a tie), each only while `keep` of its kind stay and its perfect stack has room. None
    `keep`: none (the rule before GEMS_KEEP_FLAWLESS). 17 keeps 17 (two over, no transmute's worth), 18 makes one."""
    if keep is None:
        return ()
    counts = Counter(counts)
    made: list[RuneCube] = []
    while len(made) < most:
        ready = [
            txt
            for txt in sorted(counts)
            if (found := gem_recipe(txt)) is not None
            and found.runes == RUNES_A_TAKE  # what one right click moves into the cube
            and counts[txt] - found.runes >= keep
            and counts[found.into] < STACK_MOST
        ]
        if not ready:
            break
        txt = max(ready, key=lambda t: (counts[t], -t))
        found = gem_recipe(txt)
        assert found is not None
        counts[txt] -= found.runes
        counts[found.into] += 1
        made.append(RuneCube(txt, found.into))
    return tuple(made)


def _gems(stop: StashStop, h: Holdings, view: StashView, most: int) -> StashStop:
    """`stop` with its gem transmutes after its rune transmutes, from the stacks as the stop leaves them, only when it
    leaves the cube empty (anything else in it would join the recipe) or holding one or two flawless gems of one kind
    whose stack is full (kept for the cube, `kept_gem`): the first transmute then tops those up to three from the
    stack (visit.py `_cube_runes`). The loop's carried gems a full stack refused then go onto the room the transmutes
    made (`rune_puts`). The player's own gems (`h.own`) are never touched."""
    if GEMS_KEEP_FLAWLESS is None or most <= 0 or all(i.txt != CUBE_CLASS for i in h.pack.items):
        return stop
    left = after(h.pack, stop)
    counts = Counter(dict(view.stacks))
    counts.update(put.item.txt for put in (*stop.puts, *stop.rune_puts) if put.tab)
    for step in stop.runes:
        counts[step.txt] -= RUNES_A_TAKE
        counts[step.into] += 1
        if step.gem is not None:
            counts[step.gem] -= 1
    topped: tuple[RuneCube, ...] = ()
    if left.in_cube:
        topped = _topped(left.in_cube, h, counts)
        if not topped:
            return stop
    gems = (*topped, *gem_transmutes(counts, GEMS_KEEP_FLAWLESS, most - len(topped)))
    if not gems:
        return stop
    for step in gems[len(topped) :]:
        counts[step.txt] -= RUNES_A_TAKE
        counts[step.into] += 1
    kinds = {step.txt for step in gems}
    waiting = h.junk | h.unknown
    late: list[Put] = []
    for item in loot(left, h.own):
        if item.txt in kinds and item.unit_id not in waiting and counts[item.txt] < STACK_MOST:
            counts[item.txt] += 1
            late.append(Put(item, 'inventory', -GEMS_TAB))
    return replace(stop, runes=(*stop.runes, *gems), rune_puts=(*stop.rune_puts, *late))


def _topped(cube: Sequence[Carried], h: Holdings, counts: Counter[int]) -> tuple[RuneCube, ...]:
    """The transmute topping the cube's one or two flawless gems of one kind up to three from its stack, `counts`
    updated; () when the cube holds anything else, junk or the unidentified, or the stack or the rule cannot."""
    kinds = {i.txt for i in cube}
    if len(kinds) != 1 or any(i.unit_id in h.junk | h.unknown for i in cube):
        return ()
    [txt] = kinds
    found = gem_recipe(txt)
    keep = GEMS_KEEP_FLAWLESS
    if found is None or keep is None or found.runes != RUNES_A_TAKE or len(cube) >= found.runes:
        return ()
    short = found.runes - len(cube)
    if counts[txt] < short or counts[txt] - short < keep or counts[found.into] >= STACK_MOST:
        return ()
    counts[txt] -= short
    counts[found.into] += 1
    return (RuneCube(txt, found.into),)


def rune_transmutes(counts: Mapping[int, int], most: int = RUNE_TRANSMUTES) -> tuple[RuneCube, ...]:
    """loot/storage.py `rune_transmutes` by this module's `rune_recipe`."""
    return storage.rune_transmutes(counts, most, recipe=rune_recipe)


def uncubed(counts: Mapping[int, int]) -> tuple[tuple[int, str], ...]:
    """loot/storage.py `uncubed` by this module's `rune_recipe`."""
    return storage.uncubed(counts, recipe=rune_recipe)


def sold_full(full: Set[int]) -> frozenset[int]:
    """The full stacks' classes not picked up: runes (transmuted down, RUNES_AIM) and materials, never a potion: "just
    stop picking it up, there is no use for it" (the player, 2026-10-18). A full stack's gem is still picked up and
    kept for the cube: "we just left flawlest amethyst ... something is wrong" (2026-10-17)."""
    return frozenset(
        txt for txt in full if txt in RUNE_CLASSES or (resource_tabs().get(txt) == MATERIALS_TAB and not is_potion(txt))
    )


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
    ground, junk parked on a page. `junk_left` counts the junk carried, in the cube and on a stash page (`in_stash`,
    read by unit id): a parked one not taken back is junk left too. `stash_full` and `deferred` are named apart from
    the misses."""
    later = {i.unit_id for i in deferred if i.unit_id in pack.cube_items}
    # A full stack's flawless gem kept in the cube for its transmute is no miss either
    later |= {i.unit_id for i in pack.in_cube if kept_gem(i, full)}
    items = [*loot(pack, own), *pack.in_cube]
    junk_left = sum(1 for i in items if i.unit_id in junk) + len(in_stash)
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
    if reserve_short(pack.identifies):  # the field identify's tome (loot/api.py IDENTIFY_RESERVE, M4, 2026-10-20)
        misses.append(f'identifies {pack.identifies}')
    if parked_left:
        misses.append(f'{parked_left} left on the ground')
    if in_stash:
        misses.append(f'{len(in_stash)} junk parked on a page ({_names(in_stash)})')
    said = str(portals) if needs.portals.stocked else f'from {needs.portals.name}'
    waiting = named(i for i in pack.in_cube if i.unit_id in later)
    return Contract(len(pack.in_cube), block, len(items), junk_left, keys, said, parked_left, tuple(misses),
                    tuple(stash_full), len(in_stash), waiting)  # fmt: skip
