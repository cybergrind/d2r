"""The production macro played in the arena: presses in, a `Result` out (framework-plan.md, Task 1.6).

`play` builds an `Arena` (game.py) from a scene and gives the presses to the production
`MacroRunner` at their times on the arena's clock. The runner is the real one: its `request`, the
toggle, the queue of waiting presses, the threads it starts, what follows a run that ended. Only its
`execute` is the arena's (`Play.execute`), which is `MacroRunner._execute` for the attack mode toggle
and the pickup step with the arena in place of the process, the window and the memory, as
scenarios/battle/replay.py `Replay.execute` has the take there; `Hunter.attack_mode`, `pick_up`,
`open_near` and `Hunter.step` run as they are.

Why the runner and not the routines called directly (scenarios/loop/helpers.py `attack_mode`): what a
press does while a run works is the runner's (a pickup press waits for the fight and the mode pauses
itself for it, the mode resumes after a step, the sweep asks for a pickup step of its own), and a
second copy of those rules here would be played instead of them.

Nothing in a play looks at wall time, and one thing moves the game at a time:

- the runner reads `time.monotonic()` for how long a press may wait (`EXPIRES`) and for a bounce
  (`THROTTLE`). For the play its `time` is `ArenaTime`, the arena's clock, and its card wait
  (`CARD_SECONDS`, a wait on the wall's clock that `close` ends) is none: the card is not the game's
  time. The queue's clock is set to the same. So a press that waited too long is dropped by the
  arena's seconds, as the real one is by the wall's, whatever the machine's load. The module's `time`
  and `CARD_SECONDS` are put back after the play;
- a run works on the runner's own thread, and the game's clock moves only in the thread that sleeps
  on it: a run's, or with no run working this one's, a tick at a time. A press whose time comes
  during a run is made from within that run's sleep (as `Replay.sleep` makes them, and as the
  service's hotkey thread would between two of the run's steps); one that comes with nothing running
  is made here, and the thread it starts is waited for. The wait is on the thread, never on a time: its
  wall limit (WALL_LIMIT) only turns a play that hangs into an error.

The production code keeps a few memories for a process's life, stamped with its clock (the drops and
chests a step gave up on, where a hop failed); `fresh` empties them before a play, as a new arena's
clock starts at zero and they would hide a drop from the next play.

What of the runner is not played: `_execute` itself (the capture lock, the attach, `FocusTracker`,
`X11Keyboard`, `GameMemory`, the character's key file and the Show Items key, the latency marks, the
research hooks), its teleport, seek and macro branches, `poll` and the journey, and the staff check.
The keys are the fakes' (macros/fakes.py KEYS), given for a skill only when it is on a skill key, as
`skills.skill_keys` asks.
"""

import random
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from inventory_tracking.config import HealingConfig
from inventory_tracking.input.compositor import STEP_KEYS
from inventory_tracking.levels.model import Level, Room
from inventory_tracking.macros import opening, pickup, runner as runner_module, teleport
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import Build
from inventory_tracking.macros.hunt import Hunter, threat
from inventory_tracking.macros.latency import Trace
from inventory_tracking.macros.opening import open_near
from inventory_tracking.macros.pickup import pick_up
from inventory_tracking.macros.runner import ATTACK, PICKUP, TELEPORT, MacroRunner
from inventory_tracking.macros.skills import ACTIONS, NAMES
from inventory_tracking.macros.world import World
from tests.inventory_tracking.macros.fakes import KEYS, warlock
from tests.inventory_tracking.scenarios.arena.game import EDGE, Arena
from tests.inventory_tracking.scenarios.arena.result import Result
from tests.inventory_tracking.scenarios.arena.scene import Scene


WALL_LIMIT = 120.0  # wall seconds a run's thread is waited for before the play is called hung (an error, no result)


@dataclass
class Press:
    """A press of a macro key: `routine` (the runner's names: ATTACK, PICKUP) at `at` seconds on the arena's clock."""

    at: float
    routine: str


class ArenaTime:
    """What runner.py reads of `time`, for a play: the arena's clock for `monotonic`, and a `sleep`
    that takes no time."""

    perf_counter = staticmethod(time.perf_counter)

    def __init__(self, arena: Arena) -> None:
        self.arena = arena

    def monotonic(self) -> float:
        return self.arena.clock.now

    def sleep(self, seconds: float) -> None:
        pass


