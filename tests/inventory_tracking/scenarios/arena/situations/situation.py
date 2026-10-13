"""A situation: one test case of the character's controller, whether cut from a recorded game or built by
hand, with one way to play it and one result (user, 2026-10-13: "we should be able to add to test cases some
particular pre-recorded situations ... construct situations like: we are in the middle of 4 packs ... what we
will do and how we will die").

A `Situation` is an arena scene (scene.py: ground, the character, monsters, objects, drops) with what a play
of it needs besides: the level card's marks and the route's facts (kp4.py `RoutePlay`), whether attack mode
is on at the start, the presses, monsters that appear during the play (stage.py `Spawn`), curses, how far a
monster notices the character, and for a recorded one the recording's own track and every fact that was
entered by hand (`assumed`: name -> why). It is one JSON file (`dump`, `load`) that needs no take.

    recorded = load(FIXTURES / 'vizier-stall.json')                      # cut by record.py `from_take`
    built = (Situation.on(open_field(60))
             .hero(life=0.30, ward=False)
             .pack('Undead Stygian Doll', 8, at=north(18), spread=5)
             .drop('a rune', at=east(6))
             .attack_mode(True))
    outcome = built.play(seed=3)             # presses=held('teleport', every=0.3), seconds=...
    print(story(outcome))                    # story.py
    built.trials(range(1, 31))               # death rate, when, what killed

`play` gives the presses to the production `MacroRunner` through kp4.py `RoutePlay` (every routine is the
runner's own `perform`: the attack mode toggle, the teleport key with the route's stage and the level card,
the pickup key, the seek key), on a `Stage` (stage.py), with the standalone healer beside it as incident.py
has it. Presses are a recorded list, `held(key, every=...)`, `once(key, at=...)`, or none; `attack_mode(True)`
is the toggle pressed at 0.0, before any of them.

Distances are world units (sub-tiles; a tile is 5). The compass is the world's axes, not the screen's: north
is -y, east +x. A constructed situation stands in area 137 unless told otherwise: the one area of the
monster-level table at 84 or more that no route of routes/catalog names, so the teleport key is the plain
step toward the card's mark there.
"""

import json
import math
import statistics
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.tables import points_of, tables
from inventory_tracking.combat.sim.monsters import CHAMPION_FLAG, COLD, FIRE, LIGHTNING, STRONG, UNIQUE_FLAG
from inventory_tracking.config import PLAYER_HEALING
from inventory_tracking.levels.model import Walkable, pack_cells
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.runner import ATTACK, HUNT_ELITES, PICKUP, TELEPORT
from inventory_tracking.macros.world import MINION_FLAG
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.scenarios.arena import scene as scene_file
from tests.inventory_tracking.scenarios.arena.cut import DEFAULT_HERO
from tests.inventory_tracking.scenarios.arena.driver import Press
from tests.inventory_tracking.scenarios.arena.kp4 import Mark, RoutePlay
from tests.inventory_tracking.scenarios.arena.mobs import AURA_MOD
from tests.inventory_tracking.scenarios.arena.scene import Drop, Mob, Prop, Scene
from tests.inventory_tracking.scenarios.arena.situations.bestiary import name_of, txt_of
from tests.inventory_tracking.scenarios.arena.situations.stage import ARENA_AWARE, Hurt, Spawn, Stage, Tick, awareness


Point = tuple[float, float]
FIXTURES = Path(__file__).parent / 'fixtures'
AREA = 137  # the module text has why
LIFE = 1783.0  # the character's most life in the takes of 2026-10-13 (the Vizier fixture's hero)
KEYS = {'attack': ATTACK, 'teleport': TELEPORT, 'pickup': PICKUP, 'seek': HUNT_ELITES}  # a key's word -> the routine
RANKS = {'plain': 0, 'minion': MINION_FLAG, 'champion': CHAMPION_FLAG, 'unique': UNIQUE_FLAG}
ENCHANTMENTS = {'extra strong': STRONG, 'fire': FIRE, 'lightning': LIGHTNING, 'cold': COLD, 'aura': AURA_MOD}
LAST_BLOWS = 1.5  # seconds before a death whose blows are named as what killed
SAMPLE = 0.2  # seconds between the samples an outcome keeps of the life and the place
FIRST_UNIT = 5_000_000  # unit ids of what a builder makes, counted from here


