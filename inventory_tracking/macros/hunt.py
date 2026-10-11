"""Attack mode and the seek step. The toggle turns attack mode on and off; the seek step goes toward
the nearest unique or champion and leaves attack mode on. The history of each rule is in macros/plan.md.

Attack mode (`Hunter.attack_mode`, a run that lives until cancelled): everything within the blades'
REACH with a clear shot (sight.py: the flight layer of the read grids, closed doors) is fought while
the player moves about as they like. The mouse, the keyboard and the character's own moves and casts
are not cancels: only its toggle or the macro request ends it, the game being left, or MISSES_IN_A_ROW fights
that stopped one after another. The player's hand is on the mouse all along, so the actuator aims
once and casts at once (`Actuator.steady` off). the teleport and seek steps work meanwhile: the runner pauses the
mode for the step and resumes it after (runner.py).

A fight (`Hunter.fight`) is one hold of the input that has Echoing Strike: the right mouse button
when it holds the skill, else its skill key, else a left click with Shift. The game casts at its own
rate; an input idle RETAP_SECONDS is released and pressed again. The pointer is kept on the combat
policy's line (combat/policy.py, the decision the simulator scores); a monster in reach the policy
finds no line for is aimed at directly, the elite first, then the nearest, AIM_BEYOND past it. An
elite gets Sigil: Lethargy under it once per SIGIL_SECONDS, the strongest monster in reach Death Mark
once per DEATH_MARK_SECONDS. The main weapon set is swapped in for a tough pack only (`tough`).

What the fight decides from what it sees and the clock (where to cast, whose the pointer is, the
held input, the move asked for) is combat/controller.py, apart from the game; this module reads the
game, asks it and acts.

The player's move comes before any strike (`sense`, `serve_move`): a left click releases the strike
and blocks it until the character has gone and stands again; a click made while a cast ran, which
the game may have swallowed, is made again for the player. A held key or a running character makes
the mode wait.

The step inside a fight (`asked_step`, `take_step`, `step`; combat/stance.py decides where): the mode
never moves the character on its own. The pickup request while hostiles are near asks for one step
to a better place to stand: in a fight the strike is let go, the spot is walked to and the fight
goes on from there, and the press still picks up afterwards when something worth it lay on the
ground; with nothing in reach and nothing to pick up the step goes to where the hostiles near can
be struck from.

The seek step (`Hunter.seek`, one request one step): toward the nearest elite the game holds in memory or the
terror tracker remembers alive in this level, onto the nearest spot with a shot at it
(sight.firing_spots, within STRIKE_REACH), by a click when that is within WALK_UNITS over clear
ground, by a teleport hop otherwise (teleport.hop_toward). None known: the unexplored room nearest by
the way (the potential from the character's own tile). An elite already in reach is only named.
"""

import math
import threading
from collections.abc import Callable, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field

from inventory_tracking.combat.controller import (
    CLICK,
    GAVE_UP,
    MOVE_CLICKS,
    NO_CAST,
    PENDING,
    RETAP,
    Aim,
    CastWatch,
    Move,
    aim_choice,
    serve,
)
from inventory_tracking.combat.policy import (
    REACH,
    RUN_MODES,
    STRIKE_REACH,
    Choice,
    LinePolicy,
    Policy,
    observe,
)
from inventory_tracking.combat.score import LiveScore
from inventory_tracking.combat.stance import (
    CAMP_GAIN,
    CAMP_REACH,
    Camp,
    camp,
    no_footing,
)
from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground, Level, Room, Target
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros.actuator import POINTER_DRIFT, Abort, Cancelled
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pickup import choose, unshunned
from inventory_tracking.macros.rotation import (
    ELITE_LIFE,
    Rotation,
)
from inventory_tracking.macros.routines import (
    ACTING,
    CHARACTERS,
    DEAD,
    SUPER_UNIQUE_FLAG,
    TOWN_NPCS,
    take_battle_weapons,
)
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach
from inventory_tracking.macros.skills import (
    BLADE_WARP,
    DEATH_MARK,
    ECHOING_STRIKE,
    ENGORGE,
    SWAP_WEAPONS,
    skill_name,
)
from inventory_tracking.macros.teleport import (
    MOVED,
    Way,
    ground_fraction,
    hop_toward,
    in_view,
    ready,
)
from inventory_tracking.macros.tour import Bounds, tour
from inventory_tracking.macros.travel import (
    JUMP_REACH,
    LOW_CHARGES,
    WARP_DELAY,
    Point,
    Step,
    Travel,
    attackable,
    label,
    life,
    step_line,
    step_walk,
)
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import NO_OWNER, VALUABLE, Drop, Monster, World, has_room
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror.bosses import BOSSES
from inventory_tracking.terror.tracker import BARRICADES, UNKILLABLE


# monstats.txt hydra1-3 (AI Hydra, no life of their own): the fire heads the Council casts, which never die
# and are left out of the hostiles
HYDRAS = frozenset((351, 352, 353))
# monstats.txt MonType `vulture` (vulture1-5: combat/data/tables.json): the birds the blades pass through in the air
# (AIRBORNE: their modes 1 and 8); on the ground they are fought like other monsters
VULTURES = frozenset((110, 111, 112, 113, 608))
AIRBORNE = frozenset((1, 8))
FIRST_STRIKE_SECONDS = 0.3  # the held strike this long with no cast seen yet: the mark and sigil wait no longer
DEATH_MARK_SECONDS = 8.0  # between two Death Marks; the debuff lasts 125 + 13/level frames (skills.txt)
WALK_CLICKS = 2  # clicks for one walk to a firing spot
WALK_UNITS = 10.0  # a firing spot this near, over clear ground, is walked to, not teleported to (as NEAR_WARP)
FIGHT_SECONDS = 60.0  # one fight ends here at the latest; attack mode looks again right after
POLL = 0.1  # seconds between looks in attack mode while nothing is fought
FRAME = 0.04  # seconds between looks during a fight: one game frame, so a move of the player's is yielded to at once
DECIDE_SECONDS = 0.12  # between two askings of the policy while its monster lives
SIGHT = 30.0  # world units: hostiles further off are not part of the decision
# The sweep after a step asked for: the mode goes on stepping by itself, to a better place whenever
# there is one and toward the nearest hostile when nothing is in reach, until nothing hostile is within
# SWEEP_UNITS, the player moves by hand, FOLLOW_STEPS are taken or FOLLOW_SECONDS pass with no step.
FOLLOW_STEPS = 12
FOLLOW_SECONDS = 8.0  # since the press or the sweep's last step
WARP_CHARGES = 15  # with fewer charges on the staff the teleport step hops by Blade Warp where it can
WARP_RETRY = 3.0  # seconds the teleport step leaves Blade Warp alone after one that moved nobody
BOSS_MARK_UNITS = 60.0  # world units from a level's mark: a boss or super unique this near is the one it marks
GATHER_CLEAR = 12.0  # world units: no hostile this near the character or a drop when the sweep stops for it
HOLD_SIGHT = 40.0  # world units: a valuable this near that the sweep does not take is stayed by
HOLD_UNITS = 25.0  # the sweep's own steps end no further than this from it
GATHER_CHECK = 0.3  # seconds between two looks of the sweep for something to pick up
GATHER_TRIES = 2  # times the sweep stops for one drop
GATHER_SECONDS = 3.0  # a pickup step's time, added to the sweep's own so that it goes on after
FOLLOW_CHECK = 0.7  # seconds between two looks for a better place while a fight goes on
SWEEP_UNITS = 60.0  # hostiles this near are gone to
STAND_OFF = 14.0  # units short of the nearest hostile a stride toward it ends (the player engages at 12 to 14)
# A place a fight is left for, asked for or not, has to be worth this many times where the character stands
# (with nothing in reach: stance.CAMP_GAIN); the worth counts the monsters where they stand, not where they come
SWEEP_GAIN = 2.0
# A character in a walk or run mode that has not moved for this many seconds is stuck, not going anywhere:
# the mode stops waiting for it.
RUN_IN_PLACE = 1.5
WAIT_LOG_SECONDS = 3.0  # between log lines on what attack mode is waiting for
# A place a step failed for is shunned for SHUN_SECONDS, and STEP_FAILURES failures in a row end the sweep.
SHUN_UNITS = 6.0
SHUN_SECONDS = 10.0
STEP_FAILURES = 2
# The seek order: the unexplored room is the first stop of a tour of all unexplored rooms (macros/tour.py).
# A remembered monster no longer where it was seen (within VANISH_UNITS of the character, not among the live
# ones) is not gone to again.
# A monster the strikes do nothing to (seen by its life, not by type: a bird in the air, something burrowed, an
# immune) is left alone: once UNTOUCHED_CASTS casts show its life unchanged, it is no hostile for
# UNTOUCHABLE_SECONDS (not fought, swept or sought toward), then tried again.
UNTOUCHED_CASTS = 4
UNTOUCHABLE_SECONDS = 20.0
ROOM_UNITS = 40.0  # a known hostile this much further than the nearest unexplored room still goes first
VANISH_UNITS = 25.0
SLICE = 0.01  # seconds between looks at the left mouse button while the mode waits or fights
TOUGH_POINTS = 40_000.0  # life points in reach from which a pack is worth the main weapons
MAIN_AFTER = 1.0  # seconds after a step before the main weapons are swapped in for a fight
SWAP_RETRY_SECONDS = 5.0  # after a swap to the main weapons that did not come
INPUT_SECONDS = 1.0  # Echoing Strike on no input for this long (another skill selected) before it is a stopped fight
MISSES_IN_A_ROW = 5  # fights that stopped one after another before attack mode gives up
IDLE_LOG_SECONDS = 3.0  # between log lines on what attack mode sees while nothing is in reach

