"""The teleport key (KP_4) in the arena: a recorded moment of a route played again with the presses that
were made, by the runner's own teleport routine (macros/runner.py `MacroRunner.perform`: the route's stage
by macros/route.py `press`, and the runner's plain step under it).

incident.py plays the attack mode toggle and the pickup key (driver.py `Play.execute`). `RoutePlay` is that
play with what the teleport routine asks of the service (appraisal/service.py), each from the production
code with the arena in the game's place:

- the routes' progress: `Progress(ROUTES, PERFORMED, dead=...)` as the service makes it, told the game and
  the level once (the service's `poll` does that every second) and, for a moment cut after an object was
  used, that object as the step itself notes it (`Progress.used`);
- the bosses dead (terror/tracker.py `killed`): the names of the incident's `bosses` whose units died in
  the arena. The tracker itself is not run;
- the level card (levels/guide.py `LevelGuide.target` and `marks`): `Card`, the marks the level's own
  handler gives for the take's rooms (levels/registry.py `handler_for(area).guide`, kept in the incident's
  route file by `store`), put in order by levels/guide.py `lead_first` with `Progress.lead`, as the guide
  does. The rooms and the ground a `Target` carries are the scene's (the driver's `Level`);
- the objects the marks name (the seals): a `Prop` on each mark that has a `use`, where the handler's
  layout puts it, with the unit id the session log has for it; `opened` ones are in mode 2;
- the build: the runner is given the play's build as its fallback and the fakes' layers, and names the
  run's build at its first look (`choosing`), as in the service.

All three routines of a `RoutePlay` go through `MacroRunner.perform`; only `_execute` (the process, the
window, the keyboard, the memory) is the arena's, as in driver.py.

One wait of the runner's is on the wall and not on `time`: `cancelled.wait(quiet_until - now)`, the quiet
after a teleport step before attack mode resumes (TRAVEL_QUIET, 0.5 s). With the real `threading.Event` it
would take half a wall second and none of the arena's, and the mode would be back in the instant of the
step's end: the very thing a mashed key keeps from happening. For a `RoutePlay` runner.py's `threading` is
`ArenaThreading`, whose events wait on the arena's clock a tick at a time (the presses that fall due are
made from those ticks, as in a run's own sleep); the module's `threading` is put back after the play.

What is not there: the level guide itself (its card follows the character with a delay; here it is always
the level's), the journey and `poll`, the monster tracker (`remembered`, `supers`, the visited rooms: the
hunter has none, as in driver.py), a seal boss appearing when its arm's last seal is opened, and the game
being left (`route.leave`). A press takes no time of the arena's but what its routine sleeps (the real one
took 20 to 40 ms from the request to its last line).

"As it was": the game of 09:06 was played with a rule of the night before, withdrawn the same day because of
this very moment: the teleport step did not hop to a mark a pack stood by ("N monsters by <mark>: the fight
first", the main weapons, a sweep step, attack mode on). The replay of the recording is played with that rule
put back on the test's side (`RoutePlay(as_it_was=True)`, `pack_ahead` and `fight_first` below, as
battle/test_tower_cellar5.py AS_IT_WAS does for its evening); a play without it is today's key.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.kp4 --seeds 10 [--cut]

For a moment recorded with the withdrawn rule the report has two tables: as it was, and today's key.
"""

import argparse
import json
import math
import statistics
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from itertools import pairwise
from pathlib import Path
from typing import Any

from inventory_tracking.builds.warlock.echoing_strike.mechanics import MISSILE
from inventory_tracking.combat.stance import CROWD_MOST, CROWD_UNITS
from inventory_tracking.config import PLAYER_HEALING, with_overrides
from inventory_tracking.input.compositor import STEP_KEYS
from inventory_tracking.levels.guide import lead_first, place
from inventory_tracking.levels.handler import marker_room
from inventory_tracking.levels.model import Level, LevelSnapshot, Location, Poi, Room, Target
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.pickup import worth_a_stop
from inventory_tracking.macros.route import FIGHT_NEAR, PERFORMED
from inventory_tracking.macros.routines import take_battle_weapons
from inventory_tracking.macros.runner import ATTACK, PICKUP, TELEPORT
from inventory_tracking.macros.teleport import USES, ready
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.takes.takes import Take, monsters_of, player_of
from inventory_tracking.takes.timeline import GAME_RATE
from tests.inventory_tracking.macros.fakes import LAYERS
from tests.inventory_tracking.scenarios.arena import scene as scene_file
from tests.inventory_tracking.scenarios.arena.cut import DEFAULT_HERO, MAIN, STAFF, cut, level_of
from tests.inventory_tracking.scenarios.arena.driver import Play, Press, key_names
from tests.inventory_tracking.scenarios.arena.game import EDGE, Arena
from tests.inventory_tracking.scenarios.arena.incident import FIXTURES, TAKES, Incident, births
from tests.inventory_tracking.scenarios.arena.scene import Prop, Scene


