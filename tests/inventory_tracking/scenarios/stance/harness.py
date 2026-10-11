"""One recorded fight moment, replayed frame by frame: how fast a where-to-stand strategy clears it.

A fixture is one moment of a take: the character's place, the hostiles with the share of life they have,
the companions (not modelled), the raw door rows (the `d` rows of a take frame, read as combat/sim/situation.py
reads them), the walkable grids copied beside the take, and what the game did after (`after`). `load` reads
one; `scene` builds one by hand for a test. `play` asks a `Strategy` (`stay`, `production()`) whenever the
character is free and counts what its casts take off the monsters.

What the model assumes, on purpose:

- monsters stand still and do not strike; a body's full points are points_of(txt, area), times ELITE_LIFE
  for an elite, and it starts with its full points times its life share;
- the strategy and the aim see what production sees: a `Foe` with the points left, NOT multiplied by ELITE_LIFE;
- a walk takes WALK_LATENCY_FRAMES (the cast that has to end plus the click) plus the distance at RUN_SPEED,
  rounded up to frames; a hop takes HOP_FRAMES whatever the distance; the character casts nothing meanwhile,
  and the blades already flying keep flying (they were born from where the character stood);
- a walk whose straight line is barred (stance.way) is refused: the character stays and casts that turn;
- a cast is the production aim (LiveAim over LinePolicy, through the window) and the production blades
  (echoing_strike.cast, CONTACT_RADIUS, the duplicate rule, damage_table), born BIRTH_LAG frames after the cast;
- companions, Health Link and Hex Purge are not modelled; `in_fight` of a fixture is not read;
- the fight is cleared when every body that started within `near` units of the scene's origin is dead, and the
  replay stops there: bodies further off may still be alive, and are in the observation until then.
"""

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from inventory_tracking.combat import stance
from inventory_tracking.combat.controller import LiveAim
from inventory_tracking.combat.mechanics.damage import damage_table
from inventory_tracking.combat.mechanics.echoing_strike import LIFE, OUT_FRAMES, cast
from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.combat.policy import DUPLICATE, Foe, LinePolicy, Observation, walls
from inventory_tracking.combat.sim.input import BIRTH_LAG, CAST_FRAMES
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.hunt import ELITE_LIFE
from inventory_tracking.macros.view import Viewport


Point = tuple[float, float]
ASPECT = 2560 / 1418  # the player's window (the takes' rect)
WALK_LATENCY_FRAMES = 9  # the cast that has to end plus the click: 0.36 s
RUN_SPEED = 20.0  # units a second the character runs
HOP_FRAMES = 38  # a hop (weapon swap, teleport, swap back): 1.5 s whatever the distance
NEAR = 30.0  # units from the scene's origin: the monsters the fight is over when they are dead


@dataclass(frozen=True)
class Body:
    unit: int
    txt: int
    at: Point
    points: float  # full life points (an elite's ELITE_LIFE times its type's)
    elite: bool = False  # a unique, champion or super unique
    life: float = 1.0  # the share of full life at the start, (0, 1]


@dataclass(frozen=True)
class Scene:
    name: str
    area: int
    origin: Point  # where the character stands at the start
    bodies: tuple[Body, ...]
    ground: Ground | None
    doors: tuple[Door, ...] = ()
    recorded: dict = field(default_factory=dict)  # the fixture's `after`: what the game did
    blocked: Callable[[Point], bool] | None = field(init=False, default=None)  # walls for a blade (policy.walls)
    barred: Callable[[Point], bool] | None = field(init=False, default=None)  # no footing for a walk

    def __post_init__(self) -> None:
        object.__setattr__(self, 'blocked', walls(self.ground, self.doors))
        object.__setattr__(self, 'barred', stance.no_footing(self.ground, self.doors))


@dataclass(frozen=True)
class Move:
    to: Point
    hop: bool = False  # a hop: HOP_FRAMES whatever the distance, never refused
    walk: float | None = None  # units of a way round what bars the straight line (the game finds it); None: straight


@dataclass
class CastTrace:
    frame: int  # the frame the cast started (its blades are born BIRTH_LAG frames later)
    origin: Point
    focal: Point
    paths: list[list[Point]]  # what echoing_strike.cast returned: five blade paths
    touched: set[int] = field(default_factory=set)  # the monsters its blades touched, filled as they fly


@dataclass(frozen=True)
class MoveTrace:
    started: int  # the frame the move was accepted
    arrives: int  # the frame the character is free again, standing at `to`
    start: Point
    to: Point
    hop: bool
    walk: float  # units walked (0.0 for a hop)


