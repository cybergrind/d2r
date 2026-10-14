"""The pickup step: one thing that is not fighting (user, 2026-10-10), the first that applies:

1. A valuable item on the ground is picked up: every rune, and what the loot marks point at
   (materials with the keys and essences, bases of expensive uniques; loot/ground.py), and the equipment
   the loot filter shows: unique and set items, and the smaller rare, magic and white ones, with what a
   Warlock uses among them (loot/shown.py), the nearest first.
   Then a gold pile of `pickup_gold_minimum` or more within one jump: a Blade Warp onto it, and a
   click on it if that did not take it.
2. A super healing or full rejuvenation potion (never a smaller or plain one) near the character is
   picked up when the belt is missing one of its kind (tracking/belt.py `column_shortages`: a column
   holds what its lowest potion is, an empty one what it last held this game (`Loot.columns`), or what
   config.BELT's layout says when one is set, else rejuvenation).
3. With the belt full, life missing and such a potion near: one of the same kind is drunk from the
   belt's hotkey row and the one on the ground picked up in its place.
4. Nothing of those: the press is hunt.Hunter.step: with hostiles near it starts the sweep (attack mode
   then moves on its own), else it is a seek step toward any hostile or the next room of the tour.

In a pile the game stacks the labels: the item under the pointer is read from the game before a
click (`take`), another potion of the kind wanted serves as well, and one not wanted is never clicked.
One press takes every potion the belt is short of (PICKS at most), the valuables lying within
PILE_UNITS of one another (as many), or one drink.

A drop within PICK_UNITS and in view is clicked and the character walks to it; one further off is
hopped toward first (teleport.hop_toward, with the level's rooms and walls). Potions are only taken
from POTION_UNITS around the character: nobody walks half a map for one. The click goes to the
item, a little above the ground it lies on, then round that (ITEM_AIMS); the item leaving the ground
is the proof, and each try logs where it aimed. During attack mode a press with something to pick
up stops the fight for it at once (hunt.Hunter.asked_step; since 2026-10-11 for gold and potions as
for valuables); with nothing to pick up it asks the fight for a better stand.

On the host (2026-10-10): the drops, their positions and the life read right, and a click on the
item itself picks it up with Show Items on. UNCONFIRMED: the belt cell of a belt item (its path x,
as tracking/state.py reads it; the belt was full on every press so far), and what the hover record
holds with nothing under the pointer.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from functools import partial
from typing import Protocol

from inventory_tracking.combat.policy import RUN_MODES
from inventory_tracking.common import LOG
from inventory_tracking.config import APPRAISAL, BELT, INPUT
from inventory_tracking.levels.model import Ground, Level, Target
from inventory_tracking.loot.materials import material_classes
from inventory_tracking.loot.shown import game_filter, pickup_rules, shown_gems
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import ACTING, DEAD, UNIT_PIXELS, press_skill
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.teleport import HOVER_SECONDS, ground_fraction, hop_toward, in_view, ready, ready_world
from inventory_tracking.macros.travel import JUMP_REACH, PRESSED, Travel, spare_jump, walk_reaches
from inventory_tracking.macros.world import GOLD, HEALING, REJUVENATION, VALUABLE, Drop, Loot, has_room
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS, TILE_UNITS
from inventory_tracking.tracking.belt import column_shortages, potion_kind


# Gold is taken by standing on it, so it is gone to and never clicked (user, 2026-10-11: "blade warp to
# location would be enough"): a Blade Warp onto the pile, and a click on it when the pile is too near
# for one or the jump did not take it. Only a pile within one jump is worth it.
GOLD_UNITS = JUMP_REACH  # one jump's reach, whatever the jump
GOLD_WALK = 6.0  # world units: a pile this near is walked onto
GOLD_SECONDS = 0.9  # for the pile to leave the ground after the key (a Blade Warp of 23 units lands in 0.81 s)
POTION_UNITS = 25.0  # world units: a potion further off is not worth the walk
PICK_UNITS = 20.0  # a drop this near, in view, is clicked (the character walks); further, hopped toward
HOPS = 4  # teleports toward one drop per press at most
# The belt is looked at after the drink's key: Frigid Highlands, 03:00:04 on 2026-10-11, the key went
# out 0.3 s after a teleport, the belt stayed full, and six clicks on two potions picked nothing up
# (6.4 s, "under the pointer at 3 aims and no click picked it up"); the next press, the belt one
# short by then, took the potion in 0.44 s. The key is pressed once more, then the press stops.
DRINK_SECONDS = 0.6
DRINK_TAPS = 2
DRINK_BELOW = 0.7  # of the life: under it a potion is drunk to make room for the one on the ground
# Where a drop is clicked, in classic pixels (600 high; across, down) from the ground it lies on, tried
# in turn. The first host presses (18:41 on 2026-10-10, a Large Charm) clicked at 0, -10 and +10 down:
# the character walked to spots 9 to 21 pixels below the item each time and picked nothing up, so a
# click lands about 14 pixels lower than `ground_fraction` says and the item was never under it. The
# aims start that much higher and go round it. With them four of four items were picked up (18:46 to
# 18:54): three at the first aim, one at the second after a click the game took nothing from.
# The aim 24 pixels up comes first: in every log up to 2026-10-11 the first click with the item under
# the pointer took it 101 times of 111 there and 87 of 130 at 14 pixels up (none of 21 at 6): the click
# lands lower than the pointer shows the label, so an aim on the label's lower edge walks the character
# to the ground behind it (an Eth Rune in the Tower, 16:53:14: two such clicks ran 17 units past it).
ITEM_AIMS = ((0, -24), (0, -14), (0, -6), (-10, -14), (10, -14), (0, -34), (0, 2))
# Where the label is looked for first, from afar too. Of the 71 pickups from 17:20 to 19:11 on
# 2026-10-11 that ended on a label seen (the hover flag set), 62 had it 24 pixels up, 5 at 54, 2 at
# 34, 1 at 14 and 1 at (-10, -14): in a pile the next label sits 30 pixels higher. With 54 the ninth
# aim after a walk up to the item, a Tir Rune took 3.8 s and Rare Chain Gloves 4.6 s (19:10 that day).
# The whole column above the item, every 10 pixels, is looked at before any walk: a Sol Rune among
# three potions and another rune (Tower Cellar 5, 19:38:29 on 2026-10-11) had a potion's label at 24
# and 34 and its own at 44, which was the fifteenth aim, after a walk past it: 3.4 s and five more
# presses of the player's.
LOOK_AIMS = ((0, -24), (0, -54), (0, -34), (0, -44), (0, -14), (0, -64), (0, -74), (0, -84))
MOVED_UNITS = 1.0  # the character this far from where an aim was taken: the pointer is on other ground by now
# Further aims only looked at, never clicked blind: in a pile the game stacks the labels, and the item
# wanted is under the pointer well above its ground or to a side. A press clicked whatever lay at the
# first aims and took a potion nobody wanted (host, 21:10 on 2026-10-10: a full rejuvenation with the
# belt full of them, between two healing potions).
PILE_AIMS = ((0, -44), (-20, -24), (20, -24), (0, -54), (-20, -44), (20, -44), (0, -64), (-30, -14), (30, -14))
# In a pile of many drops the label of one is pushed further still: a Flawless Diamond among 12 drops
# showed at none of the 16 aims, four presses running (Arcane Sanctuary, 16:03:45 to 16:04:06 on
# 2026-10-11; the clicks made unseen had a monster under them), and the player took it by hand. With
# PILE_DROPS or more drops within PILE_UNITS of the one wanted, the looks go on up the column above it
# and to both sides (`pile_aims`), never clicked unseen.
PILE_DROPS = 3
PILE_UNITS = 10.0
PILE_MORE = 30  # further aims looked at for one drop at most (0.06 s each)
# A drop no click took is left alone this long, so that the next press takes the rest of the pile
# first (four presses went to that diamond while gold and a rune lay beside it).
SHUN_MISS = 8.0
STAND_SECONDS = 1.5  # for the character to come to a stand before an aim is taken
NEAR_UNITS = 6.0  # world units: a drop further off is walked up to before every aim is tried
PICKS = 4  # potions one press picks up at most, while the belt is still short and one lies near
PICK_SECONDS = 1.5  # for the item to leave the ground after the click, plus the walk at WALK_SPEED
WALK_SPEED = 6.0  # world units a second, on the slow side
CLICKS = 2  # clicks on an aim that has the item under it
# Aims with the item under the pointer whose clicks took nothing before the item is given up, and how
# long a later press leaves it alone. Worldstone Keep 3, 22:16 on 2026-10-10: a Large Charm was under
# the pointer at 16 aims, 30 clicks in 21 s picked nothing up (the player took it by hand 4 s later;
# the cause is not known: no take was recorded there), and all the while nothing else was done.
MISSED_AIMS = 3
SHUN_SECONDS = 30.0
SHUNNED: dict[int, float] = {}  # unit id -> the clock until which the pickup step leaves the drop alone
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


def wanted() -> dict:
    """What counts as valuable: the loot marks' own settings (config.AppraisalConfig), and every rune
    from `pickup_rune_minimum` (all of them: the marks point only at the dearer ones) and the groups
    of `pickup_also` (every ring and jewel), which the marks do not point at, and the equipment the
    loot filter shows: unique and set items of any size, the rest up to `pickup_shown_cells` (loot/shown.py),
    and the gems the game's copy of the filter shows (user, 2026-10-12: chipped ones, enabled in the game)."""
    materials = material_classes((*APPRAISAL.material_marks, *APPRAISAL.pickup_also))
    if APPRAISAL.pickup_filter_shown:
        materials |= shown_gems(game_filter())
    return {
        'rune_minimum': APPRAISAL.pickup_rune_minimum,
        'unique_minimum': APPRAISAL.unique_minimum if APPRAISAL.unique_marks else None,
        'materials': materials,
        'gold_minimum': APPRAISAL.pickup_gold_minimum,
        'shown': pickup_rules(APPRAISAL.pickup_shown_cells) if APPRAISAL.pickup_filter_shown else (),
        # What a full inventory stops the press for: what the marks point at (world.py `prized`).
        'prized_rune_minimum': APPRAISAL.rune_minimum,
        'prized_materials': frozenset(material_classes(APPRAISAL.material_marks)),
    }


