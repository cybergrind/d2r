"""The level run's acts: the pursuit's moves, operating objects, the seek step, the jumps and steps, dead ends.
A part of macros/hunt.py `Hunter`, its methods bound there."""

import math
from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING

from inventory_tracking.combat.policy import RUN_MODES, observe
from inventory_tracking.combat.stance import CAMP_GAIN, CAMP_REACH, Camp, camp, no_footing
from inventory_tracking.combat.survival import pressure
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Monster, Teleport, World
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Level, Room, Target
from inventory_tracking.macros import route
from inventory_tracking.macros.actuator import Abort, Expired
from inventory_tracking.macros.build import Intent, NoWay
from inventory_tracking.macros.drinking import key_of, on_belt
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import PICK_UP, Goal
from inventory_tracking.macros.hunting import shrines
from inventory_tracking.macros.hunting.base import (
    BLOCK_SECONDS,
    BOSS_MARK_UNITS,
    DEAD_END_NEAR,
    DEAD_END_SECONDS,
    DECIDE_SECONDS,
    FRAME,
    MOO_MOO_FARM,
    NO_HOPS,
    OWN_TELEPORT_SECONDS,
    PAUSES,
    POLL,
    ROOM_UNITS,
    ROUTE_USE_TRIES,
    SAID_AGAIN,
    SIGHT,
    STALE_LOOK,
    STALE_MOVED,
    STUCK_SECONDS,
    STUCK_WINDOW,
    SWEEP_GAIN,
    SWEEP_UNITS,
    WALK_CLICKS,
    WALK_UNITS,
    Judged,
    act_window,
    threat,
)
from inventory_tracking.macros.pickup import Refused, pick_up
from inventory_tracking.macros.pursuit import PASSAGE, Defer, Ended, Hold, Move as Advance, Operate, Pursuit
from inventory_tracking.macros.routines import SUPER_UNIQUE_FLAG, take_battle_weapons
from inventory_tracking.macros.safety import WALK_ROUND, WAY_SHARE
from inventory_tracking.macros.sight import clear_shot, in_reach, in_reach as in_reach_of
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT, skill_name
from inventory_tracking.macros.teleport import (
    EXPIRED,
    MOVED,
    USES,
    Covered,
    entry_spot,
    ground_fraction,
    hop_toward,
    in_view,
    marked_thing,
    ready,
    scaled,
    use_thing,
    used_already,
    walk_into,
)
from inventory_tracking.macros.travel import (
    KEY_POLL,
    LOOPED,
    LOOPED_TELEPORT,
    PLAYER_STEP,
    PRESSED,
    SEEK,
    Point,
    Step,
    Untaken,
    attackable,
    facts_with,
    label,
    navigator,
    planning,
    spare_jump,
    step_walk,
)
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import FIGHT, STAND, USE
from inventory_tracking.terror.bosses import BOSSES


if TYPE_CHECKING:
    from inventory_tracking.macros.hunt import Hunter


# The route's `use` stage whose object shows used at its operate still waits what the object brings: the click before
# may have taken late. 00:45:48 on 2026-10-21: De Seis seal "did not take the click" (the walk began after
# STILL_SECONDS), the act expired, the seal opened (mode 1 at the character beside it), the next look said "At De Seis
# seal" and went on with no wait; De Seis came 0.9 s after the seal, behind the Teleports, and was never fought.
# Off: an object found used brings nothing, as before.
SETTLE_FOUND_USED = False  # off for the 2026-10-21 ~01:00 restart: no regression tests or wide suite yet


def found_used_settles(goal: Goal) -> bool:
    """Whether an object found used at `goal`'s operate is waited out as one just used (SETTLE_FOUND_USED): the
    route's `use` stage, noted done by this operate, so the wait comes once (no renewal at the same object)."""
    return SETTLE_FOUND_USED and goal.stage is not None and goal.stage.kind == USE


def dead_end(self: Hunter, spot: Point, now: float) -> None:
    """A move failed to reach `spot`: it is passed for DEAD_END_SECONDS (`barred`); a second within STUCK_WINDOW
    near it is stuck, and the loop's moves may take Teleport for STUCK_SECONDS (`looped_now`)."""
    again = any(math.dist(spot, at) <= DEAD_END_NEAR and until > now - STUCK_WINDOW for at, until in self.dead_ends)
    self.dead_ends = [*self.dead_ends[-20:], (spot, now + DEAD_END_SECONDS)]
    if again and self.looped is LOOPED:
        self.stuck_until = now + STUCK_SECONDS
        LOG.info('Macro: pursuit: stuck: (%.1f, %.1f) not reached again; Teleport allowed for %.0fs', *spot,
                 STUCK_SECONDS)  # fmt: skip


def looped_now(self: Hunter, now: float) -> Intent:
    """The loop's moves' intent: `looped`, or with the staff's Teleport while stuck (STUCK_SECONDS)."""
    return LOOPED_TELEPORT if self.looped is LOOPED and now < self.stuck_until else self.looped


