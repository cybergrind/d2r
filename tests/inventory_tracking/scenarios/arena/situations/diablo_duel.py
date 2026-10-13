"""Diablo against one character, frame by frame, to compare ways of standing against his red lightning
(rca/2026-10-13/diablo.md section 5). Diablo is the simulator's (sim/diablo.py through sim/casters.py `Minds`: his
think, his stream, ring, wall and swings by the client's rules); the character is a stand-in of the Echoing Strike
Warlock as the recorded fights show it, and a **policy** chooses where it stands at each look.

The character [take unless said]: casts a strike of CAST_FRAMES (combat/stance.py CAST_SECONDS 0.36 s) whenever it
stands with Diablo within REACH (the blades' 22.1 units, builds' mechanics RANGE); each cast takes 1 / CASTS_TO_KILL
of his life (the median recorded fight, 8.0 s from his first sight to his death, spent striking: 22 casts); walks at
RUN_SPEED (20 units a second, combat/stance.py) once a cast under way is over; its mercenary and Defiler stand by it
(they draw 18 % of his thinks, sim/diablo.py CHARACTER_SHARE). Its resistances are the takes' main set (physical 10,
lightning and fire and cold 75 after the cap, magic 0), its life 1,818, its ward a physical pool of 185 (sim-casters.md
section 9) cast again WARD_AGAIN after it falls; no potion is drunk: a fight that takes more than the life is a death.

Policies (`POLICIES`):

- `today`: what the macro does now (the recordings' "Hold"): it stands and strikes; out of reach it walks at him;
- `priced`: at each look (every 0.12 s, macros/safety.py's cadence) the candidates are holding and the places across
  his line (combat/threats/diablo.py `escapes`, 4 and 8 units either side), each priced as the decision loop prices:
  the seconds it costs (the walk, during which nothing is struck) plus the life it costs (combat/threats/diablo.py
  `price` over the way, the stream under way with the missiles in flight, x KAPPA seconds a point: macros/safety's
  life price with potions on the belt, combat/harm.py `life_price`); the least wins. Nothing is a rule about Diablo:
  the price knows his stream and the arbiter picks the place;
- `priced, far`: the same with also places on his line at the blades' edge (FAR_STAND units off): there the flight
  is longest, so a stand lasts longest before the stream reaches it;
- `step at the cast` (a contrast, not the architecture's way): when his SC mode begins, a walk 8 units across, then
  strike again.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.diablo_duel [--seeds 20]
"""

import argparse
import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field

from inventory_tracking.combat.sim import diablo as rules
from inventory_tracking.combat.sim.monsters import Pack, Walker
from inventory_tracking.combat.threats import diablo as threat


Point = tuple[float, float]
LIFE = 1818.0  # the character's most life in the takes (hurt events: max_life 1818)
WARD = 185.0  # its ward's pool (sim-casters.md section 9)
WARD_AGAIN = 25  # frames after the pool falls until the macro has cast it again [take: "Psychic Ward" 0.4..1 s on]
STOPPED = {'physical': 0.10, 'lightning': 0.75, 'fire': 0.75, 'cold': 0.75, 'poison': 0.75, 'magic': 0.0}
REACH = 22.1  # units: the blades' range (builds/warlock/echoing_strike/mechanics.py RANGE)
CAST_FRAMES = 9  # combat/stance.py CAST_SECONDS 0.36 s
CASTS_TO_KILL = 22  # 8.0 s of striking (the median of the 19 recorded fights) / 0.36 s
STEP = 20.0 / 25  # units a frame walked (combat/stance.py RUN_SPEED)
LOOK = 3  # frames between looks (macros/safety.py: 0.12 s)
KAPPA = 4.0 / 480.0  # seconds a point of life (macros/safety.py settings: 4 s a potion of 480 points)
HOLD = 0.72  # seconds a hold is priced over (combat/harm.py SafetySettings.hold_dwell)
FAR_STAND = 21.0  # units: just inside the blades' range
START = 18.0  # units from him at the start (the recorded fights' first strikes: 15 to 21)
COMPANIONS = ((2.5, 2.0), (-2.0, 3.0))  # offsets of the mercenary and the Defiler from the character
SECONDS = 40  # the most a fight is played


@dataclass
class Fight:
    """One play: what it cost and how long it took."""

    seed: int
    policy: str
    killed_at: float | None = None
    died_at: float | None = None
    taken: dict[str, float] = field(default_factory=dict)  # points by source: 'lightning', 'wall', 'ring', 'melee'
    casts: int = 0
    moved: float = 0.0
    streams: int = 0

    @property
    def lost(self) -> float:
        return sum(self.taken.values())


