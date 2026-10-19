"""The level run's goal: side drops, potions, the stand-by, chests, clearing the way, the agenda's targets,
passing and taking back. A part of macros/hunt.py `Hunter`, its methods bound there."""

import math
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from inventory_tracking.automation.priority import reserve
from inventory_tracking.common import LOG
from inventory_tracking.config import HEAL_PRIORITY
from inventory_tracking.levels.model import SUPER_CHEST, UNIQUE_CHEST, Ground, Room, Target
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros import lootpolicy, route, supply
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import (
    COVER,
    FULL_CLEAR,
    KILL,
    ON_THE_WAY,
    OPEN,
    PICKUP as SIDE,
    Leader,
    LevelView,
    Objective,
)
from inventory_tracking.macros.build import Intent
from inventory_tracking.macros.drinking import on_belt
from inventory_tracking.macros.drop_ledger import GATHER_TRIES
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import (
    CLEAR_WAY,
    PICK_NEAR,
    PICK_REACH,
    PICK_UP,
    USE_NEAR,
    WAIT,
    Goal,
    clear_way,
    first_fight,
    goal_of,
    in_the_way,
    nearer,
    rest_of_level,
)
from inventory_tracking.macros.hunting.base import (
    ALONE_BOSS_UNITS,
    BLOCK_SECONDS,
    CLEAR_SECONDS,
    DECIDE_SECONDS,
    FAR_JUDGED,
    GATHER_CLEAR,
    JUDGE_GAP,
    LOOP_PICK_SECONDS,
    OMEN_NEAR,
    OPEN_NEAR,
    PASS_SECONDS,
    PROGRESS_LOOK,
    PROGRESS_SECONDS,
    QUIET_UNITS,
    REMEMBERED_NEAR,
    REST_SECONDS,
    SHACK_TRIES,
    SUPER_NEAR,
    SUPER_TRIES,
    TAKE_BACK,
    VANISH_UNITS,
    WAYS,
    Judging,
    door_entry,
    hostiles,
    omen_stand,
    passing_key,
    threat,
)
from inventory_tracking.macros.movement import HOPS
from inventory_tracking.macros.pickup import (
    POTION_UNITS,
    Refused,
    choose,
    gheeds_carried,
    shortages,
    unique_grand_charm,
    unshunned,
    worth_a_stop,
)
from inventory_tracking.macros.pursuit import Pursuit
from inventory_tracking.macros.runmode import AGENDA, DOUBLE, Mode, aim_of, doubles, mode_of, said
from inventory_tracking.macros.shacks import shack_thing
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.supply import detour, low, worth
from inventory_tracking.macros.travel import PRESSED, STANDING, Point, clear_line, label, open_reaches, walked_length
from inventory_tracking.macros.world import HEALING, REJUVENATION, VALUABLE, Drop, Loot, Monster, Thing, World, has_room
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import FIGHT, USE


if TYPE_CHECKING:
    from inventory_tracking.macros.hunt import Hunter


def side_drop(
    self: Hunter,
    run: Run,
    here: Point,
    foes: Sequence[Monster] = (),
    world: World | None = None,
    *,
    restocking: bool = False,
) -> Drop | None:
    """What a level run takes on its way (the pickup key's own rules, macros/pickup.py `choose`): a
    valuable within PICK_NEAR, gold within a jump, a potion the belt wants; not a drop gone for
    GATHER_TRIES times already. A valuable not on the way is no side goal and hides nothing nearer. A wanted
    potion with hostiles near it or the character is taken all the same, as a goal whose guards are the fight
    first (`goal`, goals.py `in_the_way`): the pickup itself never begins among them, and a potion they hold
    BLOCK_SECONDS is left. With none of those: in the quiet, a potion within RESTOCK_UNITS walked that a belt
    low on potions restocks (`restock`); then, the belt's healing potions below the reserve, a healing potion
    further off that is worth its detour (`scarce`). `restocking`: attack mode's own look with no level run,
    which takes only the restock. Every potion left is said once (macros/supply.py `Potions.refuse`)."""
    if run.loot is None:
        return None
    now = run.clock()
    loot = unshunned(run.loot(), now)
    self.again(run, loot.drops, here, world)
    # What the run has given up on is out of the choice, said once each: the next drop is chosen in its place
    given_up = {unit: self.drops.given_up(unit) for unit in self.drops.gathered if self.drops.spent(unit)}
    given_up |= {
        unit: f'left: guarded {BLOCK_SECONDS:.0f} s'
        for unit, since in self.guarded_since.items()
        if now - since > BLOCK_SECONDS
    }
    for found in loot.drops:
        if found.unit_id in given_up:
            self.refused_potion(found, here, given_up[found.unit_id])
            self.left(found, here, given_up[found.unit_id], 'the level run')
            if self.given_up_charm(run, found, given_up[found.unit_id]):
                return None  # the run ends for the Gheed's swap
    loot = replace(loot, drops=tuple(found for found in loot.drops if found.unit_id not in given_up))
    if restocking:
        return self.restock(run, loot, here, foes, world)
    if self.buffs.quiet_by_the_boss and any(self.boss(m) and math.dist(here, (m.x, m.y)) <= self.reach for m in foes):
        # No side goal but a potion while the run's boss is in reach (macros/buffs.py QUIET_BY_THE_BOSS, F3 of
        # rca/2026-10-18/andariel-cadence-findings.md §5): her death first, then her drops land (loop.py DROPS_LAND)
        # and the ground is looked at again. A Dol Rune 32 away took 5.7 s of Andariel's fight at 11:49:03.
        loot = replace(loot, drops=tuple(found for found in loot.drops if found.kind in (HEALING, REJUVENATION)))
    plan = choose(loot, here)
    drop = plan.drop if plan is not None else None
    looped = self.pursuit is not None and self.pursuit.looped
    while drop is not None and drop.kind == VALUABLE and not self.on_the_way(run, here, drop, world, looped=looped):
        # Out of the choice, and nothing nearer hidden by it: at 22:56:06 on 2026-10-14 a Flawless Sapphire 43
        # away hid a super healing potion 8 away with the belt 6 short (run-1932-findings.md issue 2)
        loot = replace(loot, drops=tuple(found for found in loot.drops if found.unit_id != drop.unit_id))
        plan = choose(loot, here)
        drop = plan.drop if plan is not None else None
    if drop is not None and drop.kind == VALUABLE and looped and not self.walked_near(run, here, drop, world):
        # The loop's far valuable (beyond PICK_NEAR walked) hides no potion the belt wants nearer: that one first
        supplies = choose(replace(loot, drops=tuple(found for found in loot.drops if found.kind != VALUABLE)), here)
        potion = supplies.drop if supplies is not None else None
        nearer = potion is not None and math.dist(here, (potion.x, potion.y)) < math.dist(here, (drop.x, drop.y))
        if potion is not None and potion.kind in (HEALING, REJUVENATION) and nearer:
            drop = potion
    if drop is not None and drop.kind in (HEALING, REJUVENATION):
        guards = threat(run)(here, (drop.x, drop.y))
        if not guards:
            self.guarded_since.pop(drop.unit_id, None)
            return drop
        if len(self.guarded_since) > 200:
            self.guarded_since.clear()
        self.guarded_since.setdefault(drop.unit_id, now)
        if self.potions.refuse(drop.unit_id, 'guarded: its guards are the fight first'):
            LOG.info(
                'Macro: pursuit: %s at (%.0f, %.0f), %.0f away: %d hostiles within %.0f of it or the '
                'character are the fight first',
                drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), guards, GATHER_CLEAR,
            )  # fmt: skip
        return drop
    if drop is not None:
        return drop
    return self.restock(run, loot, here, foes, world) or self.scarce(run, loot, here, world)


