"""Layer 5 of the loot design (loot/design.md §2, §5, §7 M4): field identify and drop.

The player, 2026-10-20: "we don't want to bring all trash monarchs in town. just get it, identify with scroll, and drop
if it is bad"; "we can just pickup or appraise these items and drop if ther aren't good enough"; "4os monarch
deflection -- we absolutely want to keep it"; "also start M4 field identify" (the design's recommended answers: Q5 the
do-not-pick-again memory lasts the game, Q6 a scroll for every item of the classes, Q12 never within SIGHT of a
hostile, the batch waits for the level's end).

- `Field.takes` / `Field.pick`: with the KP_6 loop on, a magic or rare drop the GOOD pickup leaves (pickmode.py `sure`)
  whose ground verdict (loot/ground_judge.py) is an identify of a class in CLASSES is picked up, and remembered by unit
  id for the game as picked *for the field identify* (macros/pickmode.py `kept`, one call). Such a drop is an identify
  candidate: no game is kept and no trip made for it (pickmode.py `is_candidate`).
- `Field.settle`: at a level's end and before the loop makes room (`settle`, one call at each site: portal.py `to_town`,
  loop.py `Loop.leave`, running/execution.py `make_room`), only those items, still unidentified in the inventory, are
  identified with the Tome, read and appraised (the identify worker, identify/service.py `appraise`), decided
  (loot/keep.py `decide`), and the ones it says DROP for put down at the feet and never picked up again this game
  (game/kept.py `PutDown.reject`). Everything else, and everything today's rules pick, keeps today's town path.

Never: within SIGHT of a hostile or with life low, with a valuable on the ground the loop could pick up now, in town,
dead, in controller mode, with a panel open (the player's); never for the player's items, a rune, gem, potion, charm,
jewel, set or unique item, nor anything not identified by a real read. Bounded: MOST_TRIES identifies of an item a game,
MOST_A_BATCH items a batch, the tome's charges. The player's hand (actuator.py `Hand`) and a cancel end the batch and
go on up as they would from any act; nothing is counted as failed for them. Hooks never raise anything else.

Log lines (the d2-loop-watch tools read the drop: logwords.py FIELD_DROP):

    Macro: loot: field: magic Monarch (unit 1728653239): drop K8 worthless (no price, worthless, verdict vendor), no
        want
    Macro: inventory: 447 (1728653239) at (3, 0) dropped in the field: K8 worthless (...), no want
    Macro: loot: field: Town Portal: 1 identified, 1 dropped, 0 kept
    Macro: loot: field: Town Portal: 2 to identify wait: 1 hostiles within 30

The big items (the player, 2026-10-20 ~11:55: "bases or blue/rare items might take much place (like spears, matron
bow) -- we want to check them and drop in the middle of the run, without caring them along occupying a lot of space
to the town"; ~12:00 "start all three"):

- G14 (`FIELD_BIG`): every magic or rare item of BIG_CELLS cells or more the filter shows (source 'shown') that no
  other class takes is a field-identify item too: identified in the field, the bad ones dropped at the feet, only the
  kept ones carried to town. In the MOST pickup level, which takes them anyway, they are remembered for the routine
  the same way (pickmode.py `kept`).
- G15 (`FIELD_OVERSIZE`): a magic or rare item over the pickup's cell cap (config.py `pickup_shown_cells`, 6: the
  2x4 spears, polearms, bows, the Zakarum Shield) the filter shows is picked for the field identify only: the cap
  is lifted for it alone (macros/pickup.py `wanted`, loot/shown.py `oversize_rules`).
- A field item of BIG_CELLS or more is taken only when the inventory keeps a SURE_BLOCK free after it (`leaves_room`),
  and the pickup goes to every other valuable in sight first (macros/pickup.py `choose`): a big item never takes
  the room a valuable needs. The field routine before the loop makes room drops the bad ones first.

The big uniques and sets and the cube (the player, 2026-10-20 ~13:28: "probably it is good idea to identify a big items
in the middle of the run (like right now we have a big hammer in cube) and probably drop them without bringing to the
town, for sake of efficiency"):

- G18 (`FIELD_NAMED`): a set or unique item of BIG_CELLS cells or more (no ring, amulet, charm or jewel) the pickup
  takes by its own rules is remembered for the routine (`Field.note`, pickmode.py `_kept`); what is picked does not
  change. Identified and decided as the others; put down only as a surplus copy (`surplus`): an owned copy, not better
  than every owned copy by its rolls, under DUPLICATE_IST by its own rolls, no want row; with no price by its rolls
  only the same item with equal or worse rolls whose KB band is under DUPLICATE_IST. Else kept, to town as before.
- The cube: the loop's items of a field class in the cube (`FieldHands.cubed`; unidentified big ones by their kind
  too, `carried_class`, since an item carried into a new game has a new unit) are taken out into the inventory first
  where it has room for them and a SURE_BLOCK after (macros/cube.py `unpack`), identified there with the Tome (it
  works on the inventory's grid: macros/junk.py `identify` clicks the inventory's cells; nothing in the repo shows it
  on the cube's), the bad ones put down from the inventory, and the others put back into the cube (cube.py
  `stash_only`). Bounded: MOST_TRIES take-outs or identifies an item a game; no room: they wait for Cain.

    Macro: loot: field: Town Portal: 1 of 1 taken out of the cube to identify
    Macro: inventory: 116 (624993714) at (0, 0) dropped in the field: K6 a surplus copy, not better, cheap: ...
    Macro: loot: field: Town Portal: 1 of 1 put back into the cube

Room for the big ones mid-run (`FIELD_AT_ONCE`; the player, 2026-10-20 ~14:28: "we must redesign our routins to
actually have space for mid-run identifying big items"; a magic Monarch at 14:24:32 and two magic gloves at 13:53 were
never picked: after a visit the free cells are the 2x4 block and two more, and `leaves_room` wants a 1x3 after it):

- A big field item (BIG_CELLS+) that fits but leaves no SURE_BLOCK is taken into the free block all the same
  (`Field.pick` `_squeeze`) when the Tome has a charge, no other big item waits unidentified in the inventory or the
  cube (one at a time), and no sure valuable in the look would lose its room to it. Else it is left, said once a drop:

    Macro: loot: field: magic Monarch (unit 5) left: another big item waits to be identified (unit 4)

- A big item in the cube (the room rules' stash put it there) comes out into the free block for the identify though
  no SURE_BLOCK is left after it, one a batch, at every site but ROOM_SITE (`_take_out`), and goes back after.
- A field item of any size left on the ground for want of room (the rare Kriss of 14:52:26: flawless gems filled the
  free cells) gets room at the next quiet look (`_room_for`): the routine's drops first, then the loop's decided items
  (gems, runes, charms, kept ones) into the cube; the cube full too, the room rules' trip to town (`trip`; the player,
  ~14:58: "if we have no room for optimization to keep picking up items - we need to do town routine"). Once a drop a
  game.

    Macro: loot: field: at once: rare Kriss (unit 7): room: 3 of the loop's items into the cube
    Macro: loot: field: at once: rare Kriss (unit 7): the cube has no room for its 1x3: a trip to town for room

- The stash-bound items (runes, gems, shards, statues, keys, essences) go into the cube at the first quiet look after
  their pickup, in one batch (`CUBE_AT_PICKUP`, `Field.park` / `_park`; the player, ~15:02: "move all items that
  we're going to stash in town ... and stash in cube, to have space for identifying items along the way"):

    Macro: loot: cube: 2 of the loop's stash-bound items moved in (Ist Rune, Flawless Ruby)

- Every big item picked for the routine is identified at the first quiet look of the level run (hunt.py
  `field_now` -> `at_once`, the site 'at once'; no hostile within SIGHT, no panel, nothing to pick up): a bad one put
  down at the feet as at the other sites, a kept one into the cube where it fits (the block free again), else it stays
  and the room rules answer the next valuable (the cube, the Gheed's swap, a trip):

    Macro: loot: field: at once: 1 identified, 1 dropped, 0 kept
    Macro: loot: field: at once: magic Monarch (unit 5) kept: into the cube
    Macro: loot: field: at once: magic Monarch (unit 5) kept: it stays in the inventory, the cube has no room for it
"""

