"""What the service logs and the combat takes say about the macro loop's own time: how long it takes
to notice and react, what a handover costs, where it waits on fixed pauses and what it does twice.

Two sources, both git-ignored runs of real play:

- `inventory_tracking/runs/alt-d/<stamp>/probe.log`: the macro's own lines with millisecond stamps.
  A gap between two lines is wall time on the host, reads and decisions included.
- `inventory_tracking/runs/combat/<stamp>-<area>/`: the recorder's frames, about 25 a second. A frame
  says where the character and every monster stood, which buttons were down and whether a macro run
  was working, so "a hostile came into reach" has a time the log does not have. A frame is 40 ms:
  nothing here is finer than that. A take's clock is tied to the log's by the manifest's
  `started_at` (written at the first frame), good to a frame or two.

Each measure prints its count, median, 90th percentile and the worst case with the log or take and
the time to look at. The letters are the ones the loop report uses.

    uv run --offline python -m tests.inventory_tracking.scenarios.loop.evidence [first stamp]

The default first stamp is the first log with the fight's summary line (2026-10-10 16:55 local).
"""

import bisect
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from inventory_tracking.combat.policy import REACH, RUN_MODES
from inventory_tracking.combat.sim.situation import load_ground
from inventory_tracking.combat.takes import Take, monsters_of, player_of
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.routines import ACTING, TOWN_NPCS
from inventory_tracking.macros.sight import in_reach
from inventory_tracking.macros.skills import ECHOING_STRIKE
from inventory_tracking.terror.tracker import UNKILLABLE


LOGS = Path('inventory_tracking/runs/alt-d')
TAKES = Path('inventory_tracking/runs/combat')
FIRST = '20261010T135554Z'
STAMP = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) \w+ (.*)$')
UNIT = re.compile(r'\((\d+)\)')
ON, PAUSED, OFF = 'Macro: Attack mode on', 'Macro: Attack mode paused', 'Macro: Attack mode off'
STRIKE = 'Macro: Echoing Strike ('
LEFT_BUTTON, STRIKE_BUTTON = 1 << 8, 1 << 10  # the pointer mask's bits (XQueryPointer)
IDLE_FRAMES = 8  # frames the mode stood idle with nothing in reach before a hostile came into it
HOP_UNITS = 5.0  # the character this far from where the frame before had it: a teleport landed
Rows = dict[str, list[tuple[float, str]]]  # measure -> (seconds, where to look)


def quantile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))] if ordered else math.nan


def show(name: str, rows: list[tuple[float, str]]) -> None:
    if not rows:
        print(f'{name}: n=0')
        return
    values = [seconds for seconds, _ in rows]
    worst = max(rows)
    print(
        f'{name}: n={len(values)} median={statistics.median(values) * 1000:.0f}ms '
        f'p90={quantile(values, 0.9) * 1000:.0f}ms worst={worst[0] * 1000:.0f}ms @ {worst[1]}'
    )


# --- the service logs ---


def macro_lines(path: Path) -> list[tuple[float, str, str]]:
    """(wall seconds, message, stamp text) of the macro's lines and the slow-pass warnings."""
    found = []
    for line in path.read_text(errors='replace').splitlines():
        match = STAMP.match(line)
        if match and match[3].startswith(('Macro', 'Slow service')):
            at = datetime.strptime(match[1], '%Y-%m-%d %H:%M:%S').timestamp() + int(match[2]) / 1000
            found.append((at, match[3], f'{match[1]},{match[2]}'))
    return found


def step_kind(text: str) -> str:
    """What ran between a pause of attack mode and its return, from the lines in between."""
    hops, swaps = text.count('Macro: Teleport on '), text.count('Swap Weapons on')
    many = f'x{min(hops, 3)}{"+" if hops > 3 else ""}'
    if 'Picking up' in text:
        kind = 'pickup'
    elif 'Walking into' in text:
        kind = 'door'
    elif 'Macro stopped' in text or 'Macro failed' in text:
        kind = 'a step that stopped'
    elif 'is in reach: attack mode takes it' in text:
        kind = 'seek that only named the elite'
    elif 'Macro: Walking ' in text:
        kind = 'seek walk'
    elif 'seek:' in text and hops:
        kind = f'seek hop {many}'
    elif hops:
        kind = f'teleport hop {many}'
    else:
        kind = 'other'
    return f'{kind} + weapon swap' if swaps else kind


