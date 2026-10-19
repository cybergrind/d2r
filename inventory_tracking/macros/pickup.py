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
from inventory_tracking.game.records import GOLD, HEALING, REJUVENATION, VALUABLE, Drop, Loot, Player, has_room
from inventory_tracking.levels.model import Ground, Level, Target
from inventory_tracking.loot.materials import material_classes
from inventory_tracking.loot.shown import game_filter, pickup_rules, shown_gems
from inventory_tracking.macros import lootpolicy
from inventory_tracking.macros.actuator import Abort
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
# Valuables the macro picked up itself (unit ids survive into the inventory): outside the KP_6 loop, the ones a full
# inventory may move into the cube (hunting/choice.py `stay_by`); the player's never are.
TAKEN: set[int] = set()
# Valuables clicked and not seen to leave the ground in the wait: unit id -> (drop, clock of the click); found
# carried later, picked up late (`late`).
CLICKED: dict[int, tuple[Drop, float]] = {}
LATE_SECONDS = 5.0  # after its click, a valuable found carried counts as picked up by it
STOP_UNITS = 40.0  # world units: a valuable this near holds a teleport step back (`worth_a_stop`)
STOP_TRIES = 2
STOPPED: dict[int, int] = {}  # unit id -> the teleport steps that went for the drop instead of hopping
STOOD_SECONDS = 0.4  # the character standing this long after a click with the item still there: a miss
POLL = 0.05
ITEM_UNIT = 4
MONSTER_UNIT = 1  # in the record of the unit under the pointer
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
        'shown': pickup_rules(APPRAISAL.pickup_shown_cells) if APPRAISAL.pickup_filter_shown else (),
        # What a full inventory stops the press for: what the marks point at (game/records.py `prized`).
        'prized_rune_minimum': APPRAISAL.rune_minimum,
        'prized_materials': frozenset(material_classes(APPRAISAL.material_marks)),
    }


def shortages(loot: Loot) -> tuple[int, int]:
    """(rejuvenation, healing) the belt is missing (rca/2026-10-13/potions-findings.md, step 1)."""
    return column_shortages(loot.belt, loot.columns, BELT.layout)


def choose(loot: Loot, here: tuple[float, float]) -> Plan | None:
    """What this press picks up, if anything (the order is the module doc's)."""

    def away(drop: Drop) -> float:
        return math.dist(here, (drop.x, drop.y))

    # A valuable with no room is left: no click takes it, and the press would do nothing else.
    valuables = [drop for drop in loot.drops if drop.kind == VALUABLE and has_room(loot.room, drop.size)]
    if valuables:
        return Plan(min(valuables, key=away))
    gold = [drop for drop in loot.drops if drop.kind == GOLD and away(drop) <= GOLD_UNITS]
    if gold:
        return Plan(min(gold, key=away))
    near = sorted((drop for drop in loot.drops if drop.kind in KINDS and away(drop) <= POTION_UNITS), key=away)
    if not near:
        return None
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


def take(run: Run, drop: Drop, alike: Sequence[Drop] = (), others: Sequence[Drop] = ()) -> Drop:
    """Click `drop` or one of `alike` (same kind) until one leaves the ground; the one that did. With the hover
    record (`run.hovered`) aims are looked at first and only one with a wanted item under it is clicked, CLICKS
    times (a click as a cast ends is swallowed); one of `others` under it is never clicked. Without the record,
    or with no aim showing it, the nearer aims are clicked blind. Controller mode: `pad_take`."""
    if run.pad is not None:
        return pad_take(run, drop, alike, others)
    serves = {found.unit_id: found for found in (drop, *alike)}
    unwanted = {found.unit_id for found in others}
    # Every aim logged whatever the end (user, 2026-10-11: "log all failed attempts").
    looked: list[str] = []
    try:
        return _take(run, drop, serves, unwanted, looked, alike, others)
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
) -> Drop:
    missed = 0
    first: tuple[tuple[int, int], ...] = LOOK_AIMS
    here = run.world().player
    far = here is not None and math.dist((here.x, here.y), (drop.x, drop.y)) > NEAR_UNITS
    # From afar: look at the first aims, then walk up and look at every aim, and only then click blind.
    every: tuple[tuple[int, int], ...] = (*first, *(aim for aim in (*ITEM_AIMS, *PILE_AIMS) if aim not in first))
    looks = [(first, False), (every, True)] if far else [(every, False)]
    crowd = sum(math.dist((drop.x, drop.y), (other.x, other.y)) <= PILE_UNITS for other in (*alike, *others))
    if crowd >= PILE_DROPS:
        looks.append((pile_aims(crowd), False))
    stages = [*((aims, walk, False) for aims, walk in looks), (ITEM_AIMS, False, True)]
    for aims, walk, blind in stages if run.hovered is not None else [(ITEM_AIMS, False, True)]:
        if walk and walk_up(run, drop):
            return drop
        for aim in aims:
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
            what = 'wanted' if under is not None else 'unread or nothing' if over is None else f'{over}'
            note = '' if run.hover_note is None else f' [{run.hover_note()}]'
            looked.append(f'{aim} {"blind " if blind else ""}{what}{note}')
            if under is None and (not blind or (over is not None and over[0] == ITEM_UNIT and over[1] in unwanted)):
                continue  # nothing wanted seen, or an unwanted item under the pointer
            if under is None and over is not None and over[0] == MONSTER_UNIT:
                continue  # the click would hit the monster or its corpse
            for _ in range(CLICKS if under is not None else 1):
                looked[-1] += ' clicked'
                if click(run, under or drop, aim, over):
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
                    break
            missed += under is not None
            if missed >= MISSED_AIMS:
                SHUNNED[drop.unit_id] = run.clock() + SHUN_SECONDS
                raise Abort(f'{drop.label} was under the pointer at {missed} aims and no click picked it up')
        if not blind and (aims, walk, blind) == stages[-2]:
            LOG.info(
                'Macro: no aim had %s under the pointer, or its clicks took nothing; clicking every aim', drop.label
            )
    SHUNNED[drop.unit_id] = run.clock() + SHUN_MISS
    raise Abort(f'no click picked up {drop.label}')