def fresh() -> None:
    """The production code's memories of a process's life, emptied: each is stamped with the clock
    of the play that made it (pickup.py SHUNNED and STOPPED, opening.py SHUNNED, teleport.py FAR_FAILED,
    LANDED and LANDING)."""
    for memory in (pickup.SHUNNED, pickup.STOPPED, opening.SHUNNED, teleport.FAR_FAILED):
        memory.clear()
    teleport.LANDED.clear()
    teleport.LANDING.clear()


def key_names(world: World, skills: Sequence[int] | None = None) -> dict[int, str]:
    """The key of each skill asked for, as `MacroRunner._execute` gives them from the character's key
    file: here the fakes' keys, and as there no key for a skill that is on no skill key. Asked with
    the skills always: the routines played (attack mode, the pickup step) name theirs, and the macro
    request, which asks for the prebuff's without naming them, is not played: nor is the route's leave,
    which asks the same way (routines.py `character_keys`): the arena has no game to leave, and says so
    (before, its empty answer ended the play in `KeyError: -1` at the swap to the main weapons)."""
    if world.player is None:
        raise Abort('not in a game')
    if skills is None:
        raise Abort('the arena has no game to leave: the macro request and the route\'s leave are not played')
    for skill in skills:
        name = NAMES.get(skill, f'skill {skill}')
        if skill not in ACTIONS and skill not in world.slots:
            raise Abort(f'{name} is not on a skill key')
        if skill not in KEYS:
            raise Abort(f'{name} has no key the macro can press')
    return {skill: KEYS[skill] for skill in skills}


class Play:
    """One play: the arena, the production hunter and runner, and the presses still to come."""

    def __init__(
        self, arena: Arena, presses: Sequence[Press], seconds: float, seed: int, build: Build | None = None
    ) -> None:
        self.arena, self.seconds = arena, seconds
        # The build the hunter and every run play (`Game.run`), as the runner would have chosen it. None: the
        # Echoing Strike Warlock as the scene's character plays it.
        build = self.build = arena.build = warlock(arena.world) if build is None else build
        self.pending = sorted(presses, key=lambda press: press.at)
        self.pace = random.Random(seed)  # the macro's own pauses and scatter, one stream for the play
        scene = arena.scene
        # The level as the level guide gives it to the hunter: the scene's rooms (none in a fight-only
        # scene) and its walkable grids.
        rooms = tuple(Room(r['preset'], r['x'], r['y'], r['width'], r['height']) for r in scene.rooms)
        self.level = Level(scene.hero.area, rooms, arena.ground.grids)
        self.hunter = Hunter(lambda: self.level, lambda area: [], None, build=build)
        # No wall clock in a play: the same seed gives the same play however busy the machine (the safety caps
        # bound a look's work alone; macros/safety.py `Safety.timer`).
        self.hunter.safety.timer = None
        self.ended = False
        self.failed: list[BaseException] = []
        self.runner = MacroRunner(
            None,
            capture_lock=threading.Lock(),
            saved_games=Path(),
            display=self.display,
            execute=self.guarded,
            trace=Trace(clock=arena.clock),
        )
        self.runner.queue.clock = arena.clock
        self.runner.hunter = self.hunter

    def display(self, lines: list[str]) -> None:
        """The runner's card: what the macro says and why a run stopped, kept with the arena's time."""
        for line in lines:
            self.arena.say(line)

    # -- the macro, production -----------------------------------------------------------------------

    def execute(self, cancelled: threading.Event, routine: str) -> None:
        """`MacroRunner._execute` for ATTACK and PICKUP, with the arena for the game."""
        arena, runner, hunter = self.arena, self.runner, self.hunter
        run = arena.run()
        run.pace.rng = self.pace
        run.cancelled = run.actuator.cancelled = cancelled
        run.actuator.allow(*STEP_KEYS)
        run.say = runner._say
        run.deadline = runner.deadline
        run.ground = runner.ground
        loadout = self.build.weapons
        if loadout is not None:
            run.prebuff_hands, run.battle_hands = loadout.prebuff, loadout.battle
        if routine == PICKUP:
            level = hunter.level() if hunter.level is not None else None
            stepped = []

            def otherwise() -> None:
                if not open_near(run, level, key_names, threat(run)):
                    stepped.append(hunter.step(run, key_names))

            pick_up(run, level, key_names, otherwise, threat(run))
            if stepped:
                runner.attack_mode = True
        elif routine == ATTACK:
            run.actuator.drift, run.actuator.steady = 10**6, False
            hunter.pick = runner._pick
            hunter.attack_mode(run, key_names)
        else:
            raise AssertionError(f'the arena has no routine {routine}')

    def guarded(self, cancelled: threading.Event, routine: str) -> None:
        """`execute`, with what is no stop of the macro's own kept: the runner would show it as
        "Macro failed" and go on, and a fault of the arena would pass for a result."""
        try:
            self.execute(cancelled, routine)
        except Abort:
            raise
        except Exception as failure:
            self.failed.append(failure)
            raise

    # -- the presses and the end -----------------------------------------------------------------------

    def due(self) -> bool:
        return bool(self.pending) and self.pending[0].at <= self.arena.clock.now + EDGE

    def press(self) -> None:
        now = self.arena.clock.now
        self.runner.request(now, now, self.pending.pop(0).routine)

    def tick(self) -> None:
        """After every tick of the arena, in the thread that moved its clock: the play ends at the
        horizon or the death, and inside a run the presses that fell due are made."""
        if self.ended:
            return
        if self.arena.over is not None or self.arena.clock.now >= self.seconds - EDGE:
            self.end()
            return
        while self.runner.working and self.due():
            self.press()

    def end(self) -> None:
        """The play is over: the world stands still, the run working now stops and nothing follows it
        (as `Replay.end`)."""
        self.ended = True
        self.arena.end()
        with self.runner.lock:
            self.runner.attack_mode = False
            self.runner.queue.clear('the play ended')
            self.runner.cancelled.set()
        self.pending.clear()

    def settle(self) -> None:
        """Wait until no run works: the thread of the one working, and of whatever followed it."""
        limit = time.monotonic() + WALL_LIMIT
        while True:
            with self.runner.lock:
                thread, working = self.runner.thread, self.runner.working
            if thread is not None and thread.is_alive():
                thread.join(0.05)
            elif not working:
                return
            if time.monotonic() > limit:
                raise RuntimeError(f'a run of the macro did not end in {WALL_LIMIT:.0f} s of wall time')

    def run(self) -> Result:
        fresh()
        arena = self.arena
        saved, card = runner_module.time, runner_module.CARD_SECONDS
        runner_module.time = ArenaTime(arena)  # type: ignore[assignment]
        runner_module.CARD_SECONDS = 0.0
        arena.each_tick = self.tick
        try:
            while True:
                self.settle()
                if not self.ended and (arena.over is not None or arena.clock.now >= self.seconds - EDGE):
                    self.end()
                if self.ended:
                    break
                if self.due():
                    self.press()  # nothing runs: the press starts its run, waited for above
                else:
                    arena.time.step()
            self.settle()
            self.runner.close()
        finally:
            if not self.ended:
                self.end()
            runner_module.time, runner_module.CARD_SECONDS = saved, card
            arena.each_tick = None
        if self.failed:
            raise self.failed[0]
        return arena.result()