SOURCES = {rules.LIGHTNING_MISSILE: 'lightning', rules.WALL_FLAME: 'wall', rules.RING_MISSILE: 'ring'}


class Duel:
    def __init__(self, seed: int, policy: str, casts_to_kill: int = CASTS_TO_KILL) -> None:
        self.seed, self.policy, self.casts_to_kill = seed, policy, casts_to_kill
        self.diablo = Walker(1, 243, 0.0, 0.0)
        self.pack = Pack([self.diablo], seed=seed)
        self.pack.minds.resists = dict(rules.CHARACTER_RESISTS)
        self.hero: Point = (START, 0.0)
        self.goal: Point | None = None  # where a walk goes
        self.casting = 0  # frames left of a strike under way
        self.pool, self.ward_back = WARD, -1
        self.sc_since: int | None = None
        self.looked = -LOOK
        self.stepped = 0  # the streams a step was made for (`step at the cast`)
        self.fight = Fight(seed, policy)
        self.life = 1.0  # Diablo's share left

    # -- the character ---------------------------------------------------------------------------------------------

    def bodies(self) -> list[Point]:
        return [self.hero, *((self.hero[0] + dx, self.hero[1] + dy) for dx, dy in COMPANIONS)]

    def stream(self) -> threat.Stream:
        flying = tuple(
            ((bolt.x, bolt.y), math.atan2(bolt.dy, bolt.dx))
            for bolt in self.pack.minds.bolts
            if bolt.missile == rules.LIGHTNING_MISSILE
        )
        return threat.Stream(self.diablo.at, self.sc_since, flying)

    def protection(self) -> threat.Protection:
        return threat.Protection(STOPPED, self.pool)

    def way_to(self, place: Point) -> threat.Way:
        gap = math.dist(self.hero, place)
        moving = gap / (STEP * 25)
        return threat.Way(((self.hero, self.casting / 25, 0.0), (place, moving, HOLD)))

    def choose(self, frame: int) -> Point | None:
        """The place to go to; None: hold here (and strike)."""
        d = math.dist(self.hero, self.diablo.at)
        if self.policy == 'today':
            return self._closer() if d > REACH else None
        if self.policy == 'step at the cast':
            if self.sc_since is not None and self.stepped < self.fight.streams:
                self.stepped = self.fight.streams
                return threat.escapes(self.diablo.at, self.hero, (8.0,))[frame % 2]
            if self.goal is not None:
                return self.goal
            return self._closer() if d > REACH else None
        kappa = KAPPA * life_factor(self.policy)
        stream, protection = self.stream(), self.protection()
        hold_way = threat.Way(((self.hero, self.casting / 25, HOLD),))
        options: list[tuple[float, Point | None]] = []
        reachable = d <= REACH
        hold_cost = kappa * threat.price(stream, hold_way, protection) + (0.0 if reachable else HOLD)
        options.append((hold_cost, None))
        places = threat.escapes(self.diablo.at, self.hero)
        if self.policy == 'priced, far' or not reachable:
            places += [self._on_ring(FAR_STAND, turn) for turn in (0.0, 0.35, -0.35)]
        for place in places:
            way = self.way_to(place)
            moving = math.dist(self.hero, place) / (STEP * 25)
            out = 0.0 if math.dist(place, self.diablo.at) <= REACH else HOLD
            options.append((moving + out + kappa * threat.price(stream, way, protection), place))
        return min(options, key=lambda option: option[0])[1]

    def _closer(self) -> Point:
        return self._on_ring(REACH - 2, 0.0)

    def _on_ring(self, radius: float, turn: float) -> Point:
        at = self.diablo.at
        angle = math.atan2(self.hero[1] - at[1], self.hero[0] - at[0]) + turn
        return (at[0] + radius * math.cos(angle), at[1] + radius * math.sin(angle))

    # -- a frame ---------------------------------------------------------------------------------------------------

    def frame(self, frame: int) -> None:
        mind = self.diablo.mind
        assert mind is not None
        if self.diablo.doing == 'cast' and mind.skill == 'DiabLight':
            self.sc_since = 0 if self.sc_since is None else self.sc_since + 1
        else:
            self.sc_since = None
        if self.sc_since == 0:
            self.fight.streams += 1
        for blow in self.pack.step(frame, self.bodies()):
            if blow.target != 0:
                continue
            source = SOURCES.get(blow.missile, 'melee' if blow.kind == 'melee' else 'other')
            points, self.pool = threat._through(blow.parts, threat.Protection(STOPPED), self.pool)
            self.fight.taken[source] = self.fight.taken.get(source, 0.0) + points
        if self.pool <= 0 and self.ward_back < 0:
            self.ward_back = frame + WARD_AGAIN
        if 0 <= self.ward_back <= frame:
            self.pool, self.ward_back = WARD, -1
        if self.fight.lost >= LIFE:
            self.fight.died_at = frame / 25
            return
        if self.casting:
            self.casting -= 1
            if not self.casting:
                self.fight.casts += 1
                self.life -= 1 / self.casts_to_kill
            return
        if frame - self.looked >= LOOK:
            # A look every LOOK frames; a strike under way puts the next one off to its end (the macro looks
            # meanwhile, but a walk does not begin before the cast is over).
            self.looked = frame
            self.goal = self.choose(frame)
        if self.goal is not None:
            gap = math.dist(self.hero, self.goal)
            step = min(STEP, gap)
            if gap > 1e-6:
                self.hero = (
                    self.hero[0] + (self.goal[0] - self.hero[0]) / gap * step,
                    self.hero[1] + (self.goal[1] - self.hero[1]) / gap * step,
                )
                self.fight.moved += step
            if gap <= STEP:
                self.goal = None
            return
        if math.dist(self.hero, self.diablo.at) <= REACH:
            self.casting = CAST_FRAMES

    def play(self) -> Fight:
        for frame in range(SECONDS * 25):
            self.frame(frame)
            if self.fight.died_at is not None:
                break
            if self.life <= 1e-9:
                self.fight.killed_at = frame / 25
                break
        return self.fight


