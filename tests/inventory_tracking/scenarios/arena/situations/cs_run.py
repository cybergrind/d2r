"""A whole Chaos Sanctuary run as one situation (user, 2026-10-13: "full cs run ... we're in the beginning of
the CS, one press of KP_1, then it runs the whole level automatically; we can simulate some potion drops along
the way ... I'd like to check what it will look like with current state, how far it will reach").

`cs-run` is the game of 12:33 on 2026-10-13 (take 20261013T093331Z-108, schema 4, 252 s, 204 kills, no death)
taken whole as a snapshot, not as a moment:

- the level's ground, rooms and card (the six marks of the level's handler) are the take's `level.json`, all of it;
- the character is the take's first frame: at the entrance from the River of Flame, its life, belt, buffs and
  the weapon set in hand as recorded. The Teleport staff is the one thing set by hand: the base has it full
  (CHARGES); the recording had it empty, which is the variant "the staff empty";
- every hostile the take ever saw on the level's ground stands where the take first saw it, at the life it
  had then, and sleeps until the character is within the game's own awareness (stage.py GAME_AWARE, 35
  units). The 18 the take saw behind the entrance, in the River of Flame, are left out: the level file has no
  ground under them, so here they could neither come nor be reached (`outside` puts them back, to see what
  the macro does with a hostile it has no way to);
- the five seals stand where the take has them, closed, with their own unit ids; the other objects of the take
  (chests) as first seen;
- a seal's boss pack appears as the take has it: the Vizier's six 0.98 s after seal class 396 is opened, De
  Seis's eight 0.98 s after class 394, the Infector's twelve 1.01 s after class 392 (`Spawn(after=...)`);
- Diablo appears 15.3 s after the fifth seal, where the take first saw him (`LevelStage.finale`);
- a potion drops from a kill where the take has one appear by a death (`potion_drops`: 19 of the take's own).

Three things the arena lacks for a whole level are added here, on the test's side (`LevelStage`):

- **the client's sight** (`sight`, units): the macro reads only the monsters and objects within SIGHT of the
  character, as the game's client holds only the units of the rooms round it. A radius, not rooms: an
  assumption (the take's monsters were first seen 53 units off in the median, 64 at the third quartile);
- **a drop from a kill** (`potions`: unit -> the potion and where from the corpse);
- **what appears after every seal** (a `Spawn` with neither a time nor an object: Diablo);
- **the play's end**: LINGER seconds after Diablo's death (the route's next stages are the loot and leaving
  the game, which the arena has no menu for), or when nothing has happened for STALL seconds (no kill, no
  strike, no object used, the character within STILL units of where it was): a stall is the result then, and
  the rest of the cap would add nothing but wall time.

And one thing the service gives the macro that no arena play has had to (kp4.py: "the monster tracker ...
the hunter has none"): **the terror tracker's memory** (`Memory`, installed by `LevelPlay`), without which the
seek step and the pursuit have no room to call explored and go back and forth between two. It is a stand-in
written from terror/tracker.py, not the tracker: the rooms the character was in or next to (`explore`), the
hostiles seen alive where last seen, dropped when dead or when not there within the tracker's HELD_RANGE
(`remembered`), and where each super unique and boss was first seen (`supers`). It is told every tick; the
service's tracker is told by a poll.

`Run` is a `Situation` that is played on a `LevelStage` by a `LevelPlay` (situation.py names its stage and its
play as the module's `Stage` and `RoutePlay`; for a play of a `Run` those names are this file's classes and
are put back after), with driver.py's wall limit for one run of the macro lifted (attack mode is one run for
the whole play).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.cs_run [--cut] [--all]\
        [--seed N] [--only TEXT] [--log FROM TO]

prints a few lines a variant (`played`: the play with the macro's log kept by the arena's clock, `score`,
`told`); rca/2026-10-13/cs-run.md is written from it.
"""

import argparse
import functools
import json
import logging
import math
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.tables import area_level
from inventory_tracking.combat.stance import no_footing
from inventory_tracking.game.layout import HERALD_TIER_STAT, MINION_FLAG, NO_OWNER
from inventory_tracking.game.records import HEALING, REJUVENATION, Drop
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import SEALS, Ground, Walkable
from inventory_tracking.native.layout import DEAD_MODES, TILE_UNITS
from inventory_tracking.takes.takes import MonsterRow, Take, monsters_of
from inventory_tracking.terror.bosses import BOSSES as ACT_BOSSES
from inventory_tracking.terror.monsters import LEVEL_STAT
from inventory_tracking.terror.tracker import HELD_RANGE
from tests.inventory_tracking.scenarios.arena import driver, scene as scene_file
from tests.inventory_tracking.scenarios.arena.cut import full_points
from tests.inventory_tracking.scenarios.arena.game import GROUND_POTIONS
from tests.inventory_tracking.scenarios.arena.kp4 import RoutePlay
from tests.inventory_tracking.scenarios.arena.scene import Mob, Prop, Scene
from tests.inventory_tracking.scenarios.arena.situations import situation as situation_module
from tests.inventory_tracking.scenarios.arena.situations.bestiary import name_of
from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import (
    FIXTURES,
    Outcome,
    Situation,
    dump,
    held,
    load,
    once,
)
from tests.inventory_tracking.scenarios.arena.situations.stage import GAME_AWARE, Spawn, Stage