def shortages(loot: Loot) -> tuple[int, int]:
    """(rejuvenation, healing) the belt is missing: its columns by what they hold, an empty one by the
    configured layout, else by what it last held (rca/2026-10-13/potions-findings.md, step 1)."""
    return column_shortages(loot.belt, loot.columns, BELT.layout)


def choose(loot: Loot, here: tuple[float, float]) -> Plan | None:
    """What this press picks up, if anything (the module text has the order)."""

    def away(drop: Drop) -> float:
        return math.dist(here, (drop.x, drop.y))

    # A valuable the inventory has no room for is left on the ground: no click takes it, and a press
    # spent on it does nothing else (an Ort Rune and a Large Charm, 2026-10-10 night: full inventory).
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


def approach(run: Run, drop: Spot, level: Level | None, key_names) -> None:
    """Bring `drop` within a click: nothing when it is in view, within PICK_UNITS and on a clear line (travel.py
    `walk_reaches`: a drop 17 away across lava is 43 by walking, rca/2026-10-14/run-0025-findings.md §2.2; one
    18 away round a wall corner was never walked to, run-1214-findings.md §3.2), teleport hops otherwise. Where no
    hop can be made (the staff empty, no Teleport), a move by the movement in hand (`moved_in_hand`: the build's own
    sets, a Blade Warp or a walk) in its place:
    rca/2026-10-13/run-2110-findings.md §2.3, an Amn Rune 24 away left twice with "the Teleport staff has no
    charges left"."""
    for hop in range(HOPS + 1):
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
            # A click from afar walks only a clear line (travel.py `walk_reaches`, run-1214-findings.md §3.2)
            LOG.info(
                'Macro: pickup: %s: %.0f away with no clear line from (%.1f, %.1f): gone to first, not clicked '
                'from afar',
                drop.label, away, *here,
            )  # fmt: skip
        if level is None or hop == HOPS:
            if seen:
                return  # clicked from afar: the game walks the character
            raise Abort(f'{drop.label} is {away:.0f} away' + ('' if level else ' and there is no level map to hop by'))
        target = Target(
            level.area, level.rooms, (drop.x / TILE_UNITS, drop.y / TILE_UNITS), drop.label, 'loot', False, level.ground
        )
        try:
            hop_toward(run, target, player, rect, key_names)
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            if moved_in_hand(run, drop, level, aspect, key_names, stop):
                continue
            if not seen:
                raise
            LOG.info('Macro: no hop toward %s (%s); clicking it from %.0f away', drop.label, stop, away)
            return


