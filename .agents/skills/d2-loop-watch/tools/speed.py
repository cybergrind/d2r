"""Where the KP_6 loop's time goes, and whether a change made it faster.

Run with the repo's Python (it reads the combat takes):
`uv run --offline python .agents/skills/d2-loop-watch/tools/speed.py`.

A window is a stretch of local clock time (`--since`, `--until`; default the last 2 hours). For it:

1. **Games** (serve's probe.logs, `games.py`): the median game and each leg's median: the town's legs are the same
   work every game, so a leg over its floor is time to win.
2. **The level** (the Lower Kurast takes, `runs/combat/<UTC>-79`, read by `inventory_tracking.takes.legs`): per stay
   the seconds, chests and other containers, chests a minute, the split casting / moving / standing, the macro's stalls
   (standing 1.5 s and more) and the time lost against Blade Warp's pace.
3. **Where the time goes, ranked**: the stall reasons (the log lines said most in each stall, numbers folded) by their
   seconds a stay, and the worst legs. The top of this list is the next round's candidate.
4. **Inactive time and going back** (`legs.quiet`, `Leg.idle`, `Leg.away`): the seconds nothing was done (the
   character still, neither casting nor moving, no input sent) on the level and in the towns' takes (Kurast Docks,
   Pandemonium Fortress), with the town's idle stretches ranked by their log lines; and the units moved away from the
   container a leg went to (backtracking), with the legs that went back most.
0. **Cycles** (the player, 2026-10-17: "let's assume that iterations starts on LK arrival, and loop ends on the next
   LK arrival, to measure whole activities"): from one game's first `the chests` leg to the next game's, everything
   between counted (the town's legs, Cain, Jamella, the stash, repairs, the lobby, recoveries); a cycle the player
   paused (`Loop off`) or a restart of the service cut is left out. Chests a cycle from the takes started within it;
   **chests an hour of cycles** is the loop's measure, and each leg's seconds a cycle say where the time goes.
5. **Teleport charges** (the staff's, refilled by Halbu's repair on carried gold): charges spent a stay, and the
   stays with a charge against those without (stay seconds, chests a minute): what a repair's gold buys in time.

`--against SINCE UNTIL` compares the window with another (before a change): the medians' difference with a 90%
bootstrap interval for the game, the chests leg, the stay, the stalls and the chests a minute. A difference whose
interval holds 0 is no evidence either way: play more games before keeping or reverting.

    uv run --offline python .agents/skills/d2-loop-watch/tools/speed.py [--since 'YYYY-MM-DD HH:MM'] [--until ...]
        [--against 'YYYY-MM-DD HH:MM' 'YYYY-MM-DD HH:MM'] [--worst 8] [--reasons 12]
"""

import argparse
import random
import statistics
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE), str(ROOT)]

import games  # ruff: ignore[module-import-not-at-top-of-file] - the skill's own tool, beside this one
import logwords  # ruff: ignore[module-import-not-at-top-of-file] - beside this tool
from logwords import LEG, LOOP_OFF, TELEPORT, stamp  # ruff: ignore[module-import-not-at-top-of-file]

from inventory_tracking.takes.legs import (  # ruff: ignore[module-import-not-at-top-of-file]
    CHESTS,
    REFERENCE,
    clock_of,
    legs_of,
    quiet,
)
from inventory_tracking.takes.takes import Take  # ruff: ignore[module-import-not-at-top-of-file]


COMBAT = ROOT / 'inventory_tracking' / 'runs' / 'combat'
AREA = '79'  # Lower Kurast
TOWNS = {'75': 'Kurast Docks', '103': 'Pandemonium Fortress'}  # the loop's town legs' takes
DRAWS = 2000  # bootstrap resamples
MINIMUM = 8  # samples a side for a comparison


def takes_in(since: datetime, until: datetime, area: str = AREA) -> list[Path]:
    """The takes of `area` (Lower Kurast) started in the window (their directory names are UTC stamps)."""
    low = since.astimezone(UTC).strftime('%Y%m%dT%H%M%S')
    high = until.astimezone(UTC).strftime('%Y%m%dT%H%M%S')
    return sorted(d for d in COMBAT.glob(f'*-{area}') if low <= d.name.split('Z')[0] <= high)


