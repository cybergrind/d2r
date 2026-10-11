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
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import replace

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
    BLADES_A_CAST,
    CAMP_GAIN,
    CAMP_REACH,
    RUN_SPEED,
    WALK_LATENCY,
    Camp,
    camp,
    no_footing,
    way,
)
from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground, Level, Room, Target
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros.actuator import POINTER_DRIFT, Abort, Cancelled
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pickup import choose, unshunned
from inventory_tracking.macros.routines import (
    ACTING,
    CHARACTERS,
    DEAD,
    TOWN_NPCS,
    on_screen,
    press_skill,
    screen_fraction,
    settle,
    take_battle_weapons,
)
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach
from inventory_tracking.macros.skills import (
    BLADE_WARP,
    DEATH_MARK,
    ECHOING_STRIKE,
    ENGORGE,
    HEX_PURGE,
    SIGIL_LETHARGY,
    SWAP_WEAPONS,
    TELEPORT,
    skill_name,
)
from inventory_tracking.macros.teleport import (
    HOVER_SECONDS,
    MOVED,
    WALK_SECONDS,
    Way,
    ground_fraction,
    hop_toward,
    in_view,
    landed_from,
    moved,
    ready,
)
from inventory_tracking.macros.tour import Bounds, tour
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import DEFILER_CLASS, NO_OWNER, Monster, World
from inventory_tracking.native.layout import HIRELING_CLASS_ID, TILE_UNITS
from inventory_tracking.terror.tracker import BARRICADES, UNKILLABLE