def next_index(lines, start: int, wanted, stops=(ON, PAUSED, OFF)) -> int | None:
    """The first line from `start` that `wanted` accepts, unless one of `stops` comes first."""
    for index in range(start, len(lines)):
        text = lines[index][1]
        if wanted(text):
            return index
        if text in stops:
            return None
    return None


def hop_parts(rows: Rows, between, paused_at: float, resumed_at: float, where: str) -> None:
    """One seek hop between a pause and the mode's return, cut at its log lines."""

    def first(*needles: str) -> float | None:
        return next((at for at, text, _ in between if any(needle in text for needle in needles)), None)

    read, hunting = first('pickup:', 'seek:'), first('hunting', 'exploring')
    toward, key, landed = first('Teleport toward'), first('Teleport on'), first('teleport aimed')
    if read is None or hunting is None or toward is None or key is None or landed is None:
        return
    parts = (
        ("1 paused -> the step's first read (the handover in)", read - paused_at),
        ('2 first read -> "hunting" (the scans and the firing spots)', hunting - read),
        ('3 "hunting" -> "Teleport toward" (the way and the landing planned, the staff looked at)', toward - hunting),
        ('4 "Teleport toward" -> the key (the aim: pointer steps and the pause after)', key - toward),
        ('5 the key -> landed (the key hold and the game)', landed - key),
        ('6 landed -> "Attack mode on" (the handover out)', resumed_at - landed),
    )
    for name, seconds in parts:
        rows[f'b1 one seek hop, part {name}'].append((seconds, where))


