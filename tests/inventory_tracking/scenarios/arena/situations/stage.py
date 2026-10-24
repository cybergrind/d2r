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

Three things a scene cut from a take of 2026-10-21 needs and the arena did not play (rca/2026-10-21/
fane-death-sim-findings.md), each off unless a situation asks for it, so every scene fitted before plays as it did:

- **Battle Orders** (`Orders`): up from the start and run out at `ends` (the take's moment), the most life and the life
  divided by `factor` then (the share kept, as the game: 2943 -> 1896 at 57% on 2026-10-21); its state is the
  character's `battle_orders`, which macros/cta.py reads. A Battle Orders key (macros/fakes.py KEYS) with the Call to
  Arms in hand (`CTA_CODE` among the codes in hand) casts it: at the cast's end it is up again for `lasts`, the most
  life and the life raised by `factor` if it had run out. The run is told a Call to Arms is worn (`Run.cta`) and keeps
  the casts that took across runs (`Run.lasting`, the runner's in the game), `cast_at` being the last one the macro
  knows (None: not known, as after a service restart). Battle Command is not played;
- **Teleport of the character's own** (`own_teleport`, Enigma): the run reads it (`Run.own_teleport`); with no staff
  in the scene's sets and Teleport on a key the arena casts it without charges (game.py `hop`);
- **the hops**: each Teleport cast is kept (`hops`: the clock, from, to) with the aims refused for no footing
  (game.py `refused`), so a play shows where its escapes landed.
- **the auras known** (`auras`: unit -> the factor on the others' blows, mobs.py `Mobs`): a take whose states say which
  aura each Aura Enchanted unique had gives them; left out, each has mobs.py AURA_FACTOR (Might) as before;
- **blows at the game's most** (`capped`, mobs.py `Mobs.bounded`): each melee blow cut at its monster's most, before
  the auras and the curses;
- **the game's chance to hit** (`defence`: the character's defence and level, mobs.py `Mobs.landing`, with the pack's
  swings made sure by `sure_swings` while the play runs) and **the character's block** (`block`, the take's stat 20);
- **types played hand to hand** (`melee`): mobs.py plays a type the threat table calls ranged as a shooter and
  never as a striker; a take that shows one striking in melee (the Night Lords of the Fane, 23:35:27-28: 234, 207 and
  436 at 2.9 units) names its type here, and its walkers strike as the melee types do (`Cast.hand_to_hand`), with no
  shot.
"""

import math
import random
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from inventory_tracking.builds.warlock.buffs import SIGIL_RADIUS
from inventory_tracking.combat.sim import monsters as model
from inventory_tracking.combat.sim.monsters import MELEE
from inventory_tracking.config import HealingConfig
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.memory import CTA_CODE
from inventory_tracking.levels.geometry import Point
from inventory_tracking.macros.cta import BATTLE_ORDERS, ORDERS_LASTS
from inventory_tracking.macros.engine import Run
from inventory_tracking.native.layout import DEAD_MODES
from inventory_tracking.takes.timeline import GAME_RATE
from tests.inventory_tracking.macros.fakes import KEYS
from tests.inventory_tracking.scenarios.arena.game import BLOCK_CHANCE, SIGIL_STATE_SHOWS, Arena, Flight
from tests.inventory_tracking.scenarios.arena.mobs import BLAST_KIND, Mobs, explodes
from tests.inventory_tracking.scenarios.arena.scene import Mob, Scene
from tests.inventory_tracking.scenarios.threat.harness import BLAST, BLAST_RADIUS


ARENA_AWARE = model.AWARE  # units: what the monster model has (20)
GAME_AWARE = 35.0  # units (sub-tiles): the client's own radius (rca/2026-10-13/re/notes-ai.md)
EVERYONE = 10_000.0  # units: every monster of the scene knows of the character from the first tick
BLAST_BLOW = 'blast'  # the kind of a blow that is an exploding corpse (the others are sim.monsters')
CROWD = 12.0  # units: the hostiles within this of the character are counted at every tick
CLOSE = 5.0  # units: the hostiles this near are counted too (the findings' "3 within 5": surrounded)


@contextmanager
def awareness(units: float) -> Generator[None]:
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


@dataclass(frozen=True)
class Orders:
    """Battle Orders on the character (the module text): it runs out `ends` seconds into the play unless cast again;
    `factor` is the most life with it over the most life without; a cast lasts `lasts`; `cast_at` is the play's clock
    of the last cast the macro knows (None: not known). `up` False: not on at the start (the scene's life is without
    it, `ends` is not used), for the macro to cast."""

    ends: float
    factor: float
    lasts: float = ORDERS_LASTS
    cast_at: float | None = None
    up: bool = True


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


class ReadLife:
    """The arena as the OSD healer sees it with `life_read`: the client's life (`Stage.client_life`), the rest as is."""

    def __init__(self, stage: Stage) -> None:
        self.stage = stage

    @property
    def life(self) -> float:
        return self.stage.client_life()

    def __getattr__(self, name: str):
        return getattr(self.stage, name)


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
        self.melee: frozenset[int] = frozenset()  # types played hand to hand (`hand_to_hand`)
        self.speeds: dict[int, float] = {}  # units a second by type (`paced`)
        self.rolled: set[int] = set()  # the missiles (by identity) whose chance was already rolled again
        self.hurts: list[Hurt] = []
        # The blows on the character's companions (the mercenary, the Defiler), in raw points: the arena's companions
        # lose no life, so this is what they would have taken before their own resistances.
        self.mates: list[Hurt] = []
        self.burst: list[tuple[Point, int, int]] = []  # the exploding corpses of `blasts`: place, unit, type
        # every missile a shooter let go: (the frame, the frame it lands at, from, to, at the character, it takes life)
        self.shots: list[tuple[int, int, Point, Point, bool, bool]] = []
        self.flown = 0  # of the pack's casters' missiles gone (`Minds.flown`), those already in `shots`

    def paced(self, speeds: Mapping[int, float]) -> None:
        """Walkers of the types named move at those units a second (the takes' measured pace, `speeds`)."""
        for walker in self.pack.walkers.values():
            if walker.txt in speeds:
                walker.traits = replace(walker.traits, speed=speeds[walker.txt] / GAME_RATE)
        self.speeds = dict(speeds)

    def hand_to_hand(self, types: Sequence[int]) -> None:
        """The walkers of `types` strike in melee and shoot nothing (the module text), now and when they appear."""
        self.melee = frozenset(types)
        for unit, walker in self.pack.walkers.items():
            if walker.txt in self.melee:
                walker.traits = replace(walker.traits, melee=True)
                self.pack.shots.pop(unit, None)

    def spawn(self, mob: Mob, seed: int | None = None) -> None:
        super().spawn(mob, seed)
        walker = self.pack.walkers.get(mob.unit)
        if walker is not None and walker.txt in self.speeds:
            walker.traits = replace(walker.traits, speed=self.speeds[walker.txt] / GAME_RATE)
        if walker is not None and walker.txt in self.melee:
            walker.traits = replace(walker.traits, melee=True)
            self.pack.shots.pop(mob.unit, None)

    def hit(self, unit: int, points: float, *, by_pet: bool = False) -> bool:
        died = super().hit(unit, points, by_pet=by_pet)
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
        found = self.struck(self.pack.step(self.frame, [hero_at, *companions]), hero_at)
        self.raised()
        stopped = self.stopped(resist)
        taken = 0.0
        for at, unit, txt in self.burst:
            if math.dist(at, hero_at) <= BLAST_RADIUS:
                points = BLAST * (1.0 - stopped.get(BLAST_KIND, 0.0))
                taken += points
                self.hurts.append(Hurt(now, unit, txt, BLAST_BLOW, points))
        self.blasts, self.burst = [], []
        self.mate_blows = [(blow.target - 1, blow.damage) for blow in found if blow.target > 0]
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
    the strikes begun so far; how many hostiles stand within CLOSE of the character, go for it and go for one of its
    companions (the walkers' `aim`: rca/2026-10-21/herald-fight-findings.md §1.4 read the same from the path records),
    and stand in the character's sigil (within SIGIL_RADIUS of it while its state shows)."""

    at: float
    here: Point
    life: float
    alive: int
    crowd: int
    casts: int
    close: int = 0
    on_hero: int = 0
    on_mates: int = 0
    sigiled: int = 0
    nearest: float = math.inf  # units to the nearest live hostile


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
        rules: Sequence[str] = (),
        orders: Orders | None = None,
        own_teleport: bool | None = None,
        melee: Sequence[int] = (),
        auras: Mapping[int, float] | None = None,
        capped: bool = False,
        defence: tuple[float, int] | None = None,
        block: float | None = None,
        speeds: Mapping[int, float] | None = None,
        life_read: float | None = None,
        damage_percent: Mapping[int, Sequence[tuple[float, float]]] | None = None,
    ) -> None:
        # The life the macro and the healer read (`life_read`): the client's, refreshed every `life_read` s and at once
        # on a blow that staggers; None: the life of the tick, as before
        self.life_read = life_read
        self.read_life: float | None = None
        self.read_at = 0.0
        self.read_staggers = 0
        super().__init__(scene, seed=seed, osd=osd, rules=rules, auras=auras)
        # The same monsters again, as `Arena.__init__` made them, in a `Cast`.
        self.cast = Cast(self.scene, random.Random(seed), auras, seed=seed, aware=aware, lands=lands)
        self.mobs = self.cast
        self.mobs.block_chance = BLOCK_CHANCE
        self.mobs.guard = self.guard  # the character's guard, as `Arena.__init__` gave the first ones
        if melee:
            self.cast.hand_to_hand(melee)
        self.cast.capped = capped
        self.cast.defence = defence
        if block is not None:
            self.mobs.block_chance = block
        if speeds:
            self.cast.paced(speeds)
        if damage_percent is not None:
            self.cast.damage_percent = {unit: [tuple(row) for row in rows] for unit, rows in damage_percent.items()}
        if life_read is not None and self.healer is not None:
            self.healer.arena = ReadLife(self)  # type: ignore[assignment]
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
        self.hops: list[tuple[float, Point, Point]] = []  # each Teleport cast: the clock, from, the landing
        self.own_teleport = own_teleport
        # Battle Orders (`Orders`): whether it is up, when it runs out, when a cast of it ends; the casts that took
        # (`Run.lasting`) and what became of it: (the clock, 'ran out' or 'cast')
        self.orders = orders
        self.orders_up = orders is not None and orders.up
        self.orders_until = math.inf if orders is None or not orders.up else orders.ends
        self.orders_due: float | None = None
        self.lasting: dict[int, float] = {}
        self.orders_log: list[tuple[float, str]] = []
        if orders is not None:
            if orders.cast_at is not None:
                self.lasting[BATTLE_ORDERS] = orders.cast_at
            self.shows_orders(orders.up)

    def strike(self) -> None:
        origin, focal, flying = self.here, self.ground_under_pointer(), len(self.flights)
        super().strike()
        flight = self.flights[-1] if len(self.flights) > flying else None
        self.struck.append((self.time.ticks, origin, focal, flight))

    def companions(self) -> list[Point]:
        return [(m.x, m.y) for m in self.world.monsters if m.ally or m.owner != NO_OWNER]

    def run(self, seed: int = 1) -> Run:
        run = super().run(seed)
        if self.own_teleport is not None:
            own = self.own_teleport
            run.own_teleport = lambda: own
        if self.orders is not None:
            run.cta = lambda: True
            run.lasting = self.lasting
        return run

    def hop(self) -> None:
        before, landing = self.here, self.landing
        super().hop()
        if self.landing is not None and self.landing is not landing:
            self.hops.append((self.clock.now, before, self.landing.spot))

    def act(self, event: tuple) -> None:
        key = event[1] if event[0] == 'key' else None
        held = CTA_CODE in self.sets[0]
        super().act(event)
        if self.orders is not None and self.over is None and key == KEYS[BATTLE_ORDERS] and held:
            self.orders_due = self.clock.now if self.acting_until is None else self.acting_until

    def shows_orders(self, up: bool) -> None:
        stand = self.world.player
        if stand is not None:
            self.world = replace(self.world, player=replace(stand, battle_orders=up))

    def show(self) -> None:
        """`Arena.show`; with the character's defence and level given (`defence`), the stats the macro reads carry
        them (31, 12) in place of the arena's own (771 at 94), as the live loot read would."""
        super().show()
        cast = getattr(self, 'cast', None)  # `Arena.__init__` shows the world before the cast is made
        if cast is not None and cast.defence is not None:
            defence, level = cast.defence
            stats = {**dict(self.loot.stats), 31: round(defence), 12: level}
            self.loot = replace(self.loot, stats=tuple(stats.items()))
        if self.life_read is not None and self.dead_at is None:
            self.loot = replace(self.loot, life=max(round(self.client_life()), 1))

    def client_life(self) -> float:
        """The life as the client holds it (`life_read`, 2026-10-22, rca/2026-10-21/fane-death-sim-findings.md §7): the
        frames of the takes of 2026-10-20 to 22 change it every 0.4 s (70% of 35,798 changes 0.36-0.46 s apart, 1%
        under 0.3), and at once on a blow of hit recovery (the Fane's 436, 324 and 804 came off that beat, its 234 and
        207 on it). Here: refreshed on that beat from the play's start, at a stagger, and never over the most life."""
        step = self.life_read
        assert step is not None
        now = self.clock.now
        staggers = getattr(self, 'staggers', 0)
        if self.read_life is None or int(now / step) > int(self.read_at / step) or staggers != self.read_staggers:
            self.read_life, self.read_at, self.read_staggers = self.life, now, staggers
        return min(self.read_life, self.max_life)

    def keep_orders(self, now: float) -> None:
        """Battle Orders at this tick (the module text): a cast that ended puts it up again, its end runs it out."""
        orders = self.orders
        assert orders is not None
        if self.orders_due is not None and self.orders_due <= now + 1e-9:
            self.orders_due = None
            if not self.orders_up:
                self.max_life *= orders.factor
                self.life *= orders.factor
            self.orders_up, self.orders_until = True, now + orders.lasts
            self.orders_log.append((now, 'cast'))
            self.shows_orders(True)
        if self.orders_up and now >= self.orders_until - 1e-9:
            self.orders_up = False
            self.max_life /= orders.factor
            self.life /= orders.factor
            self.orders_log.append((now, 'ran out'))
            self.shows_orders(False)

    def play_tick(self) -> None:
        now = self.clock.now
        if self.orders is not None and self.over is None:
            self.keep_orders(now)
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
        units = mobs.live()
        live = [mobs.mobs[unit].at for unit in units]
        aims = [mobs.pack.walkers[unit].aim for unit in units if unit in mobs.pack.walkers]
        sigil = self.sigil_lying(SIGIL_STATE_SHOWS)
        crowd = sum(1 for at in live if math.dist(at, here) <= CROWD)
        sampled = Tick(
            now, here, self.life, len(live), crowd, self.casts,
            close=sum(1 for at in live if math.dist(at, here) <= CLOSE),
            on_hero=sum(1 for aim in aims if aim == 0),
            on_mates=sum(1 for aim in aims if aim > 0),
            sigiled=0 if sigil is None else sum(1 for at in live if math.dist(at, sigil) <= SIGIL_RADIUS),
            nearest=min((math.dist(at, here) for at in live), default=math.inf),
        )  # fmt: skip
        self.ticks.append(sampled)
        alive = set(mobs.live())
        for unit in self.watch:
            if unit in alive:
                self.gaps[unit].append((now, math.dist(here, mobs.mobs[unit].at)))