def north(units: float) -> Point:
    return (0.0, -units)


def south(units: float) -> Point:
    return (0.0, units)


def east(units: float) -> Point:
    return (units, 0.0)


def west(units: float) -> Point:
    return (-units, 0.0)


def open_field(radius: float) -> dict[str, Any]:
    """Open walkable ground `radius` units to every side of its middle, as one grid (the character stands in
    the middle of it)."""
    side = math.ceil(2 * radius / TILE_UNITS)
    cells = pack_cells('1' * (side * TILE_UNITS) ** 2)
    room = {
        'preset': 0,
        'x': 1000,
        'y': 1000,
        'width': side,
        'height': side,
    }  # one room: the teleport step's way is over rooms
    return {'ground': [asdict(Walkable(1000, 1000, side, side, cells, cells))], 'rooms': [room], 'doors': []}


def level_of(scene: Scene) -> dict[str, Any]:
    """The ground of another scene (a recorded one's level) for a situation built by hand on it."""
    return {'ground': deepcopy(scene.ground), 'rooms': deepcopy(scene.rooms), 'doors': deepcopy(scene.doors)}


def held(
    key: str, every: float = 0.3, since: float = 0.0, until: float | None = None
) -> tuple[str, float, float, float | None]:
    """`key` pressed every `every` seconds from `since` to `until` (None: the play's end)."""
    return (KEYS[key], every, since, until)


def once(key: str, at: float = 0.0) -> Press:
    return Press(at, KEYS[key])


def spelled(presses: Iterable, seconds: float) -> list[Press]:
    """Presses in any of the three forms as the driver's list."""
    found: list[Press] = []
    for press in presses:
        if isinstance(press, Press):
            found.append(press)
        elif len(press) == 2:
            found.append(Press(float(press[0]), KEYS.get(press[1], press[1])))
        else:
            routine, every, since, until = press
            count = int(((seconds if until is None else until) - since) / every - 1e-9) + 1
            found += [Press(round(since + index * every, 3), routine) for index in range(max(count, 0))]
    return sorted(found, key=lambda press: press.at)


@dataclass
class Outcome:
    """What one play of a situation came to; the same record for a recorded and a constructed one. Times are
    seconds of the arena's clock from the play's start."""

    name: str
    seed: int
    seconds: float
    max_life: float
    start_life: float
    dead_at: float | None
    killers: list[tuple[str, str, int, float]]  # the blows of the last LAST_BLOWS seconds: type, kind, how many, points
    life: list[tuple[float, float]]  # sampled every SAMPLE seconds
    low: float
    taken: float
    hurts: list[Hurt]
    kills: list[tuple[float, int, str]]  # when, the unit, its type's name
    cleared_at: float | None
    strikes: list[float]
    track: list[tuple[float, float, float]]  # when, x, y, sampled
    crowd: list[tuple[float, int]]  # when, the hostiles within stage.CROWD of the character, sampled
    moved: float
    potions: list[tuple[float, int, str]]
    picked: list[tuple[float, str]]
    said: list[tuple[float, str]]
    appeared: list[tuple[float, str, int]]
    opened: dict[int, float]
    gaps: dict[str, tuple[float, float, float] | None]  # a boss: its first, least and last distance while alive
    boss_dead: dict[str, float | None]
    stage: str | None
    attack_mode: bool  # at the end
    alive: int  # hostiles alive at the end
    hostiles: int  # hostiles there were, those that appeared among them

    @property
    def dead(self) -> bool:
        return self.dead_at is not None

    def taken_by(self) -> dict[tuple[str, str], float]:
        """The life lost by who took it: (the type's name, the blow's kind) -> points, the most first."""
        found: Counter[tuple[str, str]] = Counter()
        for hurt in self.hurts:
            found[(name_of(hurt.txt), hurt.kind)] += hurt.points
        return dict(found.most_common())

    def said_count(self, part: str) -> int:
        return sum(1 for _, text in self.said if part in text)


