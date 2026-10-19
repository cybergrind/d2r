"""A moment of a schema 4 take played again in the arena from the take alone (combat/record.py, schema 4;
rca/2026-10-13/replay-readiness.md is what this file was written to find out).

kp4.py staged its two moments by hand from the session log: the presses, the staff's charges, the weapon
set, the ward, the seals' unit ids, the seals opened before, the bosses' units. A schema 4 take holds each
of those, and `stage` reads them there:

| What | From the take | kp4.py had it from |
| --- | --- | --- |
| the presses | `request` events (their time less their age) | the log's "request" lines, by hand |
| attack mode at the start | the last `state` event before it | the log, by hand |
| the staff's charges, the set in hand | frame key `w` | the log's "N charges kept" |
| the resistances of the set in hand | `r` | cut.py's constants |
| the belt | `b` | cut.py's default (a full belt) |
| Psychic Ward, Hex: Purge, Consume | `f` | the log ("the mode's first cast") |
| the seals: unit, place, mode | `o` (any frame has the unit; the mode is the start's) | the log's "object N of ..." |
| the seals used before, the bosses dead before | `state`: `route.used`, `route.dead` | `Staged.opened` |
| which unit is which boss | `records.jsonl`, monster data +0x2A (records4.py) | `Staged.bosses` |
| the level card's lead | checked against `state.card` (the marks are the handler's, as in kp4.py) | - |
| a seal's pack: who, where, how long after | first sights within SPAWN_SECONDS of the seal's opening | not played |
| a monster that appears (Diablo) | its first sight within APPEAR of the character | not played |
| the monsters the client did not hold yet | their first sight within the window (`late`) | not played |

`Staging.by_hand` names what still is not the take's: read it before trusting a row.

The arena has no seal boss of its own. Here the pack a take saw appear is put into the arena when the
arena's own seal is opened, the recorded delay later, where the take first saw each of its monsters
(`spawn`): a play-back of the take's spawn, not a model of it. The monsters the client first held later in
the window stand from the start where the take first saw them (`late`): the arena's monsters do not go for
anything beyond 20 units (sim/monsters.py AWARE), so they wait there.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.replay --seeds 20 [--cut] [names]
"""

import argparse
import json
import math
import random
import statistics
import threading
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
from itertools import pairwise
from pathlib import Path

from inventory_tracking.builds.warlock.echoing_strike.mechanics import MISSILE
from inventory_tracking.combat.mechanics.tables import area_level
from inventory_tracking.combat.takes import MonsterRow, Take, carried, monsters_of, player_of
from inventory_tracking.config import PLAYER_HEALING
from inventory_tracking.input.compositor import STEP_KEYS
from inventory_tracking.macros.game.layout import HERALD_TIER_STAT
from inventory_tracking.macros.runner import ATTACK, PICKUP, TELEPORT
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror.monsters import LEVEL_STAT
from tests.inventory_tracking.scenarios.arena import records4, scene as scene_file
from tests.inventory_tracking.scenarios.arena.cut import DEFAULT_HERO, HELL_PENALTY, cut, full_points, level_of, through
from tests.inventory_tracking.scenarios.arena.driver import Press, key_names
from tests.inventory_tracking.scenarios.arena.game import EDGE, Arena
from tests.inventory_tracking.scenarios.arena.incident import TAKES, Row, births, quantile
from tests.inventory_tracking.scenarios.arena.kp4 import Mark, RoutePlay, handler_marks
from tests.inventory_tracking.scenarios.arena.mobs import AURA_FACTOR, AURA_MOD, Mobs, shooter, shot_parts
from tests.inventory_tracking.scenarios.arena.scene import Mob, Prop, Scene


Point = tuple[float, float]
FIXTURES = Path(__file__).parent / 'fixtures' / 'replay'
TAKE = '20261013T093331Z-108'  # Chaos Sanctuary, 2026-10-13 12:33:31 local, 252 s: the first schema 4 take
SPAWN_SECONDS = (
    2.0  # a seal's pack is first seen within this of the seal's change of mode (0.98 to 1.01 s, three packs)
)
PACK_FLAGS = 0x1A  # type flags of a pack that comes with its boss: super unique, unique, minion
# A hostile first seen this near the character did not walk into the client's view (first sights are 32 to 77
# units off, recorder-review.md (c)): it appeared, and is put into the arena at that instant (Diablo).
APPEAR = 30.0
RIVER = '20261013T093256Z-107'  # River of Flame, the 35 s before TAKE: the staff's last charges, the way in
DIABLO = 243  # monstats row (rca/2026-10-13/simulator-plan.md §1; the take's kill of txt 243 ends the route's fight)
LOW, HIGH = 0.1, 0.9
NEAR = 25.0  # units: the crowd about the character (the d2-rca session tool counts the same)


