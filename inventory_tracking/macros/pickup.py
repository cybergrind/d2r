"""The pickup step: one thing that is not fighting (user, 2026-10-10), the first that applies:

1. the nearest valuable (runes, marked materials, what the loot filter shows), then gold within one jump;
2. a super healing or full rejuvenation potion the belt is short of (`column_shortages`);
3. with the belt full and life missing, drink one and pick the ground one up in its place;
4. else `otherwise` (the runner: hunt.Hunter.step).

The item under the pointer is read before a click (`take`): in a pile the labels stack, and an unwanted item is
never clicked. One press takes up to PICKS potions, a pile of valuables, or one drink. Far drops are hopped toward
first (`approach`); the item leaving the ground is the proof. Evidence for the aims and timings: history/pickup.md.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from functools import partial
from typing import Protocol

from inventory_tracking.combat.policy import RUN_MODES
from inventory_tracking.common import LOG
from inventory_tracking.config import APPRAISAL, BELT, INPUT
from inventory_tracking.game.layout import ITEM_UNIT, MONSTER_UNIT
from inventory_tracking.game.records import GOLD, HEALING, REJUVENATION, VALUABLE, Drop, Loot, Player, has_room
from inventory_tracking.levels.model import Ground, Level, Target
from inventory_tracking.loot import api as field_api, ground_judge
from inventory_tracking.loot.api import FIELD
from inventory_tracking.loot.materials import material_classes
from inventory_tracking.loot.shown import RARITIES, game_filter, oversize_rules, pickup_rules, profile, shown_gems
from inventory_tracking.macros import lootpolicy, pile
from inventory_tracking.macros.actuator import Abort, Cancelled, Expired, Hand
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.charms import GHEEDS_FORTUNE, is_unique_grand_charm
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import ACTING, DEAD, UNIT_PIXELS, Dead, press_skill
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.teleport import HOVER_SECONDS, ground_fraction, hop_toward, in_view, ready, ready_world
from inventory_tracking.macros.travel import JUMP_REACH, PRESSED, Travel, spare_jump, walk_reaches
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS, TILE_UNITS
from inventory_tracking.tracking.belt import column_shortages, potion_kind


# Gold is taken by standing on it (user, 2026-10-11: "blade warp to location would be enough"); a click when too
# near to jump or the jump missed. Only a pile within one jump is worth it.
GOLD_UNITS = JUMP_REACH
GOLD_WALK = 6.0  # world units: a pile this near is walked onto
GOLD_SECONDS = 0.9  # for the pile to leave the ground (a 23-unit Blade Warp lands in 0.81 s)
POTION_UNITS = 25.0  # world units: a potion further off is not worth the walk
PICK_UNITS = 20.0  # a drop this near, in view, is clicked (the character walks); further, hopped toward
HOPS = 4  # teleports toward one drop per press at most
FETCH_HOPS = 16  # a trip back to a remembered valuable (runner.py `_fetch`): the whole way, ~25 units a hop
DRINK_SECONDS = 0.6  # the belt watched after the drink's key, pressed DRINK_TAPS times at most
DRINK_TAPS = 2
DRINK_BELOW = 0.7  # of the life: under it a potion is drunk to make room for the one on the ground
# Click aims, classic pixels (600 high; across, down) from the drop's ground, in turn: a click lands ~14 px lower
# than `ground_fraction`, and 24 px up took it most often (history/pickup.md).
ITEM_AIMS = ((0, -24), (0, -14), (0, -6), (-10, -14), (10, -14), (0, -34), (0, 2))
# Where the label is looked for first, from afar too: the column above the item (pile labels stack 30 px apart).
LOOK_AIMS = ((0, -24), (0, -54), (0, -34), (0, -44), (0, -14), (0, -64), (0, -74), (0, -84))
MOVED_UNITS = 1.0  # the character this far from where an aim was taken: the pointer is on other ground by now
# Further aims only looked at, never clicked blind: a blind click once took an unwanted potion from a pile.
PILE_AIMS = ((0, -44), (-20, -24), (20, -24), (0, -54), (-20, -44), (20, -44), (0, -64), (-30, -14), (30, -14))
# With PILE_DROPS or more drops within PILE_UNITS of the one wanted, `pile_aims` looks further (never clicked unseen).
PILE_DROPS = 3
PILE_UNITS = 10.0
PILE_MORE = 30  # further aims looked at for one drop at most (0.06 s each)
SHUN_MISS = 8.0  # a drop no click took is left alone this long, so the next press takes the rest of the pile
STAND_SECONDS = 1.5  # for the character to come to a stand before an aim is taken
NEAR_UNITS = 6.0  # world units: a drop further off is walked up to before every aim is tried
PICKS = 4  # potions one press picks up at most, while the belt is still short and one lies near
PICK_SECONDS = 1.5  # for the item to leave the ground after the click, plus the walk at WALK_SPEED
WALK_SPEED = 6.0  # world units a second, on the slow side
CLICKS = 2  # clicks on an aim that has the item under it
# Aims with the item under the pointer and no pickup before it is given up, for SHUN_SECONDS (2026-10-10 22:16:
# 30 clicks in 21 s on a Large Charm, cause unknown).
MISSED_AIMS = 3
SHUN_SECONDS = 30.0
SHUNNED: dict[int, float] = {}  # unit id -> the clock until which the pickup step leaves the drop alone
# Valuables clicked and not seen to leave the ground in the wait: unit id -> (drop, clock of the click); found
# carried later, picked up late (`late`).
CLICKED: dict[int, tuple[Drop, float]] = {}
LATE_SECONDS = 5.0  # after its click, a valuable found carried counts as picked up by it
# Aims looked at with the drop not under the pointer: unit id -> those aims. A level run's pickup is cut at its
# priced 1.5 s (~10 aims), and each try began at the same aims: a Grand Charm among 9 drops never got to the pile's
# aims in 3 tries (2026-10-20 00:04:36-41). The next try looks at the others first.
LOOKED: dict[int, set[tuple[int, int]]] = {}
LOOKED_MOST = 64  # drops remembered at most
# Valuables read on the ground: unit id -> (drop, clock of the read); one found carried within LATE_SECONDS that no
# pickup click took was taken by a move's click (`taken_by_a_move`, 2026-10-19). SEEN_MOST: cleared past it.
SEEN: dict[int, tuple[Drop, float]] = {}
SEEN_MOST = 200
STOP_UNITS = 40.0  # world units: a valuable this near holds a teleport step back (`worth_a_stop`)
STOP_TRIES = 2
STOPPED: dict[int, int] = {}  # unit id -> the teleport steps that went for the drop instead of hopping
# The pickup's line, said by the click's wait (`click`) and by a later look's read (`pending`); the watch reads it
# (d2-loop-watch logwords.py PICKED)
PICKED_LINE = (
    'Macro: picked up %s %.2fs after the click %s pixels from its ground, from %.1f away; under the pointer %s'
)
STOOD_SECONDS = 0.4  # the character standing this long after a click with the item still there: a miss
# PICK_AT_ONCE (2026-10-25, rca/2026-10-25/smoothness-findings.md §3.2; the player: "when I'm playing it by hand it
# feels way smoother"): a near pickup waited after its click for the item to leave the ground (0.15 s p50, 0.19 p90)
# before the next look, then the look and the next act (0.12 s): ~0.27 s standing a pickup, 51 near pickups/h. True: a
# click on a drop within AT_ONCE_UNITS that the hover record names under the pointer, watched AT_ONCE_LOOK for a walk it
# began (then the wait as before), returns; the drop is out of every choice (SHUNNED, `unshunned`:
# the agenda's, the sweep's, the press's) for AT_ONCE_SECONDS, and its "picked up" is read at the next looks
# (`pending`, from `late`): said when it is off the ground. Still on the ground after AT_ONCE_SECONDS: a target again,
# a valuable watched as a click's (CLICKED, `late`), and that drop's next click waits as before (AT_ONCE_MISSED).
# False: every click waits, as before.
PICK_AT_ONCE = False
AT_ONCE_UNITS = 3.0  # world units: a drop this near is taken where the character stands
AT_ONCE_SECONDS = 0.5  # the click -> off the ground p90 0.19 s (the session of 2026-10-25, 154 near pickups)
AT_ONCE_LOOK = 0.06  # seconds the click is watched first: a walk it began shows by then (walks set off 0.03 s p50)
AT_ONCE_POLL = 0.02
# Unit id -> (drop, clock of the click, aim, distance, the hover record): the clicks whose pickup a later look reads
PENDING: dict[int, tuple[Drop, float, tuple[int, int], float, tuple[int, int] | None]] = {}
AT_ONCE_MISSED: set[int] = set()  # drops an at-once click left on the ground: their next click waits
AT_ONCE_MOST = 64  # misses remembered at most
POLL = 0.05
# Never a click with an item under the pointer that serves the press nothing (the player, 2026-10-21 ~00:55: "not
# always clicking correct object (we often can pickup hp/rejuv potion) that we wanted"): the game takes the item under
# the pointer. A blind aim (`_take`'s last stage) skips one that is no drop of the press's lists, not only one of
# `others`; the walk up to a far drop (`walk_up`) with another drop within LABEL_NEAR clicks its ground only with no
# other item's label there, else WALK_UP_AIMS classic pixels below it (labels stand above their items), else it is not
# walked up to. A lone drop's walk up is clicked at once, as before (the hover wait is 0.06 s). False: clicked as before
LABEL_GUARD = True
WALK_UP_AIMS = ((0, 10), (0, 20))
LABEL_NEAR = 4.0  # world units: another drop this near may have its label over the drop's ground
# The player, 2026-10-21 ~13:40: "we weren't able to pickup hp potions on the groud, it looks like we still have the
# issue with clicks". Travincal, 13:37:16-24: a super healing potion 18.6 away under the pointer at every aim, 11 clicks
# in 8 s, and the character never moved; an Amulet 19.0 away alike at 02:06:18 on 2026-10-20: the game took the clicks
# and began no walk to the item (rca/2026-10-21/potion-click-findings.md). True: an aim's CLICKS with the drop under the
# pointer that left the character standing further than NEAR_UNITS end the aims (`Unmoved`), and `pick_up` goes nearer
# first (`nearer`: a hop beside it, else the build's own move) and takes it from there. False: the other aims clicked
# from afar, as before
NEARER_AFTER_STILL = True
NEARER_HOPS = 2  # hops toward the drop at most for it
UNMOVED: dict[int, float] = {}  # unit id -> the clock until which a try goes nearer before its first click
UNMOVED_SECONDS = 30.0
# The player, 2026-10-21 ~13:40 (that potion: the loop left the game for it, a Worldstone Shard's act with it). True: a
# drop no click took that the loop keeps no game for (a potion, gold, an item lootpolicy's GUARD does not hold: what
# runner.py `valuable_left` names) is given up for the game (`give_up`) and the press goes on; a valuable stops the
# press as before (`Missed`). False: as before
GIVE_UP_CHEAP = True
GIVEN_UP: dict[int, object] = {}  # unit id -> the game it was given up in (`Loot.game`): out of every look in it
# The player, 2026-10-22 ~08:31: "why we're trying to pickup gothic staff that are hidden by our loot filter?" A label
# the game does not draw cannot be clicked: 4 presses of every aim read nothing under the pointer (the hover record's
# flag 0) and the loop stopped for the staff twice (rca/2026-10-22/hidden-staff-findings.md). True: a drop whose
# label was under the pointer at none of UNLABELLED_AIMS or more aims, every one read as nothing (no other unit, no
# unread record) with Show Items on, is `Unlabelled`; at its UNLABELLED_TRIES-th such press in a game it is waived
# (`waive`): given up for the game and out of what the loop guards (runner.py `valuable_left`, the sightings), however
# valuable, and the press goes on. False: a `Missed` as before
WAIVE_UNLABELLED = True
UNLABELLED_AIMS = 6
# 2026-10-24 (rca/2026-10-24/pickup-pack-findings.md; game 5 of 2026-10-23, take 20261023T202950Z-57): a level run
# ended on a clear spot by a tier 5 Herald pack and handed the press on; the pickup Blade Warped 16 back into the pack
# for 5648 gold, then clicked 6210 gold 8.7 s with 2-3 hostiles within 3: 2 Rejuvenations, the merc left in the pack,
# the death 10 s on. True: a press's gold (a guarded site's, `threat` given, the press's own choice: no goal's `unit`)
# waits as a potion does while a tier 4-5 Herald pack's member (combat/pack.py `in_pack`), or GOLD_CROWD hostiles,
# stand within hunting/base.py GATHER_CLEAR of the character or the pile (`pack_guard`): the press goes to `otherwise`
# (the fight), the pile stays on the ground for the next press. A goal's gold is the hunt's, held while its fight is
# live (hunting/choice.py POTION_HELD). Valuables are never held (the player's rule). False (until its gate): gold taken
# as before. On 2026-10-24 ~11:40, gated: halls 8/20 dead -> 0/20, 280 gold-scene pairs the same, 4 presses in 32 h.
PACK_GOLD_WAIT = True
GOLD_CROWD = 6  # the replay of 2026-10-21..24: 18 gold presses with 3-6 hostiles near (no pack) lost 72 life in all
UNLABELLED_TRIES = 2
UNLABELLED: dict[int, tuple[object, int]] = {}  # unit id -> (the game, its unlabelled presses in it)
WAIVED: dict[int, object] = {}  # unit id -> the game it was waived in (`waive`)
KINDS = {HEALING: PotionType.HEALING, REJUVENATION: PotionType.REJUVENATION}


@dataclass(frozen=True)
class Plan:
    drop: Drop
    drink: str | None = None  # the belt key to press first


class Refused(Abort):
    """A unique Grand Charm the game refused: a Gheed's Fortune is carried, and it is carry-one (the player,
    2026-10-18: "you cannot pickup another gheed if you have another in inventory/private tab"). Raised at the first
    such click (`refusal`); the KP_6 loop's Gheed's swap starts on it (runner.py `_gheeds_swap`)."""

    def __init__(self, drop: Drop, why: str) -> None:
        super().__init__(why)
        self.drop = drop


class Missed(Abort):
    """No click took `drop` (`_take`): the cause 'pickup' to the loop's stop rules (stops.py `decide`)."""

    def __init__(self, drop: Drop, why: str) -> None:
        super().__init__(why, cause='pickup')
        self.drop = drop