# monstats.txt hydra1-3 (AI Hydra, no life of their own): the fire heads the Council casts stand as
# hostile monsters and never die. Worldstone Keep, 2026-10-10: the fight held the strike on them for
# 11 s, and the held strike kept the player from moving away.
HYDRAS = frozenset((351, 352, 353))
# monstats.txt MonType `vulture` (vulture1-5: combat/data/tables.json): in the air the blades pass
# through them. Far Oasis, take 20261010T224210Z-43 (user: "a lot of time hunting for birds that weren't
# on land"): 33 Undead Scavengers took 73 hits, 55 of them walking, attacking or struck (modes 2, 3, 4, 9:
# 1,797 frames) and 12 in modes 1 and 8 (8,807 frames), so those two are the bird in the air.
VULTURES = frozenset((110, 111, 112, 113, 608))
AIRBORNE = frozenset((1, 8))
# Engorge (skills.txt 379, cast on a corpse): heals the character's demons 30% of their life and more
# and lowers the damage they take for 125 + 75 per level frames (user, 2026-10-10 night: use it to
# buff and heal the demon). Cast under the held strike like Death Mark: when a demon is hurt, and now
# and then for the buff. Unconfirmed in the game: whether a corpse some other skill used still serves.
ENGORGE_SECONDS = 15.0  # between two Engorges for the buff
ENGORGE_HURT_SECONDS = 4.0  # between two while a demon is under ENGORGE_BELOW of its life
ENGORGE_BELOW = 0.7
ENGORGE_REACH = 20.0  # world units: a corpse further off is not looked for
ENGORGE_RETRY = 2.0  # seconds before another look when no corpse lay in reach
ENGORGE_LOOKS = 2  # corpses the pointer is put on for one cast at most
ITEM_UNIT_TYPE = 4
MONSTER_UNIT_TYPE = 1  # the unit type of a monster, alive or dead, in the record of what is under the pointer
# Hex: Purge (skills.txt 389, a buff of 3600 + 300 per level frames): the strikes do their damage
# through it (user, 2026-10-11: "without it there is no damage"), so attack mode casts it whenever the
# character's state does not show it. A cast the state does not show afterwards is tried once more,
# then only every HEX_DISTRUST seconds: the bit is read from the tables, not yet seen in the game.
HEX_RETRY = 3.0
HEX_DISTRUST = 60.0
HEX_TRIES = 2
# Death Mark makes one monster take more damage for 125 + 13 per level frames, and costs the strike
# about 0.9 s (101 marks in the takes of 2026-10-10: its own cast of 0.42 s, then the strike idle
# 0.37 s at the median before it was pressed again). So only a monster that outlives MARK_CASTS casts
# is marked, an elite or not, and the strike is pressed again under the mark's cast (`resume`). At
# the 45% a mark of level 20 adds (Param1 and Param2: 5 + 2 a level) it pays from about four casts.
MARK_CASTS = 4
RESUME_WAIT = 0.25  # seconds for the macro's own cast to show before the strike is pressed again
FIRST_STRIKE_SECONDS = 0.3  # the held strike this long with no cast seen yet: the mark and sigil wait no longer
SIGIL_SECONDS = 10.0  # between two sigils under the same monster
DEATH_MARK_SECONDS = 8.0  # between two Death Marks; the debuff lasts 125 + 13/level frames (skills.txt)
WALK_CLICKS = 2  # clicks for one walk to a firing spot
WALK_UNITS = 10.0  # a firing spot this near, over clear ground, is walked to, not teleported to (as NEAR_WARP)
FIGHT_SECONDS = 60.0  # one fight ends here at the latest; attack mode looks again right after
POLL = 0.1  # seconds between looks in attack mode while nothing is fought
FRAME = 0.04  # seconds between looks during a fight: one game frame, so a move of the player's is yielded to at once
DECIDE_SECONDS = 0.12  # between two askings of the policy while its monster lives (a decision costs up to 50 ms)
SIGHT = 30.0  # world units: hostiles further off are not part of the decision
# The sweep after a step asked for: the mode goes on stepping by itself, to a better place whenever
# there is one and toward the nearest hostile when nothing is in reach, until nothing hostile is within
# SWEEP_UNITS, the player moves by hand, FOLLOW_STEPS are taken or FOLLOW_SECONDS pass with no step.
FOLLOW_STEPS = 12
FOLLOW_SECONDS = 8.0  # since the press or the sweep's last step
FOLLOW_CHECK = 0.7  # seconds between two looks for a better place while a fight goes on
SWEEP_UNITS = 60.0  # hostiles this near are gone to
STAND_OFF = 14.0  # units short of the nearest hostile a stride toward it ends (the player engages at 12 to 14)
STRIDE = 16.0  # units of one stride: the click has to be in view
# A place a fight is left for, asked for or not, has to be worth this many times where the character
# stands (with nothing in reach: stance.CAMP_GAIN). The worth is counted with the monsters standing
# where they are, and in the game they come to the character. Black Marsh, 2026-10-11: at 00:50 two of
# six such steps were for 1.27 and 1.34 times; at 01:13, with 40 to 76 hostiles about, steps of 9 to 25
# units were taken for 1.29 to 1.48 times with 6 to 10 hostiles in reach, back and forth.
SWEEP_GAIN = 2.0
# A walk of the mode's own is one click and a short wait: `walk_to` (two clicks, 1.5 s each, a
# second to settle) took 4 s to say "the character did not move", twice in a row at 01:13:48 and at
# 01:14:36 for the same place, with nothing cast meanwhile (user: "auto-attacking has stopped"). A
# place a step failed for is left alone for SHUN_SECONDS, and two failures in a row end the sweep.
STEP_WALK_SECONDS = 0.7
# A character in a walking or running mode that has not moved for this long is not going anywhere, and
# the mode stops waiting for it. Durance of Hate 2, 03:09:13 on 2026-10-11 (user: "a strange movement
# lag, when we were stuck"): the character stood at (17816, 6818) in mode 3 (run) for 22 s after a walk
# of the sweep's that got 5 units of its 23, the Defiler and the bound demon standing on it and in its
# way; three weapon swaps did nothing, the life went up as ever and monsters around died. The mode
# yields to a character on the move, so it cast nothing and logged nothing for those 22 s.
RUN_IN_PLACE = 1.5
WAIT_LOG_SECONDS = 3.0  # between log lines on what attack mode is waiting for
HOVER_UNITS = 12.0  # a monster named as under the pointer stands this near the ground aimed at, or is not there
SHUN_UNITS = 6.0
SHUN_SECONDS = 10.0
STEP_FAILURES = 2
# The seek step's order (user, 2026-10-11: "exploring somewhat random in different directions"; a
# Terror Zone's completion is the rooms seen times the kills, terror/chance.py). The unexplored room
# is the first stop of a tour that shows every unexplored room (macros/tour.py; the nearest room by
# the way, with a turn counted as some tiles more, left strips behind and went back for them). A
# remembered monster that is not where it was seen (within VANISH_UNITS of the character and not
# among the live ones) is not gone to again.
# A monster the strikes do nothing to is left alone (user, 2026-10-11: Far Oasis, "a lot of time
# hunting for birds that weren't on land, effectively immortal"; like the Council's hydras, but by
# what is seen, not by type: a bird in the air, something burrowed, an immune). One that was the
# line's monster for UNTOUCHED_CASTS casts and shows the life it had is no hostile for
# UNTOUCHABLE_SECONDS: not fought, not swept or sought toward. Then it is tried again (the bird lands).
UNTOUCHED_CASTS = 4
UNTOUCHABLE_SECONDS = 20.0
ROOM_UNITS = 40.0  # a known hostile this much further than the nearest unexplored room still goes first
VANISH_UNITS = 25.0
# A stride is a jump when the character can make one without a weapon swap (user, 2026-10-11): Blade
# Warp first (skills.txt 390: a thrown blade the character is teleported to, any melee weapon, a
# casting delay of 20 frames; missiles.txt 707 `bladewarp`: Vel 36 for 20 frames, half again the
# strike's blades, so some 33 units), else Teleport when it is in hand or a skill of the character's own
# (Enigma). A chain of teleport steps covered 26 units in 0.8 s in the Marsh run; the walk takes 1.6.
# Black Marsh, 01:26 on 2026-10-11, the first run with them: 31 Blade Warps of 9.5 to 24 units all landed
# on the pointer's ground (off by 2.8 at most, 1.0 at the median), 0.35 s and 45 units a second after
# the key (0.79 s at the median), the first cast 0.17 s after the landing; 8 Teleports from the staff in
# hand landed 0.31 s after the key. Blade Warp stays first (user): it spends no charges.
JUMP_REACH = 26.0  # units of a jump: in view, and within the blade's range
JUMP_LEAST = 8.0  # a stride shorter than this is walked
WARP_DELAY = 0.8  # seconds between two Blade Warps (the skill's casting delay)
JUMP_SECONDS = 1.5  # for the character to be seen somewhere else after the key
JUMP_DISTRUST = 30.0  # seconds a way of jumping that did not move the character is left alone
ENGAGE_UNITS = SIGHT  # hostiles this near: the pickup request with nothing to pick up is a step toward them, not a seek
SLICE = 0.01  # seconds between looks at the left mouse button while the mode waits or fights
TOUGH_POINTS = 40_000.0  # life points in reach from which a pack is worth the main weapons
ELITE_LIFE = 2.0  # a unique's or champion's life in Hell, in its type's points (the tables hold the plain monster's)
MAIN_AFTER = 1.0  # seconds after a step before the main weapons are swapped in for a fight
SWAP_RETRY_SECONDS = 5.0  # after a swap to the main weapons that did not come
INPUT_SECONDS = 1.0  # Echoing Strike on no input for this long (another skill selected) before it is a stopped fight
MISSES_IN_A_ROW = 5  # fights that stopped one after another before attack mode gives up
IDLE_LOG_SECONDS = 3.0  # between log lines on what attack mode sees while nothing is in reach