def restock(
    self: Hunter, run: Run, loot: Loot, here: Point, foes: Sequence[Monster], world: World | None
) -> Drop | None:
    """A potion that a belt low on potions takes before the goal, in the quiet (the player, 2026-10-14): no hostile
    within QUIET_UNITS, healing potions under half their columns or rejuvenations under the reserve, the potion
    within RESTOCK_UNITS walked (macros/supply.py `low`, `restock`). At 22:55:31.8 on 2026-10-14 the belt held 2
    healing potions of 8 with nothing within 30, a full rejuvenation lay 7 away and super healing potions 13 and
    16, and the run warped on toward Snapchip 84 away (run-1932-findings.md issue 2). Said once a potion."""
    if any(math.dist(here, (m.x, m.y)) <= QUIET_UNITS for m in foes) or not low(loot):
        return None
    world = world if world is not None else run.world()
    level = self.known_level(world.player) if world.player is not None else None
    found = supply.restock(loot, here, Ground(level.ground) if level is not None else None, world.doors)
    if found is not None and found.unit_id not in self.restock_said:
        if len(self.restock_said) > 200:
            self.restock_said.clear()
        self.restock_said.add(found.unit_id)
        belt = on_belt(loot)
        LOG.info(
            'Macro: pursuit: restock: %s at (%.0f, %.0f), %.0f away, before the goal: the belt is low (healing '
            '%d, rejuvenations %d), no hostile within %.0f',
            found.label, found.x, found.y, math.dist(here, (found.x, found.y)), belt[PotionType.HEALING],
            belt[PotionType.REJUVENATION], QUIET_UNITS,
        )  # fmt: skip
    return found


def given_up_charm(self: Hunter, run: Run, drop: Drop, why: str) -> bool:
    """The backstop of the Gheed's swap (macros/pickup.py `Refused`): a unique Grand Charm the level run gives up
    on with a Gheed's Fortune carried is the carry-one refusal, whatever its tries came to (13:56:41 on 2026-10-18:
    both ended as "priced act expired", no click was refused, and only the 45 s stand reached the swap at
    13:57:26). Asked once a drop (`swap_asked`); whether the swap starts and the run ended for it."""
    if self.carry_one is None or drop.kind != VALUABLE or drop.unit_id in self.drops.swap_asked:
        return False
    if not unique_grand_charm(drop) or not gheeds_carried(run):
        return False
    self.drops.first(self.drops.swap_asked, drop.unit_id)
    refused = Refused(drop, f"{drop.label} {why}, a Gheed's Fortune carried")
    return self.carry_one_swap(run, refused)


def carry_one_swap(self: Hunter, run: Run, refused: Refused) -> bool:
    """Whether the runner starts the Gheed's swap for `refused` (`carry_one`); the level run ends for it then, so
    the loop's swap leg follows at once (runner.py `_run_over`)."""
    if self.carry_one is None or not self.carry_one(refused):
        return False
    self.end_run(run, f"{refused}: the Gheed's swap")
    return True


def forget_given_up(self: Hunter) -> None:
    """Every give-up forgotten (`DropLedger.forget`): the Gheed's swap's GHEED_STASH (runner.py)."""
    self.drops.forget()


def again(self: Hunter, run: Run, drops: Sequence[Drop], here: Point, world: World | None = None) -> None:
    """A valuable given up (GATHER_TRIES) is tried once more when the character comes within PICK_REACH of it
    on a clear line (travel.py `clear_line`): a click from there walks. Chaos Sanctuary, 15:18:35-37 on
    2026-10-14 (rca/2026-10-14/run-1214-findings.md §3.2): the Flawless Emerald clicked four times round a wall
    corner from 18.3 away was given up, and 2 s later the character passed 5.7 from it on a clear line and went
    on; the player went back for it by hand. Once a drop: a click that takes nothing from there is not looped
    on. What the player put down is never among `drops` (world.py `PutDown`: the runner's loot passes through
    it). The level's ground is read only when a drop is a candidate."""
    spent = [
        d
        for d in drops
        if d.kind == VALUABLE
        and self.drops.spent(d.unit_id)
        and d.unit_id not in self.drops.retried
        and math.dist(here, (d.x, d.y)) <= PICK_REACH
    ]
    if not spent:
        return
    world = world if world is not None else run.world()
    level = self.known_level(world.player) if world.player is not None else None
    if level is None:
        return
    ground = Ground(level.ground)
    for drop in spent:
        if not clear_line(ground, world.doors, here, (drop.x, drop.y)):
            continue
        self.drops.first(self.drops.retried, drop.unit_id)
        why = self.drops.given_up(drop.unit_id)
        self.drops.gathered[drop.unit_id] = GATHER_TRIES - 1
        self.drops.tried.pop(drop.unit_id, None)
        self.drops.left_said.discard(drop.unit_id)
        LOG.info(
            'Macro: pickup: one more try at %s at (%.0f, %.0f), %.0f away on a clear line now (%s)',
            drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
        )  # fmt: skip
        run.say(f'One more try at {drop.label}')


def left(self: Hunter, drop: Drop, here: Point, why: str, who: str) -> None:
    """A valuable or gold `who` gives up on, said once a drop (a potion says its own: `refused_potion`)."""
    if drop.kind in (HEALING, REJUVENATION) or not self.drops.first(self.drops.left_said, drop.unit_id):
        return
    LOG.info(
        'Macro: %s leaves %s at (%.0f, %.0f), %.0f away: %s',
        who, drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
    )  # fmt: skip


def refused_potion(self: Hunter, drop: Drop, here: Point, why: str) -> None:
    """A potion the run leaves, said once a potion and reason (potions-findings.md M4: it was silent)."""
    if drop.kind in (HEALING, REJUVENATION) and self.potions.refuse(drop.unit_id, why):
        LOG.info(
            'Macro: pursuit: %s at (%.0f, %.0f), %.0f away, %s',
            drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
        )  # fmt: skip