def late(loot: Loot, now: float) -> None:
    """Log `CLICKED` valuables found carried within LATE_SECONDS as picked up (the watch's tools match the line);
    forget the rest after it."""
    for unit, (drop, at) in list(CLICKED.items()):
        if unit in loot.carried and now - at <= LATE_SECONDS:
            LOG.info(
                'Macro: picked up %s %.2fs after the click, late: carried at a later look; at (%.1f, %.1f)',
                drop.label, now - at, drop.x, drop.y,
            )  # fmt: skip
            TAKEN.add(unit)
            del CLICKED[unit]
        elif now - at > LATE_SECONDS:
            del CLICKED[unit]


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
    raise Abort(f'the pad picked up no {drop.label}')


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
            if drop.kind == VALUABLE:
                TAKEN.add(drop.unit_id)
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


def walk_up(run: Run, drop: Drop) -> bool:
    """Click the drop's ground to stand beside it; whether that picked it up too."""
    player = standing(run)
    rect = run.actuator.keys.focused_window_rect()
    if player is None or rect is None:
        raise Abort('not in a game')
    where = ground_fraction(player, drop.x, drop.y, rect[2] / rect[3])
    if not in_view(where):
        return False
    run.actuator.aim(*where, scatter=(2, 2))
    return click(run, drop, (0, 0), run.reads.hovered())


def click(run: Run, drop: Drop, aim: tuple[int, int], over: tuple[int, int] | None) -> bool:
    """One click where the pointer is; whether `drop` left the ground before the walk it made was over."""
    player = run.world().player
    if player is None:
        raise Abort('not in a game')
    away = math.dist((player.x, player.y), (drop.x, drop.y))
    run.actuator.click()
    began = run.clock()
    deadline = began + PICK_SECONDS + away / WALK_SPEED
    stood: tuple[tuple[float, float], float] | None = None  # (where the character stands, since when)
    while run.clock() < deadline:
        walker = run.world().player  # a cancel stops here
        if not on_ground(run, drop):
            LOG.info(
                'Macro: picked up %s %.2fs after the click %s pixels from its ground, from %.1f away; under the '
                'pointer %s',
                drop.label, run.clock() - began, aim, away, over,
            )  # fmt: skip
            run.say(f'{drop.label}: picked up')
            if drop.kind == VALUABLE:
                TAKEN.add(drop.unit_id)
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
    """`loot` without the shunned drops; logs late pickups first (`late`)."""
    late(loot, now)
    for unit in [unit for unit, until in SHUNNED.items() if until <= now]:
        del SHUNNED[unit]
    return replace(loot, drops=tuple(drop for drop in loot.drops if drop.unit_id not in SHUNNED))


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
            if run.loot().belt != loot.belt:
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


def pick_up(
    run: Run,
    level: Level | None,
    key_names,
    otherwise: Callable[[], None],
    threat: Threat | None = None,
    unit: int | None = None,
    looped: bool = False,
) -> bool:
    """One press of the pickup action; whether there was something to pick up. `otherwise`: the press with
    nothing to pick up. `threat`: a potion with monsters near is left (valuables and gold are not). `unit`: the
    drop a goal names, in place of `choose`'s. `looped`: the KP_6 loop's press, where a valuable with no room stops
    it whenever `lootpolicy.verdict` holds it."""
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
    if plan is None and potions and any(shortages(loot)):
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
        held = [drop for drop in left if lootpolicy.verdict(drop, lootpolicy.PRESS, **facts[drop.unit_id]).hold]
        dear = ', '.join(sorted({drop.label for drop in held}))
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
        if near:
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
    for _ in range(PICKS):
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
        took = take(run, drop, alike, [found for found in loot.drops if found.unit_id not in serving])
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
