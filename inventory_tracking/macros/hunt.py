"""Attack mode and the seek step. The toggle turns attack mode on and off; the seek step goes toward
the nearest unique or champion and leaves attack mode on. The history of each rule is in macros/plan.md.

Attack mode (`Hunter.attack_mode`, a run that lives until cancelled): everything within the reach of
the build's attack (macros/build.py `Attack.reach`) with a clear shot (sight.py: the flight layer of
the read grids, closed doors) is fought while the player moves about as they like. The mouse, the
keyboard and the character's own moves and casts are not cancels: only its toggle or the macro request
ends it, the game being left, or MISSES_IN_A_ROW fights
that stopped one after another. The player's hand is on the mouse all along, so the actuator aims
once and casts at once (`Actuator.steady` off). the teleport and seek steps work meanwhile: the runner pauses the
mode for the step and resumes it after (runner.py).

A fight (`Hunter.fight`) is one hold of the input that has the attack's skill (the Warlock's Echoing
Strike): the right mouse button when it holds the skill, else its skill key, else a left click with
Shift. The game casts at its own rate; an input idle RETAP_SECONDS is released and pressed again. The
pointer is kept where the attack aims (`Attack.aim`; for the Warlock the line of combat/policy.py, the
decision the simulator scores); a monster in reach the attack finds no cast for is aimed at directly,
the elite first, then the nearest, AIM_BEYOND past it. The
build's buffs are cast under the strike and kept up between fights by its buff plan (buffs.py; for the
Warlock builds/warlock/buffs.py: a sigil under an elite, Death Mark on the strongest monster in reach).
The main weapon set is swapped in for a tough or hard-hitting pack (`tough`).

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
import time
from collections.abc import Callable, Sequence
from contextlib import ExitStack, contextmanager, nullcontext
from dataclasses import dataclass, field, replace

from inventory_tracking.automation.priority import reserve
from inventory_tracking.combat import threats
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
from inventory_tracking.combat.escort import around, escorts, in_danger, kept_alive
from inventory_tracking.combat.harm import harm
from inventory_tracking.combat.policy import (
    MIN_FOCAL,
    RUN_MODES,
    STRIKE_REACH,
    Choice,
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
from inventory_tracking.combat.survival import pressure
from inventory_tracking.common import LOG
from inventory_tracking.config import HEAL_PRIORITY
from inventory_tracking.levels.model import Ground, Level, Room, Target
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros import route
from inventory_tracking.macros.actuator import POINTER_DRIFT, Abort, Cancelled
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import Attack, Build, NoWay, PricedStep
from inventory_tracking.macros.drinking import Drinker, key_of, on_belt
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import (
    CLEAR_WAY,
    PICK_NEAR,
    PICK_REACH,
    PICK_UP,
    REACH,
    WAIT,
    Goal,
    boss_ahead,
    clear_way,
    first_fight,
    goal_of,
    in_the_way,
    nearer,
    rest_of_level,
)
from inventory_tracking.macros.movement import WALKS, WARPS
from inventory_tracking.macros.pad import MONSTER_UNIT
from inventory_tracking.macros.pickup import POTION_UNITS, choose, pick_up, shortages, unshunned, worth_a_stop
from inventory_tracking.macros.pursuit import (
    NONE,
    PASSAGE,
    SETTLE,
    Act,
    Candidate,
    Defer,
    Ended,
    Facts,
    Hold,
    Move as Advance,
    Operate,
    Pursuit,
    Told,
    decide,
    settled,
)
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.routines import (
    ACTING,
    DEAD,
    SUPER_UNIQUE_FLAG,
    TOWN_NPCS,
    take_battle_weapons,
)
from inventory_tracking.macros.runmode import DOUBLE, Mode, Taps, aim_of, doubles, mode_of, said, tapped
from inventory_tracking.macros.safety import AWAY, STEPPING, WAY_SHARE, Safety
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach, in_reach as in_reach_of
from inventory_tracking.macros.skillpanel import select_right
from inventory_tracking.macros.skills import (
    SWAP_WEAPONS,
    TELEPORT,
    skill_name,
)
from inventory_tracking.macros.supply import Potions, detour, low, restock, worth
from inventory_tracking.macros.teleport import (
    HOVER_SECONDS,
    MOVED,
    SPOT_NEAR,
    USES,
    Covered,
    Way,
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
from inventory_tracking.macros.tour import Bounds, tour
from inventory_tracking.macros.travel import (
    AROUND_LEAST,
    GROWING,
    KEY_POLL,
    OWN_MOVE,
    PLAYER_STEP,
    PRESSED,
    SAFE_MOVE,
    SEEK,
    STANDING,
    Point,
    Step,
    Tally,
    Travel,
    attackable,
    clear_line,
    facts_with,
    label,
    life,
    navigator,
    planning,
    spare_jump,
    step_line,
    step_walk,
    walk_reaches,
    walked_length,
)
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import (
    HEALING,
    NO_OWNER,
    REJUVENATION,
    VALUABLE,
    Drop,
    Loot,
    Monster,
    Teleport,
    World,
    has_room,
)
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, FIGHT, STAND, USE, Script
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.bosses import BOSSES
from inventory_tracking.terror.danger import Unit, packs
from inventory_tracking.terror.tracker import BARRICADES, UNKILLABLE


# monstats.txt hydra1-3 (AI Hydra, no life of their own): the fire heads the Council casts, which never die
# and are left out of the hostiles
HYDRAS = frozenset((351, 352, 353))
# monstats.txt MonType `vulture` (vulture1-5: combat/data/tables.json): the birds the blades pass through in the air
# (AIRBORNE: their modes 1 and 8); on the ground they are fought like other monsters
VULTURES = frozenset((110, 111, 112, 113, 608))
AIRBORNE = frozenset((1, 8))
FIRST_STRIKE_SECONDS = 0.3  # the held strike this long with no cast seen yet: the mark and sigil wait no longer
WALK_CLICKS = 2  # clicks for one walk to a firing spot
WALK_UNITS = 10.0  # a firing spot this near, over clear ground, is walked to, not teleported to (as NEAR_WARP)
# A held key whose act stays the strike hears its reason again after this many seconds (`tell`): the card
# answers the presses (I6) without a line at every press of a mashed key.
SAID_AGAIN = 1.2
FIGHT_SECONDS = 60.0  # one fight ends here at the latest; attack mode looks again right after
POLL = 0.1  # seconds between looks in attack mode while nothing is fought
MOO_MOO_FARM = 39  # levels.txt: the Secret Cow Level
FRAME = 0.04  # seconds between looks during a fight: one game frame, so a move of the player's is yielded to at once
DECIDE_SECONDS = 0.12  # between two askings of the policy while its monster lives
# A look of the pursuit's that took longer than this has its move or use dropped (`Hunter.stale`): two and a half
# askings of the policy (DECIDE_SECONDS), above the clean game's look gap with a hostile near (0.24 s at the median,
# rca/2026-10-14/run-2040-findings.md §2.1), some 3 units of a run. STALE_MOVED: units the character may stand from
# where a second slow look in a row saw it for its act to be made (the host slow, the game the same).
STALE_LOOK = 0.3
STALE_MOVED = 2.0
SIGHT = 30.0  # world units: hostiles further off are not part of the decision
# World units: a boss attack mode goes to by itself (no level run, no fresh press: pursuit.py `decide`), as far as a
# boss standing within SIGHT of a hostile the fight sees can be: the Vizier's stall (57.4 off, his pack 19 to 51
# off; kp4-findings.md) is in it, Izual by the card's mark after a level run ended on a level change (342 off;
# run-2040-findings.md §5, the player's ruling 2026-10-15: "only nearby") is not: farther goals are KP_1's and KP_4's.
ALONE_BOSS_UNITS = 2 * SIGHT
# The sweep after a step asked for: the mode goes on stepping by itself, to a better place whenever
# there is one and toward the nearest hostile when nothing is in reach, until nothing hostile is within
# SWEEP_UNITS, the player moves by hand, FOLLOW_STEPS are taken or FOLLOW_SECONDS pass with no step.
FOLLOW_STEPS = 12
FOLLOW_SECONDS = 8.0  # since the press or the sweep's last step
BOSS_MARK_UNITS = 60.0  # world units from a level's mark: a boss or super unique this near is the one it marks
GATHER_CLEAR = 12.0  # world units: no hostile this near the character or a drop when the sweep stops for it
HOLD_SIGHT = 40.0  # world units: a valuable this near that the sweep does not take is stayed by
HOLD_UNITS = 25.0  # the sweep's own steps end no further than this from it
GATHER_CHECK = 0.3  # seconds between two looks of the sweep for something to pick up
GATHER_TRIES = 2  # times the sweep stops for one drop (and a level run goes for one, `side_drop`)
# Seconds the monsters the hands found in the way of a goal's act (teleport.py `Covered`) stay the fight that
# comes first for that goal, while any of them lives (goals.py `first_fight`)
BLOCK_SECONDS = 15.0
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
# Units along the line the pointer is tried at when an item's label lies under the aim (`off_labels`).
LABEL_SHIFTS = (0.0, 4.0, 8.0, -3.0, 12.0, -6.0)
ITEM_UNIT_TYPE = 4  # in the record of the unit under the pointer
LABEL_SECONDS = 0.5  # between two looks for a label under a pointer that stands
UNTOUCHABLE_SECONDS = 20.0
# A boss is never left alone so (`untouched`): for this long after its strikes did nothing, the run's fight with it
# is near enough only within the attack's engage ring, and it counts as in reach only there (`nearing_only`)
NEARING_SECONDS = 6.0
# Units: with no hostile this near, a level run is in the quiet: the whole upkeep is asked between its moves, and a
# belt low on potions takes the ones lying near before the goal (`restock`). goals.py CLEAR_WAY: nearer, a hostile
# with a clear line is the run's fight on its way.
QUIET_UNITS = CLEAR_WAY
ROOM_UNITS = 40.0  # a known hostile this much further than the nearest unexplored room still goes first
VANISH_UNITS = 25.0
SLICE = 0.01  # seconds between looks at the left mouse button while the mode waits or fights
TOUGH_POINTS = 40_000.0  # life points in reach from which a pack is worth the main weapons
HARD_SCORE = 4.0  # the threat score (terror/danger.py) of what is in reach from which it is, whatever its life
MAIN_AFTER = 1.0  # seconds after a step before the main weapons are swapped in for a fight
SWAP_RETRY_SECONDS = 5.0  # after a swap to the main weapons that did not come
INPUT_SECONDS = 1.0  # Echoing Strike on no input for this long (another skill selected) before it is a stopped fight
STRIKE_BACK_RETRY = 10.0  # seconds between two tries of the skill selection for the strike (`strike_back`)
MISSES_IN_A_ROW = 5  # fights that stopped one after another before attack mode gives up
IDLE_LOG_SECONDS = 3.0  # between log lines on what attack mode sees while nothing is in reach
# The navigation classes with no Teleport to spend (macros/movement.py `Ways.means`): a step of the old keys toward a
# far place goes by the class's own way there (`class_step`), not by a Teleport landing made some other way.
NO_HOPS = frozenset((WARPS, WALKS))
# Times a casting delay worth it is slept out before such a step (`class_step`): the look after the sleep may read it
# a tick short of its end, and the step was then a walk of 4 units (the arena's seal moment, seed 1)
PAUSES = 3
# The run mode (macros/runmode.py): a level run's fight on its way or of the rest of the level (goals.py
# `clear_way`, `rest_of_level`) that has been gone for CLEAR_SECONDS with no strike and no progress by the way to it
# (its way left, `Travel.eta`, down by PROGRESS_SECONDS at least), or that the navigator has no way to, is passed for
# PASS_SECONDS (across lava, a monster that keeps away, a room no tour reaches): the run goes on. A room has nothing
# to strike: judged by strikes alone, one 119 units off was passed after a run of 153 units toward it in 10 s
# (22:54:12.99 on 2026-10-14, rca/2026-10-14/run-1932-findings.md §1.2.1). Two of its looks further apart than
# JUDGE_GAP with another goal's between are not counted as time gone for it: the goal was another's meanwhile.
CLEAR_SECONDS = 10.0
PASS_SECONDS = 30.0
PROGRESS_SECONDS = 0.25
PROGRESS_LOOK = 1.0  # seconds between two askings of the way left to one clearing goal (`goes_on`)
JUDGE_GAP = 3.0
# Seconds a clearing goal the run has left for another is not taken back while that other is still the run's to go
# for (`Hunter.cleared`): the passed room of 22:54:19 came back in turn with the door eight times in 9.6 s.
TAKE_BACK = 6.0
# The goals a run to its goal fights its way to (`Hunter.cleared`): a door to another level, a place, a stand.
WAYS = frozenset((ENTER, REACH, STAND))
REST_SECONDS = 1.0  # a full clear's look for the rest of the level (the tour's potential) is made this seldom
# Seconds of fighting a buff with a duration has to last through when the route's stage brings a boss (goals.py
# `boss_ahead`): renewed before it in the quiet (macros/buffs.py `lapsing`). The Chaos Sanctuary on 2026-10-14,
# 15:19:24.9 to 49.7: the last seal open to Diablo dead 25 s, his spawn wait in it; at 06:05 23 s; 31 s more of the
# player's hand at 15:19 (run-1214-findings.md §3.4: Consume, 300 s, ran out 300.7 s after the prebuff, in his fight).
BOSS_AHEAD = 60.0

Remembered = Callable[[int], list[tuple[int, float, float, bool]]]  # area -> (unit id, x, y, leader)


@dataclass
class Bearings:
    """What the goal of a key is named from besides the world (macros/goals.py `goal_of`), the runner's
    and handed to the hunt by it: the routes' progress, the level card's first mark and the places of
    its marks by label, the tracker's last-seen places of super uniques and bosses by level."""

    progress: Progress | None = None
    card: Callable[[], Target | None] | None = None
    marks: Callable[[str], tuple[Point, ...]] | None = None
    supers: Callable[[int], list[Point]] | None = None

    def terror(self, area: int) -> bool:
        """Whether level `area` is a terror zone now, by the routes' progress (its `wanted`: terror/tracker.py
        `terrorized`); False while that is not known."""
        wanted = getattr(self.progress, 'wanted', None)
        return bool(wanted(area)) if wanted is not None else False

    def script(self, area: int) -> Script | None:
        """The route's script level `area` follows in this game (routes/progress.py `chosen`); None: no route."""
        chosen = self.progress.chosen(area) if self.progress is not None else None
        return chosen[1] if chosen is not None else None