def scarce(self: Hunter, run: Run, loot, here: Point, world: World | None) -> Drop | None:
    """A healing potion known on the level beyond the pickup key's own POTION_UNITS that is worth its
    detour now (macros/supply.py `worth`, `detour`): with the belt's healing potions below the reserve the
    character keeps (automation/priority.py `reserve`), harm's price of a potion for each one short, against
    the way there and back by the navigator's eta with the movement in hand and the pickup's dwell. Judged
    once in DECIDE_SECONDS * 4, the nearest two asked; the one found stays the goal until judged again."""
    now = run.clock()
    judged, found = self.fetching
    if now - judged < 4 * DECIDE_SECONDS:
        return found if found is not None and found.unit_id in self.potions.seen else None
    self.fetching = (now, None)
    settings = self.build.settings.safety
    belt = on_belt(loot)
    healing, rejuvenations = belt[PotionType.HEALING], belt[PotionType.REJUVENATION]
    allowed = worth(healing, reserve(loot.max_life, rejuvenations, HEAL_PRIORITY), settings.healing_seconds)
    if not allowed or not shortages(loot)[1] or world is None or world.player is None:
        return None
    rect = run.actuator.keys.focused_window_rect()
    level = self.known_level(world.player)
    if rect is None or level is None:
        return None
    ground = Ground(level.ground)
    far = [p for p in self.potions.lying(HEALING, here) if math.dist(here, (p.x, p.y)) > POTION_UNITS]
    for potion in far[:2]:
        if self.drops.spent(potion.unit):
            continue
        there = self.travel.eta(run, world, ground, rect[2] / rect[3], (potion.x, potion.y), PRESSED, level.rooms)
        cost = detour(there, settings.operate_dwell)
        if cost > allowed:
            self.refused_potion(
                Drop(potion.unit, potion.x, potion.y, potion.label, potion.kind),
                here,
                f'not worth its detour: {cost:.1f} s against {allowed:.0f} s (belt healing {healing})',
            )
            continue
        LOG.info(
            'Macro: pursuit: %s at (%.0f, %.0f) is worth its detour: %.1f s against %.0f s (belt healing %d)',
            potion.label, potion.x, potion.y, cost, allowed, healing,
        )  # fmt: skip
        drop = Drop(potion.unit, potion.x, potion.y, potion.label, potion.kind)
        self.fetching = (now, drop)
        return drop
    return None


def stay_by(self: Hunter, run: Run, here: Point, *, wanted: bool = True, foes: Sequence[Monster] = ()) -> Drop | None:
    """A valuable the pickup rules want within PICK_NEAR that neither the inventory has room for (the
    player, 2026-10-13: "when valuable doesn't fit: we need to stop near it"): the level run stands by it
    (goals.py `WAIT`). Not magic, rare or white equipment taken only because the loot filter shows it
    (`Loot.shown`: the player, 2026-10-12, "allow moving when the item isn't very valuable"); a unique or set
    item the filter shows is stood by (world.py `NAMED`: the player, 2026-10-14, the Unique Plate Mail of
    run-1214-findings.md §3.1), and not one a press went on from
    (`waived`). The card's warning says it while it lasts; taken back after. Not `wanted`: a drop to take
    comes first (the room may have come), and only the warning is taken back."""
    loot = unshunned(run.loot(), run.clock()) if run.loot is not None and wanted else None
    found = None
    if loot is not None:
        near = [d for d in loot.drops if d.kind == VALUABLE and math.dist(here, (d.x, d.y)) <= PICK_NEAR]
        left = [
            d for d in near
            if lootpolicy.verdict(
                d, lootpolicy.RUN, room=has_room(loot.room, d.size), shown=d.unit_id in loot.shown,
                given_up=d.unit_id in self.waived,
            ).hold
        ]  # fmt: skip
        found = min(left, key=lambda d: math.dist(here, (d.x, d.y))) if left else None
    if found is None:
        if self.warned is not None:
            self.warned = None
            run.warn(None)
        return None
    cube = loot is not None and loot.cube is not None and has_room(loot.cube, found.size)
    quiet = all(math.dist(here, (m.x, m.y)) > QUIET_UNITS for m in foes)
    cube_unread = loot is not None and loot.cube is None
    if (cube or cube_unread) and quiet and self.room_maker is not None and self.room_tried != found.unit_id:
        # The cube has room: the macro's own pickups go into it, and the next look takes the drop (the player,
        # 23:55 on 2026-10-17: "if we have cube space - we should move items there"; two stands for the player on
        # 2026-10-17, 47.5 s by an Amulet and one by a Flawed Sapphire)
        self.room_tried = found.unit_id
        try:
            moved = self.room_maker(run)
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: pursuit: no room made in the cube for %s: %s', found.label, stop)
            moved = 0
        if moved:
            LOG.info('Macro: pursuit: %d items into the cube: room for %s', moved, found.label)
            if self.warned is not None:
                self.warned = None
                run.warn(None)
            return None
    if self.warned != found.unit_id:
        self.warned = found.unit_id
        told = ' (the cube has room for it)' if cube else ''
        LOG.info(
            'Macro: pursuit: the inventory has no room for %s at (%.0f, %.0f), %.0f away: the run stands by it%s',
            found.label, found.x, found.y, math.dist(here, (found.x, found.y)), told,
        )  # fmt: skip
        run.stand_by(f'Inventory full: {found.label} here — make room{told}')
    return found


def shack_goal(self: Hunter, run: Run, world: World, player, route: str) -> Goal | None:
    """On the KP_6 loop's run, a container of the camp the character stands in, closed, in sight, near and
    beside one of the camp's chests (macros/shacks.py; routes/lower-kurast-loop-plan.md phase 6c): opened as a
    mark is, from where the character stands, a side goal of the level's route `route` (with none, the run has no
    stage to work and ends: pursuit.py `run_level`). One tried SHACK_TRIES times is left."""
    level = self.known_level(player)
    if level is None or run.things is None:
        return None
    ground, here = Ground(level.ground), (player.x, player.y)
    if len(self.shack_tries) > 200:
        self.shack_tries.clear()  # units of games long left
    skip = frozenset(unit for unit, tries in self.shack_tries.items() if tries >= SHACK_TRIES)
    found = shack_thing(
        run.things(), level.rooms, here, lambda origin, at: clear_shot(ground, origin, at, world.doors), skip
    )
    if found is None:
        return None
    thing, name = found
    mark = Target(player.area, (), (thing.x / TILE_UNITS, thing.y / TILE_UNITS), name, 'target', use=UNIQUE_CHEST)
    label = f'{name}, in the shack'
    return Goal(label, (thing.x, thing.y), USE, USE_NEAR, self.looped, unit=thing.unit_id, mark=mark, route=route)