@dataclass(frozen=True)
class Moment:
    """A stretch of a take to play again: `start` seconds into the take, for `seconds`; the track is read at
    `marks`. `reach`: how far from the character's start the scene keeps ground and monsters."""

    name: str
    start: float
    seconds: float
    marks: tuple[float, ...]
    about: str
    take: str = TAKE
    reach: float = 260.0  # the way to the mark the route is at has to be in the scene's rooms


MOMENTS = (
    Moment(
        'stall-vizier-seal-1',
        # 12:33:38.3 (the frame cut at is 6.99 s in): the third Blade Warp has landed at (7779.5, 5477.5); the next
        # request is at 7.01 s
        start=6.95,
        seconds=9.0,  # the first Echoing Strike of the recording is 4.26 s in (12:33:42.6)
        marks=(1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 9.0),
        about=(
            'Eight presses of the teleport key in 2 s each stop on "no Blade Warp or walk leads toward Vizier '
            'seal 1" (the staff has no charges); attack mode is off, a pack closes in. The pickup key at 3.3 s '
            'turns attack mode on (its sweep), the first strike is at 4.0 s.'
        ),
    ),
    Moment(
        'fight-in-place',
        start=39.0,  # 12:34:10.4: attack mode on since 10.3 s, no teleport request between 33.5 and 59.5 s
        seconds=12.0,
        marks=(2.0, 4.0, 6.0, 8.0, 10.0, 12.0),
        about=(
            'Attack mode on, no teleport key: the hunt walks 30 units into a pack of 17, strikes from one '
            'place for 4 s, then the pickup key five times while it goes on. 30 kills, 159 points lost.'
        ),
    ),
    Moment(
        'vizier-seal',
        start=68.0,  # 12:34:39.4: attack mode on and idle, 110 units from the seal; the teleport key at 0.21 s
        seconds=24.0,  # to the second seal's opening (23.8 s)
        marks=(3.0, 6.0, 9.0, 12.0, 15.0, 18.0, 21.0, 24.0),
        about=(
            'Four Blade Warps to Vizier seal 1 through 38 monsters, the seal opened at 5.6 s, the Grand '
            "Vizier's pack of six 1.0 s later, the Vizier dead at 16.8 s, Vizier seal 2 opened at 23.8 s."
        ),
    ),
    Moment(
        'diablo',
        start=217.5,  # 12:37:08.9: all seals open, attack mode on by the star, nothing alive; Diablo appears 2.3 s in
        seconds=8.5,
        marks=(2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0),
        about=(
            'Diablo appears at 2.3 s, is struck from 2.7 s (Death Mark, Sigil: Lethargy) and dies at 7.8 s; 45 '
            'points lost.'
        ),
    ),
    Moment(
        'river-hops',
        take=RIVER,
        start=23.9,  # 12:33:20.7: the River of Flame, 190 units from the stairs, 2 charges on the staff
        seconds=10.6,  # the take ends with the level (34.5 s): the next frame is the Chaos Sanctuary's take
        marks=(2.0, 4.0, 6.0, 8.0, 10.0, 10.6),
        about=(
            'The teleport key 28 times: three Blade Warps "2 charges kept", three Teleport hops that empty the '
            'staff, two more Blade Warps and the walk into the Chaos Sanctuary, where the take ends.'
        ),
    ),
)


@dataclass
class Pack:
    """A seal's pack as the take saw it appear: `seal` is the object's unit, `delay` the seconds from the
    seal's change of mode to the pack's first frame."""

    seal: int
    label: str
    delay: float
    mobs: list[Mob]


@dataclass
class Seen:
    """What a stretch came to, the recording's or a play's. Times are seconds after the start; None: never
    within the window. `gone`: how far from the start the character stood at each mark; `places`: where;
    `near`: how many live hostiles stood within NEAR of it then.
    `kills`: hostiles dead by each mark; `ends`: the named instants (first strike, a seal's opening, a
    boss's death); `said`: how many of the macro's lines held each of the moment's phrases."""

    places: list[list[float]]
    gone: list[float]
    taken: list[float]
    kills: list[int]
    strikes: list[float]
    low: float
    moved: float
    near: list[int] = field(default_factory=list)  # live hostiles within NEAR units of the character at each mark
    ends: dict[str, float | None] = field(default_factory=dict)
    said: dict[str, int] = field(default_factory=dict)
    dead: bool = False