def play(
    scene: Scene,
    presses: Sequence[Press],
    seconds: float,
    *,
    build: Build | None = None,
    blades: bool | None = None,
    osd: HealingConfig | None = None,
    healing_scale: float = 1.0,
    seed: int = 1,
    auras: Mapping[int, float] | None = None,
    instant_moves: bool = False,
) -> Result:
    """Play `scene` for `seconds` of the arena's time with the production macro, started by
    `presses` as the runner starts it, and say what it came to. `seed` is the monsters' rolls and the
    macro's pace; `osd` runs the standalone healer beside it; `build` is the build whose macro plays:
    the hunter and every run are handed it. None: the Echoing Strike Warlock as the scene's character
    plays it (macros/fakes.py `warlock`). `blades` is how the arena casts the strike: the production
    blades of Echoing Strike, or what the build's attack says a cast deals (`Attack.dealt`). None: the
    blades with no build named, its own `dealt` for a build that is; who hands in a build of Echoing
    Strike says `blades=True`. `instant_moves`: every move is over in the instant of its input, as in
    the fakes' game (game.py; otherwise a walk, a hop and a Blade Warp take their time). The play ends
    early at the character's death."""
    for press in presses:
        if press.routine == TELEPORT:
            raise NotImplementedError('the teleport step comes to the arena in Stage 5')
        if press.routine not in (ATTACK, PICKUP):
            raise ValueError(f'the arena plays the attack mode toggle and the pickup step, not {press.routine!r}')
    if blades is None:
        blades = build is None
    attack = None if blades or build is None else build.attack
    arena = Arena(
        scene, seed=seed, osd=osd, healing_scale=healing_scale, auras=auras, attack=attack, instant_moves=instant_moves
    )
    return Play(arena, presses, seconds, seed, build).run()
