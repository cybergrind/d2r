"""How often a monster strikes when it could, from the frames: the tallies of one take (`tally`) and
what a set of takes measures per monster type and mechanism (`measure`).

A take is tallied once into counts small enough to cache (TALLY says what they are); every
question that needs a number decided over all takes first (how far a type really reaches, how long
its swing lasts) is answered afterwards from those counts, not by reading the takes again:

- `near`: seconds a live hostile of a type and rank stood at each distance from the character, in
  bins of BIN units up to FAR. Time within any reach is a sum of bins;
- `sight`: the same for monsters that shoot (the threat table's `ranged`, and any unit that owned a
  hostile missile in the take), counted only while macros/sight.py `clear_shot` holds over the take's
  level file, looked at every SIGHT_EVERY frames. Closed doors are not looked at (said in the report);
- `swings`: one record per run of frames a hostile spent in one attack mode (hurts.ATTACK_MODES)
  that began within FAR: the distance and the target at its start, the drops in its window, the
  hostile missiles it let go and whether one reached the character, how far the character moved
  meanwhile. A run is a swing or a shot, or several back to back: `measure` divides a run by the
  type's usual run length (`usual_frames`);
- `targets`: seconds a hostile within AWARE of the character had the character, a companion or
  another as its path record's target, by which of the character and its nearest companion was nearer;
- `deaths`: every hostile's death within DEATH_REACH of the character, with the life lost in the
  NOVA_FRAMES after it and, as a control, before it, and the missiles it owned that appeared with it.

What cannot be had from a take, and what stands in:

- a swing's animation frame is not in a frame's row, so a swing's start is a mode change. A run cut
  short (hit recovery, death, the first frame of a take) counts as one swing, a run of two swings
  back to back as two only by its length;
- a drop is put on a swing when it shows in the run's frames or the HIT_AFTER after and blows.py
  called that monster its sole suspect (`sole`: the lower bound of its hits). Drops with several
  suspects that name it are `shared` (with `sole`: the upper bound). Where nothing else hostile was
  within CROWD of the character at the swing's start (`alone`) every drop in the window is its own:
  the clean measure, on fewer swings;
- whether a missile was dodged by moving: the character's displacement from the shot's start to
  the end of its missile's flight (`moved`), and whether a single step of it was a jump over JUMP
  units (a teleport): `stood`, `moved`, `jumped`. The character's mode is not used: most of its
  frames are casts, whatever its feet do.
"""

import bisect
import itertools
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from inventory_tracking.combat.hurts import ATTACK_MODES, BESIDE, MISSILE_REACH
from inventory_tracking.combat.sim.monsters import AWARE
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.world import HERALD_TIER_STAT
from inventory_tracking.terror.monsters import LEVEL_STAT
from tests.inventory_tracking.scenarios.arena.evidence.blows import (
    CLASSES,
    DEATH_MISSILE,
    FOE,
    FRIEND,
    GAP,
    HERO,
    MISSILE,
    NOBODY,
    NONE,
    NOVA,
    NOVA_FRAMES,
    OTHER,
    SEVERAL,
    SOLE_MELEE,
    SOLE_RANGED,
    SWING,
    Moment,
    Roster,
    deaths,
    name_of,
    ranged_type,
    rank_of,
)


Point = tuple[float, float]
BIN = 0.5  # units: the width of a distance bin
FAR = 40.0  # units: further from the character than this nothing is tallied (over a screen)
STEP = 0.2  # seconds at most a frame stands for: a longer gap is the recorder's pause, not time in reach
SIGHT_EVERY = 5  # frames between two looks along a shooter's line
HIT_AFTER = 2  # frames after a run's last in which a drop still is that swing's
CROWD = 8.0  # units: no other hostile this near the character and no hostile missile: the swing is alone
JUMP = 5.0  # units in one frame: a teleport, not a walk (the character ran 18.75 a second: 0.75 a frame)
MOVED = 1.5  # units over a shot's flight from which the character counts as having moved
DEATH_REACH = 20.0  # units: deaths further from the character are not tallied
# Units from a body at which a missile last seen is taken to have ended on it: a body's own size and one
# frame of an arrow's flight (the takes' arrows cover about a unit a frame).
END_ON = 2.5
IDLE = 100.0  # seconds within reach per swing above which a type is no fighter (Baal Taunt 545: 5 swings in 870 s)
BIRTH = 12  # frames around a death in which a missile of the dead one's counts as its death's
RANGED_REACH = 30.0  # the arena's reach of a shooter (scenarios/threat/harness.py), restated for the bins
# The model's melee reach as the bins have it: sim/monsters.py REACH is 3.2, and the bin that holds it
# ends at 3.5 (model.py checks the two stay together).
MODEL_REACH = 3.5
MOTIONS = ('stood', 'moved', 'jumped')
TALLY = ('seconds', 'frames', 'near', 'sight', 'swings', 'targets', 'target_units', 'deaths', 'owners', 'paths')
ENOUGH_SECONDS, ENOUGH_BLOWS = 30.0, 10  # a type is tabled with this long in reach or this many sole blows
ENOUGH_SHOTS = 20  # a shooter is tabled from this many shots


def key_of(txt: int, flags: int) -> str:
    return f'{txt}|{rank_of(flags)}'


def ground_of(level: Mapping[str, Any] | None, area: int) -> Ground | None:
    """The take's ground for lines of sight; None without a level file of the area."""
    if not level or level.get('area') != area or not level.get('ground'):
        return None
    return Ground(Walkable(**{k: v for k, v in grid.items() if k != 'masks'}) for grid in level['ground'])


def ended_on(track: Mapping[str, Any]) -> str | None:
    """Whom a missile's flight ended on, by where it was last seen: HERO or FRIEND when one of them was
    within END_ON of it then (the nearer of the two), None when neither was (a wall, the end of its
    range, or it flew on out of the client's sight)."""
    hero, friend = track['end_hero'], track['end_friend']
    if min(hero, friend) > END_ON:
        return None
    return HERO if hero <= friend else FRIEND


