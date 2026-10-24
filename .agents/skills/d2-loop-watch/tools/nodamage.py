"""The automatic RCA of a NO_DAMAGE case: why the strikes at a target took nothing off it, checked from the take.

The player, 2026-10-24 ~20:35: "we need to have some king of debug message when we expect us to deliver damage but not
damaging the mob => and do automatic rca for such cases" (just after the loop struck a Herald through a closed door).
anomalies.py finds the cases (NO_DAMAGE: a target struck with its life not falling); this tool checks every candidate
cause the take can show over the case's frames, ranks them and writes the report to
`rca/auto/<date>/nodamage-<HHMMSS>-<unit>.md`. watch.py runs it on each NO_DAMAGE line.

The causes looked at, each from the take alone (frames, events, units.jsonl, records.jsonl, level.json):

- **door**: a door unit (levels/doors.py `door_sizes` classes, the frames' `d`) read closed on the line from the
  character to the target (`Door.blocks` along it), and whether the hunt took it as passed (a live hostile or the
  character read inside its footprint earlier: `PassedDoors`, which lets a shot through it);
- **wall**: the level's grids on the line (combat/policy.py `walls` over level.json: the flight layer, unread cells);
- **immune**: the target's resistances of the strike's damage types at 100 or more (the blade physical with the
  gear's cold, the Hex: Purge explosions magic: builds/warlock/mark.py), from units.jsonl and its `stats` events;
- **untargetable**: the unit's flag word without "can be attacked" (game/layout.py ATTACKABLE_FLAG at UNIT_FLAGS of
  the record in records.jsonl: submerged, burrowed, airborne, an invulnerable phase), and its states (states.txt names:
  invisible, cloaked);
- **mode**: the target dead (0, 12), in a sequence (14: submerged, burrowed) or not in the read;
- **range**: the target beyond the blades' reach (echoing_strike/mechanics.py RANGE) or the hunt's (policy.py
  STRIKE_REACH);
- **pointer**: where the macro's `sent` moves put the pointer and where the game's pointer was (`in`) against the
  target, at each cast's aim (POINTER_LAG frames before its blades);
- **skill**: whether the casts were Echoing Strike: the right skill (`p`), the skill in use in records.jsonl, blades;
- **blades**: each cast's blades (missile 706 in the frames' `x`): their lives (short: stopped by something), whether
  one came within CONTACT of the target, how far they flew against its distance.

The verdict ranks the causes by a score (the share of the case's frames or casts each holds in, weighted by how surely
it stops all damage), with the evidence lines; `unexplained` when none holds.

    uv run --offline python .agents/skills/d2-loop-watch/tools/nodamage.py <take> [--at HH:MM:SS] [--unit U]
        [--window 20] | --since 'YYYY-MM-DD HH:MM' [--until ...] [--json] [--out rca/auto] [--no-write]

`--at`: the case covering that local time (2 s either side); with none there, the strike stretches at each target in
--window s round it, the least damage a cast first (`slow` cases: what the checks say about a fight that hurt little).
"""

import argparse
import bisect
import json
import math
import struct
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[3]
sys.path[:0] = [str(TOOLS), str(ROOT)]

import anomalies  # ruff: ignore[module-import-not-at-top-of-file]
import logwords  # ruff: ignore[module-import-not-at-top-of-file]

from inventory_tracking.builds.warlock.echoing_strike.mechanics import (  # ruff: ignore[module-import-not-at-top-of-file]
    LIFE as BLADE_FRAMES,
    MISSILE,
    POINTER_LAG,
    RANGE,
)
from inventory_tracking.combat.policy import LINE_MARGIN, LINE_SAMPLE, STRIKE_REACH, walls  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.game.layout import (  # ruff: ignore[module-import-not-at-top-of-file]
    ATTACKABLE_FLAG,
    COLD_RESIST,
    IMMUNE,
    MAGIC_RESIST,
    MONSTER_RESISTS,
    PHYSICAL_RESIST,
    UNIT_FLAGS,
)
from inventory_tracking.game.view import Viewport  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.levels.doors import CLOSED_MODE, Door, door_sizes  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.levels.model import Ground, Walkable  # ruff: ignore[module-import-not-at-top-of-file]