Remembered = Callable[[int], list[tuple[int, float, float, bool]]]  # area -> (unit id, x, y, leader)


@dataclass
class Sweep:
    """The mode moving on its own after a pickup request with hostiles near. It is on while it has
    steps left and its last step or request is no older than FOLLOW_SECONDS; the player's own move
    and STEP_FAILURES failed steps in a row end it. A place a walk failed for is left alone for
    SHUN_SECONDS."""

    steps: int = 0  # steps it may still take; 0: off
    until: float = -math.inf  # clock time it ends at unless a step or a request renews it
    looked: float = -math.inf  # clock time of its last look for a better place
    fails: int = 0  # steps that failed one after another
    shunned: list[tuple[Point, float]] = field(default_factory=list)  # places a step failed for, and when

    def start(self, now: float) -> None:
        self.steps, self.until, self.fails = FOLLOW_STEPS, now + FOLLOW_SECONDS, 0

    def end(self) -> None:
        self.steps = 0

    def spend(self, now: float) -> None:
        """One step is taken: counted, and the sweep goes on from it."""
        self.steps -= 1
        self.until = now + FOLLOW_SECONDS

    def due(self, now: float) -> bool:
        """Whether a fight under way should look for a better place now."""
        return self.steps > 0 and self.looked + FOLLOW_CHECK <= now <= self.until

    def forget(self, now: float) -> None:
        self.shunned = [(spot, at) for spot, at in self.shunned if now - at < SHUN_SECONDS]

    def shuns(self, spot: Point) -> bool:
        return any(math.dist(spot, left) < SHUN_UNITS for left, _ in self.shunned)

    def failed(self, now: float, walked: Point | None) -> None:
        """A step moved nothing; `walked` is where it was walked to, a place then left alone."""
        self.fails += 1
        if walked is not None:
            self.shunned.append((walked, now))
        if self.fails >= STEP_FAILURES:
            self.end()


def hostiles(world: World) -> list[Monster]:
    """Live monsters the hunt may strike: not owned, not allied, not townsfolk, scenery, a siege door
    or wall, a cast Hydra or a bird in the air, placed."""
    return [
        m
        for m in world.monsters
        if m.owner == NO_OWNER
        and not m.ally
        and (m.x or m.y)
        and m.txt_id not in UNKILLABLE
        and m.txt_id not in HYDRAS
        and m.txt_id not in TOWN_NPCS
        and m.txt_id not in BARRICADES
        and not (m.txt_id in VULTURES and m.mode in AIRBORNE)
    ]


def strike_input(run: Run, world: World, key_names) -> tuple[tuple[str, ...], str]:
    """(what to hold, how to say it) for Echoing Strike: the right mouse button when it holds the
    skill (as the player casts it), else its skill key, else the left button with Shift."""
    player = world.player
    assert player is not None
    if player.right_skill == ECHOING_STRIKE:
        return ('Button3',), 'right click'
    if ECHOING_STRIKE in world.slots:
        try:
            run.keys.update(key_names(world, (ECHOING_STRIKE,)))
            return (run.keys[ECHOING_STRIKE],), f'key {run.keys[ECHOING_STRIKE]}'
        except Abort as problem:
            LOG.info('Macro: %s; trying the left mouse button', problem)
    if player.left_skill == ECHOING_STRIKE:
        return ('Shift_L', 'Button1'), 'Shift+click'
    raise Abort(
        f'Echoing Strike is on no skill key and on neither mouse button '
        f'(left {skill_name(player.left_skill)}, right {skill_name(player.right_skill)})'
    )


