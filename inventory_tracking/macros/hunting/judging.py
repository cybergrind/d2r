"""What a look does with its goal: the judge, the safety pricing, the escort and the guard. A part of
macros/hunt.py `Hunter`, its methods bound there."""

import math
from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from inventory_tracking.combat import threats
from inventory_tracking.combat.escort import around, escorts, in_danger, kept_alive
from inventory_tracking.combat.harm import harm
from inventory_tracking.combat.policy import STRIKE_REACH, observe
from inventory_tracking.combat.stance import no_footing
from inventory_tracking.combat.survival import pressure
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Monster, World
from inventory_tracking.levels.model import Ground
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.build import NoWay, PricedStep
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import PICK_UP, Goal
from inventory_tracking.macros.hunting import shrines
from inventory_tracking.macros.hunting.base import (
    BLOCK_SECONDS,
    COMES_TO_ITS_MARK,
    DECIDE_SECONDS,
    EMPTY_MARK_GOES_ON,
    HURT_SECONDS,
    MARK_WAIT,
    NO_WAY_ENDS,
    NO_WAY_TO,
    OPEN_NEAR,
    PAIR_NEAR,
    SAID_AGAIN,
    SEEK_WAIT,
    SWAP_RETRY_SECONDS,
    YIELD_FRESH,
    YIELD_MOVED,
    YIELD_TAKES,
    Judged,
    paired,
)
from inventory_tracking.macros.pursuit import (
    Candidate,
    Defer,
    Ended,
    Facts,
    Hold,
    Move as Advance,
    Operate,
    Pursuit,
    carried,
    decide,
    heading,
)
from inventory_tracking.macros.safety import AWAY, STEPPING
from inventory_tracking.macros.sight import firing_spots, in_reach as in_reach_of
from inventory_tracking.macros.teleport import SPOT_NEAR, marked_thing
from inventory_tracking.macros.travel import (
    AROUND_LEAST,
    GROWING,
    SAFE_MOVE,
    STANDING,
    Point,
    Step,
    open_reaches,
    walk_reaches,
)
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import FIGHT, LEAVE, LOOT, USE


if TYPE_CHECKING:
    from inventory_tracking.macros.hunt import Hunter


