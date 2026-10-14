"""The monsters of the arena: combat/sim/monsters.py made to answer to walls, lines of sight, blasts and
auras (framework-plan.md, Task 1.2; architecture.md §6).

`Mobs` holds a scene's monsters and plays them a game tick at a time against where the character is
now. The monsters are `sim.monsters` walkers in its `Pack`, as that module has them since its refit
to the takes (its module text): the think cycle, a swing with its rest, the chance that a swing that
ran out or a shot takes life, the stagger of a monster the character strikes, whom a monster goes
for, the blows by rank, enchantment and Herald tier and their spread, a shooter's cycle with its
missile in flight, the sparks of a Lightning Enchanted one, the nova of a Cold Enchanted elite's
death. The shooter's cycle was this file's own (one landed shot a second) and moved there with the
refit. `Horde` is that pack with what it lacks:

- walls: a walk whose straight line is barred (combat/stance.py `no_footing` over the scene's grids
  and closed doors) goes by macros/travel.py `walked_way`; with no way the monster stands. With no
  ground in the scene a walk is the pack's own straight line, roll for roll;
- lines of sight: a shooter lets a missile go only while macros/sight.py `clear_shot` holds, and
  closes round the walls when it has lost the reach or the line. A missile in the air is not stopped
  by a wall (the fit's chance that a missile ends on the character has the walls of the takes in it).

`Mobs` says which monsters shoot and what (the threat table's `ranged` and its points a shot; the
types the takes show shooting that the table does not call ranged) and adds what is not a monster's
own move: an exploding corpse (the table's `death_damage`) deals BLAST to a character within
BLAST_RADIUS, and a live monster with a damage aura raises the blows of the others within BOOST_RANGE.

What is this file's own assumption, not a table's or a take's, is named where it is set: the points
of a shot, the kind of a blast, which aura an Aura Enchanted monster has, that a type nothing calls a
shooter fights hand to hand.

Not modelled, as in `sim.monsters`: fleeing, bodies in each other's way, damage that is no blow. A
companion of the character's stands where the scene has it and is never hurt; the companions a
monster goes for are the places `tick` is given.
"""

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import replace

from inventory_tracking.combat import threats
from inventory_tracking.combat.mechanics.tables import points_of, tables
from inventory_tracking.combat.sim import casters
from inventory_tracking.combat.sim.casters import resisted
from inventory_tracking.combat.sim.guard import Guard
from inventory_tracking.combat.sim.monsters import (
    MELEE,
    PHYSICAL,
    SHOT,
    SHOT_REACH,
    STAND,
    Blow,
    Pack,
    Walker,
    boost,
    shoots,
)
from inventory_tracking.combat.stance import WAY_SAMPLE, no_footing
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.travel import walked_way
from inventory_tracking.macros.world import LYING_DEAD, NO_OWNER, Monster
from inventory_tracking.terror.danger import DANGER, MIGHT
from tests.inventory_tracking.scenarios.arena.scene import Mob, Scene

# The threat scenarios' numbers, used here as they are there (framework-plan.md has them moved to this
# file; scenarios/threat/harness.py is left alone by this task, so they are imported, not copied):
# BOOST_RANGE 16, Might's range at level 1 (terror/data/threats.json auras); BLAST_RADIUS 4 and BLAST
# 450 points, both that file's assumptions (the takes hold too few exploding corpses to refit them).
from tests.inventory_tracking.scenarios.threat.harness import BLAST, BLAST_RADIUS, BOOST_RANGE
from tests.inventory_tracking.scenarios.threat.table import table


# monmode.txt: the client's modes of a monster's strikes and casts (macros/world.py STRIKING_MODES), and the sequence
# (SQ 14) Baal's inferno shows (the probe, sim/baal.py)
CAST_MODES = {'A1': 4, 'A2': 5, 'SC': 7, 'S1': 8, 'S2': 9, 'S3': 10, 'S4': 11, 'SQ': 14}
SUMMONED = 7_000_000  # unit ids of the monsters a cast raises (sim/casters.py `Summon`), counted from here


