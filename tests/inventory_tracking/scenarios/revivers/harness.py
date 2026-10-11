"""A fight against monsters that come back: the least the combat simulator lacks for revivers.

combat/sim/engine.py replays a take open loop and a monster dies once. Here the monsters stand where
a scenario puts them, the blades are the production ones (mechanics/echoing_strike.py `cast`, the
contact radius, the duplicate rule, the cast cadence of sim/input.py), and a `Raiser` brings a corpse
within its range back at full life every `period` frames while it lives itself (the same unit id, as
the terror tracker's logs of 2026-10-03 show it in the game). `run` measures what a fight achieves in
a scenario's seconds: when the pack is really dead, the casts spent, the life taken off monsters that
came back.

What decides is a `Fight`: a callable from a `Brief` (the production `Observation` plus what the
production code does not know today: who raises whom, from how far) to a production `Choice`, a
`Move` or None. `today` is the game's own aim (combat/controller.py `LiveAim` over `LinePolicy`, the
simulator's `live` candidate) and never looks at the extras. `prototype` is the changes proposed,
one on top of the other (FIGHTS), to count what each would mend:

- `flagged`: the same line sweep with the revivers weighted REVIVER_WEIGHT (a flag on `Foe`);
- `reposition`: and when a live reviver covers the pack and no blade can reach it, a move to a spot
  with a shot at it;
- `hold`: and with no such spot, no cast at what would only come back;
- `reference`: and when two revivers raise each other and no line takes both, a move onto their
  common line.

Not modelled, on purpose: monsters do not move or strike, the companions, Health Link and Hex Purge
are off, a move is a hop of MOVE_FRAMES whatever the distance, and a raise is one corpse per `period`
(the tables' think delay over the raise chance: table.py), the nearest corpse first.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from inventory_tracking.combat.controller import LiveAim
from inventory_tracking.combat.mechanics.damage import damage_table
from inventory_tracking.combat.mechanics.echoing_strike import LIFE, OUT_FRAMES, cast
from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.combat.policy import (
    DUPLICATE,
    REACH,
    STRIKE_REACH,
    Choice,
    Foe,
    LinePolicy,
    Observation,
    clear_line,
)
from inventory_tracking.combat.sim.input import BIRTH_LAG, CAST_FRAMES
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.hunt import ELITE_LIFE
from inventory_tracking.macros.view import Viewport


Point = tuple[float, float]
ORIGIN: Point = (5000.0, 5000.0)
ASPECT = 2560 / 1418  # the player's window (the takes' rect)
MOVE_FRAMES = 25  # ASSUMED: one hop to a firing spot and standing free again (teleport.py allows 1.5 s at most)
REVIVER_WEIGHT = 10.0  # a point off a reviver in the prototypes: above any line of plain monsters a pack offers
SPOT_RINGS = (8.0, 12.0, 16.0, STRIKE_REACH)  # units from the reviver where a firing spot is looked for
SPOT_BEARINGS = 24


@dataclass(frozen=True)
class Body:
    unit: int
    txt: int
    at: Point
    points: float  # life points at full health as the game has them (an elite's ELITE_LIFE times its type's)
    elite: bool = False  # a unique or champion: what the game's observation flags as `leader`


@dataclass(frozen=True)
class Raiser:
    unit: int  # the reviver's own unit
    range: float  # units from the reviver to a corpse it can raise
    period: int  # frames between two raises while a corpse lies in range
    raises: frozenset[int]  # the units it can raise


@dataclass(frozen=True)
class Scenario:
    name: str
    area: int
    bodies: tuple[Body, ...]
    raisers: tuple[Raiser, ...] = ()
    blocked: Callable[[Point], bool] | None = None  # the walls and closed doors for a blade
    seconds: float = 30.0
    within: float | None = None  # wanted: the pack really dead within this many seconds (None: it cannot be)
    raised: int = 0  # wanted: at most this many monsters brought back meanwhile
    casts: int | None = None  # wanted: at most this many casts (the bound when the pack cannot be killed)
    why: str = ''

    @property
    def frames(self) -> int:
        return round(self.seconds * GAME_RATE)


@dataclass(frozen=True)
class Move:
    to: Point  # where the character should stand


@dataclass
class Brief:
    seen: Observation  # what the production policy is given today
    raisers: dict[int, Raiser]  # the live revivers by unit
    corpses: dict[int, Point]  # the dead that a live reviver could raise, by unit
    spots: Callable[[Point], bool] | None = None  # whether the character can stand at a point (None: anywhere)


Fight = Callable[[Brief], Choice | Move | None]


@dataclass
class Result:
    cleared_at: int | None = None  # the frame the last monster died for good; None: something lived at the end
    casts: int = 0
    moves: int = 0
    revivals: int = 0
    wasted: float = 0.0  # life points taken off monsters that were then raised
    taken: float = 0.0  # life points taken in all
    deaths: dict[int, list[int]] = field(default_factory=dict)  # unit -> the frames it died at
    alive: tuple[int, ...] = ()  # the units alive at the end

    @property
    def cleared(self) -> bool:
        return self.cleared_at is not None

    @property
    def seconds(self) -> float | None:
        return None if self.cleared_at is None else self.cleared_at / GAME_RATE

    def line(self) -> str:
        """The numbers a test's reason quotes."""
        end = f'dead at {self.seconds:.1f} s' if self.cleared else f'{len(self.alive)} alive at the end'
        return f'{end}, {self.casts} casts, {self.revivals} raised ({self.wasted:.0f} points wasted)'


