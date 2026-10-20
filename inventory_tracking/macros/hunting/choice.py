"""The level run's goal: side drops, potions, the stand-by, chests, clearing the way, the agenda's targets,
passing and taking back. A part of macros/hunt.py `Hunter`, its methods bound there."""

import math
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from inventory_tracking.automation.priority import reserve
from inventory_tracking.common import LOG
from inventory_tracking.config import HEAL_PRIORITY
from inventory_tracking.game.layout import STRIKING_MODES
from inventory_tracking.game.records import (
    HEALING,
    REJUVENATION,
    VALUABLE,
    Drop,
    Loot,
    Monster,
    Thing,
    World,
    has_room,
)
from inventory_tracking.levels.model import UNIQUE_CHEST, Ground, Room, Target
from inventory_tracking.levels.presets import display_name
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros import lootpolicy, route, supply
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import (
    COVER,
    FULL_CLEAR,
    KILL,
    ON_THE_WAY,
    OPEN,
    PICKUP as SIDE,
    TRANSIT,
    ZONE_LEFT,
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
    PLACE_NEAR,
    REACH,
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
    ARRIVED_SECONDS,
    BLOCK_SECONDS,
    CLEAR_SECONDS,
    DECIDE_SECONDS,
    ENGAGE_STRIKERS,
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
from inventory_tracking.macros.hunting.throne import (
    GIVEN_UP,
    STAND_MARK,
    THRONE,
    THRONE_WAVES,
    seat_of,
    stand_of,
    wave_goal,
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
from inventory_tracking.macros.superchests import level_goal, mark_use, super_chests
from inventory_tracking.macros.supply import detour, low, worth
from inventory_tracking.macros.travel import PRESSED, STANDING, Point, clear_line, label, open_reaches, walked_length
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
    """What a level run takes on its way (pickup.py `choose`): a valuable within PICK_NEAR, gold within a jump, a
    potion the belt wants; not one given up (GATHER_TRIES). A valuable off the way hides nothing nearer. A wanted
    potion's guards are the fight first (goals.py `in_the_way`); one guarded BLOCK_SECONDS is left. Else `restock`,
    then `scarce`. `restocking`: attack mode's own look, the restock only."""
    if run.loot is None:
        return None
    now = run.clock()
    loot = unshunned(run.loot(), now)
    self.again(run, loot.drops, here, world)
    # Given-up drops leave the choice, said once each
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
        # Only potions while the run's boss is in reach: her death first (QUIET_BY_THE_BOSS,
        # rca/2026-10-18/andariel-cadence-findings.md §5 F3).
        loot = replace(loot, drops=tuple(found for found in loot.drops if found.kind in (HEALING, REJUVENATION)))
    plan = choose(loot, here)
    drop = plan.drop if plan is not None else None
    looped = self.pursuit is not None and self.pursuit.looped
    while drop is not None and drop.kind == VALUABLE and not self.on_the_way(run, here, drop, world, looped=looped):
        # Out of the choice, hiding nothing nearer (run-1932-findings.md issue 2)
        loot = replace(loot, drops=tuple(found for found in loot.drops if found.unit_id != drop.unit_id))
        plan = choose(loot, here)
        drop = plan.drop if plan is not None else None
    if drop is not None and drop.kind == VALUABLE and looped and not self.walked_near(run, here, drop, world):
        # The loop's far valuable hides no nearer wanted potion: that one first
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
    """A potion a low belt takes before the goal, in the quiet (no hostile within QUIET_UNITS; supply.py `low`,
    `restock`; the player, 2026-10-14; run-1932-findings.md issue 2). Said once a potion."""
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
    """The Gheed's swap backstop: a unique Grand Charm given up on with a Gheed's Fortune carried is the carry-one
    refusal (pickup.py `Refused`), whatever its tries ended as (2026-10-18 13:56:41). Asked once a drop; whether the
    swap starts (the run then ended)."""
    if self.carry_one is None or drop.kind != VALUABLE or drop.unit_id in self.drops.swap_asked:
        return False
    if not unique_grand_charm(drop) or not gheeds_carried(run):
        return False
    self.drops.first(self.drops.swap_asked, drop.unit_id)
    refused = Refused(drop, f"{drop.label} {why}, a Gheed's Fortune carried")
    return self.carry_one_swap(run, refused)


def carry_one_swap(self: Hunter, run: Run, refused: Refused) -> bool:
    """Whether the runner starts the Gheed's swap for `refused`; the level run then ends (runner.py `_run_over`)."""
    if self.carry_one is None or not self.carry_one(refused):
        return False
    self.end_run(run, f"{refused}: the Gheed's swap")
    return True


def forget_given_up(self: Hunter) -> None:
    """Every give-up forgotten (`DropLedger.forget`): the Gheed's swap's GHEED_STASH (runner.py)."""
    self.drops.forget()


def again(self: Hunter, run: Run, drops: Sequence[Drop], here: Point, world: World | None = None) -> None:
    """A given-up valuable is tried once more (once a drop) when the character comes within PICK_REACH of it on a
    clear line (rca/2026-10-14/run-1214-findings.md §3.2). What the player put down is never among `drops`
    (game/kept.py `PutDown`)."""
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
    """A healing potion beyond POTION_UNITS worth its detour (supply.py `worth`, `detour`) while the belt is below
    the reserve: the potions short at harm's price against the eta there and back. Judged once in 4 *
    DECIDE_SECONDS over the nearest two; the one found stays the goal until then."""
    if not loot.belt_read:
        return None  # unknown, not low: the next look reads it again
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


def stay_by(
    self: Hunter,
    run: Run,
    here: Point,
    *,
    wanted: bool = True,
    foes: Sequence[Monster] = (),
    world: World | None = None,
) -> Drop | None:
    """A wanted valuable within PICK_NEAR with no room for it: the run stands by it (goals.py `WAIT`; the player,
    2026-10-13: "when valuable doesn't fit: we need to stop near it"). Not equipment taken only because the filter
    shows it ("allow moving when the item isn't very valuable", 2026-10-12), but a shown unique or set item, yes
    (2026-10-14); not one a press went on from (`waived`). The card warns meanwhile. Not `wanted`: only the warning
    is taken back. Out of the KP_6 loop, while a trip could be made (`trips_by_hand`), the shared no-room routine
    (`no_room`: the cube, then a trip) stands by what a trip is made for too (lootpolicy.py `trip_for`; the player,
    2026-10-19: "EVERY loop and activity should have the same routines"); the cube is tried for the rest. The loop's
    stand is its stops' (runner.py `poll`)."""
    loot = unshunned(run.loot(), run.clock()) if run.loot is not None and wanted else None
    found = None
    quiet = all(math.dist(here, (m.x, m.y)) > QUIET_UNITS for m in foes)
    hand = loot is not None and self.trips_by_hand(run)
    if loot is not None:
        near = [d for d in loot.drops if d.kind == VALUABLE and math.dist(here, (d.x, d.y)) <= PICK_NEAR]
        roomless = [d for d in near if not has_room(loot.room, d.size) and d.unit_id not in self.waived]
        left = [
            d for d in near
            if lootpolicy.verdict(
                d, lootpolicy.RUN, room=has_room(loot.room, d.size), shown=d.unit_id in loot.shown,
                given_up=d.unit_id in self.waived,
            ).hold
            or (hand and d in roomless and lootpolicy.trip_for(d, shown=d.unit_id in loot.shown))
        ]  # fmt: skip
        found = min(left, key=lambda d: math.dist(here, (d.x, d.y))) if left else None
        if found is None and not self.looping() and roomless:
            # An identify candidate or shown gear the run goes on from: the cube still makes its room once
            other = min(roomless, key=lambda d: math.dist(here, (d.x, d.y)))
            self.no_room(run, world, other, loot, quiet=quiet, trip=False)
    if found is None or loot is None:
        if self.warned is not None:
            self.warned = None
            run.warn(None)
        return None
    if self.no_room(run, world, found, loot, quiet=quiet):
        if self.warned is not None:
            self.warned = None
            run.warn(None)
        return None
    if self.warned != found.unit_id:
        self.warned = found.unit_id
        cube = loot.cube is not None and has_room(loot.cube, found.size)
        told = ' (the cube has room for it)' if cube else ''
        LOG.info(
            'Macro: pursuit: the inventory has no room for %s at (%.0f, %.0f), %.0f away: the run stands by it%s',
            found.label, found.x, found.y, math.dist(here, (found.x, found.y)), told,
        )  # fmt: skip
        run.stand_by(f'Inventory full: {found.label} here — make room{told}')
    return found


def trips_by_hand(self: Hunter, run: Run) -> bool:
    """Whether the hunt by hand holds what the shared no-room routine makes a trip for (lootpolicy.py `trip_for`):
    the KP_6 loop off, mouse mode, and a trip possible in this game (the runner's `can_trip`). Without one the sites'
    own rules stand: shown gear and plain valuables are gone on from, as the player ruled when no trip followed a
    stand (2026-10-12: "allow moving when the item isn't very valuable"; 2026-10-18: "moved on from by hand")."""
    return not self.looping() and run.pad is None and self.can_trip is not None and self.can_trip()


def no_room(
    self: Hunter, run: Run, world: World | None, found: Drop, loot: Loot, *, quiet: bool, trip: bool = True
) -> bool:
    """The shared no-room routine's first steps for `found`, a valuable with no inventory room (macros/running/room.py),
    only in the quiet: the cube once a drop (`room_maker`: the loop's items by the protected cells, never the
    player's; "if we have cube space - we should move items there", the player, 2026-10-17), then, with the cube tried
    or full and `trip`, the trip's ask (`room_trip`: an activity by hand; it cancels the run when due). Whether room
    was made in the cube: the next look takes it."""
    if not quiet:
        return False
    cube = loot.cube is not None and has_room(loot.cube, found.size)
    if (cube or loot.cube is None) and self.room_maker is not None and self.room_tried != found.unit_id:
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
            return True
    tried = self.room_tried == found.unit_id or not (cube or loot.cube is None)
    if trip and tried and self.room_trip is not None:
        self.room_trip(run, found, world if world is not None else run.world(), loot)
    return False


def shack_goal(self: Hunter, run: Run, world: World, player, route: str) -> Goal | None:
    """On the KP_6 loop, a closed container in sight beside one of the camp's chests (shacks.py;
    routes/lower-kurast-loop-plan.md phase 6c), a side goal of `route`; left after SHACK_TRIES."""
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
    """A full clear's nearest closed super chest within SUPER_NEAR; left after SUPER_TRIES."""
    if run.things is None:
        return None
    chests = [
        thing
        for thing in super_chests(run.things(), rooms)  # the glowing ones and the unique-chest spots' (superchests.py)
        if thing.mode == 0
        and thing.selectable is not False
        and self.shack_tries.get(thing.unit_id, 0) < SUPER_TRIES
        and math.dist(here, (thing.x, thing.y)) <= SUPER_NEAR
        and passing_key((thing.x, thing.y), thing.unit_id, rooms) not in self.passed
    ]
    if not chests:
        return None
    thing = min(chests, key=lambda t: math.dist(here, (t.x, t.y)))
    place = (thing.x / TILE_UNITS, thing.y / TILE_UNITS)
    mark = Target(player.area, (), place, 'Super chest', 'target', use=mark_use(thing))
    return Goal('full clear: Super chest', (thing.x, thing.y), USE, USE_NEAR, spend, unit=thing.unit_id, mark=mark,
                route=route, clearing=True)  # fmt: skip


def at_hand(self: Hunter, found: Goal | None, player, world: World) -> bool:
    """Whether the route's `found` is a chest opened from where the character stands: then before the shack's
    container (rca/2026-10-17/slow-legs-findings.md)."""
    level = self.known_level(player)
    if found is None or found.do != USE or level is None:
        return False
    return open_reaches(Ground(level.ground), world.doors, (player.x, player.y), found.place, OPEN_NEAR)


def blockers(self: Hunter, goal: Goal | None, foes: Sequence[Monster], now: float) -> list[Monster]:
    """Living hostiles the hands found in the way of `goal`'s act (`Covered`), for BLOCK_SECONDS."""
    blocking = self.blocking
    if blocking is None or goal is None:
        return []
    label, units, until = blocking
    found = [m for m in foes if m.unit_id in units]
    if label != goal.label or now > until or not found:
        self.blocking = None
        return []
    return found


UNEXPLORED = 'an unexplored room'  # what a tour stop is called (`next_room`, `elsewhere`)


def goal(
    self: Hunter, run: Run, world: World, foes: list[Monster], pressed: bool, posted: Pursuit | None
) -> Goal | None:
    """The goal the key means now (goals.py `goal_of`) from the route's stage, the card, the hostiles and memory.
    A press takes a valuable beside the character first (pickup.py `worth_a_stop`, once a press); a level run its
    side drop. Hostiles barring the act make their fight the goal (`first_fight`). `posted`: the mailbox as read."""
    player = world.player
    assert player is not None
    here, area, bearings = (player.x, player.y), player.area, self.bearings
    running = posted is not None and posted.runs
    staged = route.staged(bearings.progress, area)
    card = bearings.card() if bearings.card is not None else None
    if card is not None and card.area != area:
        card = None  # the card is still the level just left
    if (
        card is not None
        and staged is None
        and posted is not None
        and posted.agenda
        and not (pressed and posted.advance)
    ):
        # A terror zone run with no route stage here (a pending red portal, a `clear`): the card's first mark is
        # another level's door, no goal of the zone's (21:05:44 on 2026-10-19: "Ancients' Way" on the Frozen
        # Tundra; rca/2026-10-19/tz-coverage-findings.md F2). The player's own teleport press keeps it.
        card = None
    drop = side = stay = None
    if pressed and posted is not None and posted.advance:
        if self.stopped_for[0] != posted.pressed_at:
            self.stopped_for = (posted.pressed_at, worth_a_stop(run))
        drop = self.stopped_for[1]
    elif running:
        side = self.side_drop(run, here, foes, world)
        stay = self.stay_by(run, here, wanted=side is None, foes=foes, world=world)
    elif self.pursuing and not pressed:
        # Attack mode's own goal: a restock potion first
        side = self.side_drop(run, here, foes, world, restocking=True)
    known = self.remembered(area) if self.remembered is not None else []
    live = {m.unit_id for m in foes}
    self.vanished |= {unit for unit, x, y, _ in known if unit not in live and math.dist(here, (x, y)) <= VANISH_UNITS}

    def elsewhere() -> tuple[Point, str] | None:
        # Nothing known of the boss: the nearest hostile known, else the nearest unexplored room (as seek does).
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
        # The KP_6 loop: a shack's container in sight first
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
        # Every hostile, the `untouchable` too: a boss the strikes did nothing to is still where the fight is.
        foes=hostiles(world),
        remembered=known,
        supers=bearings.supers(area) if bearings.supers is not None else (),
        gone=frozenset(self.vanished | set(self.untouchable)),
        # Only a press or a level run seeks an unknown boss (a potential over the whole level).
        elsewhere=elsewhere if pressed or running else None,
        entry=door_entry(card),
        drop=drop,
        side=side,
        stay=stay,
    )
    if (
        found is not None
        and staged is not None
        and staged[1].mark
        and found.stage is None
        and found.mark is not None
        and found.mark.label != staged[1].mark
        and posted is not None
        and posted.agenda
        and not (pressed and posted.advance)
    ):
        # A terror zone run whose stage's way out is not on the card yet: the card's first mark is another level's
        # door (01:01:26 on 2026-10-20, Lost City: "at Ancient Tunnels (Valley of Snakes is not marked yet)" again
        # and again, the game left). The nearest unexplored room instead, where the way out comes in sight
        level, rect = self.known_level(player), run.actuator.keys.focused_window_rect()
        frontier = self.frontier(level, player, rect) if level is not None and rect is not None else None
        if frontier is None:
            found = None
        else:
            _, _, (x, y) = frontier
            place = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS)
            label = f'seek {staged[1].mark} (not marked yet): an unexplored room'
            found = Goal(label, place, REACH, PLACE_NEAR, found.spend, known=False, route=staged[0], clearing=True)
    if (
        THRONE_WAVES
        and area == THRONE
        and staged is not None
        and posted is not None
        and posted.agenda
        and (found is None or found.stage == staged[1])
        and (world.game_name, area, staged[1].boss) not in self.marks_empty
    ):
        # The Throne's waves, then the portal (the player, 2026-10-20 ~09:33: "tz leveling should do baal and trone
        # fight"; hunting/throne.py)
        found = throne_goal(self, run, world, here, staged, found)
    if (
        found is not None
        and found.do == FIGHT
        and found.unit is None
        and found.stage is not None
        and (world.game_name, area, found.stage.boss) in self.marks_empty
    ):
        found = None  # its boss was not by its place (judging.py `empty_mark`): the level is explored or the run ends
    if opens is not None and not self.at_hand(found, player, world):
        found = opens
    missed = self.missed
    if found is not None and missed is not None and missed[0] == found.label and run.clock() <= missed[1]:
        found = nearer(found)  # its act missed from there: from nearer now
    if found is not None and found.do == FIGHT and found.unit in self.nearing:
        # strikes did nothing from there: fight from within the engage ring
        found = replace(found, near=min(found.near, self.attack.engage))
    self.base = found
    barring = self.blockers(found, foes, run.clock())
    if found is not None and running and (not self.pursuing or found.guarded):
        # The run's own move: what stands where the act is made is fought first (a pack on a seal, a potion's
        # guards); a press is never refused so (architecture §1).
        known = {m.unit_id for m in barring}
        barring += [m for m in in_the_way(found, foes, here) if m.unit_id not in known]
    return first_fight(found, here, barring, self.reach) if found is not None and barring else found