def judge(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, *, in_reach: bool, attacking: bool = True
) -> Judged:
    """One look of the pursuit: the goal, the facts and the decision (pursuit.py `decide`); nothing is done.
    A fight's place is the nearest with a shot at the boss (`firing_target`)."""
    player = world.player
    assert player is not None
    # Read once, before the look's clock: a press posted later is the next look's (run-0025-findings.md §2.1)
    posted = self.pursuit
    here, now = (player.x, player.y), run.clock()
    if in_reach and self.only_bound(world, foes, ground, here):
        # A summoner's bound units (Baal's clone) are no fight to hold (rca/2026-10-14/baal-sim.md fix 2)
        in_reach = False
    if in_reach and self.nearing_only(world, foes, ground, here, now):
        in_reach = False  # the strikes did nothing from here (`untouched`)
    if posted is not None and posted.leashed and posted.area is None:
        named = replace(posted, area=player.area)  # the level run is of the level it was asked on
        self.swap(posted, named)
        posted = named
    onward = carried(posted, player.area, now) if posted is not None else None
    if posted is not None and onward is not None and self.swap(posted, onward):
        self.carry_on(run, posted, onward)  # before the mode is looked at: the player's switch goes with the run
        posted = onward
    pressed = posted is not None and posted.fresh(now)
    self.run_mode(run, player.area, posted)
    goal = self.goal(run, world, foes, pressed, posted)
    if posted is not None and posted.runs and not (pressed and posted.advance):
        goal = self.cleared(run, world, foes, ground, goal)  # the run's own look: what its mode adds
        goal = shrines.side_goal(self, run, world, goal, posted)  # an Experience Shrine on the way (2026-10-20)
    if not pressed and not (posted is not None and posted.leashed):
        goal = self.nearby(goal, here)
    noted = heading(posted, goal) if posted is not None else None
    if posted is not None and noted is not None and self.swap(posted, noted):
        posted = noted  # across its level's open passage the run goes on (`carry_on`)
    self.pursued = goal
    level = self.known_level(player)
    rect = run.actuator.keys.focused_window_rect()
    place, there, beyond = None, False, math.inf
    if goal is not None:
        place = goal.place
        if goal.do == FIGHT:
            there = in_reach_of(ground, here, goal.place, goal.near, world.doors)
            if not there and level is not None and goal.known:
                # As `firing_target`, quietly, on the attack's engage ring (run-1932-findings.md §4.2)
                engage = self.attack.engage
                spots = firing_spots(ground, goal.place, STRIKE_REACH, here, world.doors, engage) or [goal.place]
                rooms = level.rooms
                place = next((s for s in spots if room_at(rooms, (s[0] / TILE_UNITS, s[1] / TILE_UNITS))), spots[0])
        elif goal.shrine:
            there = shrines.there(ground, world, here, goal)  # clicked on a clear line, never across a wall
            beyond = max(goal.gap(here) - goal.near, 0.0)
        elif goal.do == USE and goal.mark is not None:
            thing = marked_thing(run, goal.mark)
            near = goal.gap(here) <= SPOT_NEAR or (
                thing is not None and math.dist(here, (thing.x, thing.y)) <= goal.near
            )
            there = thing is not None and near
            if thing is not None and posted is not None and posted.rush and posted.runs:
                # The loop opens from beside the object (`OPEN_NEAR`), never across a wall (`open_reaches`). The
                # way goes to the object's own place, which stays put; a place beside it moved with every move
                # (2026-10-16 22:50: the goal's cell changed in 112 of 213 looks)
                at = (thing.x, thing.y)
                things = run.things() if run.things is not None else ()
                near = PAIR_NEAR if paired(things, thing, here) else OPEN_NEAR
                there = there and open_reaches(ground, world.doors, here, at, near)
                if not there:
                    place = at
        elif goal.do == PICK_UP:
            # Near enough to click is a walk within reach, not a straight line (run-0025-findings.md §2.2)
            there = walk_reaches(ground, world.doors, here, goal.place, goal.near)
            if not there and goal.unit is not None and goal.unit not in self.round_said:
                away = math.dist(here, goal.place)
                if away <= goal.near:
                    if len(self.round_said) > 200:
                        self.round_said.clear()
                    self.round_said.add(goal.unit)
                    LOG.info(
                        'Macro: pickup: %s: %.0f away with no clear line from (%.1f, %.1f): gone to first, '
                        'not clicked from afar',
                        goal.label, away, *here,
                    )  # fmt: skip
        else:
            there = goal.gap(here) <= goal.near
            beyond = max(goal.gap(here) - goal.near, 0.0)  # an arrival by distance (pursuit.py `moved`)

    def way():
        if goal is None or place is None or rect is None:
            return NoWay('no game window')
        rooms = level.rooms if level is not None else ()
        return self.travel.toward(run, world, ground, rect[2] / rect[3], place, goal.spend, rooms)

    facts = Facts(
        now, goal, there, in_reach, attacking, way, player.area, now < self.settled_at,
        beyond=beyond, least_move=AROUND_LEAST,
    )  # fmt: skip
    # The strike gap counts while a hostile is within reach, clear line or not (I2)
    near = any(math.dist(here, (m.x, m.y)) <= self.reach for m in foes)
    rush = posted is not None and posted.rush and posted.runs
    facts = replace(facts, quiet=min(now - self.struck_at, 60.0) if near else 0.0, near=near, rush=rush)
    if self.pursuing and rect is not None:
        facts = self.safety_priced(run, world, foes, ground, facts, posted, rect)
    if facts.candidates:
        # A spot a move just failed to reach is not priced again for a while (`barred`)
        facts = replace(facts, candidates=tuple(c for c in facts.candidates if not self.barred(c.act, now)))
    act = decide(facts, posted, self.pursuing)
    if (
        isinstance(act, Hold)
        and posted is not None
        and posted.looped
        and goal is not None
        and goal.do in (LOOT, LEAVE)
        and now - self.hurt_at > HURT_SECONDS
    ):
        # The route's boss dead, her pack is not fought while nothing hurts (the player, 2026-10-17: "we don't even
        # need to kill some trash mobs and can loot and leave")
        act = Ended(f"the route's boss is dead: {goal.label} next, what does not hurt is not fought")
    if isinstance(act, Advance) and self.barred(act, now):
        act = NoWay(f'{goal.label if goal else "the goal"}: the move there just did not take; looking again')
    self.empty_mark(world, goal, act, now)
    if isinstance(act, Advance) and act.reason:
        place = act.step.spot
    if (
        isinstance(act, NoWay)
        and goal is not None
        and goal.shrine
        and act.reason.startswith('no way toward')
        and not act.reason.endswith(GROWING)
    ):
        shrines.no_way(self, goal, act.reason)  # a side goal: left, the level's own way is not explored for it
    elif (
        isinstance(act, NoWay)
        and goal is not None
        and goal.clearing
        and act.reason.startswith('no way toward')
        and not act.reason.endswith(GROWING)  # a way not grown yet in the look's time is no way that fails
    ):
        # a run's clearing goal it has no way to: the next look goes on
        self.pass_by(goal, act.reason, now, level.rooms if level is not None else ())
    elif (
        isinstance(act, NoWay)
        and goal is not None
        and self.agenda is not None
        and act.reason.startswith('no way toward')
        and (world.game_name, player.area) not in self.wayless
    ):
        # The route's goal with no way over the known rooms: explore to grow the way, never stand (2026-10-19
        # 09:46, the player: "we stuck and exit without visiting next location")
        self.wayless.add((world.game_name, player.area))
        LOG.info('Macro: agenda: no way to %s: the level is explored for it (cover)', goal.label)
    elif (
        isinstance(act, NoWay)
        and not act.arrived
        and goal is not None
        and self.agenda is not None
        and act.reason.startswith('no way toward')
        and (world.game_name, player.area) in self.wayless
    ):
        # Explored for it and still no way: the run ends, not the 45 s watchdog (01:04:16-01:05:01 on 2026-10-20,
        # Lost City: "no way toward Valley of Snakes" after its rooms, the game left by the watchdog)
        key = (world.game_name, player.area)
        if self.no_way_since is None or self.no_way_since[0] != key:
            self.no_way_since = (key, now)
        elif now - self.no_way_since[1] >= NO_WAY_ENDS:
            act = Ended(f'{NO_WAY_TO}{goal.label} after exploring for it {now - self.no_way_since[1]:.0f} s')
    else:
        self.no_way_since = None
    return Judged(act, goal, place, posted, pressed)