Point = tuple[float, float]
# The shooter's cycle before the refit: one shot every SHOT_FRAMES, landed SHOT_LANDS into it. Nothing
# here plays by them any more (sim.monsters has the cycle, at the rate of the takes); they stay as
# the yardstick evidence/model.py lays the takes against, and a shot's points are still "a second
# of the threat table's points" (`shot_parts`), which is SHOT_FRAMES of them.
SHOT_FRAMES = int(GAME_RATE)
RANGED_REACH = SHOT_REACH  # units a shooter shoots within: sim.monsters', which has the takes for it
SHOT_LANDS = SHOT_FRAMES // 2
# The kind of damage of an exploding corpse: this file's assumption (the table only says which corpses
# explode, monstats `deathDmg`).
BLAST_KIND = PHYSICAL
AURA_MOD = 30  # monumod `aura`: Aura Enchanted (threat_table.json rules.modifiers)
# What an Aura Enchanted monster's aura does to the blows around it. A scene's Mob says that it has an
# aura, not which: this file's assumption is Might, the factor terror/danger.py counts for it
# (DANGER.aura_physical, 2.0), on the whole blow as scenarios/threat/harness.py `rate` puts a boost.
AURA_FACTOR = DANGER.aura_physical[MIGHT]
# monstats element types (the threat table's `elements`) as the kinds of damage a resistance cuts.
KINDS = {'fire': 'fire', 'ltng': 'lightning', 'cold': 'cold', 'frze': 'cold'}
ELEMENTAL, MAGIC = 'elemental', 'magic'  # parts nothing resists: an element the table does not name, and magic


# The character's resistances before the cap, in Hell (the penalty of 100 taken off), by the weapon set's base
# codes: the `character_stats` of the takes that start with each set in hand (cut.py MAIN and STAFF: fire 190,
# lightning 179, cold 189; fire 154, lightning 108, cold 118) and their poison (evidence/CURSES.md: 195 and 124).
# A curse moves these, not the capped share (Lower Resist's -55 on fire 90 leaves 35, not 20).
RAW_RESISTS: dict[frozenset[str], dict[str, float]] = {
    frozenset(('fla', 'uit')): {'fire': 90.0, 'lightning': 79.0, 'cold': 89.0, 'poison': 95.0},
    frozenset(('6cs', 'wa3')): {'fire': 54.0, 'lightning': 8.0, 'cold': 18.0, 'poison': 24.0},
}


def raw_resists(codes: Sequence[str]) -> dict[str, float] | None:
    """The resistances before the cap of the set of `codes` (RAW_RESISTS), None for a set the takes do not show."""
    return RAW_RESISTS.get(frozenset(codes))


def threat_row(txt: int) -> dict:
    """The type's row of the threat table; empty for a type it does not hold."""
    return table()['monsters'].get(str(txt), {})


def is_ranged(txt: int) -> bool:
    return bool(threat_row(txt).get('ranged'))


def shooter(txt: int) -> bool:
    """Whether the arena plays the type as a shooter: the threat table calls it ranged, or the takes
    show it shooting and not striking (sim.monsters `shoots`: the shamans, the Hydras). What such a
    one shoots is `shot_parts`' last resort, the mean of its monstats attack: an assumption, the
    takes hold 0 to 3 of their hits each."""
    return is_ranged(txt) or shoots(txt)


def explodes(txt: int) -> bool:
    return bool(threat_row(txt).get('death_damage'))


def shot_parts(walker: Walker) -> dict[str, float]:
    """A ranged monster's shot in raw points by kind of damage: the threat table's multiples of monlvl
    `DM(H)` at the monster's level (physical, elemental, magic, times the family's factor from the
    probe logs), a second of them to a shot, raised by rank, Extra Strong and Herald tier as a blow of
    sim.monsters is (`boost`). The elemental part is of the first element the type's row names; with
    all multiples zero the shot is the mean of the type's monstats attack, as `Traits` has it."""
    row = threat_row(walker.txt)
    found = row.get('multiple', {})
    traits = walker.traits
    base = float(tables()['monlvl'].get(str(traits.level), {}).get('DM(H)', 0))
    factor = base * found.get('hard', 1.0) * boost(traits.rank, walker.mods, walker.tier) * SHOT_FRAMES / GAME_RATE
    kind = next((KINDS[e['type']] for e in row.get('elements', ()) if e['type'] in KINDS), ELEMENTAL)
    parts = {PHYSICAL: found.get('physical', 0.0), kind: found.get('elemental', 0.0), MAGIC: found.get('magic', 0.0)}
    parts = {name: share * factor for name, share in parts.items() if share}
    return parts or {PHYSICAL: sum(traits.damage) / 2}