OUT = ROOT / 'rca' / 'auto'
STATES = ROOT / 'pricing' / 'raw' / 'game-excel' / 'states.txt'
ECHOING_STRIKE = 388  # skills.txt (builds/warlock/skills.py ECHOING_STRIKE; not imported: it registers the names)
STRIKE_TYPES = (PHYSICAL_RESIST, COLD_RESIST, MAGIC_RESIST)  # the blade, the gear's cold, Hex: Purge (mark.py)
RATE = 25.0  # frames a second
CONTACT = 2.5  # units between a blade and the target that make a contact (no-hits-findings.md: 2.5)
SHORT_BLADE = 30  # frames: a blade gone sooner was stopped (it lives BLADE_FRAMES, 38, free)
AIM_OFF = 3.0  # units of the target off the aim line: the blades (1.9 either side at the spawn) pass it by
HIDING_STATES = {146: 'invis', 153: 'cloak_of_shadows', 156: 'cloaked', 159: 'fade'}  # states.txt rows
MODE_NAMES = ('death', 'neutral', 'walk', 'get hit', 'attack 1', 'attack 2', 'block', 'cast', 'skill 1', 'skill 2',
              'skill 3', 'skill 4', 'dead', 'knockback', 'sequence', 'run')  # fmt: skip
SEQUENCE = 14  # monster mode: a sequence (a frog or a Water Watcher submerged, a burrower under the sand)
AT_SLACK = 2.0  # seconds either side of --at that pick a case
SLOW_TOP = 3  # the slow stretches looked at when --at finds no case
HELD = 0.3  # a cause's score from which it is the verdict
STRONG = 0.5  # a share of frames or casts from which a cause is taken as holding


@dataclass
class Cause:
    name: str  # door, wall, immune, untargetable, mode, range, pointer, skill, blades
    score: float  # 0-1: how much of the case it explains
    verdict: str  # one line
    evidence: list[str] = field(default_factory=list)


@dataclass
class Report:
    case: dict  # anomalies.Case.as_json()
    line: str  # the ANOMALY line
    causes: list[Cause]
    slow: bool = False  # not a NO_DAMAGE case: a stretch --at picked for little damage a cast
    path: str = ''

    @property
    def top(self) -> str:
        held = [c for c in self.causes if c.score >= HELD]
        if held:
            return f'{held[0].name}: {held[0].verdict} ({held[0].score:.2f})'
        hints = [c for c in self.causes if c.score > 0]
        if not hints:
            return 'unexplained'
        return f'unexplained (hint: {hints[0].name}: {hints[0].verdict}, {hints[0].score:.2f})'

    def summary(self) -> str:
        """The watch's one line."""
        what = 'slow stretch' if self.slow else 'NO_DAMAGE RCA'
        d = self.case['data']
        return f'{what}: {self.case["take"]} {self.case["start"][11:19]} unit {d["unit"]}: {self.top}; {self.path}'


# --- The take's parts --------------------------------------------------------------------------------------------


def ground_of(directory: Path) -> Ground | None:
    """The level's grids the recorder copied beside the take (as echoing_strike/sim/situation.py `load_ground`)."""
    found = anomalies.rows(directory, 'level.json')
    if not found:
        return None
    grids = tuple(Walkable(**grid) for grid in found[0].get('ground', ()))
    return Ground(grids) if grids else None


def state_names(path: Path = STATES) -> dict[int, str]:
    try:
        rows = path.read_text(errors='replace').splitlines()[1:]
    except OSError:
        return {}
    return {i: row.split('\t')[0] for i, row in enumerate(rows)}


def states_on(words: str) -> list[int]:
    """The states set in a unit's state words (hex, STATE_RUN: states 0-255, 32 a little-endian word)."""
    raw = bytes.fromhex(words or '')
    return [8 * i + bit for i, byte in enumerate(raw) for bit in range(8) if byte >> bit & 1]


def blade_place(path: str) -> tuple[float, float] | None:
    """A missile's place from its path record (echoing_strike/hits.py `path_position`); None when unread."""
    if not path:
        return None
    fx, x, fy, y = struct.unpack_from('<HHHH', bytes.fromhex(path))
    return x + fx / 65536, y + fy / 65536


def along(start: tuple[float, float], end: tuple[float, float]) -> list[tuple[float, float]]:
    """The points looked at on a line (policy.py `clear_line`: LINE_SAMPLE apart, LINE_MARGIN off both ends)."""
    length = math.dist(start, end)
    if length <= 2 * LINE_MARGIN:
        return []
    steps = max(int((length - 2 * LINE_MARGIN) / LINE_SAMPLE), 1)
    found = []
    for index in range(steps + 1):
        t = min((LINE_MARGIN + index * LINE_SAMPLE) / length, (length - LINE_MARGIN) / length)
        found.append((start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t))
    return found