def empty_mark(self: Hunter, world: World, goal: Goal | None, act, now: float) -> None:
    """Notes a route's boss fight stood at with no boss (`goal.unit` None: by its mark or where one was last seen,
    the act an arrival that strikes nothing). After MARK_WAIT the stage is given up on this level for the game
    (`marks_empty`, read by `goal`) and the level is explored for it (`wayless`); said once. Not for a boss the game
    brings there later (COMES_TO_ITS_MARK). EMPTY_MARK_GOES_ON off: nothing noted."""
    player = world.player
    if (
        not EMPTY_MARK_GOES_ON
        or player is None
        or goal is None
        or goal.do != FIGHT
        or goal.unit is not None
        or not goal.route
        or goal.stage is None
        or goal.stage.kind != FIGHT
        or goal.stage.boss in COMES_TO_ITS_MARK
    ):
        return
    key = (world.game_name, player.area, goal.stage.boss)
    if not (isinstance(act, NoWay) and act.arrived):
        if isinstance(act, Hold) and not goal.known:
            self.mark_since.pop(key, None)  # a wave fought: the seek's wait counts afresh from its end
        return
    if key in self.marks_empty:
        return
    if len(self.mark_since) > 200:
        self.mark_since.clear()
    since = self.mark_since.setdefault(key, now)
    # A seek of a boss not known yet (Lister, after the Throne's waves) waits SEEK_WAIT: the waves come in turn
    if now - since < (MARK_WAIT if goal.known else SEEK_WAIT):
        return
    if len(self.marks_empty) > 200:
        self.marks_empty.clear()
    self.marks_empty.add(key)
    self.wayless.add((world.game_name, player.area))
    LOG.info(
        'Macro: run: %s: no boss here after %.0f s; the stage is left and the level explored for it',
        goal.label, now - since,
    )  # fmt: skip


