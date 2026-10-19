"""The sparks of a Lightning Enchanted monster in the takes: SPARKS.md and sparks.json.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.sparks [--jobs N] [--no-cache]

reads every take of `split.json` (the halves the monster refit was fitted and judged on; a take
recorded since is in neither and is not read) and writes `SPARKS.md` and `sparks.json` beside this
file. Nothing here is fitted: `fit.py` reads `sparks.json`'s train half. `--render` writes SPARKS.md
again from sparks.json (the model's side of its tables is read when it is written); `--deaths <scene>`
is another question, of the arena and not of the takes: what dealt the last blows in the plays of a
fixture scene the character died in (`last_blows`).

Which missile. missiles.txt holds one row a monster's enchantment lets go as charged bolts,
`lightunique` (SPARK, the id the model and mechanics/tables.py MISSILES carry). Its owner is in the
missile's unit record (blows.py OWNER), so a spark is its monster's by that id and not by standing
near it. `buglightning` (225) flies the same way and is a Death Beetle's own, enchanted or not: it is
not counted here.

What a take is tallied into (`tally`, cached per take as scan.py does):

- `monsters`: every hostile that is Lightning Enchanted by its enchantments (hurts.LIGHTNING) or owned
  a spark: its rank, level and Herald tier, the seconds it was seen alive, and its `hits`: the frames
  in which its life was lower than in the frame before. A frame's row holds a monster's life in 128ths
  of its most, so a hit that takes less than that does not show: the hits of a Herald with tens of
  thousands of points are undercounted, a plain monster's hardly;
- `releases`: the sparks of one owner first seen in the same frame (or the next): how many, where the
  owner and the character stood, how long before it the owner was last seen to lose life, and of each
  spark its flight (frames seen, how far out, how near the character, where it ended) and the drop of
  the character's life that followed its end, if any, with what blows.py made of that drop;
- `drops`: every drop of the character's life with a spark near (blows.py `missiles`).

What a take cannot say, and what stands in:

- **why a release came.** The takes hold the monster's life per frame and its mode. A release is laid
  against the owner's hits (`since`: frames from its last seen loss of life) and against the time it
  was being struck (`struck_seconds`: the frames within STRUCK frames after a hit, merged);
- **whether a spark that ended at the character took life.** A spark is taken to have ended on the
  character when it was last seen within rates.END_ON of it before its time was up (`on_hero`); the
  drop is its own when blows.py put it on the spark's owner alone (`sole`), shared when the owner is
  one of several suspects, and whatever the class when any drop followed within AFTER frames (`any`).
  `fell` is the fall of the character's life over those frames whatever its size: a drop under
  hurts.HURT_LEAST is no row of blows.py, and a spark might take less.
"""

import argparse
import hashlib
import inspect
import itertools
import json
import math
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from inventory_tracking.combat.hurts import LIGHTNING, Sightings, enchantments
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim.monsters import SPARK as SPARK_KIND, SPARK_MISSILE
from inventory_tracking.combat.takes import Take
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.game.layout import HERALD_TIER_STAT
from inventory_tracking.native.layout import PLAYER_DEAD_MODES
from inventory_tracking.terror.monsters import LEVEL_STAT
from tests.inventory_tracking.scenarios.arena.evidence import blows, scan
from tests.inventory_tracking.scenarios.arena.evidence.blows import (
    DEATH_MISSILE,
    MISSILE,
    RANKS,
    SEVERAL,
    Moment,
    Roster,
    name_of,
    rank_of,
)
from tests.inventory_tracking.scenarios.arena.evidence.rates import ELITE, END_ON, STEP, quantile


Point = tuple[float, float]
HERE = Path(__file__).parent
SPLIT = HERE / 'split.json'
CACHE = scan.CACHE / 'sparks'
SPARK = SPARK_MISSILE  # missiles.txt `lightunique`, as the bundled tables name the row
assert tables()['missiles'][str(SPARK)]['Missile'] == 'lightunique'
LIGHTNING_RESIST = 2  # the index of the lightning resistance in a row's `resists` (record.RESIST_STATS: stat 41)
FAR = 40.0  # units: a release further from the character than a screen is still tallied; this is the bins' end
SAME = 1  # frames: sparks of one owner first seen this close together are one release
AFTER = 3  # frames after a spark was last seen in which a drop is looked for
EARLY = 5  # frames: a spark's direction is where it is this long after its first sight
AGES = (25, 50, 70)  # frames: how far out a spark is at these ages
# Frames after a seen loss of life a monster counts as being struck: the windows the releases are laid
# against, each a candidate for the model's (`measure` gives the releases a second and the fit of each).
WINDOWS = (5, 10, 15, 25)
STRUCK = 10  # frames: the window a span of hits is closed with (`releasing`)
BANDS = (0.0, 4.0, 8.0, 12.0, 16.0, 20.0, FAR)  # units from the owner to the character at a release
LEVELS = (0, 75, 85, 200)  # monster levels: the edges of the bands a table is split by
SINCE = ((0, 0), (1, 4), (5, 9), (10, 24), (25, 10**9))  # frames from the owner's last seen hit to a release
BEND = 20.0  # degrees between two strides from which a spark has turned
_SEEN: Sightings = {}


def bearing(start: Point, end: Point) -> float:
    """Degrees of the direction from `start` to `end`, 0 to 360."""
    return math.degrees(math.atan2(end[1] - start[1], end[0] - start[0])) % 360


def turned(first: float, second: float) -> float:
    """Degrees between two directions, 0 to 180."""
    return abs((second - first + 180) % 360 - 180)


