"""The pickup step: one thing that is not fighting (user, 2026-10-10), the first that applies:

1. A valuable item on the ground is picked up: every rune, and what the loot marks point at
   (materials with the keys and essences, bases of expensive uniques; loot/ground.py), the nearest first.
2. A super healing or full rejuvenation potion (never a smaller or plain one) near the character is
   picked up when the belt is missing one of its kind (tracking/belt.py `column_shortages`: a column
   holds what its lowest potion is, an empty one rejuvenation).
3. With the belt full, life missing and such a potion near: one of the same kind is drunk from the
   belt's hotkey row and the one on the ground picked up in its place.
4. Nothing of those: the press is a seek step (hunt.Hunter.seek: toward the next elite, attack mode on).

In a pile the game stacks the labels: the item under the pointer is read from the game before a
click (`take`), another potion of the kind wanted serves as well, and one not wanted is never clicked.
One press takes every potion the belt is short of (PICKS at most), one valuable, or one drink.

A drop within PICK_UNITS and in view is clicked and the character walks to it; one further off is
hopped toward first (teleport.hop_toward, with the level's rooms and walls). Potions are only taken
from POTION_UNITS around the character: nobody walks half a map for one. The click goes to the
item, a little above the ground it lies on, then round that (ITEM_AIMS); the item leaving the ground
is the proof, and each try logs where it aimed. During attack mode the press waits for the fight:
the runner starts this once nothing is left in reach (runner.py, hunt.Hunter.after_fight).

On the host (2026-10-10): the drops, their positions and the life read right, and a click on the
item itself picks it up with Show Items on. UNCONFIRMED: the belt cell of a belt item (its path x,
as tracking/state.py reads it; the belt was full on every press so far), and what the hover record
holds with nothing under the pointer.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from inventory_tracking.combat.policy import RUN_MODES
from inventory_tracking.common import LOG
from inventory_tracking.config import APPRAISAL, INPUT
from inventory_tracking.levels.model import Level, Target
from inventory_tracking.loot.materials import material_classes
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import UNIT_PIXELS
from inventory_tracking.macros.teleport import HOVER_SECONDS, ground_fraction, hop_toward, in_view, ready
from inventory_tracking.macros.world import HEALING, REJUVENATION, VALUABLE, Drop, Loot, has_room
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS, TILE_UNITS
from inventory_tracking.tracking.belt import column_shortages, potion_kind


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
ITEM_AIMS = ((0, -14), (0, -24), (0, -6), (-10, -14), (10, -14), (0, -34), (0, 2))
# Further aims only looked at, never clicked blind: in a pile the game stacks the labels, and the item
# wanted is under the pointer well above its ground or to a side. A press clicked whatever lay at the
# first aims and took a potion nobody wanted (host, 21:10 on 2026-10-10: a full rejuvenation with the
# belt full of them, between two healing potions).
PILE_AIMS = ((0, -44), (-20, -24), (20, -24), (0, -54), (-20, -44), (20, -44), (0, -64), (-30, -14), (30, -14))
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
STOOD_SECONDS = 0.4  # the character standing this long after a click with the item still there: a miss
POLL = 0.05
ITEM_UNIT = 4
KINDS = {HEALING: PotionType.HEALING, REJUVENATION: PotionType.REJUVENATION}


@dataclass(frozen=True)
class Plan:
    drop: Drop
    drink: str | None = None  # the belt key to press first


def wanted() -> dict:
    """What counts as valuable: the loot marks' own settings (config.AppraisalConfig), and every rune
    from `pickup_rune_minimum` (all of them: the marks point only at the dearer ones) and the groups
    of `pickup_also` (every ring and jewel), which the marks do not point at."""
    return {
        'rune_minimum': APPRAISAL.pickup_rune_minimum,
        'unique_minimum': APPRAISAL.unique_minimum if APPRAISAL.unique_marks else None,
        'materials': material_classes((*APPRAISAL.material_marks, *APPRAISAL.pickup_also)),
    }


def choose(loot: Loot, here: tuple[float, float]) -> Plan | None:
    """What this press picks up, if anything (the module text has the order)."""

    def away(drop: Drop) -> float:
        return math.dist(here, (drop.x, drop.y))

    # A valuable the inventory has no room for is left on the ground: no click takes it, and a press
    # spent on it does nothing else (an Ort Rune and a Large Charm, 2026-10-10 night: full inventory).
    valuables = [drop for drop in loot.drops if drop.kind == VALUABLE and has_room(loot.room, drop.size)]
    if valuables:
        return Plan(min(valuables, key=away))
    near = sorted((drop for drop in loot.drops if drop.kind != VALUABLE and away(drop) <= POTION_UNITS), key=away)
    if not near:
        return None
    rejuvenation, healing = column_shortages(loot.belt)
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


def approach(run: Run, drop: Drop, level: Level | None, key_names) -> None:
    """Bring `drop` within a click: nothing when it is near and in view, teleport hops otherwise."""
    for hop in range(HOPS + 1):
        player, rect = ready(run)
        aspect = rect[2] / rect[3]
        away = math.dist((player.x, player.y), (drop.x, drop.y))
        seen = in_view(ground_fraction(player, drop.x, drop.y, aspect))
        if seen and away <= PICK_UNITS:
            return
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
            if run.cancelled.is_set() or not seen:
                raise
            LOG.info('Macro: no hop toward %s (%s); clicking it from %.0f away', drop.label, stop, away)
            return


def take(run: Run, drop: Drop, alike: Sequence[Drop] = (), others: Sequence[Drop] = ()) -> Drop:
    """Click `drop`, or one of `alike` (drops that serve as well: the same kind), until one leaves the
    ground; the one that did. With the game's record of the unit under the pointer (`run.hovered`)
    the aims are first only looked at, and one that has such an item under it is clicked, CLICKS times
    if need be (a click made while a cast ends is swallowed: the character neither walks nor picks
    up). An aim with one of `others` under it (the rest of what lies there) is never clicked: that item
    is not wanted. Without the record, or when no aim shows the item, the nearer aims are clicked in turn."""
    serves = {found.unit_id: found for found in (drop, *alike)}
    unwanted = {found.unit_id for found in others}
    missed = 0
    # A potion is taken by the click 24 pixels above its ground more often than by the first aim: in
    # the logs from 21:00 on 2026-10-10, 14 of 16 potions went at (0, -24) and 1 at (0, -14), where 10
    # clicks had the potion under the pointer and only walked the character to it. Valuables are the
    # other way round (12 at -14, 3 at -24), so they keep the order.
    first = ITEM_AIMS if drop.kind == VALUABLE else (ITEM_AIMS[1], ITEM_AIMS[0], *ITEM_AIMS[2:])
    here = run.world().player
    far = here is not None and math.dist((here.x, here.y), (drop.x, drop.y)) > NEAR_UNITS
    # From afar the item is looked for at the nearer aims only; when none shows it the character walks
    # up to it and every aim is looked at again, and only then are aims clicked without the item seen
    # under them. Tower Cellar 4, 23:11 on 2026-10-10: a Grand Charm 16 away showed at none of 16 aims
    # (2.4 s), the first click made anyway had a corpse under it, and from 2 away the next aim took it.
    looks = [(first, False), ((*first, *PILE_AIMS), True)] if far else [((*first, *PILE_AIMS), False)]
    stages = [*((aims, walk, False) for aims, walk in looks), (first, False, True)]
    for aims, walk, blind in stages if run.hovered is not None else [(first, False, True)]:
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
            if under is None and (not blind or (over is not None and over[0] == ITEM_UNIT and over[1] in unwanted)):
                continue  # nothing wanted there to see, or an item not wanted lies under the pointer
            for _ in range(CLICKS if under is not None else 1):
                if click(run, under or drop, aim, over):
                    return under or drop
            missed += under is not None
            if missed >= MISSED_AIMS:
                SHUNNED[drop.unit_id] = run.clock() + SHUN_SECONDS
                raise Abort(f'{drop.label} was under the pointer at {missed} aims and no click picked it up')
        if not blind and (aims, walk, blind) == stages[-2]:
            LOG.info(
                'Macro: no aim had %s under the pointer, or its clicks took nothing; clicking every aim', drop.label
            )
    raise Abort(f'no click picked up {drop.label}')


def standing(run: Run):
    """The character once it stands (STAND_SECONDS at most): an aim taken while it runs is off by
    the way it goes before the click, and the click walks it past the item. Black Marsh, 01:13 on
    2026-10-11: a shard 14 away took 6 s, the character sent 18 units past it and back; a ring was
    passed twice. Both pickups began under a walk of attack mode's."""
    until = run.clock() + STAND_SECONDS
    while True:
        player = run.world().player
        if player is None or player.mode not in RUN_MODES or run.clock() >= until:
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