@dataclass
class Staging:
    """A moment made ready: everything `played` needs, from the take (`by_hand`: what is not)."""

    moment: Moment
    scene: Scene
    marks: list[Mark]
    presses: list[tuple[float, str]]
    opened: list[str]
    bosses: list[tuple[int, str]]
    dead_before: list[str]
    packs: list[Pack]
    arrivals: list[tuple[float, Mob]]  # (seconds after the start, a monster that appeared by the character)
    late: int  # how many of the scene's monsters the client first held after the start
    far: int  # how many stood further than cut.py keeps a monster (MOB_RANGE) at the start
    card: list | None  # `state.card` at the start: area, label, kind, spot, use, warp
    attack_mode: bool
    sweep: int  # `state.sweep`: the steps attack mode may still take on its own (hunt.py `Sweep.steps`)
    truth: Seen
    by_hand: tuple[str, ...]


PHRASES = (
    'no Blade Warp or walk leads toward',
    'Blade Warp toward',
    'Attack mode on',
    'Attack mode paused',
    'Echoing Strike',
    '=Macro: Healing potion',
    '=Macro: Blade Warp',
    '=Macro: Teleport',
    'Walking into',
    ': open',
    'Picking up',
    'toward a better place',
)
# What a staging does not have from the take, for every moment (the report's table (2) has the evidence).
BY_HAND = (
    "attack mode on at the start is a toggle pressed at 0 s: the hunt begins anew (`state` has the sweep's "
    "steps, not its age, nor the hunt's remembered units, its failed jumps and the build's buff timers)",
    "a monster's points at full life are the type's by the tables (the client holds a share of 128)",
    "the other weapon set's resistances are cut.py's constants (`r` is of the set in hand)",
    "the level card is the handler's for the whole level file (the take's `state.card` is its lead only)",
    "the code is today's tree: the manifest's `code` names the commit and the files that differed, not their text",
    "the drops on the ground (`g`) are not put into the scene: a potion's item code is not in `g` (kind and label are)",
)


def said_times(lines: Sequence[str], phrase: str) -> int:
    """How many of the lines hold `phrase`; with '=' before it, how many are it (a key pressed: "Macro: Blade
    Warp" is the press, "Blade Warp toward ..." and "Blade Warp aimed at ..." are about it)."""
    if phrase.startswith('='):
        return sum(1 for line in lines if line == phrase[1:])
    return sum(1 for line in lines if phrase in line)


def frame_at(take: Take, seconds: float) -> int:
    zero = take.frames[0]['t']
    return next(index for index, row in enumerate(take.frames) if row['t'] - zero >= seconds - EDGE)


def state_at(take: Take, t: float) -> dict:
    """The macro's state as the last `state` event up to `t` has it."""
    found: dict = {}
    for event in take.events:
        if event['t'] > t:
            break
        if event['event'] == 'state':
            found = event
    return found


def mob_of(row: MonsterRow, area: int, known: dict[int, dict]) -> Mob:
    """A hostile of a frame as a scene's monster: cut.py `cut`'s rule, for a row of any frame."""
    unit = known.get(row.unit) or {}
    stats = unit.get('stats', {})
    tier = int(stats.get(str(HERALD_TIER_STAT), 0))
    full = full_points(row, area, tier)
    return Mob(
        row.unit, row.txt, row.at,
        level=int(stats.get(str(LEVEL_STAT)) or area_level(area) or 0),
        life=round(full * row.life_share, 1), full=full, flags=row.flags,
        mods=tuple(unit.get('mods', ())), tier=tier, mode=row.mode,
    )  # fmt: skip


def seal_changes(take: Take) -> dict[int, float]:
    """unit id -> the time an object of `o` first left mode 0 (a seal's opening, a chest's)."""
    found: dict[int, float] = {}
    for frame in take.frames:
        for unit, _, mode, *_ in frame.get('o', ()):
            if mode and unit not in found:
                found[unit] = frame['t']
    return found


def things_of(
    take: Take, index: int, marks: Sequence[Mark], opened: Sequence[str]
) -> tuple[list[Prop], dict[str, int]]:
    """The scene's objects: what `o` holds at the start, and the object of every mark that names one,
    with the unit id any frame of the take has for it (the client holds a seal only from near). Also
    mark label -> unit id."""
    props = {row[0]: Prop(row[0], row[1], (row[3], row[4]), row[2]) for row in carried(take, 'o')[index] or ()}
    labels: dict[str, int] = {}
    for mark in marks:
        if not mark.use:
            continue
        spot = (mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS)
        unit = next(
            (
                row[0]
                for frame in take.frames
                for row in frame.get('o', ())
                if row[1] == mark.use and math.dist((row[3], row[4]), spot) < 1.0
            ),
            None,
        )
        if unit is None:
            continue
        labels[mark.label] = unit
        if unit not in props:
            props[unit] = Prop(unit, mark.use, spot, 2 if mark.label in opened else 0)
    return list(props.values()), labels