def towns(since: datetime, until: datetime) -> list:
    """The inactive time of every town take in the window (`legs.quiet`)."""
    found = []
    for area in TOWNS:
        for path in takes_in(since, until, area):
            try:
                measured = quiet(Take.load(path))
            except (OSError, ValueError, KeyError) as error:
                print(f'  {path.name}: not read ({error})', file=sys.stderr)
                continue
            if measured is not None and not any(stretch.mine for stretch in measured.stretches):
                found.append(measured)
    return found


def stays(paths: list[Path]) -> tuple[list[dict], list[tuple]]:
    """Per stay: seconds, chests, others, split, stalls, lost; and every leg with its take (for the worst list)."""
    rows, every = [], []
    for path in paths:
        try:
            take = Take.load(path)
        except (OSError, ValueError, KeyError) as error:
            print(f'  {path.name}: not read ({error})', file=sys.stderr)
            continue
        found = legs_of(take)
        if not found:
            continue
        seconds = sum(leg.seconds for leg in found)
        chests = sum(leg.to in CHESTS for leg in found)
        stalls: dict[str, float] = defaultdict(float)
        for leg in found:
            for stall in leg.stalls:
                if not stall.mine:
                    stalls[' | '.join(stall.reasons) or '(nothing said)'] += stall.seconds
        mine = any(stall.mine for leg in found for stall in leg.stalls)
        rows.append(
            {
                'take': path.name,
                'seconds': seconds,
                'chests': chests,
                'others': sum(leg.to is not None and leg.to not in CHESTS for leg in found),
                'casting': sum(leg.casting for leg in found),
                'moving': sum(leg.moving for leg in found),
                'standing': sum(leg.standing for leg in found),
                'stalled': sum(stalls.values()),
                'stalls': dict(stalls),
                'lost': sum(leg.lost for leg in found if leg.to is not None),
                'idle': sum(leg.idle for leg in found),
                'teleports': sum(e['event'] == 'log' and TELEPORT in e.get('text', '') for e in take.events),
                'delay': sum(leg.delay for leg in found),
                'away': sum(leg.away for leg in found),
                'tail': sum(leg.seconds for leg in found if leg.to is None),
                'mine': mine,
            }
        )
        every += [(take, leg) for leg in found if leg.to is not None]
    return [row for row in rows if not row['mine']], every


def cycles(since: datetime, until: datetime, rows: list[dict]) -> list[dict]:
    """Section 0 of the module text: each cycle's start, seconds, chests and seconds by leg."""
    found: list[dict] = []
    args = argparse.Namespace(sessions=None, since=since)
    for directory in games.sessions(args):
        start: datetime | None = None
        legs: dict[str, float] = defaultdict(float)
        leg: tuple[str, datetime] | None = None
        game = None
        paused = False
        for line in (directory / 'probe.log').read_text(errors='replace').splitlines():
            at = stamp(line)
            if at is None or at < since or at > until:
                continue
            if LOOP_OFF in line:
                paused = True
            m = LEG.search(line)
            if m is None:
                continue
            if leg is not None:
                legs[leg[0]] += (at - leg[1]).total_seconds()
            number, name = m.group(1), m.group(2).strip()
            leg = (name, at)
            if name == 'the chests' and number != game:
                if start is not None and not paused:
                    found.append({'start': start, 'seconds': (at - start).total_seconds(), 'legs': dict(legs)})
                start, game, paused, legs = at, number, False, defaultdict(float)

    def local_of(take: str) -> datetime:
        utc = datetime.strptime(take.split('Z')[0], '%Y%m%dT%H%M%S').replace(tzinfo=UTC)
        return utc.astimezone().replace(tzinfo=None)

    taken = sorted((local_of(r['take']), r['chests']) for r in rows)
    for cycle in found:
        end = cycle['start'] + timedelta(seconds=cycle['seconds'])
        cycle['chests'] = sum(
            n for at, n in taken if cycle['start'] - timedelta(seconds=15) <= at < end - timedelta(seconds=15)
        )
    return found


def cycle_lines(found: list[dict]) -> list[str]:
    if not found:
        return ['cycles: none']
    hours = sum(c['seconds'] for c in found) / 3600
    chests = sum(c['chests'] for c in found)
    legs: dict[str, float] = defaultdict(float)
    for c in found:
        for name, seconds in c['legs'].items():
            legs[name] += seconds
    n = len(found)
    lines = [
        f'cycles (Lower Kurast arrival to the next): {n}, '
        f'median {statistics.median(c["seconds"] for c in found):.1f} s, '
        f'{chests / n:.1f} chests a cycle: **{chests / hours:.0f} chests an hour of cycles**',
        '  a cycle by leg (s): '
        + ', '.join(f'{name} {s / n:.1f}' for name, s in sorted(legs.items(), key=lambda kv: -kv[1])),
    ]
    return lines