def moved_in_hand(run: Run, drop: Spot, level: Level, aspect: float, key_names, why: Abort) -> bool:
    """One move toward `drop` by the build's own movement sets (macros/travel.py `Travel.toward`, as a pressed
    goal), when no hop could be made (`why`); whether one was made."""
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
    """Aims beyond ITEM_AIMS and PILE_AIMS for a drop among `crowd` others: the column above it as high
    as that many labels stack, then columns to both sides, the nearer first."""
    top = -64 - 10 * min(crowd, 12)
    known = {*ITEM_AIMS, *PILE_AIMS, *LOOK_AIMS}
    column = [(0, down) for down in range(-74, top - 1, -10)]
    sides = [(across, down) for across in (-40, 40, -60, 60, -20, 20) for down in range(-14, top - 1, -20)]
    return tuple(aim for aim in (*column, *sides) if aim not in known)[:PILE_MORE]


def take(run: Run, drop: Drop, alike: Sequence[Drop] = (), others: Sequence[Drop] = ()) -> Drop:
    """Click `drop`, or one of `alike` (drops that serve as well: the same kind), until one leaves the
    ground; the one that did. With the game's record of the unit under the pointer (`run.hovered`)
    the aims are first only looked at, and one that has such an item under it is clicked, CLICKS times
    if need be (a click made while a cast ends is swallowed: the character neither walks nor picks
    up). An aim with one of `others` under it (the rest of what lies there) is never clicked: that item
    is not wanted. Without the record, or when no aim shows the item, the nearer aims are clicked in turn.
    In controller mode: `pad_take`."""
    if run.pad is not None:
        return pad_take(run, drop, alike, others)
    serves = {found.unit_id: found for found in (drop, *alike)}
    unwanted = {found.unit_id for found in others}
    # Every aim of this take and what the record held there, logged whatever the end (user,
    # 2026-10-11: "log all failed attempts"): the aims only looked at left no trace before.
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
    # From afar the item is looked for at the nearer aims only; when none shows it the character walks
    # up to it and every aim is looked at again, and only then are aims clicked without the item seen
    # under them. Tower Cellar 4, 23:11 on 2026-10-10: a Grand Charm 16 away showed at none of 16 aims
    # (2.4 s), the first click made anyway had a corpse under it, and from 2 away the next aim took it.
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
                continue  # nothing wanted there to see, or an item not wanted lies under the pointer
            if under is None and over is not None and over[0] == MONSTER_UNIT:
                continue  # a click there is on the monster (or its corpse), not on the drop
            for _ in range(CLICKS if under is not None else 1):
                looked[-1] += ' clicked'
                if click(run, under or drop, aim, over):
                    return under or drop
                now = run.world().player
                if now is None or math.dist((player.x, player.y), (now.x, now.y)) > MOVED_UNITS:
                    # The click walked the character: the pointer is no longer where the aim was
                    # taken, and a second click there walks further off (8 units, that Eth Rune).
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


