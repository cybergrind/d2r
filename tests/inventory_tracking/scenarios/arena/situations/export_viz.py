"""Situations as files for the Godot viewer (combat_viewer/README.md, "The exported file" and "Situations"):
one file a situation, one run a variant, so Tab in the viewer flips between variants on one timeline.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.export_viz            # all
    ... export_viz --situation four-packs [--seed 3]      # one, in a few seconds; prints the time it took
    ... export_viz --list                                 # the catalog as JSON, and index.json refreshed
    ... export_viz --tasks inventory_tracking/runs/combat/<take> [--out .../viz]   # a take's task sidecar

The viewer runs these itself: `--list` when its Situations tab opens, the export of one situation when it is
opened without a fresh file or E is pressed on it (the call the take list makes for a take:
`<module> <source>/<name> --out <directory> [--policies ...]`), `--tasks` after a take's own export.

**The file** is the take exporter's schema 1 (inventory_tracking/builds/warlock/echoing_strike/viz.py, whose
helpers write it here too), with the stance files' per-run `player` and these additions, each optional to
the viewer:

- a run's `tracks`: {unit: track}: where each monster stood in that run (the arena's monsters move as the
  character does, so each variant has its own); the top-level `monsters` hold the first variant's;
- a run's `objects`: [{x, y, kind ('drop', 'seal', 'open', 'mark'), label, from, until}] and `shots`:
  [[t0, t1, x0, y0, x1, y1, takes life]]: a shooter's missile from where it was let go to where it lands;
- a run's `summary` (what the variant came to: `died` {at, cause} or null, `cleared_at`, `alive`, `hostiles`,
  `lost`, `low`, `potions`, `kills`, `strikes`, `moved`, `goals`: a line a boss of the route and the stage);
- a run's `debug`: `lines` [[tick, text]] (what the macro said), `presses` [[tick, routine, what became of
  it]], `tasks` [[tick, {attack, routine, working, what, sweep}]] (macro_state.py `snapshot` at each change;
  null: not recorded), `life` (a step series) and `max_life`, `potions` [[tick, who, kind]], `hurts`
  [[tick, points, type, kind of blow]], `death` {tick, cause} or null.

The first run is named `recorded` because the viewer's left view is its first run: it is the first variant
(for a recorded situation the arena's replay of the recorded presses, not the recording itself: the fixture
holds the recording's character and numbers, not its monsters' paths). Every variant, the first among them,
is also a run of its own under Tab.

**Fresh or stale.** A file carries `stamp`: the newest change among the fixtures, this package, the arena and
the production packages a play runs (STAMPED). `--list` writes a situation whose file is older than that
into the index without its file ("stale: ..."), which the viewer exports again when it is opened.

**A take's tasks** (`--tasks`): `<out>/<take>.tasks.json` with the same `debug` built from a schema 4 take's
own events (`state`, `request`, `press`, `said`, `hurt`); an older take gets `tasks: null`. The viewer reads
it beside the take's file. Ticks are the take's game ticks (combat/timeline.py `ticks`).
"""

import argparse
import json
import sys
import time
from bisect import bisect_right
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from inventory_tracking.builds.warlock.echoing_strike.hits import CONTACT_RADIUS
from inventory_tracking.builds.warlock.echoing_strike.mechanics import LIFE
from inventory_tracking.builds.warlock.echoing_strike.sim.input import BIRTH_LAG
from inventory_tracking.builds.warlock.echoing_strike.viz import (
    INDEX,
    RECORDED,
    SCALE,
    SCHEMA,
    Frame,
    dumps,
    entry,
    monster_name,
    permille,
    steps,
    track,
    walls,
)  # fmt: skip
from inventory_tracking.combat import macro_state
from inventory_tracking.combat.takes import Take
from inventory_tracking.combat.timeline import GAME_RATE, ticks as game_ticks
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.route import FIGHT_NEAR
from inventory_tracking.macros.runner import ATTACK, HUNT_ELITES, PICKUP, TELEPORT
from inventory_tracking.native.layout import DEAD_MODES, TILE_UNITS
from tests.inventory_tracking.scenarios.arena.game import POTIONS
from tests.inventory_tracking.scenarios.arena.kp4 import RoutePlay
from tests.inventory_tracking.scenarios.arena.situations.bestiary import name_of
from tests.inventory_tracking.scenarios.arena.situations.catalog import SEED, Entry, catalog
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage
from tests.inventory_tracking.scenarios.stance.export_viz import MARGIN, grow, pack