def cycle_yield(before: list[dict], after: list[dict]) -> str:
    """Chests an hour of cycles, before -> after, with a 90% bootstrap interval of the difference."""
    if len(before) < MINIMUM or len(after) < MINIMUM:
        return 'too few cycles'

    def rate(found: list[dict]) -> float:
        return 3600 * sum(c['chests'] for c in found) / sum(c['seconds'] for c in found)

    rng = random.Random(7)
    draws = sorted(
        rate(rng.choices(after, k=len(after))) - rate(rng.choices(before, k=len(before))) for _ in range(DRAWS)
    )
    low, high = draws[int(0.05 * DRAWS)], draws[int(0.95 * DRAWS)]
    was, now = rate(before), rate(after)
    verdict = 'better' if low > 0 else 'worse' if high < 0 else 'no evidence'
    return (
        f'{was:.0f} -> {now:.0f} chests an hour of cycles ({now - was:+.0f}, 90% [{low:+.0f}, {high:+.0f}]: {verdict})'
    )


def window_games(since: datetime, until: datetime) -> list:
    args = argparse.Namespace(sessions=None, since=since)
    found = []
    for directory in games.sessions(args):
        found += games.read(directory, since, until)[0]
    return [g for g in found if g.end == 'next' and g.seconds is not None]


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def shift(before: list[float], after: list[float], more_better: bool = False) -> str:
    """The medians' difference (after - before) and its 90% bootstrap interval."""
    if len(before) < MINIMUM or len(after) < MINIMUM:
        return f'too few ({len(before)} / {len(after)})'
    rng = random.Random(7)
    draws = sorted(
        statistics.median(rng.choices(after, k=len(after))) - statistics.median(rng.choices(before, k=len(before)))
        for _ in range(DRAWS)
    )
    low, high = draws[int(0.05 * DRAWS)], draws[int(0.95 * DRAWS)]
    delta = statistics.median(after) - statistics.median(before)
    better, worse = ('worse', 'better') if more_better else ('better', 'worse')
    verdict = better if high < 0 else worse if low > 0 else 'no evidence'
    medians = f'{statistics.median(before):6.1f} -> {statistics.median(after):6.1f}'
    return f'{medians}  ({delta:+.1f}, 90% [{low:+.1f}, {high:+.1f}]: {verdict})'


def measures(found: list, rows: list[dict], quiets: list) -> dict[str, list[float]]:
    return {
        'game s': [g.seconds for g in found],
        'chests leg s': [g.legs.get('the chests', 0.0) for g in found],
        'town legs s': [sum(s for n, s in g.legs.items() if n != 'the chests') for g in found],
        'stay on the level s': [r['seconds'] for r in rows],
        'macro stalls s a stay': [r['stalled'] for r in rows],
        'lost to the pace s a stay': [r['lost'] for r in rows],
        'chests a minute': [60 * r['chests'] / r['seconds'] for r in rows if r['seconds'] > 0],
        'chests a stay': [r['chests'] for r in rows],
        'containers a stay': [r['chests'] + r['others'] for r in rows],
        'idle on the level s a stay': [r['idle'] for r in rows],
        'going back u a stay': [r['away'] for r in rows],
        **{f'idle in {name} s a take': [q.idle for q in quiets if str(q.area) == area] for area, name in TOWNS.items()},
    }


MORE_BETTER = ('chests a minute', 'chests a stay', 'containers a stay')