def barred(self: Hunter, act, now: float) -> bool:
    """Whether `act` is a move to within DEAD_END_NEAR of a spot a move failed to reach DEAD_END_SECONDS ago."""
    if not isinstance(act, Advance) or act.dodge or act.reason.startswith('retreat'):
        return False
    if act.step.skill == TELEPORT and now < self.stuck_until:
        return False  # stuck: a Teleport crosses what the move that failed did not
    return any(until > now and math.dist(act.step.spot, spot) <= DEAD_END_NEAR for spot, until in self.dead_ends)


def pursue(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, key_names, *, in_reach: bool
) -> bool:
    """One look of the pursuit and its act (pursuit.py): a move, a use, or the hand-over to the route's step.
    Whether something was done (the loop then looks again). An act from a `stale` look is not made."""
    looked = run.clock()
    taken = self.yielded_act(run, world)
    if taken is not None:
        # The act the fight was let go for, as that look priced it (YIELD_TAKES): not judged again
        found, looked = taken
        LOG.info(
            'Macro: pursuit: the act the fight was let go for is made (%.2f s old): %s',
            run.clock() - looked, found.goal.label if found.goal is not None else type(found.act).__name__,
        )  # fmt: skip
        self.pursued = found.goal
    else:
        with self.way_time():
            found = self.judge(run, world, foes, ground, in_reach=in_reach)
    act, goal, posted, pressed = found.act, found.goal, found.posted, found.pressed
    running = posted is not None and posted.runs
    stamp = posted.pressed_at if posted is not None else -math.inf
    if self.pursuing and run.loot is not None:
        loot = run.loot()
        supply = on_belt(loot)
        kind = PotionType.REJUVENATION
        settings = self.build.settings
        # Recover the budget; the next look must see the healing before it allows a costlier act
        if (
            0 < loot.life < loot.max_life * settings.safety.floor / 100
            and loot.belt_read  # an unread cell may hold the healing potion
            and not supply[PotionType.HEALING]
            and supply[kind]
            and run.clock() - self.drinker.drunk_at.get(kind, -math.inf) >= settings.drink.rejuvenation_gap
            and not self.drinker.busy
            and not self.drinker.shift_down(run)
        ):
            key = key_of(loot, kind)
            if key is not None and self.drinker.take(run, key, kind, loot, pressure(self.drinker.readings)):
                self.tell(run, 'recovering the life budget; the next look decides the act')
                return True
    if isinstance(act, Hold):
        # A fight's cached yield from the last look must not release this strike again
        self.judged = (stamp, run.clock(), False)
        if act.reason:
            self.tell(run, act.reason)
        elif pressed:
            raised = '; pressed through: budget raised' if self.safety.decision.get('floor_raised') else ''
            self.tell(
                run,
                f'{goal.label if goal else "the goal"}: the least-time safe act is the fight{raised}',
                again=SAID_AGAIN,
            )
        return False
    if isinstance(act, Ended):
        self.end_run(run, act.reason, posted)
        return False
    if isinstance(act, NoWay):
        self.tell(run, act.reason, aloud=pressed or running)
        if act.reason.startswith('safety:'):
            self.nap(run, DECIDE_SECONDS)
            return True
        self.judged = (stamp, run.clock(), False)
        return False
    if isinstance(act, Defer):
        self.defer(run, goal, act.goal.label if act.goal is not None else 'the key', posted)
        return False
    if self.stale(run, world, looked, act):
        return True
    # The pointer held for the act, its mark re-based as it begins (`Actuator.held_act`)
    try:
        with run.actuator.held_act(), self.way_time():
            if isinstance(act, Advance):
                assert found.place is not None
                with self.priced_for(run, act_window(act.step)):
                    self.advance(run, world, ground, act, found.place, key_names)
                if WALK_ROUND and act.dodge and act.step.skill is None and (act.onward or self.safety.rounds):
                    # A walk across or round an act walked round (macros/safety.py WALK_ROUND): the next look is not
                    # put off to the walk's end, so the walk round goes on before the character stands
                    self.expired_motion = True
                if pressed and not running:
                    # The key moved the character: the sweep does not walk back (2026-10-11 00:49). A level run
                    # keeps its sweep for the fights on its way
                    self.sweep.end()
            else:
                with self.priced_for(run, self.build.settings.safety.operate_dwell):
                    self.operate(run, world, act.goal, key_names)
        self.told.new(None)
        self.refused = None
    except Abort as stop:
        if run.stops(stop):
            raise
        if isinstance(stop, Refused) and self.carry_one_swap(run, stop):
            return True  # carry-one: the Gheed's swap, not a try counted toward giving the charm up
        if isinstance(act, Advance) and 'did not move' in str(stop) and not isinstance(stop, Untaken):
            # Not tried again at once (rca/2026-10-16/loop-shack-stalls-findings.md §2). Not for `Untaken` (a
            # cooldown): barring its spot left no act priced (2026-10-17: 33 times in 198 games)
            self.dead_end(act.step.spot, run.clock())
        if isinstance(act, Operate) and act.goal.do == PICK_UP and act.goal.unit is not None:
            if len(self.drops.tried) > 200:
                self.drops.tried.clear()
            self.drops.tried[act.goal.unit] = str(stop)
        if isinstance(stop, Covered):
            self.blocked(run, stop.units)
        elif isinstance(act, Operate) and self.base is not None:
            self.missed = (self.base.label, run.clock() + BLOCK_SECONDS)  # tried again from nearer
        self.give_up(run, f'no {"move toward" if isinstance(act, Advance) else "use of"} {act.goal.label}: {stop}')
        self.nap(run, FRAME)
    return True