Point = tuple[float, float]
ROOT = Path(__file__).parents[5]
OUT = ROOT / 'inventory_tracking' / 'runs' / 'combat' / 'viz-situations'
TAKES_OUT = ROOT / 'inventory_tracking' / 'runs' / 'combat' / 'viz'
SIDECAR = '.tasks.json'
LINGER = 25  # ticks kept after a play's end
ELITE_FLAGS = 0x02 | 0x04 | 0x08  # super unique, champion, unique (combat/sim/monsters.py)
# What a play runs: a change in any of these makes an exported file stale (the module text).
STAMPED = (
    'tests/inventory_tracking/scenarios/arena',
    'tests/inventory_tracking/macros',
    'inventory_tracking/macros',
    'inventory_tracking/combat',
    'inventory_tracking/builds',
    'inventory_tracking/routes',
    'inventory_tracking/levels',
    'inventory_tracking/automation',
)
KEY_NAMES = {TELEPORT: 'KP_4 teleport', HUNT_ELITES: 'KP_2 seek', ATTACK: 'KP_3 attack mode', PICKUP: 'pickup'}


def stamp() -> float:
    """The newest change among what a play runs and the fixtures."""
    newest = 0.0
    for part in STAMPED:
        for path in (ROOT / part).rglob('*.py'):
            newest = max(newest, path.stat().st_mtime)
    for path in FIXTURES.glob('*.json'):
        newest = max(newest, path.stat().st_mtime)
    return round(newest, 3)


# -- the macro's task at a moment -----------------------------------------------------------------------


def task(snap: dict[str, Any], area: int, saying: str = '') -> dict[str, Any]:
    """A row of macro_state.py `snapshot` (or a take's `state` event) as the viewer's task readout."""
    routine = snap.get('routine') if snap.get('working') else None
    route = snap.get('route') or {}
    stage = (route.get('stages') or {}).get(str(area))
    card = snap.get('card')
    staged = ''
    if stage:
        name, kind, mark, boss = stage[0], stage[1], stage[2], stage[3]
        staged = f'{name}: {kind} {boss or mark}'.strip()
    if routine is None:
        what = 'idle'
    elif routine == TELEPORT:
        what = f'teleport step toward {card[1] if card else "nothing marked"}' + (f' ({staged})' if staged else '')
    elif routine == HUNT_ELITES:
        what = 'seek: ' + (saying or 'an elite, else exploring')
    elif routine == ATTACK:
        what = 'attack mode' + (f' ({staged})' if staged else '')
    elif routine == PICKUP:
        what = 'pickup' + (f': {saying}' if saying else '')
    else:
        what = str(routine)
    return {
        'attack': bool(snap.get('attack_mode')),
        'routine': routine,
        'working': bool(snap.get('working')),
        'what': what,
        'sweep': snap.get('sweep'),
    }


def after(text: str) -> str:
    """What a line of the macro says it is after, for the task readout ('' when it names nothing)."""
    text = text.removeprefix('Macro: ')
    for start in ('Picking up ', 'Teleport toward ', 'Blade Warp toward ', 'Walking toward '):
        if text.startswith(start):
            return text[len(start) :].split(':')[0].split(',')[0]
    return ''


# -- one play, every tick -------------------------------------------------------------------------------