def super_chest_goal(
    self: Hunter, run: Run, player, here: Point, route: str, spend: Intent, rooms: Sequence[Room] = ()
) -> Goal | None:
    """A full clear's closed super chest within SUPER_NEAR, nearest first, opened as a route's chest is; one tried
    SUPER_TRIES times is left (its tries counted with the shacks' containers, `act`)."""
    if run.things is None:
        return None
    chests = [
        thing
        for thing in run.things()
        if thing.txt_id == SUPER_CHEST
        and thing.mode == 0
        and thing.selectable is not False
        and self.shack_tries.get(thing.unit_id, 0) < SUPER_TRIES
        and math.dist(here, (thing.x, thing.y)) <= SUPER_NEAR
        and passing_key((thing.x, thing.y), thing.unit_id, rooms) not in self.passed
    ]
    if not chests:
        return None
    thing = min(chests, key=lambda t: math.dist(here, (t.x, t.y)))
    place = (thing.x / TILE_UNITS, thing.y / TILE_UNITS)
    mark = Target(player.area, (), place, 'Super chest', 'target', use=SUPER_CHEST)
    # A clearing goal: passed like one when it is gone for CLEAR_SECONDS with no progress (`goes_on`)
    return Goal('full clear: Super chest', (thing.x, thing.y), USE, USE_NEAR, spend, unit=thing.unit_id, mark=mark,
                route=route, clearing=True)  # fmt: skip


def at_hand(self: Hunter, found: Goal | None, player, world: World) -> bool:
    """Whether the route's `found` is a chest the character opens from where it stands (travel.py `open_reaches`):
    before the shack's container then, not after a hop to the rack and one back (9 of 27 stays 19:45-20:08 on
    2026-10-17 landed within 4 of the chest and went to the rack first, 2.9 s from there to the chest opened;
    rca/2026-10-17/slow-legs-findings.md)."""
    level = self.known_level(player)
    if found is None or found.do != USE or level is None:
        return False
    return open_reaches(Ground(level.ground), world.doors, (player.x, player.y), found.place, OPEN_NEAR)


def blockers(self: Hunter, goal: Goal | None, foes: Sequence[Monster], now: float) -> list[Monster]:
    """The hostiles alive that the hands found in the way of `goal`'s act (`Covered`), while that is
    no older than BLOCK_SECONDS; forgotten once none of them lives or the goal changed."""
    blocking = self.blocking
    if blocking is None or goal is None:
        return []
    label, units, until = blocking
    found = [m for m in foes if m.unit_id in units]
    if label != goal.label or now > until or not found:
        self.blocking = None
        return []
    return found


def goal(
    self: Hunter, run: Run, world: World, foes: list[Monster], pressed: bool, posted: Pursuit | None
) -> Goal | None:
    """The goal the key means now (macros/goals.py `goal_of`), from the route's stage, the level
    card, the hostiles in the world and the tracker's memory. A valuable beside the character comes
    first for a press (macros/pickup.py `worth_a_stop`, asked once a press: it counts its tries); on a
    level run a drop the pickup rules take (`side_drop`). Hostiles that bar the goal's act make the
    fight with them the goal (`first_fight`). `pressed`: a fresh press asks for its goal now; `posted`:
    the mailbox as the look read it (`judge`). A level run's mode adds to it at the look (`cleared`)."""
    player = world.player
    assert player is not None
    here, area, bearings = (player.x, player.y), player.area, self.bearings
    running = posted is not None and posted.runs
    staged = route.staged(bearings.progress, area)
    card = bearings.card() if bearings.card is not None else None
    if card is not None and card.area != area:
        card = None  # the card is still the level just left
    drop = side = stay = None
    if pressed and posted is not None and posted.advance:
        if self.stopped_for[0] != posted.pressed_at:
            self.stopped_for = (posted.pressed_at, worth_a_stop(run))
        drop = self.stopped_for[1]
    elif running:
        side = self.side_drop(run, here, foes, world)
        stay = self.stay_by(run, here, wanted=side is None, foes=foes)
    elif self.pursuing and not pressed:
        # Attack mode's own goal (no level run, no press): a potion a low belt restocks in the quiet comes first
        side = self.side_drop(run, here, foes, world, restocking=True)
    known = self.remembered(area) if self.remembered is not None else []
    live = {m.unit_id for m in foes}
    self.vanished |= {unit for unit, x, y, _ in known if unit not in live and math.dist(here, (x, y)) <= VANISH_UNITS}

    def elsewhere() -> tuple[Point, str] | None:
        # Nothing is known of the boss: whatever of the level is left to look for it in, as the seek
        # step looks (the nearest hostile known, else the unexplored room nearest by the way).
        quarry = self.quarry(area, here, foes, any_hostile=True)
        if quarry is not None:
            return quarry
        level, rect = self.known_level(player), run.actuator.keys.focused_window_rect()
        frontier = self.frontier(level, player, rect) if level is not None and rect is not None else None
        if frontier is None:
            return None
        _, _, (x, y) = frontier
        return ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS), 'an unexplored room'

    opens = None
    if running and posted is not None and posted.rush and side is None and stay is None:
        # the KP_6 loop's run: a shack's container in sight first, a side goal of the level's route
        opens = self.shack_goal(run, world, player, staged[0] if staged is not None else '')
    found = goal_of(
        here,
        spend=self.looped_now(run.clock())
        if posted is not None and posted.rush
        else PRESSED
        if pressed or running
        else STANDING,
        reach=self.reach,
        stage=staged[1] if staged is not None else None,
        route=staged[0] if staged is not None else '',
        card=card,
        # Every hostile, the ones left alone for a while among them (`untouchable`): a boss the strikes
        # did nothing to is still where the fight is, and nothing else is sought in its place.
        foes=hostiles(world),
        remembered=known,
        supers=bearings.supers(area) if bearings.supers is not None else (),
        gone=frozenset(self.vanished | set(self.untouchable)),
        # Only a press or a level run looks for a boss nothing is known of: the mode by itself goes
        # nowhere for it (macros/pursuit.py `decide`), and the look costs a potential over the whole level.
        elsewhere=elsewhere if pressed or running else None,
        entry=door_entry(card),
        drop=drop,
        side=side,
        stay=stay,
    )
    if opens is not None and not self.at_hand(found, player, world):
        found = opens
    missed = self.missed
    if found is not None and missed is not None and missed[0] == found.label and run.clock() <= missed[1]:
        found = nearer(found)  # its act did not take from where the character stood: from nearer now
    if found is not None and found.do == FIGHT and found.unit in self.nearing:
        # a boss the strikes did nothing to from where they were made: its fight is near enough in the engage ring
        found = replace(found, near=min(found.near, self.attack.engage))
    self.base = found
    barring = self.blockers(found, foes, run.clock())
    if found is not None and running and (not self.pursuing or found.guarded):
        # The run's own move, no press asking for the goal now: what stands where the goal's act is made
        # is fought first (a pack on a seal, the guards of a wanted potion). A press is never refused this
        # way (architecture §1). With the safety pricing on, harm prices what stands at an object; a potion's
        # guards stay a presence floor (no pickup among a pack, Tower Cellar 5) until harm prices the pickup.
        known = {m.unit_id for m in barring}
        barring += [m for m in in_the_way(found, foes, here) if m.unit_id not in known]
    return first_fight(found, here, barring, self.reach) if found is not None and barring else found