Point = tuple[float, float]
GAME = 'arena'  # the game's name the progress is told (`World.game_name` of the arena's world)
MADE_UP = 990_000_000  # unit ids of the marked objects the session log does not name, counted from here


@dataclass(frozen=True)
class Staged:
    """An incident on a route. `opened`: the labels of the marked objects used before its start; `bosses`:
    (unit id, the route's name of it) of the bosses in the scene; `units`: (mark label, the object's unit id
    in the session log); `reach`: how far from the character the scene keeps ground and monsters; `boss`:
    the route's name of the boss the moment is about, if any; `seal`: the label of the mark the moment is
    about, if any; `opened_at`: when the session log has that object opened, seconds after the start;
    `mashed`: the seconds after the start within which the key was mashed; `as_it_was`: the recording was
    played with the rule withdrawn since (`fight_first`), and its replay is given it."""

    incident: Incident
    reach: float = 60.0
    opened: tuple[str, ...] = ()
    bosses: tuple[tuple[int, str], ...] = ()
    units: tuple[tuple[str, int], ...] = ()
    boss: str | None = None
    seal: str | None = None
    opened_at: float | None = None
    mashed: float = 0.0
    as_it_was: bool = False

    @property
    def name(self) -> str:
        return self.incident.name


# Take 20261013T060607Z-108 begins at 09:06:07.58 of the session log (probe.log of session
# 20261013T060446Z-aa50e0b0): its three Blade Warp landings at 12.07, 32.58 and 34.27 s are logged at
# 09:06:19.654, 40.169 and 41.836. The presses below are that log's "request" lines less that time.
SEAL_PACK = Staged(
    Incident(
        name='kp4-seal-pack',
        take='20261013T060607Z-108',
        start=12.08,  # the Blade Warp has landed at (7687.5, 5317.5), 32.6 from the first Vizier seal
        # The log has the seal opened 21.03 s in (09:06:40.689) and the next one at 22.92; the arena's fight
        # leaves the character elsewhere, so the window runs on to the last press before the boss's stage.
        seconds=26.0,
        presses=(
            # 09:06:19.528, queued behind the step that landed: it runs at 19.662, the landing's instant
            (0.0, TELEPORT),
            *((at, TELEPORT) for at in (0.2, 0.43, 0.87, 1.17, 1.83, 2.11, 2.32, 2.53, 2.87)),
            (3.28, ATTACK),  # 09:06:22.945 "request hunt any ... Attack mode off": the toggle, the mode being on
            *((at, TELEPORT) for at in (4.5, 4.75, 5.0, 5.27, 5.61, 6.27)),
            (14.95, PICKUP),
            (16.78, PICKUP),
            # 09:06:38.893 on: the pack is down, the step warps to the seal and opens it at 40.689, then the
            # second seal at 42.576
            *((at, TELEPORT) for at in (19.23, 19.99, 20.4, 20.64, 20.85, 21.1, 21.36, 22.52, 22.75)),
        ),
        marks=(2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 20.0),
        # 09:06:25.833 "Psychic Ward": the mode's first cast, so the ward was down. 09:06:18.624 "Blade Warp
        # toward Vizier seal 1: 5 charges kept": the main weapons in hand, five charges on the staff.
        hero=(('ward', False), ('hand', 0), ('sets', (MAIN, replace(STAFF, teleport_charges=5)))),
        about=(
            'Chaos Sanctuary, 2026-10-13 09:06:19: the teleport step lands 33 units from the first Vizier seal '
            'with a pack by it. Sixteen presses of the teleport key in 6.4 s each say "the fight first" and '
            'pause attack mode; the first strike comes 7.1 s after the landing.'
        ),
    ),
    units=(('Vizier seal 1', 2960892495), ('Vizier seal 2', 960608137)),
    seal='Vizier seal 1',
    opened_at=21.03,  # 09:06:40.689 "Vizier seal 1: open"
    mashed=6.8,  # the last press of the burst is at 6.27, attack mode is on at 6.96 and strikes at 7.11
    as_it_was=True,  # every press of the burst said "the fight first": the rule of that morning
)
# The teleport key's presses of the second moment, seconds into the take (09:06:42.709 to 09:07:06.035).
BOSS_PRESSES = (
    35.13, 39.62, 40.46, 41.02, 41.52, 42.06, 42.63, 43.2, 43.61, 43.84, 44.05, 44.24, 44.42, 44.64, 44.86, 45.06,
    45.24, 45.49, 45.71, 45.9, 46.15, 46.36, 46.7, 47.06, 47.42, 47.61, 53.24, 53.85, 54.31, 54.53, 54.74, 54.97,
    55.26, 55.52, 55.72, 56.0, 56.24, 56.45, 56.67, 57.0, 57.22, 57.41, 57.61, 57.8, 58.0, 58.23, 58.46,
)  # fmt: skip
BOSS_AWAY = Staged(
    Incident(
        name='kp4-boss-away',
        take='20261013T060607Z-108',
        start=35.0,  # 09:06:42.585 "Diablo: Grand Vizier of Chaos, attack mode": the second seal is open
        seconds=25.0,  # the game is left at 09:07:07.8, the take's end
        presses=(
            (0.0, TELEPORT),  # 09:06:42.415, queued behind the step that opened the seal
            *((round(at - 35.0, 2), TELEPORT) for at in BOSS_PRESSES),
        ),
        marks=(5.0, 10.0, 15.0, 20.0, 25.0),
        hero=(('hand', 0), ('sets', (MAIN, replace(STAFF, teleport_charges=4)))),  # 09:06:40.801 "4 charges kept"
        about=(
            'Chaos Sanctuary, 2026-10-13 09:06:42: both Vizier seals are open and the route is at "fight Grand '
            'Vizier of Chaos", a stage with no mark. The Vizier and four minions stand 52 to 59 units off; 48 '
            'presses of the teleport key in 25 s each say "Grand Vizier of Chaos, attack mode" and move nothing.'
        ),
    ),
    reach=80.0,  # the Vizier stands 57 units off: the scene keeps him and the ground under him
    opened=('Vizier seal 1', 'Vizier seal 2'),
    bosses=((1171600073, 'Grand Vizier of Chaos'),),  # class 306, type flags 0x0a; his four minions have 0x10
    units=(('Vizier seal 1', 2960892495), ('Vizier seal 2', 960608137)),
    boss='Grand Vizier of Chaos',
)
STAGED = (SEAL_PACK, BOSS_AWAY)