def recorded(take: Take, moment: Moment, labels: dict[str, int], bosses: Sequence[tuple[int, str]]) -> Seen:
    """The recording's side of a moment."""
    zero = take.frames[0]['t']
    start, end = zero + moment.start, zero + moment.start + moment.seconds
    frames = [frame for frame in take.frames if start - EDGE <= frame['t'] <= end]
    events = [event for event in take.events if start < event['t'] <= end]
    rows = [(frame['t'] - start, row) for frame in frames if (row := player_of(frame)) is not None]
    origin = rows[0][1].at
    places, gone, taken, kills, near = [], [], [], [], []
    for mark in moment.marks:
        at = next((row.at for t, row in reversed(rows) if t <= mark + EDGE), origin)
        frame = next((frame for frame in reversed(frames) if frame['t'] - start <= mark + EDGE), frames[0])
        near.append(sum(1 for row in monsters_of(frame) if row.hostile and math.dist(row.at, at) <= NEAR))
        places.append([round(at[0], 1), round(at[1], 1)])
        gone.append(round(math.dist(origin, at), 1))
        past = [event for event in events if event['t'] - start <= mark]
        taken.append(float(sum(event.get('lost', 0) for event in past if event['event'] == 'hurt')))
        kills.append(sum(1 for event in past if event['event'] == 'kill'))
    strikes = [round(at - start, 2) for at in births(frames, MISSILE)]
    ends: dict[str, float | None] = {'first strike': strikes[0] if strikes else None}
    changes = seal_changes(take)
    for label, unit in labels.items():
        at = changes.get(unit)
        ends[f'{label} opened'] = round(at - start, 2) if at is not None and start <= at <= end else None
    for unit, name in bosses:
        died = next(
            (
                frame['t'] - start
                for frame in frames
                for row in monsters_of(frame)
                if row.unit == unit and not row.alive
            ),
            None,
        )
        ends[f'{name} dead'] = None if died is None else round(died, 2)
    # Every line the macro logged (the `said` events are the minority that went to the card); a slow press's
    # warning quotes its outcome and would count twice.
    lines = [event['text'] for event in events if event['event'] == 'log' and 'slow press' not in event['text']]
    lives = [row.life for _, row in rows if row.life and row.max_life]
    return Seen(
        places, gone, taken, kills, strikes,
        low=float(min(lives, default=0)),
        moved=round(sum(math.dist(a.at, b.at) for (_, a), (_, b) in pairwise(rows)), 1),
        near=near, ends=ends,
        said={phrase: said_times(lines, phrase) for phrase in PHRASES},
    )  # fmt: skip