def throne_goal(self: Hunter, run: Run, world: World, here: Point, staged, found: Goal | None) -> Goal | None:
    """The Throne's goal for the route's stage `staged` (route, stage) from goal_of's `found` (hunting/throne.py
    `wave_goal`): the hall, the stand, the wait for Baal to leave, the portal. A wait that ends with no wave leaves
    the stage as an empty mark does (judging.py `empty_mark`): the level is explored, then the run ends."""
    route_name, stage = staged
    marks = self.bearings.marks(STAND_MARK) if self.bearings.marks is not None else ()
    seat = seat_of(world.monsters)
    now = run.clock()
    self.waves.begin(world.game_name)
    found_now = wave_goal(
        self.waves,
        area=THRONE,
        stage=stage,
        route=route_name,
        found=found,
        here=here,
        hostiles=hostiles(world),
        seat=seat,
        stand=stand_of([(x * TILE_UNITS, y * TILE_UNITS) for x, y in marks], seat),
        reach=self.reach,
        spend=found.spend if found is not None else PRESSED,
        now=now,
        passed=lambda m: m.unit_id in self.passed,
    )
    if found_now is GIVEN_UP:
        if len(self.marks_empty) > 200:
            self.marks_empty.clear()
        self.marks_empty.add((world.game_name, THRONE, stage.boss))
        self.wayless.add((world.game_name, THRONE))
        return None
    assert found_now is None or isinstance(found_now, Goal)
    return found_now