def body(unit: int, txt: int, at: tuple[float, float], area: int, *, elite: bool = False) -> Body:
    """A monster of `txt` standing `at` units from the character, with its type's points in `area` on Hell."""
    full = points_of(txt, area) * (ELITE_LIFE if elite else 1.0)
    return Body(unit, txt, (ORIGIN[0] + at[0], ORIGIN[1] + at[1]), full, elite)


def tougher(scenario: Scenario, name: str, factor: float, **wanted) -> Scenario:
    """The scenario with every monster's life `factor` times its type's in the area: what the game's
    observation still takes for the area's own life (combat/policy.py `observe` knows the area, not
    the terror level, the player count or a Herald)."""
    bodies = tuple(replace(b, points=b.points * factor) for b in scenario.bodies)
    return replace(scenario, name=name, bodies=bodies, **wanted)


def meets(scenario: Scenario, result: Result) -> list[str]:
    """What a fight's result falls short of in the scenario's wanted outcome; empty when it meets it."""
    short = []
    if scenario.within is not None and (result.seconds is None or result.seconds > scenario.within):
        short.append(f'not dead within {scenario.within:g} s')
    if result.revivals > scenario.raised:
        short.append(f'{result.revivals} raised, {scenario.raised} allowed')
    if scenario.casts is not None and result.casts > scenario.casts:
        short.append(f'{result.casts} casts, {scenario.casts} allowed')
    return short


def wall(x0: float, y0: float, x1: float, y1: float) -> Callable[[Point], bool]:
    """A wall over the rectangle (x0, y0)-(x1, y1), in units from the character's starting place."""
    left, right = sorted((ORIGIN[0] + x0, ORIGIN[0] + x1))
    low, high = sorted((ORIGIN[1] + y0, ORIGIN[1] + y1))
    return lambda point: left <= point[0] <= right and low <= point[1] <= high


def walls(*parts: Callable[[Point], bool]) -> Callable[[Point], bool]:
    return lambda point: any(part(point) for part in parts)