def yield_shift(before: tuple[list, list[dict]], after: tuple[list, list[dict]]) -> str:
    """Chests an hour of play (the loop's aim: chests, not games), before -> after, with a 90% bootstrap interval of
    the difference (games and stays resampled apart)."""

    def rate(found: list, rows: list[dict]) -> float:
        return 3600 * statistics.mean(r['chests'] for r in rows) / statistics.mean(g.seconds for g in found)

    sides = [before, after]
    if any(len(found) < MINIMUM or len(rows) < MINIMUM for found, rows in sides):
        return 'too few games'
    rng = random.Random(7)
    draws = sorted(
        rate(rng.choices(after[0], k=len(after[0])), rng.choices(after[1], k=len(after[1])))
        - rate(rng.choices(before[0], k=len(before[0])), rng.choices(before[1], k=len(before[1])))
        for _ in range(DRAWS)
    )
    low, high = draws[int(0.05 * DRAWS)], draws[int(0.95 * DRAWS)]
    was, now = rate(*before), rate(*after)
    verdict = 'better' if low > 0 else 'worse' if high < 0 else 'no evidence'
    return f'{was:.0f} -> {now:.0f} chests an hour ({now - was:+.0f}, 90% [{low:+.0f}, {high:+.0f}]: {verdict})'


def per_hour(found: list, rows: list[dict]) -> str:
    """The whole loop's yield: games and chests an hour of game time (town legs, lobby and level together)."""
    hours = sum(g.seconds for g in found) / 3600
    if not hours or not rows:
        return 'no games'
    chests = statistics.mean(r['chests'] for r in rows) * len(found)
    return f'{len(found) / hours:.1f} games and {chests / hours:.0f} chests an hour of play'


def inactive(rows: list[dict], every: list[tuple], quiets: list, games_n: int, args: argparse.Namespace) -> None:
    """Section 4 of the module text: the idle seconds on the level and in the towns, the towns' idle stretches by
    their log lines, and the legs that went back most."""
    print('\ninactive (still, neither casting nor moving, no input sent):')
    if rows:
        n = len(rows)
        idle, delay, stay, away = (sum(r[k] for r in rows) / n for k in ('idle', 'delay', 'seconds', 'away'))
        print(f'  Lower Kurast: {idle:.1f} s a stay of {stay:.1f} (and {delay:.1f} s in a skill delay after a cast); '
              f'going back {away:.0f} units a stay')  # fmt: skip
    for area, name in TOWNS.items():
        mine = [q for q in quiets if str(q.area) == area]
        if mine:
            per_game = f', {sum(q.idle for q in mine) / games_n:.1f} s a game' if games_n else ''
            print(f'  {name}: {sum(q.idle for q in mine) / len(mine):.1f} s a take of '
                  f'{sum(q.seconds for q in mine) / len(mine):.1f} ({len(mine)} takes{per_game})')  # fmt: skip
    reasons: dict[str, list[float]] = defaultdict(list)
    for q in quiets:
        for stretch in q.stretches:
            reasons[f'{TOWNS.get(str(q.area), q.area)}: ' + (' | '.join(stretch.reasons) or '(nothing said)')].append(
                stretch.seconds
            )
    if reasons and games_n:
        print('  idle stretches in town (s a game; times seen):')
        for reason, values in sorted(reasons.items(), key=lambda kv: -sum(kv[1]))[: args.reasons]:
            print(f'    {sum(values) / games_n:5.2f}  x{len(values):<4} {reason[:150]}')
    back = sorted(every, key=lambda tl: -tl[1].away)[: args.worst]
    if back and back[0][1].away > 0:
        print(f'  the {len(back)} legs that went back most:')
        for take, leg in back:
            print(f'    {take.directory.name} {clock_of(take, leg.begin)} to {leg.to}: back {leg.away:.0f} units, line '
                  f'{leg.line:.0f} way {leg.way:.0f}, {leg.seconds:.1f}s, idle {leg.idle:.1f}s')  # fmt: skip