# -- the level card -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Mark:
    """One mark of the level card as the level's handler gives it: `spot` in tiles (levels/guide.py `place`)."""

    label: str
    kind: str
    spot: Point
    use: int = 0


class Card:
    """The level card for the macro (levels/guide.py `LevelGuide.target` and `marks`), always the level's
    own: the handler's marks, the mark the route is at put first (`lead_first` with `Progress.lead`)."""

    def __init__(self, level: Callable[[], Level], marks: Sequence[Mark], progress: Progress) -> None:
        self.level, self.progress = level, progress
        self.pois = tuple(
            Poi(
                mark.label,
                marker_room(Room(0, round(mark.spot[0]), round(mark.spot[1]), 8, 8), *mark.spot),
                mark.kind,
                spot=mark.spot,
                use=mark.use,
            )
            for mark in marks
        )

    def target(self) -> Target | None:
        level = self.level()
        if not self.pois:
            return None
        poi = lead_first(self.pois, self.progress.lead(level.area))[0]
        return Target(level.area, level.rooms, place(poi), poi.label, poi.kind, False, level.ground, poi.use)

    def marks(self, label: str) -> tuple[Point, ...]:
        return tuple(place(poi) for poi in self.pois if poi.label == label)


def handler_marks(area: int, rooms: Sequence[dict], at: Point) -> list[Mark]:
    """The marks the level's handler gives for the take's rooms (the rows of its level file)."""
    handler = handler_for(area)
    if handler is None:
        return []
    found = tuple(
        Room(
            row['preset'], row['x'], row['y'], row['width'], row['height'], row.get('variant'),
            tuple(row['block']) if row.get('block') else None, tuple(row.get('leads_to', ())),
        )
        for row in rooms
    )  # fmt: skip
    guidance = handler.guide(LevelSnapshot(Location(area, 0, round(at[0]), round(at[1])), found))
    return [Mark(poi.label, poi.kind, place(poi), poi.use) for poi in guidance.pois]


