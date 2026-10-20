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
"""

import threading
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from inventory_tracking.common import LOG
from inventory_tracking.config import APPRAISAL
from inventory_tracking.game.records import VALUABLE, Carried, Drop, Pack
from inventory_tracking.items.grid import Grid
from inventory_tracking.loot import ground_judge
from inventory_tracking.loot.facts import MAGIC, RARE, SET, UNIQUE, ItemFacts, Owner, from_carried, from_drop
from inventory_tracking.loot.ground_judge import Then
from inventory_tracking.loot.keep import (
    CHARMS,
    GEMS,
    JEWELS,
    LOOP_GEAR,
    ORGANS,
    POTIONS,
    RUNES,
    SUNDER,
    Action,
    Decision,
    decide_all,
)
from inventory_tracking.loot.shadow import Appraised
from inventory_tracking.loot.storage import SURE_BLOCK
from inventory_tracking.loot.value import DUPLICATE_IST, Value, appraise_result


__all__ = [
    'BIG_CELLS',
    'CLASSES',
    'FIELD',
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
    'droppable',
    'leaves_room',
    'oversize',
    'reserve_short',
    'settle',
]

# M4 on (the player, 2026-10-20: "also start M4 field identify"). False: nothing is picked for the field identify and
# nothing identified or dropped in the field; the tome's reserve is no reason for a visit
FIELD_IDENTIFY = True
# The classes of loot/design.md §4.2 the field identify picks and judges: G6 every magic Monarch, first (§7 M4: "G6
# first (every magic Monarch), then G9-G11"). G9 (magic/rare daggers and grimoires), G10 (magic/rare circlets) and
# G11 (magic rings and amulets: the rare ones are today's pickup); the player, 2026-10-20 ~11:05: "turn on G9-G11 too".
# G14 the shown magic/rare items of BIG_CELLS+ cells and G15 those over the cell cap (module text; the player, ~12:00:
# "start all three")
CLASSES = frozenset(('G6', 'G9', 'G10', 'G11', 'G14', 'G15'))
IMPLEMENTED = frozenset(('G6', 'G9', 'G10', 'G11', 'G14', 'G15'))
# The order a batch identifies the classes in (§5 `identify.order`): the dearest class first, then the larger items
ORDER = ('G6', 'G10', 'G9', 'G15', 'G14', 'G11')
# Step 1 of the big items (module text; the player, 2026-10-20 ~11:55 "we want to check them and drop in the middle of
# the run", ~12:00 "start all three"; Q6: "a scroll on every item >= 4 cells"). False: such an item is the GOOD
# pickup's only by another class, and the MOST level carries it to town unjudged as before
FIELD_BIG = True
# Step 2 (the same words: "like spears, matron bow"). False: the cell cap holds for magic and rare items as before
FIELD_OVERSIZE = True
BIG_CELLS = 4  # Q6 "every item >= 4 cells": a 2x2 helm, glove, boot, circlet and up
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


def droppable(facts: ItemFacts, value: Value | None = None) -> str | None:
    """Why the field drop must not put `facts` down whatever its decision, None when it may: not the loop's, not
    identified, a set or unique item, a never-dropped kind, or (`value`) a want row names it or it is expensive. A
    second guard below `keep.decide`, stricter on purpose: a magic Monarch with 4 sockets or of Deflecting is never
    put down in the field ("4os monarch deflection -- we absolutely want to keep it", the player, 2026-10-20)."""
    if facts.owner != Owner.LOOP:
        return f"not the loop's (owner {facts.owner.value})"
    if not facts.identified:
        return 'not identified'
    if facts.quality in (SET, UNIQUE):
        return 'a set or unique item'
    if facts.base_type in NEVER_DROPPED:
        return 'never dropped (runes, gems, potions, charms, jewels, tools)'
    if value is not None and value.wants:
        return f'wanted: {value.wants[0].label}'
    if value is not None and value.worth_ist is not None and value.worth_ist >= DUPLICATE_IST:
        return f'expensive ({value.worth_ist:.3g} Ist)'
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

    def pick(self, drop: Drop, game: tuple[str, int] | str | None, room: tuple[str, ...] | None = None) -> bool:
        """Whether the pickup takes `drop` for the field identify (`takes`), with `room` (the inventory's rows, None
        unread) left for a valuable after it (`leaves_room`); remembered for `game` when it does."""
        klass = self.takes(drop)
        if klass is None:
            return False
        if cells(drop) >= BIG_CELLS and not leaves_room(room, drop.size):
            return False  # a big one never takes a valuable's room: left, seen again at the next look
        name = game[0] if isinstance(game, tuple) else game
        with self.lock:
            if len(self.picked) > PICKED_MOST:
                self.picked.clear()
            self.picked[drop.unit_id] = (name, klass)
        return True

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

    def settle(self, hands: FieldHands, when: str) -> Settled:
        """The field routine (§2.4): identify what waits, drop what fails; only what is left, so safe to call again."""
        if not FIELD_IDENTIFY or not self.looping():
            return Settled()
        game = hands.game()
        if game is None:
            return Settled()
        self._begin(game)
        pack = hands.carried()
        if pack is None:
            return Settled()
        mine = [item for item in hands.loops(pack) if self.class_of(item.unit_id, game) is not None]
        pending = [item for item in mine if item.unit_id not in self.judged]
        unknown = [item for item in pending if not item.identified and self.tries[item.unit_id] < MOST_TRIES]
        known = [item for item in pending if item.identified]
        if not unknown and not known:
            return Settled()
        why = hands.unquiet()
        if why is not None:
            key = (game, when)  # said once a game and site: a stand reads it at every look
            if key not in self.said:
                self.said.add(key)
                self.log('%s %s: %d to identify wait: %s', PREFIX, when, len(unknown) + len(known), why)
            return Settled(waited=why, pending=len(unknown) + len(known))
        done = self._identify(hands, pack, game, when, unknown)
        units = [item.unit_id for item in (*known, *done)]
        judged = self._judge(hands, units, game) if units else []
        left = len(pending) - len(judged)
        self.log('%s %s: %d identified, %d dropped, %d kept%s', PREFIX, when, len(done), sum(j.dropped for j in judged),
                 sum(not j.dropped for j in judged), f', {left} wait (Cain in town)' if left else '')  # fmt: skip
        return Settled(tuple(judged), None, left)

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
                refused = droppable(facts, value)
                if refused is not None:
                    self.log('%s %s (unit %d): not dropped: %s', PREFIX, facts.title(), unit, refused)
                else:
                    why = f'in the field: {decision.rule} {decision.reason}'
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


def _rank(klass: str | None) -> int:
    return ORDER.index(klass) if klass in ORDER else len(ORDER)


def _label(item: Carried) -> str:
    from inventory_tracking.items.metadata import item_base

    base = item_base(item.txt)
    return f'{"magic" if item.quality == MAGIC else "rare" if item.quality == RARE else "item"} ' + (
        base['name'] if base is not None else str(item.txt)
    )


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