def lifted(run: Run, drop: Drop) -> bool:
    return not on_ground(run, drop)


def pad_take(run: Run, drop: Drop, alike: Sequence[Drop], others: Sequence[Drop]) -> Drop:
    """`take` in controller mode (macros/pad.py `PadActs.pick_up`): the character stands on the drop, or on the
    nearer of the drops that serve as well, and the Loot record is pressed (the client's Loot takes the nearest
    item); never with one of `others` nearer. A gold pile is taken by standing on it."""
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
    """Go for a gold pile: a Blade Warp onto it, which may take it; if not, or for a pile too near
    to jump to, it is clicked like any item (`others`: what else lies there and is not wanted).
    The jump is the own one of the build the run plays that spares the staff and is thrown over a clear
    line (travel.py `spare_jump`), if it has one on a key; a build without one clicks.
    It is pressed as it always was: with no look at its casting delay or at a wall in its line."""
    player, rect = ready(run)
    world = run.world()
    where = ground_fraction(player, drop.x, drop.y, rect[2] / rect[3])
    away = math.dist((player.x, player.y), (drop.x, drop.y))
    if not in_view(where):
        raise Abort(f'{drop.label} is not in view')
    jump = spare_jump(run.build.movement, world.slots)
    # Not in controller mode: a jump there lands at its one length, not on the pile (macros/pad.py); the
    # pile is walked onto instead (`take`).
    if away > GOLD_WALK and jump is not None and jump.line and key_names is not None and run.pad is None:
        run.keys.update(key_names(world, (jump.skill,)))
        run.actuator.aim(*where, scatter=(2, 2))
        began = run.clock()
        press_skill(run, jump.skill)
        # Landing on a pile has not taken one yet (7210 at 13:30:30 and 5283 at 13:43:43 on 2026-10-11,
        # both with the character 0.7 from it; the click after took the second in 0.07 s), so the
        # wait is only for the landing.
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
    # Standing where the record puts the pile did not take it (Halls of Vaught, 13:30:30 on 2026-10-11:
    # the jump landed 0.7 from a pile of 7210 and a click on that ground walked 1.2 more, the pile
    # still there; user: "bad coordinates"). So the pile is then clicked like any item, where the
    # game says it is under the pointer (`take`), and the log has the aim that took it.
    take(run, drop, others=others)
    return True