NAME = 'cs-run'
TAKE = '20261013T093331Z-108'
ABOUT = (
    'a whole Chaos Sanctuary run from the entrance: the level, 210 sleeping monsters, five seals, their boss '
    'packs and Diablo of the game of 12:33, 2026-10-13 (252 s, 204 kills, no death there)'
)
WHOLE = 2_000.0  # units from the entrance: further than any ground of the level
SECONDS = 400.0  # the play's cap; the recorded run took 252
CHARGES = 69  # the staff when full (cut.py STAFF)
SIGHT = 65.0  # units: how far the macro reads monsters and objects (the module text)
SPAWN_AFTER = 2.0  # seconds after a seal's opening within which a first sight is that seal's pack
FINALE = 'Diablo, after the fifth seal'  # the label of the spawn that waits for every seal
DROP_AFTER = 6.0  # seconds: a potion first seen this long after a death, at most
DROP_NEAR = 15.0  # units from the corpse
SUPER_UNIQUE = 0x02
DIABLO = 243  # monstats row (the take's unit rows; bestiary.name_of says 'Diablo')
# txt of a super unique -> the route's name of it (routes/catalog/act4.py)
BOSSES = {306: 'Grand Vizier of Chaos', 312: 'Lord De Seis', 362: 'Infector of Souls'}
ROUTE = (  # the stages of routes/catalog/act4.py for area 108, as `Progress` words them, in order
    'use Vizier seal 1', 'use Vizier seal 2', 'fight Grand Vizier of Chaos', 'use De Seis seal',
    'fight Lord De Seis', 'use Infector seal 1', 'use Infector seal 2', 'fight Infector of Souls', 'fight Diablo',
)  # fmt: skip
POTION_CLASS = {kind: class_id for class_id, (kind, _) in GROUND_POTIONS.items()}  # 'healing' -> the item class
WALL_LIMIT = 3_600.0  # wall seconds one run of the macro may take in a play of a whole level
STALL = 60.0  # seconds with nothing happening after which a play is over (the module text)
STILL = 10.0  # units: a character this near where it was has not moved
LINGER = 5.0  # seconds a play goes on after Diablo's death


# -- the stage ------------------------------------------------------------------------------------------


class Memory:
    """What the service's terror tracker remembers of a level for the hunter, kept by the stage (the module
    text): `explored`, `remembered` and `supers` are the three callables the service hands over
    (appraisal/service.py: `zones.visited_rooms`, `zones.remembered`, `zones.supers`)."""

    def __init__(self, area: int, rooms: Sequence[dict]) -> None:
        self.area = area
        self.rooms = [(room['x'], room['y'], room['width'], room['height']) for room in rooms]
        self.seen: set[tuple] = set()
        self.positions: dict[int, tuple[float, float, bool]] = {}  # unit -> x, y, a leader
        self.bosses: dict[int, Point] = {}

    def note(self, here: Point, monsters: Iterable[Any], dead: Iterable[int]) -> None:
        """One look: the character's place, the hostiles the client holds, the units dead."""
        x, y = here[0] / TILE_UNITS, here[1] / TILE_UNITS
        for rx, ry, width, height in self.rooms:  # terror/tracker.py `explore`
            if rx <= x < rx + width and ry <= y < ry + height:
                self.seen.update(
                    room
                    for room in self.rooms
                    if room[0] <= rx + width
                    and rx <= room[0] + room[2]
                    and room[1] <= ry + height
                    and ry <= room[1] + room[3]
                )
                break
        present = set()
        for monster in monsters:
            present.add(monster.unit_id)
            if monster.mode in DEAD_MODES:
                self.positions.pop(monster.unit_id, None)
                continue
            self.positions[monster.unit_id] = (monster.x, monster.y, monster.leader)
            if monster.flags & SUPER_UNIQUE or monster.txt_id in ACT_BOSSES:
                self.bosses.setdefault(monster.unit_id, (monster.x, monster.y))
        for unit in dead:
            self.positions.pop(unit, None)
        for unit, (mx, my, _) in list(self.positions.items()):  # it moved or died unseen
            if unit not in present and math.dist((mx, my), here) <= HELD_RANGE:
                del self.positions[unit]

    def explored(self, area: int) -> set[tuple]:
        return self.seen if area == self.area else set()

    def remembered(self, area: int) -> list[tuple[int, float, float, bool]]:
        if area != self.area:
            return []
        return [(unit, x, y, leader) for unit, (x, y, leader) in self.positions.items()]

    def supers(self, area: int) -> list[Point]:
        return list(self.bosses.values()) if area == self.area else []