def log_evidence(first: str) -> tuple[Rows, Counter, list[tuple[float, str, int | None, str]]]:
    """The measures of the logs from `first` on, the counts, and the fights' aim lines for (c)."""
    rows: Rows = defaultdict(list)
    counts: Counter = Counter()
    aims: list[tuple[float, str, int | None, str]] = []  # (wall, kind, unit, where)
    files = sorted(path for path in LOGS.glob('*/probe.log') if path.parent.name >= first)
    counts['logs'] = len(files)
    for path in files:
        lines = macro_lines(path)
        name = path.parent.name
        for index, (at, text, stamp) in enumerate(lines):
            where = f'{name} {stamp}'
            if text == PAUSED:
                resumed = next_index(lines, index + 1, lambda found: found == ON, stops=(PAUSED, OFF))
                if resumed is None:
                    counts['b pauses the mode never came back from'] += 1
                    continue
                between = lines[index + 1 : resumed]
                joined = '\n'.join(found for _, found, _ in between)
                kind = step_kind(joined)
                gap = lines[resumed][0] - at
                rows[f'b paused -> on [{kind}]'].append((gap, where))
                rows['b paused -> on [all]'].append((gap, where))
                if kind == 'seek hop x1' and 'the pointer was found' not in joined:
                    hop_parts(rows, between, at, lines[resumed][0], where)
            elif text == ON:
                own = 0  # marks, sigils and swaps of the macro's own before the first strike
                for later_at, later, _ in lines[index + 1 :]:
                    if later_at - at > 6 or later.startswith(('Macro: idle:', 'Macro: Attack mode', 'Macro: pickup')):
                        break
                    if later.startswith(STRIKE):
                        key = 'straight' if not own else f'after {own} of Death Mark, the sigil, a swap'
                        rows[f'a3 on -> the first strike [{key}]'].append((later_at - at, where))
                        break
                    own += later in ('Macro: Death Mark', 'Macro: Sigil: Lethargy', 'Macro: Swap Weapons')
            elif text.startswith('Macro: fight ('):
                why = text.split('; ', 1)[1]
                counts['fights'] += 1
                counts[f'fight ended: {re.sub(r" [(].*", "", why)}'] += 1
                counts['fights with no cast seen'] += ' 0 casts seen' in text
                aims.append((at, 'end', None, where))
                again = next_index(lines, index + 1, lambda found: found.startswith(STRIKE))
                if again is None:
                    continue
                gap = lines[again][0] - at
                if why.startswith('Nothing left in reach'):
                    rows['d "Nothing left in reach" -> the next strike, the mode not paused'].append((gap, where))
                    if gap < 1.0:
                        rows['d churn: the next strike within 1 s'].append((gap, where))
                elif why.startswith('Yielded'):
                    rows['yielded to the player -> the next strike'].append((gap, where))
                elif why.startswith('Stopping for the main weapons'):
                    rows['g stopped for the main weapons -> the next strike'].append((gap, where))
            elif text == 'Macro: Main weapons for the fight':
                again = next_index(lines, index + 1, lambda found: found.startswith(STRIKE))
                counts['g swaps to the main weapons'] += 1
                if again is not None:
                    rows['g "Main weapons for the fight" -> the strike'].append((lines[again][0] - at, where))
            elif text in ('Macro: Death Mark', 'Macro: Sigil: Lethargy'):
                # Its own lines ("... on <key>", "Death Mark on <monster>") are skipped: the next line is
                # the first thing the fight does after it.
                after = next(
                    (found for found in lines[index + 1 :] if not found[1].startswith((f'{text} on', 'Macro: Death'))),
                    None,
                )
                if after is not None and after[0] - at < 3:
                    rows[f'a4 {text[7:]}: said -> the next thing the fight does'].append((after[0] - at, where))
            elif text.startswith(('Macro: line through', STRIKE)):
                unit = UNIT.search(text)
                kind = 'line' if text.startswith('Macro: line through') else 'strike'
                aims.append((at, kind, int(unit[1]) if unit else None, where))
            elif text.startswith('Macro: pickup:'):
                counts['e pickup scans'] += 1
                counts['e pickup scans that found nothing to pick up'] += 'nothing to pick up' in text
                before = next((line for line in reversed(lines[:index]) if line[1].startswith('Macro: pickup:')), None)
                counts['e pickup scans within 1 s of the one before'] += before is not None and at - before[0] < 1.0
            elif text.startswith('Macro: seek:'):
                counts['e seek scans'] += 1
                before = next((found for found in reversed(lines[:index]) if found[1].startswith('Macro: seek:')), None)
                counts['e seek scans within 1 s of the one before'] += before is not None and at - before[0] < 1.0
            elif text.startswith('Macro: the pointer was found'):
                counts['f aim retries'] += 1
                rows['f an aim retry: the line before -> this one'].append((at - lines[index - 1][0], where))
            elif 'swallowed made again' in text:
                after = re.search(r'([\d.]+)s after the press', text)
                assert after is not None
                rows['f a swallowed click: the press -> made again'].append((float(after[1]), where))
            elif text.startswith('Macro: Teleport toward'):
                counts['hops'] += 1
                retries = 0
                while lines[index + 1 + retries][1].startswith('Macro: the pointer was found'):
                    retries += 1
                if lines[index + 1 + retries][1] == 'Macro: Teleport':
                    gap = lines[index + 1 + retries][0] - at
                    rows[f'f a hop\'s aim, "Teleport toward" -> the key [{retries} retries]'].append((gap, where))
            elif text.startswith('Slow service pass'):
                took = re.search(r'pass: (\d+) ms', text)
                assert took is not None
                rows['service passes over the slow mark'].append((int(took[1]) / 1000, f'{where} {text[:110]}'))
            elif text.startswith('Macro stopped: the mouse'):
                counts['f steps stopped by the mouse'] += 1
        hunted = Counter(
            match[1] for _, text, _ in lines if (match := re.match(r'Macro: hunting the elite \d+ \((\d+)\)', text))
        )
        for unit, steps in hunted.items():
            rows['e seek steps per hunted elite (a count, not ms)'].append((steps / 1000, f'{name} unit {unit}'))
    return rows, counts, sorted(aims)


# --- the takes ---