def standing(run: Run):
    """The character once it stands (STAND_SECONDS at most): an aim taken while it runs is off by
    the way it goes before the click, and the click walks it past the item. Black Marsh, 01:13 on
    2026-10-11: a shard 14 away took 6 s, the character sent 18 units past it and back; a ring was
    passed twice. Both pickups began under a walk of attack mode's. And once its cast is over: a click
    made under a cast is swallowed, and the miss is only seen STOOD_SECONDS later (three of the sweep's
    own pickups on 2026-10-11, 14:51 to 14:54, a Ring and two potions: the first click on each took
    nothing with the item under the pointer and the character not moving, 0.65 s each)."""
    until = run.clock() + STAND_SECONDS
    while True:
        player = run.world().player
        if player is None or player.mode not in RUN_MODES | ACTING or run.clock() >= until:
            return player
        run.pace.sleep(0.02)


def walk_up(run: Run, drop: Drop) -> bool:
    """A click on the ground the drop lies on, for the character to stand beside it; whether the
    click picked it up as well."""
    player = standing(run)
    rect = run.actuator.keys.focused_window_rect()
    if player is None or rect is None:
        raise Abort('not in a game')
    where = ground_fraction(player, drop.x, drop.y, rect[2] / rect[3])
    if not in_view(where):
        return False
    run.actuator.aim(*where, scatter=(2, 2))
    return click(run, drop, (0, 0), run.hovered() if run.hovered is not None else None)


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
            return True
        if walker is not None and walker.mode in DEAD:
            # Tower Cellar 5, 22:51:00 on 2026-10-11: the clicks went on 4.7 s over the body.
            raise Abort('the character is dead')
        place = None if walker is None or walker.mode in RUN_MODES else (walker.x, walker.y)
        if place is None or stood is None or stood[0] != place:
            stood = None if place is None else (place, run.clock())
        elif run.clock() - stood[1] >= STOOD_SECONDS:
            break  # the walk the click made is over and the item is still there
        run.pace.sleep(POLL)
    now = run.world().player
    LOG.info(
        'Macro: %s at (%.1f, %.1f) still on the ground after the click %s pixels from it; the character from '
        '(%.1f, %.1f) to %s; under the pointer %s',
        drop.label, drop.x, drop.y, aim, player.x, player.y,
        None if now is None else (round(now.x, 1), round(now.y, 1)), over,
    )  # fmt: skip
    return False


def worth_a_stop(run: Run) -> Drop | None:
    """What a teleport step picks up before it leaves: a valuable the inventory has room for within
    STOP_UNITS, or a gold pile within a jump; each STOP_TRIES times at most, so that one no click
    takes cannot hold the step. Tower Cellar, 17:35:18 on 2026-10-11: the sweep had stopped for a
    Ring 29 away, a teleport step cancelled that pickup 30 ms later, the next landed 6.5 from the
    Ring and two more left the level (user: "we have missed more important unique and moved away")."""
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
    """`loot` without the drops a press gave up on less than SHUN_SECONDS ago."""
    for unit in [unit for unit, until in SHUNNED.items() if until <= now]:
        del SHUNNED[unit]
    return replace(loot, drops=tuple(drop for drop in loot.drops if drop.unit_id not in SHUNNED))


def drink(run: Run, key: str, loot: Loot) -> None:
    """The belt key `key`, and the belt seen with the potion gone from it."""
    for tap in range(1, DRINK_TAPS + 1):
        run.actuator.tap(key)  # a keyboard key in either mode: it flips nothing (macros/pad.py)
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


# How many hostiles stand too near the character (first point) or a thing to go to (second) for the
# press to be spent on it (hunt.py `threat`: the sweep's own measure, GATHER_CLEAR).
Threat = Callable[[tuple[float, float], tuple[float, float]], int]


