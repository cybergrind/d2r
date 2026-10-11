"""Cut the macro's logged step moments out of the combat takes into scenario fixtures.

    uv run --offline python -m tests.inventory_tracking.scenarios.stance.build_fixtures

Reads the alt-d probe logs from SINCE on, finds the combat take each logged step falls in, and writes one JSON
fixture per moment under fixtures/. Deterministic: the same logs and takes give the same files.
"""

from __future__ import annotations

import bisect
import gzip
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from inventory_tracking.combat.takes import MonsterRow, Take, monsters_of, player_of


REPO = Path(__file__).resolve().parents[4]
ALT_D = REPO / 'inventory_tracking' / 'runs' / 'alt-d'
COMBAT = REPO / 'inventory_tracking' / 'runs' / 'combat'
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
SINCE = '20261010T204511Z'
LOCAL_OFFSET = timedelta(hours=3)  # the log's clock is local, UTC+3
MATCH_RADIUS = 3.0  # units between the logged `from` point and the frame's player
SEARCH_SECONDS = 1.0  # how far either side of the nearest frame a second search looks
HYDRAS = {351, 352, 353}
HOSTILE_RANGE = 40.0
CLEAR_RANGE = 30.0
CLEAR_WINDOW = 30.0
NO_CAST_WINDOW = 10.0
GROUND_RANGE = 60.0
TILE = 5.0  # world units per tile
PLAYER_STEPS = (1.0, 2.0, 3.0, 5.0)
ALIVE_STEPS = (1.0, 2.0, 3.0, 5.0, 8.0)

LOG = re.compile(
    r'(?P<local>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) INFO Macro: step asked '
    r'(?P<fight>in the fight with|with) (?P<in_reach>\d+) of (?P<near>\d+) hostiles (?:near )?in reach, '
    r'from \((?P<fx>-?[\d.]+), (?P<fy>-?[\d.]+)\): (?P<rest>.+)$'
)


@dataclass(frozen=True)
class Moment:
    local: str  # the log's own timestamp, 'YYYY-MM-DD HH:MM:SS,mmm'
    at: datetime  # the same instant in UTC
    in_fight: bool
    in_reach: int
    near: int
    origin: tuple[float, float]
    decision: str


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.dist(a, b)


def read_moments() -> list[Moment]:
    """Every logged step from the alt-d probe logs whose directory stamp is SINCE or later, in log order."""
    moments: list[Moment] = []
    for directory in sorted(ALT_D.iterdir()):
        if not directory.is_dir() or directory.name < SINCE:
            continue
        probe = directory / 'probe.log'
        if not probe.exists():
            continue
        for line in probe.read_text(encoding='utf-8').splitlines():
            found = LOG.search(line)
            if found is None:
                continue
            local = datetime.strptime(found['local'], '%Y-%m-%d %H:%M:%S,%f')
            # the decision's pickup suffix is not part of the logged decision the fixture keeps
            decision = found['rest'].partition('; pickup after:')[0].strip()
            moments.append(
                Moment(
                    local=found['local'],
                    at=(local - LOCAL_OFFSET).replace(tzinfo=UTC),
                    in_fight=found['fight'].startswith('in the fight'),
                    in_reach=int(found['in_reach']),
                    near=int(found['near']),
                    origin=(float(found['fx']), float(found['fy'])),
                    decision=decision,
                )
            )
    return moments


class Loaded:
    """Takes loaded on demand, with the frame times and the start each one's clock is read from."""

    def __init__(self) -> None:
        self.cache: dict[str, Take] = {}

    def take(self, directory: Path) -> Take:
        if directory.name not in self.cache:
            self.cache[directory.name] = Take.load(directory)
        return self.cache[directory.name]


def started_at(take: Take) -> datetime:
    return datetime.fromisoformat(take.manifest['started_at'])


def contains(take: Take, at: datetime) -> bool:
    """The take's [started_at, finished_at] holds the moment; a take not yet finished ends at its last frame."""
    start = datetime.fromisoformat(take.manifest['started_at'])
    if at < start:
        return False
    if take.manifest.get('finished_at'):
        return at <= datetime.fromisoformat(take.manifest['finished_at'])
    return bool(take.frames) and at <= start + timedelta(seconds=take.frames[-1]['t'] - take.frames[0]['t'])


