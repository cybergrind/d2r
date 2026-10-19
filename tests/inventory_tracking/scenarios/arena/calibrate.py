"""Whether the arena may be believed (framework-plan.md, Task 1.9; architecture.md §6.2 C): a scene cut
from a recording, played with what the player really did, and what the arena's monsters did to the
character held against what the recording shows.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.calibrate
        [--root inventory_tracking/runs/combat] [--seconds 8] [--seeds 5]

runs `calibrate` over every fixture that has a `source` and writes fixtures/CALIBRATION.md (the table,
the spread of the ratios, what it says) and fixtures/trusted.json (scene -> whether it may be believed;
trust.py reads it).

**The play is open loop for the character and closed loop for the monsters.** No production macro code
runs. `recorded` reads from the take, tick by tick from the scene's frame (the build's sim/situation.py
`cut`: the recorder's samples as game ticks, the corpse rows left out):

- where the character stood (it is put there before each tick: not walked, not hopped);
- where its companions stood (the monsters go for the character or one of them: sim.monsters);
- its casts of Echoing Strike: the blades' first tick and the focal point fitted from the recorded
  blades (`Cast.fitted`), those still in the air when the scene starts among them;
- its belt keys (build_scenes.py `belt_keys`), drunk in the arena from the scene's belt, which is an
  assumption of every scene (cut.py DEFAULT_HERO);
- the weapon set in hand, from the resistances of the `hurt` events (cut.py `resists_at`, `hand_of`),
  where the take holds them; else the scene's stays;
- its life by tick, to measure against, and the deaths of the scene's hostiles.

`play` is `Arena` (game.py) driven without any of its inputs: the place, the hand and the companions
are set on it before each `Ticks.step`, a belt key is `Arena.drink`, and a cast is a `Flight` put in
`Arena.flights` with the production blades (`echoing_strike.cast`) from the recorded place to the
recorded focal point, returning to where the recording has the character then (the arena's own
`strike` returns them to where it stood at the cast, and takes its focal point from the fakes'
pointer). `Arena` can be driven this way as it is; nothing of it is copied here. Its monsters move,
strike and die by `Mobs` and by the damage of the replayed casts.

**Like with like.** A third of the life the takes lost is no blow at all: damage over time, a cost the
character pays itself (evidence/EVIDENCE.md, section 2: the drops with no suspect). The arena has
none of that and is not to: its blows are held against the take's drops *that have a suspect*
(evidence/blows.py: every drop of the take put on a striker, a missile's owner or a death, or on
nobody). So each scene has two comparisons: the raw one (all the life the take lost, as before the
refit of the monsters) and the attributed one (`Fit.taken_blamed`: the take's drops with a suspect;
the arena's side is the same in both, every point of it is a blow). The verdict goes by the
attributed one where the take's drops were attributed (`Fit.life_ratio`).

**What is compared.** The life the character lost (`life_lost`: the sum of the falls of its life from
tick to tick, in the take and in the arena alike, so a potion hides only what it gives within one
tick; a fall of the most life is not a blow, combat/hurts.py `lost`) and the scene's hostiles that
died. The window ends early where the comparison would stop being of the same thing: at the
character's death in the take or in the arena (the arena's world stands still from there), and where
the take leaves the level or ends.

A death of the character in the arena does not end the play: the potions replayed were drunk against
the take's blows, so it says the arena hit harder, not that the player would have died. The character
is raised with full life and the rest of the window is measured (`play`).

**The verdict.** `Fit.trusted` is the rule of the plan: both ratios within TRUST. The verdict written
to trusted.json (`Row.trusted`) asks two things more, which only ever take trust away: that it holds
with every one of SEEDS seeds of the monsters' rolls, and that the take holds no single drop the
scene's monsters cannot deal in the arena (BEYOND: the sums may agree while the blow that mattered is
not there, as in the one recorded death).

**What the method cannot see** (each named in a `Fit`'s notes where it applies):

- the monsters the scene does not hold: one further off than cut.py MOB_RANGE at the scene's frame,
  or one the character hopped to. Their blows are in the take's life and not in the arena's
  ("strangers");
- drift: the arena's monsters are not where the recording's were, the longer the more (WINDOW);
- the companions' damage (the arena's deal none: fewer kills there), and what the mercenary took
  instead of the character is only as good as its recorded place.
"""

import argparse
import json
import math
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from inventory_tracking.builds.warlock.echoing_strike.mechanics import LIFE, cast
from inventory_tracking.builds.warlock.echoing_strike.sim.situation import Situation, cut as situation_of
from inventory_tracking.combat.hurts import SUSPECT_REACH, hurts, lost, sole
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim.monsters import (
    AWARE,
    MELEE,
    PHYSICAL,
    SHOT,
    Blow,
    nova_points,
    spread as size_factor,
)
from inventory_tracking.combat.takes import Take, monsters_of
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.game.layout import LYING_DEAD, NO_OWNER
from inventory_tracking.macros.game.records import Monster
from inventory_tracking.native.layout import DEAD_MODES, PLAYER_DEAD_MODES
from tests.inventory_tracking.scenarios.arena.build_scenes import FIXTURES, REPO, ROOT, SCENE_FILE, belt_keys
from tests.inventory_tracking.scenarios.arena.cut import ALWAYS_ASSUMED, hand_of
from tests.inventory_tracking.scenarios.arena.evidence import blows as attribution, scan
from tests.inventory_tracking.scenarios.arena.game import SERVE, Arena, Flight
from tests.inventory_tracking.scenarios.arena.mobs import AURA_FACTOR, AURA_MOD, Mobs, shooter, shot_parts
from tests.inventory_tracking.scenarios.arena.scene import Scene, load


Point = tuple[float, float]
Vitals = tuple[float, float]  # life, most life

# Seconds compared. Long enough for the moment a scene was cut for to be inside it (moments.py LEAD:
# a scene starts 3 s before its burst, its death or its first potion) and for blows to add up; short
# enough that the monsters of the scene are still the ones that hurt the character. Measured over the
# 72 fixtures on 2026-10-12 (CALIBRATION.md, "The window": each played 15 s): the scenes whose take
# has lost MIN_TAKEN and has no stranger yet are 4 at 2 s, 26 at 4 s, 28 at 6 s, 25 at 8 s and at
# 10 s, 20 at 12 s; the scenes without a stranger fall from 64 to 49 by 8 s and to 33 by 12 s; and the
# median distance of a monster near the character from where the take has it is 4 to 6 units up to
# 8 s and 16 at 10 s. So 8 s: the last mark before the drift more than doubles, with as many scenes
# to measure as any.
WINDOW = 8.0
# Points of life lost in the take under which the ratio says nothing: a twentieth of the character's
# life (1783 in the takes of 2026-10-11), about one light blow. Under it the take holds no measurement
# to hold the arena against.
MIN_TAKEN = 90.0
TRUST = (0.5, 2.0)  # arena / take: within these the arena is believed
CAST_LEAD = LIFE  # ticks before the scene's frame whose casts are still in the air at it
# Units from the recorded character within which a hostile the scene does not hold is a stranger: the
# reach combat/hurts.py takes a striker for a suspect of a drop within.
STRANGER_REACH = SUSPECT_REACH
MIN_SECONDS = 2.0  # a comparison shorter than this is said to be short in the notes
# A drop of the take this many times the heaviest blow the scene's monsters can deal in the arena is
# one the arena cannot deal (two blows between two samples would be 2: the takes sample every tick,
# and a drop of two full top rolls at once is not what 1.5 lets through by chance). Such a scene is
# not believed whatever its ratios: the sums may agree while the blow that mattered is not there.
BEYOND = 1.5
BEYOND_NOTE = 'a blow the arena cannot deal'
MOSTLY_NOTE = 'mostly not blows'
BIG = 300.0  # points: a drop the evidence lists by itself (EVIDENCE.md, section 8)
# The share of the life a take lost that has a suspect under which the scene is said to be mostly
# not blows: the arena cannot be held against it whatever its monsters do.
MOSTLY = 0.5
LATE = 2  # ticks a window may end short of its length for a late last sample
UNREAD_SHARE = 0.25  # of the window's ticks without the character's life: more is said in the notes
REPORT = FIXTURES / 'CALIBRATION.md'
VERDICTS = FIXTURES / 'trusted.json'