def frame_rows(take: Take, ground: Ground) -> list[dict | None]:
    """Per frame: what the reaction measures need; None without the character or in another level."""
    rows: list[dict | None] = []
    for frame in take.frames:
        player = player_of(frame)
        if player is None or player.area != take.manifest['area']:
            rows.append(None)
            continue
        doors = tuple(Door(d[0], d[1], d[2], float(d[3]), float(d[4])) for d in frame.get('d', ()))
        reach = sum(
            1
            for m in monsters_of(frame)
            if m.hostile
            and (m.x or m.y)
            and m.txt not in UNKILLABLE
            and m.txt not in TOWN_NPCS
            and in_reach(ground, player.at, m.at, REACH, doors)
        )
        mask = frame['in'][2] or 0
        rows.append(
            {
                't': frame['t'],
                'macro': bool(frame.get('macro')),
                'here': player.at,
                'mode': player.mode,
                'reach': reach,
                'left': bool(mask & LEFT_BUTTON),
                'strike': bool(mask & STRIKE_BUTTON),
                'busy': bool(frame['in'][5]) or bool(frame.get('panels')),
                'armed': player.right_skill == ECHOING_STRIKE,
            }
        )
    return rows


def calm(row: dict | None) -> bool:
    """A macro run works and the character stands free with no input of the player's: attack mode idles."""
    return (
        row is not None
        and row['macro']
        and row['mode'] not in RUN_MODES
        and row['mode'] not in ACTING
        and not (row['left'] or row['strike'] or row['busy'])
    )


def reactions(rows: Rows, counts: Counter, frames: list[dict | None], stamp) -> None:
    """(a) A hostile comes into reach with a clear shot while the mode has idled IDLE_FRAMES at one
    place, to the strike button going down. (a2) The same from a hop's landing."""
    index = 0
    while index < len(frames):
        row = frames[index]
        back = frames[max(0, index - IDLE_FRAMES) : index]
        idle = len(back) == IDLE_FRAMES and all(
            calm(b) and b['reach'] == 0 and math.dist(b['here'], row['here']) < 0.5 for b in back if row and b
        )
        if row is None or not (calm(row) and row['reach'] and row['armed'] and idle and all(back)):
            index += 1
            continue
        end = index
        outcome: tuple[str, float | None] = ('nothing in 3 s', None)
        while end < len(frames) and frames[end] is not None and frames[end]['t'] - row['t'] < 3.0:
            now = frames[end]
            if now['strike'] or now['mode'] in ACTING:
                outcome = ('the strike', now['t'] - row['t'])
                break
            if not now['macro'] or now['left'] or now['busy'] or now['mode'] in RUN_MODES:
                outcome = ('the player moved, pressed a key, or the mode went off', None)
                break
            ahead = frames[end : end + 3]
            if len(ahead) == 3 and all(found is not None and found['reach'] == 0 for found in ahead):
                outcome = ('it left reach again unstruck', now['t'] - row['t'])
                break
            end += 1
        counts[f'a outcome: {outcome[0]}'] += 1
        if outcome[0] == 'the strike' and outcome[1] is not None:
            rows['a a hostile came into reach while the mode idled -> the strike input down'].append(
                (outcome[1], stamp(row['t']))
            )
        index = end + 1
    for index in range(1, len(frames)):
        before, landed = frames[index - 1], frames[index]
        if before is None or landed is None or not (landed['macro'] and landed['armed'] and landed['reach']):
            continue
        if math.dist(before['here'], landed['here']) < HOP_UNITS or before['strike'] or landed['strike']:
            continue
        for later, now in enumerate(frames[index:], index):
            hopped = later > index and frames[later - 1] and math.dist(frames[later - 1]['here'], now['here']) >= 5
            if now is None or now['t'] - landed['t'] >= 3.0 or now['left'] or now['mode'] in RUN_MODES or hopped:
                counts['a2 landed with a hostile in reach, no strike before a move or the next hop'] += 1
                break
            if now['strike']:
                rows['a2 a hop landed with a hostile in reach -> the strike input down'].append(
                    (now['t'] - landed['t'], stamp(landed['t']))
                )
                break