Point = tuple[float, float]
Remembered = Callable[[int], list[tuple[int, float, float, bool]]]  # area -> (unit id, x, y, leader)


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


def label(monster: Monster) -> str:
    return f'{"the elite" if monster.leader else "the monster"} {monster.txt_id} ({monster.unit_id})'


def life(monster: Monster | None) -> str:
    if monster is None:
        return 'gone'
    return f'{monster.life}/{monster.max_life}' if monster.max_life else 'life unknown'


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
        self.sigiled: dict[int, float] = {}  # unit id -> clock time of the last sigil under it
        self.policy: Policy = policy or LinePolicy()  # where to cast (combat/policy.py)
        self.score = LiveScore()  # the last minute of attack mode: damage and kills (combat/score.py)
        self.marked_at = -math.inf  # clock time of the last Death Mark
        self.engorged_at = -math.inf  # clock time of the last Engorge (or of the last look for a corpse)
        self.purged_at = -math.inf  # clock time of the last Hex: Purge cast
        self.warped_at = -math.inf  # clock time of the last Blade Warp
        self.jump_failed: dict[int, float] = {}  # skill -> clock time a jump by it last moved nothing
        self.shunned: list[tuple[Point, float]] = []  # places a step failed for, and when
        self.step_fails = 0  # steps that failed one after another
        self.stepped_at = -math.inf  # clock time of the last step the mode took
        self.route: tuple[int, list[Bounds]] = (0, [])  # (level, the rooms the explore steps go to stand in, in order)
        self.vanished: set[int] = set()  # remembered monsters that were not where they were seen
        self.tested: dict[int, tuple[int, int]] = {}  # unit -> (casts with the line through it, its life then)
        self.untouchable: dict[int, float] = {}  # unit -> clock time until which it is left alone
        self.purges_unseen = 0  # casts of it in a row that the character's state did not show after
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
        self.stepping: Camp | None = None  # the step the fight stopped for
        self.follow = 0  # steps the mode may still take for the last press (FOLLOW_STEPS)
        self.follow_until = -math.inf
        self.follow_checked = -math.inf  # clock time of the sweep's last look for a better place
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
            walk_to(run, goal, player, rect[2] / rect[3], name)
        elif self.no_charges(run):
            self.afoot(run, ground, player, rect, goal, name, key_names)
        else:
            hop_toward(run, target, player, rect, key_names)

    @staticmethod
    def no_charges(run: Run) -> bool:
        staff = run.teleport() if run.teleport is not None else None
        return staff is not None and staff.charges == 0

    def afoot(self, run: Run, ground: Ground, player, rect, goal: Point, name: str, key_names) -> None:
        """A seek step with the staff's charges gone (Frigid Highlands, 02:55 on 2026-10-11: 69 charges
        went in seven minutes and ten presses then stopped with "no charges left"): a Blade Warp of
        up to JUMP_REACH straight toward `goal` over a clear line, else one click's walk of STRIDE."""
        world = run.world()
        here = (player.x, player.y)
        away = math.dist(here, goal)
        aspect = rect[2] / rect[3]
        barred = no_footing(ground, world.doors)

        def at(stride: float) -> Point:
            return (here[0] + (goal[0] - here[0]) * stride / away, here[1] + (goal[1] - here[1]) * stride / away)

        def footed(spot: Point) -> bool:
            return in_view(ground_fraction(player, spot[0], spot[1], aspect)) and (
                barred is None
                or not any(barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            )

        if away >= JUMP_LEAST and self.jump_by(run, world) == BLADE_WARP:
            longest = min(away, JUMP_REACH)
            for stride in (longest, longest * 0.75, longest * 0.5):
                spot = at(stride)
                if stride >= JUMP_LEAST and footed(spot) and clear_shot(ground, here, spot, world.doors):
                    run.say(f'Blade Warp toward {name}: the Teleport staff has no charges left')
                    self.jump(
                        run, Camp(spot, 0.0, 0.0, 0.5, stride, hop=True, casts=BLADE_WARP), player, aspect, key_names
                    )
                    return
        stride = min(away, STRIDE)
        if stride >= MOVED and footed(at(stride)) and way(barred, here, at(stride)):
            run.say(f'Walking toward {name}: the Teleport staff has no charges left')
            step_walk(run, at(stride), player, aspect, attackable(world))
            return
        raise Abort(f'the Teleport staff has no charges left, and no Blade Warp or walk leads toward {name}')

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
        self.follow, self.follow_until = FOLLOW_STEPS, run.clock() + FOLLOW_SECONDS
        self.step_fails = 0
        LOG.info('Macro: step asked with %d hostiles near, from (%.1f, %.1f): the sweep takes it', len(near), *here)

    def better_stand(
        self, world: World, foes: list[Monster], ground: Ground, aspect: float, gain: float = CAMP_GAIN
    ) -> Camp | None:
        """The place worth going to from where the character stands (combat/stance.py `camp`), or
        None: on foot, and in view, as the walk is one click on it."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT + CAMP_REACH]
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        seen = observe(player, near, companions, ground, world.doors)
        policy = self.policy if isinstance(self.policy, LinePolicy) else LinePolicy()
        return camp(
            seen,
            policy,
            no_footing(ground, world.doors),
            shown=lambda spot: (
                in_view(ground_fraction(player, spot[0], spot[1], aspect))
                and not any(math.dist(spot, left) < SHUN_UNITS for left, _ in self.shunned)
            ),
            gain=gain,
        )

    def follow_on(self, run: Run, world: World, foes: list[Monster], ground: Ground, key_names) -> bool:
        """The sweep with nothing in reach: the next place if one is worth it, else a stride toward
        the nearest hostile within SWEEP_UNITS, else (a wall between) the seek step's own move onto a
        firing spot at it. Whether a step was taken."""
        player = world.player
        rect = run.actuator.keys.focused_window_rect()
        if run.clock() > self.follow_until or player is None or rect is None:
            self.follow = 0
            return False
        self.shunned = [(spot, at) for spot, at in self.shunned if run.clock() - at < SHUN_SECONDS]
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SWEEP_UNITS]
        if not near:
            return False
        aspect = rect[2] / rect[3]
        found = self.better_stand(world, near, ground, aspect)
        stride = None if found is not None else self.toward(run, world, near, ground, aspect)
        LOG.info(
            'Macro: sweeping with %d hostiles near and none in reach, from (%.1f, %.1f): %s',
            len(near), *here,
            stand_line(found) if stride is None else stride_line(stride),
        )  # fmt: skip
        found = found or stride
        if found is not None:
            self.sweep_to(run, found)
            self.take_step(run, aspect, key_names, ground)
            return True
        level = self.known_level(player)
        if level is None:
            self.follow = 0
            return False
        # A wall between: onto a firing spot at the nearest, as the seek step goes to an elite, with
        # the pointer held as a step holds it (the mode itself aims once and casts at once).
        nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
        self.follow -= 1
        self.follow_until = run.clock() + FOLLOW_SECONDS
        drift, steady = run.actuator.drift, run.actuator.steady
        run.actuator.drift, run.actuator.steady = POINTER_DRIFT, True
        try:
            self.go(run, level, ground, player, rect, (nearest.x, nearest.y), label(nearest), world.doors, key_names)
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            LOG.info('Macro: the sweep ends: no way to %s (%s)', label(nearest), stop)
            self.follow = 0
            return False
        finally:
            run.actuator.drift, run.actuator.steady = drift, steady
        self.follow_checked = run.clock()
        return True

    def sweep_to(self, run: Run, found: Camp) -> None:
        """One of the sweep's own steps is to be taken: counted, and the sweep goes on from it."""
        self.follow -= 1
        self.follow_until = run.clock() + FOLLOW_SECONDS
        self.stepping = found

    def toward(self, run: Run, world: World, near: list[Monster], ground: Ground, aspect: float) -> Camp | None:
        """A stride toward the nearest hostile, to end STAND_OFF short of it: a jump of up to
        JUMP_REACH when the character can make one (`jump_by`), else a straight walk of STRIDE; onto
        footing, in view. None when there is none (a wall between: the firing spot's to find)."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
        mob = (nearest.x, nearest.y)
        away = math.dist(here, mob)
        barred = no_footing(ground, world.doors)

        def at(stride: float) -> Point:
            return (here[0] + (mob[0] - here[0]) * stride / away, here[1] + (mob[1] - here[1]) * stride / away)

        if any(math.dist(at(min(away - STAND_OFF, STRIDE)), left) < SHUN_UNITS for left, _ in self.shunned):
            return None
        skill = self.jump_by(run, world)
        if skill is not None and away - STAND_OFF >= JUMP_LEAST:
            longest = min(away - STAND_OFF, JUMP_REACH)
            for stride in (longest, longest * 0.75, longest * 0.5):
                spot = at(stride)
                if stride < JUMP_LEAST or not in_view(ground_fraction(player, spot[0], spot[1], aspect)):
                    continue
                if barred is not None and any(
                    barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                ):
                    continue
                if skill == BLADE_WARP and not clear_shot(ground, here, spot, world.doors):
                    continue  # the blade flies there: no wall in its way
                return Camp(spot, 0.0, 0.0, 0.5, stride, hop=True, casts=skill)
        stride = min(away - STAND_OFF, STRIDE)
        if stride < MOVED:
            return None
        spot = at(stride)
        if not in_view(ground_fraction(player, spot[0], spot[1], aspect)):
            return None
        if not way(barred, here, spot):
            return None
        if stride < STRIDE / 2 and not clear_shot(ground, spot, mob, world.doors):
            return None  # a few units up to a wall it stands behind: the firing spot's to find
        return Camp(spot, 0.0, 0.0, WALK_LATENCY + stride / RUN_SPEED, stride)

    def jump_by(self, run: Run, world: World, *, warp: bool = True) -> int | None:
        """The skill a stride can be jumped by now, without a weapon swap: Blade Warp when it is in a
        slot and its casting delay is over, else Teleport from the staff in hand or as the
        character's own skill. None: the stride is walked."""

        def trusted(skill: int) -> bool:
            return run.clock() - self.jump_failed.get(skill, -math.inf) > JUMP_DISTRUST

        if warp and BLADE_WARP in world.slots and trusted(BLADE_WARP) and run.clock() - self.warped_at >= WARP_DELAY:
            return BLADE_WARP
        if TELEPORT in world.slots and trusted(TELEPORT):
            staff = run.teleport() if run.teleport is not None else None
            if staff is None or (staff.in_hand and staff.charges > 0):
                return TELEPORT
        return None

    def jump(self, run: Run, found: Camp, player, aspect: float, key_names) -> None:
        """One jump onto `found.spot` by the skill it names: the pointer on its ground, the key, and
        the character seen somewhere else. What it was aimed at and where it landed goes to the log."""
        skill = found.casts
        try:
            run.keys.update(key_names(run.world(), (skill,)))
            # No wait of its own for the cast in flight: `press_skill` waits for the character (with one,
            # 0.39 s went by between the decision and the key at the median, 2026-10-11).
            run.actuator.aim(*ground_fraction(player, found.spot[0], found.spot[1], aspect), scatter=(4, 3))
            pressed = run.clock()
            press_skill(run, skill)
            if skill == BLADE_WARP:
                self.warped_at = run.clock()
            spot = found.spot
            if run.seen(lambda w: w.player is not None and landed_from(w.player, player, spot), JUMP_SECONDS) is None:
                raise Abort(f'{skill_name(skill)}: the character did not move')
        except Abort:
            self.jump_failed[skill] = run.clock()
            raise
        landed = run.world().player
        if landed is not None:
            LOG.info(
                'Macro: %s aimed at (%.1f, %.1f), %.1f from (%.1f, %.1f); landed at (%.1f, %.1f), off by %.1f, '
                '%.2fs after the key',
                skill_name(skill), *found.spot, found.walk, player.x, player.y, landed.x, landed.y,
                math.dist((landed.x, landed.y), found.spot), run.clock() - pressed,
            )  # fmt: skip

    def asked_step(self, run: Run, world: World, foes: list[Monster], reachable, ground, aspect) -> Camp | None:
        """The pickup request inside a fight: the step to take now, if one is worth it. The press goes
        on waiting for the fight's end only when there is something to pick up."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        if run.loot is not None and choose(unshunned(run.loot(), run.clock()), here) is None:
            self.after_fight.clear()  # nothing to pick up: no pickup step, and so no seek step, after the fight
            if self.unwait is not None:
                self.unwait()
        self.shunned = [(spot, at) for spot, at in self.shunned if run.clock() - at < SHUN_SECONDS]
        found = self.better_stand(world, foes, ground, aspect, SWEEP_GAIN)
        self.follow, self.follow_until = FOLLOW_STEPS, run.clock() + FOLLOW_SECONDS
        self.step_fails = 0
        LOG.info(
            'Macro: step asked in the fight with %d of %d hostiles in reach, from (%.1f, %.1f): %s; pickup after: %s',
            len(reachable), len(foes), *here, stand_line(found), self.after_fight.is_set(),
        )  # fmt: skip
        if found is None:
            run.say(f'Standing well: no better place within {CAMP_REACH:.0f}')
        return found

    def take_step(self, run: Run, aspect: float, key_names=None, ground: Ground | None = None) -> None:
        """Go to the place the fight stopped for, or the stride's end: a jump when the character can
        make one over the distance (`jump_by`; a Blade Warp needs a clear line), else one click's
        walk. The player's own move comes first: a press of theirs, a held key or a character
        already going drops the step. A step that fails leaves its place alone for a while."""
        found, self.stepping = self.stepping, None
        world = run.world()
        player = world.player
        if found is None or player is None:
            return
        why = 'a move was asked for' if self.move is not None else self.moving(run, world)
        if why is not None:
            LOG.info('Macro: the step is dropped (%s)', why)
            self.follow = 0
            return
        here = (player.x, player.y)
        if not found.hop and key_names is not None and ground is not None and math.dist(here, found.spot) >= JUMP_LEAST:
            # Walking by a click through a pack is what failed (the click meets a monster): jumped instead.
            skill = self.jump_by(run, world)
            if skill == BLADE_WARP and not clear_shot(ground, here, found.spot, world.doors):
                skill = self.jump_by(run, world, warp=False)
            if skill is not None:
                found = replace(found, hop=True, casts=skill, walk=math.dist(here, found.spot))
        try:
            if found.hop and key_names is not None:
                self.jump(run, found, player, aspect, key_names)
            else:
                step_walk(run, found.spot, player, aspect, attackable(world))
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            self.step_fails += 1
            if not found.hop:
                self.shunned.append((found.spot, run.clock()))
            if self.step_fails >= STEP_FAILURES:
                self.follow = 0
            run.say(f'No step: {stop}')
            LOG.info('Macro: the step to (%.1f, %.1f) failed (%s), %d in a row', *found.spot, stop, self.step_fails)
            return
        self.step_fails = 0
        self.step_asked_at = self.follow_checked = self.stepped_at = run.clock()

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
            if self.purge_due(run, world):
                try:
                    self.purge(run, world, key_names)
                    run.pause('key')
                except Abort as stop:
                    if run.cancelled.is_set():
                        raise
                    LOG.info('Macro: no Hex: Purge (%s)', stop)
                    self.purged_at = run.clock()
                continue
            level = self.known_level(player)
            ground = Ground(level.ground if level is not None else ())
            here = (player.x, player.y)
            foes = self.foes(world, run.clock())
            if not any(in_reach(ground, here, (m.x, m.y), REACH, world.doors) for m in foes):
                self.step_aside()
                if self.follow and foes and self.follow_on(run, world, foes, ground, key_names):
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
                tough = self.tough(world, reachable)
                settled = run.clock() - entered >= MAIN_AFTER
                held = self.main_weapons(run, world, key_names, swap=settled and tough)
                pause = entered + MAIN_AFTER if tough and not held else None
                self.fight(run, ground, rect[2] / rect[3], key_names, until=pause)
                misses = 0
                self.take_step(run, rect[2] / rect[3], key_names, ground)  # the step the fight stopped for, if any
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
        origin = Way(Target(level.area, level.rooms, here, 'here', 'explore', False, level.ground), Viewport.of(rect))
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
        if self.no_charges(run):
            goal = ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS)
            self.afoot(run, Ground(level.ground), player, rect, goal, 'an unexplored room', key_names)
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
            self.follow = 0  # the player moves by hand: no step of the mode's own after it
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
        a focal point the window lets the pointer reach."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT]
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        seen = observe(
            player, near, companions, ground, world.doors, aimable=lambda focal: view.reachable_focal(here, focal)
        )
        found = aim_choice(self.policy, seen, [m.unit_id for m in reachable])
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
                    if self.tough(world, reachable):
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
                if self.follow and self.follow_checked + FOLLOW_CHECK <= run.clock() <= self.follow_until:
                    # The sweep: a better place is gone to without a press.
                    self.follow_checked = run.clock()
                    better = self.better_stand(world, foes, ground, aspect, SWEEP_GAIN)
                    if better is not None:
                        LOG.info(
                            'Macro: sweeping in the fight with %d of %d hostiles in reach, from (%.1f, %.1f): %s',
                            len(reachable), len(foes), *here, stand_line(better),
                        )  # fmt: skip
                        self.sweep_to(run, better)
                        ended = 'Stepping to a better place'
                        break
                if self.step_asked_at is not None and cast.casts:
                    LOG.info('Macro: first cast %.2fs after the step', run.clock() - self.step_asked_at)
                    self.step_asked_at = None
                if choice is None or choice.unit not in alive or run.clock() - decided_at >= DECIDE_SECONDS:
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
                if struck and self.purge_due(run, world):
                    self.casting = True
                    self.purge(run, world, key_names)
                    cast.excuse(run.clock())
                    self.resume(run, again)
                if struck and run.clock() - self.marked_at > DEATH_MARK_SECONDS and DEATH_MARK in world.slots:
                    strongest = max(reachable, key=lambda m: (m.leader, m.max_life, -math.dist(here, (m.x, m.y))))
                    if self.worth_a_mark(world, strongest):
                        self.casting = True  # the mark's own cast swallows a click as a strike does
                        self.death_mark(run, strongest, aspect, key_names)
                        aim.forget()
                        cast.excuse(run.clock())  # the mark's own cast is no missing strike
                        self.resume(run, again)
                if struck and prey.leader and run.clock() - self.sigiled.get(prey.unit_id, -math.inf) > SIGIL_SECONDS:
                    self.casting = True
                    self.sigil(run, world, prey, aspect, key_names)
                    aim.forget()
                    cast.excuse(run.clock())
                    self.resume(run, again)
                if struck and ENGORGE in world.slots and self.engorge_due(run, world):
                    self.casting = True
                    if self.engorge(run, world, aspect, key_names):
                        aim.forget()
                        cast.excuse(run.clock())
                        self.resume(run, again)
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

    def sigil(self, run: Run, world: World, prey: Monster, aspect: float, key_names) -> None:
        """Sigil: Lethargy on the ground under an elite (slows it, lowers its defence)."""
        assert world.player is not None
        run.keys.update(key_names(world, (SIGIL_LETHARGY,)))
        where = ground_fraction(world.player, prey.x, prey.y, aspect)
        if not on_screen(where):
            # Off the screen (the blades reach further than it shows): no sigil now, asked again in a second.
            self.sigiled[prey.unit_id] = run.clock() - SIGIL_SECONDS + 1.0
            return
        run.actuator.aim(*where, scatter=(4, 3))
        press_skill(run, SIGIL_LETHARGY)
        self.sigiled[prey.unit_id] = run.clock()

    def engorge_due(self, run: Run, world: World) -> bool:
        """Whether Engorge is worth a cast now: a demon of the character's is out, and it is hurt or
        the last cast is ENGORGE_SECONDS old."""
        player = world.player
        if run.corpses is None or player is None:
            return False
        demons = [
            m
            for m in world.monsters
            if (m.ally or m.owner == player.unit_id or m.txt_id == DEFILER_CLASS) and m.txt_id != HIRELING_CLASS_ID
        ]
        if not demons:
            return False
        hurt = any(m.max_life and m.life < ENGORGE_BELOW * m.max_life for m in demons)
        return run.clock() - self.engorged_at > (ENGORGE_HURT_SECONDS if hurt else ENGORGE_SECONDS)

    def engorge(self, run: Run, world: World, aspect: float, key_names) -> bool:
        """Engorge on the nearest corpse in view within ENGORGE_REACH; whether it was cast."""
        player = world.player
        assert player is not None
        assert run.corpses is not None
        here = (player.x, player.y)
        near = [
            corpse
            for corpse in run.corpses()
            if math.dist(here, corpse[1:]) <= ENGORGE_REACH and on_screen(ground_fraction(player, *corpse[1:], aspect))
        ]
        if not near:
            self.engorged_at = run.clock() - ENGORGE_HURT_SECONDS + ENGORGE_RETRY
            return False
        run.keys.update(key_names(world, (ENGORGE,)))
        alive = {m.unit_id for m in world.monsters}
        # The nearest corpse the pointer really has under it: of 12 casts on 2026-10-10 the record
        # named a monster under the pointer 11 times and an item's label once, and whether that monster
        # was the corpse was not known (a live one stands on a corpse often: the fight is there).
        for unit, x, y in sorted(near, key=lambda corpse: math.dist(here, corpse[1:]))[:ENGORGE_LOOKS]:
            run.actuator.aim(*ground_fraction(player, x, y, aspect), scatter=(3, 3))
            over = None
            if run.hovered is not None:
                run.pace.sleep(HOVER_SECONDS)
                over = run.hovered()
                # Not cast with a live monster or an item's label under the pointer; with nothing
                # there it is (whether the record shows a corpse at all is not known yet).
                if over is not None and (
                    over[0] == ITEM_UNIT_TYPE or (over[0] == MONSTER_UNIT_TYPE and over[1] in alive)
                ):
                    LOG.info(
                        'Macro: no Engorge at (%.1f, %.1f): under the pointer %s, not the corpse %d', x, y, over, unit
                    )
                    continue
            press_skill(run, ENGORGE)
            self.engorged_at = run.clock()
            LOG.info(
                'Macro: Engorge on the corpse %d at (%.1f, %.1f), %.1f away; under the pointer %s',
                unit, x, y, math.dist(here, (x, y)), over,
            )  # fmt: skip
            return True
        self.engorged_at = run.clock() - ENGORGE_HURT_SECONDS + ENGORGE_RETRY
        return True  # the pointer was moved: the strike's aim is put back

    def resume(self, run: Run, again: Callable[[], None] | None) -> None:
        """The held strike pressed again under a cast of the macro's own (a mark, a sigil, Engorge,
        Hex: Purge), so the game has it waiting when that cast ends: left alone it stood idle 0.37 s
        at the median after a Death Mark before the hold's own press-again came."""
        if again is None:
            return
        run.seen(lambda w: w.player is not None and w.player.mode in ACTING, RESUME_WAIT)
        again()

    def worth_a_mark(self, world: World, target: Monster) -> bool:
        """Whether `target` outlives MARK_CASTS casts on its line: else the mark costs more casting
        than the damage it adds."""
        if world.player is None:
            return False
        policy = self.policy if isinstance(self.policy, LinePolicy) else LinePolicy()
        foe = observe(world.player, [target], ()).foes[target.unit_id]
        full = foe.left * (ELITE_LIFE if foe.elite else 1.0)
        return full > MARK_CASTS * BLADES_A_CAST * policy.damage_of(foe.txt)

    def purge_due(self, run: Run, world: World) -> bool:
        """Whether Hex: Purge is to be cast now: the character's state reads without it."""
        player = world.player
        if player is None or HEX_PURGE not in world.slots:
            return False
        if player.hex_purge is not False:
            self.purges_unseen = 0 if player.hex_purge else self.purges_unseen
            return False
        wait = HEX_RETRY if self.purges_unseen < HEX_TRIES else HEX_DISTRUST
        return run.clock() - self.purged_at > wait

    def purge(self, run: Run, world: World, key_names) -> None:
        """Hex: Purge, a cast on the character itself."""
        if self.purges_unseen == HEX_TRIES:
            LOG.warning('Macro: Hex: Purge cast %d times and the state does not show it', HEX_TRIES)
        run.keys.update(key_names(world, (HEX_PURGE,)))
        press_skill(run, HEX_PURGE)
        self.purged_at = run.clock()
        self.purges_unseen += 1

    def death_mark(self, run: Run, target: Monster, aspect: float, key_names) -> None:
        """Death Mark on `target`: the pointer on its body, then the key (Quick Cast)."""
        world = run.world()
        if world.player is None:
            raise Abort('not in a game')
        run.keys.update(key_names(world, (DEATH_MARK,)))
        point = screen_fraction(world.player, target.x, target.y, aspect)
        if not on_screen(point):
            return
        run.actuator.aim(*point, scatter=(3, 3))
        if all(m.unit_id != target.unit_id for m in run.world().monsters):
            return  # it died under the strike while the pointer went over: no mark on a corpse
        press_skill(run, DEATH_MARK)
        self.marked_at = run.clock()
        run.say(f'Death Mark on {label(target)}, {life(target)}')