# -- the play -------------------------------------------------------------------------------------------


class ArenaEvent(threading.Event):
    """A `threading.Event` whose timed wait is on the arena's clock: a tick at a time, in the thread that
    waits, until it is set or the time is over. A wait without a limit is the real one."""

    def __init__(self, arena: Arena) -> None:
        super().__init__()
        self.arena = arena

    def wait(self, timeout: float | None = None) -> bool:
        if timeout is None:
            return super().wait()
        clock = self.arena.clock
        until = clock.now + timeout
        while not self.is_set() and clock.now < until - EDGE:
            clock.sleep(min(1 / GAME_RATE, until - clock.now))
        return self.is_set()


class ArenaThreading:
    """What runner.py reads of `threading`, for a `RoutePlay`: its events are `ArenaEvent`s."""

    def __init__(self, arena: Arena) -> None:
        self.arena = arena

    def Event(self) -> ArenaEvent:
        return ArenaEvent(self.arena)

    def __getattr__(self, name: str) -> object:
        return getattr(threading, name)


AHEAD_UNITS = 45.0  # the withdrawn rule's: a mark this near is arrived at by the next hop or the one after


def pack_ahead(hunter: Hunter, run: Run, target: Target) -> int:
    """`Hunter.pack_ahead` as it was on the morning of 2026-10-13 (commit 464d88a, withdrawn the same day):
    how many hostiles stand by a mark the teleport step is about to stand at: an object to use (not a way
    on), within AHEAD_UNITS of the character, with more than CROWD_MOST hostiles within CROWD_UNITS of it."""
    if target.warp or not target.use or USES[target.use].leaves:
        return 0
    player, _ = ready(run)
    if player.area != target.area:
        return 0
    mark = (target.point[0] * TILE_UNITS, target.point[1] * TILE_UNITS)
    if math.dist((player.x, player.y), mark) > AHEAD_UNITS:
        return 0
    near = sum(1 for m in hunter.foes(run.world(), run.clock()) if math.dist(mark, (m.x, m.y)) <= CROWD_UNITS)
    return near if near > CROWD_MOST else 0


def fight_first(runner, run: Run, plain: Callable[[Target | None], None]) -> Callable[[Target | None], None]:
    """The runner's plain teleport step as it was that morning: `plain` with the withdrawn branch before the
    boss's step and the hop (after the drop worth a stop, as it stood in runner.py)."""

    def step(card: Target | None) -> None:
        walker = runner.hunter
        if walker is None or card is None or worth_a_stop(run) is not None:
            return plain(card)
        crowd = pack_ahead(walker, run, card)
        if not crowd:
            return plain(card)
        run.say(f'{crowd} monsters by {card.label}: the fight first')
        take_battle_weapons(run)
        walker.step(run, key_names)
        runner.attack_mode = True
        return None

    return step


