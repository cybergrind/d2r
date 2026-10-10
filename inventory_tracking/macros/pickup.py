"""The pickup step: one thing that is not fighting (user, 2026-10-10), the first that applies:

1. A valuable item on the ground is picked up: what the loot marks point at (runes from the
   configured minimum, materials, bases of expensive uniques; loot/ground.py), the nearest first.
2. A healing or full rejuvenation potion (never a plain one) near the character is picked up when the belt is
   missing one of its kind (tracking/belt.py `column_shortages`: a column holds what its lowest
   potion is, an empty one rejuvenation).
3. With the belt full, life missing and such a potion near: one of the same kind is drunk from the
   belt's hotkey row and the one on the ground picked up in its place.
4. Nothing of those: the press is a seek step (hunt.Hunter.seek: toward the next elite, attack mode on).

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
from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.combat.policy import RUN_MODES
from inventory_tracking.common import LOG
from inventory_tracking.config import APPRAISAL, INPUT
from inventory_tracking.levels.model import Level, Target
from inventory_tracking.loot.materials import material_classes
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import UNIT_PIXELS
from inventory_tracking.macros.teleport import ground_fraction, hop_toward, in_view, ready
from inventory_tracking.macros.world import HEALING, REJUVENATION, VALUABLE, Drop, Loot
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS, TILE_UNITS
from inventory_tracking.tracking.belt import column_shortages, potion_kind


POTION_UNITS = 25.0  # world units: a potion further off is not worth the walk
PICK_UNITS = 20.0  # a drop this near, in view, is clicked (the character walks); further, hopped toward
HOPS = 4  # teleports toward one drop per press at most
DRINK_BELOW = 0.7  # of the life: under it a potion is drunk to make room for the one on the ground
# Where a drop is clicked, in classic pixels (600 high; across, down) from the ground it lies on, tried
# in turn. The first host presses (18:41 on 2026-10-10, a Large Charm) clicked at 0, -10 and +10 down:
# the character walked to spots 9 to 21 pixels below the item each time and picked nothing up, so a
# click lands about 14 pixels lower than `ground_fraction` says and the item was never under it. The
# aims start that much higher and go round it. With them four of four items were picked up (18:46 to
# 18:54): three at the first aim, one at the second after a click the game took nothing from.
ITEM_AIMS = ((0, -14), (0, -24), (0, -6), (-10, -14), (10, -14), (0, -34), (0, 2))
PICK_SECONDS = 1.5  # for the item to leave the ground after the click, plus the walk at WALK_SPEED
WALK_SPEED = 6.0  # world units a second, on the slow side
HOVER_SECONDS = 0.06  # for the game to note what is under the pointer after it moved (a frame or two)
CLICKS = 2  # clicks on an aim that has the item under it
STOOD_SECONDS = 0.4  # the character standing this long after a click with the item still there: a miss
POLL = 0.05
ITEM_UNIT = 4
KINDS = {HEALING: PotionType.HEALING, REJUVENATION: PotionType.REJUVENATION}


@dataclass(frozen=True)
class Plan:
    drop: Drop
    drink: str | None = None  # the belt key to press first


def wanted() -> dict:
    """What counts as valuable: the loot marks' own settings (config.AppraisalConfig)."""
    return {
        'rune_minimum': APPRAISAL.rune_minimum,
        'unique_minimum': APPRAISAL.unique_minimum if APPRAISAL.unique_marks else None,
        'materials': material_classes(APPRAISAL.material_marks),
    }


def choose(loot: Loot, here: tuple[float, float]) -> Plan | None:
    """What this press picks up, if anything (the module text has the order)."""

    def away(drop: Drop) -> float:
        return math.dist(here, (drop.x, drop.y))

    valuables = [drop for drop in loot.drops if drop.kind == VALUABLE]
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


def take(run: Run, drop: Drop) -> None:
    """Click `drop` until it leaves the ground. With the game's record of the unit under the pointer
    (`run.hovered`) the aims are first only looked at, and the one that has the item under it is
    clicked, CLICKS times if need be (a click made while a cast ends is swallowed: the character
    neither walks nor picks up). Without the record, or when no aim shows the item, every aim is
    clicked in turn."""
    for blind in (False, True) if run.hovered is not None else (True,):
        for aim in ITEM_AIMS:
            player = run.world().player
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
            on_item = over == (ITEM_UNIT, drop.unit_id)
            if not blind and not on_item:
                continue
            for _ in range(CLICKS if on_item else 1):
                if click(run, drop, aim, over):
                    return
        if not blind:
            LOG.info(
                'Macro: no aim had %s under the pointer, or its clicks took nothing; clicking every aim', drop.label
            )
    raise Abort(f'no click picked up {drop.label}')


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


def pick_up(run: Run, level: Level | None, key_names, otherwise: Callable[[], None]) -> bool:
    """One press of the pickup action; whether there was something to pick up. `level` is the level
    map if known, `otherwise` what the press does with nothing to pick up (the runner: the seek step)."""
    player, _ = ready(run)
    loot = run.loot() if run.loot is not None else Loot()
    here = (player.x, player.y)
    plan = choose(loot, here)
    LOG.info(
        'Macro: pickup: %d drops (%s), belt short %s, life %d/%d; %s',
        len(loot.drops), ', '.join(sorted({drop.kind for drop in loot.drops})) or 'none',
        column_shortages(loot.belt), loot.life, loot.max_life,
        'nothing to pick up' if plan is None else f'{plan.drop.label} at ({plan.drop.x:.0f}, {plan.drop.y:.0f})',
    )  # fmt: skip
    if plan is None:
        otherwise()
        return False
    drop = plan.drop
    if plan.drink is not None:
        run.say(f'Drinking ({plan.drink}) to make room for {drop.label}')
        run.actuator.tap(plan.drink)
        run.pause('key')
    run.say(f'Picking up {drop.label}, {math.dist(here, (drop.x, drop.y)):.0f} away')
    approach(run, drop, level if level is not None and level.area == player.area else None, key_names)
    take(run, drop)
    return True