class Film:
    """A play sampled at every tick (situation.py `play(each_tick=...)`)."""

    def __init__(self, area: int, life: float = 0.0) -> None:
        self.area = area
        self.hero: dict[int, Point] = {}
        self.modes: list[tuple[int, int]] = []
        self.life: list[tuple[int, int]] = [(0, round(life))]  # the scene's life, before the first tick
        self.paths: dict[int, dict[int, Point]] = {}
        self.mob_life: dict[int, list[tuple[int, int]]] = {}
        self.first_life: dict[int, int] = {}
        self.deaths: dict[int, int] = {}
        self.taken: list[tuple[int, int]] = []
        self.tasks: list[tuple[int, dict[str, Any]]] = []
        self.drops: dict[int, tuple[Point, str, int | None]] = {}  # unit -> place, label, the tick it was gone
        self.opened: dict[int, int] = {}
        self.before: dict[int, float] = {}
        self.dealt = 0.0
        self.end = 0

    def __call__(self, arena: Stage, play: RoutePlay) -> None:
        tick = self.end = arena.time.ticks
        stand = arena.world.player
        assert stand is not None
        self.hero[tick] = arena.here
        self.modes.append((tick, stand.mode))
        self.life.append((tick, round(arena.life)))
        hostile = set(arena.mobs.hostile)
        for unit, mob in arena.mobs.mobs.items():
            if unit not in hostile:
                continue
            alive = mob.life > 0 and mob.mode not in DEAD_MODES
            if alive or unit not in self.deaths:
                self.paths.setdefault(unit, {})[tick] = mob.at
            share = permille(mob.life, mob.full)
            self.first_life.setdefault(unit, share)
            self.mob_life.setdefault(unit, []).append((tick, share))
            self.dealt += max(self.before.get(unit, mob.life) - max(mob.life, 0.0), 0.0)
            self.before[unit] = max(mob.life, 0.0)
            if not alive:
                self.deaths.setdefault(unit, tick)
        self.taken.append((tick, round(self.dealt)))
        lying = {drop.unit_id: drop for drop in arena.loot.drops}
        for unit, drop in lying.items():
            self.drops.setdefault(unit, ((drop.x, drop.y), drop.label, None))
        for unit, (at, label, gone) in self.drops.items():
            if gone is None and unit not in lying:
                self.drops[unit] = (at, label, tick)
        for thing in arena.things:
            if thing.mode and thing.unit_id not in self.opened:
                self.opened[thing.unit_id] = tick
        saying = next((after(text) for _, text in reversed(arena.told[-6:]) if after(text)), '')
        row = task(macro_state.snapshot(play.runner), self.area, saying)
        if not self.tasks:
            self.tasks.append((0, row))  # the first look is the state in force from the start
        elif self.tasks[-1][1] != row:
            self.tasks.append((tick, row))


def tick_of(seconds: float) -> int:
    return round(seconds * GAME_RATE)


def debug_of(outcome: Outcome, film: Film) -> dict[str, Any]:
    presses = [[tick_of(at), KEY_NAMES.get(routine, routine), became] for at, routine, became in outcome.pressed_]  # type: ignore[attr-defined]
    death = None
    if outcome.dead_at is not None:
        cause = ', '.join(f'{count} {name} {kind} ({points:.0f})' for name, kind, count, points in outcome.killers)
        death = {'tick': tick_of(outcome.dead_at), 'cause': cause or 'no blow in the last 1.5 s'}
    return {
        'lines': [[tick_of(at), text.removeprefix('Macro: ')] for at, text in outcome.said],
        'presses': sorted(presses),
        'tasks': [[tick, row] for tick, row in film.tasks],
        'life': steps(film.life),
        'max_life': round(outcome.max_life),
        'potions': [[tick_of(at), who, POTIONS.get(kind, {}).get('kind', '?')] for at, kind, who in outcome.potions],
        'hurts': [[tick_of(hurt.at), round(hurt.points), name_of(hurt.txt), hurt.kind] for hurt in outcome.hurts],
        'death': death,
    }