class RoutePlay(Play):
    """A play with the routes: every routine is the runner's own (`MacroRunner.perform`), the teleport
    routine among them (the module text has what it is given). `as_it_was`: the teleport step has the rule
    withdrawn on 2026-10-13 (`fight_first`)."""

    def __init__(
        self,
        arena: Arena,
        presses: Sequence[Press],
        seconds: float,
        seed: int,
        marks: Sequence[Mark],
        opened: Sequence[str] = (),
        bosses: Sequence[tuple[int, str]] = (),
        as_it_was: bool = False,
    ) -> None:
        super().__init__(arena, presses, seconds, seed)
        self.as_it_was = as_it_was
        runner, area = self.runner, arena.scene.hero.area
        runner.builds, runner.fallback, runner.build = tuple(LAYERS), self.build, self.build
        self.bosses = tuple(bosses)
        self.progress = runner.progress = Progress(ROUTES, PERFORMED, dead=self.slain)
        self.progress.note(GAME, area)
        self.card = Card(lambda: self.level, marks, self.progress)
        for label in opened:
            for spot in self.card.marks(label):
                self.progress.used(area, label, spot, self.card.marks(label))
        runner.target, runner.marks = self.card.target, self.card.marks

    def pursuing(self) -> None:
        """The play's builds with the pursuit loop on (`BuildSettings.pursuit`, macros/pursuit.py): the one
        played, the runner's fallback and layers (it names the run's build from them at its first look) and
        the hunter's."""

        def on(build):
            return replace(build, settings=with_overrides(build.settings, pursuit=True))

        runner = self.runner
        self.build = self.arena.build = runner.fallback = runner.build = on(self.build)
        runner.builds = tuple(on(layer) for layer in runner.builds)
        self.hunter.use(self.build)

    def slain(self) -> frozenset[str]:
        """The bosses dead, by the routes' names (terror/tracker.py `killed`)."""
        mobs = self.arena.mobs
        alive = set(mobs.live())
        return frozenset(name for unit, name in self.bosses if unit in mobs.mobs and unit not in alive)

    def stage(self) -> str | None:
        """The stage the level is at, as the route's log names it; None: none left."""
        step = self.progress.step(self.arena.scene.hero.area)
        return None if step is None else step.stage.text()

    def execute(self, cancelled: threading.Event, routine: str) -> None:
        """`MacroRunner._execute` with the arena for the game: the run made, and `perform` on it."""
        arena, runner = self.arena, self.runner
        run = arena.run()
        run.pace.rng = self.pace
        run.cancelled = run.actuator.cancelled = cancelled
        run.actuator.allow(*STEP_KEYS)
        run.say = runner._say
        run.warn = runner._warn
        run.stand_by = runner._stand_by
        run.deadline = runner.deadline
        run.ground = runner.ground
        run.ending = self.progress.ending
        loadout = self.build.weapons
        if loadout is not None:
            run.prebuff_hands, run.battle_hands = loadout.prebuff, loadout.battle
        if not (self.as_it_was and routine == TELEPORT):
            runner.perform(run, run.actuator, routine, key_names)
            return
        staged = runner.staged  # the class's: the teleport routine gives it its plain step
        runner.staged = lambda run, key_names, plain: staged(run, key_names, fight_first(runner, run, plain))
        try:
            runner.perform(run, run.actuator, routine, key_names)
        finally:
            del runner.staged

    def run(self):
        saved = runner_module.threading
        runner_module.threading = ArenaThreading(self.arena)  # type: ignore[assignment]
        try:
            return super().run()
        finally:
            runner_module.threading = saved


# -- what a play and the recording came to --------------------------------------------------------------


@dataclass(frozen=True)
class Told:
    """What a moment came to, in seconds after its start (None: never within the window).

    `strikes`: when each strike began. `quiet`: the longest time without a strike's beginning while a
    hostile stood within the strike's reach of the character (the window's ends count as strikes).
    `quiet_mashed`: the same within the incident's `mashed` seconds. `taken` and `low`: the life lost and
    the least life. `pack_down`: when no pack stood by the seal for the first time (the withdrawn rule's
    count, `pack_ahead`: more than CROWD_MOST hostiles within CROWD_UNITS of the mark). `opened`: when the seal
    was opened. `moved`: how far the character went. `boss_gap`: the least and the last distance to the boss;
    `boss_dead`: when it died. `stage`: the route's stage at the end."""

    strikes: tuple[float, ...]
    quiet: float
    quiet_mashed: float
    taken: float
    low: float
    pack_down: float | None
    opened: float | None
    moved: float
    boss_gap: tuple[float, float] | None
    boss_dead: float | None
    stage: str | None
    dead: bool = False


def longest_quiet(strikes: Sequence[float], reached: Sequence[tuple[float, bool]], until: float) -> float:
    """The longest stretch within [0, `until`] in which a hostile was in reach at every sample (`reached`:
    (time, whether one was)) and no strike began."""
    longest, since = 0.0, None
    casts = sorted(strikes)
    for at, near in reached:
        if at > until + EDGE:
            break
        while casts and casts[0] <= at + EDGE:
            casts.pop(0)
            since = None
        if not near:
            since = None
        elif since is None:
            since = at
        if since is not None:
            longest = max(longest, at - since)
    return round(longest, 2)