class Unlabelled(Missed):
    """No click took `drop` and its label was never under the pointer (WAIVE_UNLABELLED): the game draws none for it,
    the loot filter hides it."""


class Unmoved(Missed):
    """CLICKS with `drop` under the pointer left the character standing `away` units off (NEARER_AFTER_STILL): the
    game began no walk to it. `pick_up` goes nearer (`nearer`)."""

    def __init__(self, drop: Drop, away: float) -> None:
        super().__init__(drop, f'{drop.label}: the clicks with it under the pointer moved nobody from {away:.0f} away')
        self.away = away


def gheeds_carried(run: Run) -> bool:
    """Whether an identified Gheed's Fortune is in the carried inventory (anyone's: carry-one counts any)."""
    pack = run.reads.carried()
    return pack is not None and any(
        is_unique_grand_charm(item.txt, item.quality) and item.identified and item.unique == GHEEDS_FORTUNE
        for item in pack.items
    )


def unique_grand_charm(drop: Drop) -> bool:
    """Whether `drop` is a unique Grand Charm (Gheed's or a Sunder, alike until identified), else by its label."""
    return is_unique_grand_charm(drop.txt, drop.quality) or 'Unique Grand Charm' in drop.label


def refusal(run: Run, drop: Drop, after: Player | None) -> Refused | None:
    """The `Refused` a missed click on `drop` was, else None: a unique Grand Charm, the character (`after`) within
    NEAR_UNITS (not a walk cut short), a Gheed's carried, and room for it (a full inventory is the room rules')."""
    if not unique_grand_charm(drop):
        return None
    if after is None or math.dist((after.x, after.y), (drop.x, drop.y)) > NEAR_UNITS:
        return None
    if not gheeds_carried(run):
        return None
    loot = run.reads.loot()
    if loot is None or not has_room(loot.room, drop.size):
        return None
    return Refused(drop, f"{drop.label} was refused by the game: another Gheed's Fortune is carried")


