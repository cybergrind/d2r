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
BLAST_RADIUS, and a live monster with a damage aura raises the blows of the others within AURA_RANGE.

What is this file's own assumption, not a table's or a take's, is named where it is set: the points
of a shot, the kind of a blast, which aura an Aura Enchanted monster has, that a type nothing calls a
shooter fights hand to hand.

Not modelled, as in `sim.monsters`: fleeing, damage that is no blow. A companion of the character's stands where the
scene has it and is never hurt; the companions a monster goes for are the places `tick` is given (game.py plays them,
with its rule PETS_FIGHT, from the blows on them `tick` keeps in `mate_blows`).

Two rules a play may turn on (game.py `Arena.rules`, 2026-10-21; rca/2026-10-21/herald-fight-findings.md §3.4 "what
the arena lacks"), both off unless asked so that every scene fitted and pinned before plays roll for roll as it did:

- **the sigil slows** (`Horde.slowed`: a walker's place -> the factor on its speed and its attack rate): Sigil:
  Lethargy's aurastat1 `attackrate` and aurastat3 `velocitypercent`, both ln78 = Param7 + (lvl - 1) x Param8 = -50 + 0
  (skills.txt 393, combat/data/tables.json `skills`): half the speed, a swing begun inside it twice as long. A walker of
  a read AI (sim/casters.py) is not slowed. Not verified: whether a boss or a Herald takes the whole slow;
- **bodies block** (`Horde.bodies`: the character's and its companions' places with their body radii): a walker's
  stride that would end inside another body (another walker's, the character's, a companion's) and nearer to it is a
  stride to the side if one is free, else not made. A body's radius is half its monstats2 SizeX (BODY_RADII), the
  character's HERO_BODY: both read as world units, an assumption of this file.
"""

import math
import random
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from typing import Any

from inventory_tracking.combat import revivers, threats
from inventory_tracking.combat.mechanics.tables import points_of, tables
from inventory_tracking.combat.sim import casters, monsters as sim_monsters
from inventory_tracking.combat.sim.casters import hit_chance, resisted
from inventory_tracking.combat.sim.guard import Guard
from inventory_tracking.combat.sim.monsters import (
    CHAMPION,
    MELEE,
    MINION,
    PHYSICAL,
    SHOT,
    SHOT_REACH,
    STAGGER,
    STAND,
    STRIKE,
    UNIQUE,
    WALK,
    Blow,
    Pack,
    Traits,
    Walker,
    boost,
    shoots,
)
from inventory_tracking.combat.stance import WAY_SAMPLE, no_footing
from inventory_tracking.game.layout import LYING_DEAD, MAGIC_RESIST, NO_OWNER
from inventory_tracking.game.records import Monster
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.safety import AURA_LEVELS, aura_raise
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.travel import walked_way
from inventory_tracking.takes.timeline import GAME_RATE
from inventory_tracking.terror.danger import MIGHT
from tests.inventory_tracking.scenarios.arena.scene import Mob, Scene

# The threat scenarios' numbers, used here as they are there (framework-plan.md has them moved to this
# file; scenarios/threat/harness.py is left alone by this task, so they are imported, not copied):
# BLAST_RADIUS 4 and BLAST 450 points, both that file's assumptions (the takes hold too few exploding corpses to
# refit them).
from tests.inventory_tracking.scenarios.threat.harness import BLAST, BLAST_RADIUS
from tests.inventory_tracking.scenarios.threat.table import table


# The immune ones as the live look reads them (the measure of builds/warlock/mark.py DESIGNATED_MARK, 2026-10-22): an
# immune mob's record carries magic 100 (`Monster.resists`), and the demons' blows take life off it (`Mobs.hit`): the
# strike takes nothing, the demons are its answer. False (the default): as before, immune to every hit, unread.
IMMUNE_READ = False


# monmode.txt: the client's modes of a monster's strikes and casts (game/layout.py STRIKING_MODES), and the
# sequence (SQ 14) Baal's inferno shows (the probe, sim/baal.py)
CAST_MODES = {'A1': 4, 'A2': 5, 'SC': 7, 'S1': 8, 'S2': 9, 'S3': 10, 'S4': 11, 'SQ': 14}
# A walker's motion as the client shows it (`Mobs.motion_mode`; monmode.txt WL 2, GH 3). Before 2026-10-22 a walker
# that walked or swung kept the take's mode (often NU 1), so macros/safety.py read it as idle (Hostile.active False)
# and combat/harm.py priced a unique running in at nothing (pursuit-mode Fane deaths, fane-death-sim-findings.md §11).
# Only over a plain mode of the take's (NU, WL, GH, A1, A2, RN): a submerged frog or an airborne vulture keeps its own.
WALK_MODE, GET_HIT_MODE = 2, 3
PLAIN_MODES = frozenset((1, 2, 3, 4, 5, 15))
SHOWN_MOTION = True
# A raise of stat 25 (Might, Fanaticism) on a blow's physical points alone in every scene, as the game does; before
# 2026-10-22 an uncapped scene raised the whole blow, elements too (the coordinator, after the death agent's note)
PHYSICAL_RAISE = True
SUMMONED = 7_000_000  # unit ids of the monsters a cast raises (sim/casters.py `Summon`), counted from here


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
# Units within which a melee blow reaches the character under `capped` (`Mobs.in_reach`): the population replay's
# striker distance (rca/2026-10-21/fane-death-sim-findings.md §8), the game's melee range and the two bodies
MELEE_REACH = 4.0
# A thrown missile under `capped` (2026-10-22, rca/2026-10-21/fane-death-sim-findings.md §10): the takes' javelins
# (missiles.txt pantherjav5, SrcDamage 128) of 2026-10-20 to 22, 22 hits, hold the Slingers' throws at 463-627 (1126 for
# two) beside a tier 5 pack whose stat 25 read 285, 300-498 beside one with none: x1.25 between them, not the x3.85 of
# stat 25, and no throw over 345 raw beside a tier 5 Herald whose monstats most there is 905. A throw at its type's most
# with neither its stat 25 nor its Herald tier's boost (x2.5) is the least envelope over all 22 (the tier 5 Herald's 750
# against the 627 seen). False: as each says
SHOT_RAISED = False  # True: a shot raised by its stat 25 as a melee blow is
SHOT_TIER = False  # True: a shot's cut at its most with the Herald tier's boost
AURA_MOD = 30  # monumod `aura`: Aura Enchanted (threat_table.json rules.modifiers)
# What an Aura Enchanted monster's aura does to the blows around it. A scene's Mob says that it has an
# aura, not which: this file's assumption is Might, on the whole blow as scenarios/threat/harness.py `rate` puts a
# boost. Its level (2026-10-22, rca/2026-10-21/fane-death-sim-findings.md §8-§9): the takes' stats 350/351 show Might at
# 16 on the Aura Enchanted (macros/safety.py AURA_LEVELS), +190% (x2.9) within 46 units; over the takes' 1658 fight
# windows the arena with each unit's own stat 25 takes 1.10 of the game's life a swing from the aura holders' packs,
# with half of it (x1.95, terror/danger.py's 2.0, level 7's) 0.77, with none 0.43. So level 16's factor and range, in
# place of DANGER.aura_physical (2.0) and BOOST_RANGE (16, level 1's)
AURA_RAISE, AURA_RANGE = aura_raise(MIGHT, AURA_LEVELS[MIGHT])
AURA_FACTOR = 1.0 + AURA_RAISE / 100
# The holder's own blows are raised by its aura too (2026-10-25, rca/2026-10-25/t5-blow-findings.md): in the takes of
# 10-23..25 the unique's stat 25 equals its minions' in all 27 tier 5 packs read with both (285, 190, 475, 118). Before,
# `_raised` left the holder out: the t5 Hulk Herald landed and showed (`shown_percent`) x1.0, the safety priced it 651.
# monstats element types (the threat table's `elements`) as the kinds of damage a resistance cuts.
KINDS = {'fire': 'fire', 'ltng': 'lightning', 'cold': 'cold', 'frze': 'cold'}
ELEMENTAL, MAGIC = 'elemental', 'magic'  # parts nothing resists: an element the table does not name, and magic
# Sigil: Lethargy's slow (the module text): ln78 of skills.txt 393 at any level, Param7 -50 with Param8 0.
_SIGIL = tables()['skills']['393']
SIGIL_SLOW = 1.0 + float(_SIGIL['Param7']) / 100.0
# Body radii in world units (the module text): half of monstats2 SizeX (pricing/raw/game-excel, read 2026-10-21):
# thornhulk1/2 (127, 128) 3, blunderbore4 (189, the Urdar) 3, megademon2 (361, the Pit Lord) 3, warputriddefiler (744)
# 2. Any other type BODY_RADIUS; the character HERO_BODY. Assumptions where no row is named.
BODY_RADII: dict[int, float] = {127: 1.5, 128: 1.5, 189: 1.5, 361: 1.5, 744: 1.0}
BODY_RADIUS = 1.0
HERO_BODY = 1.0
SIDESTEP = (90.0, -90.0, 45.0, -45.0)  # degrees off a blocked stride a walker tries instead, in this order


def body_of(txt: int) -> float:
    """A body's radius by its type (BODY_RADII)."""
    return BODY_RADII.get(txt, BODY_RADIUS)


# The character's resistances before the cap, in Hell (the penalty of 100 taken off), by the weapon set's base
# codes: the `character_stats` of the takes that start with each set in hand (cut.py MAIN and STAFF: fire 190,
# lightning 179, cold 189; fire 154, lightning 108, cold 118) and their poison (evidence/CURSES.md: 195 and 124).
# A curse moves these, not the capped share (Lower Resist's -55 on fire 90 leaves 35, not 20).
RAW_RESISTS: dict[frozenset[str], dict[str, float]] = {
    frozenset(('fla', 'uit')): {'fire': 90.0, 'lightning': 79.0, 'cold': 89.0, 'poison': 95.0},
    frozenset(('6cs', 'wa3')): {'fire': 54.0, 'lightning': 8.0, 'cold': 18.0, 'poison': 24.0},
}


# [table] monumod.txt constants 10, 12, 13: the attack rating bonus of a champion, a unique's minion and a unique, in %
# (sim/monsters.py `boost` holds the damage bonuses; the attack rating ones are not in tables.json)
RANK_RATING = {CHAMPION: 75, MINION: 50, UNIQUE: 100}


@contextmanager
def sure_swings(on: bool = True) -> Generator[None]:
    """While the block runs, sim/monsters.py's swings at the character take life every time (`swing_of`'s
    `takes_life` 1), for `Mobs.landing` to roll the game's chance to hit instead; off: nothing changes. The live
    forecast (combat/harm.py) holds its own `swing_of` and is not touched."""
    if not on:
        yield
        return
    plain = sim_monsters.swing_of

    def swing_of(txt: int) -> Mapping[str, Any]:
        found = plain(txt)
        return {**found, 'takes_life': {**found['takes_life'], 'value': 1.0}}

    sim_monsters.swing_of = swing_of  # pyrefly: ignore[bad-assignment]
    try:
        yield
    finally:
        sim_monsters.swing_of = plain


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
        # The arena's rules (the module text), None while off: the factor a walker's place puts on its speed and
        # attack rate, and the bodies besides the walkers' that a stride may not end in.
        self.slowed: Callable[[Point], float] | None = None
        self.bodies: Sequence[tuple[Point, float]] | None = None
        self.base: dict[int, Traits] = {}  # unit -> its traits as made, before a slow

    def step(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        self.frame = frame
        slow = self._slow() if self.slowed is not None else {}
        before = {unit: (walker.at, walker.doing, walker.until) for unit, walker in self.walkers.items()}
        blows = super().step(frame, targets)
        for unit, factor in slow.items():
            walker = self.walkers.get(unit)
            if walker is None or unit not in before:
                continue
            _, doing, until = before[unit]
            if walker.doing == STRIKE and (doing != STRIKE or walker.until != until) and walker.until > frame:
                # A swing (or shot) begun in the sigil: its frames at the slowed attack rate
                walker.until = frame + math.ceil((walker.until - frame) / factor)
                if walker.lands > frame:
                    walker.lands = frame + math.ceil((walker.lands - frame) / factor)
        if self.bodies is not None:
            self._unblock({unit: at for unit, (at, _, _) in before.items()})
        return blows

    def _slow(self) -> dict[int, float]:
        """Each walker's speed as the sigil slows it this frame (`slowed`); the walkers it slows and their factor."""
        assert self.slowed is not None
        found = {}
        for unit, walker in self.walkers.items():
            if walker.mind is not None:
                continue
            base = self.base.setdefault(unit, walker.traits)
            factor = self.slowed(walker.at)
            walker.traits = base if factor >= 1.0 else replace(base, speed=base.speed * factor)
            if factor < 1.0:
                found[unit] = factor
        return found

    def _unblock(self, before: Mapping[int, Point]) -> None:
        """Every stride of this frame that ended inside another body and nearer to it: one to the side (SIDESTEP)
        if that is free, else none (the module text, bodies block)."""
        assert self.bodies is not None
        for unit in sorted(self.walkers):
            walker = self.walkers[unit]
            old = before.get(unit)
            if old is None or walker.at == old:
                continue
            radius = body_of(walker.txt)
            others = [*self.bodies, *((w.at, body_of(w.txt)) for u, w in self.walkers.items() if u != unit)]

            def blocked(spot: Point, start: Point = old, mine: float = radius, near=others) -> bool:
                return any(
                    math.dist(spot, at) < mine + theirs and math.dist(spot, at) < math.dist(start, at) - 1e-9
                    for at, theirs in near
                )

            if not blocked(walker.at):
                continue
            dx, dy = walker.at[0] - old[0], walker.at[1] - old[1]
            walker.x, walker.y = old
            for turn in SIDESTEP:
                angle = math.radians(turn)
                side = (old[0] + dx * math.cos(angle) - dy * math.sin(angle),
                        old[1] + dx * math.sin(angle) + dy * math.cos(angle))  # fmt: skip
                if self._footing(side) and not blocked(side):
                    walker.x, walker.y = side
                    break

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
    AURA_RANGE while it lives) is for a scene that knows its auras and curses; left out, every Aura
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
        # Each melee blow cut at the game's own most for its monster (`bounded`); False: the fitted spread's whole tail,
        # as every scene before 2026-10-22
        self.capped = False
        # The character's defence and level (`landing`): a melee swing at the character lands with the game's chance
        # to hit (sim/casters.py `hit_chance`) instead of the fitted one; None: the fitted chance, as before. Its rolls
        # are a stream of their own, drawn last, so no other roll moves.
        self.defence: tuple[float, int] | None = None
        self.hit_rng = random.Random(rng.getrandbits(32))
        # Each unit's damagepercent (stat 25) as the take read it (fane-death-sim-findings.md §8): the sum
        # of the damage auras on it (Might L16 +190, Concentration L16 +285, Fanaticism L12 +118 in the takes), its own
        # aura among them, on the physical points alone with `capped`; it replaces `auras`. None: `auras`, as before
        self.damage_percent: dict[int, list[tuple[float, float]]] | None = None  # unit -> (seconds, percent), in order
        # The monsters a cast raised (sim/casters.py `Summon`: Baal's tentacles and clone): unit -> (its summoner, the
        # frame it is gone at or None). They go when that frame comes or their summoner dies; neither is a kill.
        self.area = scene.hero.area
        self.seed = 1  # a newcomer's rolls (`spawn`); stage.py's `Cast` gives the play's
        self.summoned: dict[int, tuple[int, int | None]] = {}
        self.next_summon = SUMMONED
        # The blows of the last tick on the character's companions: (the index of the companion among those `tick` was
        # given, its raw points), for game.py's rule PETS_FIGHT
        self.mate_blows: list[tuple[int, float]] = []
        # game.py's rule REVIVERS_RAISE: a live reviver's unit -> the frame of its next raise (`raise_dead`), and the
        # raises played
        self.raise_due: dict[int, int] = {}
        self.raises = 0

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
            life = full
            summoner = self.mobs.get(summon.unit)
            if summon.most > 0 and summoner is not None:
                # [code] Baal's clone: a third of his most life and of his life (sim/baal.py)
                full, life = summoner.full * summon.most, summoner.full * summon.share
            mob = Mob(self.next_summon, summon.txt, summon.at, 0, life, full)
            self.spawn(mob, summon.seed)
            lasts = None if summon.lasts is None else summon.frame + summon.lasts
            self.summoned[mob.unit] = (summon.unit, lasts)
        minds.summons = []
        for unit, (summoner, lasts) in list(self.summoned.items()):
            if (lasts is not None and self.frame >= lasts) or summoner not in self.pack.walkers:
                self.vanish(unit)

    def raise_dead(self) -> list[int]:
        """game.py's rule REVIVERS_RAISE: each live reviver of the production table (combat/revivers.py) raises the
        nearest corpse of its family within its raise range back at full life where it lies (the same unit, as the
        game does: scenarios/revivers/harness.py), never one it spares (combat/revivers.py `spared`: a unique, a
        champion but for a Greater Mummy), one every its `seconds` (the table's mean wait: the think delay over the
        raise chance; the cast's own length is not played). The first comes that long after the reviver is first seen
        with a corpse in range. Returns the units raised this tick."""
        table = revivers.revivers()
        found = []
        for unit in self.live():
            reviver = table.get(self.mobs[unit].txt)
            if reviver is None:
                continue
            at = self.mobs[unit].at
            dead = [
                mob
                for mob in self.mobs.values()
                if mob.mode == LYING_DEAD
                and mob.unit in self.hostile
                and mob.unit not in self.summoned
                and mob.txt in reviver.raises
                and not revivers.spared(reviver, mob.flags)
                and math.dist(at, mob.at) <= reviver.range
            ]
            if not dead:
                self.raise_due.pop(unit, None)
                continue
            due = self.raise_due.setdefault(unit, self.frame + round(reviver.seconds * GAME_RATE))
            if self.frame < due:
                continue
            corpse = min(dead, key=lambda mob: (math.dist(at, mob.at), mob.unit))
            self.raise_due[unit] = self.frame + round(reviver.seconds * GAME_RATE)
            self.hostile.remove(corpse.unit)
            self.spawn(replace(corpse, life=corpse.full, mode=1))
            self.raises += 1
            found.append(corpse.unit)
        return found

    def turn(self, unit: int) -> None:
        """A hostile made the character's (Bind Demon, game.py `Arena.bind`): out of the pack and the hostiles, an
        ally where it stands with the life it has; no kill."""
        mob = self.mobs.get(unit)
        if mob is None or unit not in self.hostile:
            return
        self.hostile.remove(unit)
        self.pack.remove(unit)
        mob.ally = True

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
        """The factor the live auras around a monster put on its blows, its own among them (the game's stat 25)."""
        mob = self.mobs.get(unit)
        factor = 1.0
        if mob is None:
            return factor
        if self.damage_percent is not None:
            # The take's own reading (`damage_percent`): the sum of the damage auras on the unit, its own among them,
            # the last at or before this tick (the first while none is yet)
            readings = self.damage_percent.get(unit, ())
            now = self.frame / GAME_RATE
            value = next((value for at, value in reversed(readings) if at <= now), readings[0][1] if readings else 0.0)
            return 1.0 + value / 100
        for other in self.live():
            raises = self.auras.get(other, 1.0)
            if raises != 1.0 and math.dist(self.mobs[other].at, mob.at) <= AURA_RANGE:
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

    def bounded(self, blows: Sequence[Blow]) -> list[Blow]:
        """The blows with each melee one cut at the game's most for its monster (`capped`, 2026-10-22,
        rca/2026-10-21/fane-death-sim-findings.md): the game rolls a blow uniformly between its least and its most
        (monstats A1MinD/A1MaxD(H) times monlvl DM(H) at its level, times its rank's, Extra Strong's and its Herald
        tier's boost: `Traits.damage`), and an enchantment's element at most its share of that (`Traits.elements`);
        sim/monsters.py `spread` draws the fitted size spread over the mean, whose top decile (x1.84 to x4.99, fitted
        on 50 blows of mean 64) gives a level 96 unique blows of the character's whole life. The auras round it (on the
        physical points alone, as the game's Might) and the curses on the character are put on after (`landed`,
        `stopped`), so the cut is the game's most under them too. Shots, sparks, novas and a read AI's casts are left
        as they are. The fitted spread, not the uniform roll (2026-10-25, rca/2026-10-25/t5-blow-findings.md): the
        takes' clean tier 5 minion blows land at 0.38-0.76 of their priced most, at or under a uniform roll's least,
        and the roll killed halls seed 10."""
        found = []
        for blow in blows:
            walker = self.pack.walkers.get(blow.unit)
            if blow.kind == SHOT and walker is not None and walker.mind is None:
                found.append(self._shot_cut(blow, walker))
                continue
            if blow.kind != MELEE or walker is None or walker.mind is not None:
                found.append(blow)
                continue
            most = walker.traits.damage[1]
            shares = {element: top for element, _, top in walker.traits.elements}
            parts = {
                kind: min(
                    points, most if kind == PHYSICAL else most * shares.get(kind, 0.0) if kind in shares else points
                )
                for kind, points in (blow.parts or {PHYSICAL: blow.damage}).items()
            }
            found.append(replace(blow, damage=sum(parts.values()), parts=parts))
        return found

    def _shot_cut(self, blow: Blow, walker: Walker) -> Blow:
        """A shooter's shot cut at its most (`capped`, 2026-10-22, rca/2026-10-21/fane-death-sim-findings.md §10): each
        kind at the larger of the shot's own points (`shot_parts`) and what the type's monstats attack gives it at most
        (`Traits.damage`, its elements' top shares), both without the Herald tier's boost (SHOT_TIER), as a melee blow
        is cut (`bounded`). sim/monsters.py draws a shot's size from the fitted spread over the mean (x4.6 seen), which
        made a Slinger's throw 2326 raw points, 7754 taken (danger-area110-1912, seed 18); the game's missile has no
        such tail. Its stat 25 does not raise it (SHOT_RAISED, `landed`)."""
        most = walker.traits.damage[1]
        tier = (
            1.0
            if SHOT_TIER
            else boost(walker.traits.rank, walker.mods, walker.tier) / boost(walker.traits.rank, walker.mods, 0)
        )
        own = self.pack.shots.get(walker.unit, {})
        shares = {element: top for element, _, top in walker.traits.elements}
        tops = {PHYSICAL: most} | {kind: most * share for kind, share in shares.items()}
        parts = {
            kind: min(points, max(own.get(kind, 0.0), tops.get(kind, 0.0)) / tier) if kind in own or kind in tops
            else points
            for kind, points in (blow.parts or {PHYSICAL: blow.damage}).items()
        }  # fmt: skip
        return replace(blow, damage=sum(parts.values()), parts=parts)

    def in_reach(self, blow: Blow, hero_at: Point) -> bool:
        """Whether a melee blow at the character comes from within MELEE_REACH of it (`capped`, 2026-10-22,
        rca/2026-10-21/fane-death-sim-findings.md §9). sim/monsters.py `reach_of` gives a share of swings the fit's
        tail, up to 10 units: the takes' hurts name attackers that far, since a fast monster's place is read up to
        0.4 s late (a Flesh Hunter runs 18.6 units a second). The arena's places are exact, so that tail would land the
        unique Herald's 3033 from 9.8 units (fane-death-24 at the client's levels, seed 4); the population replay
        (findings §8) counted the arena's blows from within 4 alone. A blow on a companion, a shot and a read AI's
        casts are as they were."""
        walker = self.pack.walkers.get(blow.unit)
        if blow.kind != MELEE or blow.target != 0 or walker is None or walker.mind is not None:
            return True
        return math.dist(walker.at, hero_at) <= MELEE_REACH

    def landing(self, blows: Sequence[Blow]) -> list[Blow]:
        """The melee blows at the character that hit (`defence`, 2026-10-22, rca/2026-10-21/fane-death-sim-findings.md
        §2): each lands with the game's chance to hit, AR = A1TH(H) x monlvl TH(H) at the monster's level, the rank's
        bonus on it (RANK_RATING), against the character's defence and level (sim/casters.py `hit_chance`, [code +
        table], clamped 5-95 %). The pack swings as if every swing took life (`sure_swings`); the block is the arena's
        own roll after this. A blow on a companion, a shot and a read AI's casts are as they were."""
        found = []
        for blow in blows:
            walker = self.pack.walkers.get(blow.unit)
            chance = self.to_hit(walker) if blow.kind == MELEE and blow.target == 0 and walker is not None else None
            if chance is None or self.hit_rng.random() < chance:
                found.append(blow)
        return found

    def to_hit(self, walker: Walker) -> float | None:
        """A walker's chance to hit the character with a swing (`landing`); None: not rolled here (no `defence`, a read
        AI, a type with no monstats row)."""
        row = tables()['monsters'].get(str(walker.txt))
        if self.defence is None or walker.mind is not None or row is None:
            return None
        defence, level = self.defence
        rated = 1 + RANK_RATING.get(walker.traits.rank, 0) / 100
        row = {**row, 'A1TH(H)': str(float(row.get('A1TH(H)') or 0) * rated)}
        return hit_chance(row, walker.traits.level, defence, level)

    def struck(self, blows: Sequence[Blow], hero_at: Point | None = None) -> list[Blow]:
        """The pack's blows of a tick as this file plays them: at the game's most (`capped`), within the game's melee
        reach of the character (`capped`, `in_reach`), hitting with the game's chance (`defence`)."""
        found = list(blows)
        if self.capped:
            found = self.bounded(found)
            if hero_at is not None:
                found = [blow for blow in found if self.in_reach(blow, hero_at)]
        if self.defence is not None:
            found = self.landing(found)
        return found

    def tick(self, hero_at: Point, companions: Sequence[Point], resist: Mapping[str, float]) -> float:
        """One game tick: every live hostile thinks, moves, strikes and shoots at the character or one
        of its `companions`. The points taken off the character this tick, each kind of damage cut to
        the share `resist` lets through (a kind it does not name: all of it), under a curse on it."""
        found = self.struck(self.pack.step(self.frame, [hero_at, *companions]), hero_at)
        self.raised()
        stopped = self.stopped(resist)
        taken = 0.0
        for at in self.blasts:
            if math.dist(at, hero_at) <= BLAST_RADIUS:
                taken += BLAST * (1.0 - stopped.get(BLAST_KIND, 0.0))
        self.blasts = []
        self.mate_blows = [(blow.target - 1, blow.damage) for blow in found if blow.target > 0]
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
        raised = (
            self._raised(blow.unit)
            if blow.kind == MELEE or (blow.kind == SHOT and (SHOT_RAISED or not self.capped))
            else 1.0
        )
        if (self.capped or PHYSICAL_RAISE) and raised != 1.0:
            # The game's Might (and Fanaticism's damage) raise a blow's physical points alone: its elements as rolled
            # (`capped` scenes, and every scene since PHYSICAL_RAISE)
            parts = dict(blow.parts or {PHYSICAL: blow.damage})
            parts[PHYSICAL] = parts.get(PHYSICAL, 0.0) * raised
            blow, raised = replace(blow, damage=sum(parts.values()), parts=parts), 1.0
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

    def hit(self, unit: int, points: float, *, by_pet: bool = False) -> bool:
        """The character's damage on a monster (`by_pet`: a demon's); True: it died now. Nothing comes off an immune
        one (but a demon's with IMMUNE_READ), a companion or a corpse. The pack is told what share of the monster's
        most life the hit took: a tick's hits may stagger it at the next tick, and a swing under way is then lost; a
        Lightning Enchanted one may let its sparks go (`Pack.struck`). One that dies may let a nova go
        (`Pack.died`), and an exploding one leaves its blast for the next tick."""
        mob = self.mobs.get(unit)
        if mob is None or unit not in self.pack.walkers or (mob.immune and not (by_pet and IMMUNE_READ)):
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
        if walker is not None and SHOWN_MOTION and mob.mode in PLAIN_MODES and walker.doing != casters.CAST:
            return self.motion_mode(mob, walker)
        if walker is None or walker.mind is None or walker.doing != casters.CAST or threats.of(mob.txt) is None:
            return mob.mode
        mind = walker.mind
        if mind.ai == casters.DIABLO:
            frames = casters.Minds._diablo_frames(mind.mode)
            begun = walker.until - frames - mind.delay
        elif mind.ai == casters.BAAL:
            from inventory_tracking.combat.sim import baal

            frames = baal.MODE_FRAMES.get(mind.mode, 0)
            begun = walker.until - baal.THINK_FRAMES  # [code] he thinks every 25 frames: his act began at the think
        else:
            frames = casters.MODE_FRAMES.get((mind.ai, mind.mode), 0)
            begun = walker.until - frames - mind.delay
        return CAST_MODES.get(mind.mode, mob.mode) if self.frame - 1 < begun + frames else mob.mode

    def motion_mode(self, mob: Mob, walker: Walker) -> int:
        """The mode the client shows a walker in while it moves, swings or reels (SHOWN_MOTION): walk (WL 2), the
        melee swing's frames as attack 1 (A1 4), get hit (GH 3); standing, a shooter's gap and a swing's rest the
        scene's own mode."""
        if walker.doing == WALK:
            return WALK_MODE
        if walker.doing == STAGGER:
            return GET_HIT_MODE
        if walker.doing == STRIKE and walker.unit not in self.pack.shots and walker.lands >= 0:
            frames = sim_monsters.swing_of(mob.txt)['frames']['value']
            begun = walker.lands - max(round(sim_monsters.fitted()['melee']['blow']['share'] * frames), 1)
            if self.frame - 1 < begun + frames:
                return CAST_MODES['A1']
        return mob.mode

    def flights(self, kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
        """The missiles in flight of the classes `kinds` as game/decode.py `flights` reads them: (owner unit,
        class, x, y)."""
        found = [(bolt.unit, bolt.missile, bolt.x, bolt.y) for bolt in self.pack.minds.bolts if bolt.missile in kinds]
        for missile in self.pack.flying:
            # A shooter's bolt of a named class (sim/monsters.py `Pack.bolts`) where it is on its way now
            if missile.kind in kinds and missile.origin is not None and missile.lands > missile.born:
                share = min(max((self.frame - missile.born) / (missile.lands - missile.born), 0.0), 1.0)
                x = missile.origin[0] + (missile.at[0] - missile.origin[0]) * share
                y = missile.origin[1] + (missile.at[1] - missile.origin[1]) * share
                if (x, y) != missile.origin:
                    found.append((missile.unit, missile.kind, x, y))
        return tuple(found)

    def monsters(self) -> list[Monster]:
        """The monsters as game/ reads them now: life in whole points, a dead one lying
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
                resists=((MAGIC_RESIST, 100),) if IMMUNE_READ and mob.immune else (),
                damage_percent=self.shown_percent(mob.unit),
            )
            for mob in self.mobs.values()
        ]

    def shown_percent(self, unit: int) -> int | None:
        """A hostile's stat 25 as the live client's full stat list shows it (game/decode.py, `Monster.damage_percent`,
        2026-10-22): the raise its blows play by (`_raised`): the take's reading where the scene carries them
        (`damage_percent`), else the auras round it (`auras`, AURA_FACTOR); 0 for none. None for a companion."""
        if unit not in self.hostile:
            return None
        return round((self._raised(unit) - 1.0) * 100)

    def corpses(self) -> tuple[tuple[int, float, float], ...]:
        """The monsters lying dead as (unit id, x, y), as `Run.corpses` gives them (world.corpses)."""
        return tuple((mob.unit, mob.at[0], mob.at[1]) for mob in self.mobs.values() if mob.mode == LYING_DEAD)