def pack_down(counts: Sequence[tuple[float, int]]) -> float | None:
    """When the pack by the seal was first down: the first sample at which `pack_ahead` would let the step go
    on. (Not "for good": once the character goes to the seal, what follows it stands by the seal again.)"""
    return next((round(at, 2) for at, count in counts if count <= CROWD_MOST), None)


def mark_of(marks: Sequence[Mark], label: str | None) -> Point | None:
    spot = next((mark.spot for mark in marks if mark.label == label), None)
    return None if spot is None else (spot[0] * TILE_UNITS, spot[1] * TILE_UNITS)


def played(
    scene: Scene,
    marks: Sequence[Mark],
    staged: Staged,
    seed: int,
    presses: Sequence[tuple] | None = None,
    as_it_was: bool | None = None,
):
    """One play of the moment in the arena, the standalone healer beside the macro: (`Told`, the lines the
    macro said with their times). `presses`: other presses than the recorded ones. `as_it_was`: with the
    rules of the recording's day (None: as the moment was recorded, `Staged.as_it_was`); False: today's."""
    incident = staged.incident
    arena = Arena(scene, seed=seed, osd=PLAYER_HEALING)
    given = incident.presses if presses is None else presses
    play = RoutePlay(
        arena, [Press(at, routine) for at, routine in given], incident.seconds, seed, marks,
        staged.opened, staged.bosses, staged.as_it_was if as_it_was is None else as_it_was,
    )  # fmt: skip
    reach = play.build.attack.reach if play.build.attack is not None else 0.0
    seal = mark_of(marks, staged.seal)
    boss = next((unit for unit, name in staged.bosses if name == staged.boss), None)
    thing = next((prop.unit for prop in scene.things if seal is not None and math.dist(prop.at, seal) < 1), None)
    strikes: list[float] = []
    reached: list[tuple[float, bool]] = []
    packs: list[tuple[float, int]] = []
    gaps: list[float] = []
    seen: dict[str, Any] = {'casts': 0, 'low': arena.life, 'opened': None, 'boss_dead': None}
    spy = play.tick

    def tick() -> None:
        now, here = arena.clock.now, arena.here
        if arena.over is None:
            if arena.casts > seen['casts']:
                strikes.extend([round(now, 2)] * (arena.casts - seen['casts']))
                seen['casts'] = arena.casts
            live = [arena.mobs.mobs[unit].at for unit in arena.mobs.live()]
            reached.append((now, any(math.dist(here, at) <= reach for at in live)))
            if seal is not None:
                packs.append((now, sum(1 for at in live if math.dist(seal, at) <= CROWD_UNITS)))
                if seen['opened'] is None and any(t.unit_id == thing and t.mode for t in arena.things):
                    seen['opened'] = round(now, 2)
            if boss is not None:
                if boss in arena.mobs.live():
                    gaps.append(math.dist(here, arena.mobs.mobs[boss].at))
                elif seen['boss_dead'] is None:
                    seen['boss_dead'] = round(now, 2)
            seen['low'] = min(seen['low'], arena.life)
        spy()

    play.tick = tick  # type: ignore[method-assign]
    result = play.run()
    told = Told(
        strikes=tuple(strikes),
        quiet=longest_quiet(strikes, reached, incident.seconds),
        quiet_mashed=longest_quiet(strikes, reached, staged.mashed),
        taken=round(result.taken, 1),
        low=round(max(seen['low'], 0.0), 1),
        pack_down=pack_down(packs) if seal is not None else None,
        opened=seen['opened'],
        moved=round(result.moved, 1),
        boss_gap=(round(min(gaps), 1), round(gaps[-1], 1)) if gaps else None,
        boss_dead=seen['boss_dead'],
        stage=play.stage(),
        dead=result.dead_at is not None,
    )
    return told, result.said