@dataclass
class Trials:
    """Many plays of one situation, one seed each."""

    outcomes: list[Outcome]

    @property
    def death_rate(self) -> float:
        return sum(1 for play in self.outcomes if play.dead) / len(self.outcomes)

    @staticmethod
    def spread(values: Sequence[float | None]) -> tuple[float, float, float] | None:
        found = [value for value in values if value is not None]
        return (min(found), statistics.median(found), max(found)) if found else None

    def died_at(self) -> tuple[float, float, float] | None:
        return self.spread([play.dead_at for play in self.outcomes])

    def cleared_at(self) -> tuple[float, float, float] | None:
        return self.spread([play.cleared_at for play in self.outcomes])

    def lost(self) -> tuple[float, float, float] | None:
        return self.spread([play.taken for play in self.outcomes])

    def killers(self) -> dict[tuple[str, str], int]:
        """In how many deaths each (type, kind of blow) was among the last blows."""
        found: Counter[tuple[str, str]] = Counter()
        for play in self.outcomes:
            found.update({(name, kind) for name, kind, _, _ in play.killers})
        return dict(found.most_common())

    def taken_by(self) -> dict[tuple[str, str], float]:
        """The mean life lost a play by who took it."""
        found: Counter[tuple[str, str]] = Counter()
        for play in self.outcomes:
            found.update(play.taken_by())
        return {key: points / len(self.outcomes) for key, points in found.most_common()}

    def row(self) -> str:
        died, lost, clear = self.died_at(), self.lost(), self.cleared_at()
        cleared = sum(1 for play in self.outcomes if play.cleared_at is not None)
        killers = ', '.join(f'{name} {kind} ({count})' for (name, kind), count in list(self.killers().items())[:3])
        return (
            f'{self.death_rate:.0%} | {"-" if died is None else f"{died[1]:.1f}"} | '
            f'{"-" if lost is None else f"{lost[0]:.0f} / {lost[1]:.0f} / {lost[2]:.0f}"} | '
            f'{cleared}/{len(self.outcomes)}{"" if clear is None else f" at {clear[1]:.1f}"} | {killers or "-"}'
        )


ROW_HEAD = 'deaths | median death, s | life lost least / median / most | cleared | among the last blows (deaths)'