class LevelPlay(RoutePlay):
    """`RoutePlay` whose hunter and runner have the tracker's memory, as the service gives it to them."""

    def __init__(self, arena: Any, *given: Any) -> None:
        super().__init__(arena, *given)
        memory = getattr(arena, 'memory', None)
        if memory is not None:
            self.hunter.remembered, self.hunter.explored = memory.remembered, memory.explored
            self.runner.supers = memory.supers


class LevelStage(Stage):
    """`Stage` for a whole level (the module text): the client's sight, potions from kills, the finale."""

    sight: float | None = None  # None while `Arena.__init__` shows the world for the first time

    def __init__(
        self, scene: Scene, *, sight: float | None = SIGHT,
        potions: Mapping[int, tuple[str, float, float]] | None = None, stall: float | None = STALL,
        finale: int | None = None, **given: Any,
    ) -> None:  # fmt: skip
        super().__init__(scene, **given)
        self.stall, self.last_unit = stall, finale  # `finale`: the unit whose death ends the play (Diablo)
        self.stalled_at: float | None = None  # when the play was ended for a stall
        self.finale_fell: float | None = None  # when the finale's unit died
        self.counted = 0  # the kills looked at so far (a potion, the finale's death)
        self.busy = (0.0, self.here, 0, 0, 0)  # the last time something happened, and the counts then
        self.memory = Memory(self.scene.hero.area, self.scene.rooms)
        self.sight = sight
        self.gifts = dict(potions or {})  # unit -> the potion its death leaves (`Arena.potions` is who drank)
        self.seals = [thing.unit_id for thing in self.things if thing.txt_id in SEALS]
        self.dropped: list[tuple[float, int, str]] = []  # (seconds, the unit killed, the potion's kind)
        self.next_drop = 800_000_000
        self.show()
        self.remember()

    def remember(self) -> None:
        hostile = [m for m in self.world.monsters if not m.ally and m.owner == NO_OWNER]
        self.memory.note(self.here, hostile, self.world.dead)

    def seen(self, at: Point) -> bool:
        return self.sight is None or math.dist(at, self.here) <= self.sight

    def show(self) -> None:
        super().show()
        if self.sight is None:
            return
        world = self.world
        kept = tuple(m for m in world.monsters if m.ally or m.owner != NO_OWNER or self.seen((m.x, m.y)))
        if len(kept) != len(world.monsters):
            self.world = replace(world, monsters=kept)

    def run(self, seed: int = 1):
        run = super().run(seed)
        run.things = lambda: tuple(thing for thing in self.things if self.seen((thing.x, thing.y)))
        run.containers = run.things
        return run

    def play_tick(self) -> None:
        now = self.clock.now
        for thing in self.things:  # as `Stage.play_tick` notes an opening, a tick earlier for the finale's due
            if thing.mode and thing.unit_id not in self.opened:
                self.opened[thing.unit_id] = now
        if self.seals and all(unit in self.opened for unit in self.seals):
            last = max(self.opened[unit] for unit in self.seals)
            for spawn in self.spawns:
                if spawn.at is None and spawn.after is None and spawn.due is None:
                    spawn.due = last + spawn.delay
        super().play_tick()
        for unit in self.kills[self.counted :]:
            if unit in self.gifts:
                self.leave_potion(now, unit, *self.gifts[unit])
            if unit == self.last_unit:
                self.finale_fell = now
        self.counted = len(self.kills)
        self.remember()
        self.ending(now)

    def ending(self, now: float) -> None:
        """The play's end before its cap (the module text): after the finale's death, or at a stall."""
        if self.over is not None:
            return
        if self.finale_fell is not None and now >= self.finale_fell + LINGER:
            self.end()
            return
        since, where, kills, casts, used = self.busy
        if (len(self.kills), self.casts, len(self.opened)) != (kills, casts, used) or (
            math.dist(where, self.here) > STILL
        ):
            self.busy = (now, self.here, len(self.kills), self.casts, len(self.opened))
        elif self.stall is not None and now - since >= self.stall:
            self.stalled_at = now
            self.end()

    def leave_potion(self, now: float, unit: int, kind: str, dx: float, dy: float) -> None:
        """A potion on the ground by the corpse of `unit`: where the take had it from its corpse, or on the
        corpse when nobody can stand there."""
        corpse = self.mobs.mobs[unit].at
        at = (round(corpse[0] + dx), round(corpse[1] + dy))
        if not self.footing(at):
            at = (round(corpse[0]), round(corpse[1]))
        class_id = POTION_CLASS[kind]
        self.next_drop += 1
        self.drop_class[self.next_drop] = class_id
        lying = Drop(self.next_drop, float(at[0]), float(at[1]), GROUND_POTIONS[class_id][1], kind)
        self.loot = replace(self.loot, drops=(*self.loot.drops, lying))
        self.dropped.append((now, unit, kind))