def safety_priced(
    self: Hunter,
    run: Run,
    world: World,
    foes: list[Monster],
    ground: Ground,
    facts: Facts,
    posted: Pursuit | None,
    rect,
) -> Facts:
    """The facts with the safety's prices (safety.py `Safety.price`); unchanged with no life read."""
    player = world.player
    assert player is not None
    now = facts.now
    if run.loot is None:
        return facts
    loot = run.loot()
    if loot.max_life > 0 and loot.life > 0:
        if self.life_seen is not None and loot.life < self.life_seen:
            self.hurt_at = now
        self.life_seen = loot.life
        facts = replace(facts, hurt=now - self.hurt_at <= HURT_SECONDS)
        staff = self.worn(run)
        hands = 'travel' if staff is not None and staff.in_hand else 'battle'
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        seen = self.attack.sees(observe(player, foes, companions, ground, world.doors), companions)
        look = self.safety.look(
            world, loot, hands, seen.blocked, self.build.shield, self.build.settings.safety,
            now=now, flights=getattr(run, 'flights', None), draw=self.build.draw,
        )  # fmt: skip
        facts = self.safety.price(
            facts,
            posted,
            look,
            loot,
            pressure(self.drinker.readings),
            self.build.settings.safety,
            seen,
            self.attack,
            lambda point: self.travel.leg(run, world, ground, rect[2] / rect[3], point, SAFE_MOVE),
            self.travel.jumps(run, world, SAFE_MOVE),
            no_footing(ground, world.doors),
            hands,
            options=lambda point: self.travel.options(run, world, ground, rect[2] / rect[3], point, SAFE_MOVE),
            battle_ready=now - self.swap_failed_at >= SWAP_RETRY_SECONDS,
            teleport_hands='battle' if self.own_teleport(run, now) else 'travel',
        )
        facts = self.escorted(run, world, ground, rect, look, facts)
    return facts


def escorted(self: Hunter, run: Run, world: World, ground: Ground, rect, look, facts: Facts) -> Facts:
    """The priced facts plus jumps that bring the mercenary (`JumpSource.brings`: Blade Warp) out of a place it
    dies at (combat/escort.py), priced as the others less its death's cost. Unchanged with nothing priced, no
    such jump, or no mercenary in danger."""
    player = world.player
    if not facts.priced or player is None:
        return facts
    brought = {source.jump.skill for movement in self.travel.sets for source in movement.sources if source.brings}
    ready = [jump for jump in self.travel.jumps(run, world, SAFE_MOVE) if jump.skill in brought]
    found = kept_alive(world.monsters, player.unit_id)
    if not ready or not found:
        return facts
    settings = self.build.settings.safety
    endangered = in_danger(look, found, settings)
    if not endangered:
        return facts
    here, jump = (player.x, player.y), ready[0]
    aspect = rect[2] / rect[3]
    landings: dict[Point, Step] = {}
    for point in around(here, jump.reach, jump.least):
        for step in self.travel.options(run, world, ground, aspect, point, SAFE_MOVE):
            if step.skill == jump.skill and math.dist(here, step.spot) > 2.0:
                landings[step.spot] = step
    goal = facts.goal or Goal('the fight', here, FIGHT, self.reach, STANDING)
    added = []
    for escort in escorts(look, endangered, landings, settings):
        seconds = jump.takes(math.dist(here, escort.spot))
        step = PricedStep(escort.spot, jump.skill, None, 'battle', seconds)
        priced = harm(look, escort.spot, settings.horizon, 'battle', settings)
        # The jump's seconds and overhead, less the death it spares
        spent = seconds + settings.move_overhead - escort.credit
        added.append(Candidate(Advance(step, goal, escort.line(), dodge=True), spent, priced, False, seconds))
    if not added:
        return facts
    return replace(facts, candidates=(*facts.candidates, *added))