@dataclass
class Trace:
    """What `play` fills when it is given one: everything a picture of the replay needs."""

    casts: list[CastTrace] = field(default_factory=list)
    moves: list[MoveTrace] = field(default_factory=list)
    life: list[tuple[int, int, float]] = field(default_factory=list)  # (frame, unit, life points left)
    deaths: dict[int, int] = field(default_factory=dict)  # unit -> frame
    taken: list[tuple[int, float]] = field(default_factory=list)  # (frame, points taken so far)
    end_frame: int = 0  # the last frame simulated


@dataclass
class View:
    seen: Observation  # what production sees: the origin, the foes with points left, the walls, no window yet
    barred: Callable[[Point], bool] | None  # no footing: what a walk may not cross
    frame: int
    moves_made: int


Strategy = Callable[[View], Move | None]  # asked whenever the character is free; None = stay and cast


@dataclass
class Result:
    cleared_at: int | None = None  # the frame the last near body died; None: something near lived at the end
    casts: int = 0
    moves: int = 0
    refused: int = 0  # walks through a barred line
    walked: float = 0.0  # units walked (walks only; a hop is not counted)
    taken: float = 0.0  # life points taken off the monsters
    kills_at: list[int] = field(default_factory=list)  # the frame of each death, any distance
    alive: int = 0  # bodies alive when the replay stopped

    @property
    def cleared(self) -> bool:
        return self.cleared_at is not None

    @property
    def seconds(self) -> float | None:
        return None if self.cleared_at is None else self.cleared_at / GAME_RATE

    def line(self) -> str:
        """The numbers a test's reason quotes."""
        end = f'dead at {self.seconds:.1f} s' if self.cleared else f'{self.alive} alive at the end'
        return f'{end}, {self.casts} casts, {self.moves} moves ({self.walked:.0f} units walked), {self.refused} refused'


def body(unit: int, txt: int, at: Point, area: int, *, elite: bool = False, life: float = 1.0) -> Body:
    """A monster of `txt` at world point `at`, with its type's points in `area` on Hell."""
    full = points_of(txt, area) * (ELITE_LIFE if elite else 1.0)
    return Body(unit, txt, (float(at[0]), float(at[1])), full, elite, life)


def scene(
    name: str,
    area: int,
    origin: Point,
    bodies: tuple[Body, ...] | list[Body],
    ground: Ground | None = None,
    doors: tuple[Door, ...] | list[Door] = (),
) -> Scene:
    """A hand-made scene: the bodies are world points already (see `body`)."""
    return Scene(name, area, (float(origin[0]), float(origin[1])), tuple(bodies), ground, tuple(doors))


def load(path: str | Path) -> Scene:
    """The scene of one fixture file (the format in the module's package notes, build_fixtures.py)."""
    fixture = json.loads(Path(path).read_text())
    area = int(fixture['area'])
    bodies = tuple(
        body(h['unit'], h['txt'], h['at'], area, elite=h.get('elite', False), life=h.get('life', 1.0))
        for h in fixture['hostiles']
    )
    grids = tuple(Walkable(**grid) for grid in fixture.get('ground', ()))
    # The door row as combat/sim/situation.py `cut` reads a take frame's `d` rows (unit, txt, mode, x, y).
    doors = tuple(Door(d[0], d[1], d[2], float(d[3]), float(d[4])) for d in fixture.get('doors', ()))
    player = fixture['player']
    return Scene(
        fixture['name'],
        area,
        (float(player[0]), float(player[1])),
        bodies,
        Ground(grids) if grids else None,
        doors,
        dict(fixture.get('after', {})),
    )