def stage(moment: Moment, takes: Path = TAKES) -> Staging:
    """The moment made ready from its take (the module text has what comes from where)."""
    directory = takes / moment.take
    take = Take.load(directory)
    if take.schema < 4:
        raise ValueError(f'{moment.take}: schema {take.schema}; a replay from the take alone needs 4')
    zero = take.frames[0]['t']
    index = frame_at(take, moment.start)
    start = take.frames[index]['t']
    end = zero + moment.start + moment.seconds
    scene = cut(take, index, defaults=DEFAULT_HERO, name=moment.name, reach=moment.reach)
    assumed = set(scene.assumed)

    # The character, from the keys written at a change.
    staff, belt, buffs, resists = (carried(take, key)[index] for key in 'wbfr')
    hero = scene.hero
    main, other = hero.sets
    if staff is not None:
        other = replace(other, teleport_charges=int(staff[0]))
        hero = replace(hero, hand=1 if staff[2] else 0)
        assumed -= {'hand'}
    if resists is not None:
        physical, fire, lightning, cold = resists[:4]
        read = {
            'physical': through(physical),
            'fire': through(fire - HELL_PENALTY),
            'lightning': through(lightning - HELL_PENALTY),
            'cold': through(cold - HELL_PENALTY),
        }
        main, other = (main, replace(other, resist=read)) if hero.hand else (replace(main, resist=read), other)
    hero = replace(hero, sets=(main, other))
    if belt is not None:
        hero = replace(hero, belt=tuple(belt))
        assumed -= {'belt'}
    if buffs is not None:
        ward, purge, consume = buffs
        hero = replace(
            hero,
            ward=hero.ward if ward is None else ward,
            hex_purge=hero.hex_purge if purge is None else purge,
            consume=hero.consume if consume is None else consume,
        )
        assumed -= {
            name for name, value in (('ward', ward), ('hex_purge', purge), ('consume', consume)) if value is not None
        }
    scene.hero = hero

    # The macro's state, the card, the seals.
    state = state_at(take, start)
    route = state.get('route') or {}
    area = hero.area
    opened = [label for level, label, _ in route.get('used', ()) if level == area]
    level = level_of(take) or {}
    marks = handler_marks(area, level.get('rooms', ()), hero.at)
    scene.things, labels = things_of(take, index, marks, opened)

    # The monsters the client came to hold within the window: a seal's pack, or one that was there.
    known = {unit['unit']: unit for unit in take.units}
    held = {mob.unit for mob in scene.mobs}
    far = 0
    for row in monsters_of(take.frames[index]):  # cut.py keeps no hostile beyond MOB_RANGE: the window goes there
        away = math.dist(row.at, hero.at)
        if row.hostile and row.unit not in held and row.life and row.at != (0.0, 0.0) and away <= moment.reach:
            scene.mobs.append(mob_of(row, area, known))
            far += 1
    before = {row.unit for frame in take.frames[: index + 1] for row in monsters_of(frame)}
    changes = {unit: at for unit, at in seal_changes(take).items() if start < at <= end and unit in labels.values()}
    packs: dict[int, Pack] = {}
    arrivals: list[tuple[float, Mob]] = []
    late = 0
    for frame in take.frames[index + 1 :]:
        if frame['t'] > end:
            break
        for row in monsters_of(frame):
            if row.unit in before:
                continue
            before.add(row.unit)
            if not row.hostile or row.at == (0.0, 0.0):
                continue
            seal = next(
                (
                    unit
                    for unit, at in changes.items()
                    if 0 <= frame['t'] - at <= SPAWN_SECONDS and row.flags & PACK_FLAGS
                ),
                None,
            )
            mob = mob_of(row, area, known)
            stand = player_of(frame)
            if seal is None and stand is not None and math.dist(row.at, stand.at) <= APPEAR:
                arrivals.append((round(frame['t'] - start, 2), mob))
                continue
            if seal is None:
                scene.mobs.append(mob)
                late += 1
                continue
            label = next(label for label, unit in labels.items() if unit == seal)
            pack = packs.setdefault(seal, Pack(seal, label, round(frame['t'] - changes[seal], 2), []))
            pack.mobs.append(mob)
    scene.assumed = tuple(sorted(assumed))

    names = records4.bosses(directory)
    cast = [*scene.mobs, *(mob for pack in packs.values() for mob in pack.mobs), *(mob for _, mob in arrivals)]
    names.update({mob.unit: 'Diablo' for mob in cast if mob.txt == DIABLO})
    held = {mob.unit for mob in cast}
    bosses = sorted((unit, name) for unit, name in names.items() if unit in held)
    requests = [
        (round(event['t'] - event.get('age', 0.0) - start, 2), event['routine'])
        for event in take.events
        if event['event'] == 'request' and start < event['t'] <= end
    ]
    for _, routine in requests:
        if routine not in (TELEPORT, PICKUP, ATTACK):
            raise ValueError(f'{moment.name}: the take has a request of {routine!r}, which the arena does not play')
    attack_mode = bool(state.get('attack_mode'))
    presses = [(0.0, ATTACK), *requests] if attack_mode else requests
    return Staging(
        moment, scene, marks, presses, opened, bosses,
        dead_before=sorted(route.get('dead') or ()),
        packs=list(packs.values()), arrivals=arrivals, late=late, far=far, card=state.get('card'),
        attack_mode=attack_mode, sweep=int(state.get('sweep') or 0),
        truth=recorded(take, moment, labels, bosses), by_hand=BY_HAND,
    )  # fmt: skip


# -- the play -------------------------------------------------------------------------------------------