def guard(self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground) -> Advance | None:
    """Attack mode with the pursuit loop off: the pursuit's safety look and arbiter, its answer taken only for a
    STEPPING move (a dodge, a place a read model offers; not AWAY) that a strike follows from. No retreat, firing
    stand or goal: the mode alone never goes back, so those left it out of reach (rca/2026-10-14/baal-sim.md
    fix 3). Looked at only while `guarded`. None: strike on."""
    player = world.player
    if self.pursuing or player is None or run.loot is None or not self.guarded(foes):
        return None
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        return None
    here, now = (player.x, player.y), run.clock()
    near = any(math.dist(here, (m.x, m.y)) <= self.reach for m in foes)
    facts = Facts(now, None, False, True, True, lambda: NoWay('attack mode alone goes nowhere'), player.area)
    facts = replace(facts, quiet=min(now - self.struck_at, 60.0) if near else 0.0, near=near)
    priced = self.safety_priced(run, world, foes, ground, facts, None, rect)
    if not priced.priced:
        return None
    act = decide(priced, None)
    if not isinstance(act, Advance) or not act.reason.startswith(STEPPING) or act.reason.endswith(AWAY):
        return None
    # Only a landing a strike follows from, or the mode would stand out of reach (baal-sim.md weakness 4)
    landing = next((c for c in priced.candidates if isinstance(c.act, Advance) and c.act.step == act.step), None)
    return act if landing is not None and landing.strikes else None


def guarded(self: Hunter, foes: Sequence[Monster]) -> bool:
    """Whether `guard` looks: a read model's hostile about (combat/threats `of`) or what lingers after one."""
    return bool(self.safety.casters) or any(threats.of(m.txt_id) is not None for m in foes)


def take_guard(self: Hunter, run: Run, aspect: float, key_names, ground: Ground) -> None:
    """Makes the step `guard` chose, as a dodge (`hurry`); the player's own move first. The next look strikes."""
    act, self.guarding = self.guarding, None
    if act is None:
        return  # no look at the game: the mode alone as it was (the loop goldens' reads)
    world = run.world()
    player = world.player
    if player is None:
        return
    why = 'a move was asked for' if self.move is not None else self.moving(run, world)
    if why is not None:
        LOG.info('Macro: attack mode: the step is dropped (%s)', why)
        return
    here = (player.x, player.y)
    LOG.info(
        'Macro: attack mode: %s, to (%.1f, %.1f), %.1f away from (%.1f, %.1f)%s; the strike follows',
        act.reason, *act.step.spot, math.dist(here, act.step.spot), *here, ' (a dodge)' if act.dodge else '',
    )  # fmt: skip
    run.say(f'{act.reason[:1].upper()}{act.reason[1:]}')
    try:
        self.travel.make(run, act.step, world, aspect, key_names, ground, name=act.goal.label, hurry=act.dodge)
    except Abort as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: attack mode: the step to (%.1f, %.1f) failed (%s)', *act.step.spot, stop)