def cleared(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, found: Goal | None
) -> Goal | None:
    """A level run's goal by its mode (macros/runmode.py; the player, 2026-10-14): the hostiles on its way
    first, those within CLEAR_WAY with a clear line (goals.py `clear_way`); on a full clear the rest of the
    level next (`rest_of_level`: what is in sight, what is remembered alive, the rooms not explored); then
    `found`, the route's. A fight, a drop or a stand-by of `found`'s own is left as it is. Out of a full clear
    only a way through the level is cleared (WAYS: a door, a place, a stand), not the way to an object: what
    stands at a seal is priced at it and the seal calls its pack (the arena's seal moment: fighting the 12 by
    Vizier seal 1 first left the Vizier alive in all ten plays); and a level with no route is the key's old
    step. What has gone CLEAR_SECONDS with no strike and no progress by the way, or that the navigator had no way
    to, is passed for PASS_SECONDS (`goes_on`, `judge`); a goal left for another is not taken back while that other
    is still the one to go for (TAKE_BACK, `taken_back`)."""
    mode = self.mode
    if mode is not None and mode.agenda and self.agenda is not None:
        return self.agenda_cleared(run, world, foes, ground, found)
    clear = mode is not None and mode.clear
    if found is not None and (found.do in (PICK_UP, WAIT, FIGHT) or found.guarded):
        return found
    # Nor on the KP_6 loop's rushed run (not a full clear): its way out is gone to, a pack beside it fought only
    # when it hurts or blocks (the player, 2026-10-16: "don't fight what isn't attacking"). Cleared, every pack on
    # the way down the Catacombs was a goal, and the run stood ~1.8 s at each before its strike (RUSH_UNMOVED): 41
    # stands, 74 s, at 10:20-10:41 on 2026-10-18 (rca/2026-10-18/freeze-near-mobs-findings.md)
    if not clear and (self.rushing or found is None or not found.route or found.do not in WAYS):
        return found
    player = world.player
    assert player is not None
    here, now = (player.x, player.y), run.clock()
    level = self.known_level(player)
    rooms = level.rooms if level is not None else ()
    self._forget_passed(now)
    spend = found.spend if found is not None else PRESSED

    herald = bool(self.omens) or any(m.tier and m.leader for m in foes)
    route = found.route if found is not None else ''
    chest = self.super_chest_goal(run, player, here, route, spend, rooms) if clear and not herald else None

    def candidate(skip: frozenset[object]) -> Goal | None:
        rest = self.rest_of(run, world, foes, here, skip, rooms) if clear and chest is None else None
        base = chest or (rest_of_level(rest, found, self.reach, spend) if rest is not None else found)
        near = self._on_the_way(world, ground, foes, here, skip)
        return clear_way(base, here, near, self.reach) if base is not None and near else base

    return self._clear_through(candidate, run, world, ground, rooms, found, now)


def _forget_passed(self: Hunter, now: float) -> None:
    """The passes and the goals left for another that are over (`goes_on`, `taken_back`)."""
    self.passed = {key: until for key, until in self.passed.items() if until > now}
    self.left_for = {key: left for key, left in self.left_for.items() if left[0] > now}


def _on_the_way(
    self: Hunter,
    world: World,
    ground: Ground,
    foes: Sequence[Monster],
    here: Point,
    skip: frozenset[object],
    which: Callable[[Monster], bool] = lambda m: True,
) -> list[Monster]:
    """The hostiles on the way (of `which`): within CLEAR_WAY with a clear line, not passed nor skipped."""
    return [
        m
        for m in foes
        if m.unit_id not in self.passed
        and m.unit_id not in skip
        and which(m)
        and math.dist(here, (m.x, m.y)) <= CLEAR_WAY
        and clear_shot(ground, here, (m.x, m.y), world.doors)
    ]


def _clear_through(
    self: Hunter,
    candidate: Callable[[frozenset[object]], Goal | None],
    run: Run,
    world: World,
    ground: Ground,
    rooms: Sequence[Room],
    found: Goal | None,
    now: float,
) -> Goal | None:
    """The goal `candidate` gives, taken back (`taken_back`) and passed when it goes on no more (`goes_on`): a goal
    passed now gives its place to the next, three times at most; `found` when none holds."""
    chosen = found
    for _ in range(3):
        goal = self.taken_back(candidate, rooms, found)
        if goal is None or not goal.clearing or self.goes_on(run, world, ground, goal, rooms, now):
            chosen = goal
            break
    self.went_for(chosen, rooms, now)
    return chosen


def agenda_cleared(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, found: Goal | None
) -> Goal | None:
    """The terror zone kinds' run (`cleared`, macros/goals-plan.md §3): the agenda's next target first (agenda.py
    `Agenda.in_level`: a Herald, its omen, a side drop's guards then the drop, the leaders, the rooms), the
    route's stage of the level (`found`) after it. Passing, judging and taking back are the full clear's (`goes_on`,
    `taken_back`), and so are the hostiles on the way (leaders within CLEAR_WAY with a clear line; every one on a
    Full clear TZ). A drop's guards are the fight first (the player's example: "we may need some kill action near
    pickup item, then pickup"); a stand-by by a valuable, a guarded potion, a boss's fight are left as they are."""
    player = world.player
    assert player is not None
    here, now, area = (player.x, player.y), run.clock(), player.area
    level = self.known_level(player)
    rooms = level.rooms if level is not None else ()
    self._forget_passed(now)
    if found is not None and (found.do == WAIT or found.guarded):
        return found
    if found is not None and found.do == PICK_UP:
        side = Objective(SIDE, found.label, 3, area, found.place, found.unit)
        target = self.agenda_target(run, world, foes, here, frozenset(), rooms, side)
        guard = next((m for m in foes if target is not None and target.kind == KILL and m.unit_id == target.unit), None)
        if guard is None:
            return found
        # The fight first is the level run's own work (`clearing`): the drop's goal holds no route stage on a level
        # with no route (Great Marsh), and a fight goal with neither ended the run there, the elite and the gold
        # left (09:01:51 on 2026-10-19, pursuit.py `run_level`: "nothing is left to go to on this level")
        return replace(first_fight(found, here, [guard], self.reach), clearing=True)
    spend = found.spend if found is not None else PRESSED
    everyone = self.agenda_policy is not None and self.agenda_policy(area) == FULL_CLEAR
    things = run.things() if run.things is not None else ()  # read once a look: the super chests (`agenda_chests`)

    def candidate(skip: frozenset[object]) -> Goal | None:
        target = self.agenda_target(run, world, foes, here, skip, rooms, None, things)
        if target is None:
            base = found
        elif target.kind == OPEN:
            base = self.agenda_chest(area, target, found, spend)
        else:
            unit = target.unit if target.kind == KILL else None
            assert target.place is not None
            base = rest_of_level((target.place, target.label, unit), found, self.reach, spend)
        if base is None or (base is found and found is not None and found.do == FIGHT):
            return base
        near = self._on_the_way(world, ground, foes, here, skip, lambda m: bool(everyone or m.leader or m.tier))
        return clear_way(base, here, near, self.reach) if near else base

    return self._clear_through(candidate, run, world, ground, rooms, found, now)