def summary_of(situation: Situation, outcome: Outcome) -> dict[str, Any]:
    """What a variant came to, for the viewer's row of it: the death or the survival, the numbers, and for each
    boss of the route how near the character came and when it died."""
    arena: Stage = outcome.stage_  # type: ignore[attr-defined]
    goals = []
    for unit, name in situation.bosses:
        gaps = arena.gaps.get(unit, [])
        near = next((at for at, gap in gaps if gap <= FIGHT_NEAR), None)
        least = min((gap for _, gap in gaps), default=None)
        dead = outcome.boss_dead.get(name)
        reached = 'never' if near is None else f'at {near:.1f} s'
        closest = '' if least is None else f' (least {least:.0f} off)'
        goals.append(
            f'{name} within {FIGHT_NEAR:g} units: {reached}{closest}; '
            + ('alive at the end' if dead is None else f'dead at {dead:.1f} s')
        )
    if outcome.stage:
        goals.append(f'the route at the end: {outcome.stage}')
    died = None
    if outcome.dead_at is not None:
        cause = ', '.join(f'{count} {name} {kind} ({points:.0f})' for name, kind, count, points in outcome.killers)
        died = {'at': round(outcome.dead_at, 2), 'cause': cause or 'no blow in the last 1.5 s'}
    return {
        'died': died,
        'cleared_at': None if outcome.cleared_at is None else round(outcome.cleared_at, 2),
        'alive': outcome.alive,
        'hostiles': outcome.hostiles,
        'lost': round(outcome.taken),
        'low': round(outcome.low),
        'potions': len(outcome.potions),
        'kills': len(outcome.kills),
        'strikes': len(outcome.strikes),
        'moved': round(outcome.moved),
        'goals': goals,
    }


def run_of(
    name: str, label: str, situation: Situation, outcome: Outcome, film: Film, frame: Frame, end: int
) -> dict[str, Any]:
    arena: Stage = outcome.stage_  # type: ignore[attr-defined]
    casts = []
    for _, origin, focal, flight in arena.struck:
        if flight is None:
            continue
        touched = {unit for unit, _ in flight.first}  # type: ignore[attr-defined]
        casts.append(
            {
                't': flight.birth,
                'o': list(frame(origin)),
                'f': list(frame(focal)),
                'n': len(touched),
                'b': pack(flight.paths, frame),
            }
        )  # type: ignore[attr-defined]
    objects = []
    for at, text, gone in film.drops.values():
        objects.append(
            {
                'x': frame(at)[0],
                'y': frame(at)[1],
                'kind': 'drop',
                'label': text,
                'from': 0,
                'until': end if gone is None else gone,
            }
        )
    labels = {
        (round(mark.spot[0] * TILE_UNITS), round(mark.spot[1] * TILE_UNITS)): mark.label for mark in situation.marks
    }
    for prop in situation.scene.things:
        x, y = frame(prop.at)
        text = labels.get((round(prop.at[0]), round(prop.at[1])))
        if text is None:
            continue  # a chest: not drawn
        opened = 0 if prop.mode else film.opened.get(prop.unit)
        if opened != 0:
            objects.append(
                {'x': x, 'y': y, 'kind': 'seal', 'label': text, 'from': 0, 'until': end if opened is None else opened}
            )
        if opened is not None:
            objects.append({'x': x, 'y': y, 'kind': 'open', 'label': f'{text}: open', 'from': opened, 'until': end})
    used = {(round(prop.at[0]), round(prop.at[1])) for prop in situation.scene.things}
    for spot, text in labels.items():
        if spot not in used:
            objects.append(
                {'x': frame(spot)[0], 'y': frame(spot)[1], 'kind': 'mark', 'label': text, 'from': 0, 'until': end}
            )
    shots = [
        [t0, t1, *frame(start), *frame(to), int(takes and at_hero)]
        for t0, t1, start, to, at_hero, takes in arena.cast.shots
    ]
    seconds = max(outcome.seconds, 1e-9)
    kills = len(film.deaths)
    score = {
        'placement_per_combat_second': round(film.dealt / seconds),
        'placement_points': round(film.dealt),
        'combat_seconds': round(outcome.seconds if outcome.cleared_at is None else outcome.cleared_at, 1),
        'life_taken': round(film.dealt),
        'kills': kills,
        'casts': len(casts),
        'contacts': sum(cast['n'] for cast in casts),
        'blades_walled': 0,
        'gain': None,
    }
    last = film.end
    hero = dict(film.hero)
    for tick in range(last + 1, end + 1):
        hero[tick] = film.hero[last]
    return {
        'name': name,
        'label': label,
        'policy': name != RECORDED,
        'casts': casts,
        'life': {str(unit): steps(rows) for unit, rows in sorted(film.mob_life.items())},
        'deaths': {str(unit): tick for unit, tick in sorted(film.deaths.items())},
        'taken': steps(film.taken),
        'score': score,
        'player': track(hero, frame),
        'moves': [],
        'tracks': {
            str(unit): {**track(path, frame), 'seen': [[min(path), end]]} for unit, path in sorted(film.paths.items())
        },
        'objects': objects,
        'shots': shots,
        'debug': debug_of(outcome, film),
        'summary': summary_of(situation, outcome),
    }