@dataclass
class Run(Situation):
    """A situation played on a `LevelStage`. `potions`: (unit, the potion's kind, dx, dy from the corpse)."""

    sight: float = SIGHT
    potions: tuple[tuple[int, str, float, float], ...] = ()
    stall: float | None = STALL
    notes: dict[str, Any] = field(default_factory=dict)  # what the cut counted (the fixture's `level.notes`)
    outside: list[Mob] = field(default_factory=list)  # the take's hostiles off the level's ground, left out

    def play(self, *args: Any, **kwargs: Any) -> Outcome:
        staged = functools.partial(
            LevelStage, sight=self.sight, potions={unit: (kind, dx, dy) for unit, kind, dx, dy in self.potions},
            stall=self.stall, finale=next((unit for unit, name in self.bosses if name == 'Diablo'), None),
        )  # fmt: skip
        saved = situation_module.Stage, situation_module.RoutePlay, driver.WALL_LIMIT
        situation_module.Stage, situation_module.RoutePlay = staged, LevelPlay  # type: ignore[assignment,misc]
        driver.WALL_LIMIT = WALL_LIMIT
        try:
            return super().play(*args, **kwargs)
        finally:
            situation_module.Stage, situation_module.RoutePlay, driver.WALL_LIMIT = saved  # type: ignore[misc]


# -- the cut --------------------------------------------------------------------------------------------


def mob_of(row: MonsterRow, known: Mapping[int, dict], area: int) -> Mob:
    """A monster of the take as cut.py `cut` makes one: its level, enchantments and Herald tier from
    `units.jsonl`, its points from the type's in the area, the life as the share the row has."""
    unit = known.get(row.unit) or {}
    stats = unit.get('stats', {})
    tier = int(stats.get(str(HERALD_TIER_STAT), 0))
    full = full_points(row, area, tier)
    return Mob(
        row.unit, row.txt, row.at,
        level=int(stats.get(str(LEVEL_STAT)) or area_level(area) or 0),
        life=round(full * row.life_share, 1), full=full, flags=row.flags, mods=tuple(unit.get('mods', ())), tier=tier,
    )  # fmt: skip


def first_sights(take: Take) -> dict[int, tuple[float, MonsterRow]]:
    """Each hostile of the take alive at its first sight: unit -> (seconds into the take, its row then)."""
    zero = take.frames[0]['t']
    found: dict[int, tuple[float, MonsterRow]] = {}
    for frame in take.frames:
        for row in monsters_of(frame):
            if row.unit not in found and row.hostile and row.alive and row.at != (0.0, 0.0):
                found[row.unit] = (frame['t'] - zero, row)
    return found


def objects_of(take: Take) -> list[tuple[float, list]]:
    """Each object of the take as first seen, one a (class, place): (seconds, its `o` row). The client gives
    an object a new unit id when it comes back into sight; the first is kept."""
    zero = take.frames[0]['t']
    found: dict[tuple, tuple[float, list]] = {}
    for frame in take.frames:
        for row in frame.get('o', ()):
            found.setdefault((row[1], row[3], row[4]), (frame['t'] - zero, row))
    return list(found.values())


def openings(take: Take) -> dict[int, float]:
    """A seal's unit -> the seconds into the take at which it left mode 0."""
    zero = take.frames[0]['t']
    found: dict[int, float] = {}
    for frame in take.frames:
        for row in frame.get('o', ()):
            if row[1] in SEALS and row[2] and row[0] not in found:
                found[row[0]] = frame['t'] - zero
    return found


def potion_drops(take: Take) -> tuple[list[tuple[int, str, float, float]], int]:
    """The take's own potions as drops from kills: each healing or rejuvenation potion first seen on the ground
    (one a place: the client renumbers a drop that comes back into sight) is given to the monster that died
    nearest it, within DROP_NEAR units and DROP_AFTER seconds before; (unit, kind, dx, dy from the corpse).
    Also how many potions had no such death."""
    zero = take.frames[0]['t']
    killed = {event['unit']: event['t'] - zero for event in take.events if event.get('event') == 'kill'}
    places: dict[int, Point] = {}
    seen: set[tuple] = set()
    found: dict[int, tuple[int, str, float, float]] = {}
    orphans = 0
    for frame in take.frames:
        at = frame['t'] - zero
        for row in monsters_of(frame):
            if row.at != (0.0, 0.0) and row.alive:
                places[row.unit] = row.at
        for _, x, y, kind, *_ in frame.get('g') or ():
            if kind not in (HEALING, REJUVENATION) or (x, y, kind) in seen:
                continue
            seen.add((x, y, kind))
            near = [
                (math.dist(places[unit], (x, y)), unit)
                for unit, when in killed.items()
                if unit in places and unit not in found and -0.2 <= at - when <= DROP_AFTER
            ]
            gap, unit = min(near, default=(math.inf, 0))
            if gap > DROP_NEAR:
                orphans += 1
                continue
            found[unit] = (unit, kind, round(x - places[unit][0], 1), round(y - places[unit][1], 1))
    return list(found.values()), orphans