def tally(take_name: str, moments: Sequence[Moment], rows: Sequence[Mapping[str, Any]], roster: Roster) -> dict:
    """One take's sparks (the module text): `monsters`, `releases`, `drops`, and the take's `seconds`."""
    charged = {unit for unit in roster.units if LIGHTNING in (roster.mods(unit) or ())}
    owners = {f.owner for m in moments for f in m.flying if f.txt == SPARK and f.owner is not None}
    watched = charged | owners
    monsters: dict[int, dict[str, Any]] = {}
    last_life: dict[int, tuple[int, int]] = {}  # unit -> (frame index, life) of its last live sight
    modes: dict[int, dict[int, int]] = defaultdict(dict)  # unit -> frame index -> mode
    places: dict[int, dict[int, Point]] = defaultdict(dict)
    tracks: dict[tuple[int, float], dict[str, Any]] = {}
    seconds = 0.0
    for position, moment in enumerate(moments):
        step = min(moments[position + 1].t - moment.t, STEP) if position + 1 < len(moments) else 0.0
        hero = moment.hero
        if hero is not None:
            seconds += step
        for monster in moment.foes:
            if monster.unit not in watched:
                continue
            found = monsters.get(monster.unit)
            if found is None:
                monsters[monster.unit] = {
                    'unit': monster.unit,
                    'txt': monster.txt,
                    'name': name_of(monster.txt),
                    'rank': rank_of(monster.flags),
                    'mods': roster.mods(monster.unit),
                    'level': roster.stat(monster.unit, LEVEL_STAT),
                    'tier': roster.stat(monster.unit, HERALD_TIER_STAT),
                    'seconds': 0.0,
                    'near': 0.0,
                    'hits': [],
                    'first': moment.index,
                }
                found = monsters[monster.unit]
            found['last'] = moment.index
            found['seconds'] += step
            away = None if hero is None else math.dist(monster.at, hero.at)
            if away is not None and away <= FAR / 2:
                found['near'] += step
            before = last_life.get(monster.unit)
            if before is not None and before[0] == moment.index - 1 and monster.life < before[1]:
                found['hits'].append(
                    [moment.index, before[1] - monster.life, None if away is None else round(away, 1), monster.mode]
                )
            last_life[monster.unit] = (moment.index, monster.life)
            modes[monster.unit][moment.index] = monster.mode
            places[monster.unit][moment.index] = monster.at
        for flight in moment.flying:
            if flight.txt != SPARK:
                continue
            track = tracks.get(flight.key)
            if track is None:
                tracks[flight.key] = {
                    'owner': flight.owner,
                    'kind': flight.kind,
                    'first': moment.index,
                    'start': flight.at,
                    'seen': 0,
                    'path': 0.0,
                    'steps': 0,
                    'closest': None,
                    'at': {},
                    'heading': None,
                    'run': 0,
                    'runs': [],
                    'bends': [],
                }
                track = tracks[flight.key]
            if track.get('last') == moment.index - 1:
                track['path'] += math.dist(track['end'], flight.at)
                track['steps'] += 1
            if track.get('last') == moment.index - 1 and flight.at != track['end']:
                heading = bearing(track['end'], flight.at)
                if track['heading'] is not None and turned(track['heading'], heading) >= BEND:
                    track['runs'].append(track['run'])
                    track['bends'].append(round(turned(track['heading'], heading)))
                    track['run'] = 0
                track['heading'] = heading
                track['run'] += 1
            track['last'], track['end'] = moment.index, flight.at
            track['seen'] += 1
            age = moment.index - track['first']
            if age == EARLY or age in AGES:
                track['at'][age] = flight.at
            if hero is not None:
                away = math.dist(flight.at, hero.at)
                if track['closest'] is None or away < track['closest']:
                    track['closest'] = away
                track['end_hero'] = away
                track['end_friend'] = min((math.dist(flight.at, f.at) for f in moment.friends), default=FAR)
                others = (math.dist(flight.at, f.at) for f in moment.foes if f.unit != flight.owner)
                track['end_foe'] = min(others, default=FAR)
            else:
                track['end_hero'] = track['end_friend'] = track['end_foe'] = None

    final = len(moments) - 1

    def fell(last: int) -> int | None:
        """The points the character's life fell by in the AFTER frames after frame `last`, whatever the
        size (a drop under hurts.HURT_LEAST is no row of blows.py); None where the vitals were not read."""
        span = [m.hero.life for m in moments[last : last + AFTER + 1] if m.read and m.hero and m.hero.life is not None]
        return span[0] - min(span) if len(span) > 1 else None

    def drop_after(track: Mapping[str, Any]) -> list[Any] | None:
        """The first drop within AFTER frames of the spark's last sight: [frames after, points, class,
        suspects, sole on the owner, the owner among the suspects, the lightning resistance read]."""
        for row in rows:
            if row['frame'] < track['last']:
                continue
            if row['frame'] > track['last'] + AFTER:
                break
            owner = track['owner']
            named = [s for s in row['by'] if s['unit'] == owner and s['missile'] == SPARK]
            sole = bool(named) and len(row['by']) == 1 and row['class'] != SEVERAL
            resists = row['resists']
            return [
                row['frame'] - track['last'],
                row['lost'],
                row['class'],
                len(row['by']),
                int(sole),
                int(bool(named)),
                None if not resists else resists[LIGHTNING_RESIST],
            ]
        return None

    groups: dict[tuple[int | None, int], list[dict[str, Any]]] = {}
    for track in sorted(tracks.values(), key=lambda track: track['first']):
        owner = track['owner']
        key = next(
            (key for key in ((owner, track['first'] - back) for back in range(SAME + 1)) if key in groups),
            (owner, track['first']),
        )
        groups.setdefault(key, []).append(track)
    releases = []
    for (owner, first), sparks in groups.items():
        monster = monsters.get(owner) if owner is not None else None
        hero = moments[first].hero
        origin = places[owner].get(first) or places[owner].get(first - 1) if owner in places else None
        hits = [hit[0] for hit in monster['hits']] if monster else []
        since = min((first - hit for hit in hits if hit <= first), default=None)
        flown = []
        for track in sparks:
            start = origin or track['start']
            early = track['at'].get(EARLY)
            flown.append(
                {
                    'seen': track['seen'],
                    'frames': track['last'] - track['first'] + 1,
                    'born': round(math.dist(start, track['start']), 2),
                    'course': None if early is None else round(bearing(start, early), 1),
                    'out': round(math.dist(start, track['end']), 2),
                    'outs': {str(age): round(math.dist(start, at), 2) for age, at in track['at'].items()},
                    'stride': round(track['path'] / track['steps'], 4) if track['steps'] else None,
                    'closest': None if track['closest'] is None else round(track['closest'], 2),
                    'end_hero': None if track['end_hero'] is None else round(track['end_hero'], 2),
                    'end_friend': None if track['end_friend'] is None else round(track['end_friend'], 2),
                    'end_foe': None if track['end_foe'] is None else round(track['end_foe'], 2),
                    'last': track['last'],
                    'cut': int(track['last'] >= final),  # the take ended with the spark in flight
                    'runs': track['runs'][1:],  # frames between two turns (the first run began before the first sight)
                    'bends': track['bends'],
                    'fell': fell(track['last']),
                    'drop': drop_after(track),
                }
            )
        releases.append(
            {
                'take': take_name,
                'frame': first,
                'owner': owner,
                'kind': sparks[0]['kind'],
                'known': int(monster is not None),
                'rank': monster and monster['rank'],
                'txt': monster and monster['txt'],
                'level': monster and monster['level'],
                'tier': monster and monster['tier'],
                'charged': None if monster is None or monster['mods'] is None else int(LIGHTNING in monster['mods']),
                'alive': int(owner in modes and first in modes[owner]),
                'mode': modes[owner].get(first) if owner in modes else None,
                'mode_before': modes[owner].get(first - 1) if owner in modes else None,
                'away': None if hero is None or origin is None else round(math.dist(origin, hero.at), 2),
                'to_hero': None if hero is None or origin is None else round(bearing(origin, hero.at), 1),
                'hero_dead': None if hero is None else int(hero.mode in PLAYER_DEAD_MODES or not moments[first].read),
                'since': since,
                'sparks': flown,
            }
        )
    near = []
    for row in rows:
        mine = [missile for missile in row['missiles'] if missile[0] == SPARK]
        if not mine:
            continue
        units = {missile[2] for missile in mine}
        suspects = [s for s in row['by'] if s['unit'] in units and s['via'] in (MISSILE, DEATH_MISSILE)]
        near.append(
            {
                'take': take_name,
                'frame': row['frame'],
                'lost': row['lost'],
                'class': row['class'],
                'suspects': len(row['by']),
                'sparks': len(mine),
                'others': len(row['missiles']) - len(mine),
                'sole': int(len(row['by']) == 1 and len(suspects) == 1 and row['class'] != SEVERAL),
                'rank': suspects[0]['rank'] if suspects else None,
                'level': suspects[0]['level'] if suspects else None,
                'tier': suspects[0]['tier'] if suspects else None,
                'resist': None if not row['resists'] else row['resists'][LIGHTNING_RESIST],
                'max_life': row['max_life'],
            }
        )
    for found in monsters.values():
        found['seconds'], found['near'] = round(found['seconds'], 2), round(found['near'], 2)
        found['take'] = take_name
    return {
        'take': take_name,
        'seconds': round(seconds, 2),
        'monsters': list(monsters.values()),
        'releases': releases,
        'drops': near,
    }