def off_line(origin, aim, point) -> float:
    """How far `point` lies from the ray origin -> aim (beyond the origin), in units; inf behind the origin."""
    dx, dy = aim[0] - origin[0], aim[1] - origin[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = point[0] - origin[0], point[1] - origin[1]
    if px * ux + py * uy < 0:
        return math.inf
    return abs(px * uy - py * ux)


def share(part: int, whole: int) -> str:
    return f'{part}/{whole}' + (f' ({100 * part / whole:.0f}%)' if whole else '')


# --- The checks ------------------------------------------------------------------------------------------------------


@dataclass
class Window:
    """What the checks read: the case's frames with the target, its casts, the take's other parts."""

    take: anomalies.Take
    read: anomalies.StrikeRead
    unit: int
    start: float
    end: float  # the last strike + DAMAGE_LAG
    casts: list[float]
    frames: list[dict]  # the frames of [start, end] the cases count
    rows: list[tuple[dict, list]]  # (frame, the target's row) where it is in the read
    records: list[dict] = field(default_factory=list)  # records.jsonl's rows up to the end (read once)

    @property
    def lost(self) -> int:
        """The target's life of 128 lost in the window (a slow stretch's; 0 in a NO_DAMAGE case)."""
        lives = [m[5] for _, m in self.rows]
        return lives[0] - min(lives) if lives else 0

    def place(self, frame: dict) -> tuple[float, float]:
        return frame['p'][3], frame['p'][4]


def window_of(take: anomalies.Take, read: anomalies.StrikeRead, data: dict) -> Window:
    unit, start = int(data['unit']), float(data['from'])
    end = float(data['to']) + anomalies.DAMAGE_LAG
    i, j = bisect.bisect_left(read.frame_times, start), bisect.bisect_right(read.frame_times, end)
    frames = [f for f in take.frames[i:j] if not anomalies.outside(f)]
    rows = [(f, m) for f in frames for m in f.get('m', ()) if m[0] == unit]
    casts = [c for c in read.by_target.get(unit, read.casts) if start <= c <= float(data['to']) + anomalies.CAST_AFTER]
    records = [row for row in anomalies.rows(take.directory, 'records.jsonl') if row.get('t', 0) <= end]
    return Window(take, read, unit, start, end, casts, frames, rows, records)


def passed_doors(take: anomalies.Take, upto: float) -> dict[tuple[float, float], float]:
    """The doors (by place: a door's unit is made again as rooms load) read closed that a live hostile or the
    character stood inside before `upto`: the hunt counts them open (levels/doors.py PassedDoors), the time first."""
    found: dict[tuple[float, float], float] = {}
    for frame in take.frames:
        if frame['t'] > upto:
            break
        standing = [frame['p'][3:5], *(m[3:5] for m in anomalies.hostiles(frame))]
        for d in frame.get('d') or ():
            door = Door(d[0], d[1], d[2], float(d[3]), float(d[4]))
            if door.mode == CLOSED_MODE and (door.x, door.y) not in found and any(map(door.within, standing)):
                found[door.x, door.y] = frame['t']
    return found


def doors_check(w: Window) -> Cause:
    sizes = door_sizes()
    passed = passed_doors(w.take, w.end)
    closed_on, open_on, seen = 0, 0, Counter()
    for frame, m in w.rows:
        line = along(w.place(frame), (m[3], m[4]))
        blocking = False
        for d in frame.get('d') or ():
            if d[1] not in sizes:
                continue
            door = Door(d[0], d[1], d[2], float(d[3]), float(d[4]))
            shut = Door(door.unit_id, door.txt_id, CLOSED_MODE, door.x, door.y)  # its frame, whatever its mode
            if not any(map(shut.blocks, line)):
                continue
            key = (door.txt_id, door.mode, door.x, door.y)
            seen[key] += 1
            if door.mode == CLOSED_MODE:
                blocking = True
            else:
                open_on += 1
        closed_on += blocking
    whole = len(w.rows)
    evidence = []
    for (txt, mode, x, y), n in seen.most_common():
        state = 'closed' if mode == CLOSED_MODE else ('opening' if mode == 1 else 'open')
        hunt = ''
        if mode == CLOSED_MODE and (x, y) in passed:
            hunt = f'; the hunt counts it passed (open) since {w.take.local(passed[x, y]):%H:%M:%S}'
        evidence.append(
            f'door class {txt} at ({x:.0f}, {y:.0f}), {state}, on the line in {share(n, whole)} frames{hunt}'
        )
    if not seen:
        return Cause('door', 0.0, f'no door on the line ({whole} frames)', [f'{len(sizes)} door classes looked for'])
    score = 0.9 * closed_on / whole if whole else 0.0
    verdict = f'a closed door on the line in {share(closed_on, whole)} frames' if closed_on else 'only open doors'
    return Cause(
        'door', score, verdict, evidence + ([f'open doors on the line in {open_on} frame-doors'] if open_on else [])
    )


def walls_check(w: Window, ground: Ground | None) -> Cause:
    if ground is None:
        return Cause('wall', 0.0, 'no level grids in the take (level.json)', [])
    blocked = walls(ground)
    assert blocked is not None
    stopped = unread = 0
    first: tuple[float, float] | None = None
    for frame, m in w.rows:
        line = along(w.place(frame), (m[3], m[4]))
        flight = [p for p in line if ground.flyable(*p) is False]
        hole = [p for p in line if ground.walkable(*p) is None]
        stopped += bool(flight)
        unread += bool(hole) and not flight
        if flight and first is None:
            first = flight[0]
    whole = len(w.rows)
    evidence = [
        f'{len(ground)} grids; the flight layer blocks the line in {share(stopped, whole)} frames'
        + (f', first at ({first[0]:.1f}, {first[1]:.1f})' if first else ''),
        f'unread cells (no grid) on it in {share(unread, whole)} more frames',
    ]
    score = 0.8 * stopped / whole + 0.4 * unread / whole if whole else 0.0
    verdict = 'walls on the line' if stopped else ('unread cells on the line' if unread else 'the line is clear')
    return Cause('wall', min(score, 0.8), verdict, evidence)


def stats_of(w: Window) -> tuple[dict[str, int], str]:
    """The target's stat list and state words last known at the case's end: units.jsonl, then its `stats` events."""
    stats: dict[str, int] = {}
    states = ''
    for row in anomalies.rows(w.take.directory, 'units.jsonl'):
        if row.get('unit') == w.unit:
            stats = dict(row.get('stats') or {})
    for e in w.take.events:
        if e.get('event') == 'stats' and e.get('unit') == w.unit and e['t'] <= w.end:
            stats.update(e.get('stats') or {})
            states = e.get('states') or states
    return stats, states


def immune_check(w: Window) -> Cause:
    stats, _ = stats_of(w)
    if not stats:
        return Cause('immune', 0.0, 'no stat list of the target in the take', [])
    resists = {name: int(stats.get(str(stat), 0)) for stat, name in MONSTER_RESISTS.items()}
    immune = [MONSTER_RESISTS[s] for s in STRIKE_TYPES if int(stats.get(str(s), 0)) >= IMMUNE]
    text = ', '.join(f'{k} {v}' for k, v in resists.items())
    if len(immune) == len(STRIKE_TYPES):
        return Cause('immune', 0.9, 'immune to every damage type of the strike', [f'resists {text}'])
    if immune:
        return Cause('immune', 0.15 * len(immune), f'immune to {", ".join(immune)} only', [f'resists {text}'])
    return Cause('immune', 0.0, 'not immune to the strike', [f'resists {text}'])


def records_of(w: Window) -> list[tuple[float, str, str, str]]:
    """(t, record, states, skill) of the target's records.jsonl rows in the window (and the last before it)."""
    found: list[tuple[float, str, str, str]] = []
    for row in w.records:
        for unit, record, states, skill in row.get('u', ()):
            if unit == w.unit:
                if row['t'] < w.start:
                    found = [(row['t'], record, states, skill)]
                else:
                    found.append((row['t'], record, states, skill))
    return found


def untargetable_check(w: Window, names: dict[int, str]) -> Cause:
    records = records_of(w)
    _, words = stats_of(w)
    flags = []
    for _, record, _, _ in records:
        raw = bytes.fromhex(record)
        if len(raw) >= UNIT_FLAGS + 4:
            flags.append(struct.unpack_from('<I', raw, UNIT_FLAGS)[0])
    on = set(states_on(words))
    for _, _, states, _ in records:
        on |= set(states_on(states))
    named = ', '.join(f'{names.get(s, s)} ({s})' for s in sorted(on)) or 'none'
    hiding = [HIDING_STATES[s] for s in sorted(on) if s in HIDING_STATES]
    evidence = [f'states: {named}']
    if flags:
        clear = [f for f in flags if not f & ATTACKABLE_FLAG]
        words = ', '.join(sorted({hex(f) for f in flags}))
        told = f'"can be attacked" ({hex(ATTACKABLE_FLAG)}) clear in {share(len(clear), len(flags))}'
        evidence.insert(0, f'unit flags {words} in {len(flags)} records; {told}')
        if clear:
            return Cause(
                'untargetable', 0.95 * len(clear) / len(flags), 'the game says it cannot be attacked', evidence
            )
    else:
        evidence.insert(0, 'no record of the target in records.jsonl: its flag word unread')
    if hiding:
        return Cause('untargetable', 0.6, f'in the state {", ".join(hiding)}', evidence)
    return Cause('untargetable', 0.0, 'attackable' if flags else 'unknown (no record)', evidence)


def mode_check(w: Window) -> Cause:
    """The target's modes while it was struck at (a death after the last strike is no cause)."""
    last = w.end - anomalies.DAMAGE_LAG
    modes = Counter(m[2] for f, m in w.rows if f['t'] <= last)
    named = ', '.join(f'{MODE_NAMES[k] if 0 <= k < len(MODE_NAMES) else k} ({k}) {n}' for k, n in modes.most_common())
    whole = sum(f['t'] <= last for f in w.frames)
    missing = whole - sum(modes.values())
    seen = sum(modes.values())
    evidence = [f'modes in {seen} frames: {named or "-"}', f'not in the read in {share(missing, whole)} frames']
    dead = sum(n for k, n in modes.items() if k in anomalies.DEAD)
    hidden = modes.get(SEQUENCE, 0)
    if whole and missing / whole >= STRONG:
        return Cause('mode', 0.95 * missing / whole, 'the target is not in the read', evidence)
    if dead:
        return Cause('mode', 0.95 * dead / max(seen, 1), 'struck at a dead target', evidence)
    if hidden:
        return Cause('mode', 0.8 * hidden / max(seen, 1), 'in a sequence (submerged, burrowed)', evidence)
    return Cause('mode', 0.0, 'alive and in the read', evidence)


def range_check(w: Window) -> Cause:
    away = [math.dist(w.place(f), (m[3], m[4])) for f, m in w.rows]
    if not away:
        return Cause('range', 0.0, 'no distance (the target not in the read)', [])
    beyond = sum(a > RANGE for a in away)
    reach = sum(a > STRIKE_REACH for a in away)
    evidence = [f'distance {min(away):.1f}-{max(away):.1f}, median {sorted(away)[len(away) // 2]:.1f}',
                f'beyond the blades\' {RANGE:.1f} in {share(beyond, len(away))} frames, beyond the hunt\'s '
                f'{STRIKE_REACH:.0f} in {share(reach, len(away))}']  # fmt: skip
    score = 0.75 * beyond / len(away) + 0.1 * (reach - beyond) / len(away)
    verdict = "out of the blades' reach" if beyond else ('at the edge of reach' if reach else 'within reach')
    return Cause('range', score, verdict, evidence)


def frame_at(w: Window, t: float) -> dict | None:
    times = w.read.frame_times
    i = bisect.bisect_right(times, t) - 1
    return w.take.frames[i] if i >= 0 else None


def target_at(frame: dict, unit: int) -> tuple[float, float] | None:
    return next(((m[3], m[4]) for m in frame.get('m', ()) if m[0] == unit), None)


def pointer_check(w: Window) -> Cause:
    sent = [e for e in w.take.events if e.get('event') == 'sent' and e.get('input') == 'move' and e.get('f')]
    sent_times = [e['t'] for e in sent]
    game_off, sent_off = [], []
    for c in w.casts:
        frame = frame_at(w, c - POINTER_LAG / RATE)
        if frame is None or not frame.get('rect') or not frame.get('in'):
            continue
        here, there = w.place(frame), target_at(frame, w.unit)
        if there is None:
            continue
        view = Viewport.of(tuple(frame['rect']))
        fx, fy = frame['in'][3], frame['in'][4]
        if fx is not None:
            game_off.append(off_line(here, view.world(here, fx, fy), there))
        i = bisect.bisect_right(sent_times, c) - 1
        if i >= 0:
            f = sent[i]['f']
            sent_off.append(off_line(here, view.world(here, f[0], f[1]), there))
    drift = [e for e in w.take.events if e.get('event') == 'pointer_check' and w.start <= e['t'] <= w.end]

    def told(offs: list[float]) -> str:
        far = sum(o > AIM_OFF for o in offs)
        finite = sorted(o for o in offs if o < math.inf)
        median = f'median {finite[len(finite) // 2]:.1f}' if finite else 'all behind'
        return f'{median}, over {AIM_OFF:.0f} in {share(far, len(offs))}'

    evidence = [f'the game\'s pointer off the target\'s line at the casts\' aims: {told(game_off)}',
                f'the last sent move off it: {told(sent_off)}']  # fmt: skip
    evidence += [f'pointer_check at {w.take.local(e["t"]):%H:%M:%S}: drift {e.get("drift")} (limit {e.get("limit")})'
                 for e in drift]  # fmt: skip
    if not game_off:
        return Cause('pointer', 0.0, 'no aim read (no casts or no pointer)', evidence)
    far = sum(o > AIM_OFF for o in game_off) / len(game_off)
    sent_far = sum(o > AIM_OFF for o in sent_off) / len(sent_off) if sent_off else 0.0
    score = 0.7 * far + (0.1 if drift else 0.0)
    if far >= STRONG and sent_far < STRONG:
        verdict = "the game's pointer was not where the macro sent it"
    elif far >= STRONG:
        verdict = 'the macro aimed off the target'
    else:
        verdict = 'aimed at the target'
    return Cause('pointer', min(score, 0.8), verdict, evidence)


def skill_check(w: Window) -> Cause:
    rights = Counter(f['p'][6] for f in w.frames if len(f['p']) > 6)
    modes = Counter(f['p'][1] for f in w.frames)
    used: Counter[int] = Counter()
    player = w.frames[0]['p'][0] if w.frames else None
    for row in w.records:
        if row.get('t', 0) < w.start:
            continue
        for unit, _, _, skill in row.get('u', ()):
            if unit == player:
                raw = bytes.fromhex(skill or '')
                if len(raw) >= 2:
                    used[struct.unpack_from('<H', raw)[0]] += 1
    events = [e for e in w.take.events if e.get('event') == 'cast' and w.start <= e['t'] <= w.end]
    evidence = [
        f'right skill in the frames: {", ".join(f"{k} x{n}" for k, n in rights.most_common()) or "-"} '
        f'(Echoing Strike {ECHOING_STRIKE})',
        f'skill in use (records.jsonl): {", ".join(f"{k} x{n}" for k, n in used.most_common()) or "not recorded"}',
        f'character modes: {", ".join(f"{k} x{n}" for k, n in modes.most_common())}',
        f'{len(w.casts)} {w.read.counted} given to the target, {len(events)} `cast` events in the window',
    ]
    if not w.casts:
        return Cause('skill', 0.7, 'no cast came of the strikes', evidence)
    others = sum(n for k, n in rights.items() if k != ECHOING_STRIKE)
    if rights and others / sum(rights.values()) >= STRONG:
        return Cause('skill', 0.7, 'the right skill was not Echoing Strike', evidence)
    if w.read.counted != 'blade casts':
        return Cause('skill', 0.2, 'no blades recorded: the casts may not be Echoing Strike', evidence)
    return Cause('skill', 0.0, 'Echoing Strike, its blades seen', evidence)


def blades_check(w: Window, ground: Ground | None) -> Cause:
    """Each cast's blades: their frames, a contact with the target, the furthest they flew."""
    tracks: dict[int, list[tuple[float, tuple[float, float]]]] = {}
    i = bisect.bisect_left(w.read.frame_times, w.start)
    j = bisect.bisect_right(w.read.frame_times, w.end + BLADE_FRAMES / RATE)
    for frame in w.take.frames[i:j]:
        for x in frame.get('x') or ():
            place = blade_place(x[5]) if x[1] == MISSILE and len(x) > 5 else None
            if place is not None:
                tracks.setdefault(x[0], []).append((frame['t'], place))
    casts = sorted(w.casts)
    by_cast: dict[float, list[list[tuple[float, tuple[float, float]]]]] = {}
    for track in tracks.values():
        k = bisect.bisect_right(casts, track[0][0] + 1e-6) - 1
        if k >= 0 and track[0][0] - casts[k] <= anomalies.BLADE_BIRTH + 0.05:
            by_cast.setdefault(casts[k], []).append(track)
    if not by_cast:
        return Cause('blades', 0.0, 'no blades recorded for the casts', [])
    touched = short = 0
    stops: Counter[str] = Counter()
    reach: list[float] = []
    for c, blades in by_cast.items():
        frame = frame_at(w, c)
        origin = w.place(frame) if frame else blades[0][0][1]
        hit = False
        for track in blades:
            reach.append(max(math.dist(origin, p) for _, p in track))
            if len(track) < SHORT_BLADE:
                short += 1
                last = track[-1][1]
                if ground is not None:
                    what = 'a wall' if ground.flyable(*last) is False else 'open ground'
                    stops[what] += 1
            for t, p in track:
                f = frame_at(w, t)
                there = target_at(f, w.unit) if f else None
                if there is not None and math.dist(p, there) <= CONTACT:
                    hit = True
                    break
        touched += hit
    blades = sum(len(b) for b in by_cast.values())
    away = [math.dist(w.place(f), (m[3], m[4])) for f, m in w.rows]
    evidence = [
        f'{len(by_cast)} casts with blades, {blades} blades; a blade within {CONTACT} of the target in '
        f'{share(touched, len(by_cast))} casts',
        f'{share(short, blades)} blades gone before {SHORT_BLADE} frames (free: {BLADE_FRAMES})'
        + (f'; their last place: {", ".join(f"{k} x{n}" for k, n in stops.most_common())}' if stops else ''),
        f'furthest a blade flew: median {sorted(reach)[len(reach) // 2]:.1f}'
        + (f' against the target at {sorted(away)[len(away) // 2]:.1f}' if away else ''),
    ]
    stopped = short / blades if blades else 0.0
    if touched and touched / len(by_cast) >= STRONG:
        if w.lost >= anomalies.HURT:
            return Cause('blades', 0.0, f'the blades reached it (it lost {w.lost}/128)', evidence)
        return Cause('blades', 0.25, 'the blades went through it and took nothing (a missed roll?)', evidence)
    if stopped >= STRONG:
        return Cause('blades', 0.6 * stopped, 'the blades were stopped short of it', evidence)
    return Cause('blades', 0.4 * (1 - touched / len(by_cast)), 'the blades passed it by', evidence)


def checked(take: anomalies.Take, read: anomalies.StrikeRead, case: anomalies.Case) -> list[Cause]:
    w = window_of(take, read, case.data)
    ground = ground_of(take.directory)
    names = state_names()
    causes = [doors_check(w), walls_check(w, ground), immune_check(w), untargetable_check(w, names), mode_check(w),
              range_check(w), pointer_check(w), skill_check(w), blades_check(w, ground)]  # fmt: skip
    found = sorted(causes, key=lambda c: -c.score)
    door = next(c for c in found if c.name == 'door')
    blades = next(c for c in found if c.name == 'blades')
    if door.score >= 0.3 and blades.verdict.startswith('the blades were stopped'):
        door.evidence.append('the blades were stopped short too: the door verified by the blades')
        door.score = min(door.score + 0.05, 1.0)
        found.sort(key=lambda c: -c.score)
    return found


# --- The report ------------------------------------------------------------------------------------------------------


def said_in(take: anomalies.Take, start: float, end: float, unit: int, most: int = 25) -> list[str]:
    """The service's lines in the case naming the target or the fight's outcome, as said (local times)."""
    told = []
    for t, text in take.lines():
        if start - 1.0 <= t <= end and (str(unit) in text or 'fight (' in text or 'takes no damage' in text):
            told.append(f'{take.local(t):%H:%M:%S.%f}'[:12] + ' ' + text.split(logwords.SAID, 1)[-1][:220])
    return told[:most]


def markdown(report: Report, take: anomalies.Take, read: anomalies.StrikeRead) -> str:
    d = report.case['data']
    start, end = float(d['from']), float(d['to'])
    rows = [f'| {i} | {c.name} | {c.score:.2f} | {c.verdict} |' for i, c in enumerate(report.causes, 1)]
    head = 'A slow stretch (not a NO_DAMAGE case)' if report.slow else 'NO_DAMAGE'
    parts = [
        f'# {head}: {report.case["take"]} {report.case["start"][11:19]}, unit {d["unit"]}',
        '',
        'Automatic RCA (.agents/skills/d2-loop-watch/tools/nodamage.py, the player 2026-10-24 ~20:35: "we need to have '
        'some king of debug message when we expect us to deliver damage but not damaging the mob => and do automatic '
        f'rca for such cases"). Written {datetime.now():%Y-%m-%d %H:%M:%S}; read-only, from the take alone.',
        '',
        f'`{report.line}`',
        '',
        f'**Verdict: {report.top}**',
        '',
        '| # | cause | score | what the take says |',
        '| --- | --- | --- | --- |',
        *rows,
        '',
        '## Evidence',
        '',
    ]
    for c in report.causes:
        parts += [f'### {c.name} ({c.score:.2f}): {c.verdict}', '', *(f'- {e}' for e in c.evidence), '']
    parts += ["## The service's lines", '', '```', *said_in(take, start, end, int(d['unit'])), '```', '']
    parts += ['## Deeper', '', f'- `python3 .agents/skills/d2-loop-watch/tools/anomalies.py {take.name} --json`',
              f'- `python3 .agents/skills/d2-rca/tools/session.py unit {take.name} {d["unit"]}`',
              f'- frames {take.local(start):%H:%M:%S}-{take.local(end):%H:%M:%S}: '
              f'{read.counted}, `x` blades, `d` doors, `in` pointer', '']  # fmt: skip
    return '\n'.join(parts)


def written(report: Report, take: anomalies.Take, read: anomalies.StrikeRead, out: Path) -> Path:
    start = datetime.fromisoformat(report.case['start'])
    directory = out / f'{start:%Y-%m-%d}'
    directory.mkdir(parents=True, exist_ok=True)
    slow = 'slow-' if report.slow else ''
    path = directory / f'nodamage-{slow}{start:%H%M%S}-{report.case["data"]["unit"]}.md'
    report.path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    path.write_text(markdown(report, take, read))
    return path


# --- Picking the cases -----------------------------------------------------------------------------------------------


def loaded(directory: Path) -> tuple[anomalies.Take, list[tuple[float, float, str]]]:
    """The take with its session's lines, and the windows no case counts in (as anomalies.py `detect`)."""
    take = anomalies.Take.load(directory)
    serve = anomalies.serve_of(directory.name)
    on = None
    if serve is not None and take.frames:
        start, end = take.frames[0]['t'] + take.offset - anomalies.LEAD, take.frames[-1]['t'] + take.offset + 1.0
        take.said = [(epoch - take.offset, text) for epoch, text in serve.between(start, end)] or None
        on = serve.states.get(directory.name)
    return take, anomalies.windows(take, on)


def local_on(take: anomalies.Take, clock: str) -> float:
    """The take's clock at a local HH:MM:SS (the take's date; past midnight the next day)."""
    day = take.local(take.frames[0]['t'])
    at = datetime.combine(day.date(), datetime.strptime(clock, '%H:%M:%S').time())
    if at < day - timedelta(hours=1):
        at += timedelta(days=1)
    return at.timestamp() - take.offset


def slow_cases(read: anomalies.StrikeRead, at: float, window: float) -> list[anomalies.Case]:
    """The per-target stretches round `at` with 2+ casts and no kill, the least life lost a cast first."""
    near = [
        s
        for s in read.stretches()
        if s.unit and not s.killed and len(s.casts) >= 2 and s.start <= at + window and s.end >= at - window
    ]
    near.sort(key=lambda s: (s.lost / len(s.casts), -len(s.casts)))
    return [read.case(s) for s in near[:SLOW_TOP]]


def reports(
    directory: Path,
    at: str | None = None,
    unit: int | None = None,
    window: float = 20.0,
    limits: anomalies.Limits | None = None,
    out: Path | None = OUT,
) -> list[Report]:
    take, skip = loaded(directory)
    if not take.frames:
        return []
    read = anomalies.StrikeRead(take)
    cases = anomalies.no_damage(take, skip, limits or anomalies.Limits())
    slow = False
    if at is not None:
        t = local_on(take, at)
        cases = [c for c in cases if c.data['from'] - AT_SLACK <= t <= c.data['to'] + AT_SLACK]
        if not cases and unit is None:
            cases, slow = slow_cases(read, t, window), True
    if unit is not None:
        cases = [c for c in cases if c.data['unit'] == unit]
    found = []
    for case in cases:
        report = Report(case.as_json(), case.line(), checked(take, read, case), slow=slow)
        if out is not None:
            written(report, take, read, out)
        found.append(report)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('takes', nargs='*', help='take directories or names (runs/combat/<name>)')
    parser.add_argument('--at', help='local HH:MM:SS: the case covering it, else the slow stretches round it')
    parser.add_argument('--unit', type=int)
    parser.add_argument('--window', type=float, default=20.0, help='seconds round --at for the slow stretches')
    parser.add_argument('--since', type=logwords.local)
    parser.add_argument('--until', type=logwords.local)
    parser.add_argument('--dry-casts', type=int, default=anomalies.Limits.dry_casts)
    parser.add_argument('--dry-seconds', type=float, default=anomalies.Limits.dry_seconds)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--no-write', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    directories = [Path(t) if Path(t).is_dir() else anomalies.COMBAT / t for t in args.takes]
    if args.since is not None:
        directories += anomalies.takes_since(args.since, args.until)
    if not directories:
        parser.error('a take or --since')
    limits = anomalies.Limits(dry_casts=args.dry_casts, dry_seconds=args.dry_seconds)
    found: list[Report] = []
    for directory in directories:
        try:
            got = reports(directory, args.at, args.unit, args.window, limits, None if args.no_write else args.out)
        except (OSError, ValueError, KeyError, IndexError) as error:
            print(f'{directory.name}: unread ({error})', file=sys.stderr)
            continue
        found += got
        if not args.json:
            for report in got:
                print(report.summary(), flush=True)
    if args.json:
        print(json.dumps([asdict(r) | {'top': r.top} for r in found], indent=1))


if __name__ == '__main__':
    main()
