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
from contextlib import ExitStack
from dataclasses import replace

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
from inventory_tracking.combat.policy import MIN_FOCAL, RUN_MODES, STRIKE_REACH, Choice, Policy, observe
from inventory_tracking.combat.score import LiveScore
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Drop, Monster, World
from inventory_tracking.levels.model import Ground, Level, Room, Target
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros.actuator import POINTER_DRIFT, Abort, Cancelled
from inventory_tracking.macros.agenda import Agenda
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import Attack, Build, Intent
from inventory_tracking.macros.drinking import Drinker
from inventory_tracking.macros.drop_ledger import DropLedger
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import WAIT, Goal, boss_ahead
from inventory_tracking.macros.hunting import choice, judging, moves, sweep
from inventory_tracking.macros.hunting.base import (
    BOSS_AHEAD,
    DECIDE_SECONDS,
    FIGHT_SECONDS,
    FIRST_STRIKE_SECONDS,
    FOLLOW_CHECK,
    FRAME,
    HARD_SCORE,
    HERALD_OMEN,
    HURT_SECONDS,
    IDLE_LOG_SECONDS,
    INPUT_SECONDS,
    ITEM_UNIT_TYPE,
    LABEL_SECONDS,
    LABEL_SHIFTS,
    MAIN_AFTER,
    MISSES_IN_A_ROW,
    NEARING_SECONDS,
    OMEN_LOOK,
    OMEN_SECONDS,
    POLL,
    QUIET_UNITS,
    RUN_IN_PLACE,
    RUSH_UNMOVED,
    SIGHT,
    SLICE,
    STRIKE_BACK_RETRY,
    SWAP_RETRY_SECONDS,
    TOUGH_POINTS,
    UNTOUCHABLE_SECONDS,
    UNTOUCHED_CASTS,
    WAIT_LOG_SECONDS,
    Bearings,
    Judging,
    Remembered,
    Sweep,
    hostiles,
    strike_input,
    threat,
)
from inventory_tracking.macros.pad import MONSTER_UNIT
from inventory_tracking.macros.pickup import Refused
from inventory_tracking.macros.pursuit import NONE, SETTLE, Move as Advance, Pursuit, Told, settled
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.routines import ACTING, DEAD, Dead, take_battle_weapons
from inventory_tracking.macros.runmode import Mode, Taps, tapped
from inventory_tracking.macros.safety import Safety
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach, in_reach as in_reach_of
from inventory_tracking.macros.skillpanel import select_right
from inventory_tracking.macros.skills import SWAP_WEAPONS, skill_name
from inventory_tracking.macros.supply import Potions
from inventory_tracking.macros.teleport import HOVER_SECONDS, MOVED, Way, hop_toward
from inventory_tracking.macros.tour import Bounds, tour
from inventory_tracking.macros.travel import LOOPED, Point, Step, Tally, Travel, label, life, step_line
from inventory_tracking.macros.view import Viewport
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror.bosses import BOSSES
from inventory_tracking.terror.danger import Unit, packs