# ---------------------------------------------------------------------------------------------------
# All takes, once each.


def stamp() -> str:
    """A hash of the code that makes a take's cache file: blows.py and this module's `tally`."""
    digest = hashlib.sha1((HERE / 'blows.py').read_bytes())
    digest.update(inspect.getsource(tally).encode())
    digest.update(repr((SPARK, SAME, AFTER, EARLY, AGES, FAR, BEND)).encode())
    return digest.hexdigest()[:12]


def read(directory: Path, seen: Sightings) -> dict[str, Any]:
    """One take's sparks; `skipped` says why there are none."""
    name = directory.name
    try:
        take = Take.load(directory)
    except (OSError, ValueError) as exc:
        return {'take': name, 'skipped': f'not read ({exc})'}
    if take.schema < 2 or not take.frames:
        return {'take': name, 'skipped': 'schema 1 or no frames'}
    mods = enchantments(seen, take)
    moments = list(blows.walk(take))
    return tally(name, moments, blows.blows(take, mods, moments), Roster(take, mods))


def _work(job: tuple[Path, Path | None, str]) -> dict[str, Any]:
    directory, cache, mark = job
    if cache is None:
        return read(directory, _SEEN)
    path = cache / f'{directory.name}.{mark}.json'
    if path.exists():
        return json.loads(path.read_text())
    found = read(directory, _SEEN)
    for old in cache.glob(f'{directory.name}.*.json'):
        old.unlink()
    path.write_text(json.dumps(found, separators=(',', ':')))
    return found


def gather(
    directories: Sequence[Path],
    *,
    cache: Path | None = CACHE,
    probes: Iterable[Path] | None = None,
    jobs: int | None = None,
    progress: bool = True,
) -> list[dict[str, Any]]:
    """`read` of every take, from the cache where it holds one, in `jobs` processes (as scan.scan)."""
    global _SEEN  # the workers inherit it by fork
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
    logs = sorted(scan.PROBES.glob('*/terror-probe.jsonl')) if probes is None else sorted(probes)
    began = time.monotonic()
    _SEEN = scan.probe_sightings(logs, None if cache is None else cache.parent)
    work = [(directory, cache, stamp()) for directory in directories]
    jobs = jobs or min(os.cpu_count() or 1, 16)
    if jobs <= 1 or len(work) <= 1:
        return [_work(job) for job in work]
    found = []
    with get_context('fork').Pool(jobs) as pool:
        for done, result in enumerate(pool.imap(_work, work, chunksize=2), 1):
            found.append(result)
            if progress and (done % 100 == 0 or done == len(work)):
                print(f'{done}/{len(work)} takes, {time.monotonic() - began:.0f} s', file=sys.stderr)
    return found


# ---------------------------------------------------------------------------------------------------
# What a set of takes measures.


def struck_frames(hits: Sequence[int], window: int) -> int:
    """Frames a monster was being struck in, by the frames of its seen hits: `window` after each, merged
    (the same sum as `window` for the first hit and the frames since the hit before, `window` at most,
    for each later one: how sim/monsters.py `Pack.struck` counts them)."""
    return sum(min(later - sooner, window) for sooner, later in itertools.pairwise(hits)) + (window if hits else 0)


def deviance(pairs: Sequence[tuple[float, int]], rate: float) -> float:
    """How badly `rate` times a monster's exposure gives its count of releases, summed over the monsters
    (`pairs`: exposure, releases): the Poisson deviance. Lower is the better relation."""
    total = 0.0
    for exposure, count in pairs:
        mean = rate * exposure
        if mean > 0:
            total += 2 * ((count * math.log(count / mean) if count else 0.0) - (count - mean))
    return round(total, 1)


def spread(values: Sequence[float], digits: int = 2) -> dict[str, Any]:
    def at(share: float) -> float | None:
        found = quantile(values, share)
        return None if found is None else round(found, digits)

    return {'n': len(values), 'p10': at(0.1), 'p50': at(0.5), 'p90': at(0.9), 'least': at(0.0), 'most': at(1.0)}


def upper(n: int, sure: float = 0.95) -> float | None:
    """The chance under which the truth lies with `sure` confidence when none of `n` showed it."""
    return round(1 - (1 - sure) ** (1 / n), 3) if n else None


def level_band(level: int | None) -> str:
    for low, high in itertools.pairwise(LEVELS):
        if level is not None and low <= level < high:
            return f'under {high}' if not low else f'{low}-{high - 1}' if high < LEVELS[-1] else f'{low} and up'
    return 'not known'


def on_hero(spark: Mapping[str, Any], whole: int) -> bool:
    """The spark ended on the character: last seen within rates.END_ON of it, before its time was up and
    not because the take ended."""
    return (
        spark['end_hero'] is not None and spark['end_hero'] <= END_ON and spark['frames'] < whole and not spark['cut']
    )


def releasing(monsters: Sequence[Mapping[str, Any]], counts: Mapping[tuple[str, int], int]) -> dict[str, Any]:
    """The releases of `monsters` against their seen hits: per hit, and per second of being struck for
    each of WINDOWS, each with its deviance over the monsters seen struck."""
    seen = [m for m in monsters if m['hits']]
    released = [counts.get((m['take'], m['unit']), 0) for m in seen]
    hits = [[hit[0] for hit in m['hits']] for m in seen]
    total = sum(released)
    found: dict[str, Any] = {
        'monsters': len(seen),
        'hits': sum(map(len, hits)),
        'releases': total,
        'releases_unstruck': sum(counts.get((m['take'], m['unit']), 0) for m in monsters if not m['hits']),
    }
    if not found['hits']:
        return found
    # From a monster's first seen hit to its last and one window on: the longest it can have been struck.
    spans = [(h[-1] - h[0] + STRUCK) / GAME_RATE for h in hits]
    found['per_span'] = {'span_seconds': round(sum(spans), 1), 'value': round(total / sum(spans), 4)}
    per_hit = total / found['hits']
    found['per_hit'] = {
        'value': round(per_hit, 4),
        'deviance': deviance([(len(h), n) for h, n in zip(hits, released, strict=True)], per_hit),
    }
    found['per_second'] = []
    for window in WINDOWS:
        seconds = [struck_frames(h, window) / GAME_RATE for h in hits]
        rate = total / sum(seconds)
        found['per_second'].append(
            {
                'window': window,
                'struck_seconds': round(sum(seconds), 2),
                'value': round(rate, 4),
                'deviance': deviance(list(zip(seconds, released, strict=True)), rate),
            }
        )
    return found


def by_gap(monsters: Sequence[Mapping[str, Any]], frames: Mapping[tuple[str, int], Sequence[int]]) -> dict[str, Any]:
    """The hits of `monsters` by the frames since the hit before, each band with how many of them brought
    a release: one in the hit's frame or the next, with no later hit before it (`frames`: the frames of a
    monster's releases)."""
    found: dict[str, list[int]] = {'first': [0, 0], **{band_of(low): [0, 0] for low, _high in SINCE[1:]}}
    for monster in monsters:
        hits = [hit[0] for hit in monster['hits']]
        last = {max(hit for hit in hits if hit <= frame) for frame in frames.get((monster['take'], monster['unit']), ())
                if any(0 <= frame - hit <= 1 for hit in hits)}  # fmt: skip
        before = None
        for hit in hits:
            band = 'first' if before is None else band_of(hit - before)
            found[band][0] += 1
            found[band][1] += hit in last
            before = hit
    return found


