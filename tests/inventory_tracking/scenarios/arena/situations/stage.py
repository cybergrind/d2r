"""The arena with what a situation needs on top (game.py `Arena`, mobs.py `Mobs`), all of it on the test's side.

`Arena` answers one question of a play: how much life went. A situation asks who took it, lets a pack appear
in the middle of a play and says how far a monster notices the character. `Cast` is `Mobs` with those three,
roll for roll the same monsters when none of them is used (test_situations.py plays the Vizier's moment
through kp4.py and through here and compares):

- **who hurt** (`Cast.hurts`): `Mobs.tick` gives a tick's sum; here each blow that took life is kept with its
  monster's type, its kind (a swing, a shot, a spark, a nova, an exploding corpse) and its points after the
  resistances. `tick` is `Mobs.tick` line for line with that record added, so the block's rolls fall the same;
- **a monster that appears** (`Cast.spawn`): a walker put into the pack while it plays, with its own rolls as
  the pack gives a monster its own (`Pack.__init__`: one generator per unit), a shooter with its shot. The
  arena has no seal boss; a situation scripts one (`Stage.spawns`);
- **awareness** (`aware`, units): combat/sim/monsters.py has it as the constant AWARE (20; the game's own
  radius is 35 sub-tiles, rca/2026-10-13/re/notes-ai.md). It cannot be given to a `Pack`, so for a play it is
  the module's constant changed and put back (`awareness`), which every monster of the play then thinks by; a
  shooter (it wakes within SHOT_REACH, 30) is woken when the character or a companion is within `aware` of it.
  The seam production code needs: `Pack(aware=...)`, read in `_think`, `_target` and `_shoot`;
- **a shot that lands** (`lands`: type -> the chance): a shooter's missile that arrives under the character
  takes life with the fitted chance, 0.024 pooled, one character's arrows and bolts over all types
  (combat/sim/monsters.py "Shooting"). The takes hold no Gloam, Burning Soul or Black Soul, whose lightning is
  what kills in the game, so a situation may say its own chance for a type: the missile is rolled again from
  a stream of this file's (the pack's rolls stay as they are). An assumption wherever it is used, and named
  as one in every table made with it.

`Stage` is the `Arena` with that cast, the scripted spawns and curses played at their times, and a sample of
the play at every tick (`Stage.ticks`) for the situation's result.
"""

import math
import random
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from inventory_tracking.combat.sim import monsters as model
from inventory_tracking.combat.sim.monsters import MELEE
from inventory_tracking.config import HealingConfig
from inventory_tracking.macros.world import NO_OWNER
from inventory_tracking.native.layout import DEAD_MODES
from tests.inventory_tracking.scenarios.arena.game import BLOCK_CHANCE, Arena, Flight
from tests.inventory_tracking.scenarios.arena.mobs import BLAST_KIND, Mobs, explodes
from tests.inventory_tracking.scenarios.arena.scene import Mob, Scene
from tests.inventory_tracking.scenarios.threat.harness import BLAST, BLAST_RADIUS


Point = tuple[float, float]
ARENA_AWARE = model.AWARE  # units: what the monster model has (20)
GAME_AWARE = 35.0  # units (sub-tiles): the client's own radius (rca/2026-10-13/re/notes-ai.md)
EVERYONE = 10_000.0  # units: every monster of the scene knows of the character from the first tick
BLAST_BLOW = 'blast'  # the kind of a blow that is an exploding corpse (the others are sim.monsters')
CROWD = 12.0  # units: the hostiles within this of the character are counted at every tick


@contextmanager
def awareness(units: float) -> Iterator[None]:
    """combat/sim/monsters.py AWARE as `units` while the block runs (the module text has why it is done so)."""
    saved = model.AWARE
    model.AWARE = units
    try:
        yield
    finally:
        model.AWARE = saved


@dataclass(frozen=True)
class Hurt:
    """Life a monster took off the character: `at` seconds, the monster's type, the blow's kind, the points, and the
    missile (missiles.txt) of a caster's blow (0: none)."""

    at: float
    unit: int
    txt: int
    kind: str
    points: float
    missile: int = 0


@dataclass
class Spawn:
    """Monsters that appear during a play: at `at` seconds, or `delay` seconds after the object `after` (a
    `Prop`'s unit id) was operated in this play. `done`: they are there."""

    mobs: list[Mob]
    at: float | None = None
    after: int | None = None
    delay: float = 0.0
    label: str = ''
    due: float | None = field(default=None, compare=False)
    done: bool = field(default=False, compare=False)