import math
import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from inventory_tracking.common import LOG
from inventory_tracking.config import APPRAISAL
from inventory_tracking.game.records import VALUABLE, Carried, Drop, Pack
from inventory_tracking.items.grid import INVENTORY_SIZE, Grid
from inventory_tracking.loot import ground_judge
from inventory_tracking.loot.facts import MAGIC, RARE, SET, UNIQUE, ItemFacts, Owner, from_carried, from_drop
from inventory_tracking.loot.ground_judge import Then
from inventory_tracking.loot.keep import (
    CHARMS,
    GEMS,
    JEWELS,
    JUNK_MAGIC,
    JUNK_UNWANTED,
    LOOP_GEAR,
    NEVER_SOLD_CODES,
    ORGANS,
    POTIONS,
    RUNES,
    SUNDER,
    Action,
    Decision,
    decide_all,
    unusable_first,
)
from inventory_tracking.loot.shadow import Appraised
from inventory_tracking.loot.storage import RESOURCES, SURE_BLOCK, is_potion, roomed
from inventory_tracking.loot.value import DUPLICATE_IST, Value, appraise_result, better_than, comparable


__all__ = [
    'AT_ONCE',
    'BIG_CELLS',
    'CLASSES',
    'CUBE_AT_PICKUP',
    'FIELD',
    'FIELD_AT_ONCE',
    'FIELD_BIG',
    'FIELD_IDENTIFY',
    'FIELD_OVERSIZE',
    'IDENTIFY_RESERVE',
    'IMPLEMENTED',
    'MOST_A_BATCH',
    'MOST_TRIES',
    'Field',
    'FieldHands',
    'Judged',
    'Settled',
    'TownVerdict',
    'at_once',
    'droppable',
    'leaves_room',
    'oversize',
    'reserve_short',
    'settle',
    'sold_copies',
    'stash_bound',
    'surplus_copy',
    'town_asks',
    'town_kept',
    'town_sold',
    'town_verdicts',
]

# M4 on (the player, 2026-10-20: "also start M4 field identify"). False: nothing is picked for the field identify and
# nothing identified or dropped in the field; the tome's reserve is no reason for a visit
FIELD_IDENTIFY = True
# The classes of loot/design.md §4.2 the field identify picks and judges: G6 every magic Monarch, first (§7 M4: "G6
# first (every magic Monarch), then G9-G11"). G9 (magic/rare daggers and grimoires), G10 (magic/rare circlets) and
# G11 (magic rings and amulets: the rare ones are today's pickup); the player, 2026-10-20 ~11:05: "turn on G9-G11 too".
# G14 the shown magic/rare items of BIG_CELLS+ cells and G15 those over the cell cap (module text; the player, ~12:00:
# "start all three")
# G18 the big uniques and sets the pickup takes by its own rules (`FIELD_NAMED`). G19 every magic glove (the player,
# ~13:30: "we want to identify magic gloves that can roll something like 40ias + annother valuable roll, like skills";
# the want rows: loot/build_wants.py G19, junk otherwise: keep.py JUNK_MAGIC). G21 every rare boot and G22 every rare
# belt (the player, 2026-10-20 ~19:05: "is there are good rolls for belts/boots? right now we're not
# picking/identifying them", ~19:25: "we can keep really good ones"; the rows: build_wants.py G21, G22, junk otherwise:
# keep.py JUNK_UNWANTED). Before, a rare boot was G14 by its size and judged by the KB alone; a rare belt was left
CLASSES = frozenset(('G6', 'G9', 'G10', 'G11', 'G14', 'G15', 'G18', 'G19', 'G21', 'G22'))
IMPLEMENTED = frozenset(('G6', 'G9', 'G10', 'G11', 'G14', 'G15', 'G18', 'G19', 'G21', 'G22'))
# The order a batch identifies the classes in (§5 `identify.order`): the dearest class first, then the larger items
ORDER = ('G6', 'G10', 'G9', 'G19', 'G21', 'G22', 'G18', 'G15', 'G14', 'G11')
# Step 1 of the big items (module text; the player, 2026-10-20 ~11:55 "we want to check them and drop in the middle of
# the run", ~12:00 "start all three"; Q6: "a scroll on every item >= 4 cells"). False: such an item is the GOOD
# pickup's only by another class, and the MOST level carries it to town unjudged as before
FIELD_BIG = True
# Step 2 (the same words: "like spears, matron bow"). False: the cell cap holds for magic and rare items as before
FIELD_OVERSIZE = True
BIG_CELLS = 4  # Q6 "every item >= 4 cells": a 2x2 helm, glove, boot, circlet and up
# G18, the big uniques and sets (the player, 2026-10-20 ~13:28: "probably it is good idea to identify a big items in the
# middle of the run (like right now we have a big hammer in cube) and probably drop them without bringing to the town,
# for sake of efficiency"; the standing rulings: "loop should keep the best copy first", "we keep dublicates only for
# expensive items", "we can keep cheaper items (like 0.6 ist) only in case new items better than what we already
# have"). A unique or set item of BIG_CELLS+ cells the pickup takes by its own rules (what is picked is unchanged) is
# identified in the field and put down only as a surplus copy (`droppable`: an owned copy, not better, under
# DUPLICATE_IST, no want; never a charm, ring, amulet or jewel). False: every set and unique item goes to town as before
FIELD_NAMED = True
NAMED_SMALL = frozenset(('ring', 'amul'))  # itemtypes codes: a unique or set ring or amulet is never a G18 item
# Room for the big items mid-run (module text; the player, 2026-10-20 ~14:28: "we must redesign our routins to actually
# have space for mid-run identifying big items"; ~13:28 "identify a big items in the middle of the run ... and probably
# drop them without bringing to the town"). A big field item is taken into the free block though no SURE_BLOCK is left
# after it (`Field._squeeze`), one at a time, and every big one is identified at the first quiet look (`at_once`), the
# kept one put into the cube. False: a big one is taken only with a SURE_BLOCK after it and waits for the level's end
FIELD_AT_ONCE = True
# The stash-bound items into the cube at the first quiet look after their pickup (`Field.park`; the player, 2026-10-20
# ~15:02: "probably we should move all items that we're going to stash in town (gems/runes/statues/etc) pickup and
# stash in cube, to have space for identifying items along the way"). False: they stay in the inventory until the
# level's end, or the room rules move them
CUBE_AT_PICKUP = True
AT_ONCE = 'at once'  # the site's name in the routine's lines
ROOM_SITE = 'room'  # the site where room is made for a valuable waiting (running/execution.py): the reserve holds there
AT_ONCE_EVERY = 1.0  # seconds between two looks of the level run for a big item to identify (`Field.due`)
TOME_FRESH = 5.0  # seconds a read of the Tome's charges serves the pickup's squeeze (`Field._charges`)
SAID_MOST = 512  # the drops said left, at most (a game sees far fewer)
# The Tome of Identify's charges under which a visit restocks it (§5: "charges < 5 makes shop.short true", and the
# visit's contract misses it): macros/shop.py `short`, macros/town.py `contract`
IDENTIFY_RESERVE = 5
MOST_TRIES = 2  # identify clicks on one item a game, at most: a scroll spent and no flag stops the batch (§5)
MOST_A_BATCH = 8  # items identified in one batch, at most
PICKED_MOST = 512  # the units remembered as picked for the field identify, at most (a game picks far fewer)
# The kinds never put down in the field whatever a decision says (S2, the player's "never drop" list): runes, gems,
# potions, charms, jewels, the Uber organs, the loop's tools
NEVER_DROPPED = RUNES | GEMS | POTIONS | CHARMS | SUNDER | JEWELS | ORGANS | LOOP_GEAR
PREFIX = 'Macro: loot: field:'


def droppable(facts: ItemFacts, value: Value | None = None, owned: Sequence[ItemFacts] | None = None) -> str | None:
    """Why the field drop must not put `facts` down whatever its decision, None when it may: not the loop's, not
    identified, a never-dropped kind, a set or unique item but a G18 surplus copy (`surplus`, with `owned` its owned
    copies), or (`value`) a want row names it or it is expensive. A second guard below `keep.decide`, stricter on
    purpose: a magic Monarch with 4 sockets or of Deflecting is never put down in the field ("4os monarch deflection
    -- we absolutely want to keep it", the player, 2026-10-20)."""
    if facts.owner != Owner.LOOP:
        return f"not the loop's (owner {facts.owner.value})"
    if not facts.identified:
        return 'not identified'
    if facts.base_type in NEVER_DROPPED:
        return 'never dropped (runes, gems, potions, charms, jewels, tools)'
    if facts.quality in (SET, UNIQUE):
        return surplus(facts, value, owned)
    if value is not None and value.wants:
        return f'wanted: {value.wants[0].label}'
    if value is not None and value.worth_ist is not None and value.worth_ist >= DUPLICATE_IST:
        return f'expensive ({value.worth_ist:.3g} Ist)'
    return None