def late_frames(rows: Rows, counts: Counter, take: Take, stamp) -> None:
    """(h) The recorder's late frames, by what the macro was doing: nothing, a fight (the strike input
    held), or a run with the input up (a step: a hop being planned and made, a pickup, the mode idling)."""
    frames = take.frames
    places = [(f['p'][3], f['p'][4]) if f.get('p') else None for f in frames]
    landings = {
        index
        for index in range(1, len(frames))
        if frames[index].get('macro')
        and places[index]
        and places[index - 1]
        and HOP_UNITS <= math.dist(places[index], places[index - 1]) < 60
    }
    for index, frame in enumerate(frames):
        held = bool((frame['in'][2] or 0) & STRIKE_BUTTON)
        state = 'no macro run' if not frame.get('macro') else 'a macro run, the strike held' if held else 'a macro run'
        counts[f'h frames [{state}]'] += 1
        counts[f'h late frames [{state}]'] += bool(frame.get('late'))
        counts[f'h ticks lost [{state}]'] += frame.get('late', 0)
        if frame.get('late') and state == 'a macro run':
            counts['h late frames of a macro run within 0.5 s before a hop landed'] += any(
                index + ahead in landings for ahead in range(13)
            )
        if frame.get('late', 0) >= 5:
            rows[f'h a frame 5 or more ticks late [{state}]'].append((frame['late'] / 25, stamp(frame['t'])))
    counts['h hops in the takes'] += len(landings)
    counts['h hops with a late frame in the 0.5 s before the landing'] += sum(
        any(frames[back].get('late') for back in range(max(0, index - 12), index + 1)) for index in landings
    )


def take_evidence(first: str) -> tuple[Rows, Counter, list[tuple[float, int, str]]]:
    """The measures of the takes from `first` on, the counts, and the macro's kills in wall time for (c)."""
    rows: Rows = defaultdict(list)
    counts: Counter = Counter()
    kills: list[tuple[float, int, str]] = []
    for directory in sorted(path for path in TAKES.glob('2026*') if path.name >= first):
        try:
            take = Take.load(directory)
        except OSError, ValueError, json.JSONDecodeError:
            continue
        if not take.frames:
            continue
        counts['takes'] += 1
        offset = datetime.fromisoformat(take.manifest['started_at']).timestamp() - take.frames[0]['t']

        def stamp(at: float, name: str = directory.name, offset: float = offset) -> str:
            return f'{name} {datetime.fromtimestamp(offset + at).strftime("%H:%M:%S.%f")[:-3]}'

        kills += [
            (offset + e['t'], e['unit'], directory.name) for e in take.events if e['event'] == 'kill' and e.get('macro')
        ]
        reactions(rows, counts, frame_rows(take, load_ground(take) or Ground(())), stamp)
        late_frames(rows, counts, take, stamp)
    return rows, counts, kills


def kill_to_aim(rows: Rows, counts: Counter, aims, kills) -> None:
    """(c) A kill of the monster the line was through (the take) to the next line (the log, written
    once the pointer is on it), or to the fight's end when that was the last one."""
    times = [at for at, _, _, _ in aims]
    for at, unit, take in kills:
        last = bisect.bisect_right(times, at) - 1
        if last < 0 or last + 1 >= len(aims) or aims[last][1] != 'line' or at - aims[last][0] > 20:
            continue
        if aims[last][2] != unit:
            counts['c kills of a monster the line was not through'] += 1
            continue
        after_at, kind, _, where = aims[last + 1]
        if after_at - at > 5 or kind == 'strike':
            continue
        name = 'the next line (the pointer is on it)' if kind == 'line' else "the fight's end"
        rows[f'c the lined monster killed -> {name}'].append((after_at - at, f'{take}, log {where}'))


def main(first: str = FIRST) -> None:
    rows, counts, aims = log_evidence(first)
    take_rows, take_counts, kills = take_evidence(first.replace('Z', '')[:11])
    kill_to_aim(take_rows, take_counts, aims, kills)
    print(f'{counts["logs"]} logs and {take_counts["takes"]} takes from {first} on')
    for name in sorted(rows):
        show(name, rows[name])
    for name in sorted(take_rows):
        show(name, take_rows[name])
    for name, count in sorted((counts + take_counts).items()):
        print(f'{name}: {count}')


if __name__ == '__main__':
    main(*sys.argv[1:2])