def measure(tallies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What a set of takes shows of the sparks (`tally` of each)."""
    monsters = [m for one in tallies for m in one['monsters']]
    releases = [r for one in tallies for r in one['releases']]
    sparks = [(release, spark) for release in releases for spark in release['sparks']]
    counts = Counter((r['take'], r['owner']) for r in releases if r['known'])
    charged = [m for m in monsters if LIGHTNING in (m['mods'] or ())]
    most = max((spark['frames'] for _release, spark in sparks), default=0)
    whole = most - 2  # a spark seen this long flew its time out

    def owners(key: str, names: Sequence[str], of: Any) -> dict[str, Any]:
        found = {}
        for name in names:
            mine = [m for m in charged if of(m) == name]
            let = [r for r in releases if r['known'] and r['charged'] and of(r) == name]
            if not mine and not let:
                continue
            found[name] = {
                'monsters': len(mine),
                'seconds': round(sum(m['seconds'] for m in mine), 1),
                'hits': sum(len(m['hits']) for m in mine),
                'struck': sum(bool(m['hits']) for m in mine),
                'releasers': len({(r['take'], r['owner']) for r in let}),
                'releases': len(let),
                'sparks': sum(len(r['sparks']) for r in let),
            }
        return found

    elite = [m for m in charged if m['rank'] in ELITE]
    gaps = []
    by_owner: dict[tuple[str, int], list[int]] = defaultdict(list)
    for release in releases:
        if release['known']:
            by_owner[release['take'], release['owner']].append(release['frame'])
    for frames in by_owner.values():
        gaps += [later - sooner for sooner, later in itertools.pairwise(sorted(frames))]
    since = Counter()
    for release in releases:
        found = release['since']
        since[band_of(found)] += 1

    flown = [spark for _release, spark in sparks]
    early = [spark for spark in flown if spark['frames'] < whole and not spark['cut']]
    courses = [(r, s) for r, s in sparks if s['course'] is not None and s['born'] <= 0.5]
    aimed = [(r, s) for r, s in courses if r['to_hero'] is not None]
    runs = Counter(run for spark in flown for run in spark['runs'])
    bends = Counter(min((45, 90, 180), key=lambda turn: abs(turn - bend)) for s in flown for bend in s['bends'])
    strides = [spark['stride'] for spark in flown if spark['stride']]
    stride = statistics.median(strides) if strides else None
    out = {
        str(age): spread([spark['outs'][str(age)] for spark in flown if str(age) in spark['outs']], 1) for age in AGES
    }

    alive = [r for r in releases if r['hero_dead'] == 0 and r['away'] is not None]
    bands: list[dict[str, Any]] = []
    for low, high in (*itertools.pairwise(BANDS), (BANDS[0], BANDS[-1])):
        mine = [r for r in alive if low <= r['away'] < high]
        let = [spark for r in mine for spark in r['sparks']]
        near = sum(spark['closest'] is not None and spark['closest'] <= END_ON for spark in let)
        ended = sum(on_hero(spark, whole) for spark in let)
        bands.append(
            {
                'from': low,
                'to': high,
                'releases': len(mine),
                'sparks': len(let),
                'within': near,
                'on_hero': ended,
                'on_friend': sum(
                    not on_hero(spark, whole)
                    and spark['frames'] < whole
                    and spark['end_friend'] is not None
                    and spark['end_friend'] <= END_ON
                    for spark in let
                ),
                'per_release': round(ended / len(mine), 3) if mine else None,
            }
        )
    whole_band = bands.pop()
    arrived = [(r, s) for r in alive for s in r['sparks'] if on_hero(s, whole)]

    def taken(found: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]]) -> dict[str, Any]:
        drops = [spark['drop'] for _release, spark in found if spark['drop'] is not None]
        sole = [drop for drop in drops if drop[4]]
        return {
            'arrivals': len(found),
            'sole': len(sole),
            'shared': sum(bool(drop[5]) and not drop[4] for drop in drops),
            'any': len(drops),
            'fell': sum(bool(spark['fell']) for _release, spark in found),
            'points_sole': [drop[1] for drop in sole],
            'points_any': [drop[1] for drop in drops],
        }

    life = taken(arrived)
    n = life['arrivals']
    life |= {
        'low': round(life['sole'] / n, 4) if n else None,
        'high': round(life['any'] / n, 4) if n else None,
        'upper95': upper(n) if n and not life['any'] else None,
        'by_rank': {rank: taken([(r, s) for r, s in arrived if r['rank'] == rank]) for rank in RANKS},
        'by_tier': {str(tier): taken([(r, s) for r, s in arrived if r['tier'] == tier]) for tier in (0, 1, 2, 3)},
        'by_level': {
            band: taken([(r, s) for r, s in arrived if level_band(r['level']) == band])
            for band in dict.fromkeys(level_band(r['level']) for r in releases)
        },
        'levels': spread([r['level'] for r, _spark in arrived if r['level']], 0),
    }
    for part in ('by_rank', 'by_tier', 'by_level'):
        life[part] = {name: found for name, found in life[part].items() if found['arrivals']}
    ends = {(one['take'], spark['last']) for one in tallies for r in one['releases'] for spark in r['sparks']
            if on_hero(spark, whole)}  # fmt: skip
    near = [
        drop | {'ended': int(any((drop['take'], drop['frame'] - back) in ends for back in range(AFTER + 1)))}
        for one in tallies
        for drop in one['drops']
    ]
    return {
        'takes': len(tallies),
        'seconds': round(sum(one['seconds'] for one in tallies), 1),
        'takes_with_sparks': sum(bool(one['releases']) for one in tallies),
        'releases': len(releases),
        'sparks': len(sparks),
        'unowned': sum(not r['known'] for r in releases),
        'owner_not_charged': sum(bool(r['known']) and not r['charged'] for r in releases),
        'hero_dead': sum(r['hero_dead'] == 1 for r in releases),
        'by_rank': owners('rank', RANKS, lambda found: found['rank']),
        'by_tier': owners('tier', ('0', '1', '2', '3'), lambda found: str(found['tier'])),
        'by_level': owners('level', [level_band(level) for level in LEVELS[:-1]], lambda f: level_band(f['level'])),
        'release': {
            'all': releasing(elite, counts),
            'tier 0': releasing([m for m in elite if not m['tier']], counts),
            'herald': releasing([m for m in elite if m['tier']], counts),
            'since': dict(since),
            'by_gap': by_gap(elite, by_owner),
            'gap': spread(gaps, 0) | {'usual': runs_mode(Counter(gaps))},
            'mode_at': dict(Counter(str(r['mode']) for r in releases).most_common()),
        },
        'count': {'n': len(releases), 'sizes': dict(Counter(str(len(r['sparks'])) for r in releases).most_common())},
        'flight': {
            'sparks': len(flown),
            'stride': None if stride is None else round(stride, 4),
            'stride_n': len(strides),
            'frames_most': most,
            'whole': sum(spark['frames'] >= whole for spark in flown),
            'out': out,
            'out_whole': spread([spark['out'] for spark in flown if spark['frames'] >= whole], 1),
            'runs': {str(run): count for run, count in sorted(runs.items()) if run <= 20},
            'turn': runs_mode(runs),
            'turns': sum(runs.values()),
            'bends': {str(turn): bends[turn] for turn in (45, 90, 180)},
            'on_45': {
                'n': len(courses),
                'share': round(
                    sum(turned(s['course'] % 45, 0) <= 5 or s['course'] % 45 >= 40 for _r, s in courses) / len(courses),
                    3,
                )
                if courses
                else None,
            },
            'toward': {
                'n': len(aimed),
                'share': round(sum(turned(s['course'], r['to_hero']) <= 22.5 for r, s in aimed) / len(aimed), 3)
                if aimed
                else None,
            },
        },
        'ends': {
            'early': len(early),
            'on_hero': sum(on_hero(spark, whole) for spark in early),
            'on_friend': sum(
                not on_hero(s, whole) and s['end_friend'] is not None and s['end_friend'] <= END_ON for s in early
            ),
            'on_foe': sum(
                not on_hero(s, whole)
                and not (s['end_friend'] is not None and s['end_friend'] <= END_ON)
                and s['end_foe'] is not None
                and s['end_foe'] <= END_ON
                for s in early
            ),
        },
        'reach': {
            'releases': len(alive),
            'away': spread([r['away'] for r in alive], 1),
            'bands': bands,
            'all': whole_band,
            'meets': {
                'value': round(whole_band['on_hero'] / whole_band['within'], 4) if whole_band['within'] else None,
                'n': whole_band['within'],
            },
        },
        'life': life,
        'drops_near': near,
    }


def band_of(since: int | None) -> str:
    """The band of SINCE that frames `since` a hit fall in, as a table names it."""
    if since is None:
        return 'no hit seen before'
    low, high = next((low, high) for low, high in SINCE if low <= since <= high)
    return str(low) if low == high else f'{low}-{high}' if high < 10**9 else f'{low}+'


def runs_mode(counts: Mapping[int, int]) -> int | None:
    """The commonest value; of several as common, the least."""
    return min(counts, key=lambda value: (-counts[value], value)) if counts else None


# ---------------------------------------------------------------------------------------------------
# SPARKS.md.


def show(value: Any, digits: int = 2) -> str:
    if value is None:
        return '-'
    if isinstance(value, float):
        return f'{value:,.{digits}f}'
    return f'{value:,}' if isinstance(value, int) else str(value)


def over(above: Any, below: Any) -> str:
    numbers = isinstance(above, int | float) and isinstance(below, int | float)
    return f'{above / below:.2f}' if numbers and below else '-'


def table(headers: Sequence[str], lines: Sequence[Sequence[Any]]) -> list[str]:
    out = ['| ' + ' | '.join(headers) + ' |', '|' + ' --- |' * len(headers)]
    out += ['| ' + ' | '.join(str(cell) for cell in line) + ' |' for line in lines]
    return [*out, '']


def owners_part(title: str, part: str, train: Mapping[str, Any], check: Mapping[str, Any]) -> list[str]:
    def cells(found: Mapping[str, Any] | None) -> list[str]:
        if not found:
            return ['-', '-', '-', '-']
        return [
            f'{found["monsters"]:,} ({found["struck"]:,})',
            f'{found["hits"]:,}',
            f'{found["releases"]:,} of {found["releasers"]:,}',
            f'{found["sparks"]:,}',
        ]

    names = dict.fromkeys((*train[part], *check[part]))
    lines = [[name, *cells(train[part].get(name)), *cells(check[part].get(name))] for name in names]
    heads = ('Lightning Enchanted monsters (seen struck)', 'hits seen', 'releases of how many monsters', 'sparks')
    return table([title, *(f'train: {head}' for head in heads), *(f'check: {head}' for head in heads)], lines)


def relation_lines(train: Mapping[str, Any], check: Mapping[str, Any], group: str) -> list[list[Any]]:
    def cell(found: Mapping[str, Any] | None) -> str:
        return '-' if not found else f'{show(found["value"], 3)} (deviance {found["deviance"]})'

    one, other = train['release'][group], check['release'][group]
    said = f'{group}: {one["releases"]} releases, {one["hits"]} hits of {one["monsters"]} monsters'
    said += f' (check: {other["releases"]}, {other["hits"]}, {other["monsters"]})'
    lines = [[said, 'releases per hit seen', cell(one.get('per_hit')), cell(other.get('per_hit'))]]
    for index, window in enumerate(WINDOWS):
        mine = [found['per_second'][index] if found.get('per_second') else None for found in (one, other)]
        seconds = ' / '.join('-' if found is None else f'{found["struck_seconds"]:.1f}' for found in mine)
        lines.append(
            ['', f'releases per second struck, {window} frames after a hit ({seconds} s)', cell(mine[0]), cell(mine[1])]
        )
    spans = [found.get('per_span') for found in (one, other)]
    seconds = ' / '.join('-' if found is None else f'{found["span_seconds"]:.1f}' for found in spans)
    lines.append(
        [
            '',
            f'releases per second from its first seen hit to its last ({seconds} s)',
            *('-' if found is None else show(found['value'], 3) for found in spans),
        ]
    )
    return lines


def best(found: Mapping[str, Any]) -> Mapping[str, Any]:
    """The window of a release relation (`measure`'s) with the least deviance; the shorter of two alike."""
    return min(found['per_second'], key=lambda row: (row['deviance'], row['window']))


def render(found: Mapping[str, Any]) -> str:
    """SPARKS.md from sparks.json's content."""
    from tests.inventory_tracking.scenarios.arena.evidence import model  # the model's side, read last

    train, check, before = found['train'], found['check'], model.SPARKS_BEFORE
    level = int(train['life']['levels']['p50'] or check['life']['levels']['p50'] or 0)
    now = model.sparks(level) if 'sparks' in model.fitted() else None

    def got(name: str) -> Any:
        return None if now is None else now[name]

    def line(what: str, one: Any, n_one: Any, other: Any, n_other: Any, old: Any, new: Any) -> list[str]:
        return [
            what,
            f'{show(one)} (n {show(n_one)})',
            f'{show(other)} (n {show(n_other)})',
            show(old),
            over(old, one),
            show(new),
            over(new, other),
        ]

    chosen = best(train['release']['all'])
    same = next(row for row in check['release']['all']['per_second'] if row['window'] == chosen['window'])
    flight, flown = train['flight'], check['flight']
    stride = float(tables()['missiles'][str(SPARK)]['Vel']) / GAME_RATE
    life, lived = train['life'], check['life']
    both = life['arrivals'] + lived['arrivals']
    raw = model.spark_points(level)
    out = [
        '# The sparks of a Lightning Enchanted monster in the takes',
        '',
        'Generated by `uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.sparks` from the '
        'takes of `split.json`; do not edit by hand. `sparks.json` beside this file holds the same numbers; the method '
        'is in the module text of `sparks.py`. The model beside the takes is combat/sim/monsters.py: **before** is how '
        'it played sparks before they were fitted (evidence/model.py `SPARKS_BEFORE`), **now** what '
        'data/monsters_fit.json holds, fitted on the train half by evidence/fit.py. A ratio is model / measured: '
        'before over train, now over check.',
        '',
        f'- **Takes:** train {train["takes"]} ({train["seconds"]:,.0f} s), {train["takes_with_sparks"]} with sparks: '
        f'**{train["releases"]} releases, {train["sparks"]} sparks**; check {check["takes"]} '
        f'({check["seconds"]:,.0f} s), {check["takes_with_sparks"]} with sparks: **{check["releases"]} releases, '
        f'{check["sparks"]} sparks**. Takes of one game session fall in both halves.',
        f'- **The missile** is `lightunique` ({SPARK}), tied to its monster by the owner in its unit record. Releases '
        f'whose owner the take did not hold: train {train["unowned"]}, check {check["unowned"]}; whose owner is not '
        f'Lightning Enchanted by its enchantments: {train["owner_not_charged"]} and {check["owner_not_charged"]}.',
        f"- **The character lay dead** at {check['hero_dead']} of the check half's releases (train: "
        f'{train["hero_dead"]}): they count for how sparks are let go and fly, not for what reaches it or takes life.',
        f'- **Small numbers.** The train half holds {train["releases"]} releases and {life["arrivals"]} sparks that '
        'ended on the character; nothing below is more than its n.',
        '',
        '## 1. Who lets sparks go',
        '',
        *owners_part('rank', 'by_rank', train, check),
        'Only the leader of a pack lets sparks go: a unique or a super unique. Its minions carry the same enchantment '
        'and were seen struck as often, and let none go; nor did a plain monster carrying it. **Before, the model '
        f'let any monster with the enchantment release** ({", ".join(before["ranks"])}); now: '
        f'{"-" if now is None else ", ".join(now["ranks"])} (its `unique` is a unique or a super unique).',
        '',
        *owners_part("Herald's tier", 'by_tier', train, check),
        *owners_part('monster level', 'by_level', train, check),
        '## 2. When: a release against the hits its owner takes',
        '',
        "A hit is a frame in which the owner's life (in 128ths of its most) was lower than in the frame before; the "
        'time it was being struck is so many frames after each hit, merged. The deviance says how well one rate for '
        "all monsters gives each monster's count of releases (Poisson; lower is better).",
        '',
        *table(
            ['monsters', 'relation', 'train', 'check'],
            [line for group in ('all', 'tier 0', 'herald') for line in relation_lines(train, check, group)],
        ),
        f'**Per second of being struck holds best on the train half, by little**: with {chosen["window"]} frames after '
        f'a hit, {show(chosen["value"], 3)} releases a second (deviance {chosen["deviance"]} against '
        f'{train["release"]["all"]["per_hit"]["deviance"]} for a chance per hit). A chance per hit does not hold '
        "because hits close together do not each bring a release (the second table below). **A Herald's hits are "
        'undercounted** (its life is tens of thousands of points; a hit under a 128th of it does not show), so its '
        'rows per hit and per second struck are too high: the last row of each group, the releases over the whole '
        "time from its first seen hit to its last, is the lower bound. Most of the check half's Herald releases are "
        'of one take in which the character lay dead beside the Herald (20261011T195359Z-25): what struck it there '
        'the take does not say.',
        '',
        *table(
            ["frames from the owner's last seen hit to the release", 'train releases', 'check releases'],
            [
                [name, train['release']['since'].get(name, 0), check['release']['since'].get(name, 0)]
                for name in (*(band_of(low) for low, _high in SINCE), band_of(None))
            ],
        ),
        *table(
            ['frames from the hit before', 'train: hits', 'with a release', 'check: hits', 'with a release'],
            [
                [name, *train['release']['by_gap'][name], *check['release']['by_gap'][name]]
                for name in train['release']['by_gap']
            ],
        ),
        *table(
            ['', 'train (n)', 'check (n)', 'model before', 'before / train', 'model now', 'now / check'],
            [
                line(
                    f'releases per second of being struck ({chosen["window"]} frames after a hit)',
                    chosen['value'],
                    train['release']['all']['releases'],
                    same['value'],
                    check['release']['all']['releases'],
                    before['rate'],
                    got('rate'),
                ),
                line(
                    'frames between two releases of one monster, least',
                    train['release']['gap']['least'],
                    train['release']['gap']['n'],
                    check['release']['gap']['least'],
                    check['release']['gap']['n'],
                    before['gap'],
                    got('gap'),
                ),
                line(
                    'the same, median',
                    train['release']['gap']['p50'],
                    train['release']['gap']['n'],
                    check['release']['gap']['p50'],
                    check['release']['gap']['n'],
                    None,
                    None,
                ),
                line(
                    'the same, commonest',
                    train['release']['gap']['usual'],
                    train['release']['gap']['n'],
                    check['release']['gap']['usual'],
                    check['release']['gap']['n'],
                    None,
                    None,
                ),
            ],
        ),
        f'Before: a release with a chance of {before["chance"]} at every frame the monster was struck in, '
        f"{before['gap']} frames apart at least: {before['rate']} a second for one struck in every frame. The owner's "
        'mode in the frame of a release (train): '
        + ', '.join(f'{mode}: {count}' for mode, count in train['release']['mode_at'].items())
        + ' (no one mode goes with a release).',
        '',
        '## 3. How many, how fast, how far, where to',
        '',
        *table(
            ['', 'train (n)', 'check (n)', 'model before', 'before / train', 'model now', 'now / check'],
            [
                line(
                    'sparks to a release, commonest',
                    runs_mode({int(k): v for k, v in train['count']['sizes'].items()}) or 0,
                    train['count']['n'],
                    runs_mode({int(k): v for k, v in check['count']['sizes'].items()}) or 0,
                    check['count']['n'],
                    before['count'],
                    got('count'),
                ),
                line(
                    'units a frame, median',
                    flight['stride'],
                    flight['stride_n'],
                    flown['stride'],
                    flown['stride_n'],
                    stride,
                    got('stride'),
                ),
                line(
                    'frames a spark lasts at most',
                    flight['frames_most'],
                    flight['sparks'],
                    flown['frames_most'],
                    flown['sparks'],
                    before['frames'],
                    got('frames'),
                ),
                *(
                    line(
                        f'units out after {age} frames, median',
                        flight['out'][str(age)]['p50'],
                        flight['out'][str(age)]['n'],
                        flown['out'][str(age)]['p50'],
                        flown['out'][str(age)]['n'],
                        None,
                        None,
                    )
                    for age in AGES
                ),
                line(
                    'units out at its end, a spark that flew its time, median',
                    flight['out_whole']['p50'],
                    flight['out_whole']['n'],
                    flown['out_whole']['p50'],
                    flown['out_whole']['n'],
                    None,
                    None,
                ),
                line(
                    'frames between two turns, commonest',
                    flight['turn'],
                    flight['turns'],
                    flown['turn'],
                    flown['turns'],
                    before['turn'],
                    got('turn'),
                ),
                line(
                    'share of first directions on a multiple of 45 degrees',
                    flight['on_45']['share'],
                    flight['on_45']['n'],
                    flown['on_45']['share'],
                    flown['on_45']['n'],
                    1.0,
                    1.0,
                ),
                line(
                    'share of sparks sent within 22.5 degrees of the character (1 in 8 by chance: 0.125)',
                    flight['toward']['share'],
                    flight['toward']['n'],
                    flown['toward']['share'],
                    flown['toward']['n'],
                    0.125,
                    0.125,
                ),
            ],
        ),
        f'Release sizes: train {train["count"]["sizes"]}, check {check["count"]["sizes"]}. Turns by size (train): '
        f'{flight["bends"]} (check: {flown["bends"]}): a spark flies along one of eight directions or 45 degrees to '
        'either side of it and changes between the three, as the model has it; the sparks are not sent at whoever '
        "struck. The model's distances out are played in evidence/refit_check.py. The speed is the missile's `Vel` "
        'in both models (read from the game).',
        '',
        f'How the sparks that did not fly their time out ended (train {train["ends"]["early"]}, check '
        f'{check["ends"]["early"]}): on the character {train["ends"]["on_hero"]} and {check["ends"]["on_hero"]}, on a '
        f'companion {train["ends"]["on_friend"]} and {check["ends"]["on_friend"]}, on another monster '
        f'{train["ends"]["on_foe"]} and {check["ends"]["on_foe"]} (last seen within {END_ON} units of one); the rest '
        "on a wall or out of the client's sight.",
        '',
        '## 4. How many end on the character, by its distance from the monster at the release',
        '',
        f'Releases with the character alive. A spark ended on the character when it was last seen within {END_ON} '
        'units of it before its time was up; it came within reach when it was ever seen that near.',
        '',
        *table(
            [
                'units',
                *(
                    f'{half}: {head}'
                    for half in ('train', 'check')
                    for head in (
                        'releases',
                        'sparks',
                        'came within reach',
                        'ended on it',
                        'on it per release',
                        'ended on a companion',
                    )
                ),
            ],
            [
                [
                    f'{one["from"]:g} to {one["to"]:g}',
                    *(
                        cell
                        for band in (one, other)
                        for cell in (
                            band['releases'],
                            band['sparks'],
                            band['within'],
                            band['on_hero'],
                            show(band['per_release']),
                            band['on_friend'],
                        )
                    ),
                ]
                for one, other in zip(
                    [*train['reach']['bands'], train['reach']['all']],
                    [*check['reach']['bands'], check['reach']['all']],
                    strict=True,
                )
            ],
        ),
        *table(
            ['', 'train (n)', 'check (n)', 'model before', 'before / train', 'model now', 'now / check'],
            [
                line(
                    'units from the monster to the character at a release, median',
                    train['reach']['away']['p50'],
                    train['reach']['away']['n'],
                    check['reach']['away']['p50'],
                    check['reach']['away']['n'],
                    None,
                    None,
                ),
                line(
                    'share of the sparks that came within reach of the character that ended on it',
                    train['reach']['meets']['value'],
                    train['reach']['meets']['n'],
                    check['reach']['meets']['value'],
                    check['reach']['meets']['n'],
                    before['meets'],
                    got('meets'),
                ),
                line(
                    'sparks ending on the character per release',
                    train['reach']['all']['per_release'],
                    train['reach']['all']['releases'],
                    check['reach']['all']['per_release'],
                    check['reach']['all']['releases'],
                    None,
                    None,
                ),
            ],
        ),
        f'Before, every spark within {before["contact"]} units of the character ended on it; in the takes over half '
        "of those that come that near fly on (a miss, as far as a take can say). What the model's sparks do at these "
        'distances is played in evidence/refit_check.py.',
        '',
        '## 5. Whether a spark that ends on the character takes life, and how much',
        '',
        *table(
            ['', 'train', 'check'],
            [
                ['sparks that ended on the character', life['arrivals'], lived['arrivals']],
                [f'followed within {AFTER} frames by a drop put on their owner alone', life['sole'], lived['sole']],
                ['by a drop their owner shares with other suspects', life['shared'], lived['shared']],
                ['by any drop at all', life['any'], lived['any']],
                ['by a fall of the life of any size, under 5 points too', life['fell'], lived['fell']],
                [
                    'the share that takes life, lower to upper',
                    f'{show(life["low"], 3)} to {show(life["high"], 3)}',
                    f'{show(lived["low"], 3)} to {show(lived["high"], 3)}',
                ],
                [
                    'with none seen: the chance is under this at 95%',
                    show(life['upper95'], 3),
                    show(lived['upper95'], 3),
                ],
                ['points of the drops put on the owner alone', life['points_sole'] or '-', lived['points_sole'] or '-'],
                ['points of any drop that followed', life['points_any'] or '-', lived['points_any'] or '-'],
            ],
        ),
        f'**No spark that ended on the character took life on the train half ({life["sole"]} of {life["arrivals"]}), '
        f'and {lived["sole"]} of {lived["arrivals"]} on the check half** (the one drop that followed an arrival there '
        'has a monster striking beside the character as its only suspect). Not a point: the life read before and '
        'after is the same number, so it is not a blow too small to be written either. Why, a take cannot say: a miss, '
        'a block, a spark whose points are next to nothing (the level its missile is cast at may not be the '
        f"monster's), or this character's own protection. With {both} arrivals in both halves and none taking life "
        f"the chance is under {show(upper(both), 3)} at 95%; with the train half's {life['arrivals']} alone, under "
        f'{show(life["upper95"], 3)}. **The size of a spark that takes life cannot be measured: there is none.** By '
        f'the tables a spark of a level {level} monster (the median of the owners whose sparks arrived) is '
        f"{raw:g} points of lightning, {model.taken({'lightning': raw}):.1f} through the main set's resistance; "
        f'before, every arrival took that.',
        '',
        *table(
            ['the arrivals by', '', 'train: arrivals', 'took life', 'check: arrivals', 'took life (any drop)'],
            [
                [
                    said if not index else '',
                    name,
                    one.get(name, {}).get('arrivals', 0),
                    one.get(name, {}).get('sole', 0),
                    other.get(name, {}).get('arrivals', 0),
                    f'{other.get(name, {}).get("sole", 0)} ({other.get(name, {}).get("any", 0)})',
                ]
                for said, part in (
                    ("the owner's rank", 'by_rank'),
                    ("its Herald's tier", 'by_tier'),
                    ('its level', 'by_level'),
                )
                for one, other in ((life[part], lived[part]),)
                for index, name in enumerate(dict.fromkeys((*one, *other)))
            ],
        ),
        'The drops blows.py lists with a spark near the character (within 3 units, or within 6 and gone by the next '
        'frame), in both halves:',
        '',
        *table(
            ['half', 'take', 'frame', 'points', 'class', 'sparks near', 'a spark ended on the character just before'],
            [
                [
                    half,
                    drop['take'],
                    drop['frame'],
                    drop['lost'],
                    drop['class'],
                    drop['sparks'],
                    'yes' if drop['ended'] else 'no: it flew on',
                ]
                for half in ('train', 'check')
                for drop in found[half]['drops_near']
            ],
        ),
        "None of them is a spark's: in each the spark was still in flight two units or more from the character in "
        "the frame of the drop and after it. EVIDENCE.md counts them as the owner's (one as a death's missile).",
        '',
        '## 6. The model beside the takes',
        '',
        *table(
            ['', 'before', 'now', 'train', 'check'],
            [
                [
                    'who lets sparks go',
                    ', '.join(before['ranks']),
                    '-' if now is None else ', '.join(now['ranks']),
                    ', '.join(rank for rank, row in train['by_rank'].items() if row['releases']),
                    ', '.join(rank for rank, row in check['by_rank'].items() if row['releases']),
                ],
                [
                    'releases a second of being struck',
                    before['rate'],
                    show(got('rate'), 3),
                    show(chosen['value'], 3),
                    show(same['value'], 3),
                ],
                [
                    'frames between two releases at least',
                    before['gap'],
                    show(got('gap')),
                    train['release']['gap']['least'],
                    check['release']['gap']['least'],
                ],
                [
                    'sparks to a release',
                    before['count'],
                    show(got('count')),
                    train['count']['sizes'],
                    check['count']['sizes'],
                ],
                [
                    'frames a spark lasts',
                    before['frames'],
                    show(got('frames')),
                    flight['frames_most'],
                    flown['frames_most'],
                ],
                ['frames between two turns', before['turn'], show(got('turn')), flight['turn'], flown['turn']],
                [
                    'units a frame',
                    show(stride),
                    show(got('stride')),
                    show(flight['stride'], 3),
                    show(flown['stride'], 3),
                ],
                [
                    'units from the character at which a spark is in reach of it',
                    before['contact'],
                    show(got('contact')),
                    END_ON,
                    END_ON,
                ],
                [
                    'share of the sparks in reach that end on it',
                    before['meets'],
                    show(got('meets'), 3),
                    show(train['reach']['meets']['value'], 3),
                    show(check['reach']['meets']['value'], 3),
                ],
                [
                    'share of those that takes life',
                    before['takes_life'],
                    show(got('takes_life'), 3),
                    f'{show(life["low"], 3)} of {life["arrivals"]}',
                    f'{show(lived["low"], 3)} of {lived["arrivals"]}',
                ],
                [
                    f'points of one that does (level {level}, the main set)',
                    show(model.taken({'lightning': raw}), 1),
                    show(got('points'), 1),
                    'none seen',
                    'none seen',
                ],
            ],
        ),
        '## 7. What the takes cannot say',
        '',
        '- **Why a release comes.** Neither every hit nor every second of being struck gives one; the best one rate '
        "does is the deviance above. Hits under a 128th of the owner's life are not seen.",
        '- **Why a spark that reaches the character takes nothing.** One number stands for a miss, a block, a spark '
        "of next to no points and this character's protection; another character would need its own.",
        f"- **The size of a spark's blow.** No drop is a spark's in {train['sparks'] + check['sparks']:,} sparks.",
        '- **A companion in the way.** A spark that ends near a companion is counted; whether it hurt it is not '
        'looked at (nothing in the arena hurts a companion).',
        '',
    ]
    return '\n'.join(out)


# ---------------------------------------------------------------------------------------------------
# What kills in the arena: the blows of the last second of the plays the character died in.


def last_blows(names: Sequence[str], seeds: Sequence[int], window: float = 1.0) -> dict[str, Any]:
    """The closed-loop plays of the fixture scenes `names` (as trials.py plays them) with every blow on
    the character written down: per scene the plays, the deaths, and of each death the blows of the
    `window` seconds before it, by kind and by who struck (its rank, type and Herald tier). A play's
    `Result` does not say what killed; this does, for the arena's monsters as they are now.

        uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.sparks --deaths <scene> ...
    """
    from tests.inventory_tracking.scenarios.arena import driver, trials  # the arena, only for this
    from tests.inventory_tracking.scenarios.arena.mobs import Horde

    cases = {case.name: case for case in trials.fixture_cases()}
    step = Horde.step
    found: dict[str, Any] = {}
    for name in names:
        case = cases[name]
        mobs = {mob.unit: mob for mob in case.scene.mobs}
        deaths = []
        for seed in seeds:
            blows: list[Any] = []

            def logged(pack: Any, frame: int, targets: Any, blows: list[Any] = blows) -> Any:
                dealt = step(pack, frame, targets)
                blows.extend(blow for blow in dealt if blow.target == 0)
                return dealt

            Horde.step = logged  # type: ignore[method-assign]
            try:
                result = driver.play(case.scene.copy(), case.presses, case.seconds, seed=seed, auras=case.auras)
            finally:
                Horde.step = step  # type: ignore[method-assign]
            if result.dead_at is None:
                continue
            last = [blow for blow in blows if blow.frame >= (result.dead_at - window) * GAME_RATE]
            deaths.append(
                {
                    'seed': seed,
                    'dead_at': round(result.dead_at, 2),
                    'blows': len(blows),
                    'sparks': sum(blow.kind == SPARK_KIND for blow in blows),
                    'last': [
                        {
                            'kind': blow.kind,
                            'raw': round(blow.damage),
                            'rank': rank_of(mobs[blow.unit].flags),
                            'name': name_of(mobs[blow.unit].txt),
                            'tier': mobs[blow.unit].tier,
                            'seconds_before': round(result.dead_at - blow.frame / GAME_RATE, 2),
                        }
                        for blow in last
                    ],
                }
            )
        found[name] = {'plays': len(seeds), 'deaths': deaths}
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='The sparks of Lightning Enchanted monsters, from all takes.')
    parser.add_argument('--deaths', nargs='+', metavar='SCENE', help='instead: what kills in these fixture scenes')
    parser.add_argument('--seeds', type=int, default=30, help='with --deaths: seeds 1..N')
    parser.add_argument('--root', type=Path, default=scan.ROOT, help='the directory of the takes')
    parser.add_argument('--jobs', type=int, help='worker processes (default: the cores, 16 at most)')
    parser.add_argument('--no-cache', action='store_true', help='read every take again')
    parser.add_argument('--cache', type=Path, default=CACHE, help='where per-take results go')
    parser.add_argument('--out', type=Path, default=HERE, help='where SPARKS.md and sparks.json go')
    parser.add_argument('--render', action='store_true', help='write SPARKS.md again from sparks.json, reading no take')
    args = parser.parse_args(argv)
    if args.deaths:
        for name, row in last_blows(args.deaths, range(1, args.seeds + 1)).items():
            print(f'{name}: dead in {len(row["deaths"])} of {row["plays"]} plays')
            for death in row['deaths']:
                said = '; '.join(
                    f'{blow["kind"]} of {blow["raw"]} raw by a {blow["rank"]} {blow["name"]}'
                    + (f' of tier {blow["tier"]}' if blow['tier'] else '')
                    + f' {blow["seconds_before"]:.2f} s before'
                    for blow in death['last']
                )
                print(
                    f'  seed {death["seed"]}: dead at {death["dead_at"]} s after {death["blows"]} blows '
                    f'({death["sparks"]} sparks); the last second: {said or "no blow of a monster"}'
                )
        return 0
    path = args.out / 'sparks.json'
    if args.render:
        found = json.loads(path.read_text())
    else:
        split = json.loads(SPLIT.read_text())
        cache = None if args.no_cache else args.cache
        halves = {
            half: gather([args.root / name for name in split[half]], cache=cache, jobs=args.jobs)
            for half in (scan.TRAIN, scan.CHECK)
        }
        found = {
            'about': 'tests/inventory_tracking/scenarios/arena/evidence/sparks.py: see SPARKS.md; fit on train, '
            'judge on check',
            'missile': SPARK,
            'split': SPLIT.name,
            'constants': {'end_on': END_ON, 'after': AFTER, 'same': SAME, 'early': EARLY, 'windows': WINDOWS},
            **{half: measure([one for one in read if 'skipped' not in one]) for half, read in halves.items()},
        }
        path.write_text(json.dumps(found, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (args.out / 'SPARKS.md').write_text(render(found), encoding='utf-8')
    print(f'{args.out / "SPARKS.md"}, sparks.json written', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