@dataclass(frozen=True)
class Judged:
    """One look of the pursuit: what was decided, for which goal, and the place the navigator was asked for;
    the mailbox as the look read it, and whether its press was fresh at the look's clock."""

    act: Act
    goal: Goal | None
    place: Point | None
    posted: Pursuit | None = None
    pressed: bool = False


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


def threat(run: Run) -> Callable[[Point, Point], int]:
    """How many hostiles stand within GATHER_CLEAR of the character or of a thing a press would go to
    (pickup.py `Threat`): the sweep's measure of a stop that is safe, for the pickup key's potions and
    chests. Presence, not yet what they could do: the price of a place (Stage 4.3) is to take its place."""

    def near(here: Point, spot: Point) -> int:
        return sum(
            1
            for monster in hostiles(run.world())
            if min(math.dist((monster.x, monster.y), here), math.dist((monster.x, monster.y), spot)) <= GATHER_CLEAR
        )

    return near


def passing_key(place: Point, unit: int | None, rooms: Sequence[Room] = ()) -> object:
    """What a level run's clearing goal is passed and judged by (`Hunter.cleared`): its monster; else the room its
    place lies in (of `rooms`, the level's), else its place to the unit. A room's goal is the tile of it nearest by the
    way from where the character stands (`frontier`), which moves as the character does: keyed by its tile, a room
    passed came back under a new key 5 units on, and the run went back and forth between it and the route's door for
    9.6 s (22:54:19, 2026-10-14, rca/2026-10-14/run-1932-findings.md §1.2.1)."""
    if unit is not None:
        return unit
    room = room_at(rooms, (place[0] / TILE_UNITS, place[1] / TILE_UNITS)) if rooms else None
    if room is not None:  # a large preset's 8 by 8 chunks are one room (`Room.block`, its whole bounds)
        return ('room', *(room.block or (room.x, room.y, room.width, room.height)))
    return (round(place[0]), round(place[1]))


@dataclass
class Judging:
    """How a level run's clearing goal has gone (`Hunter.cleared`): the seconds it has been gone for with no strike
    and no progress by the way (`idle`), the least way left to it seen (`best`, seconds by the means in hand:
    `Travel.eta`), and the look that last judged it. Kept by the goal's key across other goals: the goal coming back
    after another goes on from where it was (the 10-s judge started again at every change of goal, and two goals
    taken in turn were never passed: run-1932-findings.md §1.2.1)."""

    idle: float
    best: float
    last: float
    checked: float = -math.inf  # the look that last asked the way left


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