def pick_up(
    run: Run,
    level: Level | None,
    key_names,
    otherwise: Callable[[], None],
    threat: Threat | None = None,
    unit: int | None = None,
) -> bool:
    """One press of the pickup action; whether there was something to pick up. `level` is the level
    map if known, `otherwise` what the press does with nothing to pick up (the runner: the seek step).
    With `threat` a potion is left where monsters are near it or the character, and the press goes on
    to `otherwise`; a valuable or gold is gone for all the same. `unit`: the drop a goal names (the pursuit's
    act, priced for it: hunt.py `operate`), taken in place of the one `choose` would put first; gone from the
    ground (taken meanwhile), the press has nothing to pick up."""
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
        # A belt short of potions and potions on the ground, none taken (Chaos Sanctuary, 00:10:21 on
        # 2026-10-13: short 8 and 5, three healing potions, "nothing to pick up"): how far they lie says why.
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
        # Shown until a press finds nothing left for want of room: a line that the next thing said
        # would wipe was read as a key that does nothing (user, 2026-10-12: "an active warning that
        # must be visible to the user").
        run.warn(f'Inventory full: {named} left on the ground')
        dear = ', '.join(sorted({drop.label for drop in left if drop.prized}))
        if plan is None and dear:
            # The press stops here and says so: going on to the seek step would teleport away from
            # the drop (user, 2026-10-10 night). Only for what the marks point at (world.py `prized`):
            # for gear the filter shows the press goes on (user, 2026-10-12: "allow moving when the item
            # isn't very valuable"; Drifter Cavern, 20:00 that day: 37 presses in a row stopped for a
            # Superior Old Book, 13 hostiles 38 away). A unique or set item the filter shows is prized (the
            # player, 2026-10-14: the Unique Plate Mail fetched by hand, run-1214-findings.md §3.1).
            raise Abort(f'inventory full: no room for {dear}')
        if plan is not None:
            run.say(f'Inventory full: no room for {named}')
    else:
        run.warn(None)
    if plan is None:
        near = [drop for drop in loot.drops if drop.kind in KINDS and math.dist(here, (drop.x, drop.y)) <= POTION_UNITS]
        if near:
            # Three super healing potions with the belt's healing columns full and the life whole
            # read to the player as a pickup that failed (13:47:09 on 2026-10-11): said, then.
            named = ', '.join(sorted({drop.label for drop in near}))
            LOG.info('Macro: pickup: %s near, none the belt has a place for (short %s)', named, shortages(loot))
            run.say(f'Not picked up: the belt has no place for {named}')
        otherwise()
        return False
    if plan.drop.kind == GOLD:
        run.say(f'Going for {plan.drop.label}, {math.dist(here, (plan.drop.x, plan.drop.y)):.0f} away')
        if not collect(run, plan.drop, key_names, [found for found in loot.drops if found is not plan.drop]):
            raise Abort(f'{plan.drop.label} was not taken by standing on it')
        return True
    level = level if level is not None and level.area == player.area else None
    for _ in range(PICKS):
        drop = plan.drop
        if plan.drink is not None:
            run.say(f'Drinking ({plan.drink}) to make room for {drop.label}')
            drink(run, plan.drink, loot)
        run.say(f'Picking up {drop.label}, {math.dist(here, (drop.x, drop.y)):.0f} away')
        approach(run, drop, level, key_names)
        # What serves as well: the same kind, with room for it. A Rare Horned Helm the inventory had no
        # room for lay beside an Ith Rune (Tower Cellar 5, 19:03:28 on 2026-10-11): it was under the
        # pointer at two aims and clicked four times, 3.5 s, before the rune's own label was found.
        alike = [
            found
            for found in loot.drops
            if found.kind == drop.kind and found is not drop and has_room(loot.room, found.size)
        ]
        serving = {found.unit_id for found in (drop, *alike)}
        took = take(run, drop, alike, [found for found in loot.drops if found.unit_id not in serving])
        if plan.drink is not None or run.loot is None:
            break  # one drink a press
        # The belt may want more of what lies here: two potions drunk are two picked up in one press.
        # And a pile of valuables is one press: the Tower, 16:53 and 16:55 on 2026-10-11, two runes
        # and then three within 5 units took a press each, with attack mode back on in between.
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