def unshunned(loot: Loot, now: float) -> Loot:
    """`loot` without the drops a press gave up on less than SHUN_SECONDS ago."""
    for unit in [unit for unit, until in SHUNNED.items() if until <= now]:
        del SHUNNED[unit]
    return replace(loot, drops=tuple(drop for drop in loot.drops if drop.unit_id not in SHUNNED))


def drink(run: Run, key: str, loot: Loot) -> None:
    """The belt key `key`, and the belt seen with the potion gone from it."""
    for _ in range(DRINK_TAPS):
        run.actuator.tap(key)
        run.pause('key')
        if run.loot is None:
            return
        until = run.clock() + DRINK_SECONDS
        while run.clock() < until:
            run.world()  # a cancel stops here
            if run.loot().belt != loot.belt:
                return
            run.pace.sleep(0.05)
    raise Abort(f'the potion on {key} was not drunk: the belt is still full')


def pick_up(run: Run, level: Level | None, key_names, otherwise: Callable[[], None]) -> bool:
    """One press of the pickup action; whether there was something to pick up. `level` is the level
    map if known, `otherwise` what the press does with nothing to pick up (the runner: the seek step)."""
    player, _ = ready(run)
    loot = unshunned(run.loot() if run.loot is not None else Loot(), run.clock())
    here = (player.x, player.y)
    plan = choose(loot, here)
    LOG.info(
        'Macro: pickup: %d drops (%s), belt short %s, life %d/%d; %s',
        len(loot.drops), ', '.join(sorted({drop.kind for drop in loot.drops})) or 'none',
        column_shortages(loot.belt), loot.life, loot.max_life,
        'nothing to pick up' if plan is None else f'{plan.drop.label} at ({plan.drop.x:.0f}, {plan.drop.y:.0f})',
    )  # fmt: skip
    left = [drop for drop in loot.drops if drop.kind == VALUABLE and not has_room(loot.room, drop.size)]
    if left:
        named = ', '.join(sorted({drop.label for drop in left}))
        LOG.info('Macro: pickup: the inventory has no room for %s; left on the ground', named)
        if plan is None:
            # The press stops here and says so: going on to the seek step would teleport away from
            # the drop (user, 2026-10-10 night).
            raise Abort(f'inventory full: no room for {named}')
        run.say(f'Inventory full: no room for {named}')
    if plan is None:
        otherwise()
        return False
    level = level if level is not None and level.area == player.area else None
    for _ in range(PICKS):
        drop = plan.drop
        if plan.drink is not None:
            run.say(f'Drinking ({plan.drink}) to make room for {drop.label}')
            drink(run, plan.drink, loot)
        run.say(f'Picking up {drop.label}, {math.dist(here, (drop.x, drop.y)):.0f} away')
        approach(run, drop, level, key_names)
        alike = [found for found in loot.drops if found.kind == drop.kind and found is not drop]
        took = take(run, drop, alike, [found for found in loot.drops if found.kind != drop.kind])
        if took.kind == VALUABLE or plan.drink is not None or run.loot is None:
            break  # one valuable a press (the next may be a walk away); one drink a press
        # The belt may want more of what lies here: two potions drunk are two picked up in one press.
        player, _ = ready(run)
        loot, here = unshunned(run.loot(), run.clock()), (player.x, player.y)
        again = choose(loot, here)
        if again is None or again.drop.kind == VALUABLE or again.drink is not None:
            break
        plan = again
    return True