def export(entry_: Entry, seed: int = SEED, progress=lambda done, total, stage: None) -> dict[str, Any]:
    """One situation as the viewer's file: a run per variant, the first also as the viewer's `recorded`."""
    variants = entry_.variants()
    base = variants[0][1]
    scene = base.scene
    frame = Frame([scene.hero.at])
    ground = walls(Ground(Walkable(**grid) for grid in scene.ground), frame)
    played = []
    for index, (label, situation, presses) in enumerate(variants):
        progress(index + 1, len(variants) + 1, label)
        film = Film(situation.scene.hero.area, situation.scene.hero.life)
        outcome = situation.play(presses, seed=seed, keep=True, each_tick=film)
        played.append((label, situation, outcome, film))
    end = max(film.end for *_, film in played) + LINGER
    runs = []
    for index, (label, situation, outcome, film) in enumerate(played):
        told = f'{label} (seed {seed})' + (f': DEAD at {outcome.dead_at:.1f} s' if outcome.dead else '')
        if index == 0:
            runs.append(run_of(RECORDED, told, situation, outcome, film, frame, end))
        runs.append(run_of(f'{index + 1}. {label}'[:60], told, situation, outcome, film, frame, end))
    base_score = runs[0]['score']['placement_per_combat_second']
    for found in runs[1:]:
        score = found['score']
        score['gain'] = round(score['placement_per_combat_second'] / base_score - 1, 3) if base_score else None
    for found in runs:
        for cast in found['casts']:
            for blade in cast['b']:
                grow(frame, blade[0], blade[1])
                grow(frame, blade[2], blade[3])
    progress(len(variants) + 1, len(variants) + 1, 'writing the file')
    first, units = runs[0], {}
    for found in runs:
        for unit in found['tracks']:
            units.setdefault(unit, found)
    mobs = {
        str(mob.unit): mob
        for _, situation, _, _ in played
        for mob in [*situation.scene.mobs, *(m for s in situation.spawns for m in s.mobs)]
    }
    monsters = [
        {
            'unit': int(unit),
            'txt': mobs[unit].txt,
            'name': name_of(mobs[unit].txt),
            'elite': bool(mobs[unit].flags & ELITE_FLAGS),
            'points': round(mobs[unit].full),
            'life0': permille(mobs[unit].life, mobs[unit].full),
            **found['tracks'][unit],
            'recorded': {'death': None, 'life': []},
        }
        for unit, found in units.items()
    ]
    companions = [
        {'unit': mob.unit, 'txt': mob.txt, 'name': monster_name(mob.txt), 'seen': [[0, end]], 'k': [0, *frame(mob.at)]}
        for mob in scene.mobs
        if (mob.owner is not None or mob.ally) and mob.mode not in DEAD_MODES
    ]
    doors = []
    for row in scene.doors:
        door = Door(row[0], row[1], row[2], float(row[3]), float(row[4]))
        x, y = frame((door.x, door.y))
        doors.append({'unit': door.unit_id, 'txt': door.txt_id, 'x': x, 'y': y, 'r': round(door.radius * SCALE),
                      'seen': [[0, end]], 'closed': [[0, end]] if door.closed else []})  # fmt: skip
    debug = first['debug']
    dead = [[debug['death']['tick'], end]] if debug['death'] else []
    low_x, low_y, high_x, high_y = frame.bounds
    hero = scene.hero
    return {
        'schema': SCHEMA,
        'take': entry_.name,
        'recording': (base.source or {}).get('take'),
        'character': hero.name,
        'started_at': None,
        'area': hero.area,
        'area_name': f'{entry_.kind}: {entry_.about}',
        'level_name': display_name(hero.area),
        'kind': entry_.kind,
        'about': entry_.about,
        'variants': [label for label, *_ in variants],
        'seed': seed,
        'stamp': stamp(),
        'rate': GAME_RATE,
        'start': 0,
        'end': end,
        'seconds': round(end / GAME_RATE, 1),
        'late_ticks': 0,
        'scale': SCALE,
        'origin': list(frame.origin),
        'bounds': [low_x - MARGIN, low_y - MARGIN, high_x + MARGIN, high_y + MARGIN],
        'aspect': 1.8054,
        'birth_lag': BIRTH_LAG,
        'blade_life': LIFE,
        'contact_radius': round(CONTACT_RADIUS * SCALE),
        'player': {
            **first['player'],
            'mode': steps(played[0][3].modes),
            'run': [],
            'dead': dead,
            'life': debug['life'],
            'max_life': [0, debug['max_life']],
            'mana': [0, round(hero.mana)],
            'max_mana': [0, round(hero.max_mana)],
        },
        'pointer': {'seen': [], 'k': []},
        'monsters': monsters,
        'companions': companions,
        'doors': doors,
        'walls': ground,
        'recorded': {
            'kills': first['score']['kills'],
            'life_taken': first['score']['life_taken'],
            'taken': first['taken'],
        },
        'gate': {'passes': True, 'fails': [], 'damage_ratio': 1.0},
        'runs': runs,
        'moments': {},
    }