def surplus(facts: ItemFacts, value: Value | None, owned: Sequence[ItemFacts] | None) -> str | None:
    """Why the set or unique item `facts` is kept in the field (a G18 item is put down only as a surplus copy), None
    when it may be put down: FIELD_NAMED on, BIG_CELLS cells or more and no ring or amulet, appraised, no want row
    names it, under DUPLICATE_IST by its own rolls, a comparable owned copy (`owned`, the collection's), and not better
    than every owned copy on the rolls that matter (loot/value.py `better_than`). With no price by its rolls (Q13:
    never given up on no evidence) only the same item with equal or worse rolls than an owned copy whose KB band is
    under DUPLICATE_IST. Pure."""
    if not FIELD_NAMED:
        return 'a set or unique item'
    if facts.size[0] * facts.size[1] < BIG_CELLS or facts.base_type in NAMED_SMALL:
        return 'a small set or unique item'
    return surplus_copy(facts, value, owned)


def surplus_copy(facts: ItemFacts, value: Value | None, owned: Sequence[ItemFacts] | None) -> str | None:
    """`surplus` whatever the item's size (the field's G18 check and the town's, M6): why the set or unique item
    `facts` is kept as a copy, None when it is a surplus copy. A want row spares the first copy only (keep.py K4); a
    later copy is kept by a want only as keep.py keeps it (K3: always kept, or under its cap): the 19:57:52 Skullder's
    Ire on 2026-10-20 (0.842 Ist, `slow`, ED 193 vs the owned 193) was kept unsaid by its own-use row though K6 gave it
    up ("we keep dublicates only for expensive items", the player, 2026-10-20). The first copy goes only as
    keep.py `unusable_first` gives it up (FIRST_COPY_USABLE_ONLY). Pure."""
    if value is None:
        return 'a set or unique item with no appraisal'
    if keepers := [want for want in value.wants if want.always_keep]:
        return f'always kept: {keepers[0].label}'
    if value.worth_ist is not None and value.worth_ist >= DUPLICATE_IST:
        return f'expensive ({value.worth_ist:.3g} Ist)'
    if owned is None:
        return 'its owned copies cannot be told'
    same = [copy for copy in owned if comparable(facts, copy)]
    if not same:
        if value.wants:
            return f'the first copy, wanted: {value.wants[0].label}'
        return None if unusable_first(facts, value) is not None else 'the first copy'
    compared = better_than(facts, same, value.matters)
    if compared.better:
        return f'better than the {len(same)} owned ({compared.said()})'
    if value.worth_ist is None:
        band = value.band
        top = max((v for v in (band.q1, band.median) if v is not None), default=None) if band is not None else None
        if top is None or top >= DUPLICATE_IST:
            return 'no price by its rolls and no KB band under 1 Ist'
        if not any(relation in ('equal', 'worse') for relation in compared.relations):
            return 'no price by its rolls and not equal to or worse than an owned copy'
    return None


def sold_copies(
    carried: Sequence[Carried],
    junk: frozenset[int],
    spared: frozenset[int],
    book: Any = None,
    copies: Any = None,
) -> dict[int, tuple[str, str]]:
    """M2 (keep.DECIDES; the player, 2026-10-20 ~15:05: "Sell cheap duplicates"): the loop's identified set and unique
    items in `carried` (inventory and cube) that `keep.decide` gives up and the field's guard lets go (`droppable`: no
    rune, gem, potion, charm, jewel or tool, a surplus copy only, no want row, under DUPLICATE_IST by its own rolls, a
    comparable owned copy and not better than every one: never the best copy), unit -> (title, the rule and why).
    `junk` (sold by today's rules) and `spared` (the player's by its stats) are left out; `book` the identify worker's
    reads (loot/shadow.py BOOK), `copies` the owned copies (loot/value.py CollectionCopies: the collection, not the
    worker's `owned_verdict`, which never ran in the loop). No read or no copies told: kept (S8)."""
    from inventory_tracking.loot.shadow import BOOK
    from inventory_tracking.loot.value import CollectionCopies

    book = BOOK if book is None else book
    copies = CollectionCopies() if copies is None else copies
    found: dict[int, tuple[str, str]] = {}
    for item in carried:
        if item.unit_id in junk or item.unit_id in spared or not item.identified or item.quality not in (SET, UNIQUE):
            continue
        entry = book.get(item.unit_id)
        if entry is None:
            continue
        facts = from_carried(item, owner=Owner.LOOP, observation=entry.observation)
        value = appraise_result(facts, entry.result, entry.verdict)
        [(_, _, decision)] = decide_all([(facts, value)], copies.copies)
        if not decision.gives_up or droppable(facts, value, copies.copies(facts)) is not None:
            continue
        found[item.unit_id] = (facts.title(), f'{decision.rule} a surplus copy, not better, cheap: {decision.reason}')
    return found


# M6, the town's one decision (loot/keep.py TOWN_DECIDES; the player, 2026-10-20 16:55, "go ahead with the merge
# agent"). The kinds never sold whatever a decision says (S2, the player's "never sell" list): runes, gems, potions,
# the Crafted Sunder Charm, the Uber organs, the loop's tools and the quest items (Worldstone Shards, statues, Uber
# keys, essences: itemtype `ques`), Wirt's Leg (keep.py NEVER_SOLD_CODES); set and unique charms (Gheed's, Torch, Anni)
TOWN_NEVER_SOLD = RUNES | GEMS | POTIONS | SUNDER | ORGANS | LOOP_GEAR
VENDOR = 'vendor'  # identify/service.py `verdict_for`: no reason to keep it
# The rules a give-up in town may come from when the appraisal does not say `vendor`, each a dated ruling of the
# player's: K6 a cheap copy not better than an owned one (08:42: "a cheap item ... kept only if it beats what we already
# have"; 15:05: "Sell cheap duplicates"); K8 by kind (keep.py JUNK_UNWANTED ~12:50, rare helms only "really good",
# ~19:25 rare boots and belts: "we can keep really good ones";
# JUNK_MAGIC ~13:30, magic gloves only the IAS + skills rows). Anything else appraised other than vendor is kept, and
# the shadow names it (a question for the player, not decided here)
# K4 the first copy no build names (keep.py FIRST_COPY_USABLE_ONLY, the player 2026-10-20 ~20:10: "keep only uniques
# that are mentioned in guides as something that I probably could use"), over the same verdicts
TOWN_RULED = frozenset(('K4', 'K6'))
# The verdicts a K6 give-up sells over besides `vendor`: `slow` alone, the M2 case the player ruled on at 15:05 ("Sell
# cheap duplicates": The Reaper's Toll, slow, 0.653 Ist, 1 owned). Not `self` (own use: Trang-Oul's Claws, 0.2 Ist, 2
# owned, 17:05:27, was kept), `sell`, `check` or `keep` until the player rules (the coordinator, 2026-10-20 ~17:05)
K6_SELLS_OVER = frozenset(('slow',))
OWN_USE = 'self'  # the appraisal's own-use verdict: never sold in town but as `vendor`


@dataclass(frozen=True)
class TownVerdict:
    """The town's decision on one of the carried items: sold or kept, and why (the decision, or the guard that keeps
    it)."""

    facts: ItemFacts
    value: Value | None
    decision: Decision | None
    sold: bool
    why: str

    def said(self) -> str:
        rule = f'{self.decision.rule} ' if self.decision is not None and self.sold else ''
        return f'{"sell" if self.sold else "keep"}: {rule}{self.why}'


def _junk_by_kind(facts: ItemFacts) -> bool:
    """keep.py K8's kinds kept only by a want row, priced or not: a rare circlet, helm, boot or belt, magic gloves."""
    return (facts.quality == RARE and facts.base_type in JUNK_UNWANTED) or (
        facts.quality == MAGIC and facts.base_type in JUNK_MAGIC
    )