def stride_line(stride: Camp) -> str:
    by = skill_name(stride.casts) if stride.hop else 'a walk'
    return f'a stride of {stride.walk:.0f} toward the nearest, by {by}'


def stand_line(found: Camp | None) -> str:
    if found is None:
        return 'no better place'
    return (
        f'a place at ({found.spot[0]:.1f}, {found.spot[1]:.1f}), a walk of {found.walk:.0f} ({found.seconds:.1f}s), '
        f'worth {found.worth:.0f} against {found.here:.0f} here, {found.casts or "more than the horizon's"} casts'
    )


def attackable(world: World) -> list[Monster]:
    """The live monsters a left click attacks: not the character's own and not an ally."""
    return [m for m in world.monsters if m.owner == NO_OWNER and not m.ally and (m.x or m.y)]


def step_walk(run: Run, goal, player, aspect: float, alive: list[Monster]) -> None:
    """One click on the ground at `goal` for a step of the mode's own, and the character seen going
    within STEP_WALK_SECONDS. Not clicked with one of `alive` (the monsters a click attacks) under the
    pointer: the left button attacks it, where it stands or after a chase. The unit the game names as
    under the pointer counts only within HOVER_UNITS of the goal: Frigid Highlands, 03:00 on
    2026-10-11, five walks in three seconds were refused for "a monster under the pointer", the
    first two aimed 2 and 3 units from the Defiler and the mercenary, the next ones with nothing
    alive within 8 units of the aim (the name of the last unit hovered seems to stay)."""
    where = ground_fraction(player, goal[0], goal[1], aspect)
    if not in_view(where):
        raise Abort('the place is not in view')
    run.say(f'Walking {math.dist((player.x, player.y), goal):.0f} toward a better place')
    settle(run, limit=0.5)
    run.actuator.aim(*where, scatter=(4, 3))
    if run.hovered is not None:
        run.pace.sleep(HOVER_SECONDS)
        over = run.hovered()
        if over is not None and over[0] == MONSTER_UNIT_TYPE:
            under = [m for m in alive if m.unit_id == over[1] and math.dist((m.x, m.y), goal) <= HOVER_UNITS]
            if under:
                raise Abort(f'{label(under[0])} is under the pointer there')
    run.actuator.click()
    if run.seen(lambda w: w.player is not None and moved(w.player, player), STEP_WALK_SECONDS) is None:
        raise Abort('the character did not move')


def walk_to(run: Run, goal, player, aspect: float, name: str) -> None:
    """A click on the ground at `goal` (world units): the character walks there."""
    where = ground_fraction(player, goal[0], goal[1], aspect)
    if not in_view(where):
        raise Abort(f'the spot near {name} is not in view')
    run.say(f'Walking {math.dist((player.x, player.y), goal):.0f} toward {name}')
    # A click made while attack mode's last cast ends is swallowed (host, 19:40 on 2026-10-10: "Walking 7",
    # "the character did not move"): the character is waited free first and the click made twice at most.
    for _ in range(WALK_CLICKS):
        settle(run)
        run.actuator.aim(*where, scatter=(4, 3))
        run.actuator.click()
        if run.seen(lambda w: w.player is not None and moved(w.player, player), WALK_SECONDS) is not None:
            return
    raise Abort('the character did not move')