@dataclass
class Situation:
    name: str
    scene: Scene
    seconds: float = 20.0
    about: str = ''
    attack: bool = False  # attack mode is on from the start (the toggle at 0.0)
    presses: tuple[tuple[float, str], ...] = ()  # (seconds, the runner's routine)
    marks: tuple[Mark, ...] = ()  # the level card, the first leading unless the route leads with another
    opened: tuple[str, ...] = ()  # the marks whose objects were used before the start
    bosses: tuple[tuple[int, str], ...] = ()  # (unit, the route's name of it)
    spawns: list[Spawn] = field(default_factory=list)
    curses: tuple[tuple[float, str, float], ...] = ()
    aware: float = ARENA_AWARE
    lands: dict[int, float] = field(default_factory=dict)  # type -> the chance its shot lands (stage.py)
    as_it_was: bool = False  # the teleport step has the rule withdrawn on 2026-10-13 (kp4.py `fight_first`)
    assumed: dict[str, str] = field(default_factory=dict)  # what was entered by hand or guessed: name -> why
    source: dict[str, Any] | None = None  # a recorded one: the take, the start, the schema
    recorded: dict[str, Any] | None = None  # the recording's side of the window (record.py)
    next_unit: int = FIRST_UNIT

    # -- built by hand ----------------------------------------------------------------------------------

    @classmethod
    def on(
        cls, ground: dict[str, Any], *, name: str = 'a constructed situation', area: int = AREA, at: Point | None = None
    ) -> Situation:
        """An empty situation on `ground` (`open_field(...)` or `level_of(scene)`), the character in the
        middle of the ground's first grid unless `at` says where, with the repo's default character at full
        life (cut.py DEFAULT_HERO: both weapon sets, a full belt, the three buffs up)."""
        first = ground['ground'][0]
        middle = ((first['x'] + first['width'] / 2) * TILE_UNITS, (first['y'] + first['height'] / 2) * TILE_UNITS)
        hero = replace(DEFAULT_HERO, at=at or middle, area=area, life=LIFE, max_life=LIFE, mana=500.0, max_mana=500.0)
        scene = Scene(name, hero, [], ground['ground'], ground['doors'], ground['rooms'])
        return cls(name, scene, assumed={'everything': 'built by hand'})

    def variant(self, name: str | None = None, **changes: Any) -> Situation:
        """An independent copy, renamed and with fields replaced: the base of an experiment."""
        found = replace(deepcopy(self), **changes)
        if name:
            found.name = found.scene.name = name
        return found

    def spot(self, offset: Point) -> Point:
        here = self.scene.hero.at
        return (here[0] + offset[0], here[1] + offset[1])

    def unit(self) -> int:
        self.next_unit += 1
        return self.next_unit

    def hero(
        self,
        *,
        life: float | None = None,
        max_life: float | None = None,
        ward: bool | None = None,
        weapons: str | None = None,
        charges: int | None = None,
        belt: tuple[int | None, ...] | None = None,
    ) -> Situation:
        """The character: `life` as a share of the most (up to 1.0) or in points, the `ward` up or down,
        the 'main' or the 'staff' set in hand, the staff's `charges`, the `belt` by cell."""
        hero = self.scene.hero
        if max_life is not None:
            hero = replace(hero, max_life=float(max_life), life=min(hero.life, float(max_life)))
        if life is not None:
            hero = replace(hero, life=life * hero.max_life if life <= 1.0 else float(life))
        if ward is not None:
            hero = replace(hero, ward=ward)
        if weapons is not None:
            hero = replace(hero, hand={'main': 0, 'staff': 1}[weapons])
        if charges is not None:
            hero = replace(hero, sets=(hero.sets[0], replace(hero.sets[1], teleport_charges=charges)))
        if belt is not None:
            hero = replace(hero, belt=tuple(belt))
        self.scene.hero = hero
        return self

    def mobs_of(
        self,
        kind: str | int,
        count: int,
        at: Point,
        spread: float,
        rank: str,
        enchantments: Sequence[str | int],
        life: float,
    ) -> list[Mob]:
        """`count` monsters of a type round `at` (an offset from the character), on a sunflower of radius
        `spread` (no roll: the same pack every time). `rank` 'boss': the first a unique, the others its minions."""
        txt, area = txt_of(kind), self.scene.hero.area
        level = int(tables()['areas'][str(area)])
        mods = tuple(ENCHANTMENTS.get(mod, mod) for mod in enchantments)  # type: ignore[arg-type]
        centre, found = self.spot(at), []
        for index in range(count):
            flags = RANKS['unique' if index == 0 else 'minion'] if rank == 'boss' else RANKS[rank]
            full = points_of(txt, area) * (ELITE_LIFE if flags & (UNIQUE_FLAG | CHAMPION_FLAG) else 1.0)
            away, turn = spread * math.sqrt(index / max(count - 1, 1)), index * 2.399963
            place = (round(centre[0] + away * math.cos(turn), 1), round(centre[1] + away * math.sin(turn), 1))
            found.append(Mob(self.unit(), txt, place, level, round(full * life, 1), full, flags=flags, mods=mods))
        return found

    def pack(
        self,
        kind: str | int,
        count: int = 6,
        *,
        at: Point,
        spread: float = 5.0,
        rank: str = 'plain',
        enchantments: Sequence[str | int] = (),
        life: float = 1.0,
    ) -> Situation:
        self.scene.mobs += self.mobs_of(kind, count, at, spread, rank, enchantments, life)
        return self

    def spawn(
        self,
        kind: str | int,
        count: int = 6,
        *,
        at: Point,
        at_second: float | None = None,
        after: int | None = None,
        delay: float = 0.0,
        spread: float = 5.0,
        rank: str = 'plain',
        enchantments: Sequence[str | int] = (),
        label: str = '',
    ) -> Situation:
        """A pack that appears during the play: `at_second` seconds in, or `delay` seconds after the object
        `after` (a unit id) is operated."""
        mobs = self.mobs_of(kind, count, at, spread, rank, enchantments, 1.0)
        self.spawns.append(Spawn(mobs, at_second, after, delay, label or f'{count} {name_of(txt_of(kind))}'))
        return self

    def drop(self, label: str = 'valuable', *, at: Point) -> Situation:
        """Something on the ground the pickup step goes for; `label` is what the macro calls it."""
        self.scene.drops.append(Drop(self.unit(), label, self.spot(at)))
        return self

    def companions(self, *offsets: Point, txt: int = 338) -> Situation:
        """Companions of the character's at the offsets. The arena's companions stand, are never hurt and
        deal nothing: they are only someone else a monster may go for. `txt` 338 is the mercenary's row in
        the Vizier fixture (unit 3830005408 of take 20261013T060607Z-108)."""
        for offset in offsets:
            unit = self.unit()
            self.scene.mobs.append(Mob(unit, txt, self.spot(offset), 0, 128.0, 128.0, owner=1, ally=True))
        return self

    def thing(self, txt: int, *, at: Point, mode: int = 0) -> int:
        """An object to operate (a chest, a seal); its unit id, for `spawn(after=...)`."""
        unit = self.unit()
        self.scene.things.append(Prop(unit, txt, self.spot(at), mode))
        return unit

    def mark(self, label: str, *, at: Point, kind: str = 'target') -> Situation:
        """A mark on the level card: where the teleport key goes."""
        spot = self.spot(at)
        self.marks = (*self.marks, Mark(label, kind, (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS)))
        return self

    def attack_mode(self, on: bool = True) -> Situation:
        self.attack = on
        return self

    def aggro(self, units: float) -> Situation:
        """How far a monster notices the character (stage.py ARENA_AWARE 20, GAME_AWARE 35, EVERYONE)."""
        self.aware = units
        return self

    # -- playing ----------------------------------------------------------------------------------------

    def play(
        self,
        presses: Iterable | None = None,
        seconds: float | None = None,
        seed: int = 1,
        *,
        healer: bool = True,
        keep: bool = False,
        each_tick: Callable[[Stage, RoutePlay], None] | None = None,
    ) -> Outcome:
        """One play with the production controller. `presses` None: the situation's own (a recording's);
        `seconds` None: its own length. `keep`: the outcome carries the stage (`outcome.stage_`, for an
        exporter that wants the whole play); `each_tick` is called after every
        tick of the arena with the stage and the play (an exporter's sampler)."""
        seconds = self.seconds if seconds is None else seconds
        given = spelled(self.presses if presses is None else presses, seconds)
        if self.attack:
            given.insert(0, Press(0.0, ATTACK))
        watch = [unit for unit, _ in self.bosses]
        with awareness(self.aware):
            arena = Stage(
                self.scene, seed=seed, osd=PLAYER_HEALING if healer else None, spawns=self.spawns,
                curses=self.curses, aware=self.aware, lands=self.lands, watch=watch,
            )  # fmt: skip
            play = RoutePlay(arena, given, seconds, seed, self.marks, self.opened, self.bosses, self.as_it_was)
            pressed: list[dict] = []
            play.runner.trace.noted = lambda kind, **record: pressed.append(
                record
            )  # each press over, with what became of it
            if each_tick is not None:
                inner = play.tick

                def tick() -> None:
                    each_tick(arena, play)
                    inner()

                play.tick = tick  # type: ignore[method-assign]
            result = play.run()
        outcome = self.outcome(arena, play, seed, result.seconds)
        if keep:
            outcome.stage_ = arena  # type: ignore[attr-defined]
            outcome.presses_ = given  # type: ignore[attr-defined]
            outcome.play_ = play  # type: ignore[attr-defined]
            # (when it was made, the routine, what became of it): the runner numbers the presses in the order given
            outcome.pressed_ = sorted(  # type: ignore[attr-defined]
                (
                    given[row['n'] - 1].at,
                    str(row['routine']),
                    ', '.join(str(row[key]) for key in ('outcome', 'ended') if row.get(key)),
                )
                for row in pressed
                if 0 < row['n'] <= len(given)
            )
        return outcome

    def outcome(self, arena: Stage, play: RoutePlay, seed: int, seconds: float) -> Outcome:
        ticks: list[Tick] = arena.ticks
        every = max(round(SAMPLE * 25), 1)
        kept = [tick for index, tick in enumerate(ticks) if index % every == 0 or index == len(ticks) - 1]
        hurts = arena.cast.hurts
        dead_at = arena.dead_at
        last: Counter[tuple[str, str]] = Counter()
        points: Counter[tuple[str, str]] = Counter()
        if dead_at is not None:
            for hurt in hurts:
                if hurt.at >= dead_at - LAST_BLOWS:
                    key = (name_of(hurt.txt), hurt.kind)
                    last[key] += 1
                    points[key] += hurt.points
        strikes, casts = [], 0
        for tick in ticks:
            strikes += [round(tick.at, 2)] * (tick.casts - casts)
            casts = tick.casts
        gaps: dict[str, tuple[float, float, float] | None] = {}
        boss_dead: dict[str, float | None] = {}
        for unit, name in self.bosses:
            seen = [gap for _, gap in arena.gaps.get(unit, ())]
            gaps[name] = (round(seen[0], 1), round(min(seen), 1), round(seen[-1], 1)) if seen else None
            boss_dead[name] = arena.fell.get(unit)
        mobs = arena.mobs
        return Outcome(
            name=self.name,
            seed=seed,
            seconds=seconds,
            max_life=arena.max_life,
            start_life=float(self.scene.hero.life),
            dead_at=dead_at,
            killers=[(name, kind, count, round(points[(name, kind)], 1)) for (name, kind), count in last.most_common()],
            life=[(round(tick.at, 2), round(tick.life, 1)) for tick in kept],
            low=round(min((tick.life for tick in ticks), default=arena.life), 1),
            taken=round(arena.taken, 1),
            hurts=list(hurts),
            kills=[
                (round(arena.fell.get(unit, seconds), 2), unit, name_of(mobs.mobs[unit].txt)) for unit in arena.kills
            ],
            cleared_at=arena.cleared_at,
            strikes=strikes,
            track=[(round(tick.at, 2), round(tick.here[0], 1), round(tick.here[1], 1)) for tick in kept],
            crowd=[(round(tick.at, 2), tick.crowd) for tick in kept],
            moved=round(arena.moved, 1),
            potions=list(arena.potions),
            picked=list(arena.picks),
            said=list(arena.told),
            appeared=list(arena.appeared),
            opened=dict(arena.opened),
            gaps=gaps,
            boss_dead=boss_dead,
            stage=play.stage(),
            attack_mode=bool(play.runner.attack_mode),
            alive=len(mobs.live()),
            hostiles=len(mobs.hostile),
        )

    def trials(
        self, seeds: Iterable[int] = range(1, 31), presses: Iterable | None = None, seconds: float | None = None
    ) -> Trials:
        presses = None if presses is None else list(presses)
        return Trials([self.play(presses, seconds, seed) for seed in seeds])