def town_kept(
    facts: ItemFacts, value: Value | None, decision: Decision | None, owned: Sequence[ItemFacts] | None
) -> str | None:
    """Why the town visit keeps the carried item `facts`, None when it sells it (M6): only a give-up of
    `keep.decide`, the loop's, identified, of no never-sold kind (TOWN_NEVER_SOLD, Wirt's Leg, set/unique charms); a set
    or unique item only as a surplus copy (`surplus_copy` with `owned`, the owned copies and the ones kept this visit:
    never the first or the best copy); no want row, under DUPLICATE_IST; and appraised `vendor`, or given up by a
    TOWN_RULED rule over a K6_SELLS_OVER verdict, or by keep.py K8's kinds with a price (S8: no price is kept); never
    one appraised `self` but as `vendor`. Pure."""
    if decision is None or value is None:
        return 'no appraisal (S8)'
    if not decision.gives_up:
        return f'{decision.rule} {decision.reason}'
    if facts.owner != Owner.LOOP:
        return f"not the loop's (owner {facts.owner.value})"
    if not facts.identified:
        return 'not identified'
    kind = facts.base_type
    if kind in TOWN_NEVER_SOLD or facts.code in NEVER_SOLD_CODES or (kind in CHARMS and facts.quality in (SET, UNIQUE)):
        return "never sold (runes, gems, potions, set/unique charms, shards, Wirt's Leg, tools)"
    named = facts.quality in (SET, UNIQUE)
    if named and (why := surplus_copy(facts, value, owned)) is not None:
        return why
    # A set or unique copy's wants are `surplus_copy`'s. A capped want (`keep_up_to`) was applied by keep.py K3
    # already: a copy over its cap is not kept by it (the trap claws' cap of 2, the player 2026-10-20 ~21:05: "yes")
    if (wanted := [want for want in value.wants if want.keep_up_to is None]) and not named:
        return f'wanted: {wanted[0].label}'
    if value.worth_ist is not None and value.worth_ist >= DUPLICATE_IST:
        return f'expensive ({value.worth_ist:.3g} Ist)'
    if value.verdict == VENDOR:
        return None
    verdict = value.verdict or 'without a verdict'
    if value.verdict == OWN_USE:
        return f'appraised {verdict} (own use), not vendor'
    by_kind = _junk_by_kind(facts) and decision.rule == 'K8'
    if value.worth_ist is None and not by_kind and not named:
        return f'no price, appraised {verdict} (S8)'
    if decision.rule in TOWN_RULED and value.verdict in K6_SELLS_OVER:
        return None
    if not by_kind:
        return f'appraised {verdict}, not vendor: {decision.rule} alone sells no such item'
    return None


def town_verdicts(
    items: Sequence[tuple[ItemFacts, Value | None]],
    copies: Callable[[ItemFacts], Sequence[ItemFacts] | None],
) -> list[TownVerdict]:
    """The town's decisions on the carried `items` (M6), in their order: `keep.decide_all` (the field's rules, the best
    rolled first so the first of two copies kept counts as owned for the second), then `town_kept`. An item with no
    value (no appraisal) is kept (S8). `copies` (the owned copies, loot/value.py CollectionCopies) is asked only for the
    items a rule or the copy guard needs."""
    priced = [(facts, value) for facts, value in items if value is not None]
    decided = {facts.unit_id: decision for facts, _, decision in decide_all(priced, copies)}
    kept = [facts for facts, _ in priced if decided[facts.unit_id].action == Action.KEEP]
    found = []
    for facts, value in items:
        decision = decided.get(facts.unit_id) if value is not None else None
        owned = None
        if decision is not None and decision.gives_up and facts.quality in (SET, UNIQUE):
            owned = copies(facts)
            if owned is not None:
                owned = [*owned, *(copy for copy in kept if copy.unit_id != facts.unit_id and comparable(facts, copy))]
        why = town_kept(facts, value, decision, owned)
        sold = why is None
        found.append(TownVerdict(facts, value, decision, sold, decision.reason if sold and decision else why or ''))
    return found


def town_asks(item: Carried) -> bool:
    """Whether the town's decision needs the carried `item`'s appraisal (M6): identified, of no never-sold kind."""
    if not item.identified:
        return False
    from inventory_tracking.items.metadata import item_base

    base = item_base(item.txt)
    if base is None:
        return True
    kind = base.get('type')
    return not (kind in TOWN_NEVER_SOLD or base.get('code') in NEVER_SOLD_CODES)


def town_sold(
    carried: Sequence[Carried],
    spared: frozenset[int],
    book: Any = None,
    copies: Any = None,
    kept: dict[int, tuple[str, str]] | None = None,
) -> dict[int, tuple[str, str]]:
    """M6 (keep.TOWN_DECIDES): the carried items (inventory and cube) the town visit sells, unit -> (title, the rule
    and why): `town_verdicts` on the loop's identified items with the identify worker's reads (`book`, loot/shadow.py
    BOOK) and the owned copies (`copies`, loot/value.py CollectionCopies). `spared` (the player's by its stats) are the
    player's (K0). No read: kept (S8). `kept`, when given, gets the items `keep.decide` gave up that a town guard keeps,
    unit -> (title, the decision and the guard), for the visit's log."""
    from inventory_tracking.loot.shadow import BOOK
    from inventory_tracking.loot.value import CollectionCopies

    book = BOOK if book is None else book
    copies = CollectionCopies() if copies is None else copies
    items: list[tuple[ItemFacts, Value | None]] = []
    for item in carried:
        if not item.identified:
            continue
        entry = book.get(item.unit_id)
        owner = Owner.PLAYER if item.unit_id in spared else Owner.LOOP
        facts = from_carried(item, owner=owner, observation=entry.observation if entry is not None else None)
        items.append((facts, appraise_result(facts, entry.result, entry.verdict) if entry is not None else None))
    verdicts = town_verdicts(items, copies.copies)
    if kept is not None:
        for verdict in verdicts:
            if not verdict.sold and verdict.decision is not None and verdict.decision.gives_up:
                kept[verdict.facts.unit_id] = (verdict.facts.title(), f'{verdict.decision.said()}; {verdict.why}')
    return {
        verdict.facts.unit_id: (verdict.facts.title(), verdict.said().removeprefix('sell: '))
        for verdict in verdicts
        if verdict.sold
    }


def big_named(txt: int | None, quality: int, size: tuple[int, int]) -> bool:
    """Whether an item of class `txt` is a G18 item by its kind: a set or unique item of BIG_CELLS cells or more, not a
    ring, amulet, charm, jewel or any other never-dropped kind (items/metadata.py types)."""
    if quality not in (SET, UNIQUE) or size[0] * size[1] < BIG_CELLS or not txt:
        return False
    from inventory_tracking.items.metadata import item_base

    base = item_base(txt)
    return base is not None and base['type'] not in NAMED_SMALL | NEVER_DROPPED


def carried_class(item: Carried) -> str | None:
    """The field class of an unidentified carried item by its kind and size alone, None for none: G18 a big set or
    unique item (`big_named`), G14 a magic or rare item of BIG_CELLS cells or more (the loop's: macros/loop.py `told`
    counts an unidentified magic-or-better item the loop's)."""
    if item.identified or not FIELD_IDENTIFY:
        return None
    if FIELD_NAMED and big_named(item.txt, item.quality, item.size):
        return 'G18'
    if FIELD_BIG and item.quality in (MAGIC, RARE) and item.size[0] * item.size[1] >= BIG_CELLS:
        return 'G14'
    return None


def cells(drop: Drop) -> int:
    return drop.size[0] * drop.size[1]


def oversize(drop: Drop) -> bool:
    """Whether `drop` is over the pickup's cell cap for the filter's shown gear (config.py `pickup_shown_cells`): the
    cap is lifted only for the field identify (G15) and the bases the ground read judges (M5)."""
    return cells(drop) > APPRAISAL.pickup_shown_cells


def leaves_room(room: tuple[str, ...] | None, size: tuple[int, int]) -> bool:
    """Whether an item of `size` fits the inventory's `room` (rows, '.' free) and a SURE_BLOCK (the tallest sure
    valuable, a Grand Charm) still fits after it, where the game puts it (the first free spot). Unread: True."""
    if room is None:
        return True
    grid = Grid(room)
    spot = grid.first_spot(size)
    return spot is not None and grid.take(spot, size).has_room(SURE_BLOCK)


def reserve_short(identifies: int | None) -> bool:
    """Whether the Tome's charges are under IDENTIFY_RESERVE with the field identify on (unread or no tome: no)."""
    return FIELD_IDENTIFY and identifies is not None and identifies < IDENTIFY_RESERVE


@dataclass(frozen=True)
class Judged:
    """One item the field routine identified and decided."""

    unit_id: int
    title: str
    decision: Decision | None  # None: no appraisal, kept (S8)
    dropped: bool = False


@dataclass(frozen=True)
class Settled:
    """What a field routine did: the items it identified and decided, and why it waited (None: it did not)."""

    judged: tuple[Judged, ...] = ()
    waited: str | None = None
    pending: int = 0  # the items picked for the field identify still to do

    @property
    def dropped(self) -> int:
        return sum(item.dropped for item in self.judged)


class FieldHands(Protocol):
    """The game, as the field routine reads and acts on it (live: loot/hands.py `GameHands`; tests: a fake)."""

    def game(self) -> str | None: ...  # the game's name, None out of a game
    def carried(self) -> Pack | None: ...
    def loops(self, pack: Pack) -> Sequence[Carried]: ...  # the loop's own inventory items (not the cube's)
    def cubed(self, pack: Pack) -> Sequence[Carried]: ...  # the loop's items in the cube (none the player's)
    def take_out(self, items: Sequence[Carried]) -> list[int]: ...  # out of the cube into the inventory: those out
    def put_back(self, units: Sequence[int]) -> int: ...  # the inventory's `units` into the cube: how many went in
    def unquiet(self) -> str | None: ...  # why no field identify now, None when it may
    def identify(self, items: Sequence[Carried]) -> list[Carried]: ...  # those identified, each checked in memory
    def appraise(self, units: Sequence[int]) -> Mapping[int, Appraised]: ...  # the read and the KB result
    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None: ...  # owned copies; None cannot be told
    def drop(self, item: Carried, why: str) -> bool: ...  # put down at the feet, checked in memory
    def reject(self, item: Carried, why: str) -> None: ...  # never picked up again this game


