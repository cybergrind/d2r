"""A situation cut from a recorded take: `(take directory, start, length)` -> a `Situation` that needs the
take no more (takes are git-ignored and deleted; the fixture is what stays).

    situation = from_take(TAKES / '20261013T093331Z-108', 72.0, 16.0, name='vizier-seal', bosses={306: BOSS})
    dump(situation, FIXTURES / 'vizier-seal.json')

Where each part comes from, and what happens with a take that does not hold it (every such fact is written
into the fixture's `assumed` with its reason; `by_hand` is how a caller gives what he read in the session log):

| What | Schema 4 take | Older take |
| --- | --- | --- |
| ground, rooms, doors, monsters, the character's place, life, mana | cut.py `cut` at the start's frame | the same |
| a monster's level, enchantments, Herald tier | `units.jsonl` (cut.py) | the same; `mods` since 2026-10-11 |
| the weapon set in hand, the staff's charges | frame key `w` | `by_hand`, else cut.py's guess from the resistances |
| the belt | `b` | cut.py's default (a full belt) |
| Psychic Ward, Hex: Purge, Consume | `f` | `by_hand`, else up |
| drops on the ground | `g` | none |
| objects (seals, chests) with their mode | `o`, each at its last row | a `Prop` on each mark with a `use` (`by_hand`) |
| the level card | the level's handler over the take's rooms (kp4.py `handler_marks`) | the same |
| marks used before, attack mode at the start | the last `state` event up to the start | `by_hand` |
| which unit is which boss | `bosses` (txt of a super unique -> the route's name): always by hand | the same |
| the presses | `request` events in the window (their time less their age) | `by_hand['presses']` |
| monsters that appear in the window | first sights after the start, as `Spawn`s (below) | the same |
| the recording's side | frames and events of the window (`track`) | the same, without the macro's lines |

**Monsters that appear.** A hostile first seen after the start (and within `reach` of the character then) is
put into the play when the take first saw it, where it saw it, at full life as it was: a play-back of the
take's appearance, not a model of why it appeared. When an object of the scene changed its mode within
SPAWN_AFTER seconds before that first sight (a seal being opened), the appearance is tied to that object
instead: the pack comes that long after the arena's own opening of it, whenever the play gets there. A
monster that only walked into the client's sight is played the same way (the arena cannot tell the two apart).

Not carried: a curse on the character (frame key `s` is raw state words; give `curses=` by hand as
incident.py does), the inventory's room (`i`), the mercenary's damage.
"""

import datetime
import math
from collections.abc import Mapping, Sequence
from dataclasses import replace
from itertools import pairwise
from pathlib import Path
from typing import Any

from inventory_tracking.builds.warlock.echoing_strike.mechanics import MISSILE
from inventory_tracking.game.records import GOLD, HEALING, REJUVENATION
from inventory_tracking.macros.runner import ATTACK
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.takes.takes import Take, monsters_of, player_of
from tests.inventory_tracking.scenarios.arena.cut import DEFAULT_HERO, cut, level_of
from tests.inventory_tracking.scenarios.arena.game import GROUND_POTIONS, POTIONS
from tests.inventory_tracking.scenarios.arena.incident import births
from tests.inventory_tracking.scenarios.arena.kp4 import MADE_UP, Mark, handler_marks
from tests.inventory_tracking.scenarios.arena.scene import Drop, Prop, Scene
from tests.inventory_tracking.scenarios.arena.situations.bestiary import name_of
from tests.inventory_tracking.scenarios.arena.situations.situation import SAMPLE, Situation
from tests.inventory_tracking.scenarios.arena.situations.stage import Spawn


TAKES = Path('inventory_tracking/runs/combat')
SPAWN_AFTER = 2.0  # seconds: a first sight this soon after an object's change of mode is that object's doing
SUPER_UNIQUE = 0x02  # the type flag of a super unique (combat/sim/monsters.py SUPER_FLAG)
POTION_CODE = {kind: POTIONS[class_id]['code'] for class_id, (kind, _) in GROUND_POTIONS.items()}