def wanted() -> dict:
    """What counts as valuable: the loot marks' settings, runes from `pickup_rune_minimum`, the `pickup_also` groups,
    and what the loot filter shows (gear up to `pickup_shown_cells`, and its gems: user, 2026-10-12, chipped ones)."""
    materials = material_classes((*APPRAISAL.material_marks, *APPRAISAL.pickup_also))
    if APPRAISAL.pickup_filter_shown:
        materials |= shown_gems(game_filter())
    return {
        'rune_minimum': APPRAISAL.pickup_rune_minimum,
        'unique_minimum': APPRAISAL.unique_minimum if APPRAISAL.unique_marks else None,
        'materials': materials,
        'gold_minimum': APPRAISAL.pickup_gold_minimum,
        'shown': shown_rules() if APPRAISAL.pickup_filter_shown else (),
        # What a full inventory stops the press for: what the marks point at (game/records.py `prized`).
        'prized_rune_minimum': APPRAISAL.rune_minimum,
        'prized_materials': frozenset(material_classes(APPRAISAL.material_marks)),
    }


# The qualities whose filter-shown bases over the cell cap are read (`shown_rules`): the field identify's (loot/api.py
# G15) and the ground read's white bases (loot/ground_judge.py BASES, M5)
OVERSIZE_FIELD = frozenset((RARITIES['magic'], RARITIES['rare']))
OVERSIZE_BASES = frozenset((RARITIES['normal'], RARITIES['hiQuality']))


def shown_rules() -> tuple:
    """The filter's gear rules the look reads: up to `pickup_shown_cells`, and over it the magic and rare items the
    field identify checks (loot/api.py FIELD_OVERSIZE) and the white bases the ground read judges (ground_judge.py
    BASES): the player, 2026-10-20 ~11:55, "bases or blue/rare items might take much place (like spears, matron bow)
    -- we want to check them". Over the cap, pickmode.py `kept` takes only what those judge, in every pickup level."""
    cap = APPRAISAL.pickup_shown_cells
    qualities = (OVERSIZE_FIELD if field_api.FIELD_IDENTIFY and field_api.FIELD_OVERSIZE else frozenset()) | (
        OVERSIZE_BASES if ground_judge.BASES else frozenset()
    )
    path, stamp = profile()  # the game's own copy of the profile (loot/shown.py GAME_COPY): what it labels
    return pickup_rules(cap, path, stamp) + (oversize_rules(cap, qualities, path, stamp) if qualities else ())


def shortages(loot: Loot) -> tuple[int, int]:
    """(rejuvenation, healing) the belt is missing (rca/2026-10-13/potions-findings.md, step 1)."""
    return column_shortages(loot.belt, loot.columns, BELT.layout)


def choose(loot: Loot, here: tuple[float, float]) -> Plan | None:
    """What this press picks up, if anything (the order is the module doc's)."""

    def away(drop: Drop) -> float:
        return math.dist(here, (drop.x, drop.y))

    # A valuable with no room is left: no click takes it, and the press would do nothing else. One picked for the
    # field identify (loot/api.py) comes after every other in sight: a big one never takes a valuable's room
    valuables = [drop for drop in loot.drops if drop.kind == VALUABLE and has_room(loot.room, drop.size)]
    if valuables:
        game = loot.game[0] if loot.game is not None else None
        return Plan(min(valuables, key=lambda drop: (FIELD.class_of(drop.unit_id, game) is not None, away(drop))))
    gold = [drop for drop in loot.drops if drop.kind == GOLD and away(drop) <= GOLD_UNITS]
    if gold:
        return Plan(min(gold, key=away))
    near = sorted((drop for drop in loot.drops if drop.kind in KINDS and away(drop) <= POTION_UNITS), key=away)
    if not near or not loot.belt_read:
        return None  # an unread belt is unknown, not short: no potion from it
    rejuvenation, healing = shortages(loot)
    missing = {REJUVENATION: rejuvenation, HEALING: healing}
    for kind in (REJUVENATION, HEALING):  # the rarer first
        found = next((drop for drop in near if drop.kind == kind and missing[kind]), None)
        if found is not None:
            return Plan(found)
    if not loot.max_life or loot.life >= DRINK_BELOW * loot.max_life:
        return None
    for kind in (HEALING, REJUVENATION):  # the cheaper first
        found = next((drop for drop in near if drop.kind == kind), None)
        column = next((c for c in range(BELT_COLUMNS) if potion_kind(loot.belt[c]) == KINDS[kind]), None)
        if found is not None and column is not None:
            return Plan(found, INPUT.column_keys[column + 1])
    return None


def on_ground(run: Run, drop: Drop) -> bool:
    return run.loot is not None and any(found.unit_id == drop.unit_id for found in run.loot().drops)


class Spot(Protocol):
    """What `approach` goes to: a drop, or a chest (macros/opening.py)."""

    @property
    def x(self) -> float: ...
    @property
    def y(self) -> float: ...
    @property
    def label(self) -> str: ...


def approach(run: Run, drop: Spot, level: Level | None, key_names, hops: int = HOPS) -> None:
    """Bring `drop` within a click: nothing when in view, within PICK_UNITS and on a clear line (`walk_reaches`,
    rca/2026-10-14/run-0025-findings.md §2.2), else up to `hops` teleport hops. With no hop possible, the build's
    own movement instead (`moved_in_hand`, rca/2026-10-13/run-2110-findings.md §2.3)."""
    for hop in range(hops + 1):
        world, rect = ready_world(run)
        player = world.player
        assert player is not None
        aspect = rect[2] / rect[3]
        here = (player.x, player.y)
        away = math.dist(here, (drop.x, drop.y))
        seen = in_view(ground_fraction(player, drop.x, drop.y, aspect))
        ground = Ground(level.ground) if level is not None else None
        if seen and walk_reaches(ground, world.doors, here, (drop.x, drop.y), PICK_UNITS):
            return
        if seen and away <= PICK_UNITS:
            # A click from afar walks only a clear line (run-1214-findings.md §3.2)
            LOG.info(
                'Macro: pickup: %s: %.0f away with no clear line from (%.1f, %.1f): gone to first, not clicked '
                'from afar',
                drop.label, away, *here,
            )  # fmt: skip
        if level is None or hop == hops:
            if seen:
                return  # clicked from afar: the game walks the character
            raise Abort(f'{drop.label} is {away:.0f} away' + ('' if level else ' and there is no level map to hop by'))
        target = Target(
            level.area, level.rooms, (drop.x / TILE_UNITS, drop.y / TILE_UNITS), drop.label, 'loot', False, level.ground
        )
        try:
            hop_toward(run, target, player, rect, key_names)
        except Abort as stop:
            if run.stops(stop):
                raise
            if moved_in_hand(run, drop, level, aspect, key_names, stop):
                continue
            if not seen:
                raise
            LOG.info('Macro: no hop toward %s (%s); clicking it from %.0f away', drop.label, stop, away)
            return


def moved_in_hand(run: Run, drop: Spot, level: Level, aspect: float, key_names, why: Abort) -> bool:
    """One move toward `drop` by the build's movement sets when no hop could be made (`why`); whether made."""
    travel = Travel(run.build.movement)
    world = run.world()
    ground = Ground(level.ground)
    found = travel.toward(run, world, ground, aspect, (drop.x, drop.y), PRESSED, level.rooms)
    if not isinstance(found, Step):
        LOG.info('Macro: no hop toward %s (%s), and no move in hand: %s', drop.label, why, found.reason)
        return False
    by = 'a walk' if found.skill is None else skill_name(found.skill)
    LOG.info('Macro: no hop toward %s (%s); %s to (%.1f, %.1f) in its place', drop.label, why, by, *found.spot)
    travel.make(run, found, world, aspect, key_names, ground, name=drop.label, intent=PRESSED, goal=(drop.x, drop.y))
    return True