# -- the file -------------------------------------------------------------------------------------------


def dump(situation: Situation, path: Path) -> None:
    """Write the situation as one JSON file: the scene as scene.py writes one, the rest plain."""
    data = {
        'name': situation.name,
        'about': situation.about,
        'source': situation.source,
        'assumed': situation.assumed,
        'seconds': situation.seconds,
        'attack': situation.attack,
        'presses': [list(press) for press in situation.presses],
        'route': {
            'marks': [asdict(mark) for mark in situation.marks],
            'opened': list(situation.opened),
            'bosses': [list(boss) for boss in situation.bosses],
            'as_it_was': situation.as_it_was,
        },
        'spawns': [
            {
                'at': spawn.at,
                'after': spawn.after,
                'delay': spawn.delay,
                'label': spawn.label,
                'mobs': [scene_file._plain(mob) for mob in spawn.mobs],
            }
            for spawn in situation.spawns
        ],
        'curses': [list(curse) for curse in situation.curses],
        'aware': situation.aware,
        'lands': {str(txt): chance for txt, chance in situation.lands.items()},
        'recorded': situation.recorded,
        'scene': scene_file._plain(situation.scene),
    }
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def load(path: Path) -> Situation:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    route = data['route']
    return Situation(
        name=data['name'],
        scene=scene_file._record(Scene, data['scene']),  # type: ignore[arg-type]
        seconds=data['seconds'],
        about=data['about'],
        attack=data['attack'],
        presses=tuple((float(at), routine) for at, routine in data['presses']),
        marks=tuple(Mark(row['label'], row['kind'], tuple(row['spot']), row['use']) for row in route['marks']),
        opened=tuple(route['opened']),
        bosses=tuple((int(unit), name) for unit, name in route['bosses']),
        spawns=[
            Spawn(
                [scene_file._record(Mob, mob) for mob in row['mobs']],
                row['at'],
                row['after'],
                row['delay'],
                row['label'],
            )  # type: ignore[misc]
            for row in data['spawns']
        ],
        curses=tuple((float(at), kind, float(share)) for at, kind, share in data['curses']),
        aware=data['aware'],
        lands={int(txt): chance for txt, chance in data['lands'].items()},
        as_it_was=route['as_it_was'],
        assumed=dict(data['assumed']),
        source=data['source'],
        recorded=data['recorded'],
    )