# -- the index ------------------------------------------------------------------------------------------


def row_of(entry_: Entry, exported: dict[str, Any] | None, now: float) -> dict[str, Any]:
    """A situation's line in the index: its exported entry when the file is fresh, else a line without a
    file that says why (the viewer's take list exports such a row when it is opened)."""
    names = [label for label, *_ in entry_.variants()]
    plain = {
        'take': entry_.name,
        'area': 0,
        'area_name': f'{entry_.kind}: {entry_.about} [{len(names)} variants]',
        'started_at': None,
        'seconds': None,
        'kind': entry_.kind,
        'about': entry_.about,
        'variants': names,
    }
    if exported is None or not exported.get('file'):
        return plain
    if exported.get('stamp', 0.0) < now:
        return {**plain, 'why': 'stale: the code or the fixture changed since the export'}
    return {**exported, **{key: plain[key] for key in ('area_name', 'kind', 'about', 'variants')}}


def write_index(out: Path, fresh: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """`index.json` in `out`: every situation of the catalog, exported or not. `fresh`: entries just written."""
    out.mkdir(parents=True, exist_ok=True)
    target = out / INDEX
    known: dict[str, dict[str, Any]] = {}
    if target.exists():
        known = {row['take']: row for row in json.loads(target.read_text()).get('takes', ())}
    known.update(fresh or {})
    now = stamp()
    rows = []
    for name, entry_ in catalog().items():
        found = known.get(name)
        if found is not None and found.get('file') and not (out / found['file']).exists():
            found = None
        rows.append(row_of(entry_, found, now))
    index = {'schema': SCHEMA, 'source': str(FIXTURES.resolve()), 'situations': True, 'takes': rows, 'left_out': {}}
    target.write_text(json.dumps(index, indent=1))
    return rows


def write(entry_: Entry, out: Path, seed: int) -> dict[str, Any]:
    def progress(done: int, total: int, stage: str) -> None:
        print(f'[{done}/{total}] {stage}', flush=True)

    data = export(entry_, seed, progress)
    out.mkdir(parents=True, exist_ok=True)
    text = dumps(data)
    file = f'{entry_.name}.json'
    (out / file).write_text(text)
    return {**entry(data, file, len(text.encode())), 'stamp': data['stamp'], 'seed': seed}


# -- a take's tasks -------------------------------------------------------------------------------------


def take_debug(take: Take) -> dict[str, Any]:
    """The `debug` of a recorded take from its own events (the module text)."""
    remap = game_ticks(take.frames)
    times = [frame['t'] for frame in take.frames]
    numbers = [remap[frame['n']] for frame in take.frames]

    def tick(t: float) -> int:
        return numbers[max(bisect_right(times, t) - 1, 0)]

    area = int(take.manifest.get('area', 0))
    events = take.events
    lines = [[tick(e['t']), e['text']] for e in events if e.get('event') == 'said']
    presses = [
        [tick(e['t']), KEY_NAMES.get(e.get('routine'), str(e.get('routine'))),
         ', '.join(str(e[key]) for key in ('outcome', 'ended') if e.get(key))]
        for e in events if e.get('event') == 'press'
    ]  # fmt: skip
    tasks: list[list[Any]] | None = None
    if take.schema >= 4:
        tasks = []
        saying = ''
        for e in events:
            if e.get('event') == 'said':
                saying = after(e['text']) or saying
            if e.get('event') != 'state':
                continue
            row = task(e, area, saying)
            if not tasks or tasks[-1][1] != row:
                tasks.append([tick(e['t']), row])
    hurts = [[tick(e['t']), round(e.get('lost', 0)), '', 'hurt'] for e in events if e.get('event') == 'hurt']
    return {'lines': lines, 'presses': sorted(presses), 'tasks': tasks, 'hurts': hurts, 'potions': [], 'death': None}


def write_tasks(directory: Path, out: Path) -> Path:
    take = Take.load(directory)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f'{directory.name}{SIDECAR}'
    target.write_text(
        dumps({'schema': SCHEMA, 'take': directory.name, 'take_schema': take.schema, 'debug': take_debug(take)})
    )
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n\n')[0])
    parser.add_argument('targets', nargs='*', help='situations by name (or <folder>/<name>, as the viewer asks)')
    parser.add_argument('--situation', action='append', default=[], help='a situation to export (default: all)')
    parser.add_argument('--out', type=Path, default=None)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--list', action='store_true', help='print the catalog as JSON and refresh index.json')
    parser.add_argument(
        '--tasks', action='append', default=[], type=Path, help="a take directory: write its tasks' sidecar"
    )
    parser.add_argument('--policies', default='', help='ignored (the viewer passes it for a take)')
    args = parser.parse_args(argv)
    began = time.perf_counter()
    if args.tasks:
        for directory in args.tasks:
            print(f'[1/1] the tasks of {directory.name}', flush=True)
            print(write_tasks(directory, args.out or TAKES_OUT))
        return 0
    out = args.out or OUT
    known = catalog()
    if args.list:
        rows = write_index(out)
        print(
            json.dumps(
                [{key: row.get(key) for key in ('take', 'kind', 'about', 'variants', 'file', 'why')} for row in rows],
                indent=1,
            )
        )
        return 0
    names = [Path(name).name.removesuffix('.json') for name in (*args.targets, *args.situation)] or list(known)
    for name in names:
        if name not in known:
            print(f'no situation called {name!r}: {", ".join(known)}', file=sys.stderr)
            return 2
    fresh = {}
    for name in names:
        started = time.perf_counter()
        fresh[name] = write(known[name], out, args.seed)
        size, variants = fresh[name]['bytes'] / 1e3, len(fresh[name]['runs']) - 1
        print(f'{name}: {size:.0f} kB, {variants} variants, {time.perf_counter() - started:.1f} s', flush=True)
    write_index(out, fresh)
    print(f'{len(names)} situations in {out / INDEX}, {time.perf_counter() - began:.1f} s')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