def cut_run(takes: Path = TAKES) -> Run:
    """The take whole as a `Run` (the module text has where each part comes from)."""
    directory = takes / TAKE
    take = Take.load(directory)
    length = take.frames[-1]['t'] - take.frames[0]['t']
    base = from_take(directory, 0.0, length, name=NAME, about=ABOUT, reach=WHOLE)
    scene, area = base.scene, base.scene.hero.area
    known = {unit['unit']: unit for unit in take.units}
    sights = first_sights(take)
    opened = openings(take)
    things = [Prop(row[0], row[1], (row[3], row[4]), 0 if row[1] in SEALS else row[2]) for _, row in objects_of(take)]
    seal_of = {prop.unit: prop for prop in things if prop.txt in SEALS}

    packs: dict[int, list[tuple[float, MonsterRow]]] = {}
    diablo = [(at, row) for at, row in sights.values() if row.txt == DIABLO]
    asleep = []
    for at, row in sights.values():
        if row.txt == DIABLO:
            continue
        cause = next((unit for unit, when in opened.items() if 0.0 <= at - when <= SPAWN_AFTER), None)
        if cause is not None and row.flags & (SUPER_UNIQUE | MINION_FLAG):
            packs.setdefault(cause, []).append((at, row))
        else:
            asleep.append(row)
    barred = no_footing(Ground(Walkable(**grid) for grid in scene.ground), ())
    assert barred is not None
    mobs = [mob_of(row, known, area) for row in asleep]
    outside = [mob for mob in mobs if barred(mob.at)]  # the River of Flame's, behind the entrance
    scene.mobs = [mob for mob in scene.mobs if mob.owner is not None or mob.ally]  # the companions of frame 0
    scene.mobs += [mob for mob in mobs if not barred(mob.at)]
    scene.things = things

    spawns = []
    for unit, rows in sorted(packs.items(), key=lambda item: opened[item[0]]):
        mobs = [mob_of(row, known, area) for _, row in rows]
        names = ' and '.join(sorted({name_of(mob.txt) for mob in mobs}))
        delay = round(min(at for at, _ in rows) - opened[unit], 2)
        spawns.append(Spawn(mobs, after=unit, delay=delay, label=f'{len(mobs)} {names} (seal {seal_of[unit].txt})'))
    last = max(opened.values())
    for at, row in diablo:
        spawns.append(Spawn([mob_of(row, known, area)], delay=round(at - last, 2), label=FINALE))
    bosses = tuple(
        (row.unit, 'Diablo' if row.txt == DIABLO else BOSSES[row.txt])
        for _, row in sights.values()
        if row.txt == DIABLO or (row.txt in BOSSES and row.flags & SUPER_UNIQUE)
    )
    potions, orphans = potion_drops(take)
    hero = scene.hero
    recorded_charges = hero.sets[1].teleport_charges
    scene.hero = replace(hero, sets=(hero.sets[0], replace(hero.sets[1], teleport_charges=CHARGES)))
    assumed = {
        **base.assumed,
        'hero.sets.teleport_charges': f'{CHARGES}: the staff full; the take had {recorded_charges} ("staff empty")',
        'scene.mobs': (
            "every hostile of the take on the level's ground where it was first seen, asleep until the character "
            f'is near; the {len(outside)} off that ground (the River of Flame) left out'
        ),
        'spawns': 'a seal pack after its seal as the take has it; Diablo that long after the fifth seal',
        'level.sight': f"the macro reads monsters and objects within {SIGHT:g} units: a radius for the client's rooms",
        'level.potions': f'a potion of the take given to the death nearest it ({DROP_NEAR:g} units, {DROP_AFTER:g} s)',
        'route.bosses': 'which unit is which boss of the route: the super uniques by txt, Diablo by his row',
    }
    kills = sum(1 for event in take.events if event.get('event') == 'kill')
    notes = {
        'hostiles': len(sights),
        'asleep': len(asleep) - len(outside),
        'outside': len(outside),
        'packs': {str(seal_of[unit].txt): len(rows) for unit, rows in packs.items()},
        'opened': {str(seal_of[unit].txt): round(when, 2) for unit, when in opened.items()},
        'kills': kills,
        'seconds': round(length, 1),
        'potions': len(potions),
        'potions_without_a_death': orphans,
        'recorded_charges': recorded_charges,
    }
    values = {item.name: getattr(base, item.name) for item in fields(Situation)}
    values.update(seconds=SECONDS, bosses=bosses, spawns=spawns, aware=GAME_AWARE, assumed=assumed, attack=False)
    return Run(**values, sight=SIGHT, potions=tuple(potions), notes=notes, outside=outside)