def _cut(stop: BaseException) -> bool:
    """Whether `stop` is the player's or the run's (a hand, a cancel, an expiry, a flip): it goes on up."""
    from inventory_tracking.macros.actuator import Cancelled, Expired, Flipped, Hand

    return isinstance(stop, (Hand, Cancelled, Expired, Flipped))


class Field:
    """The field identify's memory for the game (the units picked for it, the tries, the decided) and its routine.
    One for the service (`FIELD`): the pickup filter and the runner's runs share it, hence the lock."""

    def __init__(self, log: Callable[..., None] = LOG.info) -> None:
        self.log = log
        self.lock = threading.Lock()
        self.looping: Callable[[], bool] = lambda: False  # the KP_6 loop on (runner: running/execution.py)
        self.picked: dict[int, tuple[str | None, str]] = {}  # unit -> (game, class)
        self.tries: Counter[int] = Counter()
        self.judged: dict[int, str] = {}  # unit -> the action decided (or 'kept: ...')
        self.said: set[tuple[str | None, str]] = set()  # (game, wait) said once
        self.game: str | None = None
        # FIELD_AT_ONCE: the big items picked for the routine, to identify at the first quiet look (unit -> game); the
        # drops said left (game, unit); the last look for them; the Tome's charges last read (clock, charges)
        self.waiting: dict[int, str | None] = {}
        self.left_said: set[tuple[str | None, int]] = set()
        self.looked_at = -math.inf
        self.tome_seen: tuple[float, int | None] | None = None
        # The field items left on the ground for want of room (unit -> (game, size)) and those made room for once
        self.roomless: dict[int, tuple[str | None, tuple[int, int], str]] = {}
        self.roomed: set[tuple[str | None, int]] = set()
        # The runner's (running/recovery.py `_field_trip`): the room rules' trip to town for a field item the cube makes
        # no room for (the player, ~14:58: "if we have no room for optimization ... we need to do town routine");
        # whether one is due
        self.trip: Callable[[str], bool] = lambda label: False
        # CUBE_AT_PICKUP: the stash-bound drops the pickup takes, to move into the cube at the next quiet look
        self.parking: dict[int, str | None] = {}
        self.clock: Callable[[], float] = time.monotonic

    # -- the pickup ------------------------------------------------------------------------------

    def takes(self, drop: Drop, classes: frozenset[str] | None = None) -> str | None:
        """The class (CLASSES, or `classes`) that picks `drop` for the field identify, None when none: the switch and
        the loop on, a magic or rare valuable the filter shows, unidentified, an identify by its ground verdict, else
        by its size (G15 over the cell cap, G14 from BIG_CELLS cells; the filter's gear only). Pure but for `looping`;
        the caller leaves out what the GOOD pickup takes anyway (pickmode.py `sure`)."""
        if not FIELD_IDENTIFY or drop.kind != VALUABLE or drop.quality not in (MAGIC, RARE) or drop.prized:
            return None
        if drop.source not in ('shown', 'material') or not self.looping():
            return None
        try:
            verdict = ground_judge.judge(from_drop(drop))
        except Exception:  # the wants unreadable (another edit under way): nothing is picked for it
            return None
        wanted = CLASSES if classes is None else classes
        if verdict.pick and verdict.then == Then.IDENTIFY and verdict.klass in wanted:
            return verdict.klass
        if drop.source != 'shown' or cells(drop) < BIG_CELLS:
            return None
        if oversize(drop):
            return 'G15' if FIELD_OVERSIZE and 'G15' in wanted else None
        return 'G14' if FIELD_BIG and 'G14' in wanted else None

    def pick(
        self,
        drop: Drop,
        game: tuple[str, int] | str | None,
        room: tuple[str, ...] | None = None,
        *,
        carried: frozenset[int] = frozenset(),
        waiting: Callable[[], Sequence[Drop]] | None = None,
        tome: Callable[[], int | None] | None = None,
    ) -> bool:
        """Whether the pickup takes `drop` for the field identify (`takes`), with `room` (the inventory's rows, None
        unread) left for a valuable after it (`leaves_room`), or, a big one, taken into the free block all the same
        (`_squeeze`: `carried` the units in the character's grids, `waiting()` the look's sure valuables, `tome()` the
        Tome's charges); remembered for `game` when it does, a big one for the identify at once (`at_once`)."""
        klass = self.takes(drop)
        if klass is None:
            return False
        big = cells(drop) >= BIG_CELLS
        if FIELD_AT_ONCE and room is not None and not Grid(room).has_room(drop.size):
            self._want_room(drop, game)  # the quiet look makes room in the cube (`_room_for`)
        if big and not leaves_room(room, drop.size):
            why = self._squeeze(drop, game, room, carried, waiting, tome)
            if why is not None:
                self._left(drop, game, why)
                return False  # a valuable's room is not taken: left, seen again at the next look
        self._remember(drop.unit_id, game, klass)
        if big:
            self._wait(drop.unit_id, game)
        return True

    def _squeeze(
        self,
        drop: Drop,
        game: tuple[str, int] | str | None,
        room: tuple[str, ...] | None,
        carried: frozenset[int],
        waiting: Callable[[], Sequence[Drop]] | None,
        tome: Callable[[], int | None] | None,
    ) -> str | None:
        """Why the big `drop` that leaves no SURE_BLOCK after it is not taken into the free block, None when it is
        (FIELD_AT_ONCE, the player's ~14:28 "space for mid-run identifying big items"): it fits; no other big item
        picked for the routine waits unidentified in the character's grids (one at a time); no sure valuable of the
        look loses its room to it; the Tome has a charge for the identify at once. The cheap facts first."""
        if not FIELD_AT_ONCE or room is None:
            return f'no room for a {SURE_BLOCK[0]}x{SURE_BLOCK[1]} valuable after it'
        grid = Grid(room)
        spot = grid.first_spot(drop.size)
        if spot is None:
            return f'no room for its {drop.size[0]}x{drop.size[1]}'
        other = self._unjudged(_name(game), carried, drop.unit_id)
        if other is not None:
            return f'another big item waits to be identified (unit {other})'
        after = grid.take(spot, drop.size)
        for found in waiting() if waiting is not None else ():
            if not after.has_room(found.size):
                return f'{found.label} would lose its room'
        charges = self._charges(tome)
        if charges is None:
            return "the Tome of Identify's charges are unread"
        if charges <= 0:
            return 'the Tome of Identify is empty'
        return None

    def _unjudged(self, game: str | None, carried: frozenset[int], besides: int) -> int | None:
        """A big item picked for the routine in `game`, in the character's grids (`carried`) and not decided yet, other
        than `besides`; None with none."""
        with self.lock:
            for unit, found in self.waiting.items():
                if found == game and unit != besides and unit in carried and unit not in self.judged:
                    return unit
        return None

    def _charges(self, tome: Callable[[], int | None] | None) -> int | None:
        """The Tome's charges: the last read within TOME_FRESH (the routine's own too), else `tome()`; None unread."""
        now = self.clock()
        seen = self.tome_seen
        if seen is not None and now - seen[0] < TOME_FRESH:
            return seen[1]
        if tome is None:
            return None
        try:
            found = tome()
        except Exception:  # a read under way elsewhere: unread, nothing is squeezed
            found = None
        self.tome_seen = (now, found)
        return found

    def _left(self, drop: Drop, game: tuple[str, int] | str | None, why: str) -> None:
        key = (_name(game), drop.unit_id)
        with self.lock:
            if key in self.left_said:
                return
            if len(self.left_said) > SAID_MOST:
                self.left_said.clear()
            self.left_said.add(key)
        self.log('%s %s (unit %d) left: %s', PREFIX, _named(drop.txt, drop.quality), drop.unit_id, why)

    def _want_room(self, drop: Drop, game: tuple[str, int] | str | None) -> None:
        with self.lock:
            if len(self.roomless) > PICKED_MOST:
                self.roomless.clear()
            self.roomless[drop.unit_id] = (_name(game), drop.size, _named(drop.txt, drop.quality))

    def _wait(self, unit_id: int, game: tuple[str, int] | str | None) -> None:
        if not FIELD_AT_ONCE:
            return
        with self.lock:
            if len(self.waiting) > PICKED_MOST:
                self.waiting.clear()
            self.waiting[unit_id] = _name(game)

    def note(self, drop: Drop, game: tuple[str, int] | str | None) -> bool:
        """G18: remember a set or unique drop of BIG_CELLS cells or more the pickup takes by its own rules (`big_named`;
        what is picked is not changed) for the field check; whether it was. With the loop on and the switches on."""
        if not (FIELD_IDENTIFY and FIELD_NAMED) or drop.kind != VALUABLE or not self.looping():
            return False
        if not big_named(drop.txt, drop.quality, drop.size):
            return False
        self._remember(drop.unit_id, game, 'G18')
        self._wait(drop.unit_id, game)
        return True

    def park(self, drop: Drop, game: tuple[str, int] | str | None) -> bool:
        """CUBE_AT_PICKUP: remember a stash-bound drop the pickup takes (`stash_bound`) for the cube at the next quiet
        look (`_park`); whether it was. With the loop on and the switches on."""
        if not (FIELD_AT_ONCE and CUBE_AT_PICKUP) or drop.kind != VALUABLE or not stash_bound(drop.txt):
            return False
        if not self.looping():
            return False
        with self.lock:
            if len(self.parking) > PICKED_MOST:
                self.parking.clear()
            self.parking[drop.unit_id] = _name(game)
        return True

    def _remember(self, unit_id: int, game: tuple[str, int] | str | None, klass: str) -> None:
        with self.lock:
            if len(self.picked) > PICKED_MOST:
                self.picked.clear()
            self.picked[unit_id] = (_name(game), klass)

    def class_of(self, unit_id: int, game: str | None) -> str | None:
        """The class `unit_id` was picked for in `game`, None when it was not picked for the field identify."""
        with self.lock:
            found = self.picked.get(unit_id)
        return found[1] if found is not None and found[0] == game else None

    # -- the routine -----------------------------------------------------------------------------

    def _begin(self, game: str | None) -> None:
        with self.lock:
            if game != self.game:
                self.game = game
                self.tries.clear()
                self.judged.clear()
                self.said.clear()
                self.picked = {unit: found for unit, found in self.picked.items() if found[0] == game}
                self.waiting = {unit: found for unit, found in self.waiting.items() if found == game}
                self.left_said = {key for key in self.left_said if key[0] == game}
                self.roomless = {unit: found for unit, found in self.roomless.items() if found[0] == game}
                self.roomed = {key for key in self.roomed if key[0] == game}
                self.parking = {unit: found for unit, found in self.parking.items() if found == game}

    def settle(self, hands: FieldHands, when: str) -> Settled:
        """The field routine (§2.4): identify what waits, drop what fails; only what is left, so safe to call again.
        The loop's items of the classes in the cube (`cubed`) are taken out into the inventory first where it has room
        for them and a SURE_BLOCK after (the Tome works on the inventory's items: macros/junk.py `identify`), and the
        ones kept, or not identified, go back into the cube after (`_put_back`)."""
        if not FIELD_IDENTIFY or not self.looping():
            return Settled()
        game = hands.game()
        if game is None:
            return Settled()
        self._begin(game)
        pack = hands.carried()
        if pack is None:
            return Settled()
        self.tome_seen = (self.clock(), pack.identifies)  # the pickup's squeeze reads it (`_charges`)
        pending = self._pending(hands.loops(pack), game)
        boxed = [item for item in self._pending(self._cubed(hands, pack, game), game)
                 if item.identified or self.tries[item.unit_id] < MOST_TRIES]  # fmt: skip
        active = [item for item in pending if item.identified or self.tries[item.unit_id] < MOST_TRIES]
        if not active and not boxed:
            return Settled()
        total = len(pending) + len(boxed)
        why = hands.unquiet()
        if why is not None:
            key = (game, when)  # said once a game and site: a stand reads it at every look
            if key not in self.said:
                self.said.add(key)
                self.log('%s %s: %d to identify wait: %s', PREFIX, when, len(active) + len(boxed), why)
            return Settled(waited=why, pending=len(active) + len(boxed))
        out = self._take_out(hands, pack, game, when, pending, boxed)
        if out:
            pack = hands.carried() or pack
            pending = self._pending(hands.loops(pack), game)
        unknown = [item for item in pending if not item.identified and self.tries[item.unit_id] < MOST_TRIES]
        known = [item for item in pending if item.identified]
        done = self._identify(hands, pack, game, when, unknown)
        units = [item.unit_id for item in (*known, *done)]
        judged = self._judge(hands, units, game) if units else []
        self._put_back(hands, when, out)  # not after the player's hand or a cancel: the loop's cube leg takes them
        left = total - len(judged)
        self.log('%s %s: %d identified, %d dropped, %d kept%s', PREFIX, when, len(done), sum(j.dropped for j in judged),
                 sum(not j.dropped for j in judged), f', {left} wait (Cain in town)' if left else '')  # fmt: skip
        return Settled(tuple(judged), None, left)

    def _pending(self, items: Sequence[Carried], game: str) -> list[Carried]:
        return [item for item in items if self.class_of(item.unit_id, game) is not None and item.unit_id not in
                self.judged]  # fmt: skip

    def _cubed(self, hands: FieldHands, pack: Pack, game: str) -> list[Carried]:
        """The loop's items in the cube of a field class: those picked for it this game, and, unidentified, those of
        BIG_CELLS cells or more by their kind (`carried_class`: an item carried into this game, or picked before a
        restart, is not remembered by its unit), each remembered for the game."""
        found = []
        for item in hands.cubed(pack):
            if self.class_of(item.unit_id, game) is None:
                klass = carried_class(item)
                if klass is None:
                    continue
                self._remember(item.unit_id, game, klass)
            found.append(item)
        return found

    def _take_out(
        self, hands: FieldHands, pack: Pack, game: str, when: str, pending: list[Carried], boxed: list[Carried]
    ) -> list[int]:
        """`boxed` (the cube's) into the inventory for the batch, the dearest class first, as many as the inventory
        takes with a SURE_BLOCK still free, the Tome's charges and MOST_A_BATCH allow; the units now out. With
        FIELD_AT_ONCE one big item a batch comes out without the SURE_BLOCK after it, but at the site ROOM_SITE (room
        made for a valuable waiting): it goes back into the cube it came from after, or is put down (the Unique
        Thresher of 14:39:30 on 2026-10-20 went to town unidentified: a 2x4 in the visit's free cells leaves no
        1x3)."""
        if not boxed:
            return []
        charges = (pack.identifies or 0) - sum(not item.identified for item in pending)
        room = max(MOST_A_BATCH - len(pending), 0)
        grid = pack.inventory
        chosen: list[Carried] = []
        bare = FIELD_AT_ONCE and when != ROOM_SITE  # one big item out without the reserve
        for item in sorted(boxed, key=lambda i: (_rank(self.class_of(i.unit_id, game)), -i.size[0] * i.size[1])):
            if len(chosen) >= room or (not item.identified and charges <= 0):
                continue
            spot = grid.first_spot(item.size)
            if spot is None:
                continue  # no room for it: it waits in the cube (Cain in town)
            after = grid.take(spot, item.size)
            if not after.has_room(SURE_BLOCK):
                if not bare or item.size[0] * item.size[1] < BIG_CELLS:
                    continue  # no room for it and a valuable after it: it waits in the cube (Cain in town)
                bare = False
            grid = after
            charges -= not item.identified
            chosen.append(item)
        if not chosen:
            key = (game, f'{when}: cube')
            if key not in self.said:
                self.said.add(key)
                self.log('%s %s: %d in the cube wait: no room to take them out (Cain in town)', PREFIX, when,
                         len(boxed))  # fmt: skip
            return []
        try:
            out = hands.take_out(chosen)
        except Exception as stop:
            if _cut(stop):
                raise
            self.log('%s %s: the cube did not give its items (%s): they wait', PREFIX, when, stop)
            out = []
        for item in chosen:
            if item.unit_id not in out:
                self.tries[item.unit_id] += 1  # bounded: MOST_TRIES, then Cain in town
        self.log('%s %s: %d of %d taken out of the cube to identify', PREFIX, when, len(out), len(chosen))
        return list(out)

    def _put_back(self, hands: FieldHands, when: str, out: list[int]) -> None:
        """The items taken out of the cube and not put down back into it (kept, or not identified); one that does not
        go in stays in the inventory, the loop's cube leg takes it."""
        if not out:
            return
        pack = hands.carried()
        carried = {item.unit_id for item in hands.loops(pack)} if pack is not None else set()
        back = [unit for unit in out if unit in carried]
        if not back:
            return
        try:
            moved = hands.put_back(back)
        except Exception as stop:
            if _cut(stop):
                raise
            self.log('%s %s: %d not put back into the cube (%s): they stay in the inventory', PREFIX, when, len(back),
                     stop)  # fmt: skip
            return
        self.log('%s %s: %d of %d put back into the cube', PREFIX, when, moved, len(back))

    def _identify(self, hands: FieldHands, pack: Pack, game: str, when: str, items: list[Carried]) -> list[Carried]:
        if not items:
            return []
        charges = pack.identifies or 0
        if charges <= 0:
            key = (game, 'no charges')
            if key not in self.said:
                self.said.add(key)
                self.log('%s %s: the Tome of Identify is empty or not carried: %d wait for Cain', PREFIX, when,
                         len(items))  # fmt: skip
            return []
        order = sorted(items, key=lambda i: (_rank(self.class_of(i.unit_id, game)), -i.size[0] * i.size[1], i.y, i.x))
        batch = order[: min(charges, MOST_A_BATCH)]
        try:
            done = hands.identify(batch)
        except Exception as stop:
            if _cut(stop):
                raise  # the player's hand or a cancel: no failure, the run ends as from any act
            self.log('%s %s: the identify stopped (%s): the items wait', PREFIX, when, stop)
            for item in batch:
                self.tries[item.unit_id] += 1
            return []
        taken = {item.unit_id for item in done}
        for item in batch:
            self.tries[item.unit_id] += 1
            if item.unit_id not in taken and self.tries[item.unit_id] >= MOST_TRIES:
                self.log('%s %s (unit %d) did not take an identify %d times: Cain in town', PREFIX,
                         _label(item), item.unit_id, MOST_TRIES)  # fmt: skip
        return list(done)

    def _judge(self, hands: FieldHands, units: list[int], game: str) -> list[Judged]:
        found = hands.appraise(units)
        pack = hands.carried()
        carried = {item.unit_id: item for item in hands.loops(pack)} if pack is not None else {}
        judged: list[Judged] = []
        for unit in units:
            item = carried.get(unit)
            if item is None:
                continue  # gone from the inventory meanwhile: nothing to decide
            entry = found.get(unit)
            read = entry.observation.get('item') if entry is not None else None
            if entry is None or not isinstance(read, Mapping) or read.get('identified') is not True:
                self.judged[unit] = 'kept: no identified read'
                self.log('%s %s (unit %d): no identified read or appraisal: kept (S8), Cain and the town decide',
                         PREFIX, _label(item), unit)  # fmt: skip
                judged.append(Judged(unit, _label(item), None))
                continue
            facts = from_carried(item, owner=Owner.LOOP, observation=entry.observation)
            value = appraise_result(facts, entry.result, entry.verdict)
            [(_, _, decision)] = decide_all([(facts, value)], hands.copies)
            self.log('%s %s (unit %d): %s', PREFIX, facts.title(), unit, decision.said())
            dropped = False
            if decision.action == Action.DROP:
                named = facts.quality in (SET, UNIQUE)
                refused = droppable(facts, value, hands.copies(facts) if named else None)
                if refused is not None:
                    self.log('%s %s (unit %d): not dropped: %s', PREFIX, facts.title(), unit, refused)
                else:
                    reason = f'a surplus copy, not better, cheap: {decision.reason}' if named else decision.reason
                    why = f'in the field: {decision.rule} {reason}'
                    dropped = self._drop(hands, item, why)
            self.judged[unit] = decision.action.value
            judged.append(Judged(unit, facts.title(), decision, dropped))
        return judged

    def _drop(self, hands: FieldHands, item: Carried, why: str) -> bool:
        try:
            dropped = hands.drop(item, why)
        except Exception as stop:
            if _cut(stop):
                raise
            self.log('%s %s (unit %d): the drop stopped (%s): kept for now', PREFIX, _label(item), item.unit_id, stop)
            return False
        if dropped:
            hands.reject(item, why)
        return dropped

    # -- the big items at once (FIELD_AT_ONCE) ---------------------------------------------------------------------

    def _due_units(self, game: str | None) -> set[int]:
        with self.lock:
            return {unit for unit, found in self.waiting.items()
                    if found == game and unit not in self.judged and self.tries[unit] < MOST_TRIES}  # fmt: skip

    def _roomless_due(self, game: str | None) -> dict[int, tuple[tuple[int, int], str]]:
        with self.lock:
            return {unit: (size, label) for unit, (found, size, label) in self.roomless.items()
                    if found == game and (game, unit) not in self.roomed}  # fmt: skip

    def due(self, now: float | None = None) -> bool:
        """Whether the level run's quiet look makes the routine now (`at_once`): the switches and the loop on, a big
        item picked for it not decided yet or a field item on the ground with no room not yet made room for,
        AT_ONCE_EVERY since the last look. Reads nothing."""
        if not (FIELD_IDENTIFY and FIELD_AT_ONCE) or not self.looping():
            return False
        with self.lock:
            some = (
                any(unit not in self.judged and self.tries[unit] < MOST_TRIES for unit in self.waiting)
                or any((found[0], unit) not in self.roomed for unit, found in self.roomless.items())
                or bool(self.parking)
            )
        if not some:
            return False
        now = self.clock() if now is None else now
        if now - self.looked_at < AT_ONCE_EVERY:
            return False
        self.looked_at = now
        return True

    def at_once(self, hands: FieldHands) -> bool:
        """The routine at the level run's quiet look (the player, 2026-10-20 ~14:28: "space for mid-run identifying
        big items"): for a big item picked for it carried unidentified (`_big_at_once`), then room in the cube for a
        field item left on the ground with none (`_room_for`). Whether anything was done."""
        game = hands.game()
        if game is None:
            return False
        self._begin(game)
        parked = self._park(hands, game)  # the free block kept for what needs the Tome
        done = self._big_at_once(hands, game)
        return self._room_for(hands, game) or done or parked

    def _park(self, hands: FieldHands, game: str) -> bool:
        """The loop's stash-bound items carried (runes, gems, shards, statues, keys, essences: the resource tabs';
        `stash_bound`) into the cube in one batch, at the first quiet look after one was picked (CUBE_AT_PICKUP; the
        player, 2026-10-20 ~15:02: "move all items that we're going to stash in town (gems/runes/statues/etc) pickup
        and stash in cube, to have space for identifying items along the way"): only where the cube's grid takes them
        (cube.py `stash_only` and its `plan`), never the player's, the Tome, the cube or a potion. The town visit takes
        them from the cube onto the tabs as it does the level end's (loot/storage.py). Once a pickup; whether any
        moved."""
        with self.lock:
            units = {unit for unit, found in self.parking.items() if found == game}
        if not units:
            return False
        pack = hands.carried()
        if pack is None:
            return False
        carried = {item.unit_id for item in hands.loops(pack)}
        with self.lock:
            for unit in units - carried:
                if any(item.unit_id == unit for item in pack.in_cube):
                    self.parking.pop(unit, None)  # in the cube already
        due = units & carried
        if not due:
            return False  # still on the ground: the pickup's
        if hands.unquiet() is not None:
            return False  # looked at again at the next quiet look
        with self.lock:
            for unit in due:
                self.parking.pop(unit, None)  # one try a pickup
        bound = [item for item in hands.loops(pack) if stash_bound(item.txt)]
        going = cube_fits(pack, bound)
        if not going:
            self.log("Macro: loot: cube: %d of the loop's stash-bound items stay in the inventory: no room in the cube",
                     len(bound))  # fmt: skip
            return False
        try:
            moved = hands.put_back([item.unit_id for item in going])
        except Exception as stop:
            if _cut(stop):
                raise
            self.log("Macro: loot: cube: the loop's stash-bound items not moved in (%s)", stop)
            return False
        self.log("Macro: loot: cube: %d of the loop's stash-bound items moved in (%s)", moved,
                 ', '.join(_base_name(item.txt) for item in going))  # fmt: skip
        return moved > 0

    def _big_at_once(self, hands: FieldHands, game: str) -> bool:
        """`settle` at the site AT_ONCE (it waits with a hostile within SIGHT, a panel open or a valuable to pick up)
        for the big items picked for it, then the kept ones into the cube where it has room, so the free block is free
        again (`_into_cube`). Whether anything was decided. One still on the ground is the pickup's: nothing is read
        further."""
        units = self._due_units(game)
        if not units:
            return False
        pack = hands.carried()
        if pack is None:
            return False
        self.tome_seen = (self.clock(), pack.identifies)
        carried = {item.unit_id: item for item in hands.loops(pack) if item.unit_id in units}
        # One moved into the cube meanwhile (the room rules' stash) is taken out for it (`_take_out`)
        boxed = {item.unit_id: item for item in hands.cubed(pack) if item.unit_id in units}
        if not carried and not boxed:
            return False
        if not pack.identifies and any(not item.identified for item in (*carried.values(), *boxed.values())):
            with self.lock:
                for unit in (*carried, *boxed):
                    self.tries[unit] = MOST_TRIES  # no look again this game: Cain in town
            self.log('%s %s: the Tome of Identify is empty or not carried: %d big wait for Cain', PREFIX, AT_ONCE,
                     len(carried) + len(boxed))  # fmt: skip
            return False
        done = self.settle(hands, AT_ONCE)
        if done.waited is not None:
            return False
        self._into_cube(hands, [item for item in done.judged if not item.dropped and item.unit_id in carried])
        return bool(done.judged)

    def _room_for(self, hands: FieldHands, game: str) -> bool:
        """Room for a field item left on the ground for want of it (`roomless`; the rare Kriss of 14:52:26 on
        2026-10-20: flawless gems filled the free cells, and an identify candidate gets no cube room or trip): in the
        quiet (`unquiet`), the field routine's own drops first (`settle`), then the loop's decided items (gems, runes,
        charms, kept ones; never the player's, never one waiting for the routine) into the cube where that frees a
        block of its size (`room_moves`); the cube full too, the room rules' trip to town (`trip`; the player, ~14:58:
        "we need to optimize space (move to cube) and identify items during games / if we have no room for
        optimization to keep picking up items - we need to do town routine"). Once a drop a game; whether anything was
        done."""
        wanted = self._roomless_due(game)
        if not wanted:
            return False
        pack = hands.carried()
        if pack is None:
            return False
        on_ground = {unit: found for unit, found in wanted.items() if all(i.unit_id != unit for i in pack.items)}
        for unit in set(wanted) - set(on_ground):
            self.roomed.add((game, unit))  # picked up meanwhile
        if not on_ground:
            return False
        if hands.unquiet() is not None:
            return False  # said by the routine's own waits; looked at again
        self.settle(hands, AT_ONCE)  # a bad field item put down frees its cells
        pack = hands.carried() or pack
        unit, (size, label) = max(on_ground.items(), key=lambda pair: pair[1][0][0] * pair[1][0][1])
        for found in on_ground:
            self.roomed.add((game, found))
        if pack.inventory.has_room(size):
            return False
        movable = [item for item in hands.loops(pack) if self.class_of(item.unit_id, game) is None
                   or item.unit_id in self.judged]  # fmt: skip
        moves = room_moves(pack, movable, size)
        if not moves:
            if self.trip(label):
                self.log('%s %s: %s (unit %d): the cube has no room for its %dx%d: a trip to town for room', PREFIX,
                         AT_ONCE, label, unit, *size)  # fmt: skip
                return True
            self.log('%s %s: %s (unit %d) left: the cube can make no room for its %dx%d and no trip is made', PREFIX,
                     AT_ONCE, label, unit, *size)  # fmt: skip
            return False
        try:
            moved = hands.put_back([item.unit_id for item in moves])
        except Exception as stop:
            if _cut(stop):
                raise
            self.log('%s %s: no room made for %s (unit %d): %s', PREFIX, AT_ONCE, label, unit, stop)
            return False
        self.log("%s %s: %s (unit %d): room: %d of the loop's items into the cube", PREFIX, AT_ONCE, label, unit,
                 moved)  # fmt: skip
        return moved > 0

    def _into_cube(self, hands: FieldHands, kept: Sequence[Judged]) -> None:
        """The kept big items into the cube where it has room (cube.py `stash_only` through `put_back`: the loop's
        only); one with no room stays in the inventory, and the room rules answer the next valuable."""
        if not kept:
            return
        pack = hands.carried()
        if pack is None:
            return
        carried = {item.unit_id: item for item in hands.loops(pack)}
        grid = Grid(pack.cube) if pack.cube is not None else None
        going: list[tuple[Carried, str]] = []
        for judged in kept:
            item = carried.get(judged.unit_id)
            if item is None:
                continue  # gone from the inventory meanwhile
            spot = grid.first_spot(item.size) if grid is not None else None
            if grid is None or spot is None:
                self.log('%s %s: %s (unit %d) kept: it stays in the inventory, the cube has no room for it', PREFIX,
                         AT_ONCE, judged.title, judged.unit_id)  # fmt: skip
                continue
            grid = grid.take(spot, item.size)
            going.append((item, judged.title))
        if not going:
            return
        try:
            moved = hands.put_back([item.unit_id for item, _ in going])
        except Exception as stop:
            if _cut(stop):
                raise
            self.log('%s %s: %d kept not put into the cube (%s): they stay in the inventory', PREFIX, AT_ONCE,
                     len(going), stop)  # fmt: skip
            return
        after = hands.carried()
        inside = after.cube_items if after is not None else frozenset()
        for item, title in going:
            where = 'into the cube' if item.unit_id in inside else 'it stays in the inventory, not moved'
            self.log('%s %s: %s (unit %d) kept: %s', PREFIX, AT_ONCE, title, item.unit_id, where)
        if moved < len(going):
            self.log('%s %s: %d of %d kept put into the cube', PREFIX, AT_ONCE, moved, len(going))


