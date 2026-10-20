"""Elite kills an hour of play of the KP_6 loop, and where the time goes (macros/goals-plan.md §8).

The TZ leveling loop's metric (the player, 2026-10-19: "main metric: elite kills/per hour"; 02:12: "every loop has
it's own metric"): champions, uniques, super uniques and Heralds killed (and the act bosses, which the shard watch
counts as uniques) over the **hours of play** of the loop of one kind: the time the loop was on with that kind, town,
lobby and travel included, without the stretches it was off, the gaps between sessions (restarts) and the stalls the
player sorted out (as andy.py cuts them).

Run with the repo's Python: `uv run --offline python .agents/skills/d2-loop-watch/tools/elites.py`.

- Kills: `elite_kill` events of each session's terror-probe.jsonl (terror/shards.py `ShardWatch`), once a unit and a
  session, counted when they fall in the kind's play time; by kind of kill, by level, by phase.
- Play: each session's probe.log (`runs/alt-d/<UTC>-<id>/`): the loop on/off, its kind (`Loop run:`, the resume line,
  the legs), and the legs (`Loop: game N, <leg>`), each leg's time its phase's: lobby, town, travel, level, loot, trip.
- Per game: the play seconds and the kills of each game (from its `next game` leg), for the comparison.
- Activities (the player, 2026-10-19: "track: time what we're spending engaging vs other activities (traveling, town,
  creating game)"): **engaging** is the fights' own seconds (`Macro: fight (...): N casts seen in X s`, its X before
  the line), in a level or its loot; the rest of a level's time goes by the agenda's target then (`agenda: target ...
  (kill|explore|open|pickup, ...)`): approach (to an elite or a guard), explore (an unexplored room), chests (a super
  chest), pickup; level other (no target said yet); then travel, town, lobby (Save and Exit, creating the next game)
  and trip as the phases.

    uv run --offline python .agents/skills/d2-loop-watch/tools/elites.py [--since 'YYYY-MM-DD HH:MM'] [--until ...]
        [--kind tz|tzclear|andariel|lk|any] [--against SINCE UNTIL] [--json] [--runs DIR]

`--against`: the other window's rate and a 90% bootstrap interval of the difference (games resampled): better /
worse / no evidence.
"""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE), str(ROOT)]

import logwords  # ruff: ignore[module-import-not-at-top-of-file] - beside this tool
from logwords import (  # ruff: ignore[module-import-not-at-top-of-file] - beside this tool
    FIGHT,
    KIND,
    LEG,
    LOOP_OFF,
    LOOP_ON,
    LOOP_RESUMED,
    REQUEST_LOOP,
    RESUMED,
    SAID,
    STAMP_LEN,
    STOPPED,
    TARGET,
    stamp,
)

from inventory_tracking.macros import loop as loop_module  # ruff: ignore[module-import-not-at-top-of-file]


RUNS = ROOT / 'inventory_tracking' / 'runs' / 'alt-d'
KILL_EVENT = 'elite_kill'  # terror/shards.py ShardWatch: the event's name in terror-probe.jsonl
STALL_SECONDS = 90.0  # no leg line this long, then the loop off or stopped: a stall the player sorted out (andy.py)
REQUEST_SECONDS = 2.0
MINIMUM = 8  # games a side for a comparison
DRAWS = 2000
KILL_KINDS = ('champion', 'unique', 'super', 'herald')

# The kinds by the name the log says (macros/loop.py Kind.name), and the legs only one kind makes
NAMES = {kind.name: kind.key for kind in (loop_module.LK, loop_module.ANDARIEL, loop_module.TZ, loop_module.TZ_CLEAR)}
TZ_LEGS = {
    loop_module.TZ_WAYPOINT,
    loop_module.TZ_LEVEL,
    loop_module.TZ_LOOT,
    loop_module.TZ_PICKUP,
    loop_module.TZ_NEXT_LEVEL,
    loop_module.TZ_OUT,
    loop_module.TZ_PORTAL,
    loop_module.TZ_BACK,
}
ANDARIEL_LEGS = {loop_module.TO_THE_CATACOMBS, loop_module.DOWN, loop_module.FIGHT_ANDARIEL}
LK_LEGS = {loop_module.TO_THE_CHESTS, loop_module.CHESTS, loop_module.PORTAL}

# The phases, by leg
LOBBY, TOWN, TRAVEL, LEVEL, LOOT, TRIP = 'lobby', 'town', 'travel', 'level', 'loot', 'trip'
PHASES = (LOBBY, TOWN, TRAVEL, LEVEL, LOOT, TRIP)