def recorded(take: Take, staged: Staged, scene: Scene, marks: Sequence[Mark]) -> Told:
    """The recording's side of the moment. The strikes are the births of the strike's missiles
    (incident.py `births`); the reach is the build's own; the seal's opening is the session log's."""
    from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD

    incident = staged.incident
    zero = take.frames[0]['t']
    start, end = zero + incident.start, zero + incident.start + incident.seconds
    frames = [frame for frame in take.frames if start <= frame['t'] <= end]
    attack = ECHOING_STRIKE_BUILD.attack
    reach = attack.reach if attack is not None else 0.0
    seal = mark_of(marks, staged.seal)
    boss = next((unit for unit, name in staged.bosses if name == staged.boss), None)
    strikes = [round(at - start, 2) for at in births(frames, MISSILE)]
    reached, packs, gaps, lives, places = [], [], [], [], []
    boss_dead = None
    for frame in frames:
        row = player_of(frame)
        if row is None:
            continue
        at = frame['t'] - start
        hostile = [monster for monster in monsters_of(frame) if monster.hostile and monster.alive]
        reached.append((at, any(math.dist(row.at, monster.at) <= reach for monster in hostile)))
        if seal is not None:
            packs.append((at, sum(1 for monster in hostile if math.dist(seal, monster.at) <= CROWD_UNITS)))
        found = next((monster for monster in monsters_of(frame) if monster.unit == boss), None)
        if found is not None and found.alive:
            gaps.append(math.dist(row.at, found.at))
        elif found is not None and boss_dead is None:
            boss_dead = round(at, 2)
        if row.life and row.max_life:
            lives.append(float(row.life))
        places.append(row.at)
    events = [event for event in take.events if start < event['t'] <= end and event.get('event') == 'hurt']
    return Told(
        strikes=tuple(strikes),
        quiet=longest_quiet(strikes, reached, incident.seconds),
        quiet_mashed=longest_quiet(strikes, reached, staged.mashed),
        taken=float(sum(event.get('lost', 0) for event in events)),
        low=min(lives, default=0.0),
        pack_down=pack_down(packs) if seal is not None else None,
        opened=staged.opened_at,
        moved=round(sum(math.dist(a, b) for a, b in pairwise(places)), 1),
        boss_gap=(round(min(gaps), 1), round(gaps[-1], 1)) if gaps else None,
        boss_dead=boss_dead,
        stage=None,  # the log's: the incident's text has it
    )


# -- the fixtures ---------------------------------------------------------------------------------------


def paths(staged: Staged) -> tuple[Path, Path, Path]:
    name = staged.name
    return FIXTURES / f'{name}.json', FIXTURES / f'{name}.route.json', FIXTURES / f'{name}.recorded.json'


def _told(data: Mapping[str, Any]) -> Told:
    fields: dict[str, Any] = {key: tuple(value) if isinstance(value, list) else value for key, value in data.items()}
    return Told(**fields)


def stored(staged: Staged) -> tuple[Scene, list[Mark], Told] | None:
    """The moment's scene, the level card's marks and the recording's side, as kept; None: not cut yet."""
    scene_path, route_path, told_path = paths(staged)
    if not (scene_path.exists() and route_path.exists() and told_path.exists()):
        return None
    marks = [
        Mark(row['label'], row['kind'], tuple(row['spot']), row['use'])
        for row in json.loads(route_path.read_text(encoding='utf-8'))['marks']
    ]
    return scene_file.load(scene_path), marks, _told(json.loads(told_path.read_text(encoding='utf-8')))


def store(staged: Staged, takes: Path = TAKES) -> tuple[Scene, list[Mark], Told]:
    """Cut the moment from its take: the scene (with a `Prop` on each mark that names an object), the marks
    of the level's handler for the take's rooms, and the recording's side."""
    incident = staged.incident
    take = Take.load(takes / incident.take)
    zero = take.frames[0]['t']
    frame = next(index for index, row in enumerate(take.frames) if row['t'] - zero >= incident.start)
    scene = cut(take, frame, defaults=DEFAULT_HERO, name=incident.name, reach=staged.reach)
    known = dict(incident.hero)
    scene.hero = replace(scene.hero, **known)  # type: ignore[arg-type]
    scene.assumed = tuple(name for name in scene.assumed if name not in known)
    level = level_of(take) or {}
    marks = handler_marks(scene.hero.area, level.get('rooms', ()), scene.hero.at)
    units = dict(staged.units)
    scene.things = [
        Prop(
            units.get(mark.label, MADE_UP + index),
            mark.use,
            (mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS),
            2 if mark.label in staged.opened else 0,
        )
        for index, mark in enumerate(marks)
        if mark.use
    ]
    truth = recorded(take, staged, scene, marks)
    scene_path, route_path, told_path = paths(staged)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    scene_file.dump(scene, scene_path)
    route_path.write_text(json.dumps({'marks': [asdict(mark) for mark in marks]}, indent=1) + '\n', encoding='utf-8')
    told_path.write_text(json.dumps(asdict(truth), indent=1) + '\n', encoding='utf-8')
    return scene, marks, truth