class Cast(Mobs):
    """`Mobs` that says who hurt, takes newcomers and has its awareness and its shots' chances given."""

    def __init__(
        self,
        scene: Scene,
        rng: random.Random,
        auras: Mapping[int, float] | None = None,
        *,
        seed: int = 1,
        aware: float = ARENA_AWARE,
        lands: Mapping[int, float] | None = None,
    ) -> None:
        super().__init__(scene, rng, auras)
        self.seed, self.aware = seed, aware
        self.lands = dict(lands or {})
        self.land_rng = random.Random(seed * 7_919 + 13)  # this file's stream: the pack's rolls are not touched
        self.rolled: set[int] = set()  # the missiles (by identity) whose chance was already rolled again
        self.hurts: list[Hurt] = []
        # The blows on the character's companions (the mercenary, the Defiler), in raw points: the arena's companions
        # lose no life, so this is what they would have taken before their own resistances.
        self.mates: list[Hurt] = []
        self.burst: list[tuple[Point, int, int]] = []  # the exploding corpses of `blasts`: place, unit, type
        # every missile a shooter let go: (the frame, the frame it lands at, from, to, at the character, it takes life)
        self.shots: list[tuple[int, int, Point, Point, bool, bool]] = []
        self.flown = 0  # of the pack's casters' missiles gone (`Minds.flown`), those already in `shots`

    def hit(self, unit: int, points: float) -> bool:
        died = super().hit(unit, points)
        mob = self.mobs.get(unit)
        if died and mob is not None and explodes(mob.txt):
            self.burst.append((mob.at, unit, mob.txt))
        return died

    def tick(self, hero_at: Point, companions: Sequence[Point], resist: Mapping[str, float]) -> float:
        """`Mobs.tick`, each blow that took life kept in `hurts` (the module text)."""
        now = self.frame / model.GAME_RATE
        if self.aware > model.SHOT_REACH:
            bodies = [hero_at, *companions]
            for unit in self.pack.shots:
                walker = self.pack.walkers.get(unit)
                if walker is not None and min(math.dist(walker.at, body) for body in bodies) <= self.aware:
                    self.pack.awake.add(unit)
        found = self.pack.step(self.frame, [hero_at, *companions])
        self.raised()
        stopped = self.stopped(resist)
        taken = 0.0
        for at, unit, txt in self.burst:
            if math.dist(at, hero_at) <= BLAST_RADIUS:
                points = BLAST * (1.0 - stopped.get(BLAST_KIND, 0.0))
                taken += points
                self.hurts.append(Hurt(now, unit, txt, BLAST_BLOW, points))
        self.blasts, self.burst = [], []
        for blow in found:
            if blow.target == 0 and blow.kind == MELEE and self.block_rng.random() < self.block_chance:
                self.blocked += 1
            elif blow.target == 0:
                points = self.landed(blow, stopped)
                taken += points
                mob = self.mobs.get(blow.unit)
                self.hurts.append(Hurt(now, blow.unit, mob.txt if mob else -1, blow.kind, points, blow.missile))
            else:
                mob = self.mobs.get(blow.unit)
                self.mates.append(Hurt(now, blow.unit, mob.txt if mob else -1, blow.kind, blow.damage, blow.missile))
        self.reroll()
        # A caster's missiles and curses (sim/casters.py) as the shooters' are kept: (let go, gone, from, to, at the
        # character, took life there).
        flown = self.pack.minds.flown
        self.shots += flown[self.flown :]
        self.flown = len(flown)
        for unit, walker in self.pack.walkers.items():
            self.mobs[unit].at = walker.at
        self.frame += 1
        return taken

    def reroll(self) -> None:
        """The missiles let go this tick: each kept in `shots`, and one sent at the character by a type with a
        chance of its own (`lands`) rolled again."""
        flying = self.pack.flying
        for index, missile in enumerate(flying):
            if id(missile) in self.rolled:
                continue
            mob = self.mobs.get(missile.unit)
            chance = self.lands.get(mob.txt) if mob is not None and missile.target == 0 else None
            if chance is not None:
                missile = flying[index] = replace(missile, takes=self.land_rng.random() < chance)
            self.rolled.add(id(missile))
            if mob is not None:
                self.shots.append((self.frame, missile.lands, mob.at, missile.at, missile.target == 0, missile.takes))
        self.rolled &= {id(missile) for missile in flying}