def frame_index(times: list[float], t: float) -> int:
    """The index of the frame nearest to time t (the earlier one on a tie)."""
    at = bisect.bisect_left(times, t)
    options = [j for j in (at - 1, at) if 0 <= j < len(times)]
    return min(options, key=lambda j: (abs(times[j] - t), j))


def frame_origin(take: Take, index: int) -> tuple[float, float] | None:
    player = player_of(take.frames[index])
    return None if player is None else player.at


def match(take: Take, moment: Moment) -> int | None:
    """The frame of the take at the moment's place: the nearest in time, else the best within a second."""
    times = [f['t'] for f in take.frames]
    target = times[0] + (moment.at - started_at(take)).total_seconds()

    def gap(index: int) -> float:
        origin = frame_origin(take, index)
        return math.inf if origin is None else dist(origin, moment.origin)

    best = frame_index(times, target)
    if gap(best) > MATCH_RADIUS:
        window = range(
            bisect.bisect_left(times, target - SEARCH_SECONDS), bisect.bisect_right(times, target + SEARCH_SECONDS)
        )
        if window:
            best = min(window, key=lambda j: (gap(j), j))
    return best if gap(best) <= MATCH_RADIUS else None


def find_take(moment: Moment, loaded: Loaded) -> tuple[Take, int] | str:
    """The first take (by directory name) containing the moment and matching its place, or the reason none does."""
    closest = math.inf
    for directory in sorted(COMBAT.iterdir()):
        if not (directory / 'manifest.json').exists():
            continue
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        start = datetime.fromisoformat(manifest['started_at'])
        if moment.at < start or (
            manifest.get('finished_at') and moment.at > datetime.fromisoformat(manifest['finished_at'])
        ):
            continue
        take = loaded.take(directory)
        if not contains(take, moment.at) or not take.frames:
            continue
        index = match(take, moment)
        if index is not None:
            return take, index
        times = [f['t'] for f in take.frames]
        target = times[0] + (moment.at - started_at(take)).total_seconds()
        origin = frame_origin(take, frame_index(times, target))
        if origin is not None:
            closest = min(closest, dist(origin, moment.origin))
    return f'no take matches; closest frame {closest:.1f} units off' if closest < math.inf else 'no take contains it'


def alive_units(frame: dict[str, Any]) -> set[int]:
    return {m.unit for m in monsters_of(frame) if m.alive}


def level_grids(take: Take) -> list[dict[str, Any]]:
    plain, packed = take.directory / 'level.json', take.directory / 'level.json.gz'
    if plain.exists():
        return json.loads(plain.read_text(encoding='utf-8'))['ground']
    with gzip.open(packed, 'rt', encoding='utf-8') as handle:
        return json.load(handle)['ground']


def ground_near(grids: list[dict[str, Any]], origin: tuple[float, float]) -> list[dict[str, Any]]:
    """The grids whose tile rectangle (1 tile = TILE units) comes within GROUND_RANGE of the player; no masks."""
    kept = []
    for grid in grids:
        x0, y0 = grid['x'] * TILE, grid['y'] * TILE
        x1, y1 = x0 + grid['width'] * TILE, y0 + grid['height'] * TILE
        dx = max(x0 - origin[0], 0.0, origin[0] - x1)
        dy = max(y0 - origin[1], 0.0, origin[1] - y1)
        if math.hypot(dx, dy) <= GROUND_RANGE:
            kept.append({k: v for k, v in grid.items() if k != 'masks'})
    return kept


def monster_json(m: MonsterRow) -> dict[str, Any]:
    return {'unit': m.unit, 'txt': m.txt, 'at': [m.x, m.y], 'life': round(m.life_share, 4), 'elite': m.elite}