def run(scenario: Scenario, fight: Fight, damage_of: Callable[[int], float] | None = None) -> Result:
    """The fight through the scenario, frame by frame: raises, the decision when the character is
    free, then the blades in flight. A blade's damage is the production table's (`damage_of`)."""
    damage_of = damage_of or damage_table()
    bodies = {b.unit: b for b in scenario.bodies}
    life = {b.unit: b.points for b in scenario.bodies}
    raisers = {r.unit: r for r in scenario.raisers}
    due = dict.fromkeys(raisers, 0)  # raiser -> the frame its next raise comes
    origin = ORIGIN
    busy_until = 0
    flights: list[tuple[int, list[list[Point]], set[tuple[int, str]], list[set[tuple[int, str]]]]] = []
    result = Result()

    def alive(unit: int) -> bool:
        return life[unit] > 0.0

    def corpses_of(raiser: Raiser) -> list[tuple[float, int]]:
        here = bodies[raiser.unit].at
        return sorted(
            (math.dist(here, bodies[unit].at), unit)
            for unit in raiser.raises
            if not alive(unit) and math.dist(here, bodies[unit].at) <= raiser.range
        )

    for frame in range(scenario.frames + 1):
        for unit, raiser in raisers.items():
            found = corpses_of(raiser) if alive(unit) else []
            if not found:
                due[unit] = frame + raiser.period  # nothing to raise: the wait starts at the next death
            elif frame >= due[unit]:
                risen = found[0][1]
                life[risen] = bodies[risen].points
                result.revivals += 1
                result.wasted += bodies[risen].points
                due[unit] = frame + raiser.period
        if not any(alive(unit) for unit in bodies):
            result.cleared_at = max(max(frames) for frames in result.deaths.values())
            break
        if frame >= busy_until:
            live = {unit: r for unit, r in raisers.items() if alive(unit)}
            foes = {
                # The game's observation knows a monster's type points and the share of life it shows.
                unit: Foe(b.txt, b.at, points_of(b.txt, scenario.area) * life[unit] / b.points, b.elite)
                for unit, b in bodies.items()
                if alive(unit)
            }
            seen = Observation(origin, foes, blocked=scenario.blocked, frame=frame)
            corpses = {unit: bodies[unit].at for r in live.values() for _, unit in corpses_of(r)}
            free = None if scenario.blocked is None else lambda point: not scenario.blocked(point)
            asked = fight(Brief(seen, live, corpses, free)) if foes else None
            if isinstance(asked, Move):
                origin = asked.to
                result.moves += 1
                busy_until = frame + MOVE_FRAMES
            elif asked is not None:
                at = origin
                paths = cast(at, asked.focal, lambda k, at=at: at, scenario.blocked)
                flights.append((frame + BIRTH_LAG, paths, set(), [set() for _ in paths]))
                result.casts += 1
                busy_until = frame + CAST_FRAMES
        for birth, paths, first, touched in flights:
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
                    dealt = damage_of(b.txt) * (DUPLICATE if key in first else 1.0)
                    first.add(key)
                    result.taken += min(dealt, life[unit])
                    life[unit] -= dealt
                    if not alive(unit):
                        result.deaths.setdefault(unit, []).append(frame)
    result.alive = tuple(unit for unit in bodies if alive(unit))
    return result


def today() -> Fight:
    """The aim the game's fight runs (the simulator's `live` candidate); it never moves the character."""
    aim = LiveAim(LinePolicy(yields=True), Viewport(ASPECT).reachable_focal)
    return lambda brief: aim(brief.seen)


def hittable(seen: Observation, at: Point, origin: Point | None = None, reach: float = REACH) -> bool:
    """Whether the blades reach a monster standing `at` from `origin`: in reach with a clear line."""
    origin = seen.origin if origin is None else origin
    return math.dist(origin, at) <= reach and clear_line(seen.blocked, origin, at)


def weighted(brief: Brief) -> Choice | None:
    """The production line sweep with the live revivers weighted REVIVER_WEIGHT and nothing else
    weighted: what a `reviver` flag on `Foe` would let `LinePolicy` do."""
    seen = brief.seen
    foes = {unit: replace(foe, elite=unit in brief.raisers) for unit, foe in seen.foes.items()}
    sweep = LiveAim(LinePolicy(yields=True, elite_weight=REVIVER_WEIGHT), Viewport(ASPECT).reachable_focal)
    return sweep(replace(seen, foes=foes))


def firing_spot(brief: Brief, target: Point) -> Point | None:
    """The spot nearest the character with a shot at `target`: within the hunt's reach, a clear line,
    on ground the character can stand on (the shape of macros/sight.py `firing_spots`)."""
    seen = brief.seen
    found = []
    for ring in SPOT_RINGS:
        for step in range(SPOT_BEARINGS):
            angle = 2 * math.pi * step / SPOT_BEARINGS
            spot = (target[0] + ring * math.cos(angle), target[1] + ring * math.sin(angle))
            if (brief.spots is None or brief.spots(spot)) and hittable(seen, target, spot, STRIKE_REACH):
                found.append((math.dist(seen.origin, spot), spot))
    return min(found)[1] if found else None