def way_time(self: Hunter):
    """The time limit for planning the far goal's way outside the safety's look (travel.py `planning`): the
    look's WAY_SHARE; none without a timer (the arena)."""
    timer = self.safety.timer
    if timer is None:
        return nullcontext()
    return planning(timer, timer() + self.build.settings.safety.look_seconds * WAY_SHARE)


def stale(self: Hunter, run: Run, world: World, looked: float, act) -> bool:
    """Whether the act of the look begun at `looked` is dropped: the look took over STALE_LOOK, so its game is
    old (rca/2026-10-14/run-2040-findings.md §1.2.3). A second slow look in a row with the character where it
    saw it is made: the host is slow, and a loop that drops every act moves nothing."""
    age = run.clock() - looked
    if age <= STALE_LOOK:
        self.dropped = 0
        return False
    player, now = world.player, run.world().player
    if player is None or now is None:
        return False
    moved = math.dist((player.x, player.y), (now.x, now.y))
    what = type(act).__name__
    if self.dropped and moved <= STALE_MOVED:
        LOG.info(
            'Macro: look: the act of a look %.2f s old is made (%s, %d dropped before it): the character stands '
            '%.1f units from where the look saw it',
            age, what, self.dropped, moved,
        )  # fmt: skip
        self.dropped = 0
        return False
    self.dropped += 1
    LOG.info(
        'Macro: look: the act of a look %.2f s old is dropped (%s, the character %.1f units from where the look '
        'saw it): looking again',
        age, what, moved,
    )  # fmt: skip
    return True


def give_up(self: Hunter, run: Run, reason: str) -> None:
    """Says an act given up for `reason` every time, with the count in a row (I1, I6: never silent;
    run-2110-findings.md M3)."""
    last = self.refused
    count = last[1] + 1 if last is not None and last[0] == reason else 1
    self.refused = (reason, count)
    self.tell(run, reason if count == 1 else f'{reason} (x{count})')


@contextmanager
def priced_for(self: Hunter, run: Run, seconds: float):
    """Bounds an act's hands to `seconds`: past them the next world poll raises Expired (their Abort cleanup
    unwinds) and the next look prices what happened. The previous observer is chained and restored."""
    if not self.pursuing or seconds <= 0:
        yield
        return
    until = run.clock() + seconds
    previous = run.observe

    def observed(world: World) -> None:
        if previous is not None:
            previous(world)
        if run.clock() >= until:
            self.expired_motion = world.player is not None and world.player.mode in RUN_MODES
            raise Expired(f'{EXPIRED}: look again before continuing')

    run.observe = observed
    try:
        yield
    finally:
        run.observe = previous


def advance(self: Hunter, run: Run, world: World, ground: Ground, act: Advance, place: Point, key_names) -> None:
    """Makes the navigator's move toward the goal. A casting delay about to end is waited out and the move
    priced again (`Travel.pause`); an empty staff in hand is swapped for the main weapons (`foot_step`)."""
    goal, step = act.goal, act.step
    if act.reason:
        self.tell(run, act.reason)
    player, rect = world.player, run.actuator.keys.focused_window_rect()
    assert player is not None
    if rect is None:
        raise Abort('no game window')
    aspect = rect[2] / rect[3]
    level = self.known_level(player)
    rooms = level.rooms if level is not None else ()
    wait = 0.0 if act.reason else self.travel.pause(run, world, ground, aspect, place, goal.spend, rooms)
    if wait > 0:
        # At least a frame: a sub-frame remainder would show the next look the same game frame
        run.pace.sleep(max(FRAME, wait))
        return  # the next look prices the new leg; never an unpriced replacement
    if not act.reason and step.skill is None and self.warp_ready(run, world, ground, aspect, place, goal, rooms):
        # The look priced a walk; the jump's delay is now within PLAN_AHEAD and the walk would hold the jump back
        # (2026-10-16 22:51: 17 of 41 walks between warps chosen 0.8-0.9 s after the warp)
        run.pace.sleep(FRAME)
        return  # the next look prices the jump
    if step.needs == 'battle' and not self.main_weapons(run, world, key_names):
        self.tell(run, 'waiting for the priced battle weapons')
        self.nap(run, POLL)
        return
    staff = self.worn(run)
    if staff is not None and staff.charges == 0 and staff.in_hand:
        run.keys.update(key_names(world, (SWAP_WEAPONS,)))
        take_battle_weapons(run)
    by = 'Walking' if step.skill is None else skill_name(step.skill)
    if goal.crossed and step.skill is None and step.spot == goal.place:
        # The walk across an open passage (pursuit.py `through`), said whether the safety priced it or not
        self.tell(run, f'{goal.label}: {PASSAGE}')
    here = (world.player.x, world.player.y) if world.player is not None else (player.x, player.y)
    if goal.crossed and step.skill is None and (door := door_across(world, here, place)) is not None:
        # A closed door across the walk: opened first, the walk priced again at the next look
        thing = next((t for t in (run.things() if run.things is not None else ()) if t.unit_id == door.unit_id), None)
        if thing is not None:
            mark = Target(player.area, (), (door.x / TILE_UNITS, door.y / TILE_UNITS), goal.label, 'target',
                          use=door.txt_id)  # fmt: skip
            use_thing(run, mark, world.player or player, thing, aspect)
            return
    LOG.info(
        'Macro: pursuit: %s toward %s at (%.1f, %.1f), %.0f away from (%.1f, %.1f): to (%.1f, %.1f) within %s',
        by, goal.label, *place, math.dist(here, place), *here, *step.spot, goal.spend.name,
    )  # fmt: skip
    if step.skill is not None and step.skill != TELEPORT:
        run.say(f'{by} toward {goal.label}')  # a walk and a Teleport hop say their own line
    self.travel.make(
        run, step, world, aspect, key_names, ground, name=goal.label, intent=goal.spend, goal=place, hurry=act.dodge
    )