def key_asks(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, *, unstruck: bool = False
) -> bool:
    """Inside a fight: whether the press asks for something other than the strike (a move, a use, the route's
    step); the fight then lets go. Judged once a press and every DECIDE_SECONDS while fresh. `unstruck`: before
    the fight's first strike the Hold that began it stands, short of a fresh press
    (rca/2026-10-18/andariel-cadence-findings.md F2)."""
    now = run.clock()
    if not self.pursuing:
        return False
    current = self.pursuit.pressed_at if self.pursuit is not None else -math.inf
    stamp, at, asks = self.judged
    if stamp != current or (now - at >= DECIDE_SECONDS and not unstruck):
        found = self.judge(run, world, foes, ground, in_reach=True)
        act = found.act
        asks = (
            isinstance(act, Advance | Operate | Defer)
            or (isinstance(act, NoWay) and act.reason.startswith('safety:'))
            or (isinstance(act, Ended) and found.posted is not None and found.posted.looped)  # the loop's run over
        )
        if isinstance(act, Hold) and found.pressed:
            # A fresh press answered by the strike says so (I6)
            label = found.goal.label if found.goal is not None else 'the goal'
            self.tell(run, act.reason or f'{label}: the least-time safe act is the fight', again=SAID_AGAIN)
        self.judged = (current, now, asks)
        player = world.player
        # The act the fight is let go for is the one the next look makes (`yielded_act`, YIELD_TAKES)
        self.yielded = (
            (found, now, (player.x, player.y), player.area, current)
            if asks and YIELD_TAKES and isinstance(act, Advance | Operate) and player is not None
            else None
        )
    return asks


def yielded_act(self: Hunter, run: Run, world: World) -> tuple[Judged, float] | None:
    """The look `key_asks` let the fight go for, and its clock, while it still holds (YIELD_TAKES): within YIELD_FRESH,
    the character within YIELD_MOVED of where that look saw it on the same level, the same press, not hurt since and
    the move not barred since. Taken once; None: the next look judges again."""
    kept, self.yielded = self.yielded, None
    player = world.player
    if kept is None or not YIELD_TAKES or player is None:
        return None
    found, at, there, area, pressed_at = kept
    now = run.clock()
    current = self.pursuit.pressed_at if self.pursuit is not None else -math.inf
    if (
        not 0.0 <= now - at <= YIELD_FRESH
        or player.area != area
        or math.dist((player.x, player.y), there) > YIELD_MOVED
        or current != pressed_at
        or self.hurt_at >= at
        or self.barred(found.act, now)
    ):
        return None
    return found, at


def tell(self: Hunter, run: Run, reason: str | None, *, aloud: bool = True, again: float | None = None) -> None:
    """Says a decision that moved nothing, once per change of reason. Not `aloud`: the log only. `again`: seconds
    after which the same reason is said once more (I6)."""
    repeated = (
        again is not None and reason is not None and reason == self.told.reason and run.clock() - self.told_at >= again
    )
    if self.told.new(reason) or repeated:
        self.told_at = run.clock()
        LOG.info('Macro: pursuit: %s', reason)
        if aloud:
            run.say(f'{reason[:1].upper()}{reason[1:]}')  # type: ignore[index]


def defer(self: Hunter, run: Run, goal: Goal | None, why: str, seen: Pursuit | bool | None = True) -> None:
    """Hands the press to the route's own step (a door, the loot, the leaving, a panel, the town) or the key's
    routine: raises Cancelled and takes the press out of the mailbox (a level run's leash stays). `seen`: the
    mailbox as the look read it; a press posted since stays (True: whatever it holds now)."""
    with self.mailbox:
        posted = self.pursuit if seen is True else seen
        if not isinstance(posted, Pursuit):
            posted = None
        if self.pursuit is posted:
            self.pursuit = replace(posted, spent=True) if posted is not None and posted.leashed else None
    key = posted.key if posted is not None else 'teleport'
    if self.hand_over is None:
        self.tell(run, f'{why}: nothing performs it here')
        return
    LOG.info("Macro: pursuit: %s: the route's own step takes the press", goal.label if goal is not None else why)
    self.hand_over(key)
    raise Cancelled


def blocked(self: Hunter, run: Run, units: frozenset[int]) -> None:
    """The hands found `units` in the way of the goal's act (teleport.py `Covered`): the fight with them
    comes first for that goal (`blockers`, goals.py `first_fight`)."""
    base = self.base
    if base is None:
        return
    held = self.blocking
    if held is not None and held[0] == base.label:
        units = units | held[1]
    self.blocking = (base.label, units, run.clock() + BLOCK_SECONDS)
    LOG.info('Macro: pursuit: %s: %d in the way of its act, the fight first', base.label, len(units))