def common_line_spot(brief: Brief, first: Point, second: Point) -> Point | None:
    """A spot on the line through two monsters, beyond the nearer one, from which one cast takes both."""
    seen = brief.seen
    near, far = sorted((first, second), key=lambda at: math.dist(seen.origin, at))
    gap = math.dist(near, far) or 1.0
    ux, uy = (near[0] - far[0]) / gap, (near[1] - far[1]) / gap
    for back in (6.0, 4.0, 8.0):
        spot = (near[0] + ux * back, near[1] + uy * back)
        if back + gap > STRIKE_REACH or (brief.spots is not None and not brief.spots(spot)):
            continue
        if hittable(seen, far, spot, STRIKE_REACH):
            return spot
    return None


def in_one_line(origin: Point, first: Point, second: Point) -> bool:
    """Whether a cast through the nearer of two monsters passes the further one within the contact radius."""
    near, far = sorted((first, second), key=lambda at: math.dist(origin, at))
    away = math.dist(origin, near) or 1.0
    ux, uy = (near[0] - origin[0]) / away, (near[1] - origin[1]) / away
    along = (far[0] - origin[0]) * ux + (far[1] - origin[1]) * uy
    across = abs((far[0] - origin[0]) * uy - (far[1] - origin[1]) * ux)
    return 0 < along <= REACH and across <= CONTACT_RADIUS / 2


def covering(brief: Brief) -> list[Raiser]:
    """The live revivers with something to raise now or soon: a corpse or a live monster of theirs in range."""
    seen = brief.seen
    kept = []
    for raiser in brief.raisers.values():
        here = seen.foes[raiser.unit].at
        theirs = [
            brief.corpses.get(unit) or (seen.foes[unit].at if unit in seen.foes else None) for unit in raiser.raises
        ]
        if any(at is not None and math.dist(here, at) <= raiser.range for at in theirs):
            kept.append(raiser)
    return kept


def prototype(*, reposition: bool = False, hold: bool = False, line_up: bool = False) -> Fight:
    """The proposed changes, each on top of the weighted sweep: `reposition` moves to a spot with a
    shot when a live reviver covers the pack and no blade reaches it; `hold` casts at nothing a
    reviver no spot has a shot at would raise again; `line_up` moves onto the common line of two
    revivers that raise each other when no line takes both."""

    def fight(brief: Brief) -> Choice | Move | None:
        seen = brief.seen
        live = covering(brief)
        if not live:
            return weighted(brief)
        at = {raiser.unit: seen.foes[raiser.unit].at for raiser in live}
        mutual = [
            (a, b)
            for a in live
            for b in live
            if a.unit < b.unit and b.unit in a.raises and a.unit in b.raises
            and math.dist(at[a.unit], at[b.unit]) <= min(a.range, b.range)
        ]  # fmt: skip
        for a, b in mutual if line_up else ():
            if in_one_line(seen.origin, at[a.unit], at[b.unit]):
                continue
            spot = common_line_spot(brief, at[a.unit], at[b.unit])
            if spot is not None and math.dist(spot, seen.origin) > 1.0:
                return Move(spot)
        if any(hittable(seen, where) for where in at.values()):
            return weighted(brief)
        nearest = min(live, key=lambda raiser: math.dist(seen.origin, at[raiser.unit]))
        spot = firing_spot(brief, at[nearest.unit]) if reposition else None
        if spot is not None:
            return Move(spot)
        if not hold:
            return weighted(brief)
        # No shot at the reviver from anywhere: only what it cannot raise is worth a cast.
        lasting = {unit: foe for unit, foe in seen.foes.items() if not any(unit in r.raises for r in live)}
        lasting = {unit: foe for unit, foe in lasting.items() if hittable(seen, foe.at)}
        return weighted(replace(brief, seen=replace(seen, foes=lasting))) if lasting else None

    return fight


FIGHTS: dict[str, Callable[[], Fight]] = {
    'today': today,
    'flagged': prototype,  # proposal 1: the aim knows the revivers, the character never moves
    'reposition': lambda: prototype(reposition=True),  # and proposal 2
    'hold': lambda: prototype(reposition=True, hold=True),  # and proposal 3
    'reference': lambda: prototype(reposition=True, hold=True, line_up=True),  # and proposal 4: all of them
}