class TakePlay(RoutePlay):
    """kp4.py's play with the bosses that were dead before the moment (`state.route.dead`), and with a run
    made as the production runner makes it.

    `hands_given`: the fakes' game hands every run the main weapon set (macros/fakes.py `Game.run`:
    `run.battle_hands`), and driver.py `Play.execute` and kp4.py `RoutePlay.execute` the build's on top.
    `MacroRunner._execute` does not: a run's `battle_hands` is empty until attack mode's own check sets it
    (hunt.py, "Main weapons for the fight") or the prebuff does. So the teleport step's "the main weapons,
    once" with the staff empty (hunt.py `empty_hop` and `afoot`: `take_battle_weapons`) swaps in those plays
    and does nothing in the game: the take of 2026-10-13 12:33 has the staff in hand with no charges for its
    first 12 s, through 20 teleport steps, and no swap before attack mode's. False (the default) makes the
    run as the game does."""

    def __init__(self, *args, dead_before: Sequence[str] = (), hands_given: bool = False, **kwargs) -> None:
        self.dead_before = frozenset(dead_before)
        self.hands_given = hands_given
        super().__init__(*args, **kwargs)

    def slain(self) -> frozenset[str]:
        return super().slain() | self.dead_before

    def execute(self, cancelled: threading.Event, routine: str) -> None:
        if self.hands_given:
            super().execute(cancelled, routine)
            return
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
        # As it was on the recording's day: a run made by `_execute` held no weapon sets. Since the
        # afternoon of 2026-10-13 `MacroRunner.wear` gives every run the build's (the defect this replay
        # found); the recorded game is replayed without, `hands_given` plays it with today's code.
        worn = runner.wear

        def as_it_was(run, build) -> None:
            worn(run, build)
            run.prebuff_hands = run.battle_hands = frozenset()

        runner.wear = as_it_was  # type: ignore[method-assign]
        try:
            runner.perform(run, run.actuator, routine, key_names)
        finally:
            runner.wear = worn  # type: ignore[method-assign]


def spawn(arena: Arena, mobs: Sequence[Mob], seed: int) -> None:
    """Put monsters into a running arena as `Mobs` and its pack hold those of the scene (mobs.py
    `Mobs.__init__`, sim/monsters.py `Pack.__init__`): the take's seal pack, appearing."""
    herd, pack = arena.mobs, arena.mobs.pack
    for found in mobs:
        mob = replace(found)
        herd.mobs[mob.unit] = mob
        herd.hostile.append(mob.unit)
        if AURA_MOD in mob.mods:
            herd.auras[mob.unit] = AURA_FACTOR
        walker = Mobs._walker(mob)
        pack.walkers[mob.unit] = walker
        roll = pack.rolls[mob.unit] = random.Random(seed * 1_000_003 + mob.unit)
        walker.favour = roll.random()
        if shooter(mob.txt):
            pack.shots[mob.unit] = dict(shot_parts(walker))
            walker.until = herd.frame + roll.randrange(max(round(pack._gap(walker)), 1))
    arena.cleared_at = None


def played(
    staging: Staging, seed: int, presses: Sequence[tuple[float, str]] | None = None, hands_given: bool = False
) -> tuple[Seen, list]:
    """One play of the moment: what it came to, and the lines the macro said with their times."""
    moment, scene = staging.moment, staging.scene
    arena = Arena(scene, seed=seed, osd=PLAYER_HEALING)
    given = staging.presses if presses is None else presses
    play = TakePlay(
        arena, [Press(at, routine) for at, routine in given], moment.seconds, seed, staging.marks,
        staging.opened, staging.bosses, dead_before=staging.dead_before, hands_given=hands_given,
    )  # fmt: skip
    if staging.sweep:
        # The licence to move as the take's `state` has it. Its age and its last look are not there: taken
        # as renewed and looked now (a hunt begun anew looks for a better place in its first instant, which
        # the recorded one, under way for seconds, did not).
        play.hunter.sweep.start(arena.clock.now)
        play.hunter.sweep.steps = staging.sweep
        play.hunter.sweep.looked = arena.clock.now
    origin = arena.here
    spots = {mark.label: (mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS) for mark in staging.marks if mark.use}
    labels = {
        prop.unit: label for label, spot in spots.items() for prop in scene.things if math.dist(prop.at, spot) < 1
    }
    waiting = {pack.seal: pack for pack in staging.packs}
    due: list[tuple[float, list[Mob]]] = [(at, [mob]) for at, mob in staging.arrivals]
    samples: list[tuple[float, Point, float, int, int]] = []
    strikes: list[float] = []
    ends: dict[str, float | None] = {'first strike': None}
    ends.update({f'{label} opened': None for label in labels.values() if label not in staging.opened})
    ends.update({f'{name} dead': None for _, name in staging.bosses})
    seen = {'casts': 0, 'low': arena.life}
    spy = play.tick

    def tick() -> None:
        now = arena.clock.now
        if arena.over is None:
            for thing in arena.things:
                label = labels.get(thing.unit_id)
                if label is not None and thing.mode and ends.get(f'{label} opened', 0.0) is None:
                    ends[f'{label} opened'] = round(now, 2)
                    pack = waiting.pop(thing.unit_id, None)
                    if pack is not None:
                        due.append((now + pack.delay, pack.mobs))
            for item in [item for item in due if item[0] <= now + EDGE]:
                due.remove(item)
                spawn(arena, item[1], seed)
            if arena.casts > seen['casts']:
                strikes.extend([round(now, 2)] * (arena.casts - seen['casts']))
                seen['casts'] = arena.casts
                if ends['first strike'] is None:
                    ends['first strike'] = round(now, 2)
            live = set(arena.mobs.live())
            for unit, name in staging.bosses:
                if unit in arena.mobs.mobs and unit not in live and ends[f'{name} dead'] is None:
                    ends[f'{name} dead'] = round(now, 2)
            crowd = sum(1 for unit in live if math.dist(arena.mobs.mobs[unit].at, arena.here) <= NEAR)
            samples.append((now, arena.here, arena.taken, len(arena.kills), crowd))
            seen['low'] = min(seen['low'], arena.life)
        spy()

    play.tick = tick  # type: ignore[method-assign]
    result = play.run()
    places, gone, taken, kills, near = [], [], [], [], []
    for mark in moment.marks:
        past = [sample for sample in samples if sample[0] <= mark + EDGE]
        _, at, lost, dead, crowd = past[-1] if past else (0.0, origin, 0.0, 0, 0)
        near.append(crowd)
        places.append([round(at[0], 1), round(at[1], 1)])
        gone.append(round(math.dist(origin, at), 1))
        taken.append(round(lost, 1))
        kills.append(dead)
    lines = [text for _, text in result.said]
    told = Seen(
        places, gone, taken, kills, strikes,
        low=round(max(seen['low'], 0.0), 1), moved=round(result.moved, 1), near=near, ends=ends,
        said={phrase: said_times(lines, phrase) for phrase in PHRASES},
        dead=result.dead_at is not None,
    )  # fmt: skip
    return told, result.said