def pile_aims(crowd: int) -> tuple[tuple[int, int], ...]:
    """Further aims for a drop among `crowd` others: the column above it as high as the labels stack, then the
    side columns, nearer first."""
    top = -64 - 10 * min(crowd, 12)
    known = {*ITEM_AIMS, *PILE_AIMS, *LOOK_AIMS}
    column = [(0, down) for down in range(-74, top - 1, -10)]
    sides = [(across, down) for across in (-40, 40, -60, 60, -20, 20) for down in range(-14, top - 1, -20)]
    return tuple(aim for aim in (*column, *sides) if aim not in known)[:PILE_MORE]


def take(
    run: Run, drop: Drop, alike: Sequence[Drop] = (), others: Sequence[Drop] = (), *, nearer: bool = False
) -> Drop:
    """Click `drop` or one of `alike` (same kind) until one leaves the ground; the one that did. With the hover
    record (`run.hovered`) aims are looked at first and only one with a wanted item under it is clicked, CLICKS
    times (a click as a cast ends is swallowed); one of `others` under it is never clicked. Without the record,
    or with no aim showing it, the nearer aims are clicked blind. Controller mode: `pad_take`. `nearer`: the caller
    goes nearer when the clicks from afar move nobody (`Unmoved`, NEARER_AFTER_STILL). No click took it: `Missed`."""
    if run.pad is not None:
        return pad_take(run, drop, alike, others)
    serves = {found.unit_id: found for found in (drop, *alike)}
    unwanted = {found.unit_id for found in others}
    # Every aim logged whatever the end (user, 2026-10-11: "log all failed attempts").
    looked: list[str] = []
    try:
        return _take(run, drop, serves, unwanted, looked, alike, others, nearer)
    finally:
        LOG.info(
            'Macro: aims for %s (unit %d) at (%.1f, %.1f), %d wanted and %d other drops: %s',
            drop.label, drop.unit_id, drop.x, drop.y, len(serves), len(unwanted), '; '.join(looked) or 'none',
        )  # fmt: skip


def _take(
    run: Run,
    drop: Drop,
    serves: dict[int, Drop],
    unwanted: set[int],
    looked: list[str],
    alike: Sequence[Drop],
    others: Sequence[Drop],
    nearer: bool = False,
) -> Drop:
    missed = 0
    nothing = other = 0  # aims whose hover record read nothing under the pointer; aims with another unit or unread
    first: tuple[tuple[int, int], ...] = LOOK_AIMS
    here = run.world().player
    far = here is not None and math.dist((here.x, here.y), (drop.x, drop.y)) > NEAR_UNITS
    # From afar: look at the first aims, then walk up and look at every aim, and only then click blind.
    every: tuple[tuple[int, int], ...] = (*first, *(aim for aim in (*ITEM_AIMS, *PILE_AIMS) if aim not in first))
    crowd = sum(math.dist((drop.x, drop.y), (other.x, other.y)) <= PILE_UNITS for other in (*alike, *others))
    crowded = any(math.dist((drop.x, drop.y), (other.x, other.y)) <= LABEL_NEAR for other in others)
    # In a pile the labels' own aims go first, then the drop with its label hidden or the labels swept (macros/pile.py)
    piled = crowd >= PILE_DROPS and (pile.PILE_LABELS_OFF or pile.PILE_SWEEP) and run.hovered is not None
    rest = tuple(aim for aim in every if aim not in first)
    looks = [(first, False), (every, True)] if far else [(first, False), (rest, False)] if piled else [(every, False)]
    if crowd >= PILE_DROPS:
        looks.append((pile_aims(crowd), False))
    stages = [*((aims, walk, False) for aims, walk in looks), (ITEM_AIMS, False, True)]
    if len(LOOKED) > LOOKED_MOST:
        LOOKED.clear()
    before = frozenset(LOOKED.get(drop.unit_id, ()))  # by the tries before: this one's own stages keep their order
    looking = LOOKED.setdefault(drop.unit_id, set())
    for n, (aims, walk, blind) in enumerate(stages if run.hovered is not None else [(ITEM_AIMS, False, True)]):
        if n == 1 and piled:
            found = pile.pile_take(run, drop, serves, crowd, looked, click)
            if found is not None:
                LOOKED.pop(drop.unit_id, None)
                return found
        if walk and walk_up(run, drop, serves, crowded):
            return drop
        order = aims if blind else (*(a for a in aims if a not in before), *(a for a in aims if a in before))
        for aim in order:
            player = standing(run)
            rect = run.actuator.keys.focused_window_rect()
            if player is None or rect is None:
                raise Abort('not in a game')
            aspect = rect[2] / rect[3]
            across, down = ground_fraction(player, drop.x, drop.y, aspect)
            where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
            if not in_view(where):
                continue
            run.actuator.aim(*where, scatter=(2, 2))
            over = None
            if run.hovered is not None:
                run.pace.sleep(HOVER_SECONDS)
                over = run.hovered()
            under = serves.get(over[1]) if over is not None and over[0] == ITEM_UNIT else None
            if run.hovered is not None and under is None:
                if over is None and run.hover_nothing is not None and run.hover_nothing():
                    nothing += 1
                else:
                    other += 1
            what = 'wanted' if under is not None else 'unread or nothing' if over is None else f'{over}'
            note = '' if run.hover_note is None else f' [{run.hover_note()}]'
            looked.append(f'{aim} {"blind " if blind else ""}{what}{note}')
            foreign = over is not None and over[0] == ITEM_UNIT and (over[1] in unwanted or LABEL_GUARD)
            if under is None and (not blind or foreign):
                looking.add(aim)
                continue  # nothing wanted seen, or an unwanted item under the pointer
            if under is None and over is not None and over[0] == MONSTER_UNIT:
                continue  # the click would hit the monster or its corpse
            walked = False
            for _ in range(CLICKS if under is not None else 1):
                looked[-1] += ' clicked'
                if click(run, under or drop, aim, over):
                    LOOKED.pop(drop.unit_id, None)
                    return under or drop
                now = run.world().player
                refused = refusal(run, under, now) if under is not None else None
                if refused is not None:
                    # Carry-one: no other click takes it; the swap does (`Refused`)
                    looked[-1] += ' refused'
                    SHUNNED[refused.drop.unit_id] = run.clock() + SHUN_SECONDS
                    LOG.info("Macro: pickup: %s (unit %d) refused at the first click: a Gheed's Fortune is carried",
                             refused.drop.label, refused.drop.unit_id)  # fmt: skip
                    raise refused
                if now is None or math.dist((player.x, player.y), (now.x, now.y)) > MOVED_UNITS:
                    # The click walked the character: a second click there walks further off.
                    walked = True
                    break
            away = math.dist((player.x, player.y), (drop.x, drop.y))
            if under is not None and not walked and nearer and NEARER_AFTER_STILL and away > NEAR_UNITS:
                # The game began no walk to it: the same clicks from here take nothing (NEARER_AFTER_STILL)
                looked[-1] += ' moved nobody'
                UNMOVED[drop.unit_id] = run.clock() + UNMOVED_SECONDS
                raise Unmoved(drop, away)
            missed += under is not None
            if missed >= MISSED_AIMS:
                SHUNNED[drop.unit_id] = run.clock() + SHUN_SECONDS
                raise Missed(drop, f'{drop.label} was under the pointer at {missed} aims and no click picked it up')
        if not blind and (aims, walk, blind) == stages[-2]:
            LOG.info(
                'Macro: no aim had %s under the pointer, or its clicks took nothing; clicking every aim', drop.label
            )
    SHUNNED[drop.unit_id] = run.clock() + SHUN_MISS
    if WAIVE_UNLABELLED and not missed and not other and nothing >= UNLABELLED_AIMS and run.world().show_items is True:
        raise Unlabelled(drop, f'no click picked up {drop.label}: its label under the pointer at none of {nothing}')
    raise Missed(drop, f'no click picked up {drop.label}')


