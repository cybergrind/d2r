"""The level run's acts: the pursuit's moves, operating objects, the seek step, the jumps and steps, dead ends.
A part of macros/hunt.py `Hunter`, its methods bound there."""

import math
from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING

from inventory_tracking.combat.policy import RUN_MODES, observe
from inventory_tracking.combat.stance import CAMP_GAIN, CAMP_REACH, Camp, camp, no_footing
from inventory_tracking.combat.survival import pressure
from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground, Level, Room, Target
from inventory_tracking.macros import route
from inventory_tracking.macros.actuator import Abort, Expired
from inventory_tracking.macros.build import Intent, NoWay
from inventory_tracking.macros.drinking import key_of, on_belt
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.game.layout import NO_OWNER
from inventory_tracking.macros.game.records import Monster, Teleport, World
from inventory_tracking.macros.goals import PICK_UP, Goal
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
from inventory_tracking.macros.safety import WAY_SHARE
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
    """One look of the pursuit and its act (macros/pursuit.py): a move toward the goal, what is done
    at it, the hand-over to the route's own step; whether something was done (the loop then looks at
    the game again). A hold or a reason said leaves the loop to what it did before. A move or a use decided from
    a look that took too long is not made (`stale`): the loop looks again."""
    looked = run.clock()
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
        # Budget recovery, not borrowed future life: the next look must see
        # the healing before it can authorize a formerly unaffordable act.
        if (
            0 < loot.life < loot.max_life * settings.safety.floor / 100
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
        # A fight may have yielded on the previous look. Its cached request
        # must not immediately release this newly authorized strike again.
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
    # The pointer held as a step holds it (the mode itself aims once and casts at once), its mark re-based
    # as the act begins: a hand that moved the mouse before the act stops nothing (`Actuator.held_act`).
    try:
        with run.actuator.held_act(), self.way_time():
            if isinstance(act, Advance):
                assert found.place is not None
                with self.priced_for(run, act_window(act.step)):
                    self.advance(run, world, ground, act, found.place, key_names)
                if pressed and not running:
                    # The key took the character somewhere: no step of the sweep's back to what it left
                    # (Tower Cellar 3, 00:49 on 2026-10-11). A press that moved nothing ends no sweep.
                    # A level run keeps its sweep for the fights on its way (its own moves are the run's).
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
            # Not tried again at once: 22:04:12 on 2026-10-16 made one walk 16 times in 17 s, each "did not move"
            # (rca/2026-10-16/loop-shack-stalls-findings.md §2). Not a key the game took no cast for (`Untaken`,
            # its cooldown): the way is not distrusted, and barring its spot left no act priced for DEAD_END_SECONDS
            # (33 times in 198 games on 2026-10-17, 4.0-4.8 s each: "safety: no act was priced")
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
    """The block the far goal's way is asked for in by the loop outside the safety's own look (travel.py
    `planning`): the look's share of its time (macros/safety.py WAY_SHARE) from now by the look's clock; none
    without one (the arena)."""
    timer = self.safety.timer
    if timer is None:
        return nullcontext()
    return planning(timer, timer() + self.build.settings.safety.look_seconds * WAY_SHARE)


def stale(self: Hunter, run: Run, world: World, looked: float, act) -> bool:
    """Whether the move or use decided from the look begun at `looked` is not made: the look took more than
    STALE_LOOK, so the game it read is that old (the Plains of Despair, 23:48:52 on 2026-10-14: a Move from a
    look 5.3 s old, made 36 units from where that look saw the character, into the pack that had come round it;
    rca/2026-10-14/run-2040-findings.md §1.2.3). The loop looks again. A second slow look in a row whose
    character stands where it saw it is made: the host is slow, the game has not changed, and a loop that drops
    every act moves nothing. Said `Macro: look: the act of a look ... is dropped ...`."""
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
    """An act of the loop's given up for `reason` is said every time it is, with how many times in a row
    (I1: the look says why it moved nothing; I6: never silent): run-2110-findings.md M3, where the same abort
    was said once and then silenced for 9.3 s while the card kept saying "Walking 16 toward Diablo"."""
    last = self.refused
    count = last[1] + 1 if last is not None and last[0] == reason else 1
    self.refused = (reason, count)
    self.tell(run, reason if count == 1 else f'{reason} (x{count})')


@contextmanager
def priced_for(self: Hunter, run: Run, seconds: float):
    """An act's price is not permission to spend an unbounded time in its hands.

    Existing hands already poll the world. Expiry unwinds them through their
    normal Abort cleanup; the next loop look prices what actually happened.
    Preserve the recorder/other observer and restore it even on cancellation.
    """
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
    """Make the move the navigator gave toward the goal. A casting delay about to end on the way the
    set would take is waited out first and the move asked for again (`Travel.pause`); with the staff
    in hand and no charge on it the main weapons are taken, once (`foot_step` has why)."""
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
        # At a cooldown boundary float subtraction can leave a sub-frame
        # remainder. The next look must observe a later game frame.
        run.pace.sleep(max(FRAME, wait))
        return  # the next look must reprice a new leg; never execute an unpriced replacement
    if not act.reason and step.skill is None and self.warp_ready(run, world, ground, aspect, place, goal, rooms):
        # The look priced a walk with a jump's casting delay further off than PLAN_AHEAD; by now it is within it,
        # and the goal's way is that jump (`pause` waits for nothing then): the walk would hold the jump back by
        # its stride. 22:51:10 on 2026-10-16: 1.2 s on foot, the Blade Warp held 0.9 s past its delay; 17 of the
        # session's 41 walks between two warps were chosen 0.80-0.90 s after the warp's key.
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
        # The walk across an open passage into the next level (pursuit.py `through`), said once whether the safety
        # priced the move (its candidate keeps no reason) or not
        self.tell(run, f'{goal.label}: {PASSAGE}')
    here = (world.player.x, world.player.y) if world.player is not None else (player.x, player.y)
    LOG.info(
        'Macro: pursuit: %s toward %s at (%.1f, %.1f), %.0f away from (%.1f, %.1f): to (%.1f, %.1f) within %s',
        by, goal.label, *place, math.dist(here, place), *here, *step.spot, goal.spend.name,
    )  # fmt: skip
    if step.skill is not None and step.skill != TELEPORT:
        run.say(f'{by} toward {goal.label}')  # a walk and a Teleport hop say their own line
    self.travel.make(
        run, step, world, aspect, key_names, ground, name=goal.label, intent=goal.spend, goal=place, hurry=act.dodge
    )


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
    """Whether the goal's way from here is a jump whose casting delay still runs, within PLAN_AHEAD of its end
    (`Travel.toward` counts it as over), where the look gave a walk. A jump the look did not take for any other
    reason is not looked again for."""
    player = world.player
    if player is None or not self.travel.warped_at > -math.inf:
        return False
    found = self.travel.toward(run, world, ground, aspect, place, goal.spend, rooms)
    if not isinstance(found, Step) or found.skill is None:
        return False
    return self.travel.left(found.skill, run.clock(), player.cooldown) > 0.0


def operate(self: Hunter, run: Run, world: World, goal: Goal, key_names) -> None:
    """What is done at a goal reached: its object used and the route told (macros/route.py
    `note_used`), a stand noted, a drop taken by the pickup step's own hands."""
    player, rect = world.player, run.actuator.keys.focused_window_rect()
    assert player is not None
    bearings = self.bearings
    if goal.do == PICK_UP:
        LOG.info('Macro: pursuit: %s is taken first', goal.label)
        # The hands take the drop the goal names, the one the act was priced for (run-0025-findings.md §2.2:
        # the goal "5037 gold, on the way" while the hands clicked a Magic Dusk Shroud, valuables first)
        if goal.unit is not None and (self.running or goal.unit in self.restock_said):
            # A level run (and attack mode's restock, `restock`) goes for one drop GATHER_TRIES times at most: one
            # no click takes must not hold it
            self.drops.gathered[goal.unit] = self.drops.gathered.get(goal.unit, 0) + 1
            pick_up(run, self.known_level(player), key_names, lambda: None, threat(run), unit=goal.unit)
        else:
            pick_up(run, self.known_level(player), key_names, lambda: None, unit=goal.unit)
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
        self.settled_at = run.clock() + USES[goal.mark.use].brings
        route.note_used(run, goal.mark, bearings.progress, bearings.marks)
    elif goal.do == STAND and goal.stage is not None and bearings.progress is not None:
        bearings.progress.stood(player.area, goal.stage.mark)
        run.say(f'{goal.route}: at {goal.stage.mark}')


def pursue_once(self: Hunter, run: Run, key_names, *, attacking: bool) -> Judged | None:
    """One press of the teleport key with nothing working: one pass of the same decision the mode
    makes (`pursue`), the press being this run's own; what was decided, the act made. `attacking`:
    attack mode is on or follows this press. None: the press is the route's own step's (the pursuit
    is off for the build played, the town, a goal that step performs), and nothing was done."""
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
            # With the mode not running, a strike is made only when it follows this press, for a fight
            # (runner.py `pursues`): for any other goal the press is answered without one.
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
    """One seek step: a move toward the nearest elite, or into the unexplored. With `any_hostile`
    (the pickup request: a Terror Zone's completion counts every kill and every room) toward
    whatever is nearer by the way, a known hostile of any kind or an unexplored room."""
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
    # The blades' own reach, not the firing spots': a step toward an elite attack mode already
    # fights would break that fight off.
    reach = self.reach
    near = [m for m in leaders if in_reach(ground, here, (m.x, m.y), reach, doors)]
    if near:
        run.say(f'{label(near[0])} is in reach: attack mode takes it')
        return
    quarry = self.quarry(level.area, here, foes, any_hostile)
    frontier = self.frontier(level, player, rect) if quarry is None or any_hostile else None
    # Whichever is nearer; the hostile when it is not much further (a room's worth).
    far = frontier is not None and quarry is not None
    if far and math.dist(here, quarry[0]) > frontier[0] * TILE_UNITS + ROOM_UNITS:
        quarry = None
    if quarry is None:
        self.explore(run, level, player, rect, key_names, frontier)
        return
    spot, name = quarry
    self.go(run, level, ground, player, rect, spot, name, doors, key_names)


def go(self: Hunter, run: Run, level: Level, ground: Ground, player, rect, mob, name: str, doors, key_names) -> None:
    """A move onto the nearest spot with a shot at `mob`: a walk when it is near over clear ground,
    else a teleport hop."""
    here = (player.x, player.y)
    target = self.firing_target(level, ground, here, mob, name, doors)
    goal = (target.point[0] * TILE_UNITS, target.point[1] * TILE_UNITS)
    if math.dist(here, goal) < MOVED:
        # Already on a firing spot (the shot from the character's exact place may still read blocked):
        # a click under its feet moves nothing and would stop the step.
        run.say(f'{name} is in reach: attack mode takes it')
        return
    if math.dist(here, goal) <= WALK_UNITS and clear_shot(ground, here, goal, doors):
        step_walk(run, goal, player, rect[2] / rect[3], attackable(run.world()), name=name, clicks=WALK_CLICKS)
    elif not self.afoot(run, ground, player, rect, goal, name, key_names):
        hop_toward(run, target, player, rect, key_names)
    # A step that ends where it began is said and logged as such: with the monster out of reach
    # the mode behind it has nothing to do either, and the press looked dead (that corner).
    now = run.world().player
    if now is not None and now.area == player.area and math.dist((now.x, now.y), here) < MOVED:
        LOG.warning(
            'Macro: the step toward %s moved nothing: at (%.1f, %.1f), the spot (%.1f, %.1f) %.1f away',
            name, *here, *goal, math.dist(here, goal),
        )  # fmt: skip
        run.say(f'No move toward {name}: {math.dist(here, goal):.0f} from its firing spot')


def own_teleport(self: Hunter, run: Run, now: float) -> bool:
    """Whether Teleport is the character's own skill (Enigma: game/memory.py `own_teleport`), read again at most every
    OWN_TELEPORT_SECONDS: the safety prices each look with it."""
    if self.own_read is None or now - self.own_read[1] > OWN_TELEPORT_SECONDS or now < self.own_read[1]:
        self.own_read = (bool(run.own_teleport is not None and run.own_teleport()), now)
    return self.own_read[0]


def worn(run: Run) -> Teleport | None:
    """The Teleport staff the character wears, with the charges left on it; None without one
    (Teleport as a skill, or none at all)."""
    return run.reads.teleport()


def afoot(self: Hunter, run: Run, ground: Ground, player, rect, goal: Point, name: str, key_names) -> bool:
    """A seek step that spares the staff: a stride straight toward `goal` (`stride`). A Blade Warp
    over a clear line whatever the staff holds (it costs no charge and no weapon swap: of the 106
    seek hops in the 26 games of 2026-10-11 in the Halls of Vaught, 78 had the line); with fewer
    than LOW_CHARGES also one click's walk. Whether it was made: with no such stride a hop is
    still made while a charge is left, and with none the step stops.

    The stride, the wait before it and the way round are the movement set's, asked within SEEK.
    What stays here is what no set decides: False hands the step to a Teleport hop with a weapon
    swap (teleport.py `hop_toward`, which plans its own landing), and whether to do so goes by
    the charges on the staff as they were read here. With no Teleport to spend at all the step is the
    navigation class's own (`class_step`: the walked way, a Blade Warp over a clear line)."""
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
        # No Teleport to spend: the way is the class's own (the walked way, Blade Warp over a clear line), never
        # a stride and a way round within 70 units toward a place a Teleport hop would land on
        self.class_step(run, ground, goal, name, key_names, rooms)
        return True
    # A Blade Warp just made: its casting delay is waited out when the line toward the goal is
    # clear, as presses come faster than it (0.5 s apart against 0.8 s: in the game of 15:27 on
    # 2026-10-11, 8 seek hops by Teleport to 4 by Blade Warp before the staff ran low).
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
    """The teleport step on a level whose mark is a boss's place, with the boss in sight and no
    shot at it from the mark: the step goes onto a firing spot at the boss itself, or stays when
    the character has the shot already. Whether the step was taken here. Tower Cellar 5, 20:14:33
    on 2026-10-11: the Countess stood 29 units from the place her map gives her, behind a wall
    (over 56 visits she was first seen 2 to 29 from it); the third hop had a clear line to her at
    21.5, the fourth went on to the mark, and the next press said "At Countess" with nothing in
    reach."""
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
    """The teleport step's hop toward the landing `spot` made by Blade Warp, and whether it was
    with fewer than WARP_CHARGES on the staff and the blade's line to the landing clear. Its
    casting delay is waited out; a wall, or a warp that moved nobody, leaves the hop to Teleport.

    The jump is the build's own that spares the staff (`spare_jump`), and the stride by it is the
    movement set's, asked within PLAYER_STEP. The order is this caller's, as the hop is not one
    `leg`: the charges that make the jump come first, the failure forgiven after WARP_RETRY, the
    line to the landing the way planned, and False for a Teleport hop that swaps weapons."""
    world = run.world()
    rect = run.actuator.keys.focused_window_rect()
    spare = spare_jump(self.build.movement, world.slots)
    if spare is None or world.player is None or rect is None or key_names is None:
        return False
    staff = self.worn(run)
    left = None if staff is None else staff.charges
    if left is not None and left < PLAYER_STEP.walks_under:
        # The staff empty: the step toward the target's own place by the class in hand (`foot_step`), not toward
        # the landing a Teleport would make (rca/2026-10-14/run-1932-findings.md §1.2.2)
        self.foot_step(run, target, key_names)
        return True
    # Only to spare the last charges (user, 2026-10-11 evening: "KP_4 when forcing blade warp is
    # way too slow ... prefer tp for longer distances, until around 15 charges, then blade warp
    # in priority; this is only for charges"): a warp hop took 0.8 to 1.0 s for 18 to 20 units,
    # a Teleport hop 0.6 s for 30.
    if left is None or left >= PLAYER_STEP.sparing:
        return False
    ground = Ground(target.ground)
    aspect = rect[2] / rect[3]
    here = (player.x, player.y)
    facts = facts_with(run, world, ground, aspect, self.travel, staff)
    failed = self.travel.jump_failed.get(spare.skill, -math.inf)
    # A jump by it recorded after now (a clock that went back) leaves the hop to Teleport too
    if facts.since_used(spare.skill) < 0 or run.clock() - failed < PLAYER_STEP.distrust:
        return False
    # One warp that moved nobody does not take the skill from the step for JUMP_DISTRUST as it
    # does from the sweep: Black Marsh, 18:07:38 on 2026-10-11, the third hop's warp failed and
    # the 43 hops after it were Teleports (3 warps in the game). 44 of 447 warps failed that day.
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
    """One move toward a far goal by the navigation class in hand (macros/movement.py `Ways.means`; the player,
    2026-10-14: "No TP: Blade Warp + walk, and we must use a route that is able to Blade Warp"): the class's own
    way there (`Travel.toward` within PRESSED: with no charge, the walked way, on which a Blade Warp goes over a
    clear line where it beats the walk), a casting delay worth it waited out first. Whether a move was made:
    False when the character is as near as a move brings it. No way of the class stops the step, said."""
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
    """The teleport step with the staff empty (teleport.step_toward `afoot`): one move toward the target's own
    place (a door's entry spot, else its mark) by the class in hand (`class_step`); at a door it is clicked
    (teleport.py `walk_into`), at any other place said."""
    player, rect = ready(run)
    # The staff's set gives nothing more and costs resistances and skill levels (user, 2026-10-13: 17 s with it
    # in hand and no charge in the Chaos Sanctuary): the main weapons, once.
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
    """The pickup request with nothing to pick up. With hostiles within SWEEP_UNITS it starts
    the sweep (or lets the one under way go on) and moves nothing itself: the mode, which follows
    this step, takes the steps (`follow_on`, and the look in `fight`). With none that near it is
    the seek step. Black Marsh, 01:13 on 2026-10-11: this step walked on its own and sought and
    explored by teleport, press after press, against the sweep's own walks."""
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
    """The place worth going to from where the character stands (combat/stance.py `camp`), or
    None: in view, as a click or a jump is aimed at it, and priced by the way the character will
    take there (`jumps`, with `run`; a walk without). `landed`: as the casts land by distance and as the
    blades stop at walls (stance `taken` `walls`); without, the sweep of the pursuit loop off as its
    goldens and replays were recorded."""
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
        # The cows are fought from inside the herd, as the player does it (user, 2026-10-12: "special
        # tactics for some mob types (cows/...)"): theirs is to be a `Tactic` (Stage 7); until then no
        # step out of the pack on their level.
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
        # A charged staff, a missing own-skill read, or a temporarily unavailable Teleport can all leave a
        # different jump first. Record the facts at the firing-stand decision, where the route's later
        # Teleport log cannot explain which source was available to this look.
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
    """The sweep's one look for a move, from wherever it looks: the place worth going to
    (`better_stand`), which in a fight has to be worth SWEEP_GAIN times the place the character
    fights from and with nothing in reach CAMP_GAIN times nothing; and with nothing in reach and
    no such place, a stride toward the nearest hostile (`toward`). None: stay. `priced`: the safety
    prices the place found (a level run's fight, `Safety.offer`): CAMP_GAIN of here, the firing
    stand's commitment keeping it from dithering, and places priced as the casts land by distance."""
    self.sweep.forget(run.clock())
    gain = CAMP_GAIN if priced or not fighting else SWEEP_GAIN
    place = self.better_stand(world, foes, ground, aspect, gain, run, landed=priced)
    found = Step.to(place) if place is not None else None
    if found is None and not fighting and foes:
        found = self.toward(run, world, foes, ground, aspect)
    if found is not None and self.leaves(found.spot, run.clock()):
        return None
    return found