# -- the two side by side -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Timed(Row):
    """A row whose value may never come: `never` plays of `plays` did not reach it."""

    never: int = 0
    plays: int = 0

    @property
    def verdict(self) -> str:
        if self.never == self.plays and self.plays:
            return 'outside: never in the arena'
        if math.isnan(self.recorded):
            return 'the recording never; the arena does'
        text = super().verdict
        return f'{text} (never in {self.never} of {self.plays})' if self.never else text


def compare(truth: Seen, plays: Sequence[Seen], marks: Sequence[float]) -> list[Row]:
    rows: list[Row] = []

    def row(what: str, real: float, values: Sequence[float]) -> None:
        rows.append(Row(what, real, quantile(values, LOW), statistics.median(values), quantile(values, HIGH)))

    for index, mark in enumerate(marks):
        row(f'from the start at {mark:g} s', truth.gone[index], [play.gone[index] for play in plays])
    for index, mark in enumerate(marks):
        apart = [math.dist(truth.places[index], play.places[index]) for play in plays]
        row(f'apart from the recorded place at {mark:g} s', 0.0, apart)
    for mark in marks:
        row(
            f'strikes by {mark:g} s',
            sum(1 for at in truth.strikes if at <= mark),
            [sum(1 for at in play.strikes if at <= mark) for play in plays],
        )
    for index, mark in enumerate(marks):
        row(f'life lost by {mark:g} s', truth.taken[index], [play.taken[index] for play in plays])
    for index, mark in enumerate(marks):
        row(f'kills by {mark:g} s', truth.kills[index], [play.kills[index] for play in plays])
    for index, mark in enumerate(marks):
        row(f'hostiles within {NEAR:g} at {mark:g} s', truth.near[index], [play.near[index] for play in plays])
    row('least life', truth.low, [play.low for play in plays])
    row('moved', truth.moved, [play.moved for play in plays])
    for name, real in truth.ends.items():
        values = [play.ends.get(name) for play in plays]
        found = [value for value in values if value is not None]
        if real is None and not found:
            continue
        low, mid, high = (
            (quantile(found, LOW), statistics.median(found), quantile(found, HIGH)) if found else (math.nan,) * 3
        )
        rows.append(
            Timed(
                f'{name} at, s',
                math.nan if real is None else real,
                low,
                mid,
                high,
                len(values) - len(found),
                len(values),
            )
        )
    for phrase, real in truth.said.items():
        values = [play.said.get(phrase, 0) for play in plays]
        if real or any(values):
            row(f'said "{phrase.removeprefix("=")}"', real, values)
    return rows


def apart_is_position(row: Row) -> bool:
    return row.what.startswith('apart from')


def inside(row: Row, near: float = 5.0) -> bool:
    """Whether a row is inside the band. The recorded place has no band of its own: the arena is "inside"
    when its median stands within `near` units of it."""
    if apart_is_position(row):
        return row.median <= near
    return row.inside and not (isinstance(row, Timed) and row.never * 2 > row.plays)