DOOR_NEAR = 15.0  # world units: a closed door this near, across a passage's walk, is opened first (`door_across`)


def door_across(world: World, here: Point, place: Point) -> Door | None:
    """The nearest closed door within DOOR_NEAR of the character that stands across the straight walk to `place`."""
    found = []
    for door in world.doors:
        if not door.closed or math.dist(here, (door.x, door.y)) > DOOR_NEAR:
            continue
        steps = max(1, math.ceil(math.dist(here, place) / 0.5))
        if any(door.blocks((here[0] + (place[0] - here[0]) * i / steps, here[1] + (place[1] - here[1]) * i / steps))
               for i in range(steps + 1)):  # fmt: skip
            found.append(door)
    return min(found, key=lambda door: math.dist(here, (door.x, door.y))) if found else None


def warp_ready(
    self: Hunter,
    run: Run,
    world: World,
    ground: Ground,
    aspect: float,
    place: Point,
    goal: Goal,
    rooms: tuple[Room, ...],
) -> bool:
    """Whether the goal's way is now a jump whose casting delay ends within PLAN_AHEAD, where the look gave a
    walk."""
    player = world.player
    if player is None or not self.travel.warped_at > -math.inf:
        return False
    found = self.travel.toward(run, world, ground, aspect, place, goal.spend, rooms)
    if not isinstance(found, Step) or found.skill is None:
        return False
    return self.travel.left(found.skill, run.clock(), player.cooldown) > 0.0


def operate(self: Hunter, run: Run, world: World, goal: Goal, key_names) -> None:
    """At a goal reached: its object used and the route told (route.py `note_used`), a stand noted, a drop
    taken by the pickup step's hands."""
    player, rect = world.player, run.actuator.keys.focused_window_rect()
    assert player is not None
    bearings = self.bearings
    if goal.do == PICK_UP:
        LOG.info('Macro: pursuit: %s is taken first', goal.label)
        # The hands take the drop the goal names, the one the act was priced for (run-0025-findings.md §2.2)
        if goal.unit is not None and (self.running or goal.unit in self.restock_said):
            # A level run (and `restock`) tries one drop GATHER_TRIES times at most
            self.drops.gathered[goal.unit] = self.drops.gathered.get(goal.unit, 0) + 1
            pick_up(run, self.known_level(player), key_names, lambda: None, threat(run), unit=goal.unit)
        else:
            pick_up(run, self.known_level(player), key_names, lambda: None, unit=goal.unit)
    elif goal.shrine:
        shrines.use(self, run, world, goal)  # an Experience Shrine on the way (hunting/shrines.py, 2026-10-20)
    elif goal.do == USE and goal.mark is not None:
        if rect is None:
            raise Abort('no game window')
        if goal.stage is None and goal.unit is not None:  # a shack's container (`shack_goal`): its tries counted
            self.shack_tries[goal.unit] = self.shack_tries.get(goal.unit, 0) + 1
        thing = marked_thing(run, goal.mark)
        if thing is None and route.note_empty(run, goal.mark, bearings.progress, bearings.marks):
            return  # a chest that is gone: the next mark (rca/2026-10-16/loop-first-game-findings.md)
        if thing is None:
            raise Abort(USES[goal.mark.use].absent.format(goal.mark.label))
        if goal.stage is not None:
            if len(self.use_tries) > 200:
                self.use_tries.clear()  # units of games long left
            tries = self.use_tries[thing.unit_id] = self.use_tries.get(thing.unit_id, 0) + 1
            if tries > ROUTE_USE_TRIES and route.note_empty(
                run, goal.mark, bearings.progress, bearings.marks, f'not opened in {ROUTE_USE_TRIES} tries'
            ):
                return
        use_thing(run, goal.mark, player, thing, rect[2] / rect[3])
        # `thing` as read before: one used then brings nothing (45 s at an opened chest on 2026-10-20), unless it is
        # the route's `use` stage noted done now (SETTLE_FOUND_USED)
        if not used_already(USES[goal.mark.use], thing) or found_used_settles(goal):
            self.settled_at = run.clock() + USES[goal.mark.use].brings
        route.note_used(run, goal.mark, bearings.progress, bearings.marks)
    elif goal.do == STAND and goal.stage is not None and bearings.progress is not None:
        bearings.progress.stood(player.area, goal.stage.mark)
        run.say(f'{goal.route}: at {goal.stage.mark}')