def late(loot: Loot, now: float) -> None:
    """Log `CLICKED` valuables found carried within LATE_SECONDS as picked up (the watch's tools match the line);
    forget the rest after it. So too a valuable `SEEN` on the ground within LATE_SECONDS and carried now that no
    pickup click took (`taken_by_a_move`)."""
    pending(loot, now)
    for unit, (drop, at) in list(CLICKED.items()):
        if unit in loot.carried and now - at <= LATE_SECONDS:
            LOG.info(
                'Macro: picked up %s %.2fs after the click, late: carried at a later look; at (%.1f, %.1f)',
                drop.label, now - at, drop.x, drop.y,
            )  # fmt: skip
            del CLICKED[unit]
            SEEN.pop(unit, None)
        elif now - at > LATE_SECONDS:
            del CLICKED[unit]
    taken_by_a_move(loot, now)


def pending(loot: Loot, now: float) -> None:
    """PICK_AT_ONCE: the at-once clicks' pickups read in `loot`, read at `now`. Off the ground (or carried): said picked
    up, as `click` says it. Still on the ground AT_ONCE_SECONDS after the click: said, a target again (its shun over),
    a valuable watched as a click's (CLICKED), and the drop's next click waits (AT_ONCE_MISSED)."""
    if not PENDING or loot.game is None:
        return  # none pending, or an unread look: no drop is known off the ground by it
    grounded = {drop.unit_id for drop in loot.drops}
    for unit, (drop, at, aim, away, over) in list(PENDING.items()):
        if now - at > LATE_SECONDS:
            del PENDING[unit]  # no look read it in time (the game left): not said either way
            LOG.info(
                'Macro: pickup: %s clicked %.2fs ago (PICK_AT_ONCE): no look read its pickup', drop.label, now - at
            )
        elif unit not in grounded or unit in loot.carried:
            del PENDING[unit]
            LOG.info(PICKED_LINE, drop.label, now - at, aim, away, over)
            LOG.info('Macro: pickup: %s read picked up at a later look (PICK_AT_ONCE)', drop.label)
            SEEN.pop(unit, None)  # said here, not again by `taken_by_a_move`
        elif now - at >= AT_ONCE_SECONDS:
            del PENDING[unit]
            if SHUNNED.get(unit) == at + AT_ONCE_SECONDS:
                del SHUNNED[unit]  # its own shun only: one set since stays
            if len(AT_ONCE_MISSED) > AT_ONCE_MOST:
                AT_ONCE_MISSED.clear()
            AT_ONCE_MISSED.add(unit)
            if drop.kind == VALUABLE:
                CLICKED[unit] = (drop, at)
            LOG.info(
                'Macro: %s at (%.1f, %.1f) still on the ground %.2fs after the click %s pixels from it (PICK_AT_ONCE): '
                'a target again, its next click waited on',
                drop.label, drop.x, drop.y, now - at, aim,
            )  # fmt: skip


def taken_by_a_move(loot: Loot, now: float) -> None:
    """A valuable read on the ground within LATE_SECONDS and carried now, never clicked by the pickup: a move's click
    on its label took it (Tal Rune at 23:42:53 on 2026-10-19, a level run's walk; no line said it, so the watch called
    it missed). Said as picked up; this read's ground valuables noted (`SEEN`)."""
    for unit, (drop, at) in list(SEEN.items()):
        if unit in loot.carried and unit not in CLICKED and now - at <= LATE_SECONDS:
            LOG.info(
                'Macro: picked up %s %.2fs after it was last read on the ground, by a move\'s click: carried at a '
                'later look; at (%.1f, %.1f)',
                drop.label, now - at, drop.x, drop.y,
            )  # fmt: skip
            del SEEN[unit]
        elif now - at > LATE_SECONDS:
            del SEEN[unit]
    if len(SEEN) > SEEN_MOST:
        SEEN.clear()
    for drop in loot.drops:
        if drop.kind == VALUABLE and drop.unit_id not in loot.carried:
            SEEN[drop.unit_id] = (drop, now)


def lifted(run: Run, drop: Drop) -> bool:
    return not on_ground(run, drop)


def pad_take(run: Run, drop: Drop, alike: Sequence[Drop], others: Sequence[Drop]) -> Drop:
    """`take` in controller mode (`PadActs.pick_up`): stand on the drop or the nearer alike one and press Loot;
    never with one of `others` nearer."""
    assert run.pad is not None
    player = run.world().player
    if player is None:
        raise Abort('not in a game')
    here = (player.x, player.y)
    unwanted = [(found.x, found.y) for found in others]
    for found in sorted((drop, *alike), key=lambda d: math.dist(here, (d.x, d.y)))[:2]:
        gone = partial(lifted, run, found)
        if run.pad.pick_up(found.unit_id, (found.x, found.y), gone, found.label, unwanted):
            run.say(f'{found.label}: picked up')
            return found
    SHUNNED[drop.unit_id] = run.clock() + SHUN_MISS
    raise Missed(drop, f'the pad picked up no {drop.label}')


def collect(run: Run, drop: Drop, key_names, others: Sequence[Drop] = ()) -> bool:
    """Go for a gold pile: the build's staff-sparing jump onto it (`spare_jump`), which may take it; else, or when
    too near, it is clicked like any item (`others`: not wanted). The jump ignores cast delay and walls."""
    player, rect = ready(run)
    world = run.world()
    where = ground_fraction(player, drop.x, drop.y, rect[2] / rect[3])
    away = math.dist((player.x, player.y), (drop.x, drop.y))
    if not in_view(where):
        raise Abort(f'{drop.label} is not in view')
    jump = spare_jump(run.build.movement, world.slots)
    # Not in controller mode: a pad jump lands at its fixed length, not on the pile; `take` walks onto it.
    if away > GOLD_WALK and jump is not None and jump.line and key_names is not None and run.pad is None:
        run.keys.update(key_names(world, (jump.skill,)))
        run.actuator.aim(*where, scatter=(2, 2))
        began = run.clock()
        press_skill(run, jump.skill)
        # Landing on a pile has never taken it yet, so the wait is only for the landing.
        start = (player.x, player.y)
        run.seen(
            lambda w: (
                not on_ground(run, drop) or (w.player is not None and math.dist(start, (w.player.x, w.player.y)) > 2)
            ),
            GOLD_SECONDS,
        )
        gone = not on_ground(run, drop)
        now = run.world().player
        LOG.info(
            'Macro: %s onto %s at (%.1f, %.1f), %.1f from (%.1f, %.1f); the character at %s %.2fs after: %s',
            skill_name(jump.skill), drop.label, drop.x, drop.y, away, player.x, player.y,
            None if now is None else (round(now.x, 1), round(now.y, 1)), run.clock() - began,
            'taken' if gone else 'still on the ground',
        )  # fmt: skip
        if gone:
            run.say(f'{drop.label}: picked up')
            return True
    # Standing where the record puts it does not take it (user, 2026-10-11: "bad coordinates"): click it as an item.
    take(run, drop, others=others)
    return True


def standing(run: Run):
    """The character once it stands and its cast is over (STAND_SECONDS at most): an aim taken while running sends
    the click past the item, and a click under a cast is swallowed."""
    until = run.clock() + STAND_SECONDS
    while True:
        player = run.world().player
        if player is None or player.mode not in RUN_MODES | ACTING or run.clock() >= until:
            return player
        run.pace.sleep(0.02)