def table(staging: Staging, rows: Sequence[Row], plays: Sequence[Seen]) -> str:
    moment = staging.moment
    good = sum(1 for row in rows if inside(row))
    lines = [
        f'## {moment.name}',
        '',
        moment.about,
        '',
        f'Take {moment.take}, {moment.start:g} s in, {moment.seconds:g} s; {len(plays)} seeds, '
        f'{sum(1 for play in plays if play.dead)} deaths; {len(staging.scene.mobs)} monsters in the scene '
        f'({staging.far} beyond 60 units, {staging.late} first seen after the start), '
        f'{sum(len(pack.mobs) for pack in staging.packs)} in seal packs, {len(staging.arrivals)} appearing; '
        f'{len(staging.presses)} presses. **{good} of {len(rows)} rows inside.**',
        '',
        '| | recorded | arena p10 | median | p90 | |',
        '| --- | ---: | ---: | ---: | ---: | --- |',
    ]
    for row in rows:
        verdict = ('inside' if inside(row) else 'outside') if apart_is_position(row) else row.verdict
        real = 'never' if math.isnan(row.recorded) else f'{row.recorded:g}'
        lines.append(f'| {row.what} | {real} | {row.low:g} | {row.median:g} | {row.high:g} | {verdict} |')
    return '\n'.join(lines) + '\n'


# -- the fixtures ---------------------------------------------------------------------------------------


def paths(moment: Moment) -> tuple[Path, Path]:
    return FIXTURES / f'{moment.name}.json', FIXTURES / f'{moment.name}.staging.json'


def store(moment: Moment, takes: Path = TAKES) -> Staging:
    staging = stage(moment, takes)
    scene_path, staging_path = paths(moment)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    scene_file.dump(staging.scene, scene_path)
    kept = {
        'marks': [asdict(mark) for mark in staging.marks],
        'presses': staging.presses,
        'opened': staging.opened,
        'bosses': staging.bosses,
        'dead_before': staging.dead_before,
        'packs': [asdict(pack) for pack in staging.packs],
        'arrivals': [[at, asdict(mob)] for at, mob in staging.arrivals],
        'late': staging.late,
        'far': staging.far,
        'card': staging.card,
        'attack_mode': staging.attack_mode,
        'sweep': staging.sweep,
        'truth': asdict(staging.truth),
    }
    staging_path.write_text(json.dumps(kept, indent=1) + '\n', encoding='utf-8')
    return staging


def stored(moment: Moment) -> Staging | None:
    scene_path, staging_path = paths(moment)
    if not scene_path.exists() or not staging_path.exists():
        return None
    kept = json.loads(staging_path.read_text(encoding='utf-8'))
    packs = [
        Pack(pack['seal'], pack['label'], pack['delay'], [scene_file._record(Mob, mob) for mob in pack['mobs']])  # type: ignore[misc]
        for pack in kept['packs']
    ]
    return Staging(
        moment,
        scene_file.load(scene_path),
        [Mark(row['label'], row['kind'], tuple(row['spot']), row['use']) for row in kept['marks']],
        [(at, routine) for at, routine in kept['presses']],
        kept['opened'],
        [(unit, name) for unit, name in kept['bosses']],
        kept['dead_before'],
        packs,
        [(at, scene_file._record(Mob, mob)) for at, mob in kept['arrivals']],  # type: ignore[misc]
        kept['late'],
        kept['far'],
        kept['card'],
        kept['attack_mode'],
        kept['sweep'],
        Seen(**kept['truth']),
        BY_HAND,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('names', nargs='*', help='moments to play (default: all)')
    parser.add_argument('--seeds', type=int, default=20)
    parser.add_argument('--cut', action='store_true', help='stage the moments again from the take')
    parser.add_argument('--lines', type=int, default=0, help='print what the macro said in this seed')
    parser.add_argument('--write', action='store_true', help='write fixtures/replay/REPLAY.md')
    args = parser.parse_args(argv)
    parts = []
    for moment in MOMENTS:
        if args.names and moment.name not in args.names:
            continue
        staging = store(moment) if args.cut else stored(moment) or store(moment)
        results = [played(staging, seed) for seed in range(1, args.seeds + 1)]
        plays = [told for told, _ in results]
        parts.append(table(staging, compare(staging.truth, plays, moment.marks), plays))
        print(parts[-1])
        if args.lines:
            for at, text in results[args.lines - 1][1]:
                print(f'  {at:6.2f} {text}')
    if args.write:
        head = '# Moments of a schema 4 take played again from the take alone (replay.py)\n\n'
        (FIXTURES / 'REPLAY.md').write_text(head + '\n'.join(parts), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