__all__ = ['Bearings', 'Hunter', 'threat']


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
        # The KP_6 loop's moves: Blade Warp alone, or with the staff's Teleport while the gold pays for it (the runner
        # sets it from macros/loop.py `teleports`)
        self.looped: Intent = LOOPED
        self.stuck_until = -math.inf  # until when the loop's moves may take Teleport though it is off (`stuck`)
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
        # unit -> (clock judged, Teleport brings it within LOOP_PICK_SECONDS): the loop's far valuables (`on_the_way`)
        self.far_judged: dict[int, tuple[float, bool]] = {}
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
        self.life_seen: int | None = None  # the character's life at the last priced look (`safety_priced`)
        self.hurt_at = -math.inf  # clock time a priced look last saw the character's life go down
        self.own_read: tuple[bool, float] | None = None  # (Teleport the character's own, read at) (`own_teleport`)
        self.unmoved_since: float | None = None  # since when the loop's run made no move with a hostile in reach
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
        self.drops = DropLedger()  # what the run tried and gave up on, drop by drop (macros/drop_ledger.py)
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
        self.shack_tries: dict[int, int] = {}  # a shack's container (unit): the loop's tries to open it (`shack_goal`)
        self.use_tries: dict[int, int] = {}  # a route's object (unit): the tries to use it (ROUTE_USE_TRIES)
        self.dead_ends: list[tuple[Point, float]] = []  # spots a move did not reach, and until when they are passed
        # the runner's: a level run ended by the hunt itself (the route's end, the character's death), with why
        self.run_over: Callable[[str], None] | None = None
        # The runner's (runner.py `_carry_one`): whether a unique Grand Charm refused for the Gheed's Fortune carried
        # (macros/pickup.py `Refused`) starts the KP_6 loop's Gheed's swap, which the level run then ends for
        # (`carry_one_swap`); None, or False: the run's own rules (the try counted, the drop given up after
        # GATHER_TRIES). `swap_asked`: the drops given up whose swap was asked (`side_drop`), once each
        self.carry_one: Callable[[Refused], bool] | None = None
        # The terror zone kinds' agenda (macros/agenda.py), and the policy of each level (macros/tzroutine.py
        # `policy_of`): the runner's, set when it posts their level run (runner.py `_loop_level_run`)
        self.agenda: Agenda | None = None
        self.agenda_policy: Callable[[int], str] | None = None
        self.agenda_said: tuple | None = None  # the last target said (`agenda_target`)
        # (game, level)s whose route goal the run found no way to: worked as COVER from then on (`agenda_target`)
        self.wayless: set[tuple[str, int]] = set()
        self.ended_area: int | None = None  # the level of the level run that ended last (`end_run`)
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
        # A Herald's coming: its spot -> until when, on the level `omen_area`, and when the missiles were last read
        self.omens: dict[Point, float] = {}
        self.omen_area: int | None = None
        self.omen_looked = -math.inf
        self.toured: tuple[int, int, int] | None = None  # (level, rooms, explored) said to have no stop
        # Makes room in the cube for a valuable the inventory has none for (the runner's: the macro's own pickups into
        # it, macros/cube.py `stash`), how many went; None: none is made. Tried once a drop (`room_tried`)
        self.room_maker: Callable[[Run], int] | None = None
        self.room_tried: int | None = None
        # Whether the KP_6 loop is on (the runner's): the sweep then holds a plain valuable with no room too, for the
        # loop's room rules (macros/lootpolicy.py `NO_ROOM_PLAIN`, ruled 2026-10-18 17:50)
        self.looping: Callable[[], bool] = lambda: False

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
        if monster.tier and monster.leader:
            return True  # a Terror Zone's Herald (stat 367, a unique): fought to its end (HERALD_OMEN)
        return monster.txt_id in BOSSES or any(monster.txt_id == txt for txt, _ in self.build.settings.safety.dear)

    def omens_now(self, run: Run, area: int, now: float) -> list[Point]:
        """The spots a Herald is coming to on level `area` (HERALD_OMEN), each kept OMEN_SECONDS from its first read."""
        if area != self.omen_area:
            self.omens, self.omen_area = {}, area
        flights = getattr(run, 'flights', None)
        if flights is not None and now - self.omen_looked >= OMEN_LOOK:
            self.omen_looked = now
            try:
                read = flights(frozenset((HERALD_OMEN,)))
            except OSError, ValueError:
                read = ()
            for _, _, x, y in read:
                if not any(math.dist((x, y), spot) < 1.0 for spot in self.omens):
                    self.omens[x, y] = now + OMEN_SECONDS
                    LOG.info('Macro: run: a Herald comes at (%.1f, %.1f) in 5 s: the run waits for it there', x, y)
                    run.say('A Herald is coming')
        self.omens = {spot: until for spot, until in self.omens.items() if until > now}
        return list(self.omens)

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
    def rushing(self) -> bool:
        """Whether the level run working now is the KP_6 loop's (`Pursuit.rush`): no look for a better place in a fight
        on its way (rca/2026-10-16/loop-chests-findings.md §1: 6.8 s of 43 moving to firing spots and better places)."""
        return self.running and self.pursuit is not None and self.pursuit.rush

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
            if old is not None and old.leashed and not pursuit.looped:
                # The run's crossing noted (`heading`) and its carrying on (`carried`) stay with it
                kept = {
                    'area': old.area,
                    'onward': old.onward,
                    'entered': old.entered,
                    'rush': old.rush,
                    'agenda': old.agenda,
                }
                if not pursuit.leashed:
                    pursuit = replace(pursuit, leash=old.leash, paused=old.paused, **kept)
                elif pursuit.area is None:
                    pursuit = replace(pursuit, **kept)  # a fresh pickup press: the run goes on, unpaused
            waited = self.pursued
            if waited is not None and waited.do == WAIT and waited.unit is not None:
                # A press while the run stands by a valuable with no room for it: the player goes on without it
                if len(self.waived) > 200:
                    self.waived.clear()
                self.waived.add(waited.unit)
            if pursuit.leashed and not pursuit.advance and not pursuit.looped:
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
            ended = replace(posted, leash=NONE, area=None, paused=False, onward=None, entered=None)
            self.pursuit = ended if posted.advance else None
            self.ended_area = posted.area  # the level the run was of (runner.py `_run_over`: the agenda's area worked)
        LOG.info('Macro: pursuit: the level run ends: %s', reason)
        self.travel.paced(run.clock() if run is not None else None, reason)
        self.told.new(None)
        self.mode_said = None  # the next run says its mode again
        if run is not None:
            run.say(f'Level run over: {reason}')
            if self.run_over is not None:
                # Not for the runner's own ends (run None: the toggles, the request, the game left), made under its lock
                self.run_over(reason)

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
                    self.unmoved_since = None
                    continue
                if near and self.rushing and run.clock() - self.hurt_at > HURT_SECONDS:
                    # The KP_6 loop's run: a look with no move (Blade Warp's delay running, mostly) is not a strike's
                    # unless the character was just hurt, or no move has come for RUSH_UNMOVED (something blocks the
                    # way). 95 of 97 strikes followed no loss of life after the arbiter's own hold was gone (02:15 to
                    # 02:25 on 2026-10-17), and a warp chain with a strike in it took 1.47 s a warp against 1.01
                    # (rca/2026-10-17/movement-findings.md §2)
                    if self.unmoved_since is None:
                        self.unmoved_since = run.clock()
                    if run.clock() - self.unmoved_since < RUSH_UNMOVED:
                        self.nap(run, FRAME)
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
        if not stops and self.toured != (level.area, len(level.rooms), len(seen)):
            # Said once a level and a count: a full clear ended 8 s into Tal Rasha's Tomb with its rooms unexplored
            # (00:35:56 on 2026-10-18), and nothing told why
            self.toured = (level.area, len(level.rooms), len(seen))
            LOG.info('Macro: run: the tour has no stop on level %d: %d rooms, %d explored, %d with a way from here',
                     level.area, len(level.rooms), len(seen), len(nearest))  # fmt: skip
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
                    raise Dead('the character is dead')
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
                if self.pursuing and self.key_asks(run, world, foes, ground, unstruck=again is None):
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
                    and not self.rushing
                    and self.build.settings.fight_look
                    and again is not None  # after the strike's press: the look held it back (F2, `key_asks`)
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

    # choice.py
    side_drop = choice.side_drop
    restock = choice.restock
    given_up_charm = choice.given_up_charm
    carry_one_swap = choice.carry_one_swap
    forget_given_up = choice.forget_given_up
    again = choice.again
    left = choice.left
    refused_potion = choice.refused_potion
    scarce = choice.scarce
    stay_by = choice.stay_by
    shack_goal = choice.shack_goal
    super_chest_goal = choice.super_chest_goal
    at_hand = choice.at_hand
    blockers = choice.blockers
    goal = choice.goal
    cleared = choice.cleared
    _forget_passed = choice._forget_passed
    _on_the_way = choice._on_the_way
    _clear_through = choice._clear_through
    agenda_cleared = choice.agenda_cleared
    agenda_target = choice.agenda_target
    agenda_chests = choice.agenda_chests
    agenda_chest = choice.agenda_chest
    goal_key = choice.goal_key
    taken_back = choice.taken_back
    went_for = choice.went_for
    goes_on = choice.goes_on
    on_the_way = choice.on_the_way
    walked_near = choice.walked_near
    teleport_reach = choice.teleport_reach
    pass_by = choice.pass_by
    rest_of = choice.rest_of
    next_room = choice.next_room
    run_mode = choice.run_mode
    carry_on = choice.carry_on
    nearby = choice.nearby

    # judging.py
    judge = judging.judge
    safety_priced = judging.safety_priced
    escorted = judging.escorted
    guard = judging.guard
    guarded = judging.guarded
    take_guard = judging.take_guard
    key_asks = judging.key_asks
    tell = judging.tell
    defer = judging.defer
    blocked = judging.blocked

    # moves.py
    dead_end = moves.dead_end
    looped_now = moves.looped_now
    barred = moves.barred
    pursue = moves.pursue
    way_time = moves.way_time
    stale = moves.stale
    give_up = moves.give_up
    priced_for = moves.priced_for
    advance = moves.advance
    warp_ready = moves.warp_ready
    operate = moves.operate
    pursue_once = moves.pursue_once
    known_level = moves.known_level
    seek = moves.seek
    go = moves.go
    own_teleport = moves.own_teleport
    worn = staticmethod(moves.worn)
    afoot = moves.afoot
    boss_step = moves.boss_step
    warp_hop = moves.warp_hop
    class_step = moves.class_step
    foot_step = moves.foot_step
    step = moves.step
    better_stand = moves.better_stand
    next_step = moves.next_step

    # sweep.py
    leaves = sweep.leaves
    gather = sweep.gather
    follow_on = sweep.follow_on
    sweep_to = sweep.sweep_to
    toward = sweep.toward
    asked_step = sweep.asked_step
    take_step = sweep.take_step
    quarry = sweep.quarry