# The activities (the module text): a level's time by the agenda's target kind, a fight's seconds engaging
ENGAGING, APPROACH, EXPLORE, CHESTS, PICKUP, LEVEL_OTHER = (
    'engaging',
    'approach',
    'explore',
    'chests',
    'pickup',
    'level other',
)
ACTIVITIES = (ENGAGING, APPROACH, EXPLORE, CHESTS, PICKUP, LEVEL_OTHER, TRAVEL, TOWN, LOBBY, TRIP)
TARGET_ACTIVITY = {'kill': APPROACH, 'explore': EXPLORE, 'open': CHESTS, 'pickup': PICKUP}
FIGHTING = (LEVEL, LOOT)  # the phases whose fights count as engaging


def activity_of(phase: str, target: str | None) -> str:
    """What a stretch of `phase` is spent on, with the agenda's last `target` kind (None: none said this leg)."""
    if phase == LEVEL:
        return TARGET_ACTIVITY.get(target or '', LEVEL_OTHER)
    if phase == LOOT:
        return PICKUP
    return phase


PHASE_OF = {
    loop_module.NEXT_GAME: LOBBY,
    loop_module.LEAVE: LOBBY,
    loop_module.TOWN: TOWN,
    loop_module.TZ_WAYPOINT: TRAVEL,
    loop_module.TZ_NEXT_LEVEL: TRAVEL,
    loop_module.TZ_OUT: TRAVEL,
    loop_module.TZ_PORTAL: TRAVEL,
    loop_module.TZ_BACK: TRAVEL,
    loop_module.TO_THE_CATACOMBS: TRAVEL,
    loop_module.TO_THE_CHESTS: TRAVEL,
    loop_module.TO_THE_FORTRESS: TRAVEL,
    loop_module.PORTAL: TRAVEL,
    loop_module.TZ_LEVEL: LEVEL,
    loop_module.DOWN: LEVEL,
    loop_module.FIGHT_ANDARIEL: LEVEL,
    loop_module.CHESTS: LEVEL,
    loop_module.TZ_LOOT: LOOT,
    loop_module.TZ_PICKUP: LOOT,
    loop_module.PICK_UP: LOOT,
    loop_module.TRIP: TRIP,
    loop_module.TO_THE_ENCAMPMENT: TRIP,
    loop_module.THROUGH_PORTAL: TRIP,
}


@dataclass
class Event:
    at: datetime
    kind: str  # 'leg', 'on', 'off', 'stopped', 'request', 'loopkind', 'fight', 'target', 'end'
    data: Any = None