def agenda_target(
    self: Hunter,
    run: Run,
    world: World,
    foes: Sequence[Monster],
    here: Point,
    skip: frozenset[object],
    rooms: Sequence[Room],
    side: Objective | None,
    things: Sequence[Thing] = (),
) -> Objective | None:
    """The agenda's next target on this level (agenda.py `Agenda.in_level`) from what this look knows: the leaders
    in sight and remembered alive (every hostile on a Full clear TZ), the hostiles (a drop's guards), a Herald's
    omens, the side drop, the super chests among `things` (`agenda_chests`), the next unexplored room (asked only
    when wanted), the goals passed."""
    agenda, player = self.agenda, world.player
    assert agenda is not None
    assert player is not None
    area, now = player.area, run.clock()
    policy = self.agenda_policy(area) if self.agenda_policy is not None else FULL_CLEAR
    if policy == ON_THE_WAY and (world.game_name, area) in self.wayless:
        policy = COVER  # no way to the route's goal: the rooms are explored for it (`judge`)
    everyone = policy == FULL_CLEAR
    out = skip | set(self.passed)
    live = [m for m in foes if everyone or m.leader or m.tier]
    leaders = [Leader(m.unit_id, (m.x, m.y), label(m), bool(m.tier and m.leader)) for m in live]
    seen = {m.unit_id for m in foes}
    gone = seen | self.vanished | set(self.untouchable)
    known = self.remembered(area) if self.remembered is not None else []
    leaders += [
        Leader(unit, (x, y), 'the remembered monster', live=False)
        for unit, x, y, leader in known
        if unit not in gone and (everyone or leader)
    ]
    omens = tuple((spot, omen_stand(spot, here)) for spot in self.omens_now(run, area, now))

    def frontier() -> tuple[Point, str] | None:
        room = self.next_room(run, player, area, now)
        return (room[0], room[1]) if room is not None else None

    view = LevelView(
        area,
        here,
        tuple(leaders),
        tuple((m.unit_id, (m.x, m.y)) for m in foes),
        omens,
        side,
        frontier,
        policy,
        lambda place, unit: passing_key(place, unit, rooms) in out or (unit is not None and unit in out),
        OMEN_NEAR,
        *self.agenda_chests(things),
    )
    target = agenda.in_level(view)
    said = (target.kind, target.unit, target.label) if target is not None else None
    if said != self.agenda_said:
        self.agenda_said = said
        if target is None:
            LOG.info("Macro: agenda: no target here: the route's own goal")
        else:
            LOG.info('Macro: agenda: target %s (%s, tier %d, %d leaders known here)', target.label, target.kind,
                     target.tier, agenda.known(area))  # fmt: skip
    return target


def agenda_chests(self: Hunter, things: Sequence[Thing]) -> tuple[tuple[tuple[int, Point], ...], frozenset[int]]:
    """The super chests (objects.txt 397, levels/model.py SUPER_CHEST) among the streamed `things`, for the
    agenda's CHEST tier (2026-10-19, the player: "we don't open intermediate goals, like superchests ... open them
    along the way"): (unit, place) of the closed ones (mode 0, not flagged unselectable), and the units seen open
    or tried SUPER_TRIES times (`operate` counts them with the shacks' containers), never targets again."""
    closed, spent = [], set()
    for thing in things:
        if thing.txt_id != SUPER_CHEST:
            continue
        if thing.mode != 0 or self.shack_tries.get(thing.unit_id, 0) >= SUPER_TRIES:
            spent.add(thing.unit_id)
        elif thing.selectable is not False:
            closed.append((thing.unit_id, (thing.x, thing.y)))
    return tuple(closed), frozenset(spent)


def agenda_chest(self: Hunter, area: int, target: Objective, found: Goal | None, spend: Intent) -> Goal:
    """The agenda's OPEN `target` as the run's goal: the super chest opened as a full clear's is
    (`super_chest_goal`: a USE of a SUPER_CHEST mark, its tries counted in `operate`), a clearing goal of the
    run's own (passed by `goes_on` with no progress; never the end of a level with no route, pursuit.py
    `run_level`), the route of `found` kept for the log. Its spill is the drop tiers' at the next looks."""
    assert target.place is not None
    x, y = target.place
    mark = Target(area, (), (x / TILE_UNITS, y / TILE_UNITS), 'Super chest', 'target', use=SUPER_CHEST)
    route = found.route if found is not None else ''
    return Goal(f'agenda: {target.label}', (x, y), USE, USE_NEAR, spend, unit=target.unit, mark=mark, route=route,
                clearing=True)  # fmt: skip


def goal_key(self: Hunter, goal: Goal | None, rooms: Sequence[Room]) -> object | None:
    """The key a level run's goal is judged and left by: a clearing goal's `passing_key`, the route's by itself."""
    if goal is None:
        return None
    return passing_key(goal.place, goal.unit, rooms) if goal.clearing else ('the run', goal.label, goal.do)


def taken_back(
    self: Hunter, candidate: Callable[[frozenset[object]], Goal | None], rooms: Sequence[Room], found: Goal | None
) -> Goal | None:
    """The run's next goal (`candidate`), unless it is a clearing goal left for another less than TAKE_BACK ago
    while that other would still be the goal without it: then that other (the run goes on with the goal it
    took). The other gone (reached, dead, passed), the goal left is taken back."""
    goal = candidate(frozenset())
    key = self.goal_key(goal, rooms)
    left = self.left_for.get(key) if goal is not None and goal.clearing else None
    if left is None:
        return goal
    other = candidate(frozenset((key,)))
    if other is not None and self.goal_key(other, rooms) == left[1]:
        return other
    return goal