def pursue_once(self: Hunter, run: Run, key_names, *, attacking: bool) -> Judged | None:
    """One press of the teleport key with nothing running: one pass of `pursue`'s decision with the press as
    its own; returns what was decided, the act made. `attacking`: attack mode is on or follows. None: the press
    is the route's own step's (pursuit off, the town, a goal that step performs); nothing done."""
    player, _ = ready(run)
    if not self.pursuing or player.in_town:
        return None
    world = run.world()
    level = self.known_level(player)
    ground = Ground(level.ground if level is not None else ())
    foes = self.foes(world, run.clock())
    here = (player.x, player.y)
    in_reach = any(in_reach_of(ground, here, (m.x, m.y), self.reach, world.doors) for m in foes)
    own = Pursuit('teleport', run.clock())
    with self.mailbox:
        saved, self.pursuit = self.pursuit, own
    try:
        found = self.judge(run, world, foes, ground, in_reach=in_reach, attacking=attacking)
        if isinstance(found.act, Hold) and not (found.goal is not None and found.goal.do == FIGHT):
            # A strike follows this press only for a fight (runner.py `pursues`)
            found = self.judge(run, world, foes, ground, in_reach=in_reach, attacking=False)
        if isinstance(found.act, Defer):
            return None
        run.in_time('the step')
        if isinstance(found.act, NoWay):
            self.told.new(None)  # a press with nothing working always says why it moved nothing
            self.tell(run, found.act.reason)
        elif isinstance(found.act, Advance):
            assert found.place is not None
            with self.priced_for(run, act_window(found.act.step)):
                self.advance(run, world, ground, found.act, found.place, key_names)
        elif isinstance(found.act, Operate):
            with self.priced_for(run, self.build.settings.safety.operate_dwell):
                self.operate(run, world, found.act.goal, key_names)
        return found
    finally:
        self.swap(own, saved)  # a press posted meanwhile stays for the mode


def known_level(self: Hunter, player) -> Level | None:
    level = self.level() if self.level is not None else None
    return level if level is not None and level.area == player.area else None


def seek(self: Hunter, run: Run, key_names, *, any_hostile: bool = False) -> None:
    """One seek step toward the nearest elite, or into the unexplored. `any_hostile` (the pickup request: a
    Terror Zone counts every kill and room): whichever is nearer, any known hostile or an unexplored room."""
    player, rect = ready(run)
    if player.in_town:
        raise Abort('in town: nothing to hunt')
    level = self.known_level(player)
    if level is None:
        raise Abort('no level map for this level yet (Win+C shows it)')
    ground = Ground(level.ground)
    here = (player.x, player.y)
    world = run.world()
    foes, doors = self.foes(world, run.clock()), world.doors
    leaders = [m for m in foes if m.leader]
    LOG.info(
        'Macro: seek: %d hostiles, %d elites, at (%.1f, %.1f); left %s, right %s',
        len(foes), len(leaders), *here, skill_name(player.left_skill), skill_name(player.right_skill),
    )  # fmt: skip
    # The blades' own reach: a step toward an elite already fought would break the fight off
    reach = self.reach
    near = [m for m in leaders if in_reach(ground, here, (m.x, m.y), reach, doors)]
    if near:
        run.say(f'{label(near[0])} is in reach: attack mode takes it')
        return
    quarry = self.quarry(level.area, here, foes, any_hostile)
    frontier = self.frontier(level, player, rect) if quarry is None or any_hostile else None
    # The hostile unless a room's worth further than the frontier
    far = frontier is not None and quarry is not None
    if far and math.dist(here, quarry[0]) > frontier[0] * TILE_UNITS + ROOM_UNITS:
        quarry = None
    if quarry is None:
        self.explore(run, level, player, rect, key_names, frontier)
        return
    spot, name = quarry
    self.go(run, level, ground, player, rect, spot, name, doors, key_names)