@dataclass
class Piece:
    start: datetime
    end: datetime
    phase: str
    game: str  # session/game number
    activity: str = ''  # ACTIVITIES (`activity_of`, a fight's seconds ENGAGING)

    @property
    def seconds(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass
class Kill:
    at: datetime
    kind: str
    area: int
    session: str
    unit: int


@dataclass
class Window:
    since: datetime
    until: datetime
    kind: str
    pieces: list[Piece] = field(default_factory=list)
    kills: list[Kill] = field(default_factory=list)  # those in the kind's play time
    off: int = 0  # kills outside it
    sessions: list[str] = field(default_factory=list)


def parse(lines: list[str]) -> list[Event]:
    """A session's log as this tool's events."""
    events: list[Event] = []
    for line in lines:
        at = stamp(line)
        if at is None:
            continue
        text = line[STAMP_LEN:]
        if (m := LEG.search(text)) is not None:
            events.append(Event(at, 'leg', (int(m.group(1)), m.group(2).strip())))
        elif (m := RESUMED.search(text)) is not None:
            events.append(Event(at, 'loopkind', (m.group(2) or '').strip() or None))
            if m.group(1) == 'off':
                events.append(Event(at, 'off'))
        elif (m := KIND.search(text)) is not None:
            events.append(Event(at, 'loopkind', m.group(1).strip()))
        elif LOOP_ON in text or SAID + LOOP_RESUMED in text:
            events.append(Event(at, 'on'))
        elif LOOP_OFF in text:
            events.append(Event(at, 'off'))
        elif (m := STOPPED.search(text)) is not None:
            events.append(Event(at, 'stopped', m.group(1)))
        elif REQUEST_LOOP in text:
            events.append(Event(at, 'request'))
        elif (m := FIGHT.search(text)) is not None:
            events.append(Event(at, 'fight', float(m.group(1))))
        elif (m := TARGET.search(text)) is not None:
            events.append(Event(at, 'target', m.group(1)))
    if events:
        events.append(Event(events[-1].at, 'end'))
    return events


# The shard act kinds (macros/loop.py ACT_KINDS), one per act: their legs are the TZ kinds'
ACT_KINDS = tuple(f'act{act}' for act in range(1, 6))


def kind_of_leg(leg: str, now: str | None) -> str | None:
    """The kind a leg says the loop runs (None: a leg every kind makes)."""
    if leg in TZ_LEGS:
        return now if now in ('tz', 'tzclear', *ACT_KINDS) else 'tz'
    if leg in ANDARIEL_LEGS:
        return 'andariel'
    if leg in LK_LEGS:
        return 'lk'
    return None


def walk(window: Window, session: str, events: list[Event]) -> None:
    """One session's play pieces of the window's kind (andy.py `walk`, by phase)."""
    on, kind, phase, game = False, None, LOBBY, f'{session}/0'
    target: str | None = None
    fights: list[tuple[datetime, datetime]] = []
    last: datetime | None = None
    progress: datetime | None = None
    excluded: list[tuple[datetime, datetime]] = []
    pieces: list[Piece] = []

    def account(upto: datetime) -> None:
        nonlocal last
        if last is not None and on and (window.kind == 'any' or kind == window.kind):
            start, end = max(last, window.since), min(upto, window.until)
            if end > start:
                pieces.append(Piece(start, end, phase, game, activity_of(phase, target)))
        last = upto

    for event in events:
        account(event.at)
        if event.kind == 'loopkind' and event.data:
            kind = NAMES.get(event.data, kind)
        elif event.kind == 'on':
            on, progress = True, event.at
        elif event.kind in ('off', 'stopped', 'end'):
            if on and progress is not None and (event.at - progress).total_seconds() >= STALL_SECONDS:
                excluded.append((progress, event.at))
            on = False
        elif event.kind == 'leg':
            number, leg = event.data
            progress = event.at
            kind = kind_of_leg(leg, kind) or kind
            phase = PHASE_OF.get(leg, phase)
            game = f'{session}/{number}'
            target = None
        elif event.kind == 'target':
            target = event.data
        elif event.kind == 'fight':
            fights.append((event.at - timedelta(seconds=event.data), event.at))
    for piece in pieces:
        parts = [(piece.start, piece.end)]
        for low, high in excluded:
            parts = [part for a, b in parts for part in ((a, min(b, low)), (max(a, high), b)) if part[1] > part[0]]
        for a, b in parts:
            window.pieces += engaged(Piece(a, b, piece.phase, piece.game, piece.activity), fights)


def engaged(piece: Piece, fights: list[tuple[datetime, datetime]]) -> list[Piece]:
    """`piece` with the fights' seconds in it (in a level or its loot) cut out as ENGAGING pieces."""
    if piece.phase not in FIGHTING:
        return [piece]
    out, rest = [], [(piece.start, piece.end)]
    for low, high in fights:
        if high <= piece.start or low >= piece.end:
            continue
        a, b = max(low, piece.start), min(high, piece.end)
        out.append(Piece(a, b, piece.phase, piece.game, ENGAGING))
        rest = [part for x, y in rest for part in ((x, min(y, a)), (max(x, b), y)) if part[1] > part[0]]
    return [Piece(x, y, piece.phase, piece.game, piece.activity) for x, y in rest] + out


def kills_in(directory: Path) -> list[Kill]:
    """The session's elite kills, once a unit (terror-probe.jsonl)."""
    path = directory / 'terror-probe.jsonl'
    if not path.exists():
        return []
    found, seen = [], set()
    with path.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if KILL_EVENT not in line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('event') != KILL_EVENT or row.get('unit_id') in seen or not row.get('at'):
                continue
            seen.add(row.get('unit_id'))
            at = datetime.fromisoformat(row['at']).astimezone().replace(tzinfo=None)
            found.append(
                Kill(at, str(row.get('kind') or '?'), int(row.get('area') or 0), directory.name, row['unit_id'])
            )
    return found


def read(since: datetime, until: datetime, kind: str, runs: Path = RUNS) -> Window:
    window = Window(since, until, kind)
    for directory in logwords.sessions(since, until, runs):
        window.sessions.append(directory.name)
        lines = (directory / 'probe.log').read_text(errors='replace').splitlines()
        before = len(window.pieces)
        walk(window, directory.name, parse(lines))
        mine = window.pieces[before:]
        for found in kills_in(directory):
            if not since <= found.at <= until:
                continue
            if any(piece.start <= found.at <= piece.end for piece in mine):
                window.kills.append(found)
            else:
                window.off += 1
    return window


def phase_at(window: Window, at: datetime) -> str:
    return next((piece.phase for piece in window.pieces if piece.start <= at <= piece.end), '?')


def games_of(window: Window) -> list[dict]:
    """Per game: its play seconds and its kills."""
    seconds: dict[str, float] = defaultdict(float)
    for piece in window.pieces:
        seconds[piece.game] += piece.seconds
    kills: Counter[str] = Counter()
    for found in window.kills:
        game = next((p.game for p in window.pieces if p.start <= found.at <= p.end), None)
        if game is not None:
            kills[game] += 1
    return [{'game': game, 'seconds': secs, 'kills': kills[game]} for game, secs in seconds.items() if secs > 0]


def rate(games: list[dict]) -> float:
    seconds = sum(g['seconds'] for g in games)
    return 3600 * sum(g['kills'] for g in games) / seconds if seconds else 0.0


def shift(before: list[dict], after: list[dict]) -> str:
    """Elite kills an hour, before -> after, with a 90% bootstrap interval of the difference (games resampled)."""
    if len(before) < MINIMUM or len(after) < MINIMUM:
        return f'too few games ({len(before)} / {len(after)}) for a comparison'
    rng = random.Random(7)
    draws = sorted(
        rate(rng.choices(after, k=len(after))) - rate(rng.choices(before, k=len(before))) for _ in range(DRAWS)
    )
    low, high = draws[int(0.05 * DRAWS)], draws[int(0.95 * DRAWS)]
    verdict = 'better' if low > 0 else 'worse' if high < 0 else 'no evidence'
    was, now = rate(before), rate(after)
    return f'{was:.1f} -> {now:.1f} elite kills an hour ({now - was:+.1f}, 90% [{low:+.1f}, {high:+.1f}]: {verdict})'


def measure(window: Window) -> dict:
    hours = sum(piece.seconds for piece in window.pieces) / 3600
    phases: dict[str, float] = defaultdict(float)
    for piece in window.pieces:
        phases[piece.phase] += piece.seconds
    by_phase = Counter(phase_at(window, found.at) for found in window.kills)
    doing: dict[str, float] = defaultdict(float)
    for piece in window.pieces:
        doing[piece.activity or piece.phase] += piece.seconds
    games = games_of(window)
    return {
        'kind': window.kind,
        'hours': hours,
        'kills': len(window.kills),
        'per_hour': len(window.kills) / hours if hours else None,
        'by_kind': dict(Counter(found.kind for found in window.kills)),
        'by_area': dict(Counter(found.area for found in window.kills).most_common()),
        'phases': {phase: {'seconds': phases.get(phase, 0.0), 'kills': by_phase.get(phase, 0)} for phase in PHASES},
        'activities': {name: doing.get(name, 0.0) for name in ACTIVITIES},
        'games': len(games),
        'off_kind': window.off,
        'sessions': window.sessions,
    }


def report(result: dict, games: list[dict]) -> None:
    per = result['per_hour']
    print(f"{result['kind']}: {result['kills']} elite kills in {result['hours']:.2f} h of play: "
          f"{per:.1f} an hour" if per is not None else f"{result['kind']}: no play in the window")  # fmt: skip
    if result['kills']:
        print('  by kind: ' + ', '.join(f'{k} {result["by_kind"].get(k, 0)}' for k in (*KILL_KINDS, '?')))
        print('  by level: ' + ', '.join(f'{area} {n}' for area, n in list(result['by_area'].items())[:10]))
    total = result['hours'] * 3600 or 1.0
    print(f'  {"phase":8} {"seconds":>8} {"share":>6} {"kills":>6}')
    for phase, row in result['phases'].items():
        print(f'  {phase:8} {row["seconds"]:8.0f} {row["seconds"] / total:6.0%} {row["kills"]:6d}')
    print(f'  {"activity":12} {"seconds":>8} {"share":>6} {"a game":>7}')
    count = max(len(games), 1)
    for name, seconds in result['activities'].items():
        print(f'  {name:12} {seconds:8.0f} {seconds / total:6.0%} {seconds / count:6.1f}s')
    if games:
        print(f'  {len(games)} games, {sum(g["seconds"] for g in games) / len(games):.0f} s a game of play, '
              f'{sum(g["kills"] for g in games) / len(games):.1f} elite kills a game')  # fmt: skip
    if result['off_kind']:
        print(f"  ({result['off_kind']} elite kills fell outside this kind's play time)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    now = datetime.now()
    parser.add_argument('--since', type=logwords.local, default=now - timedelta(hours=2))
    parser.add_argument('--until', type=logwords.local, default=now)
    parser.add_argument('--kind', default='tz', choices=('tz', 'tzclear', *ACT_KINDS, 'andariel', 'lk', 'any'))
    parser.add_argument('--against', nargs=2, type=logwords.local, metavar=('SINCE', 'UNTIL'))
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--runs', type=Path, default=RUNS, help="the sessions directory (default: this checkout's)")
    args = parser.parse_args()
    window = read(args.since, args.until, args.kind, args.runs)
    result, games = measure(window), games_of(window)
    if args.against:
        other = read(args.against[0], args.against[1], args.kind, args.runs)
        result['against'] = {'measure': measure(other), 'shift': shift(games_of(other), games)}
    if args.json:
        print(json.dumps(result, default=str, indent=1))
        return
    report(result, games)
    if args.against:
        print(f'\nagainst {args.against[0]:%Y-%m-%d %H:%M}-{args.against[1]:%H:%M}: {result["against"]["shift"]}')


if __name__ == '__main__':
    main()