def strike_input(run: Run, world: World, key_names, skill: int) -> tuple[tuple[str, ...], str]:
    """(what to hold, how to say it) for `skill`, the attack's strike: the right mouse button when it
    holds the skill (as the player casts it), else its skill key, else the left button with Shift. In
    controller mode its pad record (macros/pad.py), held by `Run.pad`: nothing to name for the keys."""
    player = world.player
    assert player is not None
    if run.pad is not None:
        run.keys.update(key_names(world, (skill,)))  # Abort: on no pad record
        return (), f'pad {run.keys[skill]}'
    if player.right_skill == skill:
        return ('Button3',), 'right click'
    if skill in world.slots:
        try:
            run.keys.update(key_names(world, (skill,)))
            return (run.keys[skill],), f'key {run.keys[skill]}'
        except Abort as problem:
            if run.stops(problem):
                raise
            LOG.info('Macro: %s; trying the left mouse button', problem)
    if player.left_skill == skill:
        return ('Shift_L', 'Button1'), 'Shift+click'
    raise Abort(
        f'{skill_name(skill)} is on no skill key and on neither mouse button '
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
        *,
        build: Build,
    ) -> None:
        self.level = level
        self.remembered = remembered
        self.explored = explored
        self.score = LiveScore()  # the last minute of attack mode: damage and kills (combat/score.py)
        # What is the build's and not the framework's: its attack, the ways it moves by and its buff plan.
        # The one the hunt is made with is played until the runner has seen the character and names
        # another (`use`); the process that makes the hunt before any game gives the fallback.
        self.build: Build = build
        # A policy asked where to cast in place of the build's attack (a test's, a harness's): see `policy`
        self.aimed_by: Policy | None = policy
        self.buffs = Buffs(self.build)  # the build's buff plan as it is run, and when each cast was made (buffs.py)
        # The jumps the character can make and the moves made with them (travel.py), by the build's movement sets
        self.travel = Travel(self.build.movement)
        self.route: tuple[int, list[Bounds]] = (0, [])  # (level, the rooms the explore steps go to stand in, in order)
        self.vanished: set[int] = set()  # remembered monsters that were not where they were seen
        self.tested: dict[int, tuple[int, int]] = {}  # unit -> (casts with the line through it, its life then)
        # boss unit -> clock time until which the run gets back in reach of it, the strikes having done nothing from
        # where they were made (`untouched`: a boss is never left alone)
        self.nearing: dict[int, float] = {}
        self.restock_said: set[int] = set()  # the potions a restock went for, said once each (`restock`)
        self.untouchable: dict[int, float] = {}  # unit -> clock time until which it is left alone
        self.swap_failed_at = -math.inf  # clock time a swap to the main weapons last did not come
        self.move: Move | None = None  # the move the player asked for and has not got yet: before any strike
        self.left_down = False  # the left mouse button at the last look
        self.drinker = Drinker(self.build.settings.drink)  # the belt keys beside the fight (drinking.py)
        # The game's clock bounds one look's pricing (`SafetySettings.look_seconds`); the arena's driver takes it off
        self.safety = Safety(timer=time.perf_counter)
        self.dropped = 0  # acts of slow looks dropped in a row (`stale`)
        self.expired_motion = False  # an expired macro click still moving: safety owns the next act
        self.struck_at = -math.inf  # clock time the fight last saw the character cast under the held strike
        self.stands: Point | None = None  # where attack mode last saw the character
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
        self.tried: dict[int, str] = {}  # unit id -> why the last try at it took nothing (an Abort of the hands)
        self.left_said: set[int] = set()  # the drops whose giving up was said
        self.retried: set[int] = set()  # the drops given up and then tried once more (`again`)
        self.round_said: set[int] = set()  # the drops said to be gone to first for want of a clear line (`judge`)
        self.bound_said: set[int] = set()  # the hostiles said to die with a summoner (`bound_lost`)
        self.away_said: set[int] = set()  # the same, said to be no fight to hold (`only_bound`)
        self.held: Drop | None = None  # the valuable in sight the sweep stays by (`gather`, `leaves`)
        self.held_said: set[int] = set()  # the drops that staying was said for
        self.held_logged = -math.inf
        self.stepping: Step | None = None  # the step the fight stopped for
        self.guarding: Advance | None = None  # the safety step the fight stopped for with the pursuit off (`guard`)
        self.sweep = Sweep()
        self.step_asked_at: float | None = None  # clock time of a step taken, until the first cast after it
        # The pursuit (macros/pursuit.py, behind `BuildSettings.pursuit`). `pursuit` is the mailbox the
        # runner posts a press of the teleport key to while attack mode works; the mode names the goal
        # anew at each look and decides (`judge`, `pursue`). A look reads it once, with its clock, and writes
        # it back only over what it read (`swap`): a press posted during a look is the next look's
        # (rca/2026-10-14/run-0025-findings.md §2.1: 6 of 20 pickup presses were dropped by the look under way).
        self.pursuit: Pursuit | None = None
        self.mailbox = threading.Lock()  # the runner's posts and the loop's write-backs, one at a time
        self.bearings = Bearings()  # the runner's: what a goal is named from
        # the runner's: the key's routine (the route's own step) follows the mode's pause
        self.hand_over: Callable[[str], None] | None = None
        self.told = Told()  # the reason last said for a decision that moved nothing
        self.told_at = -math.inf  # clock time it was last said
        self.pursued: Goal | None = None  # the goal of the last decision, for the recorder and the viewer
        self.stopped_for: tuple[float, Drop | None] = (-math.inf, None)  # (the press, the drop it takes first)
        self.judged: tuple[float, float, bool] = (-math.inf, -math.inf, False)  # (the press, when, it asks a move)
        # (the goal's label, the monsters the hands found in the way of its act, until when): `first_fight`
        self.blocking: tuple[str, frozenset[int], float] | None = None
        self.base: Goal | None = None  # the goal of the last look before the fight that bars it (`first_fight`)
        self.settled_at = -math.inf  # clock time an object used has brought what it calls (teleport.py `Use.brings`)
        self.missed: tuple[str, float] | None = None  # (a goal's label, until when) whose act did not take: `nearer`
        # The player's hand (`hand`): the clock time it was last seen at work (a click, a panel open, the pointer
        # moved by it), and the pointer as the last look found it. A level run it paused goes on once it rests.
        self.hand_at = -math.inf
        self.pointer_seen: tuple[int, int] | None = None
        # (the reason, how many times in a row) an act of the loop's was given up for: said every time (I1, I6)
        self.refused: tuple[str, int] | None = None
        self.struck_back_at = -math.inf  # when the strike was last selected on the right button (`strike_back`)
        self.waived: set[int] = set()  # valuables with no room a press went on from: not waited by again
        self.warned: int | None = None  # the valuable the card's "Inventory full" warning is of
        self.potions = Potions()  # the potions of the level, why one was left, the belt's healing (supply.py)
        self.guarded_since: dict[int, float] = {}  # potion -> clock time its guards were first the fight first
        self.fetching: tuple[float, Drop | None] = (-math.inf, None)  # (when judged, a scarce potion worth a detour)
        self.area: int | None = None  # the level attack mode last saw the character on (not in town)
        # The run mode (macros/runmode.py): the pickup key's presses as posted (judged as a double press at a look),
        # the player's switch as (level, full clear), the mode of the level the last look was on (the HUD's), and
        # the (level, line) last said of it
        self.taps = Taps()
        self.switched: tuple[int, bool] | None = None
        self.mode: Mode | None = None
        self.mode_said: tuple[int, str] | None = None
        self.far_said: str | None = None  # the boss attack mode alone last said it does not go to (`nearby`)
        # A level run's clearing goals passed (key -> until when: a unit, or a room's place) and the one gone for
        # now with since when (`clearing`); the full clear's last look for the rest of the level (when, level, found)
        self.passed: dict[object, float] = {}
        # Each clearing goal's judging by its key (`Judging`), the key of the goal the last look went for, and the
        # goals left for another: key -> (until, the other's key) (TAKE_BACK)
        self.judging: dict[object, Judging] = {}
        self.went: object | None = None
        self.left_for: dict[object, tuple[float, object]] = {}
        self.rest: tuple[float, int, tuple[Point, str, int | None] | None] | None = None

    def use(self, build: Build) -> None:
        """The build the hunt plays from now on: the runner's, named at a run's first look that shows
        the character (runner.py `choosing`). The same build again changes nothing. Another one (a
        game with another character) starts what is kept by build anew: when each buff was last cast
        and what the state showed of it (`buffs`), and the jumps last made and failed (`travel`),
        which are the old build's skills and the old character's casts. What is the level's and the
        fight's (the tour, the sweep, what was tested and left alone) stays."""
        if build is self.build:
            return
        self.build = build
        self.buffs = Buffs(build)
        self.travel = Travel(build.movement)
        self.drinker = Drinker(build.settings.drink)

    @property
    def attack(self) -> Attack:
        """The build's attack: the strike the fight holds, its reach, where it aims and what it deals.
        A build without one does not fight: attack mode stops with that said."""
        attack = self.build.attack
        if attack is None:
            raise Abort(f'attack mode off: the build ({self.build.name}) has no attack of its own')
        return attack

    @property
    def reach(self) -> float:
        """Units the build's attack reaches; 0.0 for a build that does not fight: nothing is in its reach."""
        attack = self.build.attack
        return 0.0 if attack is None else attack.reach

    @property
    def policy(self) -> Attack | Policy | None:
        """What is asked where to cast (combat/controller.py `aim_choice`): the build's attack, or the
        policy handed in or set in its place, which gives the aim alone (the reach, what is seen and
        what a cast deals stay the attack's)."""
        return self.aimed_by if self.aimed_by is not None else self.build.attack

    @policy.setter
    def policy(self, policy: Policy | None) -> None:
        self.aimed_by = policy

    def boss(self, monster: Monster) -> bool:
        """Whether `monster` is a boss to the hunt: an act boss (terror/bosses.py BOSSES) or a class whose life price is
        dearer (`SafetySettings.dear`: Diablo, Baal, his clone, the Ubers, ...)."""
        return monster.txt_id in BOSSES or any(monster.txt_id == txt for txt, _ in self.build.settings.safety.dear)

    def nearing_only(self, world: World, foes: Sequence[Monster], ground: Ground, here: Point, now: float) -> bool:
        """Whether everything in reach is a boss the run is getting back in reach of (`untouched`) and stands beyond
        the attack's engage ring: no fight to hold from here, the goal's move first."""
        self.nearing = {unit: until for unit, until in self.nearing.items() if until > now}
        if not self.nearing:
            return False
        reachable = [m for m in foes if in_reach_of(ground, here, (m.x, m.y), self.reach, world.doors)]
        engage = self.attack.engage
        return bool(reachable) and all(
            m.unit_id in self.nearing and math.dist(here, (m.x, m.y)) > engage for m in reachable
        )

    def quiet(self, world: World, foes: Sequence[Monster]) -> bool:
        """Whether no hostile is within QUIET_UNITS of the character: the whole upkeep goes between a run's moves."""
        player = world.player
        if player is None:
            return False
        return all(math.dist((player.x, player.y), (m.x, m.y)) > QUIET_UNITS for m in foes)

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
            self.nearing.pop(prey.unit_id, None)  # struck from here: near enough
        seen += casts
        self.tested[prey.unit_id] = (seen, life_then)
        if seen < UNTOUCHED_CASTS:
            return False
        del self.tested[prey.unit_id]
        if self.boss(prey):
            # A boss is never left alone (the player, 2026-10-14): Baal's random teleports made the strikes count casts
            # that could not land on him, and 20 s alone left him unkilled in 60 s on 2 of 10 arena seeds
            # (rca/2026-10-14/baal-sim.md). The run gets back in reach instead: its fight goal is near enough only
            # within the attack's engage ring for NEARING_SECONDS (`goal`), and he is no hostile in reach beyond it
            # (`judge`); the fight goes on from there.
            self.nearing[prey.unit_id] = run.clock() + NEARING_SECONDS
            LOG.info(
                'Macro: %s takes no damage (%s after %d casts through it): a boss is not left alone; getting back in '
                'reach, within %.0f of him',
                label(prey), life(prey), seen, self.attack.engage,
            )  # fmt: skip
            run.say(f'{label(prey)} takes no damage: getting nearer')
            return True
        self.untouchable[prey.unit_id] = run.clock() + UNTOUCHABLE_SECONDS
        LOG.info(
            'Macro: %s takes no damage (%s after %d casts through it): left alone for %.0fs',
            label(prey), life(prey), seen, UNTOUCHABLE_SECONDS,
        )  # fmt: skip
        run.say(f'{label(prey)} takes no damage: left alone')
        return True

    @property
    def pursuing(self) -> bool:
        """Whether the build played has the pursuit loop on (`BuildSettings.pursuit`)."""
        return self.build.settings.pursuit

    def pressed(self, now: float) -> bool:
        """Whether a press of the key is in the mailbox and still asks for a move."""
        return self.pursuit is not None and self.pursuit.fresh(now)

    def advancing(self, now: float) -> bool:
        """Whether a fresh press asks for its goal now, before what is in reach (the teleport key's)."""
        return self.pursuit is not None and self.pursuit.advance and self.pursuit.fresh(now)

    @property
    def running(self) -> bool:
        """Whether a level run works now (the pickup key's leash: macros/pursuit.py), not paused by the hand."""
        return self.pursuit is not None and self.pursuit.runs

    @property
    def leashed(self) -> bool:
        """Whether a level run is held, working or paused by the player's hand."""
        return self.pursuit is not None and self.pursuit.leashed

    def post(self, pursuit: Pursuit) -> None:
        """A press posted to the mailbox by the runner. A press that sets no leash keeps the one a level run
        has (the teleport key during a run asks for its goal now, and the run goes on after it); one that
        sets a leash on the same level keeps where it runs."""
        with self.mailbox:
            old = self.pursuit
            if pursuit.leashed and (old is None or not old.leashed):
                self.travel.tally = Tally()  # the run's pace counts from its own first leg (`Travel.paced`)
            if old is not None and old.leashed:
                if not pursuit.leashed:
                    pursuit = replace(pursuit, leash=old.leash, area=old.area, paused=old.paused)
                elif pursuit.area is None:
                    pursuit = replace(pursuit, area=old.area)  # a fresh pickup press: the run goes on, unpaused
            waited = self.pursued
            if waited is not None and waited.do == WAIT and waited.unit is not None:
                # A press while the run stands by a valuable with no room for it: the player goes on without it
                if len(self.waived) > 200:
                    self.waived.clear()
                self.waived.add(waited.unit)
            if pursuit.leashed and not pursuit.advance:
                self.taps = tapped(self.taps, pursuit.pressed_at)  # a double press switches the run mode (`run_mode`)
            self.pursuit = pursuit

    def swap(self, seen: Pursuit | None, new: Pursuit | None) -> bool:
        """The loop's write to the mailbox, made only while it still holds `seen`, what the loop read (by
        identity: every post is a new record); whether it was made. A press posted since stays as posted."""
        with self.mailbox:
            if self.pursuit is not seen:
                return False
            self.pursuit = new
            return True

    def end_run(self, run: Run | None, reason: str, seen: Pursuit | bool | None = True) -> None:
        """The level run is over (macros/pursuit.py `Ended`; the runner's: attack mode off, the macro
        request, the player's own move): the leash goes back to none, said once. A fresh press of the
        teleport key in the mailbox stays. `seen`: the mailbox as the look that ended the run read it; a press
        posted since then is the next look's and keeps the run (True: whatever the mailbox holds now)."""
        with self.mailbox:
            posted = self.pursuit if seen is True else seen
            if not isinstance(posted, Pursuit) or not posted.leashed:
                return
            if self.pursuit is not posted:
                LOG.info('Macro: pursuit: the level run goes on (%s): a press came during the look', reason)
                return
            self.pursuit = replace(posted, leash=NONE, area=None, paused=False) if posted.advance else None
        LOG.info('Macro: pursuit: the level run ends: %s', reason)
        self.travel.paced(run.clock() if run is not None else None, reason)
        self.told.new(None)
        self.mode_said = None  # the next run says its mode again
        if run is not None:
            run.say(f'Level run over: {reason}')

    def pause_run(self, run: Run, why: str) -> None:
        """The player's hand has the level run (macros/pursuit.py, the module text): the run is paused, said
        once, and goes on by itself once the hand rests (`hand`). Nothing is said for a run already paused."""
        posted = self.pursuit
        if posted is None or not posted.runs or not self.swap(posted, replace(posted, paused=True)):
            return
        LOG.info('Macro: pursuit: the level run is paused: %s', why)
        self.told.new(None)
        run.say(f"Level run paused: the player's hand ({why}); it goes on once the hand rests {SETTLE:g} s")

    def hand(self, run: Run, world: World) -> None:
        """One look at the player's hand: a panel open or the pointer moved by it (not where the loop last put
        it) is the hand at work, as a click is (`sense`); a panel open pauses a working run (nothing is clicked
        into a panel, I7). A paused run goes on once the hand has rested SETTLE seconds with no panel open."""
        now = run.clock()
        actuator = run.actuator
        pointer = actuator.keys.pointer()

        def apart(one: tuple[int, int] | None, other: tuple[int, int] | None) -> bool:
            # further apart than the steady guard allows (POINTER_DRIFT): a hand's tremor is no move
            if one is None:
                return False
            return other is None or max(abs(one[0] - other[0]), abs(one[1] - other[1])) > POINTER_DRIFT

        if world.open_panels:
            self.hand_at = now
            self.pause_run(run, f'{", ".join(world.open_panels)} open')
        elif self.pointer_seen is not None and apart(pointer, self.pointer_seen) and apart(pointer, actuator.left_at):
            self.hand_at = now
        elif actuator.button_held(3) or actuator.key_held():
            self.hand_at = now  # the player's own strike or key: the hand is at work
        self.pointer_seen = pointer
        posted = self.pursuit
        if posted is None or not posted.leashed or not posted.paused:
            return
        if (
            settled(self.hand_at, now, bool(world.open_panels))
            and not run.actuator.button_held(1)
            and self.swap(posted, replace(posted, paused=False))
        ):
            LOG.info('Macro: pursuit: the level run resumes: the hand has rested %.1f s', now - self.hand_at)
            self.told.new(None)
            run.say('Level run resumed')

    def side_drop(
        self,
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
        given_up = {unit: self.given_up(unit) for unit, n in self.gathered.items() if n >= GATHER_TRIES}
        given_up |= {
            unit: f'left: guarded {BLOCK_SECONDS:.0f} s'
            for unit, since in self.guarded_since.items()
            if now - since > BLOCK_SECONDS
        }
        for found in loot.drops:
            if found.unit_id in given_up:
                self.refused_potion(found, here, given_up[found.unit_id])
                self.left(found, here, given_up[found.unit_id], 'the level run')
        loot = replace(loot, drops=tuple(found for found in loot.drops if found.unit_id not in given_up))
        if restocking:
            return self.restock(run, loot, here, foes, world)
        plan = choose(loot, here)
        drop = plan.drop if plan is not None else None
        while drop is not None and drop.kind == VALUABLE and not self.on_the_way(run, here, drop, world):
            # Out of the choice, and nothing nearer hidden by it: at 22:56:06 on 2026-10-14 a Flawless Sapphire 43
            # away hid a super healing potion 8 away with the belt 6 short (run-1932-findings.md issue 2)
            loot = replace(loot, drops=tuple(found for found in loot.drops if found.unit_id != drop.unit_id))
            plan = choose(loot, here)
            drop = plan.drop if plan is not None else None
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

    def restock(self, run: Run, loot: Loot, here: Point, foes: Sequence[Monster], world: World | None) -> Drop | None:
        """A potion that a belt low on potions takes before the goal, in the quiet (the player, 2026-10-14): no hostile
        within QUIET_UNITS, healing potions under half their columns or rejuvenations under the reserve, the potion
        within RESTOCK_UNITS walked (macros/supply.py `low`, `restock`). At 22:55:31.8 on 2026-10-14 the belt held 2
        healing potions of 8 with nothing within 30, a full rejuvenation lay 7 away and super healing potions 13 and
        16, and the run warped on toward Snapchip 84 away (run-1932-findings.md issue 2). Said once a potion."""
        if any(math.dist(here, (m.x, m.y)) <= QUIET_UNITS for m in foes) or not low(loot):
            return None
        world = world if world is not None else run.world()
        level = self.known_level(world.player) if world.player is not None else None
        found = restock(loot, here, Ground(level.ground) if level is not None else None, world.doors)
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

    def given_up(self, unit: int) -> str:
        """Why a drop gone for GATHER_TRIES times is left: what its last try came to, as the hands said it (a
        priced act that expired mid-walk is not a click that took nothing: run-0025-findings.md §2.3)."""
        tries = self.gathered.get(unit, 0)
        last = self.tried.get(unit)
        if last is None:
            return f'given up after {tries} tries: still on the ground after each'
        return f'given up after {tries} tries (the last: {last})'

    def again(self, run: Run, drops: Sequence[Drop], here: Point, world: World | None = None) -> None:
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
            and self.gathered.get(d.unit_id, 0) >= GATHER_TRIES
            and d.unit_id not in self.retried
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
            if len(self.retried) > 200:
                self.retried.clear()
            self.retried.add(drop.unit_id)
            why = self.given_up(drop.unit_id)
            self.gathered[drop.unit_id] = GATHER_TRIES - 1
            self.tried.pop(drop.unit_id, None)
            self.left_said.discard(drop.unit_id)
            LOG.info(
                'Macro: pickup: one more try at %s at (%.0f, %.0f), %.0f away on a clear line now (%s)',
                drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
            )  # fmt: skip
            run.say(f'One more try at {drop.label}')

    def left(self, drop: Drop, here: Point, why: str, who: str) -> None:
        """A valuable or gold `who` gives up on, said once a drop (a potion says its own: `refused_potion`)."""
        if drop.kind in (HEALING, REJUVENATION) or drop.unit_id in self.left_said:
            return
        if len(self.left_said) > 200:
            self.left_said.clear()
        self.left_said.add(drop.unit_id)
        LOG.info(
            'Macro: %s leaves %s at (%.0f, %.0f), %.0f away: %s',
            who, drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
        )  # fmt: skip

    def refused_potion(self, drop: Drop, here: Point, why: str) -> None:
        """A potion the run leaves, said once a potion and reason (potions-findings.md M4: it was silent)."""
        if drop.kind in (HEALING, REJUVENATION) and self.potions.refuse(drop.unit_id, why):
            LOG.info(
                'Macro: pursuit: %s at (%.0f, %.0f), %.0f away, %s',
                drop.label, drop.x, drop.y, math.dist(here, (drop.x, drop.y)), why,
            )  # fmt: skip

    def scarce(self, run: Run, loot, here: Point, world: World | None) -> Drop | None:
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
            if self.gathered.get(potion.unit, 0) >= GATHER_TRIES:
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

    def stay_by(self, run: Run, here: Point, *, wanted: bool = True) -> Drop | None:
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
            left = [
                d
                for d in loot.drops
                if d.kind == VALUABLE
                and d.unit_id not in loot.shown
                and d.unit_id not in self.waived
                and not has_room(loot.room, d.size)
                and math.dist(here, (d.x, d.y)) <= PICK_NEAR
            ]
            found = min(left, key=lambda d: math.dist(here, (d.x, d.y))) if left else None
        if found is None:
            if self.warned is not None:
                self.warned = None
                run.warn(None)
            return None
        if self.warned != found.unit_id:
            self.warned = found.unit_id
            cube = loot is not None and loot.cube is not None and has_room(loot.cube, found.size)
            told = ' (the cube has room for it)' if cube else ''
            LOG.info(
                'Macro: pursuit: the inventory has no room for %s at (%.0f, %.0f), %.0f away: the run stands by it%s',
                found.label, found.x, found.y, math.dist(here, (found.x, found.y)), told,
            )  # fmt: skip
            run.warn(f'Inventory full: {found.label} here — make room{told}')
        return found

    def blockers(self, goal: Goal | None, foes: Sequence[Monster], now: float) -> list[Monster]:
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

    def goal(self, run: Run, world: World, foes: list[Monster], pressed: bool, posted: Pursuit | None) -> Goal | None:
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
            stay = self.stay_by(run, here, wanted=side is None)
        elif self.pursuing and not pressed:
            # Attack mode's own goal (no level run, no press): a potion a low belt restocks in the quiet comes first
            side = self.side_drop(run, here, foes, world, restocking=True)
        known = self.remembered(area) if self.remembered is not None else []
        live = {m.unit_id for m in foes}
        self.vanished |= {
            unit for unit, x, y, _ in known if unit not in live and math.dist(here, (x, y)) <= VANISH_UNITS
        }

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

        found = goal_of(
            here,
            spend=PRESSED if pressed or running else STANDING,
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
            drop=drop,
            side=side,
            stay=stay,
        )
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

    def cleared(self, run: Run, world: World, foes: list[Monster], ground: Ground, found: Goal | None) -> Goal | None:
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
        clear = mode is not None and mode.clear
        if found is not None and (found.do in (FIGHT, PICK_UP, WAIT) or found.guarded):
            return found
        if not clear and (found is None or not found.route or found.do not in WAYS):
            return found
        player = world.player
        assert player is not None
        here, now = (player.x, player.y), run.clock()
        level = self.known_level(player)
        rooms = level.rooms if level is not None else ()
        self.passed = {key: until for key, until in self.passed.items() if until > now}
        self.left_for = {key: left for key, left in self.left_for.items() if left[0] > now}
        spend = found.spend if found is not None else PRESSED

        def candidate(skip: frozenset[object]) -> Goal | None:
            rest = self.rest_of(run, world, foes, here, skip, rooms) if clear else None
            base = rest_of_level(rest, found, self.reach, spend) if rest is not None else found
            near = [
                m
                for m in foes
                if m.unit_id not in self.passed
                and m.unit_id not in skip
                and math.dist(here, (m.x, m.y)) <= CLEAR_WAY
                and clear_shot(ground, here, (m.x, m.y), world.doors)
            ]
            return clear_way(base, here, near, self.reach) if base is not None and near else base

        chosen = found
        for _ in range(3):  # a goal passed now gives its place to the next
            goal = self.taken_back(candidate, rooms, found)
            if goal is None or not goal.clearing:
                chosen = goal
                break
            if self.goes_on(run, world, ground, goal, rooms, now):
                chosen = goal
                break
        self.went_for(chosen, rooms, now)
        return chosen

    def goal_key(self, goal: Goal | None, rooms: Sequence[Room]) -> object | None:
        """The key a level run's goal is judged and left by: a clearing goal's `passing_key`, the route's by itself."""
        if goal is None:
            return None
        return passing_key(goal.place, goal.unit, rooms) if goal.clearing else ('the run', goal.label, goal.do)

    def taken_back(
        self, candidate: Callable[[frozenset[object]], Goal | None], rooms: Sequence[Room], found: Goal | None
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

    def went_for(self, chosen: Goal | None, rooms: Sequence[Room], now: float) -> None:
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

    def goes_on(self, run: Run, world: World, ground: Ground, goal: Goal, rooms: Sequence[Room], now: float) -> bool:
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
        self.pass_by(
            goal, f'no strike and no progress by the way in {CLEAR_SECONDS:.0f} s on the way to it', now, rooms
        )
        return False

    def on_the_way(self, run: Run, here: Point, drop: Drop, world: World | None) -> bool:
        """Whether a valuable is near enough for a level run to take on its way (`side_drop`): PICK_NEAR by walking
        (travel.py `walked_length`), not in a straight line. The Ith Rune of 22:36:09 on 2026-10-14 was 26 straight
        and 226 by walking across the lava: taken for "on the way" from one side and not from the other, it had the
        run warp back and forth 8 times (rca/2026-10-14/run-1932-findings.md §1.2.3)."""
        place = (drop.x, drop.y)
        if math.dist(here, place) > PICK_NEAR:
            return False
        world = world if world is not None else run.world()
        level = self.known_level(world.player) if world.player is not None else None
        ground = Ground(level.ground) if level is not None else None
        return walked_length(ground, world.doors, here, place) <= PICK_NEAR

    def pass_by(self, goal: Goal, why: str, now: float, rooms: Sequence[Room] = ()) -> None:
        """A level run's clearing goal is passed for PASS_SECONDS from `now` (`cleared`), said."""
        if len(self.passed) > 400:
            self.passed.clear()
        key = passing_key(goal.place, goal.unit, rooms)
        self.passed[key] = now + PASS_SECONDS
        self.judging.pop(key, None)
        LOG.info('Macro: run: passing %s at (%.0f, %.0f): %s', goal.label, *goal.place, why)

    def rest_of(
        self,
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
        if live:
            nearest = min(live, key=lambda m: math.dist(here, (m.x, m.y)))
            return (nearest.x, nearest.y), label(nearest), nearest.unit_id
        known = self.remembered(area) if self.remembered is not None else []
        seen = {m.unit_id for m in foes}
        gone = seen | self.vanished | set(self.untouchable) | out
        kept = [(x, y, unit) for unit, x, y, _ in known if unit not in gone]
        if kept:
            x, y, unit = min(kept, key=lambda k: math.dist(here, (k[0], k[1])))
            return (x, y), 'the remembered monster', unit
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
        if room is not None and passing_key(room[0], None, rooms) in out:
            return None
        return room

    def run_mode(self, run: Run, area: int, posted: Pursuit | None) -> Mode:
        """The run mode on level `area` at this look (macros/runmode.py): a double press of the pickup key whose
        window is over switches it, for this level; a switch made on another level lapses. Said once a run and a
        change (`Macro: run: ...`) while a level run is held."""
        now = run.clock()
        if self.switched is not None and self.switched[0] != area:
            self.switched = None
        with self.mailbox:
            pairs, self.taps = doubles(self.taps, now)
        terror = self.bearings.terror(area)
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
        mode = self.mode = mode_of(area, terror, self.switched)
        if posted is not None and posted.leashed:
            line = said(mode, aim_of(self.bearings.script(area)))
            if self.mode_said != (area, line):
                self.mode_said = (area, line)
                LOG.info('Macro: run: %s', line)
                run.say(f'Run: {line}')
        return mode

    def nearby(self, goal: Goal | None, here: Point) -> Goal | None:
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

    def judge(
        self, run: Run, world: World, foes: list[Monster], ground: Ground, *, in_reach: bool, attacking: bool = True
    ) -> Judged:
        """One look of the pursuit: the goal named, the facts read and the decision made
        (macros/pursuit.py `decide`). Nothing is done here. The place the navigator is asked for is the
        goal's own, and for a fight the nearest place with a shot at the boss (`firing_target`: the
        build strikes from a distance, and "near enough" for a fight is a shot)."""
        player = world.player
        assert player is not None
        # The mailbox is read once, before the look's clock: every press the look judges was made by then, and
        # one posted later is the next look's (rca/2026-10-14/run-0025-findings.md §2.1)
        posted = self.pursuit
        here, now = (player.x, player.y), run.clock()
        if in_reach and self.only_bound(world, foes, ground, here):
            # What is in reach dies with a summoner standing elsewhere (Baal's clone): it is no fight to hold, and the
            # goal (the summoner's fight) is gone to (rca/2026-10-14/baal-sim.md fix 2: 17 s on the clone, Baal 33 off)
            in_reach = False
        if in_reach and self.nearing_only(world, foes, ground, here, now):
            in_reach = False  # a boss the strikes did nothing to from here: the run gets back in reach (`untouched`)
        if posted is not None and posted.leashed and posted.area is None:
            named = replace(posted, area=player.area)  # the level run is of the level it was asked on
            self.swap(posted, named)
            posted = named
        pressed = posted is not None and posted.fresh(now)
        self.run_mode(run, player.area, posted)
        goal = self.goal(run, world, foes, pressed, posted)
        if posted is not None and posted.runs and not (pressed and posted.advance):
            goal = self.cleared(run, world, foes, ground, goal)  # the run's own look: what its mode adds
        if not pressed and not (posted is not None and posted.leashed):
            goal = self.nearby(goal, here)
        self.pursued = goal
        level = self.known_level(player)
        rect = run.actuator.keys.focused_window_rect()
        place, there, beyond = None, False, math.inf
        if goal is not None:
            place = goal.place
            if goal.do == FIGHT:
                there = in_reach_of(ground, here, goal.place, goal.near, world.doors)
                if not there and level is not None and goal.known:
                    # As `firing_target` chooses it, without its log line (this is asked at every look), but on the
                    # attack's engage ring first, not the ring just inside the reach (run-1932-findings.md §4.2: the
                    # approaches ended 17 units off, a third of the casts hitting nothing); the safety prices the leg
                    engage = self.attack.engage
                    spots = firing_spots(ground, goal.place, STRIKE_REACH, here, world.doors, engage) or [goal.place]
                    rooms = level.rooms
                    place = next((s for s in spots if room_at(rooms, (s[0] / TILE_UNITS, s[1] / TILE_UNITS))), spots[0])
            elif goal.do == USE and goal.mark is not None:
                thing = marked_thing(run, goal.mark)
                near = goal.gap(here) <= SPOT_NEAR or (
                    thing is not None and math.dist(here, (thing.x, thing.y)) <= goal.near
                )
                there = thing is not None and near
            elif goal.do == PICK_UP:
                # Near enough to click is a walk within reach, not a straight line: a drop across lava is gone to
                # by the navigator first (run-0025-findings.md §2.2: 17 straight, 43 by walking, both tries cut)
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
        # The strike gap counts while a hostile is within the strike's reach, a clear line or not (I2)
        near = any(math.dist(here, (m.x, m.y)) <= self.reach for m in foes)
        facts = replace(facts, quiet=min(now - self.struck_at, 60.0) if near else 0.0, near=near)
        if self.pursuing and rect is not None:
            facts = self.safety_priced(run, world, foes, ground, facts, posted, rect)
        act = decide(facts, posted, self.pursuing)
        if isinstance(act, Advance) and act.reason:
            place = act.step.spot
        if (
            isinstance(act, NoWay)
            and goal is not None
            and goal.clearing
            and act.reason.startswith('no way toward')
            and not act.reason.endswith(GROWING)  # a way not grown yet in the look's time is no way that fails
        ):
            # a run's clearing goal it has no way to: the next look goes on
            self.pass_by(goal, act.reason, now, level.rooms if level is not None else ())
        return Judged(act, goal, place, posted, pressed)

    def safety_priced(
        self, run: Run, world: World, foes: list[Monster], ground: Ground, facts: Facts, posted: Pursuit | None, rect
    ) -> Facts:
        """The facts with the safety's prices (macros/safety.py `Safety.price`): the candidates and the budget the
        arbiter decides by. As they were with no life read (nothing priced)."""
        player = world.player
        assert player is not None
        now = facts.now
        if run.loot is None:
            return facts
        loot = run.loot()
        if loot.max_life > 0 and loot.life > 0:
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
            )
            facts = self.escorted(run, world, ground, rect, look, facts)
        return facts

    def escorted(self, run: Run, world: World, ground: Ground, rect, look, facts: Facts) -> Facts:
        """The priced facts with the acts that take the mercenary out of a place it dies at (combat/escort.py): a jump
        that brings the companions along (`JumpSource.brings`: Blade Warp) to a landing round which it lives, priced
        as the others are (the character's own harm there, the jump's seconds) less what its death would cost. The
        arbiter chooses among them all (pursuit.py `arbitrate`); said `Macro: pursuit: escorting the mercenary ...`.
        As they were with nothing priced, no such jump, no mercenary, or none in danger."""
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
            # The jump's own seconds and the move's overhead, less the death it spares: one price, the arbiter's unit
            spent = seconds + settings.move_overhead - escort.credit
            added.append(Candidate(Advance(step, goal, escort.line(), dodge=True), spent, priced, False, seconds))
        if not added:
            return facts
        return replace(facts, candidates=(*facts.candidates, *added))

    def guard(self, run: Run, world: World, foes: list[Monster], ground: Ground) -> Advance | None:
        """Attack mode with the pursuit loop off (KP_3 as it was, which never moved): the pursuit loop's own safety
        look and arbiter (`safety_priced`, pursuit.py `decide`), its answer taken only when it is a step the strike
        goes on from: out of or across a read model's act under way (`Move.dodge`) or to another place a read model
        or what lies on the ground offers (macros/safety.py STEPPING; not the threat's plain geometry, AWAY), and only
        one a strike follows from (`Candidate.strikes`). No retreat (not even one within reach: pursuit.py KEEPING),
        no firing stand, no goal: the mode alone never goes back, so each of those left it out of reach when the boss
        walked off (the arena, 2026-10-14: fight up to 41 s against 25); rca/2026-10-14/baal-sim.md fix 3. Looked at
        only with a read model's hostile about (combat/threats `of`) or what lingers after one. None: strike on."""
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
        # The strike follows from where it lands, or the mode alone, which never goes back, would stand out of reach
        # (a dodge out of Baal's inferno ends beyond the blades: baal-sim.md weakness 4)
        landing = next((c for c in priced.candidates if isinstance(c.act, Advance) and c.act.step == act.step), None)
        return act if landing is not None and landing.strikes else None

    def guarded(self, foes: Sequence[Monster]) -> bool:
        """Whether the mode alone looks for a safety step (`guard`): a hostile of a read model about (combat/threats
        `of`), or what lingers after one. Nothing is read of the game for it."""
        return bool(self.safety.casters) or any(threats.of(m.txt_id) is not None for m in foes)

    def take_guard(self, run: Run, aspect: float, key_names, ground: Ground) -> None:
        """The step `guard` stopped the fight for, made as the pursuit loop makes a dodge (`advance`: its click
        without the settle, macros/travel.py `step_walk` `hurry`); the player's own move first. Said as
        `Macro: attack mode: stepping ...`; the mode's next look strikes again."""
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

    def key_asks(self, run: Run, world: World, foes: list[Monster], ground: Ground) -> bool:
        """Inside a fight: whether the key pressed asks for something other than the strike now (a move,
        an object to use, the route's own step), for which the fight lets go as it does for the player's
        own move. Decided once a press and again every DECIDE_SECONDS while the press is fresh: a goal in
        reach is held, and the strike is not let go for a press that asks for nothing else."""
        now = run.clock()
        if not self.pursuing:
            return False
        current = self.pursuit.pressed_at if self.pursuit is not None else -math.inf
        stamp, at, asks = self.judged
        if stamp != current or now - at >= DECIDE_SECONDS:
            found = self.judge(run, world, foes, ground, in_reach=True)
            act = found.act
            asks = isinstance(act, Advance | Operate | Defer) or (
                isinstance(act, NoWay) and act.reason.startswith('safety:')
            )
            if isinstance(act, Hold) and found.pressed:
                # A fresh press answered by the strike says so at that look (I6), as `pursue` does
                label = found.goal.label if found.goal is not None else 'the goal'
                self.tell(run, act.reason or f'{label}: the least-time safe act is the fight', again=SAID_AGAIN)
            self.judged = (current, now, asks)
        return asks

    def tell(self, run: Run, reason: str | None, *, aloud: bool = True, again: float | None = None) -> None:
        """A decision that moved nothing is said with its reason, once per change (never once per press).
        Not `aloud`: to the log alone (what the mode does with no press asking: its idle look, as before).
        `again`: seconds after which the same reason is said once more (a held key whose act stays the strike
        hears why at that rate: I6, each press has its line; never at the rate of the presses)."""
        repeated = (
            again is not None
            and reason is not None
            and reason == self.told.reason
            and run.clock() - self.told_at >= again
        )
        if self.told.new(reason) or repeated:
            self.told_at = run.clock()
            LOG.info('Macro: pursuit: %s', reason)
            if aloud:
                run.say(f'{reason[:1].upper()}{reason[1:]}')  # type: ignore[index]

    def defer(self, run: Run, goal: Goal | None, why: str, seen: Pursuit | bool | None = True) -> None:
        """The press is the route's own step's (a door, the loot, the leaving; a panel open; the town),
        or with no goal the key's own routine's: the mode pauses for that step as it does for the pickup
        step (Cancelled, the runner follows with the key's routine), and the press is taken out of the
        mailbox. A level run's leash stays: the mode goes on with it after the step. `seen`: the mailbox as
        the look read it; a press posted since stays for the next look (True: whatever it holds now)."""
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

    def blocked(self, run: Run, units: frozenset[int]) -> None:
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

    def pursue(self, run: Run, world: World, foes: list[Monster], ground: Ground, key_names, *, in_reach: bool) -> bool:
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
                    with self.priced_for(run, act.step.seconds):
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
            if isinstance(act, Operate) and act.goal.do == PICK_UP and act.goal.unit is not None:
                if len(self.tried) > 200:
                    self.tried.clear()
                self.tried[act.goal.unit] = str(stop)
            if isinstance(stop, Covered):
                self.blocked(run, stop.units)
            elif isinstance(act, Operate) and self.base is not None:
                self.missed = (self.base.label, run.clock() + BLOCK_SECONDS)  # tried again from nearer
            self.give_up(run, f'no {"move toward" if isinstance(act, Advance) else "use of"} {act.goal.label}: {stop}')
            self.nap(run, FRAME)
        return True

    def way_time(self):
        """The block the far goal's way is asked for in by the loop outside the safety's own look (travel.py
        `planning`): the look's share of its time (macros/safety.py WAY_SHARE) from now by the look's clock; none
        without one (the arena)."""
        timer = self.safety.timer
        if timer is None:
            return nullcontext()
        return planning(timer, timer() + self.build.settings.safety.look_seconds * WAY_SHARE)

    def stale(self, run: Run, world: World, looked: float, act) -> bool:
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

    def give_up(self, run: Run, reason: str) -> None:
        """An act of the loop's given up for `reason` is said every time it is, with how many times in a row
        (I1: the look says why it moved nothing; I6: never silent): run-2110-findings.md M3, where the same abort
        was said once and then silenced for 9.3 s while the card kept saying "Walking 16 toward Diablo"."""
        last = self.refused
        count = last[1] + 1 if last is not None and last[0] == reason else 1
        self.refused = (reason, count)
        self.tell(run, reason if count == 1 else f'{reason} (x{count})')

    @contextmanager
    def priced_for(self, run: Run, seconds: float):
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
                raise Abort('priced act expired: look again before continuing')

        run.observe = observed
        try:
            yield
        finally:
            run.observe = previous

    def advance(self, run: Run, world: World, ground: Ground, act: Advance, place: Point, key_names) -> None:
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

    def operate(self, run: Run, world: World, goal: Goal, key_names) -> None:
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
                self.gathered[goal.unit] = self.gathered.get(goal.unit, 0) + 1
                pick_up(run, self.known_level(player), key_names, lambda: None, threat(run), unit=goal.unit)
            else:
                pick_up(run, self.known_level(player), key_names, lambda: None, unit=goal.unit)
        elif goal.do == USE and goal.mark is not None:
            if rect is None:
                raise Abort('no game window')
            thing = marked_thing(run, goal.mark)
            if thing is None:
                raise Abort(USES[goal.mark.use].absent.format(goal.mark.label))
            use_thing(run, goal.mark, player, thing, rect[2] / rect[3])
            self.settled_at = run.clock() + USES[goal.mark.use].brings
            route.note_used(run, goal.mark, bearings.progress, bearings.marks)
        elif goal.do == STAND and goal.stage is not None and bearings.progress is not None:
            bearings.progress.stood(player.area, goal.stage.mark)
            run.say(f'{goal.route}: at {goal.stage.mark}')

    def pursue_once(self, run: Run, key_names, *, attacking: bool) -> Judged | None:
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
                with self.priced_for(run, found.act.step.seconds):
                    self.advance(run, world, ground, found.act, found.place, key_names)
            elif isinstance(found.act, Operate):
                with self.priced_for(run, self.build.settings.safety.operate_dwell):
                    self.operate(run, world, found.act.goal, key_names)
            return found
        finally:
            self.swap(own, saved)  # a press posted meanwhile stays for the mode

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
    def worn(run: Run) -> Teleport | None:
        """The Teleport staff the character wears, with the charges left on it; None without one
        (Teleport as a skill, or none at all)."""
        return run.teleport() if run.teleport is not None else None

    def afoot(self, run: Run, ground: Ground, player, rect, goal: Point, name: str, key_names) -> bool:
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

    def warp_hop(self, run: Run, target: Target, player, spot: Point, key_names) -> bool:
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
        self, run: Run, ground: Ground, goal: Point, name: str, key_names, rooms: tuple[Room, ...] = ()
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

    def foot_step(self, run: Run, target: Target, key_names) -> None:
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
        return camp(
            seen,
            attack,
            no_footing(ground, world.doors),
            shown=lambda spot: (
                in_view(ground_fraction(player, spot[0], spot[1], aspect)) and not self.sweep.shuns(spot)
            ),
            gain=gain,
            jumps=jumps,
            # The cows are fought from inside the herd, as the player does it (user, 2026-10-12: "special
            # tactics for some mob types (cows/...)"): theirs is to be a `Tactic` (Stage 7); until then no
            # step out of the pack on their level.
            escape=0.0 if player.area == MOO_MOO_FARM else None,
            landed=landed,
            walls=landed,
        )

    def next_step(
        self,
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
        A drop is stopped for GATHER_TRIES times at most: one no click takes must not hold the mode, and once
        given up it is neither chosen nor stayed by (said once, with why: `given_up`)."""
        now = run.clock()
        if self.pick is None or run.loot is None or not self.sweep.steps or now > self.sweep.until:
            self.held = None
            return
        if now - self.gather_looked < GATHER_CHECK:
            return
        self.gather_looked = now
        loot = unshunned(run.loot(), now)
        self.again(run, loot.drops, here)
        spent = {d.unit_id for d in loot.drops if self.gathered.get(d.unit_id, 0) >= GATHER_TRIES}
        for found in loot.drops:
            if found.unit_id in spent:
                self.left(found, here, self.given_up(found.unit_id), 'the sweep')
        loot = replace(loot, drops=tuple(d for d in loot.drops if d.unit_id not in spent))
        plan = choose(loot, here)
        guarded: tuple[int, int] | None = None  # (the drop left for later, the hostiles near it or the character)
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
                guarded = (plan.drop.unit_id, len(close))
                plan = None
        # A valuable in sight the sweep does not take now (no room for it, or hostiles by it) is stayed by: the
        # Tower, 17:56:14 on 2026-10-11, a Grand Charm came down 20 away, the sweep said nothing, jumped twice
        # and stood 31 from it; the player went back for it by hand. Not one given up (above): its tries are
        # spent, and staying by it holds the sweep for nothing (River of Flame, 00:26:49 on 2026-10-14: 3.9 s
        # of "no better place" by a Large Charm with six hostiles near, run-0025-findings.md §2.3).
        # Not by gear the filter shows that there is no room for (world.py `prized`): the mode goes on to
        # the hostiles (Drifter Cavern, 19:59:52 on 2026-10-12: "the sweep stays by Magic Kriss", 13
        # hostiles 39 away and attack mode idle; user: "allow moving when the item isn't very valuable").
        near = [
            d
            for d in loot.drops
            if d.kind == VALUABLE
            and math.dist(here, (d.x, d.y)) <= HOLD_SIGHT
            and (d.prized or has_room(loot.room, d.size))
        ]
        self.held = min(near, key=lambda d: math.dist(here, (d.x, d.y))) if near else None
        if plan is None:
            held = self.held
            if held is not None and held.unit_id not in self.held_said:
                if len(self.held_said) > 200:
                    self.held_said.clear()
                self.held_said.add(held.unit_id)
                if not has_room(loot.room, held.size):
                    why = 'the inventory has no room for it'
                elif guarded is not None and guarded[0] == held.unit_id:
                    why = f'{guarded[1]} hostiles within {GATHER_CLEAR:.0f} of it or the character'
                else:
                    why = 'left for later'
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
        try:
            with run.actuator.held_act():
                at = (nearest.x, nearest.y)
                self.go(run, level, ground, player, rect, at, label(nearest), world.doors, key_names)
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: the sweep ends: no way to %s (%s)', label(nearest), stop)
            self.sweep.end()
            return False
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
        intent = replace(OWN_MOVE, short=STAND_OFF, shot=True, shuns=self.sweep.shuns)
        return self.travel.stride(run, world, ground, aspect, (nearest.x, nearest.y), intent)

    def asked_step(self, run: Run, world: World, foes: list[Monster], reachable, ground, aspect) -> Step | None:
        """The pickup request inside a fight. With anything to pick up (pickup.choose: a valuable, gold
        within a jump, a potion the belt wants) the fight stops for the pickup step at once (Cancelled,
        which the runner reads as the mode's pause). With nothing: the step to take now, if one is
        worth it."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        plan = choose(unshunned(run.loot(), run.clock()), here) if run.loot is not None else None
        if (
            plan is not None
            and plan.drop.kind in (HEALING, REJUVENATION)
            and threat(run)(here, (plan.drop.x, plan.drop.y))
        ):
            plan = None  # a potion among monsters is left by the pickup step too: no pause of the fight for it
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
            if run.stops(stop):
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
            self.stands = None if player is None else (player.x, player.y)
            # Asked once the character is seen and not before the first look: the runner names the build
            # by that look (`use`), and a hunt made before any game has the fallback until then.
            attack = None if player is None else self.attack  # Abort: the build does not fight
            self.casting = player is not None and player.mode in ACTING
            self.sense(run)
            if player is not None:
                self.area = None if player.in_town else player.area  # the level whose potions are kept (`sense`)
                if player.in_town:
                    self.mode = None  # no run mode in town (the HUD's word for it: runner.py `run_badge`)
                if self.pursuing:
                    self.hand(run, world)  # a level run's pause and resume (pursuit off: no run, no look at the hand)
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
                if player is not None and self.pursuing and self.pressed(run.clock()):
                    # The player's own move wins over the key's; a panel or the town is the route's own step's
                    if why:
                        self.tell(run, f'the key waits: {why}', aloud=False)
                    else:
                        self.defer(run, None, 'the town or an open panel')
                self.step_aside()
                self.nap(run, POLL)  # the player's move (a key, the left button, a run): waited through
                continue
            assert attack is not None  # the character is seen
            foes = self.foes(world, run.clock())
            if self.leashed and player.mode in DEAD:
                self.end_run(run, 'the character died')
            elif self.running and (not self.sweep.steps or run.clock() > self.sweep.until):
                # A level run keeps the sweep's look for a better place in its fights (the stance rules:
                # combat/stance.py `camp`), as the pickup key's sweep had it; its moves are the run's.
                self.sweep.start(run.clock())
            between = self.running and not self.advancing(run.clock())
            if between and self.upkeep(run, world, foes, key_names, renewing=not self.quiet(world, foes)):
                # Between the run's moves: in the quiet the whole upkeep (Consume lapsed, a Defiler dead: the run's
                # moves starved it, Consume was down 59 s and 121 s on 2026-10-14, run-1932-findings.md issue 3), and
                # else a buff that would end inside the boss's fight the route brings next (macros/buffs.py `lapsing`;
                # its row says what quiet is)
                continue
            if self.pursuing:
                # The key first, before a buff is kept up or a strike begun: its move goes out at once
                found = self.known_level(player)
                over = Ground(found.ground if found is not None else ())
                at = (player.x, player.y)
                near = any(in_reach(over, at, (m.x, m.y), attack.reach, world.doors) for m in foes)
                if self.pursue(run, world, foes, over, key_names, in_reach=near):
                    entered = run.clock()  # as after a teleport step: the main weapons wait MAIN_AFTER
                    continue
            if self.upkeep(run, world, foes, key_names):
                continue
            level = self.known_level(player)
            ground = Ground(level.ground if level is not None else ())
            here = (player.x, player.y)
            if not any(in_reach(ground, here, (m.x, m.y), attack.reach, world.doors) for m in foes):
                self.step_aside()
                if not self.running:  # a level run takes its drops as goals of its own (`side_drop`)
                    self.gather(run, here, foes)
                if self.pursuing and self.pursue(run, world, foes, ground, key_names, in_reach=False):
                    entered = run.clock()
                    continue
                running = self.running  # a level run's moves are its own: not the sweep's toward the nearest
                if self.sweep.steps and foes and not running and self.follow_on(run, world, foes, ground, key_names):
                    continue
                if foes and run.clock() - logged_at >= IDLE_LOG_SECONDS:
                    logged_at = run.clock()
                    nearest = min(foes, key=lambda m: math.dist(here, (m.x, m.y)))
                    LOG.info(
                        'Macro: idle: %d hostiles, none in reach; nearest %s %.0f away, shot %s, from (%.0f, %.0f)',
                        len(foes), label(nearest), math.dist(here, (nearest.x, nearest.y)),
                        'clear' if clear_shot(ground, here, (nearest.x, nearest.y), world.doors) else 'blocked', *here,
                    )  # fmt: skip
                self.nap(run, POLL, key=self.pursuing)
                continue
            rect = run.actuator.keys.focused_window_rect()
            if rect is None:
                self.nap(run, POLL)
                continue
            try:
                strike_input(run, world, key_names, attack.skill)
                unready_since = None
            except Abort as stop:
                if run.stops(stop):
                    raise
                # Right after a hop the right button still holds Teleport, after a mark Death Mark: the
                # game puts the skill back within a moment, so wait; only an input that stays away is a
                # stopped fight, unless the strike can be put back on the right button (`strike_back`).
                unready_since = run.clock() if unready_since is None else unready_since
                if run.clock() - unready_since < INPUT_SECONDS:
                    self.nap(run, FRAME)
                    continue
                if self.strike_back(run, world, attack.skill):
                    unready_since = None
                    continue
            try:
                # The main weapons for a tough pack, and only once the mode has run MAIN_AFTER since the
                # last step: a swap after every hop of a chain of seek steps, and the staff back for the
                # next, costs more standing than it gains. A fight begun earlier is fought with what is
                # held and stops for the swap at that time.
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), attack.reach, world.doors)]
                boss = any(m.txt_id in BOSSES for m in reachable)  # the chain of hops ended at it
                tough = self.pursuing or boss or self.tough(world, reachable)
                settled = self.pursuing or boss or run.clock() - entered >= MAIN_AFTER
                held = self.main_weapons(run, world, key_names, swap=settled and tough)
                if self.pursuing and not held:
                    self.tell(run, 'waiting for the priced battle weapons')
                    self.nap(run, POLL)
                    continue
                pause = entered + MAIN_AFTER if tough and not held and not self.pursuing else None
                self.fight(run, ground, rect[2] / rect[3], key_names, until=pause)
                misses = 0
                self.take_guard(run, rect[2] / rect[3], key_names, ground)  # the safety step it stopped for
                self.take_step(run, rect[2] / rect[3], key_names, ground)  # the step the fight stopped for, if any
            except Cancelled:
                raise  # the mode's own pause for a valuable (`asked_step`), or the runner's cancel
            except Abort as stop:
                if run.stops(stop):
                    raise
                misses += 1
                LOG.info('Macro: the fight stopped (%s), %d in a row', stop, misses)
                if misses >= MISSES_IN_A_ROW:
                    raise Abort(f'attack mode off: {misses} fights stopped in a row, the last on "{stop}"') from stop
                self.nap(run, POLL)

    def strike_back(self, run: Run, world: World, skill: int) -> bool:
        """Keyboard mode, the strike on no key and on neither mouse button for INPUT_SECONDS (a controller stint left
        the pad's skill on the right button: rca/2026-10-14/run-1904-findings.md §3.7): the macro selects it on the
        right button in the game's skill selection (macros/skillpanel.py), at most once in STRIKE_BACK_RETRY, where
        the build's layer knows its icon (`Build.skill_icons`); whether the right button holds it now."""
        player = world.player
        icon = self.build.skill_icons.get(skill)
        if run.pad is not None or icon is None or player is None or player.right_skill is None:
            return False  # the right skill unread: the selection's outcome could not be seen
        now = run.clock()
        if now - self.struck_back_at < STRIKE_BACK_RETRY:
            return False
        self.struck_back_at = now
        LOG.info(
            'Macro: skill panel: %s is on no skill key and on neither mouse button (left %s, right %s): selecting it '
            'on the right button',
            skill_name(skill), skill_name(player.left_skill), skill_name(player.right_skill),
        )  # fmt: skip
        run.say(f'{skill_name(skill)} back on the right button')
        try:
            with run.actuator.held_act():
                select_right(run, skill, icon)
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: skill panel: %s', stop)
            return False
        return True

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
        character the macros do not know (a build without weapon sets: no layer of the character's
        own, `Build.weapons`), or hands that cannot be read, are left as they are; a swap
        that did not come is not asked for again for SWAP_RETRY_SECONDS."""
        loadout = self.build.weapons if world.player is not None else None
        if loadout is None:
            return True
        if run.hands is None:
            return not self.pursuing
        if run.clock() - self.swap_failed_at < SWAP_RETRY_SECONDS:
            return not self.pursuing or bool(loadout.battle & set(run.hands()))
        held = set(run.hands())
        if not held:
            return not self.pursuing
        if loadout.battle & held:
            return True
        if not swap:
            return False
        run.keys.update(key_names(world, (SWAP_WEAPONS,)))
        run.battle_hands = loadout.battle
        run.say('Main weapons for the fight')
        take_battle_weapons(run)
        if not loadout.battle & set(run.hands()):
            self.swap_failed_at = run.clock()
            return not self.pursuing
        return True

    def sense(self, run: Run) -> bool:
        """Look at the left mouse button; a press is a move asked for (`self.move`). True on a new press."""
        looked = self.drinker.looked_at
        self.drinker.look(run, self.stands)  # the life first: a potion is drunk beside whatever is in hand
        loot = self.drinker.last
        if self.drinker.looked_at != looked and loot is not None and self.area is not None and self.stands:
            pressed = self.drinker.pressed_at.get(PotionType.HEALING, -math.inf)
            empty = self.potions.see(loot, self.area, self.stands, run.clock(), pressed)
            if empty is not None:
                # "something is wrong if we're empty" (the player, 2026-10-13): in the log, with the cause the run
                # sees. Not on the card: the mercenary may drink every healing potion (the player, later that day:
                # "you can use all hp potions on merc"), so an empty belt is the potion pickup's to answer.
                LOG.warning('Macro: potion stock: %s', empty)
        down = run.actuator.button_held(1)
        if down and run.pad is not None:
            # In controller mode a click is the player's and flips the game back: no move is made for it.
            raise Abort('a mouse button was pressed (the game leaves controller mode)')
        pressed = down and not self.left_down
        self.left_down = down
        if down:
            self.hand_at = run.clock()  # the hand at work: a paused level run waits for it to rest
        if pressed:
            self.expired_motion = False
            self.sweep.end()  # the player moves by hand: no step of the mode's own after it
            self.pause_run(run, 'a click')
            self.move = Move(run.clock(), run.actuator.keys.pointer(), swallowed=self.casting)
            self.fresh_press = True
        return pressed

    def nap(self, run: Run, seconds: float, *, key: bool = False) -> bool:
        """Sleep `seconds`, looking at the left button every SLICE (a click is down for 60-120 ms);
        cut short, and True, on a press. With `key` a press of the teleport key posted meanwhile (the
        pursuit's mailbox) also ends the sleep, with False: it is no move of the player's hand."""
        until = run.clock() + seconds
        self.fresh_press = False
        posted = self.pursuit
        while True:
            self.sense(run)
            if self.fresh_press:  # seen here or inside the sleep (attack mode's own `watchful`)
                return True
            if key and self.pursuit is not posted:
                return False
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
        if world.open_panels:
            # The player has a panel open (the inventory, the cube, the stash): a click made again there could drop
            # an item held on the cursor (run-2110-findings.md §2.4, 21:13:59.93). The move is the player's now (I7).
            LOG.info('Macro: the click the cast swallowed is not made again: %s open', ', '.join(world.open_panels))
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
            if run.stops(stop):
                raise
            LOG.info('Macro: the click for the player was not made (%s)', stop)
            self.move = None
            return
        move.clicked(run.clock())
        LOG.info(
            'Macro: the click the cast swallowed made again at %s, %.2fs after the press (%d of %d)',
            move.pixel, move.clicked_at - move.at, move.clicks, MOVE_CLICKS,
        )  # fmt: skip

    def upkeep(self, run: Run, world: World, foes: list[Monster], key_names, *, renewing: bool = False) -> bool:
        """A buff kept up outside a fight: the first row of the build's upkeep that is due is cast, and
        whether one was. A cast of one key is followed by a pause; one that cannot be made is logged, counts
        as made now, and the mode goes on. A row with a caster takes seconds and answers for its own
        failures (macros/build.py `Tried`): a step that waits for the fight goes first. The rows are asked with
        the boss's fight the route brings next (`ahead`); `renewing`: only a buff that would end inside it."""
        player = world.player
        facts = self.buffs.facts(run, world, foes, ahead=self.ahead(player.area if player is not None else None))
        due = self.buffs.first(run, 'upkeep', facts, renewing=renewing)
        if due is None:
            return False
        own = due.row.caster is not None
        if own:
            self.step_aside()
        try:
            self.buffs.cast(run, due, key_names)
            if not own:
                run.pause('key')
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: no %s (%s)', skill_name(due.row.skill), stop)
            self.buffs.remember(due.row, run.clock())
        return True

    def ahead(self, area: int | None) -> float:
        """Seconds of a boss's fight the route brings next on level `area` (goals.py `boss_ahead`: the fight's
        stage, or the last seal of an arm): BOSS_AHEAD, else 0."""
        progress = self.bearings.progress
        step = progress.step(area) if progress is not None and area is not None else None
        script = getattr(step, 'script', None)
        if step is None or script is None:
            return 0.0
        return BOSS_AHEAD if boss_ahead(script.stages, step.stage) else 0.0

    def tough(self, world: World, reachable: list[Monster]) -> bool:
        """Whether what is in reach is worth a swap to the main weapons, which have the damage and the
        resistances at the cap (the teleport set leaves lightning at 8 and cold at 18 in Hell; user,
        2026-10-12: "we should swap to it against most of tough/hard-hitting enemies/bosses"):

        - a pack leader (a unique, a champion, a super unique), a Herald or one of a Herald's minions.
          Tower Cellar 5, 2026-10-11: the whole fight with a tier 2 Herald and the death on the staff's
          set, as its 13 times the life is not in the count below;
        - TOUGH_POINTS of life between them, an elite's counted ELITE_LIFE times;
        - plain monsters that hit hard together: a threat score (terror/danger.py) of HARD_SCORE, which
          two Gloams, four Dark Rangers or eight Extra Strong Blood Clan reach and eight plain ones or
          a herd of cows do not.

        The swap costs most of a second there and back; the caller asks for it only once the mode has
        run MAIN_AFTER since the last step."""
        if world.player is None:
            return False
        if any(m.tier or m.leader for m in reachable):
            return True
        seen = observe(world.player, reachable, ())
        if sum(foe.left * (ELITE_LIFE if foe.elite else 1.0) for foe in seen.foes.values()) >= TOUGH_POINTS:
            return True
        units = [Unit(m.unit_id, m.txt_id, m.x, m.y, m.modifiers, None, False, m.flags, m.tier) for m in reachable]
        return any(pack.score >= HARD_SCORE for pack in packs(units))

    def moving(self, run: Run, world: World, *, keys: bool = True) -> str | None:
        """Why the pointer is the player's right now, or None: a key of theirs is down, the left mouse
        button is down (a move), or the character is walking or running somewhere. Attack mode yields
        to all three: it must never get in the way of moving. With `keys` off a held key is no reason
        (a fight under way: the strike stays held through the player's own key taps)."""
        if keys and run.actuator.key_held():
            self.expired_motion = False
            return 'a key is held'
        if run.actuator.button_held(1):
            self.expired_motion = False
            return 'the left button is down'
        if world.player is not None and world.player.mode in RUN_MODES:
            if self.pursuing and self.expired_motion:
                return None  # our old click is not the player's permission to keep walking
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
        self.expired_motion = False
        return None

    def choose(
        self, world: World, foes: list[Monster], reachable: list[Monster], ground: Ground, view: Viewport
    ) -> Choice:
        """Where to cast now (combat/controller.py `aim_choice`, the decision the simulator scores as
        `live`): the attack's cast over the hostiles in sight (for the Warlock the policy's line), else
        straight at what is in reach, and a focal point the window lets the pointer reach. A boss in
        reach (terror/bosses.py) has the cast laid through it."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT]
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        attack = self.attack
        seen = attack.sees(
            observe(
                player, near, companions, ground, world.doors, aimable=lambda focal: view.reachable_focal(here, focal)
            ),
            companions,
        )
        bosses = [m.unit_id for m in reachable if m.txt_id in BOSSES]
        # A hostile bound to a summoner seen alive (combat/threats `bound`: Baal's clone goes with him) is no target
        # while anything else is in reach: what it is worth is lost at the summoner's death. The summoner in reach is
        # struck first, its kill ends both; else the rest (a tentacle) before it (rca/2026-10-14/baal-sim.md fix 2)
        lost = self.bound_lost(foes, reachable)
        if lost:
            seen = replace(seen, foes={unit: foe for unit, foe in seen.foes.items() if unit not in lost})
        reached = {m.unit_id for m in reachable}
        masters = [unit for held in lost.values() for unit in held if unit in reached and unit not in bosses]
        # What bars the pursuit's goal (`blocking`: a pack on a seal) is struck through first, after a boss
        barring = self.blocking[1] if self.blocking is not None else frozenset()
        if self.pursuing:
            barring = barring | frozenset(self.safety.blocked_by)
        first = bosses + list(dict.fromkeys(masters))
        first += [m.unit_id for m in reachable if m.unit_id in barring and m.unit_id not in {*first, *lost}]
        aimer = self.aimed_by if self.aimed_by is not None else attack
        found = aim_choice(aimer, seen, [m.unit_id for m in reachable if m.unit_id not in lost], first=first)
        assert found is not None  # the caller has something in reach
        return found

    def only_bound(self, world: World, foes: Sequence[Monster], ground: Ground, here: Point) -> bool:
        """Whether every hostile in reach is bound to a summoner seen alive (combat/threats `bound`): a strike there is
        lost, as it dies with its summoner. Said once a change (`Macro: pursuit: ... dies with ...`)."""
        lost = threats.bound({m.unit_id: m.txt_id for m in foes})
        reachable = [m for m in foes if in_reach_of(ground, here, (m.x, m.y), self.reach, world.doors)]
        only = bool(reachable) and all(m.unit_id in lost for m in reachable)
        if only:
            by_unit = {m.unit_id: m for m in foes}
            for m in reachable:
                if m.unit_id not in self.away_said:
                    if len(self.away_said) > 200:
                        self.away_said.clear()
                    self.away_said.add(m.unit_id)
                    LOG.info(
                        'Macro: pursuit: %s, the only one in reach, dies with %s: no fight to hold, the goal first',
                        label(m), label(by_unit[lost[m.unit_id][0]]),
                    )  # fmt: skip
        return only

    def bound_lost(self, foes: Sequence[Monster], reachable: Sequence[Monster]) -> dict[int, tuple[int, ...]]:
        """The hostiles in reach bound to a summoner seen alive (combat/threats `bound`), with its units: no target
        while anything else is in reach (`choose`); empty when nothing else is (the mode alone strikes what it has).
        Said once a hostile."""
        by_unit = {m.unit_id: m for m in foes}
        bound = threats.bound({m.unit_id: m.txt_id for m in foes})
        lost = {m.unit_id: bound[m.unit_id] for m in reachable if m.unit_id in bound}
        if len(lost) == len(reachable):
            return {}
        for unit, held in lost.items():
            if unit not in self.bound_said:
                if len(self.bound_said) > 200:
                    self.bound_said.clear()
                self.bound_said.add(unit)
                LOG.info(
                    'Macro: target: %s dies with %s: not struck while anything else is in reach',
                    label(by_unit[unit]), label(by_unit[held[0]]),
                )  # fmt: skip
        return lost

    def off_labels(self, run: Run, view: Viewport, here: Point, focal: Point) -> None:
        """The pointer, standing on the aim for `focal`, moved along the line when an item's label is under it: the
        game casts a skill at the unit under the pointer, so with a label there the blades fly to
        where that item lies. The blades fly their length along the line wherever on it the pointer
        is (view.py), so a pointer further out or nearer in keeps them on the monster.

        Drifter Cavern, 09:52:34 on 2026-10-12 (user: "it aimed off and continued shooting there until I
        started steer with mouse myself"): the pointer stood on the ground of a Hell Temptress 5 units
        off, at -48 degrees, for 13.8 s; the 115 blades of 21 casts flew out between -15 and +15 degrees,
        toward potions lying there, and the monster lost 44 of its 128 points to the companions."""
        if run.hovered is None:
            return
        away = math.dist(here, focal)
        tried = []
        for shift in LABEL_SHIFTS:
            if shift:
                if away + shift < MIN_FOCAL:
                    continue
                share = (away + shift) / away
                point = (here[0] + (focal[0] - here[0]) * share, here[1] + (focal[1] - here[1]) * share)
                where = view.aim(here, point)
                if where is None:
                    continue
                run.actuator.aim(*where, scatter=(2, 2))
                run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            if over is None or over[0] != ITEM_UNIT_TYPE:
                if tried:
                    LOG.info(
                        "Macro: an item's label under the aim at (%.1f, %.1f) (%s): the pointer %+.0f units along "
                        'the line instead',
                        *focal, ', '.join(tried), shift,
                    )  # fmt: skip
                return
            tried.append(f'{shift:+.0f}: item {over[1]}')
        LOG.info("Macro: an item's label under every aim along the line to (%.1f, %.1f): %s", *focal, ', '.join(tried))

    def fight(self, run: Run, ground: Ground, aspect: float, key_names, until: float | None = None) -> None:
        """Strike while anything is in reach and the player stands: one hold of the strike input
        through the whole fight, the pointer kept on the policy's line, which is asked again every
        DECIDE_SECONDS and when its monster is gone. Ends when nothing is in reach, when the player
        moves (the mode yields and comes back after), at `until` (the caller's swap to the main
        weapons), or after FIGHT_SECONDS."""
        started = run.clock()
        attack = self.attack
        held, how = strike_input(run, run.world(), key_names, attack.skill)  # before any cast: no key, no fight
        down = 0
        cast = CastWatch(started)  # the casts seen since the press (combat/controller.py)
        choice: Choice | None = None
        decided_at = -math.inf
        aim = Aim((run.actuator.keys.pointer(), -math.inf))  # where the pointer was put, and the player's hand
        view = Viewport(aspect)
        again: Callable[[], None] | None = None
        watched: set[int] = set()  # the hostiles seen in reach while the input was held
        lined: int | None = None  # the monster the line last logged went through
        labels_due = math.inf  # clock time of the next look for an item's label under the standing pointer
        counted = 0  # the casts seen up to the last look
        guarded_at = -math.inf  # clock time of the last safety look of the mode alone (`guard`)
        ended = f'Fight stopped after {FIGHT_SECONDS:.0f}s'
        with ExitStack() as stack:
            stack.callback(setattr, self.buffs, 'let_go', None)
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
                    raise Abort(f'no cast seen after the {how} ({skill_name(attack.skill)} not on {how}?)')
                self.casting = again is not None or player.mode in ACTING
                if player.mode in ACTING and attack.skill in (player.left_skill, player.right_skill):
                    self.struck_at = run.clock()  # the strike-gap fact of the pursuit's arbiter (`Facts.quiet`)
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
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), attack.reach, world.doors)]
                if not reachable:
                    ended = 'Nothing left in reach'
                    break
                if self.pursuing and self.key_asks(run, world, foes, ground):
                    ended = 'Yielded (the key asks for a move)'  # the mode makes it at its next look
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
                if self.sweep.steps and not self.running:
                    self.gather(run, here, foes)
                if not self.pursuing and self.guarded(foes) and run.clock() - guarded_at >= DECIDE_SECONDS:
                    # The pursuit loop's safety step for the mode alone (`guard`): a dodge or a model's place only
                    guarded_at = run.clock()
                    self.guarding = self.guard(run, world, foes, ground)
                    if self.guarding is not None:
                        ended = 'Stepping out of harm'
                        break
                if (
                    self.pursuing
                    and self.running
                    and self.build.settings.fight_look
                    and run.clock() - self.sweep.looked >= FOLLOW_CHECK
                ):
                    # A level run's fight keeps the sweep's look for a better place (rca/2026-10-13/kp1-level-run.md
                    # §2: the crowd escape and the keep-away floors with it), its place priced by the safety against
                    # holding (`Safety.offer`): the run's next look moves there when it is worth it, one mover
                    # (run-1932-findings.md §4: Hold alone was priced in the safe fights, struck from 17 to 22 units).
                    self.sweep.looked = run.clock()
                    better = self.next_step(run, world, foes, ground, aspect, fighting=True, priced=True)
                    self.safety.offer(better, run.clock())
                    if better is not None:
                        LOG.info(
                            'Macro: run: a better place in the fight with %d of %d hostiles in reach, from '
                            '(%.1f, %.1f): %s; the safety prices it',
                            len(reachable), len(foes), *here, step_line(better, here),
                        )  # fmt: skip
                if not self.pursuing and self.sweep.due(run.clock()):
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
                    if self.pursuing and prey.unit_id in self.nearing:
                        ended = f'Getting back in reach of {label(prey)}'  # a boss: the run's move comes first
                        break
                    continue
                counted = cast.casts
                # The strike first, Death Mark and the sigil under it once a cast is out: cast before the
                # press they held the first strike back 0.3 to 0.7 s on 190 of 405 fight starts (logs of
                # 2026-10-10, tests/inventory_tracking/scenarios/loop). The first cast flies unmarked.
                struck = again is not None and (cast.casts > 0 or run.clock() - cast.began >= FIRST_STRIKE_SECONDS)
                if struck:
                    # The build's casts under the strike, each asked in the plan's order with the clock as it
                    # reads then. A cast's own animation swallows a click as a strike does and is no missing
                    # strike; one that moved the pointer leaves the strike's aim to be put back.
                    # With the safety pricing's last prices of the build's draw (build.py `Draw`), while fresh
                    draws = self.safety.priced(run.clock())
                    asked = self.buffs.facts(run, world, foes, reachable, prey, draws)
                    for row in self.buffs.rows('fight'):
                        due = self.buffs.due(run, row, asked)
                        if due is None:
                            continue
                        self.casting = True
                        if self.buffs.cast(run, due, key_names, aspect).touched:
                            if row.on != 'self':
                                aim.forget()
                            cast.excuse(run.clock())
                            self.buffs.resume(run, again)
                pointer, left_at = run.actuator.keys.pointer(), run.actuator.left_at
                if run.pad is not None:
                    # Controller mode: the client strikes at its own target; it is turned toward the prey
                    # until the target names it (macros/pad.py). No pointer, no labels under it.
                    run.pad.steer(MONSTER_UNIT, prey.unit_id, here, (prey.x, prey.y), label(prey))
                elif aim.due(run.clock(), pointer, left_at, choice.focal, here):
                    where = view.aim(here, choice.focal)
                    if where is None:
                        ended = f'Nothing in view to aim at ({label(prey)} is off the screen)'
                        break
                    run.actuator.aim(*where, scatter=(3, 3))
                    aim.put(choice.focal, here, run.actuator.keys.pointer())
                    labels_due = run.clock() + HOVER_SECONDS  # once the game has noted what is under it
                elif pointer == left_at and run.hovered is not None and run.clock() >= labels_due:
                    # The pointer stands where the macro left it: an item's label may be under it, then or
                    # from a drop fallen since. Looked at without holding the strike's loop up.
                    labels_due = run.clock() + LABEL_SECONDS
                    over = run.hovered()
                    if over is not None and over[0] == ITEM_UNIT_TYPE:
                        self.off_labels(run, view, here, choice.focal)
                        aim.put(choice.focal, here, run.actuator.keys.pointer())
                if again is None:
                    run.say(f'{skill_name(attack.skill)} ({how}) at {label(prey)}, {life(prey)}')
                    hold = run.pad.hold(attack.skill) if run.pad is not None else run.actuator.hold(*held)
                    again = stack.enter_context(hold)
                    self.buffs.let_go = getattr(again, 'release', None)  # for a key under the strike
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