def go(self: Hunter, run: Run, level: Level, ground: Ground, player, rect, mob, name: str, doors, key_names) -> None:
    """A move onto the nearest spot with a shot at `mob`: a walk when near over clear ground, else a hop."""
    here = (player.x, player.y)
    target = self.firing_target(level, ground, here, mob, name, doors)
    goal = (target.point[0] * TILE_UNITS, target.point[1] * TILE_UNITS)
    if math.dist(here, goal) < MOVED:
        # Already on a firing spot: a click under the feet moves nothing and would stop the step
        run.say(f'{name} is in reach: attack mode takes it')
        return
    if math.dist(here, goal) <= WALK_UNITS and clear_shot(ground, here, goal, doors):
        step_walk(run, goal, player, rect[2] / rect[3], attackable(run.world()), name=name, clicks=WALK_CLICKS)
    elif not self.afoot(run, ground, player, rect, goal, name, key_names):
        hop_toward(run, target, player, rect, key_names)
    # A step that moved nothing is said, or the press looks dead
    now = run.world().player
    if now is not None and now.area == player.area and math.dist((now.x, now.y), here) < MOVED:
        LOG.warning(
            'Macro: the step toward %s moved nothing: at (%.1f, %.1f), the spot (%.1f, %.1f) %.1f away',
            name, *here, *goal, math.dist(here, goal),
        )  # fmt: skip
        run.say(f'No move toward {name}: {math.dist(here, goal):.0f} from its firing spot')


def own_teleport(self: Hunter, run: Run, now: float) -> bool:
    """Whether Teleport is the character's own skill (Enigma: game/memory.py `own_teleport`), cached for
    OWN_TELEPORT_SECONDS."""
    if self.own_read is None or now - self.own_read[1] > OWN_TELEPORT_SECONDS or now < self.own_read[1]:
        self.own_read = (bool(run.own_teleport is not None and run.own_teleport()), now)
    return self.own_read[0]


def worn(run: Run) -> Teleport | None:
    """The Teleport staff worn, with its charges; None without one."""
    return run.reads.teleport()


def afoot(self: Hunter, run: Run, ground: Ground, player, rect, goal: Point, name: str, key_names) -> bool:
    """A seek step that spares the staff: a stride toward `goal` within SEEK, a Blade Warp over a clear line
    (no charge, no swap; 2026-10-11: 78 of 106 seek hops had the line), or with few charges a walk. Whether it
    was made; False hands the step to a Teleport hop (teleport.py `hop_toward`), and with no charge and no
    stride it stops. With no Teleport at all the step is the class's own (`class_step`)."""
    staff = self.worn(run)
    left = None if staff is None else staff.charges
    low = left is not None and left < SEEK.walks_under
    if left == 0:
        take_battle_weapons(run)  # the staff is empty: nothing is cast with its set (`class_step`)
    world = run.world()
    aspect = rect[2] / rect[3]
    level = self.known_level(player)
    rooms = level.rooms if level is not None else ()
    if self.travel.means(run, world, ground, aspect, goal, PRESSED, rooms) in NO_HOPS:
        # No Teleport to spend: the class's own way, not a stride toward a hop's landing
        self.class_step(run, ground, goal, name, key_names, rooms)
        return True
    # A Blade Warp's delay is waited out on a clear line: presses (0.5 s) come faster than it (0.8 s)
    here = (player.x, player.y)
    wait = self.travel.wait(run, world, ground, aspect, here, goal, SEEK, staff)
    if wait > 0:
        run.pace.sleep(wait)
        world = run.world()
    found = self.travel.stride(run, world, ground, aspect, goal, SEEK)
    if found is not None and found.skill in (None, TELEPORT) and not low:
        return False  # a walk, or a Teleport of the stride's own: the hop plans a better one
    if found is None:
        if left is None or left:
            if low:
                LOG.info('Macro: %d charges left and no Blade Warp or walk leads toward %s: a hop', left, name)
            return False
        found = self.travel.around(run, world, ground, aspect, goal, SEEK)  # the walked way round the wall
        if found is None:
            raise Abort(f'the Teleport staff has no charges left, and no Blade Warp or walk leads toward {name}')
        LOG.info(
            'Macro: no straight way toward %s at (%.1f, %.1f) from (%.1f, %.1f): round the wall by (%.1f, %.1f)',
            name, *goal, *here, *found.spot,
        )  # fmt: skip
    by = 'Walking' if found.skill is None else skill_name(found.skill)
    run.say(f'{by} toward {name}' + (f': the Teleport staff has {left} charges left' if low else ''))
    self.travel.make(run, found, world, aspect, key_names, ground, name=name, intent=SEEK)
    return True