def walk_up(run: Run, drop: Drop, serves: dict[int, Drop] | None = None, crowded: bool = False) -> bool:
    """Click the drop's ground to stand beside it; whether that picked it up too. LABEL_GUARD with another drop near
    (`crowded`): never on the label of an item not in `serves` (`clear_ground`)."""
    player = standing(run)
    rect = run.actuator.keys.focused_window_rect()
    if player is None or rect is None:
        raise Abort('not in a game')
    aspect = rect[2] / rect[3]
    where = ground_fraction(player, drop.x, drop.y, aspect)
    if not in_view(where):
        return False
    run.actuator.aim(*where, scatter=(2, 2))
    aim = (0, 0)
    if LABEL_GUARD and crowded and run.hovered is not None:
        found = clear_ground(run, drop, where, aspect, serves or {drop.unit_id: drop})
        if found is None:
            return False
        aim, where = found
    return click(run, drop, aim, run.reads.hovered())


def clear_ground(
    run: Run, drop: Drop, where: tuple[float, float], aspect: float, serves: dict[int, Drop]
) -> tuple[tuple[int, int], tuple[float, float]] | None:
    """The aim and the place the walk up to `drop` clicks, the pointer at `where` (its ground): there with no item
    under it but one in `serves`, else the first of WALK_UP_AIMS so; the pointer left on it. None: every one has
    another item's label under it (the walk not made: the aims go on from here)."""
    assert run.hovered is not None
    tried = []
    for aim in ((0, 0), *WALK_UP_AIMS):
        if aim != (0, 0):
            point = (where[0] + aim[0] * UNIT_PIXELS[0] / 16 / aspect, where[1] + aim[1] * UNIT_PIXELS[1] / 8)
            if not in_view(point):
                continue
            run.actuator.aim(*point, scatter=(1, 1))
        else:
            point = where
        run.pace.sleep(HOVER_SECONDS)
        over = run.hovered()
        if over is None or over[0] != ITEM_UNIT or over[1] in serves:
            if tried:
                LOG.info('Macro: pickup: the walk up to %s: a label %s under its ground; clicked %s pixels below',
                         drop.label, tried[0], aim)  # fmt: skip
            return aim, point
        tried.append(f'{over}')
    LOG.info('Macro: pickup: the walk up to %s: labels under its ground and below it (%s): not walked up to',
             drop.label, ', '.join(tried))  # fmt: skip
    return None


def click(run: Run, drop: Drop, aim: tuple[int, int], over: tuple[int, int] | None) -> bool:
    """One click where the pointer is; whether `drop` left the ground before the walk it made was over."""
    player = run.world().player
    if player is None:
        raise Abort('not in a game')
    away = math.dist((player.x, player.y), (drop.x, drop.y))
    run.actuator.click()
    began = run.clock()
    if at_once(run, drop, player, began, away, over):
        # The next look at once; its pickup read by the looks after (`pending`), the drop out of their choices
        PENDING[drop.unit_id] = (drop, began, aim, away, over)
        SHUNNED[drop.unit_id] = began + AT_ONCE_SECONDS
        return True
    deadline = began + PICK_SECONDS + away / WALK_SPEED
    stood: tuple[tuple[float, float], float] | None = None  # (where the character stands, since when)
    while run.clock() < deadline:
        walker = run.world().player  # a cancel stops here
        if not on_ground(run, drop):
            LOG.info(PICKED_LINE, drop.label, run.clock() - began, aim, away, over)
            SEEN.pop(drop.unit_id, None)  # said here, not again by `taken_by_a_move`
            run.say(f'{drop.label}: picked up')
            return True
        if walker is not None and walker.mode in DEAD:
            raise Dead('the character is dead')
        place = None if walker is None or walker.mode in RUN_MODES else (walker.x, walker.y)
        if place is None or stood is None or stood[0] != place:
            stood = None if place is None else (place, run.clock())
        elif run.clock() - stood[1] >= STOOD_SECONDS:
            break  # the walk the click made is over and the item is still there
        run.pace.sleep(POLL)
    now = run.world().player
    if drop.kind == VALUABLE:
        CLICKED[drop.unit_id] = (drop, began)
    LOG.info(
        'Macro: %s at (%.1f, %.1f) still on the ground after the click %s pixels from it; the character from '
        '(%.1f, %.1f) to %s; under the pointer %s',
        drop.label, drop.x, drop.y, aim, player.x, player.y,
        None if now is None else (round(now.x, 1), round(now.y, 1)), over,
    )  # fmt: skip
    return False


def at_once(run: Run, drop: Drop, player: Player, began: float, away: float, over: tuple[int, int] | None) -> bool:
    """PICK_AT_ONCE: whether the click begun at `began` is left to the later looks' read (`pending`): a drop within
    AT_ONCE_UNITS that the hover record named under the pointer (a blind click waits), not missed at once before
    (AT_ONCE_MISSED), and in AT_ONCE_LOOK the character neither set off (the click walked it: the wait sees the walk
    through; a step onto the drop's spot is the pickup's) nor the drop already off the ground (said by the wait)."""
    proved = over is not None and over[0] == ITEM_UNIT and over[1] == drop.unit_id
    if not PICK_AT_ONCE or not proved or away > AT_ONCE_UNITS or run.loot is None or drop.unit_id in AT_ONCE_MISSED:
        return False
    while run.clock() - began < AT_ONCE_LOOK:
        now = run.world().player
        if not on_ground(run, drop):
            return False
        if now is not None and math.dist((player.x, player.y), (now.x, now.y)) > MOVED_UNITS:
            stepped_off = math.dist((now.x, now.y), (drop.x, drop.y)) > 1.0
        else:
            stepped_off = False
        if now is not None and (now.mode in RUN_MODES or stepped_off):
            return False  # a walk the click began (onto the drop's own spot is the pickup's step)
        run.pace.sleep(AT_ONCE_POLL)
    return True


def worth_a_stop(run: Run) -> Drop | None:
    """What a teleport step picks up before it leaves: a valuable with room within STOP_UNITS, or gold within a
    jump; STOP_TRIES each, so one no click takes cannot hold the step (user, 2026-10-11: "we have missed more
    important unique and moved away")."""
    player = run.world().player
    if run.loot is None or player is None:
        return None
    here = (player.x, player.y)
    plan = choose(unshunned(run.loot(), run.clock()), here)
    if plan is None or plan.drop.kind not in (VALUABLE, GOLD):
        return None
    drop = plan.drop
    if math.dist(here, (drop.x, drop.y)) > STOP_UNITS or STOPPED.get(drop.unit_id, 0) >= STOP_TRIES:
        return None
    if len(STOPPED) > 200:
        STOPPED.clear()
    STOPPED[drop.unit_id] = STOPPED.get(drop.unit_id, 0) + 1
    return drop


def unshunned(loot: Loot, now: float) -> Loot:
    """`loot` without the shunned drops and those given up for its game (`give_up`); logs late pickups first
    (`late`)."""
    late(loot, now)
    for unit in [unit for unit, until in SHUNNED.items() if until <= now]:
        del SHUNNED[unit]
    if loot.game is not None:
        for unit in [unit for unit, game in GIVEN_UP.items() if game != loot.game]:
            del GIVEN_UP[unit]  # another game's
    return replace(
        loot, drops=tuple(drop for drop in loot.drops if drop.unit_id not in SHUNNED and drop.unit_id not in GIVEN_UP)
    )


def give_up(run: Run, drop: Drop, loot: Loot, missed: Missed) -> bool:
    """GIVE_UP_CHEAP: `drop`, which no click took (`missed`), given up for the game when the loop keeps no game for it
    (lootpolicy.py GUARD, as runner.py `valuable_left`: a potion, gold, an identify candidate, what the pickup level
    does not keep); whether it was. A valuable is not: its stop is the loop's rules' (stops.py `decide`)."""
    if isinstance(missed, Unlabelled) and waive(run, drop, loot, missed):
        return True
    if not GIVE_UP_CHEAP:
        return False
    room = has_room(loot.room, drop.size)
    if lootpolicy.verdict(drop, lootpolicy.GUARD, room=room, shown=drop.unit_id in loot.shown, looped=True).hold:
        return False
    GIVEN_UP[drop.unit_id] = loot.game
    # The watch reads it (d2-loop-watch logwords.py GIVEN_UP)
    LOG.info(
        'Macro: pickup: %s at (%.0f, %.0f) given up for this game (%s); the game is kept and the press goes on',
        drop.label, drop.x, drop.y, missed,
    )  # fmt: skip
    run.say(f'{drop.label}: given up')
    return True