def went_for(self: Hunter, chosen: Goal | None, rooms: Sequence[Room], now: float) -> None:
    """Notes the goal this look went for: a clearing goal the last look went for is left for this one when this
    is another clearing goal (TAKE_BACK), unless it was passed. The route's own goal is no such other: it is what
    the run goes to when no clearing goal is left (one out of sight a moment comes back to it at once)."""
    key = self.goal_key(chosen, rooms)
    went, self.went = self.went, key
    if went is None or chosen is None or not chosen.clearing or went == key or went in self.passed:
        return
    if isinstance(went, tuple) and went[:1] == ('the run',):
        return  # the route's own goal is never left so: it is what the run is for
    if len(self.left_for) > 200:
        self.left_for.clear()
    self.left_for[went] = (now + TAKE_BACK, key)


def goes_on(
    self: Hunter, run: Run, world: World, ground: Ground, goal: Goal, rooms: Sequence[Room], now: float
) -> bool:
    """Whether a level run's clearing goal is still gone for: True while it has not been gone for CLEAR_SECONDS
    with no strike and no progress by the way (its way left by the means in hand, `Travel.eta`, down by
    PROGRESS_SECONDS); else it is passed (`pass_by`) and False. Its judging goes on across other goals
    (`Judging`). The way left is asked once in PROGRESS_LOOK seconds a goal, and before a pass: a walked field
    of a far goal on ground just read is a cold Dijkstra (rca/2026-10-14/run-2040-findings.md)."""
    key = passing_key(goal.place, goal.unit, rooms)
    judging = self.judging.get(key)
    if judging is None:
        if len(self.judging) > 400:
            self.judging = {k: j for k, j in self.judging.items() if now - j.last <= PASS_SECONDS}
        judging = self.judging[key] = Judging(0.0, math.inf, now)
    gap = now - judging.last
    struck = self.struck_at > judging.last
    judging.last = now
    if struck:
        judging.idle = 0.0
        return True
    if self.went == key or gap <= JUDGE_GAP:  # the last look's goal too, or another's a moment
        judging.idle += gap
    if now - judging.checked >= PROGRESS_LOOK or judging.idle > CLEAR_SECONDS:
        rect = run.actuator.keys.focused_window_rect()
        aspect = rect[2] / rect[3] if rect is not None else 16 / 9
        eta = self.travel.eta(run, world, ground, aspect, goal.place, goal.spend, tuple(rooms))
        judging.checked = now
        if eta <= judging.best - PROGRESS_SECONDS:
            judging.idle, judging.best = 0.0, eta
            return True
    if judging.idle <= CLEAR_SECONDS:
        return True
    self.pass_by(goal, f'no strike and no progress by the way in {CLEAR_SECONDS:.0f} s on the way to it', now, rooms)
    return False


def on_the_way(self: Hunter, run: Run, here: Point, drop: Drop, world: World | None, *, looped: bool = False) -> bool:
    """Whether a valuable is near enough for a level run to take on its way (`side_drop`): PICK_NEAR by walking
    (`walked_near`), not in a straight line. The Ith Rune of 22:36:09 on 2026-10-14 was 26 straight
    and 226 by walking across the lava: taken for "on the way" from one side and not from the other, it had the
    run warp back and forth 8 times (rca/2026-10-14/run-1932-findings.md §1.2.3). `looped`: the KP_6 loop's run,
    which takes anything it reads that Teleport brings it to (`teleport_reach`): visible loot is taken now."""
    if self.walked_near(run, here, drop, world):
        return True
    return looped and self.teleport_reach(run, here, drop, world)


def walked_near(self: Hunter, run: Run, here: Point, drop: Drop, world: World | None) -> bool:
    """Whether `drop` is within PICK_NEAR of `here` by walking (travel.py `walked_length`)."""
    place = (drop.x, drop.y)
    if math.dist(here, place) > PICK_NEAR:
        return False
    world = world if world is not None else run.world()
    level = self.known_level(world.player) if world.player is not None else None
    ground = Ground(level.ground) if level is not None else None
    return walked_length(ground, world.doors, here, place) <= PICK_NEAR


def teleport_reach(self: Hunter, run: Run, here: Point, drop: Drop, world: World | None) -> bool:
    """Whether the navigator's way to `drop` is of Teleport hops (movement.py HOPS: they cross walls and lava) and
    takes LOOP_PICK_SECONDS at most by its eta: the loop's run goes for it now (`on_the_way`). Judged once in
    FAR_JUDGED a drop, said once a drop when it is gone for (18:22:17 on 2026-10-18: a Ko Rune 34.5 straight, 117
    walked behind the character, left)."""
    now = run.clock()
    judged = self.far_judged.get(drop.unit_id)
    if judged is not None and 0.0 <= now - judged[0] < FAR_JUDGED:
        return judged[1]
    world = world if world is not None else run.world()
    player, rect = world.player, run.actuator.keys.focused_window_rect()
    level = self.known_level(player) if player is not None else None
    found, eta = False, math.inf
    if level is not None and rect is not None:
        ground, aspect, place = Ground(level.ground), rect[2] / rect[3], (drop.x, drop.y)
        intent = self.looped_now(now)
        if self.travel.means(run, world, ground, aspect, place, intent, level.rooms) == HOPS:
            eta = self.travel.eta(run, world, ground, aspect, place, intent, level.rooms)
            found = eta <= LOOP_PICK_SECONDS
    if len(self.far_judged) > 200:
        self.far_judged.clear()
    said = judged is not None and judged[1] == found
    self.far_judged[drop.unit_id] = (now, found)
    if not said:
        LOG.info(
            'Macro: run: %s at (%.0f, %.0f), %.0f away: %s',
            drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)),
            f'Teleport brings it in {eta:.1f} s: taken now, the run waits'
            if found
            else f'not taken from here: no Teleport way within {LOOP_PICK_SECONDS:g} s (eta {eta:.1f} s)',
        )  # fmt: skip
    return found


def pass_by(self: Hunter, goal: Goal, why: str, now: float, rooms: Sequence[Room] = ()) -> None:
    """A level run's clearing goal is passed for PASS_SECONDS from `now` (`cleared`), said."""
    if len(self.passed) > 400:
        self.passed.clear()
    key = passing_key(goal.place, goal.unit, rooms)
    self.passed[key] = now + PASS_SECONDS
    self.judging.pop(key, None)
    LOG.info('Macro: run: passing %s at (%.0f, %.0f): %s', goal.label, *goal.place, why)