def second_of(take: Take, start: float | str) -> float:
    """`start` as seconds into the take: a number as it is; a clock time ('12:34:43.5', local, or a whole
    ISO time with its zone) against the manifest's `started_at`."""
    if not isinstance(start, str):
        return float(start)
    began = datetime.datetime.fromisoformat(take.manifest['started_at'])
    if 'T' in start:
        asked = datetime.datetime.fromisoformat(start)
    else:
        local = began.astimezone()
        asked = datetime.datetime.combine(local.date(), datetime.time.fromisoformat(start), local.tzinfo)
    return (asked - began).total_seconds()


def last(take: Take, key: str, upto: int) -> Any:
    """What a frame key written only at a change held at frame `upto` (None: never written by then)."""
    found = None
    for frame in take.frames[: upto + 1]:
        found = frame.get(key, found)
    return found


def objects_at(take: Take, upto: int) -> dict[int, list]:
    """The `o` rows by unit, each as last written up to frame `upto`."""
    found: dict[int, list] = {}
    for frame in take.frames[: upto + 1]:
        for row in frame.get('o', ()):
            found[row[0]] = row
    return found


def openings(take: Take, first: int) -> list[tuple[float, int]]:
    """(the take's time, the unit) of each object that left mode 0 after frame `first`."""
    modes = {unit: row[2] for unit, row in objects_at(take, first).items()}
    found = []
    for frame in take.frames[first + 1 :]:
        for row in frame.get('o', ()):
            if not modes.get(row[0]) and row[2]:
                found.append((frame['t'], row[0]))
            modes[row[0]] = row[2]
    return found


def appearances(take: Take, scene: Scene, first: int, end: float, reach: float, things: Sequence[Prop]) -> list[Spawn]:
    """The hostiles first seen after frame `first` up to `end`, as spawns (the module text)."""
    zero = take.frames[first]['t']
    seen = {monster.unit for frame in take.frames[: first + 1] for monster in monsters_of(frame)}
    opened = openings(take, first)
    known = {prop.unit for prop in things}
    groups: dict[int, list[int]] = {}
    for index in range(first + 1, len(take.frames)):
        frame = take.frames[index]
        if frame['t'] > end:
            break
        fresh = [m.unit for m in monsters_of(frame) if m.unit not in seen and m.hostile and m.at != (0.0, 0.0)]
        seen.update(m.unit for m in monsters_of(frame))
        if fresh:
            groups[index] = fresh
    spawns = []
    for index, units in groups.items():
        at = take.frames[index]['t']
        try:
            there = cut(take, index, defaults=DEFAULT_HERO, reach=reach)
        except ValueError:
            continue
        mobs = [replace(mob, life=mob.full, mode=1) for mob in there.mobs if mob.unit in units and mob.life > 0]
        if not mobs:
            continue
        cause = next(
            ((when, unit) for when, unit in reversed(opened) if 0 <= at - when <= SPAWN_AFTER and unit in known), None
        )
        names = sorted({name_of(mob.txt) for mob in mobs})
        label = f'{len(mobs)} {" and ".join(names)}'
        if cause is None:
            spawns.append(Spawn(mobs, at=round(at - zero, 2), label=label))
        else:
            spawns.append(Spawn(mobs, after=cause[1], delay=round(at - cause[0], 2), label=label))
    return spawns