def waive(run: Run, drop: Drop, loot: Loot, missed: Unlabelled) -> bool:
    """WAIVE_UNLABELLED: `drop`, whose label was never under the pointer (`missed`), waived at its UNLABELLED_TRIES-th
    such press in the game: given up for it (GIVEN_UP) and out of what the loop guards (WAIVED, runner.py `_picked`);
    whether it was. Before that the stop is the loop's rules', which go back for it once (stops.py FETCH)."""
    if not WAIVE_UNLABELLED or loot.game is None:
        return False
    game, tries = UNLABELLED.get(drop.unit_id, (loot.game, 0))
    tries = tries + 1 if game == loot.game else 1
    if len(UNLABELLED) > LOOKED_MOST:
        UNLABELLED.clear()
    UNLABELLED[drop.unit_id] = (loot.game, tries)
    if tries < UNLABELLED_TRIES:
        LOG.info('Macro: pickup: %s at (%.0f, %.0f) showed no label (%s): unlabelled press %d of %d',
                 drop.label, drop.x, drop.y, missed, tries, UNLABELLED_TRIES)  # fmt: skip
        return False
    for memory in (GIVEN_UP, WAIVED):
        for unit in [unit for unit, seen in memory.items() if seen != loot.game]:
            del memory[unit]  # another game's
    GIVEN_UP[drop.unit_id] = WAIVED[drop.unit_id] = loot.game
    # The watch reads it (d2-loop-watch logwords.py GIVEN_UP)
    LOG.info(
        'Macro: pickup: %s at (%.0f, %.0f) given up for this game (%s; unlabelled press %d: the loot filter hides it);'
        ' the game is kept and the press goes on',
        drop.label, drop.x, drop.y, missed, tries,
    )  # fmt: skip
    run.say(f'{drop.label}: no label, given up')
    return True


def waived(loot: Loot) -> Loot:
    """`loot` without the drops waived in its game (`waive`)."""
    if not WAIVED or loot.game is None:
        return loot
    drops = tuple(drop for drop in loot.drops if WAIVED.get(drop.unit_id, ()) != loot.game)
    return loot if len(drops) == len(loot.drops) else replace(loot, drops=drops)


def nearer(run: Run, drop: Drop, level: Level, key_names) -> bool:
    """`Unmoved`'s remedy (NEARER_AFTER_STILL): up to NEARER_HOPS hops toward `drop` (`hop_toward`), the build's own
    move when no hop can be made (`moved_in_hand`); whether the character stands within NEAR_UNITS of it now."""
    for _ in range(NEARER_HOPS):
        world, rect = ready_world(run)
        player = world.player
        assert player is not None
        if math.dist((player.x, player.y), (drop.x, drop.y)) <= NEAR_UNITS:
            break
        target = Target(
            level.area, level.rooms, (drop.x / TILE_UNITS, drop.y / TILE_UNITS), drop.label, 'loot', False, level.ground
        )
        try:
            hop_toward(run, target, player, rect, key_names)
        except Abort as stop:
            if run.stops(stop) or isinstance(stop, Expired | Hand | Cancelled | Dead):
                raise
            if not moved_in_hand(run, drop, level, rect[2] / rect[3], key_names, stop):
                break
        now = run.world().player
        if now is None or math.dist((player.x, player.y), (now.x, now.y)) < MOVED_UNITS:
            break  # no hop was made (beside it, the landing where it stands): no second one either
    now = run.world().player
    return now is not None and math.dist((now.x, now.y), (drop.x, drop.y)) <= NEAR_UNITS


def _taken(run: Run, drop: Drop, alike: Sequence[Drop], others: Sequence[Drop], level: Level | None, key_names) -> Drop:
    """`take` for `pick_up`, with NEARER_AFTER_STILL's remedy: a drop whose clicks from afar moved nobody (`Unmoved`,
    now or on a try within UNMOVED_SECONDS) is gone nearer to (`nearer`) and taken from there."""
    remedy = NEARER_AFTER_STILL and level is not None and run.pad is None
    player = run.world().player
    far = player is not None and math.dist((player.x, player.y), (drop.x, drop.y)) > NEAR_UNITS
    if remedy and far and UNMOVED.get(drop.unit_id, -math.inf) > run.clock():
        assert level is not None
        # A try before found the clicks from afar moved nobody (a priced act cut it off): nearer first
        LOG.info('Macro: pickup: %s: the clicks from afar moved nobody before: going nearer first', drop.label)
        nearer(run, drop, level, key_names)
        return take(run, drop, alike, others)
    try:
        return take(run, drop, alike, others, nearer=remedy)
    except Unmoved as still:
        assert level is not None
        moved = nearer(run, drop, level, key_names)
        now = run.world().player
        LOG.info(
            'Macro: pickup: %s; %s: clicked from %s', still,
            'gone nearer' if moved else 'no move brought the character within reach',
            'nowhere' if now is None else f'{math.dist((now.x, now.y), (drop.x, drop.y)):.1f} away',
        )  # fmt: skip
        return take(run, drop, alike, others)


def drink(run: Run, key: str, loot: Loot) -> None:
    """Press belt key `key` and see the potion leave the belt."""
    for tap in range(1, DRINK_TAPS + 1):
        run.actuator.tap(key)  # a keyboard key in either mode: it flips nothing
        pressed = run.clock()
        run.pause('key')
        if run.loot is None:
            return
        until = run.clock() + DRINK_SECONDS
        while run.clock() < until:
            run.world()  # a cancel stops here
            looked = run.loot()
            if looked.belt_read and looked.belt != loot.belt:  # a cell left out unread is not a potion drunk
                if run.pad is not None:
                    LOG.info(
                        'Pad drink: belt key %s in controller mode: the belt cell emptied %.0f ms after press %d',
                        key, 1000 * (run.clock() - pressed), tap,
                    )  # fmt: skip
                return
            run.pace.sleep(0.05)
        if run.pad is not None:
            LOG.info('Pad drink: belt key %s in controller mode: the belt unchanged after press %d', key, tap)
    raise Abort(f'the potion on {key} was not drunk: the belt is still full')


# Hostiles too near the character (first point) or the target (second) to spend the press on it (hunt.py `threat`).
Threat = Callable[[tuple[float, float], tuple[float, float]], int]


def pack_guard(run: Run, here: tuple[float, float], spot: tuple[float, float]) -> tuple[int, int]:
    """(the hostiles within GATHER_CLEAR of the character or `spot`, those of them in a tier 4-5 Herald's pack):
    PACK_GOLD_WAIT's guard."""
    from inventory_tracking.combat.pack import in_pack  # late: the hunt's modules build on the pickup
    from inventory_tracking.macros.hunting.base import GATHER_CLEAR, hostiles

    near = [
        m
        for m in hostiles(run.world())
        if min(math.dist((m.x, m.y), here), math.dist((m.x, m.y), spot)) <= GATHER_CLEAR
    ]
    return len(near), sum(1 for m in near if in_pack(m.tier))