def stash_bound(txt: int | None) -> bool:
    """Whether an item of class `txt` goes onto the stash's resource tabs whatever else is decided (runes, gems, the
    materials: keys, statues, shards, essences, organs; loot/storage.py RESOURCES), never a potion."""
    return txt is not None and txt in RESOURCES and not is_potion(txt)


def cube_fits(pack: Pack, items: Sequence[Carried]) -> list[Carried]:
    """Those of `items` the cube's free cells take, each in the first free block, the larger first (as cube.py `plan`);
    [] with no cube carried. Pure. An empty cube has no grid in memory: read as empty (storage.py `roomed`; 16:52 on
    2026-10-20, after each town visit: "no room in the cube" with the cube empty)."""
    pack = roomed(pack)
    if pack.cube is None:
        return []
    cube = Grid(pack.cube)
    going: list[Carried] = []
    for item in sorted(items, key=lambda i: (-i.size[0] * i.size[1], -i.size[1], i.y, i.x)):
        spot = cube.first_spot(item.size)
        if spot is not None:
            cube = cube.take(spot, item.size)
            going.append(item)
    return going


def _base_name(txt: int) -> str:
    from inventory_tracking.items.metadata import item_base

    base = item_base(txt)
    return base['name'] if base is not None else str(txt)


def room_moves(pack: Pack, movable: Sequence[Carried], size: tuple[int, int]) -> list[Carried]:
    """`movable` (the loop's inventory items), smallest first, as many as the cube's free cells take until a block
    of `size` is free in the inventory; [] when that never comes (or no cube is carried). Pure. An empty cube's
    unread grid is empty (storage.py `roomed`)."""
    pack = roomed(pack)
    if pack.cube is None:
        return []
    cube = Grid(pack.cube)
    staying = list(pack.items)
    chosen: list[Carried] = []
    for item in sorted(movable, key=lambda i: (i.size[0] * i.size[1], i.y, i.x)):
        spot = cube.first_spot(item.size)
        if spot is None:
            continue
        cube = cube.take(spot, item.size)
        staying = [i for i in staying if i.unit_id != item.unit_id]
        chosen.append(item)
        if Grid.from_items(staying, INVENTORY_SIZE).has_room(size):
            return chosen
    return []