def dump_run(run: Run, path: Path) -> None:
    """situation.py `dump`, with this file's part under `level` (situation.py `load` reads past it)."""
    dump(run, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['level'] = {
        'sight': run.sight,
        'potions': [list(row) for row in run.potions],
        'notes': run.notes,
        'outside': [scene_file._plain(mob) for mob in run.outside],
    }
    path.write_text(json.dumps(data, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8')


def load_run(path: Path) -> Run:
    base = load(path)
    level = json.loads(Path(path).read_text(encoding='utf-8'))['level']
    values = {item.name: getattr(base, item.name) for item in fields(Situation)}
    potions = tuple((int(unit), kind, float(dx), float(dy)) for unit, kind, dx, dy in level['potions'])
    outside = [scene_file._record(Mob, mob) for mob in level['outside']]
    return Run(**values, sight=level['sight'], potions=potions, notes=level['notes'], outside=outside)  # type: ignore[arg-type]


def cut() -> None:
    FIXTURES.mkdir(exist_ok=True)
    dump_run(cut_run(), FIXTURES / f'{NAME}.json')


@functools.cache
def stored() -> Run:
    return load_run(FIXTURES / f'{NAME}.json')


# -- the variants ---------------------------------------------------------------------------------------


def with_outside(run: Run) -> Run:
    """The run with the River of Flame's monsters back where the take saw them, on no ground."""
    found = run.variant()
    found.scene.mobs += [replace(mob) for mob in found.outside]
    return found


def empty(run: Situation) -> Situation:
    """The staff at no charge, as the take had it."""
    return run.variant().hero(charges=0)


Variant = tuple[str, Situation, list | None]
ONCE = 'KP_1 once'
HELD = 'KP_1 once + KP_4 held, every 0.3 s'
ALONE = 'attack mode alone (KP_3)'
RECORDED = 'as recorded (187 KP_4, 64 KP_1)'
FULL, EMPTY = f'staff {CHARGES}', 'staff empty'


def ways() -> dict[str, tuple[list | None, bool]]:
    """A way of driving -> (its presses; None: the recording's own, whether attack mode is on from the start)."""
    return {
        ONCE: ([once('pickup', at=0.0)], False),
        HELD: ([once('pickup', at=0.0), held('teleport', every=0.3, since=0.3)], False),
        ALONE: ([], True),
        'KP_1 every 2 s': ([held('pickup', every=2.0)], False),
        RECORDED: (None, False),
    }


def pair(way: str, staff: str, scene: Situation | None = None, note: str = '') -> list[Variant]:
    """One way of driving on one staff, by today's keys and by the pursuit loop (`Situation.logic`)."""
    presses, attack = ways()[way]
    base = scene or (stored() if staff == FULL else empty(stored()))
    situation = base.variant(attack=attack)
    label = f'{way}, {staff}{note}'
    return [(f'{label}: today', situation.logic('today'), presses), (f'{label}: new', situation.logic('new'), presses)]


def variants() -> list[Variant]:
    """What the viewer shows: the three ways asked for with the staff full, then the two that drive the route
    with the staff empty, as the last two real games were played."""
    return [
        *pair(ONCE, FULL),
        *pair(HELD, FULL),
        *pair(ALONE, FULL),
        *pair(HELD, EMPTY),
        *pair(RECORDED, EMPTY),
    ]


def every() -> list[Variant]:
    """`variants` and the rest of the report's table: the other ways on the other staff, the pickup key pressed
    again and again, and one press with the River of Flame's monsters standing behind the entrance."""
    return [
        *variants(),
        *pair(ONCE, EMPTY),
        *pair(ALONE, EMPTY),
        *pair(RECORDED, FULL),
        *pair('KP_1 every 2 s', FULL),
        *pair('KP_1 every 2 s', EMPTY),
        *pair(ONCE, FULL, with_outside(stored()), ', the River of Flame behind'),
    ]


# -- what a play came to --------------------------------------------------------------------------------


class Watch(logging.Handler):
    """A play watched from the side: every line the macro logs ('Macro: ...', the card's lines among them)
    with the arena's time, and the runner's state at each change (attack mode, whether a run works, the
    sweep's steps left, the route's stage). It is the play's `each_tick` and a handler of the production log."""

    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.arena: Stage | None = None
        self.lines: list[tuple[float, str]] = []
        self.states: list[tuple[float, tuple[bool, bool, int, str | None]]] = []

    def emit(self, record: logging.LogRecord) -> None:
        text = record.getMessage()
        if self.arena is not None and self.arena.over is None and text.startswith('Macro: '):
            self.lines.append((self.arena.clock.now, text.removeprefix('Macro: ')))

    def __call__(self, arena: Stage, play: Any) -> None:
        self.arena = arena
        if arena.over is not None:
            return  # the play's end turns the mode off: not the macro's doing
        runner = play.runner
        row = (bool(runner.attack_mode), bool(runner.working), play.hunter.sweep.steps, play.stage())
        if not self.states or self.states[-1][1] != row:
            self.states.append((arena.clock.now, row))


@dataclass
class Score:
    """How far one play of the run got. Times are seconds of the play; None: never."""

    label: str
    seed: int
    seconds: float
    ended: str  # why the play ended: 'Diablo dead', 'dead', 'stalled' (nothing for STALL seconds) or 'the cap'
    seals: dict[str, float | None]  # the mark's label -> when it was opened
    bosses: dict[str, float | None]  # the route's name -> when it died
    appeared: list[tuple[float, str]]
    stage: str | None  # the route's stage at the end
    stages_done: int  # of ROUTE
    stages: list[tuple[float, str | None]]  # when the route came to each stage
    kills: int
    hostiles: int
    lost: float
    low: float
    potions: dict[str, int]  # who drank -> how many
    picked: int
    dropped: int
    dead_at: float | None
    killers: str
    moved: float
    strikes: int
    charges: int  # of the staff, used
    end: Point
    near: tuple[str, float]  # the nearest mark to the end and how far
    progress_at: float  # the last opening, appearance or boss's death
    last_kill: float | None
    last_move: float | None  # the last time the character was more than STILL units from where it ends
    last_lines: list[tuple[float, str]]  # the macro's log
    often: list[tuple[str, int]]  # the log's lines after `progress_at`, numbers taken out, the most said first
    stopped: list[tuple[str, int]]  # the card's "Macro stopped: ..." lines after `progress_at` (not in the log)
    attack_mode: bool  # at the last look before the end
    nearest: tuple[str, float] | None  # the nearest hostile alive at the end and how far; None: none left
    gaps: dict[str, tuple[float, float, float] | None]  # a boss: its first, least and last distance while alive
    sweep: int  # the sweep's steps left then
    wall: float = 0.0

    @property
    def done(self) -> bool:
        return self.bosses.get('Diablo') is not None


def shape(text: str) -> str:
    """A log line with its numbers taken out, so that lines that differ in a place or a count are one."""
    found, digits = [], False
    for letter in text:
        if letter.isdigit() or (digits and letter in '.,'):
            if not digits:
                found.append('#')
            digits = True
        else:
            digits = False
            found.append(letter)
    return ''.join(found)


def score(label: str, run: Situation, outcome: Outcome, watch: Watch | None = None, wall: float = 0.0) -> Score:
    props = {(round(prop.at[0]), round(prop.at[1])): prop.unit for prop in run.scene.things}
    marks = {mark.label: (mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS) for mark in run.marks}
    seals = {}
    for mark in run.marks:
        if mark.use:
            unit = props.get((round(marks[mark.label][0]), round(marks[mark.label][1])))
            seals[mark.label] = outcome.opened.get(unit) if unit is not None else None
    stage = outcome.stage
    done = ROUTE.index(stage) if stage in ROUTE else len(ROUTE)
    events = [*(at for at in seals.values() if at is not None), *(at for at in outcome.boss_dead.values() if at)]
    events += [at for at, *_ in outcome.appeared]
    progress_at = max(events, default=0.0)
    end = outcome.track[-1][1:]
    last_move = next((at for at, x, y in reversed(outcome.track) if math.dist((x, y), end) > STILL), None)
    lines = watch.lines if watch is not None else [(at, text.removeprefix('Macro: ')) for at, text in outcome.said]
    often = Counter(shape(text) for at, text in lines if at >= progress_at).most_common(8)
    stops = Counter(
        shape(text.removeprefix('Macro stopped: '))
        for at, text in outcome.said
        if at >= progress_at and text.startswith('Macro stopped: ')
    )
    arena = getattr(outcome, 'stage_', None)
    cause = ', '.join(f'{count} {name} {kind} ({points:.0f})' for name, kind, count, points in outcome.killers)
    stages: list[tuple[float, str | None]] = []
    for at, (*_, name) in watch.states if watch is not None else ():
        if not stages or stages[-1][1] != name:
            stages.append((round(at, 1), name))
    final = watch.states[-1][1] if watch is not None and watch.states else (outcome.attack_mode, False, 0, stage)
    if outcome.dead_at is not None:
        ended = 'dead'
    elif outcome.boss_dead.get('Diablo') is not None:
        ended = 'Diablo dead'
    else:
        ended = 'stalled' if getattr(arena, 'stalled_at', None) is not None else 'the cap'
    near = min(marks, key=lambda name: math.dist(marks[name], end))
    nearest = None
    if arena is not None:
        live = [
            (math.dist(arena.mobs.mobs[unit].at, end), name_of(arena.mobs.mobs[unit].txt)) for unit in arena.mobs.live()
        ]
        nearest = min(((name, round(gap, 1)) for gap, name in live), key=lambda row: row[1], default=None)
    return Score(
        label=label, seed=outcome.seed, seconds=outcome.seconds, ended=ended, seals=seals,
        bosses=dict(outcome.boss_dead), appeared=[(round(at, 1), text) for at, text, _ in outcome.appeared],
        stage=stage, stages_done=done, stages=stages, kills=len(outcome.kills), hostiles=outcome.hostiles,
        lost=outcome.taken, low=outcome.low, potions=dict(Counter(who for _, _, who in outcome.potions)),
        picked=len(outcome.picked), dropped=len(arena.dropped) if arena is not None else -1,
        dead_at=outcome.dead_at, killers=cause, moved=outcome.moved, strikes=len(outcome.strikes),
        charges=arena.charges if arena is not None else -1, end=(end[0], end[1]),
        near=(near, round(math.dist(marks[near], end), 1)), progress_at=progress_at,
        last_kill=max((at for at, *_ in outcome.kills), default=None), last_move=last_move,
        last_lines=lines[-5:], often=often, stopped=stops.most_common(4), attack_mode=final[0], sweep=final[2],
        nearest=nearest, gaps=dict(outcome.gaps), wall=wall,
    )  # fmt: skip


def at_(value: float | None) -> str:
    return 'never' if value is None else f'{value:.0f}'


def told(found: Score) -> str:
    """A play in a few lines."""
    seals = ', '.join(f'{label} {at_(at)}' for label, at in found.seals.items())
    bosses = ', '.join(f'{name} {at_(at)}' for name, at in found.bosses.items())
    death = (
        f'DEAD at {found.dead_at:.1f} s ({found.killers or "no blow in the last 1.5 s"})' if found.dead_at else 'alive'
    )
    lines = [
        f'{found.label} (seed {found.seed}): {found.seconds:.0f} s ({found.ended}), {death}; stage at the end: '
        f'{found.stage} ({found.stages_done} of {len(ROUTE)} done)',
        f'  seals opened at: {seals}',
        f'  bosses dead at: {bosses}',
        '  stages: ' + ', '.join(f'{at:g} {name}' for at, name in found.stages),
        f'  kills {found.kills} of {found.hostiles}, strikes {found.strikes}, moved {found.moved:.0f}, charges used '
        f'{found.charges}, life lost {found.lost:.0f}, least {found.low:.0f}, potions {found.potions}, '
        f'dropped {found.dropped}, picked {found.picked}',
        f'  ends at ({found.end[0]:.0f}, {found.end[1]:.0f}), {found.near[1]:.0f} from {found.near[0]}; '
        f'last progress {found.progress_at:.0f} s, last kill {at_(found.last_kill)} s, within {STILL:g} of '
        f'the end since {at_(found.last_move)} s; attack mode {"on" if found.attack_mode else "off"}, sweep steps '
        f'left {found.sweep}; nearest hostile alive: {found.nearest}; {found.wall:.0f} s of wall time',
        '  bosses, distance first / least / last while alive: '
        + ', '.join(f'{name} {gap and "/".join(f"{part:.0f}" for part in gap)}' for name, gap in found.gaps.items()),
        '  logged most since the last progress: ' + '; '.join(f'{count}x "{text}"' for text, count in found.often),
        '  logged last: ' + '; '.join(f'{at:.1f} "{text}"' for at, text in found.last_lines),
        '  "Macro stopped" since the last progress: '
        + ('; '.join(f'{count}x "{text}"' for text, count in found.stopped) or 'never'),
    ]
    return '\n'.join(lines)


def played(
    label: str, run: Situation, presses: Iterable | None, seed: int = 1, watch: Watch | None = None
) -> tuple[Score, Outcome, Watch]:
    """One play, watched: its score, the outcome (with the stage: `outcome.stage_`) and the watch."""
    watch = watch or Watch()
    log = logging.getLogger('inventory_tracking')
    level = log.level
    log.addHandler(watch)
    log.setLevel(logging.INFO)
    began = time.perf_counter()
    try:
        outcome = run.play(presses, seed=seed, keep=True, each_tick=watch)
    finally:
        log.removeHandler(watch)
        log.setLevel(level)
    return score(label, run, outcome, watch, time.perf_counter() - began), outcome, watch


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the fixture again from the take')
    parser.add_argument('--seed', type=int, action='append', default=[])
    parser.add_argument('--only', default='', help='the variants whose label holds this')
    parser.add_argument('--seconds', type=float, default=None)
    parser.add_argument('--log', nargs=2, type=float, metavar=('FROM', 'TO'), help="print the macro's log between")
    parser.add_argument('--all', action='store_true', help="every variant (default: the catalog's)")
    args = parser.parse_args(argv)
    if args.cut:
        cut()
        stored.cache_clear()
    print(json.dumps(stored().notes))
    for label, run, presses in every() if args.all else variants():
        if args.only not in label:
            continue
        for seed in args.seed or [1]:
            if args.seconds:
                run = run.variant(seconds=args.seconds)
            found, _, watch = played(label, run, presses, seed)
            print(told(found), flush=True)
            if args.log:
                for at, text in watch.lines:
                    if args.log[0] <= at <= args.log[1]:
                        print(f'    {at:7.2f} {text}')
                for at, row in watch.states:
                    if args.log[0] <= at <= args.log[1]:
                        print(f'    {at:7.2f} attack mode {row[0]}, working {row[1]}, sweep {row[2]}, stage {row[3]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