def pick_up(
    run: Run,
    level: Level | None,
    key_names,
    otherwise: Callable[[], None],
    threat: Threat | None = None,
    unit: int | None = None,
    looped: bool = False,
    trips: bool = False,
) -> bool:
    """One press of the pickup action; whether there was something to pick up. `otherwise`: the press with
    nothing to pick up. `threat`: a potion with monsters near is left, gold under a pack too (PACK_GOLD_WAIT;
    valuables are not). `unit`: the
    drop a goal names, in place of `choose`'s. `looped`: the KP_6 loop's press, where a valuable with no room stops
    it whenever `lootpolicy.verdict` holds it. `trips`: a press by hand that a trip for room may follow
    (running/room.py): what a trip is made for stops it too (lootpolicy.py `trip_for`)."""
    player, _ = ready(run)
    loot = unshunned(run.loot() if run.loot is not None else Loot(), run.clock())
    here = (player.x, player.y)
    plan = choose(loot, here)
    if unit is not None and (plan is None or plan.drop.unit_id != unit):
        named = next((drop for drop in loot.drops if drop.unit_id == unit), None)
        if named is None:
            LOG.info('Macro: pickup: the drop the goal names (unit %d) is no longer on the ground', unit)
            return False
        plan = Plan(named)
    close = threat(here, (plan.drop.x, plan.drop.y)) if threat and plan and plan.drop.kind in KINDS else 0
    if threat and plan is not None and unit is None and plan.drop.kind == GOLD and PACK_GOLD_WAIT:
        near, packed = pack_guard(run, here, (plan.drop.x, plan.drop.y))
        if packed or near >= GOLD_CROWD:
            # The watch tools may read it (d2-loop-watch logwords.py)
            LOG.info(
                'Macro: pickup: %s waits: %d hostiles near it or the character, %d of a tier 4-5 pack (PACK_GOLD_WAIT)',
                plan.drop.label, near, packed,
            )  # fmt: skip
            run.say(f'{plan.drop.label} waits: the fight first')
            otherwise()
            return False
    if plan is not None and close:
        LOG.info(
            'Macro: pickup: %s at (%.0f, %.0f) left for later: %d hostiles near it or the character',
            plan.drop.label, plan.drop.x, plan.drop.y, close,
        )  # fmt: skip
        run.say(f'{plan.drop.label} left for later: {close} monsters near')
        otherwise()
        return False
    LOG.info(
        'Macro: pickup: %d drops (%s), belt short %s, life %d/%d; %s',
        len(loot.drops), ', '.join(sorted({drop.kind for drop in loot.drops})) or 'none',
        shortages(loot), loot.life, loot.max_life,
        'nothing to pick up' if plan is None else f'{plan.drop.label} at ({plan.drop.x:.0f}, {plan.drop.y:.0f})',
    )  # fmt: skip
    potions = [math.dist(here, (drop.x, drop.y)) for drop in loot.drops if drop.kind in KINDS]
    if plan is None and potions and loot.belt_read and any(shortages(loot)):
        # A short belt and potions on the ground, none taken: how far they lie says why.
        LOG.info(
            'Macro: pickup: the nearest potion is %.0f away, of %d; one is gone for within %.0f',
            min(potions),
            len(potions),
            POTION_UNITS,
        )
    left = [drop for drop in loot.drops if drop.kind == VALUABLE and not has_room(loot.room, drop.size)]
    if left:
        named = ', '.join(sorted({drop.label for drop in left}))
        LOG.info('Macro: pickup: the inventory has no room for %s; left on the ground', named)
        # A sticky warning (user, 2026-10-12: "an active warning that must be visible to the user").
        run.warn(f'Inventory full: {named} left on the ground')
        # "Must not leave it" is `lootpolicy.verdict`'s (rca/2026-10-18/arch-level-behaviour.md step 4). In the loop
        # plain valuables hold too (the player, 2026-10-18: "we should stop and clear inventory with our designated
        # town routine"); the stop is then the room rules' (runner.py `_loop_stopped`).
        facts = {drop.unit_id: {'room': False, 'shown': drop.unit_id in loot.shown, 'looped': looped} for drop in left}
        held = [
            drop
            for drop in left
            if lootpolicy.verdict(drop, lootpolicy.PRESS, **facts[drop.unit_id]).hold
            or (trips and lootpolicy.trip_for(drop, shown=drop.unit_id in loot.shown))
        ]
        dear = ', '.join(sorted({drop.label for drop in held}))
        if plan is None and not dear and looped:
            # lootpolicy.py CANDIDATE_CUBE: an identify candidate gets the loop's cube step once before it is left
            cubed = [drop for drop in left if lootpolicy.ask_cube(drop)]
            if cubed:
                names = ', '.join(sorted({drop.label for drop in cubed}))
                raise Abort(f'inventory full: no room for {names}: the cube step first', cause='room')
        if plan is None and dear:
            # Stop rather than seek away from the drop (user, 2026-10-10). Plain shown gear lets the press go on
            # (user, 2026-10-12: "allow moving when the item isn't very valuable"); shown uniques/sets are prized
            # (run-1214-findings.md §3.1).
            raise Abort(f'inventory full: no room for {dear}', cause='room')
        if plan is not None:
            run.say(f'Inventory full: no room for {named}')
    else:
        run.warn(None)
    if plan is None:
        near = [drop for drop in loot.drops if drop.kind in KINDS and math.dist(here, (drop.x, drop.y)) <= POTION_UNITS]
        if near and loot.belt_read:  # an unread belt was said by the look (game/memory.py `belt_cells`)
            # Said, or potions left with a full belt read as a failed pickup.
            named = ', '.join(sorted({drop.label for drop in near}))
            LOG.info('Macro: pickup: %s near, none the belt has a place for (short %s)', named, shortages(loot))
            run.say(f'Not picked up: the belt has no place for {named}')
        otherwise()
        return False
    if plan.drop.kind == GOLD:
        run.say(f'Going for {plan.drop.label}, {math.dist(here, (plan.drop.x, plan.drop.y)):.0f} away')
        try:
            if collect(run, plan.drop, key_names, [found for found in loot.drops if found is not plan.drop]):
                return True
            why = 'not taken by standing on it'
        except Missed as missed:
            if not give_up(run, plan.drop, loot, missed):
                raise
            return False
        except Abort as stop:
            if 'not in view' not in str(stop):
                raise
            why = 'not in view'
        # Gold never stops the press: shunned, the rest goes on (2026-10-17 18:26:19, a game lost to a pile).
        SHUNNED[plan.drop.unit_id] = run.clock() + SHUN_SECONDS
        LOG.info('Macro: pickup: %s %s: left alone for %.0fs', plan.drop.label, why, SHUN_SECONDS)
        run.say(f'{plan.drop.label}: {why}, left')
        return False
    level = level if level is not None and level.area == player.area else None
    for picked in range(PICKS):
        drop = plan.drop
        if plan.drink is not None:
            run.say(f'Drinking ({plan.drink}) to make room for {drop.label}')
            drink(run, plan.drink, loot)
        run.say(f'Picking up {drop.label}, {math.dist(here, (drop.x, drop.y)):.0f} away')
        approach(run, drop, level, key_names)
        # What serves as well: the same kind, with room for it.
        alike = [
            found
            for found in loot.drops
            if found.kind == drop.kind and found is not drop and has_room(loot.room, found.size)
        ]
        serving = {found.unit_id for found in (drop, *alike)}
        try:
            took = _taken(run, drop, alike, [found for found in loot.drops if found.unit_id not in serving], level,
                          key_names)  # fmt: skip
        except Missed as missed:
            # A potion, gold or a cheap item never ends the press (nor the loop's game): given up for the game
            if not give_up(run, drop, loot, missed):
                raise
            return picked > 0
        if plan.drink is not None or run.loot is None:
            break  # one drink a press
        # More potions the belt wants, or the rest of a pile of valuables, in the same press.
        player, _ = ready(run)
        loot, here = unshunned(run.loot(), run.clock()), (player.x, player.y)
        again = choose(loot, here)
        if again is None or again.drop.kind == GOLD or again.drink is not None:
            break
        if VALUABLE in (took.kind, again.drop.kind) and (
            again.drop.kind != took.kind or math.dist(here, (again.drop.x, again.drop.y)) > PILE_UNITS
        ):
            break  # the next valuable is a walk away, or what is left is of another kind: the next press
        plan = again
    return True