def _rank(klass: str | None) -> int:
    return ORDER.index(klass) if klass in ORDER else len(ORDER)


def _name(game: tuple[str, int] | str | None) -> str | None:
    return game[0] if isinstance(game, tuple) else game


def _named(txt: int | None, quality: int) -> str:
    from inventory_tracking.items.metadata import item_base

    base = item_base(txt) if txt is not None else None
    return f'{"magic" if quality == MAGIC else "rare" if quality == RARE else "item"} ' + (
        base['name'] if base is not None else str(txt)
    )


def _label(item: Carried) -> str:
    return _named(item.txt, item.quality)


FIELD = Field()


def settle(run: Any, when: str) -> None:
    """The field routine's hook, one call at each site (a level's end, the room made): the run's own (`Run.field`,
    running/execution.py), nothing when it has none. Raises only the player's hand and the run's cancel."""
    field = getattr(run, 'field', None)
    if field is None:
        return
    try:
        field(when)
    except Exception as stop:
        if _cut(stop):
            raise
        LOG.info('%s %s: not made (%s: %s); the leg goes on', PREFIX, when, type(stop).__name__, stop)


def at_once(hands: Callable[[], FieldHands], field: Field | None = None) -> bool:
    """The level run's hook at a quiet look (hunt.py `field_now`): the routine for a big item picked for it
    (`Field.at_once`), the hands made only when one is due (`Field.due`); whether anything was decided. Raises only
    the player's hand and the run's cancel."""
    found = FIELD if field is None else field
    if not found.due():
        return False
    try:
        return found.at_once(hands())
    except Exception as stop:
        if _cut(stop):
            raise
        LOG.info('%s %s: not made (%s: %s); the run goes on', PREFIX, AT_ONCE, type(stop).__name__, stop)
        return False