@dataclass(frozen=True)
class Tick:
    """The play at one tick: the character's place and life, the hostiles alive and how many within CROWD,
    the strikes begun so far."""

    at: float
    here: Point
    life: float
    alive: int
    crowd: int
    casts: int


class Stage(Arena):
    """`Arena` with a `Cast`, scripted `spawns` and `curses` ((seconds, kind of damage, the share let through
    from then on), as incident.py has them), and the play sampled at every tick."""

    def __init__(
        self,
        scene: Scene,
        *,
        seed: int = 1,
        osd: HealingConfig | None = None,
        spawns: Sequence[Spawn] = (),
        curses: Sequence[tuple[float, str, float]] = (),
        aware: float = ARENA_AWARE,
        lands: Mapping[int, float] | None = None,
        watch: Sequence[int] = (),
    ) -> None:
        super().__init__(scene, seed=seed, osd=osd)
        # The same monsters again, as `Arena.__init__` made them, in a `Cast`.
        self.cast = Cast(self.scene, random.Random(seed), None, seed=seed, aware=aware, lands=lands)
        self.mobs = self.cast
        self.mobs.block_chance = BLOCK_CHANCE
        self.mobs.guard = self.guard  # the character's guard, as `Arena.__init__` gave the first ones
        self.world = replace(self.world, monsters=tuple(m for m in self.mobs.monsters() if m.mode not in DEAD_MODES))
        self.show()
        self.spawns = [replace(spawn, mobs=[replace(mob) for mob in spawn.mobs]) for spawn in spawns]
        self.curses = sorted(curses)
        self.watch = tuple(watch)  # units whose distance to the character is kept at every tick
        self.ticks: list[Tick] = []
        self.gaps: dict[int, list[tuple[float, float]]] = {unit: [] for unit in self.watch}
        self.fell: dict[int, float] = {}  # unit -> when it died
        self.picks: list[tuple[float, str]] = []
        self.appeared: list[tuple[float, str, int]] = []  # (seconds, the spawn's label, how many)
        self.opened: dict[int, float] = {}  # an object's unit -> when it was operated
        self.struck: list[
            tuple[int, Point, Point, Flight | None]
        ] = []  # a strike: the tick, from, the focal point, its flight

    def strike(self) -> None:
        origin, focal, flying = self.here, self.ground_under_pointer(), len(self.flights)
        super().strike()
        flight = self.flights[-1] if len(self.flights) > flying else None
        self.struck.append((self.time.ticks, origin, focal, flight))

    def companions(self) -> list[Point]:
        return [(m.x, m.y) for m in self.world.monsters if m.ally or m.owner != NO_OWNER]

    def play_tick(self) -> None:
        now = self.clock.now
        while self.curses and self.curses[0][0] <= now + 1e-9:
            _, kind, share = self.curses.pop(0)
            for resist in self.resists:
                resist[kind] = share
        for thing in self.things:
            if thing.mode and thing.unit_id not in self.opened:
                self.opened[thing.unit_id] = now
        for spawn in self.spawns:
            if spawn.done:
                continue
            if spawn.due is None:
                spawn.due = spawn.at if spawn.after is None else self.opened.get(spawn.after)
                if spawn.due is not None and spawn.after is not None:
                    spawn.due = max(spawn.due, 0.0) + spawn.delay
            if spawn.due is not None and spawn.due <= now + 1e-9:
                for mob in spawn.mobs:
                    self.cast.spawn(mob)
                spawn.done, self.cleared_at = True, None
                self.appeared.append((now, spawn.label, len(spawn.mobs)))
        killed, taken = len(self.kills), len(self.picked)
        super().play_tick()
        for unit in self.kills[killed:]:
            self.fell[unit] = now
        self.picks.extend((now, label) for label in self.picked[taken:])
        here, mobs = self.here, self.mobs
        live = [mobs.mobs[unit].at for unit in mobs.live()]
        self.ticks.append(
            Tick(now, here, self.life, len(live), sum(1 for at in live if math.dist(at, here) <= CROWD), self.casts)
        )
        alive = set(mobs.live())
        for unit in self.watch:
            if unit in alive:
                self.gaps[unit].append((now, math.dist(here, mobs.mobs[unit].at)))