@dataclass(frozen=True)
class Fit:
    """One scene's calibration: what the character lost and who died, in the take and in the arena."""

    scene: str
    seconds: float  # how long was compared
    taken_take: float  # life the character lost in the recording over the window (the sum of the falls)
    taken_arena: float  # the same in the arena
    kills_take: int  # hostiles of the scene that died in the recording within the window
    kills_arena: int
    notes: tuple[str, ...] = ()  # what limits this comparison
    # Of `taken_take`, the drops that have a suspect (evidence/blows.py: any class but `unknown`).
    # None: the take's drops were not attributed, and the raw comparison is all there is.
    taken_blamed: float | None = None

    @property
    def taken_ratio(self) -> float | None:
        """arena / take, raw; None when the take's is under MIN_TAKEN (nothing to measure against)."""
        return None if self.taken_take < MIN_TAKEN else self.taken_arena / self.taken_take

    @property
    def blamed_ratio(self) -> float | None:
        """arena / the take's drops that have a suspect; None when those are under MIN_TAKEN or the
        take's drops were not attributed."""
        if self.taken_blamed is None or self.taken_blamed < MIN_TAKEN:
            return None
        return self.taken_arena / self.taken_blamed

    @property
    def life_ratio(self) -> float | None:
        """The ratio the verdict goes by: like with like where the take's drops were attributed."""
        return self.taken_ratio if self.taken_blamed is None else self.blamed_ratio

    @property
    def kills_ratio(self) -> float | None:
        """arena / take. Nobody died in either: 1.0, they agree. Nobody died in the take and somebody
        in the arena: infinite. None only for a comparison of no length."""
        if self.seconds <= 0:
            return None
        if not self.kills_take:
            return math.inf if self.kills_arena else 1.0
        return self.kills_arena / self.kills_take

    @property
    def trusted(self) -> bool:
        """Both ratios known and within TRUST."""
        return all(ratio is not None and TRUST[0] <= ratio <= TRUST[1] for ratio in (self.life_ratio, self.kills_ratio))


def life_lost(samples: Iterable[Vitals | None]) -> float:
    """The life lost over a run of (life, most life) samples: the sum of the falls from one read sample
    to the next, so what a potion gives back between two blows hides nothing. A sample not read (None,
    or a most life of 0: the recorder's failed read shows 0 of 0) is skipped and the fall is counted
    across it. A fall that came with a fall of the most life (Consume ran out, the other weapons were
    taken) is not a blow as far as the life only kept its share: combat/hurts.py `lost`."""
    total, before = 0.0, None
    for sample in samples:
        if sample is None or not sample[1]:
            continue
        if before is not None:
            total += max(lost(before[0], before[1], sample[0], sample[1]), 0.0)  # type: ignore[arg-type]
        before = sample
    return total


@dataclass
class Replay:
    """What a calibration takes from a recording, by game tick from the scene's frame (tick 0)."""

    ticks: int  # ticks to play
    hero: list[Point]  # where the character stood at each tick, 0 to `ticks`
    vitals: list[Vitals | None]  # its life and most life at each tick; None: not read
    companions: list[list[tuple[int, int, Point]]] = field(default_factory=list)  # by tick: (unit, txt, place)
    casts: list[tuple[int, Point]] = field(default_factory=list)  # the blades' first tick (below 0: before), focal
    drinks: list[tuple[int, int]] = field(default_factory=list)  # (tick, belt column 1 to 4)
    hands: list[tuple[int, int]] = field(default_factory=list)  # (tick, index of the set in hand from then on)
    deaths: dict[int, int] = field(default_factory=dict)  # a hostile of the scene -> the tick it died at
    dead_at: int | None = None  # the tick the character lay dead at
    strangers: list[int] = field(default_factory=list)  # by tick: hostiles near the character the scene lacks
    left_at: int | None = None  # the first tick with a stranger, whether or not the window was cut there
    # The drops of the character's life in the window (combat/hurts.py `hurts`): (tick, points, the
    # type of the one monster striking alone or None when the drop cannot be put on one).
    drops: list[tuple[int, float, int | None]] = field(default_factory=list)
    # The same drops as evidence/blows.py classes them: (tick, points, class); None: not attributed.
    classed: list[tuple[int, float, str]] | None = None
    notes: list[str] = field(default_factory=list)

    def hero_at(self, tick: int) -> Point:
        return self.hero[min(max(tick, 0), len(self.hero) - 1)]


@dataclass
class Played:
    """What the arena made of a replay."""

    life: list[Vitals]  # the character's life and most life after each tick, from tick 0
    kills: dict[int, int]  # a hostile -> the tick it died at
    dead_at: int | None  # the tick the character died at (the first time)
    taken: float  # the blows' points as the arena counted them (`Arena.taken`)
    samples: list[Vitals] = field(default_factory=list)  # `life` with the full life of each rising: for `life_lost`
    deaths: int = 0  # times the character died
    # Every blow on the character: (tick, the striker's type, its kind, the points after the resistances
    # of the set in hand, before an aura's factor).
    blows: list[tuple[int, int, str, float]] = field(default_factory=list)
    # By tick, of the scene's hostiles the take has within AWARE of the character (those that come for
    # it): the median units between where the arena has one and where the take has it.
    apart: list[float] = field(default_factory=list)
    near: list[int] = field(default_factory=list)  # by tick: hostiles alive within STRANGER_REACH of the character
    near_take: list[int] = field(default_factory=list)  # the same in the take, of the scene's hostiles


def hostile_units(scene: Scene) -> list[int]:
    """The scene's hostiles alive at its frame."""
    return [
        mob.unit for mob in scene.mobs if mob.owner is None and not mob.ally and mob.mode != LYING_DEAD and mob.life > 0
    ]


def hands_of(take: Take, scene: Scene, start: float, tick_of: Callable[[float], int]) -> list[tuple[int, int]]:
    """(tick, the set in hand from then on) from the resistances the take's `hurt` events hold, from
    the scene's frame on (the scene's own hand is the reading before it: cut.py `cut`)."""
    found = []
    for event in take.events:
        if event['event'] == 'hurt' and event.get('resists') and event['t'] > start:
            found.append((tick_of(event['t']), hand_of([int(value) for value in event['resists']], scene.hero.sets)))
    return found