POLICIES = ('today', 'priced', 'priced, far', 'priced, life x10', 'step at the cast')
# The life price's factor swept (`--factors`): the dial between "no damage" and "fastest" (combat/harm.py
# SafetySettings.dear: the factor the decision loop puts on life while a dear boss is in the fight).
FACTORS = (2.0, 3.0, 5.0, 10.0, 20.0)


def life_factor(policy: str) -> float:
    """The factor a `priced, life xN` policy puts on KAPPA; 1 for the others."""
    head, _, factor = policy.rpartition('life x')
    return float(factor) if head else 1.0


def compare(
    seeds: range, policies: tuple[str, ...] = POLICIES, casts_to_kill: int = CASTS_TO_KILL
) -> dict[str, list[Fight]]:
    return {policy: [Duel(seed, policy, casts_to_kill).play() for seed in seeds] for policy in policies}


def summary(found: dict[str, list[Fight]]) -> list[str]:
    lines = [
        '| policy | lightning lost: mean / median / most | all lost: mean | kill s: mean / median / most | deaths '
        '| streams a fight | moved |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for policy, fights in found.items():
        light = [f.taken.get('lightning', 0.0) for f in fights]
        kills = [f.killed_at for f in fights if f.killed_at is not None]
        lines.append(
            f'| {policy} | {statistics.mean(light):.0f} / {statistics.median(light):.0f} / {max(light):.0f} '
            f'| {statistics.mean(f.lost for f in fights):.0f} '
            f'| {statistics.mean(kills):.1f} / {statistics.median(kills):.1f} / {max(kills):.1f} '
            f'| {sum(f.died_at is not None for f in fights)} / {len(fights)} '
            f'| {statistics.mean(f.streams for f in fights):.1f} | {statistics.mean(f.moved for f in fights):.0f} |'
            if kills
            else f'| {policy} | {statistics.mean(light):.0f} | - | never | - | - | - |'
        )
    return lines


def main(argv: list[str] | None = None, out: Callable[[str], None] = print) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--seeds', type=int, default=20)
    parser.add_argument('--factors', action='store_true', help='sweep the life price factor (FACTORS) instead')
    args = parser.parse_args(argv)
    policies = ('today', 'priced', *(f'priced, life x{f:g}' for f in FACTORS)) if args.factors else POLICIES
    for kill in (CASTS_TO_KILL, 2 * CASTS_TO_KILL):
        out(
            f'\nDiablo dies after {kill} strikes ({kill * CAST_FRAMES / 25:.1f} s of striking), '
            f'seeds 1..{args.seeds}:\n'
        )
        for line in summary(compare(range(1, args.seeds + 1), policies, casts_to_kill=kill)):
            out(line)


if __name__ == '__main__':
    main()