class Horde(Pack):
    """`sim.monsters.Pack` on walled ground. The walkers think, strike, shoot and roll as the pack has
    them; only where a stride goes is replaced, and only when the straight line is barred, and a
    shooter (`shots`: unit -> the parts of its shot) needs a clear line to shoot."""

    def __init__(
        self,
        walkers: Sequence[Walker],
        seed: int,
        ground: Ground,
        doors: Sequence[Door] = (),
        shots: Mapping[int, Mapping[str, float]] | None = None,
    ) -> None:
        super().__init__(walkers, seed, shots)
        self.ground, self.doors = ground, tuple(doors)
        self.barred = no_footing(ground, self.doors)  # None: open ground
        self.frame = 0
        self.ways: dict[int, tuple[tuple[int, int], list[Point]]] = {}  # unit -> the goal's cell, the way left

    def step(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        self.frame = frame
        return super().step(frame, targets)

    def _open(self, start: Point, end: Point) -> bool:
        """Whether nothing bars the straight walk from `start` to `end` (the cell stood on is not looked at)."""
        if self.barred is None:
            return True
        steps = max(int(math.dist(start, end) / WAY_SAMPLE), 1)
        return not any(
            self.barred((start[0] + (end[0] - start[0]) * k / steps, start[1] + (end[1] - start[1]) * k / steps))
            for k in range(1, steps)
        )

    def _round(self, walker: Walker, target: Point, stride: float | None = None) -> bool:
        """One stride of the walker (its own speed, or `stride` units) along the walked way to `target`;
        False: there is no way (or it has gone as far as one leads). The way is found once for each cell the
        target stands on."""
        cell = (math.floor(target[0]), math.floor(target[1]))
        known = self.ways.get(walker.unit)
        if known is None or known[0] != cell:
            assert self.barred is not None
            known = self.ways[walker.unit] = (cell, walked_way(self.barred, walker.at, target))
        way = known[1]
        if not way:
            return False
        stride = walker.traits.speed if stride is None else stride
        while way and stride > 0:
            gap = math.dist(walker.at, way[0])
            if gap <= stride:
                (walker.x, walker.y), stride = way.pop(0), stride - gap
            else:
                walker.x += (way[0][0] - walker.x) / gap * stride
                walker.y += (way[0][1] - walker.y) / gap * stride
                stride = 0.0
        return True

    def _walk(self, walker: Walker, targets: Sequence[Point]) -> None:
        target = targets[walker.aim] if 0 <= walker.aim < len(targets) else targets[self._target(walker, targets)]
        if self._open(walker.at, target):
            self.ways.pop(walker.unit, None)
            super()._walk(walker, targets)
        elif math.dist(walker.at, target) <= self._stop(walker):
            walker.until = 0  # there: it thinks at once
        elif not self._round(walker, target):
            walker.doing, walker.until = STAND, self.frame + max(walker.traits.idles, 1)

    def _sighted(self, walker: Walker, target: Point) -> bool:
        """Whether the walker has `target` within its reach with a clear line to it."""
        if not super()._sighted(walker, target):
            return False
        if clear_shot(self.ground, walker.at, target, self.doors):
            self.ways.pop(walker.unit, None)
            return True
        return False

    def _closer(self, walker: Walker, target: Point) -> bool:
        """One stride toward `target`, straight where nothing bars it; False: no way."""
        if not self._open(walker.at, target):
            return self._round(walker, target)
        self.ways.pop(walker.unit, None)
        return super()._closer(walker, target)

    # A walker of a read AI (sim/casters.py `Minds`): its walks go round walls, its first sight needs a clear
    # line, a retreat needs footing where it ends.

    def _go(self, walker: Walker, goal: Point, stride: float, stop: float) -> bool:
        if self._open(walker.at, goal):
            self.ways.pop(walker.unit, None)
            return super()._go(walker, goal, stride, stop)
        return self._round(walker, goal, stride)

    def _sees(self, walker: Walker, target: Point) -> bool:
        return clear_shot(self.ground, walker.at, target, self.doors)

    def _footing(self, spot: Point) -> bool:
        return self.barred is None or not self.barred(spot)


class Mobs:
    """A scene's monsters, played tick by tick. All rolls come from `rng`: equal scenes, equal seeds
    and equal calls give equal answers. `auras` (unit -> the factor on the blows of the others within
    BOOST_RANGE while it lives) is for a scene that knows its auras and curses; left out, every Aura
    Enchanted monster of the scene has AURA_FACTOR. The scene given is not changed."""

    def __init__(self, scene: Scene, rng: random.Random, auras: Mapping[int, float] | None = None) -> None:
        self.mobs: dict[int, Mob] = {mob.unit: replace(mob) for mob in scene.mobs}
        self.hostile = [mob.unit for mob in self.mobs.values() if mob.owner is None and not mob.ally]
        self.auras = (
            dict(auras)
            if auras is not None
            else {unit: AURA_FACTOR for unit in self.hostile if AURA_MOD in self.mobs[unit].mods}
        )
        walkers = [self._walker(self.mobs[unit]) for unit in self.live()]
        # A type of a read AI casts what its row says (sim/casters.py); it has no fitted shot.
        shots = {walker.unit: shot_parts(walker) for walker in walkers if shooter(walker.txt) and walker.mind is None}
        ground = Ground(Walkable(**grid) for grid in scene.ground)
        # A door row as the stance fixtures hold it: unit, txt, mode, x, y (scenarios/stance/harness.py `load`).
        doors = [Door(row[0], row[1], row[2], float(row[3]), float(row[4])) for row in scene.doors]
        self.pack = Horde(walkers, rng.getrandbits(32), ground, doors, shots)
        self.frame = 0  # the tick about to be played
        # The character's block (game.py sets the chance): a melee blow that would land is blocked with it, takes
        # nothing and is counted. Its own stream, drawn after the pack's seed, so a chance of 0 changes no roll.
        self.block_chance = 0.0
        self.block_rng = random.Random(rng.getrandbits(32))
        self.blocked = 0
        # The character's guard (game.py sets it: the build's, sim/guard.py): it takes its kinds of a blow of a type
        # played by the client's rules before the resistances, and stuns that type's striker. Its rolls (the
        # character's in the game) are a stream of their own, drawn after the block's, so no other roll moves.
        self.guard: Guard | None = None
        self.guard_rng = random.Random(rng.getrandbits(32))
        self.blasts: list[Point] = []  # where corpses exploded since the last tick
        # The character's resistances before the cap, Hell's penalty taken off, of the set in hand (game.py
        # sets it at each tick, `RAW_RESISTS`); None: only what the set's shares say.
        self.raw: Mapping[str, float] | None = None
        # The monsters a cast raised (sim/casters.py `Summon`: Baal's tentacles and clone): unit -> (its summoner, the
        # frame it is gone at or None). They go when that frame comes or their summoner dies; neither is a kill.
        self.area = scene.hero.area
        self.seed = 1  # a newcomer's rolls (`spawn`); stage.py's `Cast` gives the play's
        self.summoned: dict[int, tuple[int, int | None]] = {}
        self.next_summon = SUMMONED

    @staticmethod
    def _walker(mob: Mob) -> Walker:
        """The scene's monster as a walker of sim.monsters: its type, level, rank flags, enchantments
        and Herald tier are the scene's, so `Traits.of` gives its speed, its think rolls and its blow."""
        walker = Walker(
            mob.unit, mob.txt, mob.at[0], mob.at[1],
            level=mob.level or None, flags=mob.flags, mods=tuple(mob.mods), tier=mob.tier,
        )  # fmt: skip
        # A shooter is the pack's by its shot, whatever monstats `isMelee` says (Gloams and Succubi are
        # melee there and ranged by the threat table). Any other type fights hand to hand with its
        # monstats attack, though monstats does not flag it melee (maggots): this file's assumption. Left
        # as it is, the pack would have it stand. A type of a read AI (Venom Lords, Storm Casters, Doom and
        # Oblivion Knights) thinks by it whatever this says (sim/casters.py).
        walker.traits = replace(walker.traits, melee=not shooter(mob.txt))
        if mob.full > 0:
            walker.health = mob.life / mob.full
        return walker

    def spawn(self, mob: Mob, seed: int | None = None) -> None:
        """Put `mob` into the play as `__init__` and `Pack.__init__` put one there at the start: its own rolls (from
        `seed`, else the play's seed and its unit), a shooter with its shot."""
        mob = replace(mob)
        self.mobs[mob.unit] = mob
        if mob.owner is not None or mob.ally or mob.life <= 0:
            return
        self.hostile.append(mob.unit)
        walker = self._walker(mob)
        pack = self.pack
        pack.walkers[walker.unit] = walker
        roll = pack.rolls[walker.unit] = random.Random(self.seed * 1_000_003 + walker.unit if seed is None else seed)
        walker.favour = roll.random()
        if shooter(walker.txt) and walker.mind is None:
            pack.shots[walker.unit] = dict(shot_parts(walker))
            walker.until = self.frame + roll.randrange(max(round(pack._gap(walker)), 1))

    def raised(self) -> None:
        """The monsters the casts of this tick raised (`Minds.summons`) put into the play, and those whose time is up
        or whose summoner died taken out."""
        minds = self.pack.minds
        for summon in minds.summons:
            self.next_summon += 1
            full = points_of(summon.txt, self.area)
            mob = Mob(self.next_summon, summon.txt, summon.at, 0, full, full)
            self.spawn(mob, summon.seed)
            lasts = None if summon.lasts is None else summon.frame + summon.lasts
            self.summoned[mob.unit] = (summon.unit, lasts)
        minds.summons = []
        for unit, (summoner, lasts) in list(self.summoned.items()):
            if (lasts is not None and self.frame >= lasts) or summoner not in self.pack.walkers:
                self.vanish(unit)

    def vanish(self, unit: int) -> None:
        """A raised monster gone, not killed: it lies where it stood, out of the pack."""
        self.summoned.pop(unit, None)
        mob = self.mobs.get(unit)
        if mob is not None and mob.life > 0:
            mob.life, mob.mode = 0.0, LYING_DEAD
        self.pack.remove(unit)

    def live(self) -> list[int]:
        """The unit ids of the hostiles still alive."""
        return [unit for unit in self.hostile if self.mobs[unit].mode != LYING_DEAD and self.mobs[unit].life > 0]

    def _raised(self, unit: int) -> float:
        """The factor the live auras around a monster put on its blows (its own does not count)."""
        mob = self.mobs.get(unit)
        factor = 1.0
        if mob is None:
            return factor
        for other in self.live():
            raises = self.auras.get(other, 1.0)
            if other != unit and raises != 1.0 and math.dist(self.mobs[other].at, mob.at) <= BOOST_RANGE:
                factor *= raises
        return factor

    def stopped(self, resist: Mapping[str, float]) -> dict[str, float]:
        """The share of each kind of damage the character stops at this tick: `resist` (the share each lets
        through with the set in hand), what `raw` adds of the kinds `resist` does not name, all under the
        curse a caster put on the character (sim/casters.py `resisted`: the curse moves the resistance
        before the cap, which `raw` holds)."""
        through = dict(resist)
        for kind, value in (self.raw or {}).items():
            through.setdefault(kind, 1 - min(max(value, -100.0), 75.0) / 100)
        through = resisted(through, self.pack.minds.hex_on(0, self.frame), self.raw)
        return {kind: 1.0 - share for kind, share in through.items()}

    def tick(self, hero_at: Point, companions: Sequence[Point], resist: Mapping[str, float]) -> float:
        """One game tick: every live hostile thinks, moves, strikes and shoots at the character or one
        of its `companions`. The points taken off the character this tick, each kind of damage cut to
        the share `resist` lets through (a kind it does not name: all of it), under a curse on it."""
        found = self.pack.step(self.frame, [hero_at, *companions])
        self.raised()
        stopped = self.stopped(resist)
        taken = 0.0
        for at in self.blasts:
            if math.dist(at, hero_at) <= BLAST_RADIUS:
                taken += BLAST * (1.0 - stopped.get(BLAST_KIND, 0.0))
        self.blasts = []
        for blow in found:
            if blow.target == 0 and blow.kind == MELEE and self.block_rng.random() < self.block_chance:
                self.blocked += 1
            elif blow.target == 0:
                taken += self.landed(blow, stopped)
        for unit, walker in self.pack.walkers.items():
            self.mobs[unit].at = walker.at
        self.frame += 1
        return taken

    def landed(self, blow: Blow, stopped: Mapping[str, float]) -> float:
        """The points a blow that was not blocked takes off the character: its parts times the auras around its
        monster (a swing's or a shot's), the guard's share taken off first (`_guarded`), cut by `stopped`."""
        raised = self._raised(blow.unit) if blow.kind in (MELEE, SHOT) else 1.0
        if self.guard is not None and self._ruled(blow):
            return self._guarded(blow, raised).taken(stopped)
        return blow.taken(stopped) * raised

    def _ruled(self, blow: Blow) -> bool:
        """Whether a blow is of a type the client's rules play (sim/casters.py): a caster's missile or poison, or
        the blow of a walker with a mind. Only these meet the guard (sim/guard.py: the fit has it in)."""
        if blow.missile or blow.kind in (casters.SPELL, casters.POISON):
            return True
        walker = self.pack.walkers.get(blow.unit)
        return walker is not None and walker.mind is not None

    def _guarded(self, blow: Blow, raised: float) -> Blow:
        """The blow on the character after the guard: its raw parts (times the auras' `raised`) less what the pool
        takes; a melee blow that landed while the guard still stands stuns its striker (sim/guard.py)."""
        guard = self.guard
        assert guard is not None
        parts = guard.take({kind: points * raised for kind, points in (blow.parts or {PHYSICAL: blow.damage}).items()})
        walker = self.pack.walkers.get(blow.unit)
        if blow.kind == MELEE and walker is not None:
            moves = walker.traits.speed > 0
            frames = guard.stun_frames(walker.txt, walker.flags, moves, self.guard_rng.random)
            self.pack.stun(blow.unit, self.frame, frames)
        return replace(blow, damage=sum(parts.values()), parts=parts)

    def hit(self, unit: int, points: float) -> bool:
        """The character's damage on a monster; True: it died now. Nothing comes off an immune one, a
        companion or a corpse. The pack is told what share of the monster's most life the hit took: a
        tick's hits may stagger it at the next tick, and a swing under way is then lost; a Lightning
        Enchanted one may let its sparks go (`Pack.struck`). One that dies may let a nova go
        (`Pack.died`), and an exploding one leaves its blast for the next tick."""
        mob = self.mobs.get(unit)
        if mob is None or unit not in self.pack.walkers or mob.immune:
            return False
        mob.life -= points
        self.pack.struck(unit, self.frame, points / mob.full if mob.full > 0 else 0.0)
        if mob.life > 0:
            return False
        mob.life, mob.mode = 0.0, LYING_DEAD
        self.pack.died(unit, self.frame)
        if explodes(mob.txt):
            self.blasts.append(mob.at)
        return True

    def mode(self, mob: Mob) -> int:
        """The mode the client shows a monster in: the scene's, but for a type the decision loop has a read model
        of (combat/threats), whose cast under way the client shows by its mode (monmode.txt CAST_MODES) while the
        mode's own frames last (its `aidel` after it is spent standing)."""
        walker = self.pack.walkers.get(mob.unit)
        if walker is None or walker.mind is None or walker.doing != casters.CAST or threats.of(mob.txt) is None:
            return mob.mode
        mind = walker.mind
        if mind.ai == casters.DIABLO:
            frames = casters.Minds._diablo_frames(mind.mode)
        elif mind.ai == casters.BAAL:
            from inventory_tracking.combat.sim import baal

            frames = baal.MODE_FRAMES.get(mind.mode, 0)
        else:
            frames = casters.MODE_FRAMES.get((mind.ai, mind.mode), 0)
        begun = walker.until - frames - mind.delay
        return CAST_MODES.get(mind.mode, mob.mode) if self.frame - 1 < begun + frames else mob.mode

    def flights(self, kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
        """The missiles in flight of the classes `kinds` as macros/world.py `flights` reads them: (owner unit,
        class, x, y)."""
        return tuple(
            (bolt.unit, bolt.missile, bolt.x, bolt.y) for bolt in self.pack.minds.bolts if bolt.missile in kinds
        )

    def monsters(self) -> list[Monster]:
        """The monsters as macros/world.py reads them now: life in whole points, a dead one lying
        (mode 12) where it fell, the character's companions where the scene has them."""
        return [
            Monster(
                mob.unit,
                mob.txt,
                self.mode(mob),
                mob.at[0],
                mob.at[1],
                NO_OWNER if mob.owner is None else mob.owner,
                mob.flags,
                mob.ally,
                max(round(mob.life), 1) if mob.mode != LYING_DEAD and mob.life > 0 else 0,
                round(mob.full),
                modifiers=tuple(mob.mods),
                tier=mob.tier,
            )
            for mob in self.mobs.values()
        ]

    def corpses(self) -> tuple[tuple[int, float, float], ...]:
        """The monsters lying dead as (unit id, x, y), as `Run.corpses` gives them (world.corpses)."""
        return tuple((mob.unit, mob.at[0], mob.at[1]) for mob in self.mobs.values() if mob.mode == LYING_DEAD)