def tally(
    take_name: str,
    moments: Sequence[Moment],
    rows: Sequence[Mapping[str, Any]],
    roster: Roster,
    level: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The counts of one take (TALLY) from its moments and its blows (`rows` of blows.py)."""
    bins = int(FAR / BIN)
    near: dict[str, list[float]] = defaultdict(lambda: [0.0] * bins)
    sight: dict[str, list[float]] = defaultdict(lambda: [0.0] * bins)
    targets: dict[str, Counter[str]] = defaultdict(Counter)
    target_units: dict[str, set[tuple[int, str]]] = defaultdict(set)
    owners: Counter[str] = Counter()
    seconds = 0.0
    area = next((m.hero.area for m in moments if m.hero is not None), 0)
    ground = ground_of(level, area)
    places: list[Point | None] = [m.hero.at if m.hero is not None else None for m in moments]
    shooters = {f.owner for m in moments for f in m.flying if f.kind == FOE and f.hostile}
    lines: dict[int, tuple[int, bool]] = {}
    tracks: dict[tuple[int, float], dict[str, Any]] = {}
    open_runs: dict[int, dict[str, Any]] = {}
    runs: list[dict[str, Any]] = []

    def clear(moment: Moment, unit: int, at: Point, here: Point) -> bool | None:
        if ground is None:
            return None
        known = lines.get(unit)
        if known is None or moment.index - known[0] >= SIGHT_EVERY:
            known = lines[unit] = (moment.index, clear_shot(ground, at, here))
        return known[1]

    for position, moment in enumerate(moments):
        hero = moment.hero
        if hero is None:
            runs += open_runs.values()
            open_runs = {}
            continue
        step = min(moments[position + 1].t - moment.t, STEP) if position + 1 < len(moments) else 0.0
        seconds += step
        here = hero.at
        friends = [friend.at for friend in moment.friends]
        for flight in moment.flying:
            if not flight.hostile:
                continue
            away = math.dist(flight.at, here)
            track = tracks.get(flight.key)
            if track is None:
                track = tracks[flight.key] = {
                    'owner': flight.owner, 'kind': flight.kind, 'txt': flight.txt, 'first': moment.index,
                    'last': moment.index, 'closest': away, 'near': None, 'from': here, 'aimed': away,
                    'end_hero': away, 'end_friend': FAR,
                }  # fmt: skip
                owners[flight.kind] += 1
            track['last'] = moment.index
            track['closest'] = min(track['closest'], away)
            track['aimed'] = min(track['aimed'], math.dist(flight.at, track['from']))
            track['end_hero'] = away
            track['end_friend'] = min((math.dist(flight.at, friend) for friend in friends), default=FAR)
            if track['near'] is None and away <= 2 * MISSILE_REACH:
                track['near'] = moment.index
        crowd = [m for m in moment.foes if math.dist(m.at, here) <= CROWD]
        shot_at = any(f.hostile and math.dist(f.at, here) <= CROWD for f in moment.flying)
        struck = set()
        for monster in moment.foes:
            away = math.dist(monster.at, here)
            if away >= FAR:
                continue
            key = key_of(monster.txt, monster.flags)
            near[key][int(away / BIN)] += step
            shoots = ranged_type(monster.txt) or monster.unit in shooters
            seen = clear(moment, monster.unit, monster.at, here) if shoots else None
            if shoots and seen is not False:
                sight[key][int(away / BIN)] += step
            aim = moment.aims.get(monster.unit)
            if aim is not None and away <= AWARE:
                beside = min((math.dist(monster.at, friend) for friend in friends), default=None)
                nearer = 'alone' if beside is None else (HERO if away <= beside else FRIEND)
                targets[key][f'{nearer}>{aim}'] += step
                target_units[key].add((monster.unit, f'{nearer}>{aim}'))
            if monster.mode not in ATTACK_MODES:
                continue
            struck.add(monster.unit)
            run = open_runs.get(monster.unit)
            if run is not None and run['mode'] == monster.mode and run['last'] == moment.index - 1:
                run['last'] = moment.index
                continue
            if run is not None:
                runs.append(run)
            open_runs[monster.unit] = {
                'unit': monster.unit, 'txt': monster.txt, 'flags': monster.flags, 'mode': monster.mode,
                'start': moment.index, 'last': moment.index, 'away': round(away, 1), 'aim': aim,
                'alone': int(not shot_at and all(m.unit == monster.unit for m in crowd)),
                'clear': seen if shoots else clear(moment, monster.unit, monster.at, here),
            }  # fmt: skip
        for unit in [unit for unit in open_runs if unit not in struck]:
            runs.append(open_runs.pop(unit))
    runs += open_runs.values()

    frames = [row['frame'] for row in rows]
    flights: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for track in tracks.values():
        if track['kind'] == FOE:
            flights[track['owner']].append(track)

    def drops(first: int, last: int) -> Sequence[Mapping[str, Any]]:
        """The rows whose frame is in first..last."""
        return rows[bisect.bisect_left(frames, first) : bisect.bisect_right(frames, last)]

    def motion(first: int, last: int) -> tuple[float, int]:
        """How far the character was at frame `last` from where it was at `first`, and whether a
        single step between was a jump."""
        walked = [place for place in places[first : last + 1] if place is not None]
        if len(walked) < 2:
            return 0.0, 0
        jumped = any(math.dist(a, b) > JUMP for a, b in itertools.pairwise(walked))
        return round(math.dist(walked[0], walked[-1]), 1), int(jumped)

    swings = []
    for run in runs:
        unit, first, last = run['unit'], run['start'], run['last']
        window = drops(first + 1, last + HIT_AFTER)
        mine = [row for row in window if row['class'] in (SOLE_MELEE, SOLE_RANGED) and row['by'][0]['unit'] == unit]
        shared = [row for row in window if row['class'] == SEVERAL and any(s['unit'] == unit for s in row['by'])]
        fired = [track for track in flights.get(unit, ()) if first <= track['first'] <= last + HIT_AFTER]
        arrived = [track for track in fired if track['closest'] <= MISSILE_REACH]
        end = max((track['last'] for track in arrived), default=last) + HIT_AFTER
        flown = drops(min((track['near'] or track['last'] for track in arrived), default=end + 1), end)
        moved, jumped = motion(first, min(end, len(places) - 1))
        swings.append(
            {
                'txt': run['txt'],
                'rank': rank_of(run['flags']),
                'mode': run['mode'],
                'frames': last - first + 1,
                'away': run['away'],
                'aim': run['aim'],
                'alone': run['alone'],
                'clear': run['clear'],
                'any_n': len(window),
                'sole_n': len(mine),
                'sole_points': sum(row['lost'] for row in mine),
                'shared_n': len(shared),
                'shared_points': round(sum(row['lost'] / len(row['by']) for row in shared), 1),
                'fired': len(fired),
                'at_hero': int(any(track['aimed'] <= MISSILE_REACH for track in fired)),
                'on_hero': int(any(ended_on(track) == HERO for track in fired)),
                'on_friend': int(any(ended_on(track) == FRIEND for track in fired)),
                'arrived': int(bool(arrived)),
                'hit_any': int(bool(flown)),
                'hit_sole': int(any(row['class'] == SOLE_RANGED and row['by'][0]['unit'] == unit for row in flown)),
                'hit_points': sum(
                    row['lost'] for row in flown if row['class'] == SOLE_RANGED and row['by'][0]['unit'] == unit
                ),
                'moved': moved,
                'jumped': jumped,
                'level': roster.stat(unit, LEVEL_STAT),
                'tier': roster.stat(unit, HERALD_TIER_STAT),
            }
        )

    fallen = []
    for index, monster in deaths(moments):
        place = places[index] if index < len(places) else None
        if place is None or math.dist(monster.at, place) > DEATH_REACH:
            continue
        after, before = drops(index, index + NOVA_FRAMES), drops(index - NOVA_FRAMES, index - 1)
        fallen.append(
            {
                'txt': monster.txt,
                'rank': rank_of(monster.flags),
                'mods': roster.mods(monster.unit),
                'away': round(math.dist(monster.at, place), 2),
                'after_n': len(after),
                'after_points': sum(row['lost'] for row in after),
                'after_top': max((row['lost'] for row in after), default=0),
                'before_n': len(before),
                'before_points': sum(row['lost'] for row in before),
                'nova_points': sum(
                    row['lost']
                    for row in drops(index - HIT_AFTER, index + 2 * NOVA_FRAMES)
                    if row['class'] == NOVA and row['by'][0]['unit'] == monster.unit
                ),
                'missiles': sorted(
                    {
                        t['txt']
                        for t in flights.get(monster.unit, ())
                        if index - HIT_AFTER <= t['first'] <= index + BIRTH
                    }
                ),
            }
        )
    return {
        'take': take_name,
        'seconds': round(seconds, 2),
        'frames': len(moments),
        'paths': int(any(m.aims for m in moments)),
        'near': {key: [round(v, 2) for v in found] for key, found in near.items()},
        'sight': {key: [round(v, 2) for v in found] for key, found in sight.items()},
        'swings': swings,
        'targets': {key: {cell: round(v, 2) for cell, v in found.items()} for key, found in targets.items()},
        'target_units': {key: dict(Counter(cell for _unit, cell in found)) for key, found in target_units.items()},
        'deaths': fallen,
        'owners': dict(owners),
        'sighted': int(ground is not None),
    }


# ---------------------------------------------------------------------------------------------------
# What a set of takes measures.


def quantile(values: Sequence[float], share: float) -> float | None:
    """The value at `share` of the sorted values (nearest rank); None of nothing."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(share * len(ordered)) - 1))]


def spread(values: Sequence[float]) -> dict[str, Any]:
    return {
        'n': len(values),
        'p50': quantile(values, 0.5),
        'p90': quantile(values, 0.9),
        'p99': quantile(values, 0.99),
        'max': max(values, default=None),
    }


def ratio(part: float, whole: float, digits: int = 3) -> float | None:
    return round(part / whole, digits) if whole else None


def within(bins: Sequence[float], reach: float) -> float:
    """Seconds in the bins nearer than `reach` (whole bins: the reach is rounded up to one)."""
    return sum(bins[: min(len(bins), math.ceil(reach / BIN))])


def merged(tallies: Iterable[Mapping[str, Any]], part: str) -> dict[str, list[float]]:
    """The bins of `part` ('near' or 'sight') summed over the tallies, by type and rank."""
    found: dict[str, list[float]] = {}
    for one in tallies:
        for key, bins in one[part].items():
            kept = found.setdefault(key, [0.0] * len(bins))
            for index, value in enumerate(bins):
                kept[index] += value
    return found


def by_type(bins: Mapping[str, Sequence[float]]) -> dict[int, list[float]]:
    """Bins by type and rank summed to the type."""
    found: dict[int, list[float]] = {}
    for key, values in bins.items():
        kept = found.setdefault(int(key.split('|')[0]), [0.0] * len(values))
        for index, value in enumerate(values):
            kept[index] += value
    return found


def usual_frames(swings: Sequence[Mapping[str, Any]]) -> dict[tuple[int, int], int]:
    """The usual length in frames of a run of each type in each attack mode: the commonest length of
    its runs of 5 frames or more, where 10 or more runs have it. A Blood Clan's (55) attack 1 runs
    are 20 frames 113 times of about 520 and 40 frames 10 times: one swing and two."""
    lengths: dict[tuple[int, int], Counter[int]] = defaultdict(Counter)
    for swing in swings:
        if swing['frames'] >= 5:
            lengths[swing['txt'], swing['mode']][swing['frames']] += 1
    found = {}
    for key, counts in lengths.items():
        length, times = counts.most_common(1)[0]
        if times >= 10:
            found[key] = length
    return found


def swing_count(swing: Mapping[str, Any], usual: Mapping[tuple[int, int], int]) -> int:
    """How many swings a run is: its length over the type's usual one, one at least."""
    length = usual.get((swing['txt'], swing['mode']))
    return max(1, round(swing['frames'] / length)) if length else 1


def composition(row: Mapping[str, Any]) -> str:
    """What the suspects of a `several` drop are: 'swings of one type', 'swings of several types',
    'swings and missiles', 'missiles of several', or one of those 'with a death' (a death's missile
    among them)."""
    vias = {s['via'] for s in row['by']}
    types = {s['txt'] for s in row['by']}
    if vias == {SWING}:
        found = 'swings of one type' if len(types) == 1 else 'swings of several types'
    elif SWING in vias:
        found = 'swings and missiles'
    else:
        found = 'missiles of several'
    if len(row['by']) < 2:
        found = 'one suspect and a missile nobody owns'
    return found + (' with a death' if DEATH_MISSILE in vias else '')


TICK = (0.3, 0.5)  # seconds between two drops of a run of damage over time (the takes show 0.4)
# The share of the most life of a drop that recurs with nothing hostile near: 35 points of 1,778 or
# 1,783 in 107 drops, a third of them in the first five seconds of a take.
SELF = (0.019, 0.021)
SIZES = (5, 10, 20, 30, 40, 100)  # points: the edges of the size bands of the drops nobody is blamed for


def ticking(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The rows that have another of `rows` in the same take TICK seconds before or after: poison or
    burning comes off the life in such runs (20261011T085301Z-124: 5, 10 and 11 points every 0.4 s
    for half a minute with nothing hostile near)."""
    found = []
    ordered = sorted(rows, key=lambda row: (row['take'], row['t']))
    for index, row in enumerate(ordered):
        beside = [ordered[at] for at in (index - 1, index + 1) if 0 <= at < len(ordered)]
        if any(o['take'] == row['take'] and TICK[0] <= abs(o['t'] - row['t']) <= TICK[1] for o in beside):
            found.append(row)
    return found


def classes(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The drops by class: count, points and their shares; and what the classes are made of."""
    total_n, total_points = len(rows), sum(row['lost'] for row in rows)
    found: dict[str, Any] = {'n': total_n, 'points': total_points, 'deaths': sum(row['dead'] for row in rows)}

    def part(mine: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        points = sum(row['lost'] for row in mine)
        return {
            'n': len(mine),
            'points': points,
            'n_share': ratio(len(mine), total_n),
            'points_share': ratio(points, total_points),
            'p50': quantile([row['lost'] for row in mine], 0.5),
            'max': max((row['lost'] for row in mine), default=None),
        }

    for name in CLASSES:
        found[name] = part([row for row in rows if row['class'] == name])
    sole = [r for r in rows if r['class'] == SOLE_MELEE]
    shot = [r for r in rows if r['class'] == SOLE_RANGED]
    nova = [r for r in rows if r['class'] == NOVA]
    none = [r for r in rows if r['class'] == NONE]
    found['parts'] = {
        'sole melee, beside the character': part([r for r in sole if r['by'][0]['away'] <= BESIDE]),
        'sole melee, further off and aimed at it': part([r for r in sole if r['by'][0]['away'] > BESIDE]),
        'sole melee of a ranged type, further off': part(
            [r for r in sole if r['by'][0]['away'] > BESIDE and ranged_type(r['by'][0]['txt'])]
        ),
        'sole ranged, a missile within reach': part([r for r in shot if not all(m[3] for m in r['missiles'])]),
        'sole ranged, by an ended missile only': part([r for r in shot if all(m[3] for m in r['missiles'])]),
        "nova, a dead one's missile near": part([r for r in nova if r['by'][0]['via'] == DEATH_MISSILE]),
        'nova, an enchanted death nearby and no missile': part([r for r in nova if r['by'][0]['via'] != DEATH_MISSILE]),
        'unknown, nothing hostile within 8 units': part([r for r in none if not r['foes_near']]),
        'unknown, hostiles near but none striking near': part(
            [r for r in none if r['foes_near'] and (r['nearest_striking'] is None or r['nearest_striking'] > BESIDE)]
        ),
        'unknown, one striking beside (a missile nobody owns near)': part(
            [r for r in none if r['nearest_striking'] is not None and r['nearest_striking'] <= BESIDE]
        ),
        'unknown, over a pause of the recorder': part([r for r in none if r['gap'] > GAP]),
        f'unknown, one of a run of drops {TICK[0]:g} to {TICK[1]:g} s apart (damage over time)': part(ticking(none)),
        f'unknown, {SELF[0]:.1%} to {SELF[1]:.1%} of the most life (a fixed cost: see the text)': part(
            [r for r in none if r['share'] is not None and SELF[0] <= r['share'] <= SELF[1]]
        ),
        'unknown, with a plain death nearby just before': part([r for r in none if r.get('death_near')]),
        'unknown, with a plain death nearby a second earlier': part([r for r in none if r.get('death_control')]),
    }
    several = [r for r in rows if r['class'] == SEVERAL]
    found['several_of'] = {
        kind: part([r for r in several if composition(r) == kind]) for kind in sorted({composition(r) for r in several})
    }
    found['unknown_hero_modes'] = dict(Counter(str(r['hero_mode']) for r in none).most_common())
    found['unknown_sizes'] = {
        f'{low} to {high - 1}' if high else f'{low} and over': part(
            [r for r in none if r['lost'] >= low and (not high or r['lost'] < high)]
        )
        for low, high in zip(SIZES, (*SIZES[1:], 0), strict=True)
    }
    return found


def idle_types(tallies: Sequence[Mapping[str, Any]]) -> set[int]:
    """The types that stood within MODEL_REACH of the character for ENOUGH_SECONDS or more and swung
    less than once in IDLE seconds there: not fighters, and left out of the pooled figures."""
    near = by_type(merged(tallies, 'near'))
    swung: Counter[int] = Counter(s['txt'] for one in tallies for s in one['swings'] if s['away'] <= MODEL_REACH)
    return {
        txt
        for txt, bins in near.items()
        if within(bins, MODEL_REACH) >= ENOUGH_SECONDS and swung[txt] * IDLE < within(bins, MODEL_REACH)
    }


def melee_type(txt: int) -> bool:
    """A type the takes show striking by hand: not one the threat table calls ranged."""
    return not ranged_type(txt)


def reach(rows: Sequence[Mapping[str, Any]], swings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """How far a melee blow comes from: the distance of the sole striker at `sole melee` drops of types
    the threat table does not call ranged, pooled, by rank and per type; and beside it the distance
    at which swings aimed at the character begin (no attribution in it)."""
    sole = [r['by'][0] for r in rows if r['class'] == SOLE_MELEE and melee_type(r['by'][0]['txt'])]
    begun = [s for s in swings if s['aim'] == HERO and melee_type(s['txt']) and not s['fired']]
    found: dict[str, Any] = {
        'pooled': {'blows': spread([s['away'] for s in sole]), 'swings': spread([s['away'] for s in begun])},
        'ranks': {},
        'types': {},
    }
    for rank in sorted({s['rank'] for s in sole}):
        found['ranks'][rank] = spread([s['away'] for s in sole if s['rank'] == rank])
    for txt in sorted({s['txt'] for s in sole}):
        found['types'][str(txt)] = {
            'name': name_of(txt),
            'blows': spread([s['away'] for s in sole if s['txt'] == txt]),
            'swings': spread([s['away'] for s in begun if s['txt'] == txt]),
        }
    return found


def reach_of(found: Mapping[str, Any], txt: int) -> tuple[float, str]:
    """The reach to count a type's time within: the 90th percentile of its sole blows' distances with
    ENOUGH_BLOWS of them, else the pooled one; and which it was."""
    own = found['types'].get(str(txt), {}).get('blows')
    if own and own['n'] >= ENOUGH_BLOWS:
        return own['p90'], 'own'
    return found['pooled']['blows']['p90'] or 0.0, 'pooled'


def swing_stats(mine: Sequence[Mapping[str, Any]], usual: Mapping[tuple[int, int], int]) -> dict[str, Any]:
    """What a set of attack runs says: how many swings, how many at the character, how many cut short
    before the middle of the type's usual length (no blow can have landed: hit recovery, death), and
    of the whole swings at the character how many took life: `hit_low` by the drops put on that
    monster alone, `hit_high` with the drops it shares with others, `alone_hit` by any drop where
    nothing else hostile was near; the same for the swings the character stood still through."""

    def count(found: Iterable[Mapping[str, Any]]) -> int:
        return sum(swing_count(s, usual) for s in found)

    def whole(swing: Mapping[str, Any]) -> bool:
        length = usual.get((swing['txt'], swing['mode']))
        return length is None or swing['frames'] >= length / 2

    def hits(found: Sequence[Mapping[str, Any]], *parts: str) -> int:
        return sum(min(sum(s[part] for part in parts), swing_count(s, usual)) for s in found)

    known = [s for s in mine if s['aim'] is not None]
    aimed = [s for s in known if s['aim'] == HERO]
    full = [s for s in aimed if whole(s)]
    alone = [s for s in full if s['alone']]
    stood = [s for s in full if motion_of(s) == 'stood']
    return {
        'runs': len(mine),
        'swings': count(mine),
        'cut_short': sum(not whole(s) for s in mine),
        'cut_share': ratio(sum(not whole(s) for s in mine), len(mine)),
        'aim_known': len(known),
        'aimed': len(aimed),
        'aimed_share': ratio(len(aimed), len(known)),
        'whole_aimed': count(full),
        'hits_sole': hits(full, 'sole_n'),
        'hits_shared': hits(full, 'shared_n'),
        'hit_low': ratio(hits(full, 'sole_n'), count(full)),
        'hit_high': ratio(hits(full, 'sole_n', 'shared_n'), count(full)),
        'alone': count(alone),
        'alone_hit': ratio(hits(alone, 'any_n'), count(alone)),
        'stood': count(stood),
        'stood_hit_low': ratio(hits(stood, 'sole_n'), count(stood)),
        'stood_hit_high': ratio(hits(stood, 'sole_n', 'shared_n'), count(stood)),
        'left': count([s for s in full if motion_of(s) != 'stood']),
        'left_hit_high': ratio(
            hits([s for s in full if motion_of(s) != 'stood'], 'sole_n', 'shared_n'),
            count([s for s in full if motion_of(s) != 'stood']),
        ),
    }


def melee(
    rows: Sequence[Mapping[str, Any]],
    tallies: Sequence[Mapping[str, Any]],
    reaches: Mapping[str, Any],
    by_rank: bool = False,
) -> dict[str, Any]:
    """Per type (or type and rank), and pooled over all melee types under 'all': the time within
    MODEL_REACH of the character (where the reach curve has the swings begun at their full rate, and
    where the model's monsters strike), the swings begun there (`swing_stats`), the same for the
    `tail` between that and the type's measured reach (`reach_of`), and the life the type's swings
    took per second within MODEL_REACH: by the drops put on one monster of the type alone (`low`),
    with the drops whose suspects are all swings of the type (`same`), and with an even share of the
    mixed ones (`high`)."""
    swings = [s for one in tallies for s in one['swings'] if melee_type(s['txt'])]
    usual = usual_frames(swings)
    near = {key: bins for key, bins in merged(tallies, 'near').items() if melee_type(int(key.split('|')[0]))}
    bins: dict[Any, list[float]] = dict(near) if by_rank else dict(by_type(near))
    struck: dict[tuple[int, str | None], list[Mapping[str, Any]]] = defaultdict(list)
    for swing in swings:
        struck[swing['txt'], swing['rank'] if by_rank else None].append(swing)
    sole: dict[tuple[int, str | None], list[int]] = defaultdict(list)
    same: Counter[tuple[int, str | None]] = Counter()
    mixed: Counter[tuple[int, str | None]] = Counter()
    for row in rows:
        if row['class'] == SOLE_MELEE:
            suspect = row['by'][0]
            sole[suspect['txt'], suspect['rank'] if by_rank else None].append(row['lost'])
        elif row['class'] == SEVERAL:
            keys = {(s['txt'], s['rank'] if by_rank else None) for s in row['by']}
            if len(keys) == 1 and all(s['via'] == SWING for s in row['by']):
                same[next(iter(keys))] += row['lost']
                continue
            for suspect in row['by']:
                if suspect['via'] == SWING:
                    mixed[suspect['txt'], suspect['rank'] if by_rank else None] += row['lost'] / len(row['by'])
    found = {}
    idle = idle_types(tallies)
    pooled_seconds = pooled_tail = 0.0
    pooled: list[Mapping[str, Any]] = []
    for key, values in bins.items():
        txt = int(str(key).split('|')[0])
        rank = str(key).split('|')[1] if by_rank else None
        limit, source = reach_of(reaches, txt)
        limit = max(limit, MODEL_REACH)
        seconds = within(values, MODEL_REACH)
        beyond = within(values, limit) - seconds
        mine = [s for s in struck.get((txt, rank), ()) if s['away'] <= MODEL_REACH]
        tail = swing_stats([s for s in struck.get((txt, rank), ()) if MODEL_REACH < s['away'] <= limit], usual)
        blows = sole.get((txt, rank), [])
        low, middle = sum(blows), sum(blows) + same[txt, rank]
        stats = swing_stats(mine, usual)
        if txt not in idle:
            pooled_seconds += seconds
            pooled_tail += beyond
            pooled += mine
        found[str(key)] = {
            'txt': txt,
            'name': name_of(txt),
            'rank': rank,
            'seconds': round(seconds, 1),
            **stats,
            'swings_per_second': ratio(stats['swings'], seconds),
            'reach': limit,
            'reach_from': source,
            'tail_seconds': round(beyond, 1),
            'tail_swings': tail['swings'],
            'tail_swings_per_second': ratio(tail['swings'], beyond),
            'tail_whole_aimed': tail['whole_aimed'],
            'tail_hit_low': tail['hit_low'],
            'tail_hit_high': tail['hit_high'],
            'usual_frames': {str(mode): n for (kind, mode), n in sorted(usual.items()) if kind == txt},
            'blows': len(blows),
            'blow': spread(blows),
            'points_sole': low,
            'points_same_type': same[txt, rank],
            'points_mixed_share': round(mixed[txt, rank]),
            'points_per_second_low': ratio(low, seconds, 2),
            'points_per_second_same': ratio(middle, seconds, 2),
            'points_per_second_high': ratio(middle + mixed[txt, rank], seconds, 2),
            'level': quantile([s['level'] for s in struck.get((txt, rank), ()) if s['level']], 0.5),
        }
    if not by_rank:
        stats = swing_stats(pooled, usual)
        low, middle = sum(sum(blows) for blows in sole.values()), sum(same.values())
        found['all'] = {
            'name': 'all melee types',
            'left_out': sorted(idle),
            'seconds': round(pooled_seconds, 1),
            'tail_seconds': round(pooled_tail, 1),
            **stats,
            'swings_per_second': ratio(stats['swings'], pooled_seconds),
            'blows': sum(len(blows) for blows in sole.values()),
            'points_sole': low,
            'points_same_type': middle,
            'points_mixed_share': round(sum(mixed.values())),
            'points_per_second_low': ratio(low, pooled_seconds, 2),
            'points_per_second_same': ratio(low + middle, pooled_seconds, 2),
            'points_per_second_high': ratio(low + middle + sum(mixed.values()), pooled_seconds, 2),
        }
    return found


CURVE = (0.0, 2.0, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 12.0, 20.0)  # units: the edges of the reach curve's bands


def reach_curve(tallies: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Over all melee types, by the distance a swing began at: the seconds hostiles stood there, the
    swings begun, and of the whole swings at the character how many took life. Where the hits end is
    the reach, with no blow put on anybody by hand."""
    idle = idle_types(tallies)
    swings = [s for one in tallies for s in one['swings'] if melee_type(s['txt']) and s['txt'] not in idle]
    usual = usual_frames(swings)
    near = [bins for txt, bins in by_type(merged(tallies, 'near')).items() if melee_type(txt) and txt not in idle]
    found = []
    for low, high in itertools.pairwise(CURVE):
        seconds = sum(within(bins, high) - within(bins, low) for bins in near)
        stats = swing_stats([s for s in swings if low <= s['away'] < high], usual)
        found.append(
            {
                'from': low,
                'to': high,
                'seconds': round(seconds, 1),
                'swings': stats['swings'],
                'swings_per_second': ratio(stats['swings'], seconds),
                'aimed_share': stats['aimed_share'],
                'whole_aimed': stats['whole_aimed'],
                'hit_low': stats['hit_low'],
                'hit_high': stats['hit_high'],
                'alone': stats['alone'],
                'alone_hit': stats['alone_hit'],
            }
        )
    return found


def motion_of(swing: Mapping[str, Any]) -> str:
    if swing['jumped']:
        return 'jumped'
    return 'moved' if swing['moved'] >= MOVED else 'stood'


def shot_stats(shots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Of a set of shots: how many flew at where the character stood when they were let go
    (`at_hero`: a companion beside it draws the same missiles), how many ended on the character and
    how many on a companion (`ended_on`), and how many took life: `low` by the drops put on that
    shooter alone, `high` by any drop while its missile was near; of the shots that ended on the
    character (`took_*`) and of all (`hit_per_shot_*`)."""
    at_hero = [s for s in shots if s['at_hero']]
    on_hero = [s for s in shots if s['on_hero']]
    return {
        'shots': len(shots),
        'at_hero': len(at_hero),
        'at_hero_share': ratio(len(at_hero), len(shots)),
        'on_hero': len(on_hero),
        'on_hero_share': ratio(len(on_hero), len(shots)),
        'on_friend': sum(s['on_friend'] and not s['on_hero'] for s in shots),
        'on_friend_share': ratio(sum(s['on_friend'] and not s['on_hero'] for s in shots), len(shots)),
        'at_hero_on_hero_share': ratio(sum(s['on_hero'] for s in at_hero), len(at_hero)),
        'arrived': sum(s['arrived'] for s in at_hero),
        'hits_sole': sum(s['hit_sole'] for s in on_hero),
        'hits_any': sum(s['hit_any'] for s in on_hero),
        'took_low': ratio(sum(s['hit_sole'] for s in on_hero), len(on_hero)),
        'took_high': ratio(sum(s['hit_any'] for s in on_hero), len(on_hero)),
        'hit_per_shot_low': ratio(sum(s['hit_sole'] for s in shots), len(shots)),
        'hit_per_shot_high': ratio(sum(s['hit_any'] for s in shots), len(shots)),
    }


def ranged(rows: Sequence[Mapping[str, Any]], tallies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Per type that let hostile missiles go in an attack mode, and pooled under 'all': the time in
    sight within the arena's reach, the shots (runs that let a missile go) and from how far, how many
    flew at the character, reached it and took life, standing against moving, and what a hit took."""
    swings = [s for one in tallies for s in one['swings']]
    usual = usual_frames(swings)
    sight, near = by_type(merged(tallies, 'sight')), by_type(merged(tallies, 'near'))
    runs: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for swing in swings:
        runs[swing['txt']].append(swing)
    hits: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    shared: Counter[int] = Counter()
    for row in rows:
        if row['class'] == SOLE_RANGED:
            hits[row['by'][0]['txt']].append(row)
        elif row['class'] == SEVERAL:
            for suspect in row['by']:
                if suspect['via'] == MISSILE:
                    shared[suspect['txt']] += row['lost'] / len(row['by'])

    def entry(mine: Sequence[Mapping[str, Any]], seconds: float, sole: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        shots = [s for s in mine if s['fired']]
        inside = [s for s in shots if s['away'] <= RANGED_REACH and s['clear'] is not False]
        known = [s for s in shots if s['aim'] is not None]
        return {
            'seconds_in_sight': round(seconds, 1),
            'attack_runs': len(mine),
            'runs_without_missile': len(mine) - len(shots),
            'shots_in_sight': len(inside),
            'shots_per_second': ratio(len(inside), seconds),
            'blocked_shots': sum(s['clear'] is False for s in shots),
            'path_aim_known': len(known),
            'path_aim_hero_share': ratio(sum(s['aim'] == HERO for s in known), len(known)),
            **shot_stats(shots),
            'shot_from': spread([s['away'] for s in shots if s['at_hero']]),
            'motion': {kind: shot_stats([s for s in shots if motion_of(s) == kind]) for kind in MOTIONS},
            'hits': len(sole),
            'hit': spread([r['lost'] for r in sole]),
            'hit_from': spread([r['by'][0]['away'] for r in sole]),
            'points_sole': sum(r['lost'] for r in sole),
        }

    found = {}
    for txt in sorted(txt for txt, mine in runs.items() if any(s['fired'] for s in mine)):
        seconds = within(sight.get(txt, ()), RANGED_REACH)
        found[str(txt)] = {
            'txt': txt,
            'name': name_of(txt),
            'table_ranged': ranged_type(txt),
            'seconds_within': round(within(near.get(txt, ()), RANGED_REACH), 1),
            **entry(runs[txt], seconds, hits.get(txt, ())),
            'usual_frames': {str(mode): n for (kind, mode), n in sorted(usual.items()) if kind == txt},
            'missiles': dict(Counter(str(r['by'][0]['missile']) for r in hits.get(txt, ())).most_common(4)),
            'points_shared': round(shared[txt]),
            'points_per_second_low': ratio(sum(r['lost'] for r in hits.get(txt, ())), seconds, 2),
            'points_per_second_high': ratio(sum(r['lost'] for r in hits.get(txt, ())) + shared[txt], seconds, 2),
            'level': quantile([s['level'] for s in runs[txt] if s['fired'] and s['level']], 0.5),
        }
    table = [txt for txt in runs if ranged_type(txt)]
    found['all'] = {
        'name': "all types the threat table calls ranged (the arena's shooters)",
        **entry(
            [s for txt in table for s in runs[txt]],
            sum(within(sight.get(txt, ()), RANGED_REACH) for txt in table),
            [r for txt in table for r in hits.get(txt, ())],
        ),
        'points_shared': round(sum(shared[txt] for txt in table)),
    }
    return found


def targets(tallies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Whom a hostile within AWARE of the character was after, by who was nearer to it: seconds and
    the count of units (a unit counts once per cell and take), pooled and per type."""
    seconds: dict[int, Counter[str]] = defaultdict(Counter)
    units: dict[int, Counter[str]] = defaultdict(Counter)
    for one in tallies:
        for key, cells in one['targets'].items():
            seconds[int(key.split('|')[0])].update(cells)
        for key, cells in one['target_units'].items():
            units[int(key.split('|')[0])].update(cells)

    def table(time: Mapping[str, float], count: Mapping[str, int]) -> dict[str, Any]:
        found: dict[str, Any] = {}
        for nearer in (HERO, FRIEND, 'alone'):
            cells = {aim: time.get(f'{nearer}>{aim}', 0.0) for aim in (HERO, FRIEND, OTHER, NOBODY)}
            chosen = cells[HERO] + cells[FRIEND]
            found[nearer] = {
                'seconds': {aim: round(value, 1) for aim, value in cells.items()},
                'units': {aim: count.get(f'{nearer}>{aim}', 0) for aim in (HERO, FRIEND, OTHER, NOBODY)},
                'hero_share': ratio(cells[HERO], chosen),
            }
        return found

    pooled_time: Counter[str] = Counter()
    pooled_units: Counter[str] = Counter()
    for txt in seconds:
        pooled_time.update(seconds[txt])
        pooled_units.update(units[txt])
    return {
        'pooled': table(pooled_time, pooled_units),
        'types': {str(txt): {'name': name_of(txt), **table(seconds[txt], units[txt])} for txt in sorted(seconds)},
    }


def big(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Single drops put on one monster, by its rank and its Herald's tier: how large and from how far."""
    sole = [r for r in rows if r['class'] in (SOLE_MELEE, SOLE_RANGED)]
    found = {}
    for key in sorted({(r['by'][0]['rank'], r['by'][0]['tier'], r['class']) for r in sole}):
        mine = [r for r in sole if (r['by'][0]['rank'], r['by'][0]['tier'], r['class']) == key]
        found['|'.join(str(part) for part in key)] = {
            'rank': key[0],
            'tier': key[1],
            'class': key[2],
            'drop': spread([r['lost'] for r in mine]),
            'share': spread([r['share'] for r in mine if r['share'] is not None]),
            'away': spread([r['by'][0]['away'] for r in mine]),
            'deaths': sum(r['dead'] for r in mine),
        }
    return found


ELITE = ('champion', 'unique', 'super unique')  # blows.py's ranks that lead a pack or are champions


def standing(rank: str) -> str:
    return 'elite' if rank in ELITE else rank


def enchantment(mods: Sequence[int] | None) -> str:
    """The group a death is counted in by what the dying monster carried (monumod ids as hurts.py
    names them: 9 fire, 18 cold, 17 lightning)."""
    if mods is None:
        return 'not known'
    names = [name for mod, name in ((18, 'cold'), (9, 'fire'), (17, 'lightning')) if mod in mods]
    return ' + '.join(names) if names else 'none'


def novas(rows: Sequence[Mapping[str, Any]], tallies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deaths of hostiles near the character by what the dead one carried: how many were followed by
    a drop within blows.NOVA_FRAMES (and, the control, preceded by one), by distance; and the drops
    of class `nova/explosion` by the missile that was near."""
    fallen = [d for one in tallies for d in one['deaths']]
    found: dict[str, Any] = {'deaths': {}, 'drops': {}}
    bands = (('0-4', 0.0, 4.0), ('4-8', 4.0, 8.0), ('8-12', 8.0, 12.0), ('12-20', 12.0, DEATH_REACH + 0.01))
    for group in sorted({(enchantment(d['mods']), standing(d['rank'])) for d in fallen}):
        for label, low, high in bands:
            mine = [
                d for d in fallen if (enchantment(d['mods']), standing(d['rank'])) == group and low <= d['away'] < high
            ]
            if not mine:
                continue
            found['deaths']['|'.join((*group, label))] = {
                'group': group[0],
                'rank': group[1],
                'away': label,
                'n': len(mine),
                'with_missile': sum(bool(d['missiles']) for d in mine),
                'missiles': dict(Counter(str(m) for d in mine for m in d['missiles']).most_common(3)),
                'after_share': ratio(sum(d['after_n'] > 0 for d in mine), len(mine)),
                'before_share': ratio(sum(d['before_n'] > 0 for d in mine), len(mine)),
                'after_points': sum(d['after_points'] for d in mine),
                'before_points': sum(d['before_points'] for d in mine),
                'nova_n': sum(d['nova_points'] > 0 for d in mine),
                'nova_points': sum(d['nova_points'] for d in mine),
                'nova_top': max((d['nova_points'] for d in mine), default=0),
            }
    for row in rows:
        if row['class'] != NOVA:
            continue
        suspect = row['by'][0]
        key = f'{suspect["missile"] or suspect["via"]}|{enchantment(suspect["mods"])}'
        found['drops'].setdefault(key, []).append((row['lost'], suspect['away']))
    found['drops'] = {
        key: {'drop': spread([lost for lost, _a in pairs]), 'away': spread([away for _l, away in pairs])}
        for key, pairs in sorted(found['drops'].items())
    }
    return found


def coverage(tallies: Sequence[Mapping[str, Any]], most: int = 20) -> list[dict[str, Any]]:
    """The types by time within MODEL_REACH of the character, the `most` longest: what the takes are of."""
    near = by_type(merged(tallies, 'near'))
    found = [
        {
            'txt': txt,
            'name': name_of(txt),
            'ranged': ranged_type(txt),
            'seconds_in_reach': round(within(bins, MODEL_REACH), 1),
            'seconds_within_12': round(within(bins, 12.0), 1),
            'seconds_within_30': round(within(bins, RANGED_REACH), 1),
        }
        for txt, bins in near.items()
    ]
    return sorted(found, key=lambda row: -row['seconds_in_reach'])[:most]


def measure(
    rows: Sequence[Mapping[str, Any]],
    tallies: Sequence[Mapping[str, Any]],
    reaches: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Everything a set of takes measures (the rows and tallies of those takes only). `reaches`: the
    reach measure of another set to count the tails by (the check half is counted with the train
    half's reaches); the set's own is reported either way."""
    swings = [s for one in tallies for s in one['swings']]
    own = reach(rows, swings)
    reaches = own if reaches is None else reaches
    return {
        'takes': len(tallies),
        'seconds': round(sum(one['seconds'] for one in tallies), 1),
        'takes_with_paths': sum(one['paths'] for one in tallies),
        'takes_with_ground': sum(one['sighted'] for one in tallies),
        'missile_owners': dict(sum((Counter(one['owners']) for one in tallies), Counter())),
        'classes': classes(rows),
        'reach': own,
        'reach_curve': reach_curve(tallies),
        'melee': melee(rows, tallies, reaches),
        'melee_by_rank': melee(rows, tallies, reaches, by_rank=True),
        'ranged': ranged(rows, tallies),
        'targets': targets(tallies),
        'big': big(rows),
        'novas': novas(rows, tallies),
        'coverage': coverage(tallies),
        'time_per_frame': 1 / GAME_RATE,
    }