def rest_of(
    self: Hunter,
    run: Run,
    world: World,
    foes: list[Monster],
    here: Point,
    skip: frozenset[object] = frozenset(),
    rooms: Sequence[Room] = (),
) -> tuple[Point, str, int | None] | None:
    """What a full clear goes for next on the character's level: the nearest hostile in sight, else the
    nearest the tracker remembers alive where it was seen, else the first stop of the tour of the rooms not
    explored yet (`frontier`, looked for once in REST_SECONDS: a potential over the whole level); as (place,
    what, unit), no unit for a room. None: the level is clear as far as is known. What is passed, or in `skip`
    (keys as `passing_key` makes them over `rooms`), is not gone for."""
    player = world.player
    assert player is not None
    area, now = player.area, run.clock()
    out = skip | set(self.passed)
    live = [m for m in foes if m.unit_id not in out]
    heralds = [m for m in live if m.tier and m.leader]
    if heralds:  # a Herald first, wherever the others stand (HERALD_OMEN)
        herald = min(heralds, key=lambda m: math.dist(here, (m.x, m.y)))
        return (herald.x, herald.y), label(herald), herald.unit_id
    spots = self.omens_now(run, area, now)
    if spots:
        spot = min(spots, key=lambda s: math.dist(here, s))
        near = [m for m in live if math.dist(spot, (m.x, m.y)) <= OMEN_NEAR]
        if near:
            nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
            return (nearest.x, nearest.y), label(nearest), nearest.unit_id
        stand = omen_stand(spot, here)
        if passing_key(stand, None, rooms) not in out:
            return stand, 'the stand for the Herald coming', None
    if live:
        nearest = min(live, key=lambda m: math.dist(here, (m.x, m.y)))
        return (nearest.x, nearest.y), label(nearest), nearest.unit_id
    known = self.remembered(area) if self.remembered is not None else []
    seen = {m.unit_id for m in foes}
    gone = seen | self.vanished | set(self.untouchable) | out
    kept = [(x, y, unit) for unit, x, y, _leader in known if unit not in gone]
    near = [k for k in kept if math.dist(here, (k[0], k[1])) <= REMEMBERED_NEAR]
    if near:
        x, y, unit = min(near, key=lambda k: math.dist(here, (k[0], k[1])))
        return (x, y), 'the remembered monster', unit
    room = self.next_room(run, player, area, now)
    if room is not None and passing_key(room[0], None, rooms) not in out:
        return room
    if kept:
        # The level toured: the ones remembered further off, nearest first
        x, y, unit = min(kept, key=lambda k: math.dist(here, (k[0], k[1])))
        return (x, y), 'the remembered monster', unit
    return None


def next_room(self: Hunter, run: Run, player, area: int, now: float) -> tuple[Point, str, int | None] | None:
    """The first stop of the tour of the rooms not explored yet (`frontier`), looked for once in REST_SECONDS."""
    cached = self.rest
    if cached is not None and cached[1] == area and now - cached[0] < REST_SECONDS:
        room = cached[2]
    else:
        level, rect = self.known_level(player), run.actuator.keys.focused_window_rect()
        stop = self.frontier(level, player, rect) if level is not None and rect is not None else None
        room = None
        if stop is not None:
            _, _, (x, y) = stop
            room = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS), 'an unexplored room', None
        self.rest = (now, area, room)
    return room


def run_mode(self: Hunter, run: Run, area: int, posted: Pursuit | None) -> Mode:
    """The run mode on level `area` at this look (macros/runmode.py): a double press of the pickup key whose
    window is over switches it, for this level; a switch made on another level lapses. Said once a run and a
    change (`Macro: run: ...`) while a level run is held."""
    now = run.clock()
    if self.switched is not None and self.switched[0] != area:
        self.switched = None
    with self.mailbox:
        pairs, self.taps = doubles(self.taps, now)
    # Not on the KP_6 loop's run: its chests first, a terror zone or not (the player, 2026-10-16: "focus on reaching
    # chests as fast as possible"; at 08:30:26 on 2026-10-17 Lower Kurast was terrorized and the run cleared it)
    # Nor on any KP_6 loop's run (the player, 2026-10-19 ~02:12: "andy loop shouldn't focus on full clearing level.
    # we're going to have separate mods"): a terror zone's work is the terror zone kinds' own, by their agenda
    terror = self.bearings.terror(area) and not (posted is not None and (posted.rush or posted.looped))
    for first, last in pairs:
        # Each double press by the clock, also one no look came in the window of (runmode.py `owed`)
        before = mode_of(area, terror, self.switched)
        self.switched = (area, not before.clear)
        was, then = ('full clear', 'goal') if before.clear else ('goal', 'full clear')
        closed = now - last - DOUBLE  # seconds its window had been closed at this look
        late = '' if closed <= DOUBLE else f', its window closed {closed:.2f} s before this look'
        LOG.info(
            'Macro: run: a double press of the pickup key (%.2f s apart%s): %s -> %s', last - first, late, was, then
        )
    if posted is not None and posted.agenda:
        mode = Mode(True, AGENDA, agenda=True)
    else:
        mode = mode_of(area, terror, self.switched)
    self.mode = mode
    if posted is not None and posted.leashed:
        line = said(mode, aim_of(self.bearings.script(area)))
        if self.mode_said != (area, line):
            self.mode_said = (area, line)
            LOG.info('Macro: run: %s', line)
            run.say(f'Run: {line}')
    return mode


def carry_on(self: Hunter, run: Run, left: Pursuit, onward: Pursuit) -> None:
    """The level run walked across its level's open passage and goes on as the run of the level it leads into
    (macros/pursuit.py `carried`; the player, 2026-10-15: "it should carry into the Chaos Sanctuary run"), said
    `Macro: run: on into <level>`. A full clear the player switched to on the level left holds on this one (a
    double-pressed full clear stays a full clear); a switch to the goal does not carry (the player, 2026-10-15),
    and with none the level's own rules decide (`run_mode`: a terror zone is a full clear). The pace of the level
    left is said, and the next level's counts anew."""
    assert left.area is not None
    assert onward.area is not None
    if self.switched is not None and self.switched[0] == left.area:
        self.switched = (onward.area, True) if self.switched[1] else None
    name, now = display_name(onward.area), run.clock()
    LOG.info('Macro: run: on into %s: the run of %s goes on across its way out', name, display_name(left.area))
    self.travel.paced(now, f'on into {name}')
    self.told.new(None)
    run.say(f'Run: on into {name}')


def nearby(self: Hunter, goal: Goal | None, here: Point) -> Goal | None:
    """Attack mode's own goal (no level run, no fresh press): a boss's fight only within ALONE_BOSS_UNITS, else
    none, said once a goal (the player, 2026-10-15: "only nearby")."""
    if goal is None or goal.do != FIGHT or not goal.known or goal.gap(here) <= ALONE_BOSS_UNITS:
        return goal
    if self.far_said != goal.label:
        self.far_said = goal.label
        LOG.info(
            'Macro: attack mode: %s is %.0f away from (%.1f, %.1f), beyond %.0f: not gone to without a press '
            '(KP_1 runs the level to it, KP_4 steps toward it)',
            goal.label, goal.gap(here), *here, ALONE_BOSS_UNITS,
        )  # fmt: skip
    return None