def boss_step(self: Hunter, run: Run, target: Target, key_names) -> bool:
    """The teleport step toward a boss's mark with the boss in sight and no shot at it from the mark: onto a
    firing spot at the boss itself, or stay with the shot already. Whether the step was taken here. (A boss
    stands up to 29 units off her map mark: the Countess, 56 visits, 2026-10-11.)"""
    if target.warp or target.kind != 'target':
        return False  # a door, a room to explore, a drop: only a handler's own mark (levels/handler.py `target`)
    player, rect = ready(run)
    world = run.world()
    level = self.known_level(player)
    if level is None or level.area != target.area:
        return False
    mark = (target.point[0] * TILE_UNITS, target.point[1] * TILE_UNITS)
    bosses = [
        m
        for m in self.foes(world, run.clock())
        if (m.txt_id in BOSSES or m.flags & SUPER_UNIQUE_FLAG) and math.dist(mark, (m.x, m.y)) <= BOSS_MARK_UNITS
    ]
    if not bosses:
        return False
    boss = min(bosses, key=lambda m: math.dist(mark, (m.x, m.y)))
    ground, at = Ground(level.ground), (boss.x, boss.y)
    if in_reach(ground, mark, at, self.reach, world.doors):
        return False  # the mark is a stand with a shot at it: the step goes there as ever
    here = (player.x, player.y)
    LOG.info(
        'Macro: no shot at %s from the mark of %s, %.0f from it: the step goes for the boss, %.0f away',
        label(boss), target.label, math.dist(mark, at), math.dist(here, at),
    )  # fmt: skip
    if in_reach(ground, here, at, self.reach, world.doors):
        run.say(f'{label(boss)} is in reach: attack mode takes it')
        return True
    self.go(run, level, ground, player, rect, at, label(boss), world.doors, key_names)
    return True


def warp_hop(self: Hunter, run: Run, target: Target, player, spot: Point, key_names) -> bool:
    """The teleport step's hop toward `spot` by the build's staff-sparing jump (`spare_jump`: Blade Warp),
    made only with few charges left and a clear line; whether it was made. Its delay is waited out; a wall or a
    failed warp leaves the hop to Teleport (False). An empty staff takes `foot_step` instead."""
    world = run.world()
    rect = run.actuator.keys.focused_window_rect()
    spare = spare_jump(self.build.movement, world.slots)
    if spare is None or world.player is None or rect is None or key_names is None:
        return False
    staff = self.worn(run)
    left = None if staff is None else staff.charges
    if left is not None and left < PLAYER_STEP.walks_under:
        # The staff empty: toward the target's own place, not a hop's landing (run-1932-findings.md §1.2.2)
        self.foot_step(run, target, key_names)
        return True
    # Only to spare the last charges (the player, 2026-10-11: "prefer tp for longer distances, until around 15
    # charges, then blade warp in priority")
    if left is None or left >= PLAYER_STEP.sparing:
        return False
    ground = Ground(target.ground)
    aspect = rect[2] / rect[3]
    here = (player.x, player.y)
    facts = facts_with(run, world, ground, aspect, self.travel, staff)
    failed = self.travel.jump_failed.get(spare.skill, -math.inf)
    # A jump recorded after now (a clock that went back) leaves the hop to Teleport too
    if facts.since_used(spare.skill) < 0 or run.clock() - failed < PLAYER_STEP.distrust:
        return False
    # One failed warp does not bar the skill from the step as from the sweep (2026-10-11: 44 of 447 failed)
    self.travel.jump_failed.pop(spare.skill, None)
    if spare.line and not clear_shot(ground, here, spot, world.doors):
        return False
    movement = navigator(self.travel.sets, facts)
    wait = 0.0 if movement is None else movement.wait(facts, spot, PLAYER_STEP)
    if wait > 0:
        run.pace.sleep(wait)
        world = run.world()
    found = self.travel.stride(run, world, ground, aspect, spot, PLAYER_STEP)
    if found is None or found.skill != spare.skill:
        return False
    run.say(f'{skill_name(spare.skill)} toward {target.label}: {left} charges kept')
    try:
        self.travel.make(run, found, world, aspect, key_names, ground, name=target.label, intent=PLAYER_STEP)
    except Abort as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: no %s toward %s (%s): the hop is a Teleport', skill_name(spare.skill), target.label, stop)
        return False
    return True


def class_step(
    self: Hunter, run: Run, ground: Ground, goal: Point, name: str, key_names, rooms: tuple[Room, ...] = ()
) -> bool:
    """One move toward a far goal by the class in hand (movement.py `Ways.means`; the player, 2026-10-14: "No TP:
    Blade Warp + walk, and we must use a route that is able to Blade Warp"), a casting delay worth it waited
    out first. False when already as near as a move brings it; no way raises Abort."""
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    aspect = rect[2] / rect[3]
    world = run.world()
    for _ in range(PAUSES):  # a delay read a tick short at the look after the sleep is slept out, not walked
        wait = self.travel.pause(run, world, ground, aspect, goal, PRESSED, rooms)
        if wait <= 0:
            break
        run.pace.sleep(max(wait, KEY_POLL))
        world = run.world()
    kind = self.travel.means(run, world, ground, aspect, goal, PRESSED, rooms) or 'the means in hand'
    found = self.travel.toward(run, world, ground, aspect, goal, PRESSED, rooms)
    player = world.player
    assert player is not None
    if isinstance(found, NoWay):
        if found.arrived:
            return False
        raise Abort(f'no way toward {name} by {kind}: {found.reason}')
    by = 'Walking' if found.skill is None else skill_name(found.skill)
    LOG.info(
        'Macro: navigation: %s toward %s at (%.1f, %.1f) from (%.1f, %.1f) by the class %s: to (%.1f, %.1f)',
        by.lower(), name, *goal, player.x, player.y, kind, *found.spot,
    )  # fmt: skip
    run.say(f'{by} toward {name}')
    self.travel.make(run, found, world, aspect, key_names, ground, name=name, intent=PRESSED, goal=goal)
    return True