def charges(rows: list[dict]) -> None:
    """Section 5 of the module text."""
    if not rows:
        return
    with_, without = [r for r in rows if r['teleports']], [r for r in rows if not r['teleports']]
    print(f'\nteleport charges: {sum(r["teleports"] for r in rows) / len(rows):.1f} spent a stay; '
          f'{len(with_)} stays with a charge, {len(without)} without')  # fmt: skip
    for name, side in (('with', with_), ('without', without)):
        if side:
            stay = median([r['seconds'] for r in side])
            rate = 60 * sum(r['chests'] for r in side) / sum(r['seconds'] for r in side)
            print(f'  {name:8} a stay {stay:.1f} s median, {rate:.2f} chests a minute')
    if len(with_) >= MINIMUM and len(without) >= MINIMUM:
        print(f'  stay s, without -> with: {shift([r["seconds"] for r in without], [r["seconds"] for r in with_])}')


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--since', type=logwords.local)
    parser.add_argument('--until', type=logwords.local)
    parser.add_argument('--against', nargs=2, type=logwords.local, metavar=('SINCE', 'UNTIL'))
    parser.add_argument('--worst', type=int, default=8)
    parser.add_argument('--reasons', type=int, default=12)
    parser.add_argument('--no-towns', action='store_true', help="skip the towns' takes (about 0.1 s each)")
    args = parser.parse_args()
    until = args.until or datetime.now()
    since = args.since or until - timedelta(hours=2)

    found = window_games(since, until)
    rows, every = stays(takes_in(since, until))
    print(f'window {since:%Y-%m-%d %H:%M} .. {until:%H:%M}: {len(found)} whole games, {len(rows)} stays')
    now_cycles = cycles(since, until, rows)
    for line in cycle_lines(now_cycles):
        print(line)
    if found:
        legs: dict[str, list[float]] = defaultdict(list)
        for g in found:
            for name, seconds in g.legs.items():
                legs[name].append(seconds)
        print(f'game median {median([g.seconds for g in found]):.1f} s; legs (median, p90 s):')
        for name, values in sorted(legs.items(), key=lambda kv: -statistics.median(kv[1])):
            print(f'  {name:26} {statistics.median(values):5.1f} {games.quantile(values, 0.9):5.1f}  (n {len(values)})')
    if rows:
        n = len(rows)
        total = sum(r['seconds'] for r in rows)
        print(
            f'\nthe level: a stay {median([r["seconds"] for r in rows]):.1f} s median, '
            f'{60 * sum(r["chests"] for r in rows) / total:.2f} chests a minute, '
            f'{sum(r["chests"] for r in rows) / n:.1f} chests and '
            f'{sum(r["others"] for r in rows) / n:.1f} others a stay'
        )
        print(f'  the whole loop: {per_hour(found, rows)}')
        split = ', '.join(f'{k} {sum(r[k] for r in rows) / n:.1f}' for k in ('casting', 'moving', 'standing', 'tail'))
        print(f'  a stay, s: {split}; macro stalls {sum(r["stalled"] for r in rows) / n:.1f}; '
              f'lost to the pace ({REFERENCE:g} u/s) {sum(r["lost"] for r in rows) / n:.1f}')  # fmt: skip
        reasons: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            for reason, seconds in r['stalls'].items():
                reasons[reason].append(seconds)
        print(f'\nwhere the stalls go (s a stay, over {n} stays; times seen):')
        for reason, values in sorted(reasons.items(), key=lambda kv: -sum(kv[1]))[: args.reasons]:
            print(f'  {sum(values) / n:5.2f}  x{len(values):<4} {reason[:150]}')
        print(f'\nthe {args.worst} legs that lost most to the pace:')
        for take, leg in sorted(every, key=lambda tl: -tl[1].lost)[: args.worst]:
            print(f'  {take.directory.name} {clock_of(take, leg.begin)} to {leg.to}: line {leg.line:.0f} way '
                  f'{leg.way:.0f}, {leg.seconds:.1f}s (cast {leg.casting:.1f}, move {leg.moving:.1f}, stand '
                  f'{leg.standing:.1f}), lost {leg.lost:.1f}s')  # fmt: skip
    quiets = [] if args.no_towns else towns(since, until)
    inactive(rows, every, quiets, len(found), args)
    charges(rows)
    if args.against:
        before_games = window_games(*args.against)
        before_rows, _ = stays(takes_in(*args.against))
        before_quiets = [] if args.no_towns else towns(*args.against)
        a, b = measures(before_games, before_rows, before_quiets), measures(found, rows, quiets)
        print(f'\nagainst {args.against[0]:%Y-%m-%d %H:%M} .. {args.against[1]:%H:%M} '
              f'({len(before_games)} games, {len(before_rows)} stays): before -> now')  # fmt: skip
        print(f'  CYCLES: {cycle_yield(cycles(*args.against, before_rows), now_cycles)}')
        print(f'  YIELD (whole games only): {yield_shift((before_games, before_rows), (found, rows))}')
        print(f'  games: {per_hour(before_games, before_rows)} -> {per_hour(found, rows)}')
        for name in a:
            print(f'  {name:26} {shift(a[name], b[name], more_better=name in MORE_BETTER)}')


if __name__ == '__main__':
    main()