# -- the report -----------------------------------------------------------------------------------------


def said(lines: Sequence[tuple[float, str]], part: str, until: float = math.inf) -> int:
    """How many of the lines the macro said up to `until` hold `part`."""
    return sum(1 for at, text in lines if part in text and at <= until + EDGE)


def spread(values: Sequence[float | None]) -> str:
    found = [value for value in values if value is not None]
    if not found:
        return 'never'
    never = f', never in {len(values) - len(found)}' if len(found) < len(values) else ''
    return f'{min(found):g} / {statistics.median(found):g} / {max(found):g}{never}'


def table(staged: Staged, truth: Told, plays: Sequence[Told], rules: str = '') -> str:
    incident = staged.incident
    first = [play.strikes[0] if play.strikes else None for play in plays]
    rows = [
        ('first strike, s', truth.strikes[0] if truth.strikes else None, first),
        ('strikes', len(truth.strikes), [len(play.strikes) for play in plays]),
        ('longest time without a strike, a hostile in reach, s', truth.quiet, [play.quiet for play in plays]),
        (f'the same within the first {staged.mashed:g} s', truth.quiet_mashed, [play.quiet_mashed for play in plays]),
        ('life lost', truth.taken, [play.taken for play in plays]),
        ('least life', truth.low, [play.low for play in plays]),
        ('moved', truth.moved, [play.moved for play in plays]),
    ]
    if staged.seal:
        rows += [
            (f'no pack by {staged.seal} at, s', truth.pack_down, [play.pack_down for play in plays]),
            (f'{staged.seal} opened at, s', truth.opened, [play.opened for play in plays]),
        ]
    if staged.boss:
        rows += [
            (f'least distance to {staged.boss}', truth.boss_gap and truth.boss_gap[0],
             [play.boss_gap and play.boss_gap[0] for play in plays]),
            (f'last distance to {staged.boss}', truth.boss_gap and truth.boss_gap[1],
             [play.boss_gap and play.boss_gap[1] for play in plays]),
            (f'{staged.boss} dead at, s', truth.boss_dead, [play.boss_dead for play in plays]),
        ]  # fmt: skip
    lines = [
        f'## {incident.name}{rules}',
        '',
        incident.about,
        '',
        f'Take {incident.take}, {incident.start:g} s in, {incident.seconds:g} s; {len(plays)} seeds; '
        f'{sum(1 for play in plays if play.dead)} deaths.',
        '',
        '| | recorded | arena least / median / most |',
        '| --- | ---: | ---: |',
        *(f'| {what} | {"never" if real is None else f"{real:g}"} | {spread(values)} |' for what, real, values in rows),
    ]
    stages = sorted({str(play.stage) for play in plays})
    lines += ['', f'The stage at the end: {"; ".join(stages)}.']
    return '\n'.join(lines) + '\n'


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('names', nargs='*', help='moments to play (default: all)')
    parser.add_argument('--seeds', type=int, default=10)
    parser.add_argument('--cut', action='store_true', help='cut the scenes again from the takes')
    args = parser.parse_args(argv)
    for staged in STAGED:
        if args.names and staged.name not in args.names:
            continue
        scene, marks, truth = store(staged) if args.cut else stored(staged) or store(staged)
        seeds = range(1, args.seeds + 1)
        if staged.as_it_was:
            plays = [played(scene, marks, staged, seed, as_it_was=True)[0] for seed in seeds]
            print(table(staged, truth, plays, ', as it was (the rule "the fight first", withdrawn 2026-10-13)'))
        plays = [played(scene, marks, staged, seed, as_it_was=False)[0] for seed in seeds]
        print(table(staged, truth, plays, ", today's key" if staged.as_it_was else ''))
    return 0


__all__ = ['BOSS_AWAY', 'FIGHT_NEAR', 'SEAL_PACK', 'STAGED', 'RoutePlay', 'played', 'said', 'store', 'stored']

if __name__ == '__main__':
    raise SystemExit(main())
