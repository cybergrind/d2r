"""The monsters of the arena: combat/sim/monsters.py made to answer to walls, lines of sight, blasts and
auras (framework-plan.md, Task 1.2; architecture.md §6).

`Mobs` holds a scene's monsters and plays them a game tick at a time against where the character is
now. The monsters are `sim.monsters` walkers in its `Pack`, as that module has them since its refit
to the takes (its module text): the think cycle, the swings a second, the chance that a swing or a
shot takes life, whom a monster goes for, the blows by rank, enchantment and Herald tier and their
spread, a shooter's cycle with its missile in flight, the sparks of a Lightning Enchanted one, the
nova of a Cold Enchanted elite's death. The shooter's cycle was this file's own (one landed shot a
second) and moved there with the refit. `Horde` is that pack with what it lacks:

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

from inventory_tracking.combat.mechanics.tables import tables
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

    def _round(self, walker: Walker, target: Point) -> bool:
        """One stride of the walker along the walked way to `target`; False: there is no way (or it
        has gone as far as one leads). The way is found once for each cell the target stands on."""
        cell = (math.floor(target[0]), math.floor(target[1]))
        known = self.ways.get(walker.unit)
        if known is None or known[0] != cell:
            assert self.barred is not None
            known = self.ways[walker.unit] = (cell, walked_way(self.barred, walker.at, target))
        way = known[1]
        if not way:
            return False
        stride = walker.traits.speed
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
        shots = {walker.unit: shot_parts(walker) for walker in walkers if shooter(walker.txt)}
        ground = Ground(Walkable(**grid) for grid in scene.ground)
        # A door row as the stance fixtures hold it: unit, txt, mode, x, y (scenarios/stance/harness.py `load`).
        doors = [Door(row[0], row[1], row[2], float(row[3]), float(row[4])) for row in scene.doors]
        self.pack = Horde(walkers, rng.getrandbits(32), ground, doors, shots)
        self.frame = 0  # the tick about to be played
        self.blasts: list[Point] = []  # where corpses exploded since the last tick

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
        # monstats attack, though monstats does not flag it melee (maggots, Venom Lords): this file's
        # assumption. Left as it is, the pack would have it stand.
        walker.traits = replace(walker.traits, melee=not shooter(mob.txt))
        return walker

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

    def tick(self, hero_at: Point, companions: Sequence[Point], resist: Mapping[str, float]) -> float:
        """One game tick: every live hostile thinks, moves, strikes and shoots at the character or one
        of its `companions`. The points taken off the character this tick, each kind of damage cut to
        the share `resist` lets through (a kind it does not name: all of it)."""
        stopped = {kind: 1.0 - share for kind, share in resist.items()}
        taken = 0.0
        for at in self.blasts:
            if math.dist(at, hero_at) <= BLAST_RADIUS:
                taken += BLAST * resist.get(BLAST_KIND, 1.0)
        self.blasts = []
        for blow in self.pack.step(self.frame, [hero_at, *companions]):
            if blow.target == 0:
                taken += blow.taken(stopped) * (self._raised(blow.unit) if blow.kind in (MELEE, SHOT) else 1.0)
        for unit, walker in self.pack.walkers.items():
            self.mobs[unit].at = walker.at
        self.frame += 1
        return taken

    def hit(self, unit: int, points: float) -> bool:
        """The character's damage on a monster; True: it died now. Nothing comes off an immune one, a
        companion or a corpse. A Lightning Enchanted one may let its sparks go (`Pack.struck`); one
        that dies may let a nova go (`Pack.died`), and an exploding one leaves its blast for the next tick."""
        mob = self.mobs.get(unit)
        if mob is None or unit not in self.pack.walkers or mob.immune:
            return False
        mob.life -= points
        self.pack.struck(unit, self.frame)
        if mob.life > 0:
            return False
        mob.life, mob.mode = 0.0, LYING_DEAD
        self.pack.died(unit, self.frame)
        if explodes(mob.txt):
            self.blasts.append(mob.at)
        return True

    def monsters(self) -> list[Monster]:
        """The monsters as macros/world.py reads them now: life in whole points, a dead one lying
        (mode 12) where it fell, the character's companions where the scene has them."""
        return [
            Monster(
                mob.unit,
                mob.txt,
                mob.mode,
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