def cleared(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, found: Goal | None
) -> Goal | None:
    """A level run's goal by its mode (runmode.py; the player, 2026-10-14): the hostiles on the way (goals.py
    `clear_way`), on a full clear the rest of the level (`rest_of_level`), then the route's `found`. A fight, drop
    or stand-by of `found`'s is kept. Out of a full clear only a way through (WAYS) is cleared, not the way to an
    object: a seal calls its pack (fighting Vizier seal 1's pack first left the Vizier alive in ten arena plays).
    A goal with no strike or progress for CLEAR_SECONDS is passed (`goes_on`); see `taken_back`."""
    mode = self.mode
    if mode is not None and mode.agenda and self.agenda is not None:
        return self.agenda_cleared(run, world, foes, ground, found)
    clear = mode is not None and mode.clear
    if found is not None and (found.do in (PICK_UP, WAIT, FIGHT) or found.guarded):
        return found
    # Nor on the KP_6 loop's rushed run: "don't fight what isn't attacking" (the player, 2026-10-16;
    # rca/2026-10-18/freeze-near-mobs-findings.md)
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
    """`candidate`'s goal (`taken_back`); one passed now (`goes_on`) yields to the next, at most three times."""
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
    """The terror zone kinds' run (goals-plan.md §3): the agenda's next target (agenda.py `Agenda.in_level`), then
    the route's `found`; passing and the way cleared as a full clear's (leaders only, unless a Full clear TZ). A
    drop's guards are the fight first ("we may need some kill action near pickup item, then pickup")."""
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
        # `clearing`: on a level with no route a plain fight goal ended the run (Great Marsh, 2026-10-19 09:01:51)
        return replace(first_fight(found, here, [guard], self.reach), clearing=True)
    spend = found.spend if found is not None else PRESSED
    policy = self.agenda_policy(area) if self.agenda_policy is not None else None
    if policy == ZONE_LEFT:
        if self.zone_left != (world.game_name, area):
            self.zone_left = (world.game_name, area)
            LOG.info('Macro: run: %s is no longer terrorized: the level run ends', display_name(area))
        return None
    everyone, crossed = policy == FULL_CLEAR, policy == TRANSIT
    things = run.things() if run.things is not None else ()  # read once a look

    # The route's next object on this level (a seal, a chest; not a portal): beside the character it goes before a
    # farther room (agenda.py USE_FIRST)
    use_at = (
        found.place
        if found is not None
        and found.do == USE
        and found.stage is not None
        and found.stage.kind == USE
        and not found.stage.to
        and not found.stage.pending
        and not (found.mark is not None and found.mark.warp)
        else None
    )

    def candidate(skip: frozenset[object]) -> Goal | None:
        target = self.agenda_target(run, world, foes, here, skip, rooms, None, things, use_at)
        if target is None:
            # The level's super chests before the route's own goal, a crossed level's left (superchests.py LEVEL_SPOTS)
            base = (None if crossed else level_chest(self, run, world, rooms, things, skip, found, spend)) or found
        elif target.kind == OPEN:
            base = self.agenda_chest(area, target, found, spend, things)
        else:
            unit = target.unit if target.kind == KILL else None
            assert target.place is not None
            base = rest_of_level((target.place, target.label, unit), found, self.reach, spend)
        if base is None or (base is found and found is not None and found.do == FIGHT):
            return base
        # A level only crossed (TRANSIT) fights nothing on its way but what strikes at the party
        near = (
            []
            if crossed
            else self._on_the_way(world, ground, foes, here, skip, lambda m: bool(everyone or m.leader or m.tier))
        )
        if not near and (ENGAGE_STRIKERS or crossed):
            # What strikes at the party is met, not waited for (ENGAGE_STRIKERS)
            near = self._on_the_way(world, ground, foes, here, skip, lambda m: m.mode in STRIKING_MODES)
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
    use_at: Point | None = None,
) -> Objective | None:
    """The agenda's next target on this level (agenda.py `Agenda.in_level`) from what this look knows: leaders,
    hostiles, omens, the side drop, super chests, the next unexplored room (lazily), the goals passed, the route's
    next object (`use_at`)."""
    agenda, player = self.agenda, world.player
    assert agenda is not None
    assert player is not None
    area, now = player.area, run.clock()
    policy = self.agenda_policy(area) if self.agenda_policy is not None else FULL_CLEAR
    if policy == ON_THE_WAY and (world.game_name, area) in self.wayless:
        policy = COVER  # no way to the route's goal: the rooms are explored for it (`judge`)
    everyone = policy == FULL_CLEAR
    out = skip | set(self.passed)

    def here_on(x: float, y: float) -> bool:
        # A leader of this level only: the client holds the level before's for a moment after a crossing, and a River
        # of Flame elite chased from the Chaos Sanctuary's side took the run back across before its map was read
        # (08:43:48 on 2026-10-20, rca/2026-10-20/crossing-teleport-back-findings.md F1). No rooms read: none
        return room_at(rooms, (x / TILE_UNITS, y / TILE_UNITS)) is not None

    live = [m for m in foes if (everyone or m.leader or m.tier) and here_on(m.x, m.y)]
    leaders = [Leader(m.unit_id, (m.x, m.y), label(m), bool(m.tier and m.leader)) for m in live]
    seen = {m.unit_id for m in foes}
    gone = seen | self.vanished | set(self.untouchable)
    known = self.remembered(area) if self.remembered is not None else []
    leaders += [
        Leader(unit, (x, y), 'the remembered monster', live=False)
        for unit, x, y, leader in known
        if unit not in gone and (everyone or leader) and here_on(x, y)
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
        *self.agenda_chests(things, rooms),
        use_at=use_at,
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


def level_chest(
    self: Hunter,
    run: Run,
    world: World,
    rooms: Sequence[Room],
    things: Sequence[Thing],
    skip: frozenset[object],
    found: Goal | None,
    spend: Intent,
) -> Goal | None:
    """The level's next super chest or chest spot (superchests.py `level_goal`), its tries and passes the run's."""
    player = world.player
    assert player is not None
    out = skip | set(self.passed)
    return level_goal(
        world.game_name, player.area, (player.x, player.y), rooms, things, self.shack_tries,
        lambda place, unit: passing_key(place, unit, rooms) in out or (unit is not None and unit in out),
        run.clock(), spend, found.route if found is not None else '',
    )  # fmt: skip


def agenda_chests(
    self: Hunter, things: Sequence[Thing], rooms: Sequence[Room] = ()
) -> tuple[tuple[tuple[int, Point], ...], frozenset[int]]:
    """Super chests among `things` for the agenda's CHEST tier ("open them along the way", the player, 2026-10-19):
    (closed (unit, place)s, units open or tried SUPER_TRIES times). The glowing ones and, on `rooms`, the chests at
    the unique-chest spots (superchests.py: the Maggot Lair's, "we need to open superchests when we encountering
    them", the player, 2026-10-20)."""
    closed, spent = [], set()
    for thing in super_chests(things, rooms):
        if thing.mode != 0 or self.shack_tries.get(thing.unit_id, 0) >= SUPER_TRIES:
            spent.add(thing.unit_id)
        elif thing.selectable is not False:
            closed.append((thing.unit_id, (thing.x, thing.y)))
    # Tried out though out of sight: a goal's unit the client has since named anew is left all the same
    spent.update(unit for unit, tries in self.shack_tries.items() if tries >= SUPER_TRIES)
    return tuple(closed), frozenset(spent)


def agenda_chest(
    self: Hunter, area: int, target: Objective, found: Goal | None, spend: Intent, things: Sequence[Thing] = ()
) -> Goal:
    """The agenda's OPEN `target` as a clearing goal, opened as `super_chest_goal`'s; `found`'s route kept for the
    log. `things`: this look's objects, the chest's class among them (superchests.py `mark_use`)."""
    assert target.place is not None
    x, y = target.place
    use = mark_use(next((thing for thing in things if thing.unit_id == target.unit), None))
    mark = Target(area, (), (x / TILE_UNITS, y / TILE_UNITS), 'Super chest', 'target', use=use)
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
    """The run's next goal, unless it is a clearing goal left for another within TAKE_BACK that would still be the
    goal without it: then that other. The other gone, the goal left is taken back."""
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
    """Note this look's goal: the last look's clearing goal is left for this one (TAKE_BACK) unless passed. The
    route's own goal is never left so."""
    key = self.goal_key(chosen, rooms)
    went, self.went = self.went, key
    if went is None or chosen is None or not chosen.clearing or went == key or went in self.passed:
        return
    if isinstance(went, tuple) and went[:1] == ('the run',):
        return  # the route's own goal: what the run is for
    if len(self.left_for) > 200:
        self.left_for.clear()
    self.left_for[went] = (now + TAKE_BACK, key)


def goes_on(
    self: Hunter, run: Run, world: World, ground: Ground, goal: Goal, rooms: Sequence[Room], now: float
) -> bool:
    """Whether a clearing goal is still gone for: False (and passed) after CLEAR_SECONDS with no strike and no eta
    progress of PROGRESS_SECONDS, ARRIVED_SECONDS once a place goal is reached. The eta is asked once in PROGRESS_LOOK
    and before a pass (a cold field is costly: rca/2026-10-14/run-2040-findings.md)."""
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
    player = world.player
    # A room's stop stood at with nothing struck shows nothing more: ARRIVED_SECONDS, not CLEAR_SECONDS (10 s by
    # hostiles at 21:05:24 and 22:00:32 on 2026-10-19; rca/2026-10-19/tz-leveling-findings.md C1)
    # Not a Herald's stand, which is waited at
    at = goal.label.endswith(UNEXPLORED) and player is not None and goal.gap((player.x, player.y)) <= goal.near
    if judging.idle <= (ARRIVED_SECONDS if at else CLEAR_SECONDS):
        return True
    why = (
        f'stood at it {ARRIVED_SECONDS:.0f} s with no strike'
        if at
        else f'no strike and no progress by the way in {CLEAR_SECONDS:.0f} s on the way to it'
    )
    self.pass_by(goal, why, now, rooms)
    return False


def on_the_way(self: Hunter, run: Run, here: Point, drop: Drop, world: World | None, *, looped: bool = False) -> bool:
    """Whether a valuable is on the way: PICK_NEAR walked, not straight (straight made the run warp back and forth:
    rca/2026-10-14/run-1932-findings.md §1.2.3). `looped`: the KP_6 loop also takes what Teleport brings it to."""
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
    """Whether the way to `drop` is Teleport hops within LOOP_PICK_SECONDS (a Ko Rune 117 walked was left,
    2026-10-18 18:22:17). Judged once in FAR_JUDGED a drop, said on change."""
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
    self.rest = None  # the tour's next stop is looked for again (`next_room`)
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
    """A full clear's next (place, what, unit): a Herald, an omen's pack or stand, the nearest hostile in sight, the
    nearest remembered alive, the next unexplored room (unit None), the rest remembered. None: clear as far as
    known. Passed goals and `skip` (`passing_key`s) are not gone for."""
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
        x, y, unit = min(kept, key=lambda k: math.dist(here, (k[0], k[1])))
        return (x, y), 'the remembered monster', unit
    return None


def next_room(self: Hunter, run: Run, player, area: int, now: float) -> tuple[Point, str, int | None] | None:
    """The first stop of the tour of the rooms not explored yet (`frontier`) that is not passed, looked for once in
    REST_SECONDS (a pass looks again, `pass_by`)."""
    cached = self.rest
    if cached is not None and cached[1] == area and now - cached[0] < REST_SECONDS:
        room = cached[2]
    else:
        level, rect = self.known_level(player), run.actuator.keys.focused_window_rect()
        rooms = level.rooms if level is not None else ()

        def passed(place: Point) -> bool:
            return passing_key(place, None, rooms) in self.passed

        kept = self.stop_kept[1] if self.stop_kept is not None and self.stop_kept[0] == area else None
        stop = self.frontier(level, player, rect, passed, kept) if level is not None and rect is not None else None
        room = None
        self.stop_kept = None
        if stop is not None:
            _, chosen, (x, y) = stop
            room = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS), 'an unexplored room', None
            self.stop_kept = (area, (chosen.x, chosen.y, chosen.width, chosen.height))
        # None is not kept: a look with no stop (no window, the card not up) ended the run on the next looks
        # (rca/2026-10-19/tz-coverage-findings.md item 5)
        self.rest = (now, area, room) if room is not None else None
    return room


def run_mode(self: Hunter, run: Run, area: int, posted: Pursuit | None) -> Mode:
    """The run mode on `area` (runmode.py): a closed double press of the pickup key switches it for this level; a
    switch on another level lapses. Said on change."""
    now = run.clock()
    if self.switched is not None and self.switched[0] != area:
        self.switched = None
    with self.mailbox:
        pairs, self.taps = doubles(self.taps, now)
    # No TZ full clear on KP_6 loops: "focus on reaching chests as fast as possible" (the player, 2026-10-16);
    # "andy loop shouldn't focus on full clearing level. we're going to have separate mods" (2026-10-19)
    terror = self.bearings.terror(area) and not (posted is not None and (posted.rush or posted.looped))
    for first, last in pairs:
        # Every double press, also one no look saw in its window (runmode.py `owed`)
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
    """The run walked across an open passage and goes on as the next level's ("it should carry into the Chaos
    Sanctuary run", the player, 2026-10-15). A switched-to full clear carries; a switch to the goal does not. The
    left level's pace is said, the next counts anew."""
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
    """Attack mode's own goal: a boss's fight only within ALONE_BOSS_UNITS ("only nearby", the player,
    2026-10-15), said once a goal."""
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