def foot_step(self: Hunter, run: Run, target: Target, key_names) -> None:
    """The teleport step with the staff empty: one `class_step` toward the target's own place (a door's entry
    spot, else its mark); at a door it is clicked (`walk_into`), elsewhere said."""
    player, rect = ready(run)
    # An empty staff only costs resistances and skill levels (the player, 2026-10-13): the main weapons
    take_battle_weapons(run)
    entry = entry_spot(target)
    goal = scaled(entry) if entry is not None else (target.point[0] * TILE_UNITS, target.point[1] * TILE_UNITS)
    if self.class_step(run, Ground(target.ground), goal, target.label, key_names, target.rooms):
        return
    if target.warp:
        walk_into(run, target, player, rect[2] / rect[3])
        return
    run.say(f'At {target.label}')


def step(self: Hunter, run: Run, key_names) -> None:
    """The pickup request with nothing to pick up: with hostiles within SWEEP_UNITS it starts the sweep and
    moves nothing itself (the mode that follows takes the steps), else the seek step. Moving here fought the
    sweep's own walks (2026-10-11 01:13)."""
    player, _ = ready(run)
    world = run.world()
    here = (player.x, player.y)
    near = [m for m in self.foes(world, run.clock()) if math.dist(here, (m.x, m.y)) <= SWEEP_UNITS]
    if player.in_town or self.known_level(player) is None or not near:
        self.seek(run, key_names, any_hostile=True)
        return
    self.sweep.start(run.clock())
    LOG.info('Macro: step asked with %d hostiles near, from (%.1f, %.1f): the sweep takes it', len(near), *here)


def better_stand(
    self: Hunter,
    world: World,
    foes: list[Monster],
    ground: Ground,
    aspect: float,
    gain: float = CAMP_GAIN,
    run: Run | None = None,
    landed: bool = False,
) -> Camp | None:
    """The place worth going to (combat/stance.py `camp`) or None: in view, priced by the way there (`jumps`
    with `run`, else a walk). `landed`: casts land by distance and blades stop at walls; without, the sweep as
    its goldens were recorded."""
    player = world.player
    assert player is not None
    here = (player.x, player.y)
    near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT + CAMP_REACH]
    companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
    attack = self.attack
    seen = attack.sees(observe(player, near, companions, ground, world.doors), companions)
    jumps = () if run is None else self.travel.jumps(run, world)
    place = camp(
        seen,
        attack,
        no_footing(ground, world.doors),
        shown=lambda spot: in_view(ground_fraction(player, spot[0], spot[1], aspect)) and not self.sweep.shuns(spot),
        gain=gain,
        jumps=jumps,
        # Cows are fought from inside the herd (the player, 2026-10-12: "special tactics for some mob types
        # (cows/...)"); a `Tactic` later
        escape=0.0 if player.area == MOO_MOO_FARM else None,
        landed=landed,
        walls=landed,
    )
    if (
        place is not None
        and place.skill is not None
        and place.skill != TELEPORT
        and TELEPORT in world.slots
        and run is not None
    ):
        # Why a jump other than Teleport was chosen: the route's later log cannot tell which sources this look had
        staff = run.reads.teleport()
        own = run.reads.own_teleport()
        LOG.info(
            'Macro: firing stand jump source: chosen %d, offered %s, own Teleport %s, staff %s',
            place.skill,
            [jump.skill for jump in jumps],
            own,
            staff,
        )
    return place


def next_step(
    self: Hunter,
    run: Run,
    world: World,
    foes: list[Monster],
    ground: Ground,
    aspect: float,
    *,
    fighting: bool,
    priced: bool = False,
) -> Step | None:
    """The sweep's look for a move: `better_stand` (SWEEP_GAIN over here in a fight, else CAMP_GAIN), else with
    nothing in reach a stride toward the nearest hostile (`toward`). None: stay. `priced`: the safety prices
    the place (a level run's fight, `Safety.offer`), at CAMP_GAIN and `landed`."""
    self.sweep.forget(run.clock())
    gain = CAMP_GAIN if priced or not fighting else SWEEP_GAIN
    place = self.better_stand(world, foes, ground, aspect, gain, run, landed=priced)
    found = Step.to(place) if place is not None else None
    if found is None and not fighting and foes:
        found = self.toward(run, world, foes, ground, aspect)
    if found is not None and self.leaves(found.spot, run.clock()):
        return None
    return found