class Hunter:
    """The hunt's state across presses: the level and what is remembered of it come from the level
    guide and the terror tracker (callables, set by the service), sigils and marks from the clock."""

    def __init__(
        self,
        level: Callable[[], Level | None] | None = None,
        remembered: Remembered | None = None,
        explored: Callable[[int], set[tuple]] | None = None,
        policy: Policy | None = None,
    ) -> None:
        self.level = level
        self.remembered = remembered
        self.explored = explored
        self.policy: Policy = policy or LinePolicy()  # where to cast (combat/policy.py)
        self.score = LiveScore()  # the last minute of attack mode: damage and kills (combat/score.py)
        self.rotation = Rotation(lambda: self.policy)  # the casts under the held strike (rotation.py)
        self.travel = Travel()  # the jumps the character can make and the moves made with them (travel.py)
        self.route: tuple[int, list[Bounds]] = (0, [])  # (level, the rooms the explore steps go to stand in, in order)
        self.vanished: set[int] = set()  # remembered monsters that were not where they were seen
        self.tested: dict[int, tuple[int, int]] = {}  # unit -> (casts with the line through it, its life then)
        self.untouchable: dict[int, float] = {}  # unit -> clock time until which it is left alone
        self.swap_failed_at = -math.inf  # clock time a swap to the main weapons last did not come
        self.move: Move | None = None  # the move the player asked for and has not got yet: before any strike
        self.left_down = False  # the left mouse button at the last look
        # (where, since when, said) the character has been walking or running without getting anywhere
        self.ran: tuple[Point, float, bool] | None = None
        self.fresh_press = False  # a press seen since `nap` last began
        self.casting = False  # a cast runs or the strike input is held: a click now may be swallowed
        # The pickup step during attack mode (runner): the mode pauses itself once nothing is left in reach.
        self.after_fight = threading.Event()
        # The same request also asks for a step to a better stand (the runner sets both).
        self.step_asked = threading.Event()
        self.unwait: Callable[[], None] | None = None  # tells the runner the press has nothing to pick up after all
        self.pick: Callable[[], None] | None = None  # the runner's: the pickup step runs once the mode has paused
        self.gather_looked = -math.inf  # clock time of the sweep's last look for something to pick up
        self.gather_waited = -math.inf  # clock time the sweep last said it leaves a drop for later
        self.gathered: dict[int, int] = {}  # unit id -> times the sweep stopped for it
        self.held: Drop | None = None  # the valuable in sight the sweep stays by (`gather`, `leaves`)
        self.held_said: set[int] = set()  # the drops that staying was said for
        self.held_logged = -math.inf
        self.stepping: Step | None = None  # the step the fight stopped for
        self.sweep = Sweep()
        self.step_asked_at: float | None = None  # clock time of a step taken, until the first cast after it

    def foes(self, world: World, now: float) -> list[Monster]:
        """The hostiles the hunt goes for: `hostiles` without the ones left alone as untouchable."""
        self.untouchable = {unit: until for unit, until in self.untouchable.items() if until > now}
        return [m for m in hostiles(world) if m.unit_id not in self.untouchable]

    def untouched(self, run: Run, prey: Monster, casts: int) -> bool:
        """Count `casts` new casts with the line through `prey`; whether it is to be left alone now: its
        life reads and has not gone down in UNTOUCHED_CASTS of them."""
        if not prey.max_life:
            return False
        seen, life_then = self.tested.get(prey.unit_id, (0, prey.life))
        if prey.life < life_then:
            seen, life_then = 0, prey.life
        seen += casts
        self.tested[prey.unit_id] = (seen, life_then)
        if seen < UNTOUCHED_CASTS:
            return False
        del self.tested[prey.unit_id]
        self.untouchable[prey.unit_id] = run.clock() + UNTOUCHABLE_SECONDS
        LOG.info(
            'Macro: %s takes no damage (%s after %d casts through it): left alone for %.0fs',
            label(prey), life(prey), seen, UNTOUCHABLE_SECONDS,
        )  # fmt: skip
        run.say(f'{label(prey)} takes no damage: left alone')
        return True

    def known_level(self, player) -> Level | None:
        level = self.level() if self.level is not None else None
        return level if level is not None and level.area == player.area else None

    def seek(self, run: Run, key_names, *, any_hostile: bool = False) -> None:
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
        near = [m for m in leaders if in_reach(ground, here, (m.x, m.y), REACH, doors)]
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

    def go(self, run: Run, level: Level, ground: Ground, player, rect, mob, name: str, doors, key_names) -> None:
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

    @staticmethod
    def charges(run: Run) -> int | None:
        """Charges left on the Teleport staff; None without one (Teleport as a skill, or none at all)."""
        staff = run.teleport() if run.teleport is not None else None
        return None if staff is None else staff.charges

    def afoot(self, run: Run, ground: Ground, player, rect, goal: Point, name: str, key_names) -> bool:
        """A seek step that spares the staff: a stride straight toward `goal` (`stride`). A Blade Warp
        over a clear line whatever the staff holds (it costs no charge and no weapon swap: of the 106
        seek hops in the 26 games of 2026-10-11 in the Halls of Vaught, 78 had the line); with fewer
        than LOW_CHARGES also one click's walk. Whether it was made: with no such stride a hop is
        still made while a charge is left, and with none the step stops."""
        left = self.charges(run)
        low = left is not None and left < LOW_CHARGES
        world = run.world()
        aspect = rect[2] / rect[3]
        # A Blade Warp just made: its casting delay is waited out when the line toward the goal is
        # clear, as presses come faster than it (0.5 s apart against 0.8 s: in the game of 15:27 on
        # 2026-10-11, 8 seek hops by Teleport to 4 by Blade Warp before the staff ran low).
        here = (player.x, player.y)
        away = math.dist(here, goal)
        wait = WARP_DELAY - (run.clock() - self.travel.warped_at)
        if 0 < wait <= WARP_DELAY and BLADE_WARP in world.slots and away > MOVED:
            reach = min(1.0, JUMP_REACH / away)
            end = (here[0] + (goal[0] - here[0]) * reach, here[1] + (goal[1] - here[1]) * reach)
            if clear_shot(ground, here, end, world.doors):
                run.pace.sleep(wait)
                world = run.world()
        found = self.travel.stride(run, world, ground, aspect, goal)
        if found is not None and found.skill != BLADE_WARP and not low:
            return False  # a walk, or a Teleport of the stride's own: the hop plans a better one
        if found is None:
            if left is None or left:
                if low:
                    LOG.info('Macro: %d charges left and no Blade Warp or walk leads toward %s: a hop', left, name)
                return False
            raise Abort(f'the Teleport staff has no charges left, and no Blade Warp or walk leads toward {name}')
        by = 'Walking' if found.skill is None else skill_name(found.skill)
        run.say(f'{by} toward {name}' + (f': the Teleport staff has {left} charges left' if low else ''))
        self.travel.make(run, found, world, aspect, key_names, ground, name=name)
        return True

    def boss_step(self, run: Run, target: Target, key_names) -> bool:
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
        if in_reach(ground, mark, at, REACH, world.doors):
            return False  # the mark is a stand with a shot at it: the step goes there as ever
        here = (player.x, player.y)
        LOG.info(
            'Macro: no shot at %s from the mark of %s, %.0f from it: the step goes for the boss, %.0f away',
            label(boss), target.label, math.dist(mark, at), math.dist(here, at),
        )  # fmt: skip
        if in_reach(ground, here, at, REACH, world.doors):
            run.say(f'{label(boss)} is in reach: attack mode takes it')
            return True
        self.go(run, level, ground, player, rect, at, label(boss), world.doors, key_names)
        return True

    def warp_hop(self, run: Run, target: Target, player, spot: Point, key_names) -> bool:
        """The teleport step's hop toward the landing `spot` made by Blade Warp, and whether it was
        with fewer than WARP_CHARGES on the staff and the blade's line to the landing clear. Its
        casting delay is waited out; a wall, or a warp that moved nobody, leaves the hop to Teleport."""
        world = run.world()
        rect = run.actuator.keys.focused_window_rect()
        if BLADE_WARP not in world.slots or world.player is None or rect is None or key_names is None:
            return False
        left = self.charges(run)
        if left == 0:
            return self.empty_hop(run, target, player, spot, key_names)
        # Only to spare the last charges (user, 2026-10-11 evening: "KP_4 when forcing blade warp is
        # way too slow ... prefer tp for longer distances, until around 15 charges, then blade warp
        # in priority; this is only for charges"): a warp hop took 0.8 to 1.0 s for 18 to 20 units,
        # a Teleport hop 0.6 s for 30.
        if left is None or left >= WARP_CHARGES:
            return False
        wait = WARP_DELAY - (run.clock() - self.travel.warped_at)
        failed = self.travel.jump_failed.get(BLADE_WARP, -math.inf)
        if wait > WARP_DELAY or run.clock() - failed < WARP_RETRY:
            return False
        # One warp that moved nobody does not take the skill from the step for JUMP_DISTRUST as it
        # does from the sweep: Black Marsh, 18:07:38 on 2026-10-11, the third hop's warp failed and
        # the 43 hops after it were Teleports (3 warps in the game). 44 of 447 warps failed that day.
        self.travel.jump_failed.pop(BLADE_WARP, None)
        ground = Ground(target.ground)
        here = (player.x, player.y)
        if not clear_shot(ground, here, spot, world.doors):
            return False
        if wait > 0:
            run.pace.sleep(wait)
            world = run.world()
        aspect = rect[2] / rect[3]
        found = self.travel.stride(run, world, ground, aspect, spot)
        if found is None or found.skill != BLADE_WARP:
            return False
        run.say(f'Blade Warp toward {target.label}: {left} charges kept')
        try:
            self.travel.make(run, found, world, aspect, key_names, ground, name=target.label)
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            LOG.info('Macro: no Blade Warp toward %s (%s): the hop is a Teleport', target.label, stop)
            return False
        return True

    def empty_hop(self, run: Run, target: Target, player, spot: Point, key_names) -> bool:
        """The teleport step's hop with the staff empty: a Blade Warp toward the landing the way gives
        (its casting delay waited out), else one click's walk toward it; made, or the step stops."""
        rect = run.actuator.keys.focused_window_rect()
        if rect is None:
            raise Abort('no game window')
        wait = WARP_DELAY - (run.clock() - self.travel.warped_at)
        if 0 < wait <= WARP_DELAY:
            run.pace.sleep(wait)
        self.travel.jump_failed.pop(BLADE_WARP, None)
        world = run.world()
        ground = Ground(target.ground)
        aspect = rect[2] / rect[3]
        found = self.travel.stride(run, world, ground, aspect, spot)
        if found is None:
            raise Abort(f'no Blade Warp or walk leads along the way to {target.label}')
        by = 'Walking' if found.skill is None else skill_name(found.skill)
        run.say(f'{by} toward {target.label}: the Teleport staff has 0 charges left')
        self.travel.make(run, found, world, aspect, key_names, ground, name=target.label)
        return True

    def foot_step(self, run: Run, target: Target, key_names) -> None:
        """The teleport step with the staff empty (teleport.step_toward `afoot`): a Blade Warp or a walk
        straight toward the mark."""
        player, rect = ready(run)
        goal = (target.point[0] * TILE_UNITS, target.point[1] * TILE_UNITS)
        self.afoot(run, Ground(target.ground), player, rect, goal, target.label, key_names)

    def step(self, run: Run, key_names) -> None:
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
        self,
        world: World,
        foes: list[Monster],
        ground: Ground,
        aspect: float,
        gain: float = CAMP_GAIN,
        run: Run | None = None,
    ) -> Camp | None:
        """The place worth going to from where the character stands (combat/stance.py `camp`), or
        None: in view, as a click or a jump is aimed at it, and priced by the way the character will
        take there (`jumps`, with `run`; a walk without)."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT + CAMP_REACH]
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        seen = observe(player, near, companions, ground, world.doors)
        policy = self.policy if isinstance(self.policy, LinePolicy) else LinePolicy()
        jumps = () if run is None else self.travel.jumps(run, world)
        return camp(
            seen,
            policy,
            no_footing(ground, world.doors),
            shown=lambda spot: (
                in_view(ground_fraction(player, spot[0], spot[1], aspect)) and not self.sweep.shuns(spot)
            ),
            gain=gain,
            jumps=jumps,
        )

    def next_step(
        self, run: Run, world: World, foes: list[Monster], ground: Ground, aspect: float, *, fighting: bool
    ) -> Step | None:
        """The sweep's one look for a move, from wherever it looks: the place worth going to
        (`better_stand`), which in a fight has to be worth SWEEP_GAIN times the place the character
        fights from and with nothing in reach CAMP_GAIN times nothing; and with nothing in reach and
        no such place, a stride toward the nearest hostile (`toward`). None: stay."""
        self.sweep.forget(run.clock())
        place = self.better_stand(world, foes, ground, aspect, SWEEP_GAIN if fighting else CAMP_GAIN, run)
        found = Step.to(place) if place is not None else None
        if found is None and not fighting and foes:
            found = self.toward(run, world, foes, ground, aspect)
        if found is not None and self.leaves(found.spot, run.clock()):
            return None
        return found

    def leaves(self, spot: Point, now: float) -> bool:
        """Whether a step of the sweep's own to `spot` would leave the valuable it stays by (`held`):
        further than HOLD_UNITS from it. The sweep clears what it reaches from within that radius
        (user, 2026-10-11: "we shouldn't move away from valuable drops", "stay in radius, clear
        around to be safe")."""
        held = self.held
        if held is None or math.dist(spot, (held.x, held.y)) <= HOLD_UNITS:
            return False
        if now - self.held_logged >= 1.0:
            self.held_logged = now
            LOG.info(
                'Macro: the sweep stays by %s at (%.0f, %.0f): no step to (%.1f, %.1f), %.0f from it',
                held.label, held.x, held.y, *spot, math.dist(spot, (held.x, held.y)),
            )  # fmt: skip
        return True

    def gather(self, run: Run, here: Point, foes: Sequence[Monster] = ()) -> None:
        """The sweep picks up on its way (user, 2026-10-11: "when doing KP_1 auto-movement, we should also
        auto-pickup items/gold"): with the sweep on and something the pickup step would take
        (pickup.choose), the mode pauses for that step as for a press (Cancelled) and sweeps on after.
        A drop is stopped for GATHER_TRIES times at most: one no click takes must not hold the mode."""
        now = run.clock()
        if self.pick is None or run.loot is None or not self.sweep.steps or now > self.sweep.until:
            self.held = None
            return
        if now - self.gather_looked < GATHER_CHECK:
            return
        self.gather_looked = now
        loot = unshunned(run.loot(), now)
        plan = choose(loot, here)
        if plan is not None:
            # Not with a hostile beside the character or the drop: the stop ends the fight for the
            # walk and the clicks. Tower Cellar 5, 22:50:55 on 2026-10-11: the sweep stopped for a
            # potion 15 away with four hostiles within 10 (eight a second later), the clicks took
            # nothing for 5 s with a monster over the label, and the character died there, the
            # last 1000 of its life in under a second. The drop waits until the place is clear.
            drop = (plan.drop.x, plan.drop.y)
            close = [m for m in foes if min(math.dist((m.x, m.y), here), math.dist((m.x, m.y), drop)) <= GATHER_CLEAR]
            if close:
                if now - self.gather_waited >= WAIT_LOG_SECONDS:
                    self.gather_waited = now
                    LOG.info(
                        'Macro: the sweep leaves %s for later: %d hostiles within %.0f of it or the character',
                        plan.drop.label, len(close), GATHER_CLEAR,
                    )  # fmt: skip
                plan = None
        # A valuable in sight the sweep does not take (no room for it, or its clicks took nothing) is
        # stayed by: the Tower, 17:56:14 on 2026-10-11, a Grand Charm came down 20 away, the sweep
        # said nothing, jumped twice and stood 31 from it; the player went back for it by hand.
        near = [d for d in loot.drops if d.kind == VALUABLE and math.dist(here, (d.x, d.y)) <= HOLD_SIGHT]
        self.held = min(near, key=lambda d: math.dist(here, (d.x, d.y))) if near else None
        if plan is None or self.gathered.get(plan.drop.unit_id, 0) >= GATHER_TRIES:
            held = self.held
            if held is not None and held.unit_id not in self.held_said:
                if len(self.held_said) > 200:
                    self.held_said.clear()
                self.held_said.add(held.unit_id)
                why = 'the inventory has no room for it' if not has_room(loot.room, held.size) else 'no click took it'
                away = math.dist(here, (held.x, held.y))
                LOG.info('Macro: the sweep stays by %s, %.0f away: %s', held.label, away, why)
                run.say(f'Staying by {held.label}: {why}')
            return
        if len(self.gathered) > 200:
            self.gathered.clear()
        self.gathered[plan.drop.unit_id] = self.gathered.get(plan.drop.unit_id, 0) + 1
        LOG.info(
            'Macro: the sweep stops for %s, %.0f away from (%.1f, %.1f)',
            plan.drop.label, math.dist(here, (plan.drop.x, plan.drop.y)), *here,
        )  # fmt: skip
        self.sweep.until = now + FOLLOW_SECONDS + GATHER_SECONDS  # the sweep goes on after the pickup
        self.pick()
        raise Cancelled

    def follow_on(self, run: Run, world: World, foes: list[Monster], ground: Ground, key_names) -> bool:
        """The sweep with nothing in reach: the next place if one is worth it, else a stride toward
        the nearest hostile within SWEEP_UNITS, else (a wall between) the seek step's own move onto a
        firing spot at it. Whether a step was taken."""
        player = world.player
        rect = run.actuator.keys.focused_window_rect()
        if run.clock() > self.sweep.until or player is None or rect is None:
            self.sweep.end()
            return False
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SWEEP_UNITS]
        if not near:
            return False
        aspect = rect[2] / rect[3]
        found = self.next_step(run, world, near, ground, aspect, fighting=False)
        LOG.info(
            'Macro: sweeping with %d hostiles near and none in reach, from (%.1f, %.1f): %s',
            len(near), *here, step_line(found, here),
        )  # fmt: skip
        if found is not None:
            self.sweep_to(run, found)
            self.take_step(run, aspect, key_names, ground)
            return True
        level = self.known_level(player)
        if level is None:
            self.sweep.end()
            return False
        # A wall between: onto a firing spot at the nearest, as the seek step goes to an elite, with
        # the pointer held as a step holds it (the mode itself aims once and casts at once).
        nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
        if self.leaves((nearest.x, nearest.y), run.clock()):
            return False
        self.sweep.spend(run.clock())
        drift, steady = run.actuator.drift, run.actuator.steady
        run.actuator.drift, run.actuator.steady = POINTER_DRIFT, True
        try:
            self.go(run, level, ground, player, rect, (nearest.x, nearest.y), label(nearest), world.doors, key_names)
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            LOG.info('Macro: the sweep ends: no way to %s (%s)', label(nearest), stop)
            self.sweep.end()
            return False
        finally:
            run.actuator.drift, run.actuator.steady = drift, steady
        self.sweep.looked = run.clock()
        return True

    def sweep_to(self, run: Run, found: Step) -> None:
        """One of the sweep's own steps is to be taken."""
        self.sweep.spend(run.clock())
        self.stepping = found

    def toward(self, run: Run, world: World, near: list[Monster], ground: Ground, aspect: float) -> Step | None:
        """The sweep with no place worth going to and nothing in reach: a stride toward the nearest
        hostile, to end STAND_OFF short of it. None when there is none (a wall between: the firing
        spot's to find)."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
        return self.travel.stride(
            run, world, ground, aspect, (nearest.x, nearest.y), STAND_OFF, shot=True, shuns=self.sweep.shuns
        )

    def asked_step(self, run: Run, world: World, foes: list[Monster], reachable, ground, aspect) -> Step | None:
        """The pickup request inside a fight. With anything to pick up (pickup.choose: a valuable, gold
        within a jump, a potion the belt wants) the fight stops for the pickup step at once (Cancelled,
        which the runner reads as the mode's pause). With nothing: the step to take now, if one is
        worth it."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        plan = choose(unshunned(run.loot(), run.clock()), here) if run.loot is not None else None
        if plan is not None:
            # What the press asks for comes before the fight: the mode pauses for the pickup step now,
            # as it does with nothing in reach, and fights on after it. First only a valuable did; gold
            # and potions waited for the fight's end, and the steps the same presses made meanwhile
            # took the character away from them (Halls of Vaught, 13:57:08 on 2026-10-11: 5221 gold
            # 12 away, "pickup after: True" three times, then a Blade Warp of 19 and one of 16, and
            # the pile was out of a jump's reach; user: "we left gold on the ground and moved away").
            LOG.info(
                'Macro: pickup asked in the fight with %d of %d hostiles in reach: %s first, %.0f away',
                len(reachable), len(foes), plan.drop.label, math.dist(here, (plan.drop.x, plan.drop.y)),
            )  # fmt: skip
            self.after_fight.clear()
            raise Cancelled
        if run.loot is not None and plan is None:
            self.after_fight.clear()  # nothing to pick up: no pickup step, and so no seek step, after the fight
            if self.unwait is not None:
                self.unwait()
        found = self.next_step(run, world, foes, ground, aspect, fighting=True)
        self.sweep.start(run.clock())
        LOG.info(
            'Macro: step asked in the fight with %d of %d hostiles in reach, from (%.1f, %.1f): %s; pickup after: %s',
            len(reachable), len(foes), *here, step_line(found, here), self.after_fight.is_set(),
        )  # fmt: skip
        if found is None:
            run.say(f'Standing well: no better place within {CAMP_REACH:.0f}')
        return found

    def take_step(self, run: Run, aspect: float, key_names=None, ground: Ground | None = None) -> None:
        """Go to the place the fight stopped for, or the stride's end, by the way it was chosen for
        (`travel`). The player's own move comes first: a press of theirs, a held key or a character
        already going drops the step. A step that fails leaves its place alone for a while."""
        found, self.stepping = self.stepping, None
        world = run.world()
        player = world.player
        if found is None or player is None:
            return
        why = 'a move was asked for' if self.move is not None else self.moving(run, world)
        if why is not None:
            LOG.info('Macro: the step is dropped (%s)', why)
            self.sweep.end()
            return
        try:
            self.travel.make(run, found, world, aspect, key_names, ground)
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            self.sweep.failed(run.clock(), found.spot if found.skill is None else None)
            run.say(f'No step: {stop}')
            LOG.info('Macro: the step to (%.1f, %.1f) failed (%s), %d in a row', *found.spot, stop, self.sweep.fails)
            return
        self.sweep.fails = 0
        self.step_asked_at = self.sweep.looked = run.clock()

    def quarry(
        self, area: int, here, foes: list[Monster], any_hostile: bool = False
    ) -> tuple[tuple[float, float], str] | None:
        """((x, y), name) of the nearest elite (with `any_hostile`: hostile of any kind): live in
        memory first, then remembered."""
        wanted = foes if any_hostile else [m for m in foes if m.leader]
        if wanted:
            nearest = min(wanted, key=lambda m: math.dist(here, (m.x, m.y)))
            return (nearest.x, nearest.y), label(nearest)
        known = self.remembered(area) if self.remembered is not None else []
        live = {m.unit_id for m in foes}
        self.vanished |= {
            unit_id for unit_id, x, y, _ in known if unit_id not in live and math.dist(here, (x, y)) <= VANISH_UNITS
        }
        kept = [
            (x, y)
            for unit_id, x, y, leader in known
            if (leader or any_hostile)
            and unit_id not in live
            and unit_id not in self.vanished
            and unit_id not in self.untouchable
        ]
        if not kept:
            return None
        return min(kept, key=lambda found: math.dist(here, found)), 'the remembered ' + (
            'monster' if any_hostile else 'elite'
        )

    def attack_mode(self, run: Run, key_names) -> None:
        """Attack mode: fight whatever comes into reach until cancelled. Every pause the mode makes, in its own
        loop and inside a mark, a sigil or a swap, looks at the left mouse button every SLICE
        (`Pace.watched`), so no click of the player's goes unseen."""
        with run.pace.watched(lambda: self.sense(run), SLICE, run.clock):
            self._attack_mode(run, key_names)

    def _attack_mode(self, run: Run, key_names) -> None:
        misses, logged_at, waited_at = 0, -math.inf, run.clock()
        self.after_fight.clear()  # a wait left over from a run that ended another way
        self.step_asked.clear()
        self.stepping = None  # a step the last run of the mode was stopped before taking
        entered = run.clock()  # the mode starts anew after every teleport and seek step
        unready_since: float | None = None  # since when Echoing Strike has been on no input (see below)
        run.say('Attack mode on')
        while True:
            world = run.world()  # Cancelled when the runner ends the mode
            self.score.note(run.clock(), world.player, hostiles(world), world.dead)
            if not world.in_game:
                # The lobby or the menu: the mode ends, so the macro request there starts the macro at once.
                raise Abort('attack mode off: the game was left')
            player = world.player
            self.casting = player is not None and player.mode in ACTING
            self.sense(run)
            if self.move is not None and player is not None:
                self.serve_move(run, world)  # the player's move first: no strike while it is pending
                self.nap(run, FRAME)
                continue
            why = None if player is None else self.moving(run, world)
            if player is None or world.open_panels or player.in_town or why:
                if why and run.clock() - waited_at >= WAIT_LOG_SECONDS:
                    waited_at = run.clock()
                    assert player is not None
                    LOG.info('Macro: waiting (%s), at (%.1f, %.1f), mode %d', why, player.x, player.y, player.mode)
                self.step_aside()
                self.nap(run, POLL)  # the player's move (a key, the left button, a run): waited through
                continue
            if self.rotation.purge_due(run, world):
                try:
                    self.rotation.purge(run, world, key_names)
                    run.pause('key')
                except Abort as stop:
                    if run.cancelled.is_set():
                        raise
                    LOG.info('Macro: no Hex: Purge (%s)', stop)
                    self.rotation.purged_at = run.clock()
                continue
            level = self.known_level(player)
            ground = Ground(level.ground if level is not None else ())
            here = (player.x, player.y)
            foes = self.foes(world, run.clock())
            if not any(in_reach(ground, here, (m.x, m.y), REACH, world.doors) for m in foes):
                self.step_aside()
                self.gather(run, here, foes)
                if self.sweep.steps and foes and self.follow_on(run, world, foes, ground, key_names):
                    continue
                if foes and run.clock() - logged_at >= IDLE_LOG_SECONDS:
                    logged_at = run.clock()
                    nearest = min(foes, key=lambda m: math.dist(here, (m.x, m.y)))
                    LOG.info(
                        'Macro: idle: %d hostiles, none in reach; nearest %s %.0f away, shot %s, from (%.0f, %.0f)',
                        len(foes), label(nearest), math.dist(here, (nearest.x, nearest.y)),
                        'clear' if clear_shot(ground, here, (nearest.x, nearest.y), world.doors) else 'blocked', *here,
                    )  # fmt: skip
                self.nap(run, POLL)
                continue
            rect = run.actuator.keys.focused_window_rect()
            if rect is None:
                self.nap(run, POLL)
                continue
            try:
                strike_input(run, world, key_names)
                unready_since = None
            except Abort:
                # Right after a hop the right button still holds Teleport, after a mark Death Mark: the
                # game puts the skill back within a moment, so wait; only an input that stays away is a
                # stopped fight.
                unready_since = run.clock() if unready_since is None else unready_since
                if run.clock() - unready_since < INPUT_SECONDS:
                    self.nap(run, FRAME)
                    continue
            try:
                # The main weapons for a tough pack, and only once the mode has run MAIN_AFTER since the
                # last step: a swap after every hop of a chain of seek steps, and the staff back for the
                # next, costs more standing than it gains. A fight begun earlier is fought with what is
                # held and stops for the swap at that time.
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), REACH, world.doors)]
                boss = any(m.txt_id in BOSSES for m in reachable)  # the chain of hops ended at it
                tough = boss or self.tough(world, reachable)
                settled = boss or run.clock() - entered >= MAIN_AFTER
                held = self.main_weapons(run, world, key_names, swap=settled and tough)
                pause = entered + MAIN_AFTER if tough and not held else None
                self.fight(run, ground, rect[2] / rect[3], key_names, until=pause)
                misses = 0
                self.take_step(run, rect[2] / rect[3], key_names, ground)  # the step the fight stopped for, if any
            except Cancelled:
                raise  # the mode's own pause for a valuable (`asked_step`), or the runner's cancel
            except Abort as stop:
                if run.cancelled.is_set():
                    raise
                misses += 1
                LOG.info('Macro: the fight stopped (%s), %d in a row', stop, misses)
                if misses >= MISSES_IN_A_ROW:
                    raise Abort(f'attack mode off: {misses} fights stopped in a row, the last on "{stop}"') from stop
                self.nap(run, POLL)

    def step_aside(self) -> None:
        """Nothing is being fought: a step that waited for the fight (the pickup step) gets its turn, as a cancel
        the runner reads as a pause."""
        self.step_asked.clear()  # nothing in reach: the request is the pickup step's (its `step` moves)
        if self.after_fight.is_set():
            self.after_fight.clear()
            raise Cancelled

    def firing_target(self, level: Level, ground: Ground, here, mob, name: str, doors=()) -> Target:
        """The target of a hop toward `mob`: the nearest spot on a room with a shot at it, or the monster
        itself. A spot the character all but stands on leaves the hop nothing to gain, which the landing says."""
        spots = firing_spots(ground, mob, STRIKE_REACH, here, doors) or [mob]
        spot = next((s for s in spots if room_at(level.rooms, (s[0] / TILE_UNITS, s[1] / TILE_UNITS))), spots[0])
        tile = (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS)
        LOG.info(
            'Macro: hunting %s at (%.1f, %.1f), %.0f away from (%.1f, %.1f), firing spot (%.1f, %.1f) of %d',
            name, mob[0], mob[1], math.dist(here, mob), here[0], here[1], spot[0], spot[1], len(spots),
        )  # fmt: skip
        return Target(level.area, level.rooms, tile, name, 'hunt', False, level.ground)

    def frontier(self, level: Level, player, rect) -> tuple[float, Room, tuple[int, int]] | None:
        """(tiles by the way, room, tile) of the room to go and stand in next: the first stop of the
        tour that shows every unexplored room (macros/tour.py), by its tile nearest by the way."""
        seen = self.explored(level.area) if self.explored is not None else set()
        here = (player.x / TILE_UNITS, player.y / TILE_UNITS)
        # The far potential: the one the hop there is planned by (teleport.hop_toward).
        origin = Way(
            Target(level.area, level.rooms, here, 'here', 'explore', False, level.ground), Viewport.of(rect), True
        )
        # Where the character can stand in each room: its tile nearest by the way. Not its own room,
        # which showed what it shows when the character came into it.
        nearest: dict[Bounds, tuple[float, Room, tuple[int, int]]] = {}
        for room in level.rooms:
            if room_at((room,), here) is not None:
                continue
            costs = [
                (cost, (x, y))
                for x in range(room.x, room.x + room.width)
                for y in range(room.y, room.y + room.height)
                if (cost := origin.cost.get((x, y))) is not None
            ]
            if costs:
                cost, tile = min(costs)
                nearest[room.x, room.y, room.width, room.height] = (cost, room, tile)
        bounds = [(room.x, room.y, room.width, room.height) for room in level.rooms]
        before = self.route[1] if self.route[0] == level.area else []
        stops = tour(bounds, here, seen, nearest.keys(), before)
        self.route = (level.area, stops)
        return nearest[stops[0]] if stops else None

    def explore(self, run: Run, level: Level, player, rect, key_names, frontier=None) -> None:
        """A hop toward the unexplored room `frontier` names (found here when not given)."""
        found = frontier or self.frontier(level, player, rect)
        if found is None:
            raise Abort('the level is explored and nothing is left to hunt')
        cost, room, (x, y) = found
        LOG.info(
            'Macro: exploring toward room %s at (%d, %d), %.0f tiles by the way, the first of %d stops, '
            '%d explored of %d',
            room.preset, x, y, cost, len(self.route[1]),
            len(self.explored(level.area)) if self.explored is not None else 0, len(level.rooms),
        )  # fmt: skip
        goal = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS)
        if self.afoot(run, Ground(level.ground), player, rect, goal, 'an unexplored room', key_names):
            return
        target = Target(
            level.area, level.rooms, (x + 0.5, y + 0.5), 'an unexplored room', 'explore', False, level.ground
        )
        hop_toward(run, target, player, rect, key_names)

    def main_weapons(self, run: Run, world: World, key_names, *, swap: bool = True) -> bool:
        """The main weapon set in hand for a fight (it has the skill levels and the damage; a hop
        leaves the teleport set in hand); whether it is held, or nothing is known to want. With `swap`
        off it only looks. The next hop swaps the staff back in by itself (teleport.take_teleport). A
        character the macros do not know, or hands that cannot be read, are left as they are; a swap
        that did not come is not asked for again for SWAP_RETRY_SECONDS."""
        loadout = CHARACTERS.get(world.player.name) if world.player is not None else None
        if loadout is None or run.hands is None or run.clock() - self.swap_failed_at < SWAP_RETRY_SECONDS:
            return True
        held = set(run.hands())
        if not held or loadout.battle & held:
            return True
        if not swap:
            return False
        run.keys.update(key_names(world, (SWAP_WEAPONS,)))
        run.battle_hands = loadout.battle
        run.say('Main weapons for the fight')
        take_battle_weapons(run)
        if not loadout.battle & set(run.hands()):
            self.swap_failed_at = run.clock()
        return True

    def sense(self, run: Run) -> bool:
        """Look at the left mouse button; a press is a move asked for (`self.move`). True on a new press."""
        down = run.actuator.button_held(1)
        pressed = down and not self.left_down
        self.left_down = down
        if pressed:
            self.sweep.end()  # the player moves by hand: no step of the mode's own after it
            self.move = Move(run.clock(), run.actuator.keys.pointer(), swallowed=self.casting)
            self.fresh_press = True
        return pressed

    def nap(self, run: Run, seconds: float) -> bool:
        """Sleep `seconds`, looking at the left button every SLICE (a click is down for 60-120 ms);
        cut short, and True, on a press."""
        until = run.clock() + seconds
        self.fresh_press = False
        while True:
            self.sense(run)
            if self.fresh_press:  # seen here or inside the sleep (attack mode's own `watchful`)
                return True
            left = until - run.clock()
            if left <= 0:
                return False
            run.pace.sleep(min(SLICE, left))

    def serve_move(self, run: Run, world: World) -> None:
        """The move the player asked for comes before any strike (combat/controller.py `serve`): it is
        waited for, and a click a cast may have swallowed is made again for the player where they made
        it (a walk, an item picked up, a door: whatever was under the pointer)."""
        move, player = self.move, world.player
        if move is None or player is None:
            self.move = None
            return
        todo = serve(
            move, run.clock(), (player.x, player.y),
            running=player.mode in RUN_MODES, acting=player.mode in ACTING, left_down=self.left_down,
        )  # fmt: skip
        if todo == PENDING:
            return
        if todo != CLICK:
            if todo == GAVE_UP:
                LOG.info(
                    'Macro: the move asked for %.1fs ago showed nothing after %d clicks',
                    run.clock() - move.at, move.clicks,
                )  # fmt: skip
            self.move = None
            return
        keys = run.actuator.keys
        back = keys.pointer()
        assert move.pixel is not None
        try:
            keys.move_pointer(*move.pixel)
            keys.sync()
            run.actuator.click()
            if back is not None:
                keys.move_pointer(*back)
                keys.sync()
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            LOG.info('Macro: the click for the player was not made (%s)', stop)
            self.move = None
            return
        move.clicked(run.clock())
        LOG.info(
            'Macro: the click the cast swallowed made again at %s, %.2fs after the press (%d of %d)',
            move.pixel, move.clicked_at - move.at, move.clicks, MOVE_CLICKS,
        )  # fmt: skip

    def tough(self, world: World, reachable: list[Monster]) -> bool:
        """Whether what is in reach is worth a swap to the main weapons: TOUGH_POINTS of life between
        them, an elite's counted ELITE_LIFE times. An elite alone is not: the Catacombs packs died
        within a second or two of the swap, which costs most of a second there and back."""
        if world.player is None:
            return False
        seen = observe(world.player, reachable, ())
        return sum(foe.left * (ELITE_LIFE if foe.elite else 1.0) for foe in seen.foes.values()) >= TOUGH_POINTS

    def moving(self, run: Run, world: World, *, keys: bool = True) -> str | None:
        """Why the pointer is the player's right now, or None: a key of theirs is down, the left mouse
        button is down (a move), or the character is walking or running somewhere. Attack mode yields
        to all three: it must never get in the way of moving. With `keys` off a held key is no reason
        (a fight under way: the strike stays held through the player's own key taps)."""
        if keys and run.actuator.key_held():
            return 'a key is held'
        if run.actuator.button_held(1):
            return 'the left button is down'
        if world.player is not None and world.player.mode in RUN_MODES:
            here, now = (world.player.x, world.player.y), run.clock()
            if self.ran is None or math.dist(here, self.ran[0]) >= MOVED:
                self.ran = (here, now, False)
            elif now - self.ran[1] >= RUN_IN_PLACE:
                if not self.ran[2]:
                    self.ran = (*self.ran[:2], True)
                    LOG.info(
                        'Macro: the character runs in place at (%.1f, %.1f) for %.1fs (mode %d): not waited for',
                        *here, now - self.ran[1], world.player.mode,
                    )  # fmt: skip
                return None
            return 'the character is on the move'
        self.ran = None
        return None

    def choose(
        self, world: World, foes: list[Monster], reachable: list[Monster], ground: Ground, view: Viewport
    ) -> Choice:
        """Where to cast now (combat/controller.py `aim_choice`, the decision the simulator scores as
        `live`): the policy's line over the hostiles in sight, else straight at what is in reach, and
        a focal point the window lets the pointer reach. A boss in reach (terror/bosses.py) has the
        line laid through it."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT]
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        seen = observe(
            player, near, companions, ground, world.doors, aimable=lambda focal: view.reachable_focal(here, focal)
        )
        bosses = [m.unit_id for m in reachable if m.txt_id in BOSSES]
        found = aim_choice(self.policy, seen, [m.unit_id for m in reachable], first=bosses)
        assert found is not None  # the caller has something in reach
        return found

    def fight(self, run: Run, ground: Ground, aspect: float, key_names, until: float | None = None) -> None:
        """Strike while anything is in reach and the player stands: one hold of the strike input
        through the whole fight, the pointer kept on the policy's line, which is asked again every
        DECIDE_SECONDS and when its monster is gone. Ends when nothing is in reach, when the player
        moves (the mode yields and comes back after), at `until` (the caller's swap to the main
        weapons), or after FIGHT_SECONDS."""
        started = run.clock()
        held, how = strike_input(run, run.world(), key_names)  # before any cast: no key, no fight
        down = 0
        cast = CastWatch(started)  # the casts seen since the press (combat/controller.py)
        choice: Choice | None = None
        decided_at = -math.inf
        aim = Aim((run.actuator.keys.pointer(), -math.inf))  # where the pointer was put, and the player's hand
        view = Viewport(aspect)
        again: Callable[[], None] | None = None
        watched: set[int] = set()  # the hostiles seen in reach while the input was held
        lined: int | None = None  # the monster the line last logged went through
        counted = 0  # the casts seen up to the last look
        ended = f'Fight stopped after {FIGHT_SECONDS:.0f}s'
        with ExitStack() as stack:
            stack.callback(setattr, self.rotation, 'let_go', None)
            while run.clock() - started < FIGHT_SECONDS:
                world = run.world()
                player = world.player
                if player is None:
                    raise Abort('not in a game')
                if player.mode in DEAD:
                    raise Abort('the character is dead')
                alive = {m.unit_id for m in world.monsters}
                down += len(watched - alive)
                watched &= alive
                held_input = cast.step(run.clock(), player.mode in ACTING) if again is not None else None
                if held_input == NO_CAST:
                    raise Abort(f'no cast seen after the {how} (Echoing Strike not on {how}?)')
                self.casting = again is not None or player.mode in ACTING
                self.sense(run)
                why = 'a move was asked for' if self.move is not None else self.moving(run, world, keys=again is None)
                if why is not None:
                    ended = f'Yielded ({why})'
                    break
                if held_input == RETAP and again is not None:
                    # After the look at the player's move, never before it: a click just made is yielded
                    # to with the input let go, not answered with a new press (review.md, finding 7).
                    again()
                here = (player.x, player.y)
                foes = self.foes(world, run.clock())
                self.score.note(run.clock(), player, foes, world.dead)
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), REACH, world.doors)]
                if not reachable:
                    ended = 'Nothing left in reach'
                    break
                if until is not None and run.clock() >= until:
                    if self.tough(world, reachable) or any(m.txt_id in BOSSES for m in reachable):
                        ended = 'Stopping for the main weapons'  # attack mode takes them and fights on
                        break
                    until = None  # what is left is not worth the swap any more: fought on as it is
                if again is not None and run.actuator.key_held():
                    # A key of the player's (a skill of their own, a potion): the strike stays held, as
                    # their own hand would hold it, and the macro's own aims and keys wait for the release.
                    if self.nap(run, FRAME):
                        ended = 'Yielded (a move was asked for)'
                        break
                    continue
                if self.step_asked.is_set():
                    self.step_asked.clear()
                    self.stepping = self.asked_step(run, world, foes, reachable, ground, aspect)
                    if self.stepping is not None:
                        ended = 'Stepping to a better place'
                        break
                if self.sweep.steps:
                    self.gather(run, here, foes)
                if self.sweep.due(run.clock()):
                    # The sweep: a better place is gone to without a press.
                    self.sweep.looked = run.clock()
                    better = self.next_step(run, world, foes, ground, aspect, fighting=True)
                    if better is not None:
                        LOG.info(
                            'Macro: sweeping in the fight with %d of %d hostiles in reach, from (%.1f, %.1f): %s',
                            len(reachable), len(foes), *here, step_line(better, here),
                        )  # fmt: skip
                        self.sweep_to(run, better)
                        ended = 'Stepping to a better place'
                        break
                if self.step_asked_at is not None and cast.casts:
                    LOG.info('Macro: first cast %.2fs after the step', run.clock() - self.step_asked_at)
                    self.step_asked_at = None
                # The aim is kept only on what is a foe now: a bird that took off or a monster just left
                # alone as untouchable is still alive and no longer one.
                prey = next((m for m in foes if choice is not None and m.unit_id == choice.unit), None)
                if choice is None or prey is None or run.clock() - decided_at >= DECIDE_SECONDS:
                    choice, decided_at = self.choose(world, foes, reachable, ground, view), run.clock()
                    prey = next(m for m in foes if m.unit_id == choice.unit)
                if self.untouched(run, prey, cast.casts - counted):
                    choice = None  # left alone: the next look chooses among the rest
                    counted = cast.casts
                    continue
                counted = cast.casts
                # The strike first, Death Mark and the sigil under it once a cast is out: cast before the
                # press they held the first strike back 0.3 to 0.7 s on 190 of 405 fight starts (logs of
                # 2026-10-10, tests/inventory_tracking/scenarios/loop). The first cast flies unmarked.
                struck = again is not None and (cast.casts > 0 or run.clock() - cast.began >= FIRST_STRIKE_SECONDS)
                if struck and self.rotation.purge_due(run, world):
                    self.casting = True
                    self.rotation.purge(run, world, key_names)
                    cast.excuse(run.clock())
                    self.rotation.resume(run, again)
                if struck and run.clock() - self.rotation.marked_at > DEATH_MARK_SECONDS and DEATH_MARK in world.slots:
                    strongest = max(reachable, key=lambda m: (m.leader, m.max_life, -math.dist(here, (m.x, m.y))))
                    if self.rotation.worth_a_mark(world, strongest):
                        self.casting = True  # the mark's own cast swallows a click as a strike does
                        self.rotation.death_mark(run, strongest, aspect, key_names)
                        aim.forget()
                        cast.excuse(run.clock())  # the mark's own cast is no missing strike
                        self.rotation.resume(run, again)
                if struck and self.rotation.sigil_due(run, prey):
                    self.casting = True
                    self.rotation.sigil(run, world, prey, aspect, key_names)
                    aim.forget()
                    cast.excuse(run.clock())
                    self.rotation.resume(run, again)
                if struck and ENGORGE in world.slots and self.rotation.engorge_due(run, world):
                    self.casting = True
                    if self.rotation.engorge(run, world, aspect, key_names):
                        aim.forget()
                        cast.excuse(run.clock())
                        self.rotation.resume(run, again)
                pointer, left_at = run.actuator.keys.pointer(), run.actuator.left_at
                if aim.due(run.clock(), pointer, left_at, choice.focal, here):
                    where = view.aim(here, choice.focal)
                    if where is None:
                        ended = f'Nothing in view to aim at ({label(prey)} is off the screen)'
                        break
                    run.actuator.aim(*where, scatter=(3, 3))
                    aim.put(choice.focal, here, run.actuator.keys.pointer())
                if again is None:
                    run.say(f'Echoing Strike ({how}) at {label(prey)}, {life(prey)}')
                    again = stack.enter_context(run.actuator.hold(*held))
                    self.rotation.let_go = getattr(again, 'release', None)  # for a key under the strike
                    cast.began = run.clock()
                    self.casting = True  # the strike is held from here to the end of the fight
                if prey.unit_id != lined:
                    lined = prey.unit_id
                    LOG.info(
                        'Macro: line through %s, %s, %.1f away, focal (%.1f, %.1f), worth %.0f, pointer %s',
                        label(prey), life(prey), math.dist(here, (prey.x, prey.y)), *choice.focal, choice.worth,
                        run.actuator.keys.pointer(),
                    )  # fmt: skip
                watched |= {m.unit_id for m in reachable}
                if self.nap(run, FRAME):
                    ended = 'Yielded (a move was asked for)'
                    break
        down += len(watched - {m.unit_id for m in run.world().monsters})
        seconds = run.clock() - started
        LOG.info('Macro: fight (%s): %d casts seen in %.1fs, %d down; %s', how, cast.casts, seconds, down, ended)
        run.say(f'{ended}: {down} down in {cast.casts} casts')
        if cast.casts:
            run.say(f'Last minute: {self.score.line()}')  # the HUD card's standing line between fights