def recorded(
    scene: Scene,
    take: Take,
    seconds: float = WINDOW,
    *,
    leave: bool = True,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> Replay:
    """The replay of `seconds` of the take from the scene's frame: see the module text. The window is
    cut where the take ends, leaves the level or has the character dead, and (`leave`) where the
    recording leaves the scene: the tick before the first hostile the scene does not hold is within
    STRANGER_REACH of the character. `rows` are the take's drops as evidence/blows.py `blows` puts
    them on their suspects (`attributed`); without them the replay's drops have no class."""
    source = scene.source
    if source is None:
        raise ValueError(f'{scene.name}: a scene without a source has no recording to be held against')
    frames = take.frames
    index = source['frame']
    if not 0 <= index < len(frames):
        raise ValueError(f'{scene.name}: the take has no frame {index}')
    start = frames[index]['t']
    last = index
    while last + 1 < len(frames) and frames[last + 1]['t'] <= start + seconds + 0.5 / GAME_RATE:
        last += 1
    first = max(index - CAST_LEAD, 0)
    situation: Situation = situation_of(take, frames[first]['n'], frames[last]['n'], area=scene.hero.area)
    zero = situation.ticks[frames[index]['n']]
    wanted = round(seconds * GAME_RATE)
    ticks = min(wanted, situation.end - zero)
    notes = []

    def tick_of(t: float) -> int:
        return round((t - start) * GAME_RATE)

    hostile = set(hostile_units(scene))
    deaths: dict[int, int] = {}
    strangers = [0] * (ticks + 1)
    sampled = set()
    for frame in frames[index : last + 1]:
        tick = situation.ticks.get(frame['n'])
        if tick is None or not 0 <= tick - zero <= ticks:
            continue
        sampled.add(tick - zero)
        here = situation.player_at(tick)
        for monster in monsters_of(frame):
            if monster.unit in hostile:
                if monster.mode in DEAD_MODES and tick > zero:
                    deaths.setdefault(monster.unit, tick - zero)
            elif (
                monster.hostile
                and monster.at != (0.0, 0.0)
                and (monster.life or not monster.max_life)  # cut.py leaves out one with no life left
                and math.dist(monster.at, here) <= STRANGER_REACH
            ):
                strangers[tick - zero] += 1
    for event in take.events:
        if event['event'] == 'kill' and event['unit'] in hostile and start < event['t']:
            deaths.setdefault(event['unit'], tick_of(event['t']))
    for tick in range(1, ticks + 1):  # a late sample leaves a tick without a frame: what stood, stands
        if tick not in sampled:
            strangers[tick] = strangers[tick - 1]

    def dead(tick: int) -> bool:
        return situation.modes.get(tick) in PLAYER_DEAD_MODES or situation.vitals.get(tick, (1,))[0] <= 0

    dead_at = next((tick - zero for tick in range(zero + 1, zero + ticks + 1) if dead(tick)), None)
    met = next((tick for tick, count in enumerate(strangers) if count), None)
    if dead_at is not None and (met is None or dead_at < met or not leave):
        ticks = dead_at
        notes.append(f'the character died in the take at {dead_at / GAME_RATE:.1f} s')
    elif met is not None and leave:
        # From here the take's blows may be of monsters the arena does not have.
        ticks, dead_at = max(met - 1, 0), None
        notes.append(
            f'a hostile the scene lacks is within {STRANGER_REACH:.0f} of the character at {met / GAME_RATE:.1f} s'
        )
    elif ticks < wanted - LATE:
        notes.append(f'the take ends or leaves the level at {ticks / GAME_RATE:.1f} s')
    elif met is not None:
        held = sum(1 for count in strangers if count)
        notes.append(f'hostiles the scene lacks within {STRANGER_REACH:.0f} of the character in {held} ticks')
    strangers = strangers[: ticks + 1]

    vitals: list[Vitals | None] = []
    for tick in range(zero, zero + ticks + 1):
        seen = situation.vitals.get(tick)
        vitals.append(None if seen is None else (float(seen[0]), float(seen[1])))
    vitals[0] = (scene.hero.life, scene.hero.max_life)
    unread = sum(sample is None for sample in vitals)
    if ticks and unread / (ticks + 1) > UNREAD_SHARE:
        notes.append(f'life not read in {unread} of {ticks + 1} ticks')

    hero = [situation.player_at(tick) for tick in range(zero, zero + ticks + 1)]
    companions = [
        [(unit, track.txt, track.path[tick]) for unit, track in situation.companions.items() if tick in track.path]
        for tick in range(zero, zero + ticks + 1)
    ]
    casts = [(found.frame - zero, found.fitted) for found in situation.casts if found.frame - zero <= ticks]

    codes = sorted(belt_keys(take))
    drinks = [
        (tick_of(event['t']), codes.index(code) + 1)
        for event in take.events
        if event['event'] == 'keys' and start < event['t'] <= start + ticks / GAME_RATE
        for code in event.get('down') or ()
        if code in codes
    ]
    if not codes:
        notes.append('the belt keys are not known: no potion drunk')
    elif drinks:
        notes.append(f'{len(drinks)} belt keys replayed on the assumed belt')

    deaths = {unit: tick for unit, tick in deaths.items() if tick <= ticks}
    drops = []
    for hurt in hurts(replace(take, frames=frames[index : last + 1])):
        if tick_of(hurt['t']) <= ticks:
            alone = sole(hurt)
            drops.append((tick_of(hurt['t']), float(hurt['lost']), None if alone is None else int(alone[1])))
    classed = None
    if rows is not None:
        classed = [
            (tick_of(frames[row['frame']]['t']), float(row['lost']), str(row['class']))
            for row in rows
            if index < row['frame'] <= last and tick_of(frames[row['frame']]['t']) <= ticks
        ]
    moved = max((math.dist(hero[0], at) for at in hero), default=0.0)
    if moved > STRANGER_REACH:
        notes.append(f'the character went {moved:.0f} units from where the scene has it')
    told = sorted(set(scene.assumed) - set(ALWAYS_ASSUMED))
    if told:
        notes.append('assumed: ' + ', '.join(told))
    return Replay(
        ticks, hero, vitals, companions, casts, drinks, hands_of(take, scene, start, tick_of), deaths, dead_at,
        strangers, notes=notes, left_at=met, drops=drops, classed=classed,
    )  # fmt: skip


def attributed(take: Take, seen: scan.Sightings | None = None) -> list[dict[str, Any]]:
    """The take's drops, each put on its suspects (evidence/blows.py `blows`). `seen` are the terror
    probe logs' sightings (combat/hurts.py `sightings`), for the enchantments of a take recorded before
    it held them; without them a death with no missile of its own is not known to have been enchanted."""
    return attribution.blows(take, scan.enchantments(seen, take) if seen else None)


def recorded_places(take: Take, scene: Scene, ticks: int) -> list[dict[int, Point]]:
    """Where the take has each hostile of the scene, tick by tick while it lives (for the drift only)."""
    source = scene.source
    assert source is not None
    frames, index = take.frames, source['frame']
    start = frames[index]['t']
    hostile = set(hostile_units(scene))
    places: list[dict[int, Point]] = [{} for _ in range(ticks + 1)]
    for frame in frames[index:]:
        tick = round((frame['t'] - start) * GAME_RATE)
        if tick > ticks:
            break
        places[tick] = {m.unit: m.at for m in monsters_of(frame) if m.unit in hostile and m.alive}
    return places


def play(
    scene: Scene,
    replay: Replay,
    *,
    seed: int = 1,
    healing_scale: float = 1.0,
    damage_scale: float = 1.0,
    places: Sequence[Mapping[int, Point]] = (),
) -> Played:
    """The arena over a replay: the character where, with what in hand, casting and drinking as
    recorded; the monsters the arena's own.

    The arena's world stands still at the character's death, and the potions replayed were drunk
    against the take's blows, not the arena's: a death here says the arena hit harder, not that the
    player would have died. So that the rest of the window is still measured, the character is
    raised at once with full life and the play goes on (`Played.dead_at` keeps the first death,
    `deaths` their count); only the fatal blow is cut to the life that was left.

    `damage_scale` multiplies every blow on the character: the one factor the report's fit tries;
    nothing else uses it. `places` (the take's monsters by tick) only measures how far the arena's
    have drifted from them."""
    arena = Arena(scene, seed=seed, healing_scale=healing_scale)
    if damage_scale != 1.0:
        blows = arena.mobs.tick
        arena.mobs.tick = lambda *given: blows(*given) * damage_scale  # type: ignore[method-assign]
    for birth, focal in replay.casts:
        origin = replay.hero_at(birth)
        paths = cast(origin, focal, lambda k, born=birth: replay.hero_at(born + k), arena.walls)
        arena.flights.append(Flight(birth, paths, set(), [set() for _ in paths]))
    hands = dict(replay.hands)
    hostile = set(arena.mobs.hostile)
    first = (arena.life, arena.max_life)
    played = Played([first], {}, None, 0.0, samples=[first], apart=[0.0])
    step = arena.mobs.pack.step

    def watched(frame: int, targets: Sequence[Point]) -> list[Blow]:
        """The pack's step, with the blows on the character written down."""
        found = step(frame, targets)
        through = arena.resists[arena.hand]
        for blow in found:
            if blow.target == 0:
                parts = blow.parts or {PHYSICAL: blow.damage}
                points = sum(part * through.get(kind, 1.0) for kind, part in parts.items()) * damage_scale
                played.blows.append((frame + 1, arena.mobs.mobs[blow.unit].txt, blow.kind, points))
        return found

    arena.mobs.pack.step = watched  # type: ignore[method-assign]
    played.near.append(sum(1 for unit in arena.mobs.live() if _near(arena, unit, replay.hero[0])))
    for tick in range(1, replay.ticks + 1):
        stand = arena.world.player
        assert stand is not None
        x, y = replay.hero[tick]
        beside = replay.companions[tick] if tick < len(replay.companions) else []
        arena.world = replace(
            arena.world,
            player=replace(stand, x=x, y=y),
            monsters=(
                *(m for m in arena.world.monsters if m.unit_id in hostile),
                *(Monster(unit, txt, 1, at[0], at[1], NO_OWNER, ally=True) for unit, txt, at in beside),
            ),
        )
        if tick in hands:
            arena.hand = hands[tick]
        for at, column in replay.drinks:
            if at == tick:
                arena.drink(column, SERVE)
        known = len(arena.kills)
        arena.time.step()
        for unit in arena.kills[known:]:
            played.kills[unit] = tick
        played.life.append((arena.life, arena.max_life))
        played.samples.append((arena.life, arena.max_life))
        played.near.append(sum(1 for unit in arena.mobs.live() if _near(arena, unit, (x, y))))
        if tick < len(places):
            alive = set(arena.mobs.live())
            gaps = [
                math.dist(arena.mobs.mobs[unit].at, at)
                for unit, at in places[tick].items()
                if unit in alive and math.dist(at, (x, y)) <= AWARE
            ]
            played.apart.append(statistics.median(gaps) if gaps else math.nan)
            played.near_take.append(sum(1 for at in places[tick].values() if math.dist(at, (x, y)) <= STRANGER_REACH))
        if arena.dead_at is not None:
            played.dead_at = tick if played.dead_at is None else played.dead_at
            played.deaths += 1
            arena.over = arena.dead_at = None
            arena.life = arena.max_life
            arena.world = replace(arena.world, player=replace(arena.world.player, mode=stand.mode))  # type: ignore[arg-type]
            arena.show()
            played.samples.append((arena.life, arena.max_life))
    played.taken = arena.taken
    return played


def _near(arena: Arena, unit: int, here: Point) -> bool:
    return math.dist(arena.mobs.mobs[unit].at, here) <= STRANGER_REACH


def heaviest(scene: Scene) -> float:
    """The most one blow of the scene's monsters can take off the character in the arena, with the
    set the scene has in hand: a strike's top roll with the top of its enchantments' parts, or a
    shot, at the top of the fitted spread of a blow's size (sim.monsters `spread`), doubled where
    another monster of the scene has an aura (mobs.py AURA_FACTOR); or the doubled nova of a death."""
    through = scene.hero.sets[scene.hero.hand].resist
    units = hostile_units(scene)
    mobs = {mob.unit: mob for mob in scene.mobs}
    auras = [unit for unit in units if AURA_MOD in mobs[unit].mods]
    most = 0.0
    for unit in units:
        walker = Mobs._walker(mobs[unit])
        shoots = shooter(walker.txt)
        parts = dict(shot_parts(walker)) if shoots else {PHYSICAL: walker.traits.damage[1]}
        for element, _least, top in walker.traits.elements:
            parts[element] = parts.get(element, 0.0) + parts.get(PHYSICAL, 0.0) * top
        points = sum(part * through.get(kind, 1.0) for kind, part in parts.items())
        points *= size_factor(SHOT if shoots else MELEE, 1.0)
        most = max(most, points * (AURA_FACTOR if any(other != unit for other in auras) else 1.0))
        if walker.traits.nova:
            most = max(most, 2 * nova_points(walker.traits.level) * through.get('cold', 1.0))
    return most


def compare(scene: Scene, replay: Replay, played: Played) -> Fit:
    """The two sides over the replay's ticks."""
    ticks = replay.ticks
    notes = list(replay.notes)
    if played.dead_at is not None:
        again = f', {played.deaths} times in all' if played.deaths > 1 else ''
        notes.append(f'the character died in the arena at {played.dead_at / GAME_RATE:.1f} s{again}')
    taken_take = life_lost(replay.vitals)
    if taken_take < MIN_TAKEN:
        notes.append(f'the take holds under {MIN_TAKEN:.0f} points of life lost: no ratio')
    if ticks < MIN_SECONDS * GAME_RATE:
        notes.append(f'compared for under {MIN_SECONDS:.0f} s')
    drop, blow = max((points for _tick, points, _txt in replay.drops), default=0.0), heaviest(scene)
    if drop > BEYOND * blow:
        notes.append(f'{BEYOND_NOTE}: a drop of {drop:.0f} points in the take, at most {blow:.0f} a blow in the arena')
    blamed = None
    if replay.classed is not None:
        blamed = sum(points for _tick, points, group in replay.classed if group != attribution.NONE)
        if taken_take >= MIN_TAKEN and blamed < MOSTLY * taken_take:
            notes.append(f'{MOSTLY_NOTE}: {blamed:.0f} of the {taken_take:.0f} points the take lost have a suspect')
    return Fit(
        scene.name, ticks / GAME_RATE, taken_take, life_lost(played.samples), len(replay.deaths), len(played.kills),
        tuple(notes), blamed,
    )  # fmt: skip


def calibrate(
    scene: Scene,
    take: Take,
    seconds: float = WINDOW,
    *,
    seed: int = 1,
    healing_scale: float = 1.0,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> Fit:
    """The scene played open loop over `seconds` of its take, against the take: see the module text.
    `rows`: the take's drops attributed (`attributed`), for the comparison of like with like."""
    replay = recorded(scene, take, seconds, rows=rows)
    return compare(scene, replay, play(scene, replay, seed=seed, healing_scale=healing_scale))


# -- the report ------------------------------------------------------------------------------------

SEEDS = 5  # the monsters' rolls a scene is played with: a verdict that turns with the seed is no verdict
LONG = 15.0  # seconds the window's measurement plays, without leaving at the first stranger
MARKS = (2, 4, 6, 8, 10, 12, 15)  # seconds at which the window's measurement looks
ENOUGH = 3  # scenes at least for a group to have a row of its own


@dataclass
class Row:
    """One scene's calibration with what the report says of it."""

    scene: Scene
    fits: list[Fit]  # by seed, the first is the table's
    replay: Replay
    played: Played  # the first seed's
    bigs: list[int] = field(default_factory=list)  # by seed: the falls of the arena's life of BIG points or more

    @property
    def fit(self) -> Fit:
        return self.fits[0]

    @property
    def kind(self) -> str:
        return self.scene.name.rsplit('-', 1)[1]

    @property
    def beyond(self) -> bool:
        """The take holds a blow the arena cannot deal here (BEYOND)."""
        return any(note.startswith(BEYOND_NOTE) for note in self.fit.notes)

    @property
    def trusted(self) -> bool:
        """The verdict of trusted.json: believed with every seed (`Fit.trusted`), and no blow in the
        take that the arena cannot deal. Both only ever take a scene's trust away."""
        return all(fit.trusted for fit in self.fits) and not self.beyond

    @property
    def raw_trusted(self) -> bool:
        """The same verdict by the raw comparison (all the life the take lost): the rule before the refit."""
        return all(replace(fit, taken_blamed=None).trusted for fit in self.fits) and not self.beyond

    @property
    def mostly_not_blows(self) -> bool:
        return any(note.startswith(MOSTLY_NOTE) for note in self.fit.notes)


def big_falls(played: Played) -> int:
    """The ticks in which the arena's character lost BIG points or more."""
    return sum(1 for before, after in zip(played.life, played.life[1:], strict=False) if before[0] - after[0] >= BIG)


def big_table(rows: Sequence[Row]) -> list[str]:
    """Drops of BIG points or more in the compared windows: the takes', by class, and the arena's."""
    seconds = sum(row.fit.seconds for row in rows)
    take = [(points, group) for row in rows for _tick, points, group in (row.replay.classed or ()) if points >= BIG]
    blamed = [points for points, group in take if group != attribution.NONE]
    seeds = max((len(row.bigs) for row in rows), default=0)
    arena = [sum(row.bigs[seed] for row in rows if seed < len(row.bigs)) for seed in range(seeds)]
    by_class = Counter(group for _points, group in take)
    return [
        f'| | drops of {BIG:.0f} or more | per 10,000 s | largest |',
        '| --- | ---: | ---: | ---: |',
        f'| the takes, all | {len(take)} | {len(take) * 10_000 / seconds:.0f} '
        f'| {max((p for p, _g in take), default=0):.0f} |',
        f'| the takes, with a suspect | {len(blamed)} | {len(blamed) * 10_000 / seconds:.0f} '
        f'| {max(blamed, default=0):.0f} |',
        f'| the arena, mean of {seeds} seeds | {statistics.fmean(arena) if arena else 0:.1f} '
        f'| {(statistics.fmean(arena) if arena else 0) * 10_000 / seconds:.0f} | - |',
        '',
        f"The takes' by class: {', '.join(f'{group} {count}' for group, count in by_class.most_common()) or 'none'}. "
        f"The arena's by seed: {', '.join(str(count) for count in arena) or 'none'}. {seconds:.0f} s of windows; they "
        "were cut around bursts, potions and deaths, so the rate is far above a whole take's (20 in 19,097 s).",
    ]


def type_name(txt: int) -> str:
    """A monster type by the tables' name, with its id (two rows may share a name)."""
    name = tables()['monsters'].get(str(txt), {}).get('NameStr')
    return f'{name} ({txt})' if name else f'type {txt}'


def dominant(scene: Scene) -> int:
    """The type most of the scene's hostiles are of (the lower id of two as many)."""
    units = set(hostile_units(scene))
    count = Counter(mob.txt for mob in scene.mobs if mob.unit in units)
    return min(count, key=lambda txt: (-count[txt], txt))


def number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return '-'
    return 'inf' if math.isinf(value) else f'{value:.{digits}f}'


def spread(values: Sequence[float]) -> str:
    """n, least, lower quartile, median, upper quartile, most."""
    if not values:
        return '0 | - | - | - | - | -'
    found = sorted(values)
    low, _half, high = statistics.quantiles(found, n=4, method='inclusive') if len(found) > 1 else (found[0],) * 3
    cells = (found[0], low, statistics.median(found), high, found[-1])
    return f'{len(found)} | ' + ' | '.join(number(cell) for cell in cells)


def pooled(fits: Sequence[Fit], blamed: bool = False) -> float | None:
    """All the arena's points over all the take's (`blamed`: over the take's drops with a suspect):
    what a ratio per scene cannot say of the scenes where the take lost nothing."""
    take = sum((fit.taken_blamed or 0.0) if blamed else fit.taken_take for fit in fits)
    return sum(fit.taken_arena for fit in fits) / take if take else None


def groups(rows: Sequence[Row], key: Callable[[Row], str]) -> list[tuple[str, list[Row]]]:
    found: dict[str, list[Row]] = {}
    for row in rows:
        found.setdefault(key(row), []).append(row)
    return sorted(found.items(), key=lambda item: (-len(item[1]), item[0]))


def ratio_table(title: str, sets: Sequence[tuple[str, Sequence[Row]]], blamed: bool = False) -> list[str]:
    """The spread of the life-lost ratios by group: raw, or (`blamed`) against the take's drops with a suspect."""
    lines = [
        f'| {title} | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled '
        '| arena hurt, take did not | kills: n | median | pooled |',
        '| --- | ' + ' | '.join(['---:'] * 13) + ' |',
    ]
    for name, rows in sets:
        fits = [row.fit for row in rows]
        every = [fit.blamed_ratio if blamed else fit.taken_ratio for fit in fits]
        ratios = [ratio for ratio in every if ratio is not None]
        silent = sum(
            1 for fit, ratio in zip(fits, every, strict=True) if ratio is None and fit.taken_arena >= MIN_TAKEN
        )
        kills = [ratio for fit in fits if fit.kills_take and (ratio := fit.kills_ratio) is not None]
        killed = sum(fit.kills_take for fit in fits)
        lines.append(
            f'| {name} | {len(rows)} | {sum(row.trusted for row in rows)} | {spread(ratios)} '
            f'| {number(pooled(fits, blamed))} '
            f'| {silent} | {len(kills)} | {number(statistics.median(kills) if kills else None)} '
            f'| {number(sum(fit.kills_arena for fit in fits) / killed if killed else None)} |'
        )
    return lines


def scene_table(rows: Sequence[Row]) -> list[str]:
    lines = [
        '| scene | kind | area | hostiles | seconds | taken take | taken arena | ratio | take, with a suspect '
        '| ratio | kills take | kills arena | ratio | trusted | notes |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | --- | --- | --- |',
    ]
    for row in rows:
        fit, scene = row.fit, row.scene
        seen = [found.taken_ratio for found in row.fits if found.taken_ratio is not None]
        over = f' ({number(min(seen))} to {number(max(seen))})' if len(seen) > 1 else ''
        like = [found.blamed_ratio for found in row.fits if found.blamed_ratio is not None]
        like_over = f' ({number(min(like))} to {number(max(like))})' if len(like) > 1 else ''
        blamed = '-' if fit.taken_blamed is None else f'{fit.taken_blamed:.0f}'
        held = sum(found.trusted for found in row.fits)
        verdict = 'yes' if row.trusted else 'no' if not held else f'no ({held} of {len(row.fits)} seeds)'
        if held == len(row.fits) and row.beyond:
            verdict = 'no (a blow the arena cannot deal)'
        lines.append(
            f'| {scene.name} | {row.kind} | {display_name(scene.hero.area)} ({scene.hero.area}) '
            f'| {len(hostile_units(scene))}, most {type_name(dominant(scene))} | {fit.seconds:.1f} '
            f'| {fit.taken_take:.0f} | {fit.taken_arena:.0f} | {number(fit.taken_ratio)}{over} '
            f'| {blamed} | {number(fit.blamed_ratio)}{like_over} '
            f'| {fit.kills_take} | {fit.kills_arena} | {number(fit.kills_ratio)} | {verdict} | {"; ".join(fit.notes)} |'
        )
    return lines


def why_not(rows: Sequence[Row]) -> list[str]:
    """What kept the scenes not believed from it, counted (the first that applies, on the first seed)."""
    count: Counter[str] = Counter()
    for row in rows:
        fit = row.fit
        if row.trusted:
            continue
        if fit.life_ratio is None and fit.taken_arena >= MIN_TAKEN:
            count[
                f'the take lost under {MIN_TAKEN:.0f} points to blows and the arena took {MIN_TAKEN:.0f} or more'
            ] += 1
        elif fit.life_ratio is None:
            count[f'neither lost {MIN_TAKEN:.0f} points to blows: nothing to measure'] += 1
        elif fit.life_ratio > TRUST[1]:
            count[f'the arena took over {TRUST[1]:g} times the take'] += 1
        elif fit.life_ratio < TRUST[0]:
            count[f'the arena took under {TRUST[0]:g} of the take'] += 1
        elif fit.kills_ratio is None or not TRUST[0] <= fit.kills_ratio <= TRUST[1]:
            count['the life lost agrees, the kills do not'] += 1
        elif not all(found.trusted for found in row.fits):
            count['believed with the first seed, not with every one'] += 1
        else:
            count[f'both ratios agree with every seed, but the take holds {BEYOND_NOTE}'] += 1
    return [f'- {reason}: {found}' for reason, found in count.most_common()]


def blow_table(rows: Sequence[Row]) -> list[str]:
    """The blows by the type that struck: the arena's, each one, by its kind (a strike, a shot, a
    spark); the take's drops that one monster striking alone explains (combat/hurts.py `sole`), and
    all its drops in the last row."""
    arena: dict[tuple[int, str], list[float]] = {}
    take: dict[int | None, list[float]] = {}
    seconds = sum(row.fit.seconds for row in rows)
    for row in rows:
        for _tick, txt, kind, points in row.played.blows:
            arena.setdefault((txt, kind), []).append(points)
        for _tick, points, txt in row.replay.drops:
            take.setdefault(txt, []).append(points)
    lines = [
        '| striker | arena: kind | blows | median | points | take: drops put on it | median | points |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]

    def cells(found: Sequence[float]) -> str:
        return f'{len(found)} | {number(statistics.median(found) if found else None, 0)} | {sum(found):.0f}'

    told = set()
    for (txt, kind), found in sorted(arena.items(), key=lambda item: -sum(item[1])):
        theirs = () if txt in told else take.get(txt, ())  # a type's drops stand in its first row
        told.add(txt)
        lines.append(f'| {type_name(txt)} | {kind} | {cells(found)} | {cells(theirs)} |')
    for txt in sorted(t for t in take if t is not None and t not in told):
        lines.append(f'| {type_name(txt)} | - | {cells(())} | {cells(take[txt])} |')
    for kind in sorted({kind for _txt, kind in arena}):
        every = [points for (_txt, found_kind), found in arena.items() if found_kind == kind for points in found]
        lines.append(f'| every {kind} | {kind} | {cells(every)} | - | - | - |')
    every_arena = [points for found in arena.values() for points in found]
    every_take = [points for found in take.values() for points in found]
    lines.append(f'| all, {seconds:.0f} s of {len(rows)} scenes | | {cells(every_arena)} | {cells(every_take)} |')
    return lines


def window_table(found: Sequence[tuple[Replay, Played]]) -> list[str]:
    """What a longer or a shorter window would compare, from plays of LONG seconds that do not leave
    at the first stranger: see WINDOW."""
    lines = [
        '| seconds | scenes still recorded | of them no stranger yet | of those, the take lost enough '
        f'| median units a monster is from its recording | hostiles within {STRANGER_REACH:.0f}: take | arena |',
        '| ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for mark in MARKS:
        tick = round(mark * GAME_RATE)
        there = [(replay, played) for replay, played in found if replay.ticks >= tick - LATE]
        own = [(replay, played) for replay, played in there if replay.left_at is None or replay.left_at > tick]
        enough = sum(1 for replay, _played in own if life_lost(replay.vitals[: tick + 1]) >= MIN_TAKEN)

        def at_mark(series: Callable[[Played], Sequence[float]], own=own, tick=tick) -> list[float]:
            values = [series(played)[min(tick, len(series(played)) - 1)] for _replay, played in own if series(played)]
            return [value for value in values if not math.isnan(value)]

        apart = at_mark(lambda played: played.apart)
        lines.append(
            f'| {mark} | {len(there)} | {len(own)} | {enough} '
            f'| {number(statistics.median(apart) if apart else None, 1)} '
            f'| {number(statistics.fmean(at_mark(lambda played: played.near_take)) if own else None, 1)} '
            f'| {number(statistics.fmean(at_mark(lambda played: played.near)) if own else None, 1)} |'
        )
    return lines


def curve(row: Row, step: float = 0.5) -> list[str]:
    """A scene's life in the take and in the arena, `step` seconds apart, and what took it."""
    replay, played = row.replay, row.played
    lines = [
        '| seconds | life in the take | life in the arena (seed 1) '
        f'| hostiles within {STRANGER_REACH:.0f} in the arena |',
        '| ---: | ---: | ---: | ---: |',
    ]
    marks = [round(k * step * GAME_RATE) for k in range(int(replay.ticks / GAME_RATE / step) + 1)]
    for tick in sorted({*marks, replay.ticks}):
        read = next((replay.vitals[at] for at in range(tick, -1, -1) if replay.vitals[at] is not None), None)
        ours = played.life[min(tick, len(played.life) - 1)]
        lines.append(
            f'| {tick / GAME_RATE:.2f} | {"-" if read is None else f"{read[0]:.0f}"} | {ours[0]:.0f} '
            f'| {played.near[min(tick, len(played.near) - 1)]} |'
        )
    drops = ', '.join(
        f'{points:.0f} at {tick / GAME_RATE:.2f} s' + ('' if txt is None else f' ({type_name(txt)})')
        for tick, points, txt in replay.drops
    )
    blows = ', '.join(
        f'{points:.0f} at {tick / GAME_RATE:.2f} s ({type_name(txt)}, {kind})'
        for tick, txt, kind, points in played.blows
    )
    drinks = ', '.join(f'column {column} at {tick / GAME_RATE:.2f} s' for tick, column in replay.drinks)
    return [
        *lines,
        '',
        f'- drops in the take: {drops or "none"}',
        f'- blows in the arena, before an aura: {blows or "none"}',
        f'- belt keys: {drinks or "none"}',
    ]


def scale_fit(
    rows: Sequence[Row], takes: Mapping[str, Take], seconds: float, drops: Mapping[str, Sequence[Mapping[str, Any]]]
) -> list[str]:
    """One factor on every blow that would centre the ratio the verdict goes by (`Fit.life_ratio`):
    found on every other scene with a ratio, tried on the rest. `play`'s `damage_scale` only: nothing of
    the arena is changed."""
    ratioed = [row for row in rows if row.fit.life_ratio is not None]
    with_ratio = [row for row in ratioed if row.fit.taken_arena > 0]
    halves = (with_ratio[::2], with_ratio[1::2])
    if not all(halves):
        return ['Too few scenes with a ratio to fit anything.']
    centre = statistics.median(ratio for row in halves[0] if (ratio := row.fit.life_ratio) is not None)
    factor = 1 / centre
    lines = [
        f'Of the {len(ratioed)} scenes with a ratio, the {len(ratioed) - len(with_ratio)} where the arena took nothing '
        'are left out (no factor moves them); the rest are split in two by every other name. The median ratio of',
        f'the {len(halves[0])} scenes fitted on is {centre:.2f}: a factor of **{factor:.2f}** on every blow would '
        'centre it. Played again with it (`play`, `damage_scale`; first seed; "trusted" here is the bare rule of',
        'the two ratios):',
        '',
        '| half | scenes | median before | median with the factor | trusted before | trusted with the factor '
        '| least | most |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for name, half in zip(('fitted on', 'checked on'), halves, strict=True):
        after = []
        for row in half:
            source = row.scene.source
            assert source is not None
            replay = recorded(row.scene, takes[source['take']], seconds, rows=drops.get(source['take']))
            after.append(compare(row.scene, replay, play(row.scene, replay, damage_scale=factor)))
        ratios = [fit.life_ratio for fit in after if fit.life_ratio is not None]
        lines.append(
            f'| {name} | {len(half)} | {statistics.median(row.fit.life_ratio for row in half):.2f} '  # type: ignore[type-var]
            f'| {statistics.median(ratios):.2f} | {sum(row.fit.trusted for row in half)} '
            f'| {sum(fit.trusted for fit in after)} | {number(min(ratios))} | {number(max(ratios))} |'
        )
    return lines


def report(
    rows: Sequence[Row], window: Sequence[tuple[Replay, Played]], fitted: Sequence[str], root: Path, seconds: float
) -> str:
    believed = sum(row.trusted for row in rows)
    shown = root.resolve().relative_to(REPO) if root.resolve().is_relative_to(REPO) else root
    lines = [
        '# Calibration of the arena',
        '',
        'Written by `tests/inventory_tracking/scenarios/arena/calibrate.py` (its module text says how a scene is',
        f'played and what is compared) from the takes under `{shown}` on {time.strftime("%Y-%m-%d")}: every fixture',
        f'with a `source`, {seconds:g} s from its frame, the monsters rolled with seeds 1 to {SEEDS}. The table is the',
        'first seed; a ratio is arena / take, with its least and most over the seeds in brackets. A scene is',
        f'**trusted** when, with every seed, both ratios are within {TRUST[0]:g} to {TRUST[1]:g} (the life-lost ratio',
        f'is not formed when the take lost under {MIN_TAKEN:.0f} points) and the take holds no single drop over',
        f"{BEYOND:g} times the heaviest blow the scene's monsters can deal in the arena. `trusted.json` holds the",
        'verdicts; `trust.py` reads them.',
        '',
        f"**Trusted: {believed} of {len(rows)} scenes** by the comparison of like with like (the arena's blows",
        "against the take's drops that have a suspect: `evidence/blows.py`; the module text of calibrate.py);",
        f'**{sum(row.raw_trusted for row in rows)}** by the raw comparison (all the life the take lost, the rule',
        'before the refit of the monsters). Of those not trusted, by like with like:',
        '',
        *why_not(rows),
        '',
        f'Scenes whose take lost {MIN_TAKEN:.0f} points or more of which under {MOSTLY:g} have a suspect',
        f'("{MOSTLY_NOTE}": the arena has nothing to hold against them, whatever its monsters do): '
        + (', '.join(row.scene.name for row in rows if row.mostly_not_blows) or 'none')
        + '.',
        '',
        '## What this says',
        '',
        READING.strip(),
        '',
        '## The scenes',
        '',
        *scene_table(rows),
        '',
        '## The ratios',
        '',
        '"Pooled" is all the arena\'s points over all the take\'s in the group, the scenes without a ratio of',
        'their own among them. The kills columns are of the scenes where a hostile died in the take. Each',
        "table is given twice: like with like (the take's drops with a suspect), then raw (all its life lost).",
        '',
        '### Like with like',
        '',
        *ratio_table('all', [('all', rows)], True),
        '',
        *ratio_table('kind', groups(rows, lambda row: row.kind), True),
        '',
        "By the type most of the scene's hostiles are of:",
        '',
        *ratio_table('most hostiles', groups(rows, lambda row: type_name(dominant(row.scene))), True),
        '',
        '### Raw',
        '',
        *ratio_table('all', [('all', rows)]),
        '',
        *ratio_table('kind', groups(rows, lambda row: row.kind)),
        '',
        "By the type most of the scene's hostiles are of:",
        '',
        *ratio_table('most hostiles', groups(rows, lambda row: type_name(dominant(row.scene)))),
        '',
        f'The types with {ENOUGH} scenes or more, by what the arena makes of them (like with like):',
        '',
        *ratio_table(
            'most hostiles',
            sorted(
                (
                    group
                    for group in groups(rows, lambda row: type_name(dominant(row.scene)))
                    if len(group[1]) >= ENOUGH
                ),
                key=lambda group: -(pooled([row.fit for row in group[1]], True) or 0.0),
            ),
            True,
        ),
        '',
        '## The big drops',
        '',
        *big_table(rows),
        '',
        '## The blows, by who struck',
        '',
        'Over the compared windows, first seed. An arena blow is one strike, shot or spark after the',
        'resistances of the set in hand. A drop of the take is the life gone between two samples (several',
        'blows landing together are one drop); it is put on a type only when one monster alone was striking',
        "(`combat/hurts.py` `sole`), so the take's rows by type are a part of its drops: the last row has all,",
        'the drops nobody is blamed for among them.',
        '',
        *blow_table(rows),
        '',
        '## The window',
        '',
        f'Each scene played for {LONG:g} s without leaving at the first stranger (a hostile the scene does not',
        f'hold within {STRANGER_REACH:g} units of the recorded character). "Still recorded": the take is in the',
        'level and the character alive.',
        '',
        *window_table(window),
    ]
    for row in rows:
        if row.kind == 'death':
            lines += ['', f'## The death: {row.scene.name}', '', *curve(row)]
    lines += ['', '## One factor on every blow', '', *fitted, '']
    return '\n'.join(lines)


# What the run of 2026-10-12 after the refit of the monsters says, by hand, from the tables it wrote (72
# fixtures, 8 s, seeds 1 to 5). The numbers in it are that run's: when the tables move, this is to be
# read again against them. (The reading of the run before the refit is in git: the arena took 3.17 times
# the takes in sum, median 1.86, 1 scene trusted.)
READING = """
*Read by hand from the tables below as they stood on 2026-10-12, after the monsters were refitted to the
train half of all takes (`combat/sim/monsters.py`, `evidence/EVIDENCE.md`); a later run rewrites the
tables, not this text. Five of the 72 scenes are not those of the run before the refit: the fixtures
were cut again (cut.py's main set now has its physical resistance) and five newer takes took the place
of five older ones.*

**The arena is no longer three times too harsh; by these windows it is not believable either: 3 scenes
of 72, and the windows cannot say more.** What the monsters do on average is judged elsewhere, on
time that was not chosen for what happened in it: `evidence/refit_check.py` lays each mechanism beside
the check half of all takes, and there the pooled swings, shots, novas and targets are within 0.75 to
1.3 of the measured. Here:

1. **From 3.17 times the takes to 0.48, like with like** (all the arena's points over the take's drops
   that have a suspect; 0.42 raw). The median scene ratio went from 1.86 to 0.15, the quartiles from
   0.75 and 4.01 to 0.05 and 0.73. The arena's character died in 17 windows before and in 1 now; the
   takes' in 2. The arena lands 117 blows where it landed 688 (the takes: 128 drops).
2. **The windows were chosen for what happened in them, and it shows both ways.** 32 scenes were cut
   because the take lost life there (a burst, potions drunk, the death); 40 for something else (a long
   fight, a stuck hunt). With each scene played 30 times and the mean taken (a run by hand, not in the
   tables): in the 32 the arena takes 0.30 of the take's drops with a suspect (5,251 against 17,636
   points), in the 40 it takes 2.4 times (2,307 against 961). A model with the right mean does that
   on windows picked by their outcome: it cannot be told from these fixtures how far the mean is off,
   only that it is not off by three any more. Scenes cut at fixed times, whatever happened, would say.
3. **One window is mostly luck now, as it is in the game.** A swing takes life one time in six, a shot
   one in seventy: 8 s hold 0 to 5 blows of the arena. Over 30 seeds a scene with a ratio is within 0.5 to
   2 in 15% of its plays. The rule of this file (every seed within the bounds) asks for what the
   game itself would not give if the same eight seconds were played twice. Trust by scene is the
   wrong instrument for a model that rolls; a verdict by mechanism (refit_check) or over many windows
   pooled is the right one.
4. **The takes' losses come in clusters, the arena's blows one by one.** 13 drops of 300 points or
   more with a suspect in these windows, 9 of them shared between several strikers; the arena has 5 a
   seed. Where the take lost 1,829 points in 8 s to a pack of Hell Temptresses the arena takes 90: its
   mean for that pack is about 190, the take's eight seconds were ten times that. Rolls that do not
   know of each other do not make such seconds. What makes them is not in a take: a curse, the
   character's protection gone, a stand in the middle of a pack. The recorder writing the character's
   state list would show it.
5. **The sparks of a Lightning Enchanted monster were not refitted and are now the largest part.** 75 of
   the arena's 117 blows, 3,207 of its 9,136 points; every spark that touches the character lands
   (sim/monsters.py: measured on one Herald for where they fly, never for what they take). The one
   scene the arena is far too harsh in (20261011T195037Z-25-373-potions: 4 times the take's blows, the
   character dead in 24 of 30 plays) is the Herald's sparks.
6. **The death (20261011T195037Z-25-493).** The take: one drop of 1,051 at 3.0 s, the tier 2 Herald in
   an attack mode 8.9 units off. Before the refit no monster of the scene could deal it (370 at most)
   and none reached further than 3.2 units. Now the Herald's blow goes up to 1,650 and a swing may be
   begun from up to 12 units; played 400 times (by hand), the arena's character dies in the three
   seconds in 8 plays, loses 500 points or more in 36 and nothing in 186. In the table's first seed it
   loses nothing. So it can die where the recorded one died, and seldom does: the arena does not
   know what made that blow either.
7. **By type** (like with like, the tables below): Ice Spawn scenes pool at 0.83 and hold 2 of the 3
   trusted scenes, Ghost 1.05, Devilkin 1.12 (one nova on the staff's set carries it); the scenes led
   by shooters are low (Dark Archer 0.08, Hell Temptress 0.18), and so are Returned (0.07). All of
   these are scenes of the kinds chosen for their bursts. Black Soul's factor of 5 on every shot was
   not refitted (the takes hold 34 of its shots and no hit of one alone).
8. **The kills did not move** (median 0.78, pooled 0.81 of 58 scenes): they are the character's
   doing and the companions', which this refit did not touch.

**What limits the measurement itself.** 41 scenes have under 90 points lost to blows in the take and
in the arena alike. 3 scenes are mostly not blows (named above): their take lost 168 to 1,479 points
of which under half have a suspect. 19 windows end early at a hostile the scene does not hold; the
scenes of one moment cut three times (20261012T065226Z-130-4606, -4609, -4612) count three times.

**What would make the arena believable for a safety rule, in order:** (a) scenes cut at fixed times,
so that the mean can be checked on windows not chosen by their outcome; (b) the character's state
list in the takes (curses, the protection it has up), so that the clusters can be modelled instead
of averaged; (c) the sparks fitted like the swings; (d) more play against the types that still use the
pooled rows (all but 5 melee types and 3 shooters have their own chance to take life).
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Hold the arena against the takes its scenes were cut from.')
    parser.add_argument('--root', type=Path, default=ROOT, help='the takes (default: runs/combat)')
    parser.add_argument('--fixtures', type=Path, default=FIXTURES, help='the scenes, and where the report goes')
    parser.add_argument('--seconds', type=float, default=WINDOW, help='the window compared')
    parser.add_argument('--seeds', type=int, default=SEEDS, help='seeds of the monsters each scene is played with')
    parser.add_argument(
        '--probes', type=Path, default=scan.PROBES, help='the terror probe logs: the enchantments of the earlier takes'
    )
    args = parser.parse_args(argv)

    began = time.monotonic()
    paths = sorted(path for path in args.fixtures.glob('*.json') if SCENE_FILE.fullmatch(path.name))
    rows: list[Row] = []
    window: list[tuple[Replay, Played]] = []
    takes: dict[str, Take] = {}
    drops: dict[str, list[dict[str, Any]]] = {}
    logs = sorted(args.probes.glob('*/terror-probe.jsonl'))
    seen = scan.probe_sightings(logs, scan.CACHE if scan.CACHE.is_dir() else None)
    missing = []
    for count, path in enumerate(paths, 1):
        scene = load(path)
        if scene.source is None:
            continue
        name = scene.source['take']
        print(f'\rscenes {count}/{len(paths)} {scene.name:<48}', end='', file=sys.stderr)
        if name not in takes:
            try:
                takes[name] = Take.load(args.root / name)
            except (OSError, ValueError, EOFError, KeyError) as exc:
                missing.append(f'{scene.name}: the take was not read ({type(exc).__name__})')
                continue
        take = takes[name]
        if name not in drops:
            drops[name] = attributed(take, seen)
        replay = recorded(scene, take, args.seconds, rows=drops[name])
        plays = [play(scene, replay, seed=seed) for seed in range(1, args.seeds + 1)]
        fits = [compare(scene, replay, played) for played in plays]
        rows.append(Row(scene, fits, replay, plays[0], [big_falls(played) for played in plays]))
        long = recorded(scene, take, LONG, leave=False)
        window.append((long, play(scene, long, places=recorded_places(take, scene, long.ticks))))
    print(file=sys.stderr)
    if missing:
        print('\n'.join(missing), file=sys.stderr)
        return 1
    fitted = scale_fit(rows, takes, args.seconds, drops)
    (args.fixtures / REPORT.name).write_text(report(rows, window, fitted, args.root, args.seconds), encoding='utf-8')
    verdicts = {row.scene.name: row.trusted for row in rows}
    (args.fixtures / VERDICTS.name).write_text(json.dumps(verdicts, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    believed = sum(verdicts.values())
    print(f'{len(rows)} scenes, {believed} trusted, {time.monotonic() - began:.0f} s: {args.fixtures / REPORT.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