def track(
    take: Take, scene: Scene, spawns: Sequence[Spawn], first: int, seconds: float, bosses: Sequence[tuple[int, str]]
) -> dict[str, Any]:
    """The recording's side of the window, in the words of an `Outcome` (situation.py)."""
    start = take.frames[first]['t']
    end = start + seconds
    frames = [frame for frame in take.frames[first:] if frame['t'] <= end]
    units = {mob.unit: mob.txt for mob in scene.mobs if mob.owner is None and not mob.ally and mob.life > 0}
    units.update({mob.unit: mob.txt for spawn in spawns for mob in spawn.mobs})
    every = max(round(SAMPLE * 25), 1)
    life, way, kills, places = [], [], [], []
    dead: set[int] = set()
    gaps: dict[str, list[float]] = {name: [] for _, name in bosses}
    boss_dead: dict[str, float | None] = {name: None for _, name in bosses}
    for index, frame in enumerate(frames):
        row = player_of(frame)
        if row is None:
            continue
        at = round(frame['t'] - start, 2)
        places.append(row.at)
        if index % every == 0:
            life.append([at, row.life])
            way.append([at, round(row.x, 1), round(row.y, 1)])
        rows = {monster.unit: monster for monster in monsters_of(frame)}
        for unit, txt in units.items():
            if unit in rows and not rows[unit].alive and unit not in dead:
                dead.add(unit)
                kills.append([at, unit, name_of(txt)])
        for unit, name in bosses:
            if unit in rows and rows[unit].alive:
                gaps[name].append(math.dist(row.at, rows[unit].at))
            elif unit in rows and boss_dead[name] is None:
                boss_dead[name] = at
    events = [event for event in take.events if start < event['t'] <= end]
    hurts = [event for event in events if event.get('event') == 'hurt']
    lives = [point[1] for point in life if point[1]]
    return {
        'life': life,
        'low': min(lives, default=0),
        'taken': float(sum(event.get('lost', 0) for event in hurts)),
        'hurts': [[round(event['t'] - start, 2), event.get('lost', 0)] for event in hurts],
        'kills': kills,
        'strikes': [round(at - start, 2) for at in births(frames, MISSILE)],
        'track': way,
        'moved': round(sum(math.dist(a, b) for a, b in pairwise(places)), 1),
        'said': [[round(e['t'] - start, 2), e['text']] for e in events if e.get('event') == 'said'],
        'gaps': {
            name: [round(seen[0], 1), round(min(seen), 1), round(seen[-1], 1)] if seen else None
            for name, seen in gaps.items()
        },
        'boss_dead': boss_dead,
        'opened': [[round(when - start, 2), unit] for when, unit in openings(take, first) if when <= end],
    }