def build(take: Take, index: int, moment: Moment) -> dict[str, Any]:
    frames = take.frames
    frame = frames[index]
    player = player_of(frame)
    assert player is not None
    origin = player.at
    times = [f['t'] for f in frames]
    start_t = frame['t']
    last_t = frames[-1]['t']

    monsters = monsters_of(frame)
    hostiles = [
        m
        for m in monsters
        if m.hostile and m.at != (0.0, 0.0) and m.txt not in HYDRAS and dist(m.at, origin) <= HOSTILE_RANGE
    ]
    companions = [m for m in monsters if m.companion and dist(m.at, origin) <= HOSTILE_RANGE]
    ids = {m.unit for m in hostiles}
    cleared_ids = {m.unit for m in hostiles if dist(m.at, origin) <= CLEAR_RANGE}

    # cleared: the first frame (within the window) where none of the cleared-set hostiles is alive
    cleared: float | None = None
    j = index
    while j < len(frames) and frames[j]['t'] - start_t <= CLEAR_WINDOW:
        if not cleared_ids & alive_units(frames[j]):
            cleared = frames[j]['t'] - start_t
            break
        j += 1

    end_rel = cleared if cleared is not None else NO_CAST_WINDOW
    casts = sum(1 for e in take.events if e.get('event') == 'cast' and start_t <= e['t'] <= start_t + end_rel)

    player_at: dict[str, list[float]] = {}
    for step in PLAYER_STEPS:
        if start_t + step > last_t:
            continue
        here = player_of(frames[frame_index(times, start_t + step)])
        if here is not None:
            player_at[f'{step:.1f}'] = [here.x, here.y]

    alive_at: dict[str, int] = {}
    for step in ALIVE_STEPS:
        if start_t + step > last_t:
            continue
        alive_at[f'{step:.1f}'] = len(ids & alive_units(frames[frame_index(times, start_t + step)]))

    return {
        'name': f'{take.directory.name}-{moment.local[11:19].replace(":", "")}',
        'log_time': moment.local,
        'take': take.directory.name,
        'area': take.manifest['area'],
        'in_fight': moment.in_fight,
        'logged': {'in_reach': moment.in_reach, 'near': moment.near, 'decision': moment.decision},
        'player': [player.x, player.y],
        'hostiles': [monster_json(m) for m in hostiles],
        'companions': [{'unit': m.unit, 'txt': m.txt, 'at': [m.x, m.y]} for m in companions],
        'doors': frame.get('d', []),
        'ground': ground_near(level_grids(take), origin),
        'after': {
            'player_at': player_at,
            'alive_at': alive_at,
            'cleared_seconds': None if cleared is None else round(cleared, 2),
            'casts': casts,
        },
    }


def short(decision: str) -> str:
    if decision.startswith('no better'):
        return decision
    found = re.match(r'a stand at \(([-\d.]+), ([-\d.]+)\), (\d+) away, its line worth (\d+) against (\d+)', decision)
    if found is None:
        return decision[:60]
    return f'stand {found[3]} away, worth {found[4]} vs {found[5]}'


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for old in FIXTURES.glob('*.json'):
        old.unlink()
    loaded = Loaded()
    moments = read_moments()
    unmatched = 0
    names: set[str] = set()
    for moment in moments:
        found = find_take(moment, loaded)
        if isinstance(found, str):
            unmatched += 1
            print(f'UNMATCHED {moment.local} from ({moment.origin[0]}, {moment.origin[1]}): {found}')
            continue
        take, index = found
        fixture = build(take, index, moment)
        if fixture['name'] in names:
            raise SystemExit(f'duplicate fixture name {fixture["name"]}')
        names.add(fixture['name'])
        (FIXTURES / f'{fixture["name"]}.json').write_text(
            json.dumps(fixture, indent=1, ensure_ascii=False) + '\n', encoding='utf-8'
        )
        within30 = sum(1 for h in fixture['hostiles'] if dist(tuple(h['at']), tuple(fixture['player'])) <= CLEAR_RANGE)
        after = fixture['after']
        print(
            f'{fixture["name"]:<32} fight={fixture["in_fight"]!s:<5} in_reach={moment.in_reach:>2} '
            f'near={moment.near:>2} hostiles30={within30:>2} cleared={after["cleared_seconds"]!s:>5} '
            f'casts={after["casts"]:>2}  {short(moment.decision)}'
        )
    print(f'fixtures {len(names)}, unmatched {unmatched} of {len(moments)} logged moments')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