def play(
    scene: Scene,
    strategy: Strategy,
    seconds: float = 20.0,
    near: float = NEAR,
    trace: Trace | None = None,
    linger: int = 0,
) -> Result:
    """The scene replayed for `seconds` at GAME_RATE frames a second, the strategy asked whenever the character
    is free. The replay stops when the near bodies are dead (the fight is cleared there), or `linger` frames
    later: the blades in flight keep flying (and hurting) but nothing new is cast or moved. A `trace` is filled."""
    damage_of = damage_table()
    aim = LiveAim(LinePolicy(yields=True), Viewport(ASPECT).reachable_focal)
    bodies = {b.unit: b for b in scene.bodies}
    life = {b.unit: b.points * b.life for b in scene.bodies}
    deaths: dict[int, int] = {}
    needed = {b.unit for b in scene.bodies if math.dist(b.at, scene.origin) <= near}
    origin, walk_to, busy_until = scene.origin, None, 0
    flights: list[tuple[int, list[list[Point]], set[tuple[int, str]], list[set[tuple[int, str]]], set[int]]] = []
    result = Result()

    def alive(unit: int) -> bool:
        return life[unit] > 0.0

    stop: int | None = None
    for frame in range(round(seconds * GAME_RATE) + 1):
        if trace is not None:
            trace.end_frame = frame
        if walk_to is not None and frame >= busy_until:
            origin, walk_to = walk_to, None  # the walk has ended: the character stands at its spot
        if frame >= busy_until and stop is None:
            foes = {
                # The game's observation: the type's points in the area, times the life share it shows now.
                unit: Foe(b.txt, b.at, points_of(b.txt, scene.area) * life[unit] / b.points, b.elite)
                for unit, b in bodies.items()
                if alive(unit)
            }
            seen = Observation(origin, foes, blocked=scene.blocked, frame=frame)
            move = strategy(View(seen, scene.barred, frame, result.moves))
            if (
                isinstance(move, Move)
                and not move.hop
                and move.walk is None
                and not stance.way(scene.barred, origin, move.to)
            ):
                result.refused += 1
                move = None
            if isinstance(move, Move):
                distance = math.dist(origin, move.to) if move.walk is None else move.walk
                walk = math.ceil(distance / RUN_SPEED * GAME_RATE)
                busy_until = frame + (HOP_FRAMES if move.hop else WALK_LATENCY_FRAMES + walk)
                walk_to = move.to
                if trace is not None:
                    trace.moves.append(
                        MoveTrace(frame, busy_until, origin, move.to, move.hop, 0.0 if move.hop else distance)
                    )
                result.moves += 1
                result.walked += 0.0 if move.hop else distance
            else:
                choice = aim(seen)
                if choice is None:
                    busy_until = frame + 1  # nothing worth a cast: wait a frame
                else:
                    at = origin
                    paths = cast(at, choice.focal, lambda k, at=at: at, scene.blocked)
                    record = CastTrace(frame, at, choice.focal, paths)
                    if trace is not None:
                        trace.casts.append(record)
                    flights.append((frame + BIRTH_LAG, paths, set(), [set() for _ in paths], record.touched))
                    result.casts += 1
                    busy_until = frame + CAST_FRAMES
        for birth, paths, first, touched, hit in flights:
            k = frame - birth
            if not 0 <= k < LIFE:
                continue
            leg = 'out' if k <= OUT_FRAMES else 'back'
            for blade, path in enumerate(paths):
                if k >= len(path):
                    continue
                for unit, b in bodies.items():
                    key = (unit, leg)
                    if not alive(unit) or key in touched[blade] or math.dist(path[k], b.at) > CONTACT_RADIUS:
                        continue
                    touched[blade].add(key)
                    hit.add(unit)
                    dealt = damage_of(b.txt) * (DUPLICATE if key in first else 1.0)
                    first.add(key)
                    result.taken += min(dealt, life[unit])
                    life[unit] -= dealt
                    if trace is not None:
                        trace.life.append((frame, unit, max(life[unit], 0.0)))
                        trace.taken.append((frame, result.taken))
                    if not alive(unit):
                        deaths[unit] = frame
                        if trace is not None:
                            trace.deaths[unit] = frame
                        result.kills_at.append(frame)
        if stop is None and needed and not any(alive(unit) for unit in needed):
            result.cleared_at = max(deaths[unit] for unit in needed)
            stop = frame + linger
        if stop is not None and frame >= stop:
            break
    result.alive = sum(alive(unit) for unit in bodies)
    return result


def stay(view: View) -> None:
    """Never moves: the character casts from where it stands (today, when the press answers 'Standing well')."""
    return None


def production(first: int = 1, follow: int = 0, hop: bool = False) -> Strategy:
    """The production step (combat/stance.py `camp`): the press's own step (`first`, taken wherever a
    place is worth it), then up to `follow` more, each only when nothing is in reach from where the
    character stands (macros/hunt.py `follow_on`). `hop` lets it teleport, which the game's step does not."""
    policy = LinePolicy(yields=True)

    def strategy(view: View) -> Move | None:
        if view.moves_made >= first + follow:
            return None
        seen = view.seen
        if (
            view.moves_made >= first
            and stance.taken(seen, policy, stance.Field(seen.blocked, None), seen.origin, 0.0)[0]
        ):
            return None
        found = stance.camp(seen, policy, view.barred, hop=hop)
        return None if found is None else Move(found.spot, found.hop, None if found.hop else found.walk)

    return strategy