def from_take(
    directory: Path,
    start: float | str,
    seconds: float,
    *,
    name: str,
    about: str = '',
    reach: float = 60.0,
    bosses: Mapping[int, str] | None = None,
    by_hand: Mapping[str, Any] | None = None,
) -> Situation:
    """Cut the window of `seconds` from `start` (seconds into the take, or a clock time). `bosses`: txt of a
    super unique -> the route's name of it. `by_hand` (each key optional, each recorded in `assumed`):
    'hero' (Hero fields by name), 'presses' ((seconds, routine)), 'opened' (mark labels used before),
    'units' (mark label -> the object's unit id), 'attack' (attack mode on at the start), 'as_it_was',
    'curses', and 'why' (one line saying where they were read)."""
    take = Take.load(Path(directory))
    given = dict(by_hand or {})
    why = given.pop('why', 'entered by hand')
    assumed: dict[str, str] = {}
    zero = take.frames[0]['t']
    at = second_of(take, start)
    first = next(index for index, row in enumerate(take.frames) if row['t'] - zero >= at)
    begin = take.frames[first]['t']
    scene = cut(take, first, defaults=DEFAULT_HERO, name=name, reach=reach)
    modern = take.schema >= 4
    hero = scene.hero
    kept = set(scene.assumed)

    staff, buffs, belt = last(take, 'w', first), last(take, 'f', first), last(take, 'b', first)
    if modern and staff is not None:
        hero = replace(
            hero, hand=1 if staff[2] else 0, sets=(hero.sets[0], replace(hero.sets[1], teleport_charges=staff[0]))
        )
        kept -= {'hand'}
    if modern and buffs is not None and None not in buffs:
        hero = replace(hero, ward=bool(buffs[0]), hex_purge=bool(buffs[1]), consume=bool(buffs[2]))
        kept -= {'ward', 'hex_purge', 'consume'}
    if modern and belt is not None:
        hero = replace(hero, belt=tuple(belt))
        kept -= {'belt'}
    if 'hero' in given:
        fields = dict(given.pop('hero'))
        hero = replace(hero, **fields)
        kept -= set(fields)
        assumed.update({f'hero.{field}': why for field in fields})
    scene.hero = hero
    ground = last(take, 'g', first)
    if modern and ground is not None:
        for unit, x, y, kind, label, *_ in ground:
            if kind == GOLD:
                scene.drops.append(
                    Drop(unit, 'gld', (x, y), gold=int(label.split()[0]) if label.split()[0].isdigit() else 1)
                )
            else:
                scene.drops.append(
                    Drop(unit, POTION_CODE.get(kind, label) if kind in (HEALING, REJUVENATION) else label, (x, y))
                )
        kept -= {'drops'}
    assumed.update({f'scene.{field}': "not in the take: cut.py's default" for field in sorted(kept)})

    level = level_of(take) or {}
    marks = handler_marks(hero.area, level.get('rooms', ()), hero.at)
    state = next((e for e in reversed(take.events) if e.get('event') == 'state' and e['t'] <= begin), None)
    route = (state or {}).get('route') or {}
    if state is not None:
        opened = tuple(label for area, label, _ in route.get('used', ()) if area == hero.area)
        attack = bool(state.get('attack_mode'))
    else:
        opened, attack = tuple(given.pop('opened', ())), bool(given.pop('attack', False))
        assumed['route.opened'] = assumed['attack'] = why
    objects = objects_at(take, first) if modern else {}
    spots = {(mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS): mark for mark in marks if mark.use}
    things = [Prop(unit, row[1], (row[3], row[4]), row[2]) for unit, row in objects.items()]
    if not modern:
        ids = dict(given.pop('units', {}))
        things = [
            Prop(ids.get(mark.label, MADE_UP + index), mark.use, spot, 2 if mark.label in opened else 0)
            for index, (spot, mark) in enumerate(spots.items())
        ]
        assumed['scene.things'] = f'no objects in a take of schema {take.schema}: a Prop on each mark with a use; {why}'
    scene.things = things

    found = dict(bosses or {})
    rows = {unit['unit']: unit for unit in take.units}
    named = tuple(
        (unit, found[row['txt']]) for unit, row in rows.items() if row['txt'] in found and row['flags'] & SUPER_UNIQUE
    )
    if found:
        assumed['route.bosses'] = 'which super unique is which boss of the route: given by txt'

    spawns = appearances(take, scene, first, begin + seconds, reach, things)
    present = {mob.unit for mob in scene.mobs} | {mob.unit for spawn in spawns for mob in spawn.mobs}
    named = tuple(boss for boss in named if boss[0] in present)
    requests = [
        e for e in take.events if e.get('event') == 'request' and begin <= e['t'] - e.get('age', 0.0) < begin + seconds
    ]
    if requests or modern:
        presses = tuple((round(e['t'] - e.get('age', 0.0) - begin, 2), e['routine']) for e in requests)
    else:
        presses = tuple((float(when), routine) for when, routine in given.pop('presses', ()))
        assumed['presses'] = why
    as_it_was = bool(given.pop('as_it_was', False))
    if as_it_was:
        assumed['route.as_it_was'] = 'played with the rule "the fight first", withdrawn 2026-10-13 (kp4.py)'
    curses = tuple(given.pop('curses', ()))
    if given:
        raise ValueError(f'by_hand has nothing called {sorted(given)}')
    # Attack mode on at the start is the toggle at 0.0, unless the window's first request is that toggle.
    starts_it = attack and not (presses and presses[0] == (0.0, ATTACK))
    return Situation(
        name=name,
        scene=scene,
        seconds=seconds,
        about=about,
        attack=starts_it,
        presses=presses,
        marks=tuple(Mark(mark.label, mark.kind, tuple(mark.spot), mark.use) for mark in marks),
        opened=opened,
        bosses=named,
        spawns=spawns,
        curses=curses,
        as_it_was=as_it_was,
        assumed=assumed,
        source={
            'take': take.directory.name,
            'schema': take.schema,
            'start': round(at, 2),
            'seconds': seconds,
            'frame': first,
        },
        recorded=track(take, scene, spawns, first, seconds, named),
    )
