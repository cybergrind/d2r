"""The anomalies of a closed combat take: the character idle, a long fight with one target, jumps that go nowhere.

The player, 2026-10-21 ~21:08: "do automatic searching-rca-fixing loop for all cases where we wereen't active for a long
time / this should become a part of monitoring loop: - monitor all time that we weren't moving/killing/doing something
- all the cases where we were engaging with mob for a more than 30 seconds - all cases where we have jumped a lot in
short period of time staying withing small area (back-forwards, stuck, weren't able to engage in fight/kill things)".

A take is `inventory_tracking/runs/combat/<UTC>-<area>/`: frames at ~25/s (`p` the character: unit, mode, area, x, y,
skills, life, max, mana, max; `m` the units: unit, class, mode, x, y, life of 128, max, ?, owner, ally), events (the
kills, casts, the service's `log` lines on the take's clock, `state` with the pursuit's goal) and the manifest's clock.
The log lines and the loop's state at the take's open come from the session's probe.log (local time = the UTC name +
3 h); the take's own `log` events only without it (a take cut by a restart lost its last ones).

- **IDLE**: >= --idle s (8) still: no move (<= --still units from where it began), no strike (STRIKE: a cast that is no
  strike, a Defiler summoned, is no activity: 20261021T175851Z-123), no kill, no hostile falling HURT/128 under its best
  (127/128 flickers), in a field level with the loop on; pieces of PIECE s or more at one spot MERGE_GAP s apart are one
  case. Not counted: a panel open, town, the lobby or a load (`game` false), the character dead, the loop off (by the
  player or a stop), the Throne's wave wait (after its WAVES line in area 131), a Herald's wait up to its N s while no
  hostile is near, the loop's own wait (WAITING), a restart's safe point. Facts: the hostiles within --near (30), the
  nearest, the life lost, the pursuit's goal then; `cause?:` the log's kinds in it (numbers folded, top 3).
- **LONG_FIGHT**: one target struck at (STRIKE lines name its unit) for > --fight s (30), from the first strike to its
  death, its leaving the read, or the last strike before a gap of FIGHT_GAP s (let go); an agenda's elite target
  (ELITE_TARGET) likewise from the first strike near it to its death. Facts: its class (monstats.txt *hcIdx), elite or
  monster and the agenda's tier, its life of 128 at the start and end and over the slowest 10 s, our casts a second,
  jumps, our life lost.
- **JUMP_CLUSTER**: >= --jumps (6) landings (the position jumping > JUMP_STEP units between frames: Teleport, Blade
  Warp) in --jump-window s (15) all within --jump-radius (25) of their centroid, with <= 1 kill in the window, the
  cluster lasting --jump-least s (5) or more. Facts: the jumps, the radius, the kills, the jump casts said; `reasons:`
  the jumps' reasons from the log (JUMP_REASON).
- **NO_DAMAGE** (the player, 2026-10-24 ~20:35: "we need to have some king of debug message when we expect us to
  deliver damage but not damaging the mob => and do automatic rca for such cases"): one target struck at (the
  decisions' `Strike` target and the STRIKE lines, STRIKE_GAP s apart at most) with >= --dry-casts (4) casts of its
  own (each blade cast, BLADE births in the frames, given to the target struck last before it; the `cast` events
  where a take has no blades) over >= --dry-seconds (1.5) s, and its life never falling: no `hit` on it, its life of
  128 never HURT under its start, no kill, up to DAMAGE_LAG s after the last strike. Also a stretch of strikes at
  anything with that many casts and no `hit` on any hostile (`no hit on anything`). Facts: the target (elite or
  monster, its class, the agenda's or its stats' Herald tier), its distance, the casts and the life before and after.
  tools/nodamage.py RCAs each case (watch.py runs it).

One line per case, `ANOMALY: <kind> <take> <local from-to> <seconds>s: <facts>; cause?: <top kinds>` (watch.py says
them when a take closes), or `--json`. Stdlib only (watch.py runs with a plain python3).

    python3 .agents/skills/d2-loop-watch/tools/anomalies.py <take>... | --since 'YYYY-MM-DD HH:MM' [--until ...]
        [--idle 8] [--still 1.5] [--near 30] [--fight 30] [--jumps 6] [--jump-window 15] [--jump-radius 25]
        [--jump-least 5] [--dry-casts 4] [--dry-seconds 1.5] [--json] [--summary]
"""

import argparse
import bisect
import gzip
import json
import math
import sys
import zlib
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import logwords
from logwords import (
    ELITE_TARGET,
    HERALD_WAIT,
    JUMP_CAST,
    JUMP_REASON,
    LOOP_OFF,
    LOOP_ON,
    LOOP_RESUMED,
    LOOP_STOPPED,
    NOISE,
    NUMBER,
    OPENED,
    PLACE,
    RESUMED_OFF,
    SAFE_POINT,
    SAID,
    STRIKE,
    WAITING,
    WAVES,
)


ROOT = Path(__file__).resolve().parents[4]
COMBAT = ROOT / 'inventory_tracking' / 'runs' / 'combat'
MONSTATS = ROOT / 'pricing' / 'raw' / 'game-excel' / 'monstats.txt'
PREFIX = 'ANOMALY:'

TOWNS = frozenset({1, 40, 75, 103, 109})  # Rogue Encampment, Lut Gholein, Kurast Docks, Pandemonium Fortress, Harrogath
THRONE = 131  # Throne of Destruction: the wave wait
NO_OWNER = 4294967295
DEAD = (0, 12)  # monster modes: dying, dead
CHARACTER_DEAD = (0, 17)  # player modes: dying, dead
HURT = 2  # of 128: a hostile's life this far under its most since a stretch began (127/128 flickers with regeneration)
LEAD = 3.0  # seconds before a stretch whose log lines may name its cause (the stand's reason is said as it begins)
FIGHT_GAP = 12.0  # seconds with no strike at a target: the fight with it is let go
SLOW_WINDOW = 10.0  # seconds: a long fight's slowest stretch
JUMP_STEP = 5.0  # units between two frames: a jump (Teleport, Blade Warp), not a walk
MAX_KILLS = 1  # kills in a jump window that still make it a cluster
TOP = 3  # log kinds a case names
HERALD = 'Herald wait'
WAVE = 'wave wait'
PIECE = 2.0  # seconds: the shortest still that is a piece of an IDLE
MERGE_GAP = 4.0  # seconds between two still pieces at one spot that make one IDLE
# NO_DAMAGE (2026-10-24)
BLADE = 706  # missiles.txt: Echoing Strike's blade (builds/warlock/echoing_strike/mechanics.py MISSILE)
BLADE_BIRTH = 0.1  # seconds: blades first seen this close together are one cast (five spawn in a frame or two)
STRIKE_GAP = 1.5  # seconds between two strikes at one target that keep one stretch of strikes at it
CAST_AFTER = 0.5  # seconds after its strike a cast may begin and still be that strike's (the press, the pointer lag)
DAMAGE_LAG = 1.0  # seconds after the last strike its damage may still show (blades fly ~0.8 s; the server batches)
NO_HIT = 'nothing'  # the `what` of a stretch of strikes at anything with no hit on any hostile


@dataclass(frozen=True)
class Limits:
    idle: float = 8.0  # seconds
    still: float = 1.5  # units
    near: float = 30.0  # units
    fight: float = 30.0  # seconds
    jumps: int = 6
    jump_window: float = 15.0  # seconds
    jump_radius: float = 25.0  # units
    jump_least: float = 5.0  # seconds a cluster lasts at least (6 hops in 3 s cost 3 s: no case)
    dry_casts: int = 4  # NO_DAMAGE: casts at one target with its life not falling
    dry_seconds: float = 1.5  # NO_DAMAGE: ... over this long at least


@dataclass
class Case:
    kind: str  # IDLE, LONG_FIGHT, JUMP_CLUSTER, NO_DAMAGE
    take: str
    start: datetime  # local
    end: datetime
    facts: str
    cause: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    @property
    def seconds(self) -> float:
        return (self.end - self.start).total_seconds()

    def line(self) -> str:
        word = 'reasons' if self.kind == 'JUMP_CLUSTER' else 'cause?'
        cause = '; '.join(self.cause) or 'none said'
        return (
            f'{PREFIX} {self.kind} {self.take} {self.start:%H:%M:%S}-{self.end:%H:%M:%S} {self.seconds:.0f}s: '
            f'{self.facts}; {word}: {cause}'
        )

    def as_json(self) -> dict:
        found = asdict(self)
        found.update(start=self.start.isoformat(), end=self.end.isoformat(), seconds=round(self.seconds, 1))
        return found


# --- The take ---------------------------------------------------------------------------------------------------------


def rows(directory: Path, name: str) -> list[dict]:
    """A take's file, plain or packed; an open take's gzip ends mid-stream and a line may be torn: what reads. The plain
    file first while it is there: the packer (takes/retain.py) writes the gzip beside it and removes the plain file only
    once the gzip is whole, so a gzip next to a plain file is still being written (two false LONG_FIGHTs on 2026-10-24,
    rca/2026-10-24/slow-fights-findings.md)."""
    packed, plain = directory / f'{name}.gz', directory / name
    found: list[dict] = []
    try:
        if plain.exists():
            with plain.open(encoding='utf-8', errors='replace') as handle:
                parsed(handle, found)
        elif packed.exists():
            with gzip.open(packed, 'rt', encoding='utf-8', errors='replace') as handle:
                parsed(handle, found)
    except OSError, EOFError, zlib.error:
        pass
    return found


def parsed(handle: Iterable[str], into: list[dict]) -> None:
    """Each whole JSON line into `into` (kept as far as it got when the stream breaks)."""
    for text in handle:
        try:
            into.append(json.loads(text))
        except ValueError:
            continue


@dataclass
class Take:
    directory: Path
    manifest: dict
    frames: list[dict]  # those with the character (`p`)
    events: list[dict]
    offset: float  # the wall clock minus the take's monotonic clock
    said: list[tuple[float, str]] | None = None  # the session's probe.log lines in the take, on its clock

    @classmethod
    def load(cls, directory: Path) -> Take:
        manifest = json.loads((directory / 'manifest.json').read_text())
        frames = [f for f in rows(directory, 'frames.jsonl') if f.get('p') and 't' in f]
        events = [e for e in rows(directory, 'events.jsonl') if 't' in e]
        clock = manifest.get('clock')
        if clock:
            offset = clock['wall'] - clock['monotonic']
        else:
            first = frames[0]['t'] if frames else 0.0
            offset = datetime.fromisoformat(manifest['started_at']).timestamp() - first
        return cls(directory, manifest, frames, events, offset)

    @property
    def name(self) -> str:
        return self.directory.name

    @property
    def area(self) -> int:
        return int(self.manifest.get('area', 0))

    def local(self, t: float) -> datetime:
        return datetime.fromtimestamp(t + self.offset)

    def times(self, kind: str) -> list[float]:
        return sorted(e['t'] for e in self.events if e.get('event') == kind)

    def lines(self) -> list[tuple[float, str]]:
        """The service's log lines while the take was open, on its clock: probe.log's (a take cut by a restart lost
        its last events: 20261021T171201Z-79 after +74 s), else the take's own `log` events."""
        if self.said is not None:
            return self.said
        return [(e['t'], e.get('text', '')) for e in self.events if e.get('event') == 'log']


# --- The loop's state, the windows not counted ------------------------------------------------------------------------


def switched(line: str) -> bool | None:
    """The loop turned on (True) or off (False) by this line, as watch.py reads it; None: neither."""
    if LOOP_OFF in line or LOOP_STOPPED in line or RESUMED_OFF in line:
        return False
    if LOOP_ON in line or LOOP_RESUMED in line:
        return True
    return None


def session_of(take: str, runs: Path = logwords.RUNS) -> Path | None:
    """The serve session whose log opened the take: the last one started before it (both names in UTC)."""
    stamp = take.split('Z')[0]
    if not runs.exists():
        return None
    started = sorted(d for d in runs.iterdir() if d.is_dir() and d.name.startswith('20') and d.name < stamp + 'Z~')
    return started[-1] if started else None


@dataclass
class Serve:
    """A serve session's probe.log as read so far (watch.py asks again as it grows): each line's epoch and text, and
    the loop's state at each take's open."""

    path: Path
    read: int = 0  # bytes consumed, up to the last whole line
    on: bool = False
    states: dict[str, bool] = field(default_factory=dict)
    epochs: list[float] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)

    def update(self) -> Serve:
        try:
            with self.path.open('rb') as handle:
                handle.seek(self.read)
                chunk = handle.read()
        except OSError:
            return self
        whole = chunk[: chunk.rfind(b'\n') + 1]
        self.read += len(whole)
        epoch = self.epochs[-1] if self.epochs else 0.0
        for line in whole.decode(errors='replace').splitlines():
            at = logwords.stamp(line)
            epoch = at.timestamp() if at is not None else epoch  # a traceback's line: its stamp's
            self.epochs.append(epoch)
            self.texts.append(line)
            state = switched(line)
            if state is not None:
                self.on = state
            elif (m := OPENED.search(line)) is not None:
                self.states[m.group(1)] = self.on
        return self

    def between(self, start: float, end: float) -> list[tuple[float, str]]:
        """The lines stamped in [start, end] (epochs)."""
        a, b = bisect.bisect_left(self.epochs, start), bisect.bisect_right(self.epochs, end)
        return list(zip(self.epochs[a:b], self.texts[a:b], strict=True))


_SESSIONS: dict[Path, Serve] = {}


def serve_of(take: str, runs: Path = logwords.RUNS) -> Serve | None:
    """The take's session log, read (once, then as it grows)."""
    session = session_of(take, runs)
    if session is None or not (session / 'probe.log').exists():
        return None
    serve = _SESSIONS.setdefault(session, Serve(session / 'probe.log'))
    return serve.update()


def loop_at_open(take: str, runs: Path = logwords.RUNS) -> bool | None:
    """Whether the loop was on when the take opened (its session's probe.log); None unknown."""
    serve = serve_of(take, runs)
    return serve.states.get(take) if serve is not None else None


def windows(take: Take, on: bool | None) -> list[tuple[float, float, str]]:
    """The stretches no case counts in: the loop off, the Throne's wave wait, a Herald's, the loop's own wait."""
    found: list[tuple[float, float, str]] = []
    first = take.frames[0]['t'] if take.frames else 0.0
    off_since = first if on is False else None
    for t, text in take.lines():
        state = switched(text)
        if state is False and off_since is None:
            off_since = t
        elif state is True and off_since is not None:
            found.append((off_since, t, 'loop off'))
            off_since = None
        elif (m := HERALD_WAIT.search(text)) is not None:
            found.append((t, t + float(m.group(1)), HERALD))
        elif (m := WAITING.search(text)) is not None:
            found.append((t, t + float(m.group(1)), 'the loop waits'))
        elif SAFE_POINT.search(text):
            found.append((t, math.inf, 'restart'))
        elif take.area == THRONE and WAVES.search(text) and not any(why == WAVE for _, _, why in found):
            found.append((t, math.inf, WAVE))
    if off_since is not None:
        found.append((off_since, math.inf, 'loop off'))
    return found


def outside(frame: dict) -> bool:
    """A frame no case counts: town, the lobby or a load, a panel open, the character dead."""
    p = frame['p']
    return not frame.get('game', True) or bool(frame.get('panels')) or p[2] in TOWNS or p[1] in CHARACTER_DEAD


def hostiles(frame: dict) -> list[list]:
    return [m for m in frame.get('m', ()) if m[8] == NO_OWNER and not m[9] and m[2] not in DEAD and m[5] > 0]


def between(times: list[float], after: float, upto: float) -> int:
    """How many of the sorted `times` fall in (after, upto]."""
    return bisect.bisect_right(times, upto) - bisect.bisect_right(times, after)


# --- The log's kinds ------------------------------------------------------------------------------------------------


def kind_of(text: str) -> str:
    """A log line's kind: past the prefix, numbers folded, up to its first ';', a said line and its pursuit twin one."""
    text = text.split(SAID, 1)[1] if SAID in text else text
    text = PLACE.sub('', NUMBER.sub('N', text)).split(';')[0].strip().removeprefix('pursuit: ').replace(',:', ':')
    text = ' '.join(text.split())
    return (text[:1].lower() + text[1:])[:80]


def kinds(lines: list[tuple[float, str]], start: float, end: float, top: int = TOP) -> list[str]:
    """The most said kinds of the lines in [start, end], the census, gold and the like left out."""
    counted = Counter(
        kind_of(text) for t, text in lines if start <= t <= end and SAID in text and not NOISE.search(text)
    )
    return [f'{k} x{n}' for k, n in counted.most_common(top)]


def reasons(lines: list[tuple[float, str]], start: float, end: float, top: int = TOP) -> list[str]:
    """The jumps' reasons said in [start, end]: the goal toward (folded), a better place, keeping range (why)."""
    counted: Counter[str] = Counter()
    for t, text in lines:
        if start <= t <= end and (m := JUMP_REASON.search(text)) is not None:
            if m.group(1):
                counted[f'toward {NUMBER.sub("N", m.group(1))}'] += 1
            elif m.group(2):
                counted[m.group(2)] += 1
            else:
                counted[m.group(3) + (f': {m.group(4)}' if m.group(4) else '')] += 1
    return [f'{k} x{n}' for k, n in counted.most_common(top)]


def said_before(lines: list[tuple[float, str]], t: float) -> str:
    """The kind of the last line said before `t` (a still nothing names: what the service said last)."""
    told = [text for at, text in lines if at < t and SAID in text and not NOISE.search(text)]
    return kind_of(told[-1]) if told else 'nothing'


def goal_in(take: Take, start: float, end: float) -> str:
    """The pursuit's goal at the stretch's end (the last `state` event in it or before it)."""
    goal = None
    for e in take.events:
        if e.get('event') == 'state' and e['t'] <= end:
            goal = (e.get('pursuit') or {}).get('goal') or goal
        elif e['t'] > end:
            break
    if not goal:
        return 'none'
    return f'{goal.get("do", "?")} {NUMBER.sub("N", str(goal.get("label", "?")))}'


# --- The cases ------------------------------------------------------------------------------------------------------


def idles(take: Take, skip: list[tuple[float, float, str]], limits: Limits) -> list[Case]:
    """The still stretches: no move, no strike, no kill, no hostile hurt; pieces at one spot a few seconds apart (a
    strike at a corpse, a pet's kill between) are one case when their still seconds sum to limits.idle or more."""
    casts, kills = take.times('cast'), take.times('kill')
    lines = take.lines()
    strikes = sorted(t for t, text in lines if STRIKE.search(text))
    frames = take.frames

    def excluded(frame: dict) -> bool:
        """Outside, or in a window not counted; a Herald's wait only while none is near: once its pack is there, a
        still is a fight not made (20261021T175851Z-123 at +12 s: 15 Flayers within 11, no strike for 8.5 s)."""
        if outside(frame):
            return True
        come = any(math.dist(frame['p'][3:5], m[3:5]) <= limits.near for m in hostiles(frame))
        return any(a <= frame['t'] <= b and not (why == HERALD and come) for a, b, why in skip)

    pieces: list[tuple[int, int]] = []

    def close(first: int, last: int) -> None:
        if frames[last]['t'] - frames[first]['t'] >= PIECE:
            pieces.append((first, last))

    start: int | None = None
    best: dict[int, int] = {}  # each hostile's most life of 128 since the stretch began
    for i, frame in enumerate(frames):
        lives = {m[0]: m[5] for m in hostiles(frame)}
        if excluded(frame):
            if start is not None:
                close(start, i - 1)
            start = None
            continue
        if start is None:
            start, best = i, lives
            continue
        before = frames[i - 1]['t']
        hurt = any(life <= best.get(unit, life) - HURT for unit, life in lives.items())
        for unit, life in lives.items():
            best[unit] = max(best.get(unit, life), life)
        moved = math.dist(frames[start]['p'][3:5], frame['p'][3:5]) > limits.still
        busy = between(strikes, before, frame['t']) or between(kills, before, frame['t'])
        if moved or busy or hurt:
            close(start, i - 1)
            start, best = i, lives
    if start is not None:
        close(start, len(frames) - 1)
    runs: list[list[tuple[int, int]]] = []
    for piece in pieces:
        if runs:
            last = runs[-1][-1]
            gap = frames[piece[0]]['t'] - frames[last[1]]['t']
            spot = math.dist(frames[piece[0]]['p'][3:5], frames[last[0]]['p'][3:5])
            if gap <= MERGE_GAP and spot <= limits.still * 2:
                runs[-1].append(piece)
                continue
        runs.append([piece])
    return [idle_case(take, run, lines, casts, limits) for run in runs if still_seconds(take, run) >= limits.idle]


def still_seconds(take: Take, run: list[tuple[int, int]]) -> float:
    return sum(take.frames[b]['t'] - take.frames[a]['t'] for a, b in run)


def idle_case(take: Take, run: list[tuple[int, int]], lines: list, casts: list[float], limits: Limits) -> Case:
    frames = take.frames
    first, last = run[0][0], run[-1][1]
    a, b = frames[first], frames[last]
    inside = frames[first : last + 1]
    here = a['p'][3:5]
    near = [math.dist(here, m[3:5]) for f in inside for m in hostiles(f)]
    within = max(sum(math.dist(here, m[3:5]) <= limits.near for m in hostiles(f)) for f in inside)
    lost = a['p'][7] - min((f['p'][7] for f in inside if f['p'][7] > 0), default=a['p'][7])  # 0: a torn read
    nearest = f'{min(near):.0f}' if near else '-'
    goal = goal_in(take, a['t'], b['t'])
    cast = between(casts, a['t'], b['t'])
    still = still_seconds(take, run)
    pieces = f' in {len(run)} pieces ({still:.0f}s still)' if len(run) > 1 else ''
    facts = (
        f'still at ({here[0]:.0f}, {here[1]:.0f}){pieces}, no strike, {cast} other casts, {within} hostiles within '
        f'{limits.near:.0f} (nearest {nearest}), life -{max(lost, 0)}, goal {goal}'
    )
    data = {'x': here[0], 'y': here[1], 'within': within, 'nearest': min(near) if near else None, 'casts': cast,
            'life_lost': max(lost, 0), 'goal': goal, 'at': round(a['t'] - frames[0]['t'], 1), 'pieces': len(run),
            'still': round(still, 1)}  # fmt: skip
    cause = kinds(lines, a['t'] - LEAD, b['t']) or [f'none said; the last before: {said_before(lines, a["t"])}']
    return Case('IDLE', take.name, take.local(a['t']), take.local(b['t']), facts, cause, data)


def monster_names(path: Path = MONSTATS) -> dict[int, tuple[str, str, bool]]:
    """monstats.txt by *hcIdx: (Id, NameStr, boss)."""
    found: dict[int, tuple[str, str, bool]] = {}
    try:
        text = path.read_text(errors='replace').splitlines()
    except OSError:
        return found
    head = text[0].split('\t')
    at = {name: head.index(name) for name in ('Id', '*hcIdx', 'NameStr', 'boss') if name in head}
    for row in text[1:]:
        cells = row.split('\t')
        try:
            index = int(cells[at['*hcIdx']])
        except KeyError, IndexError, ValueError:
            continue
        boss = 'boss' in at and len(cells) > at['boss'] and cells[at['boss']] == '1'
        found[index] = (cells[at['Id']], cells[at['NameStr']] if 'NameStr' in at else '', boss)
    return found


_MONSTERS: dict[int, tuple[str, str, bool]] = {}


def monster(index: int) -> str:
    if not _MONSTERS:
        _MONSTERS.update(monster_names())
    row = _MONSTERS.get(index)
    if row is None:
        return f'class {index}'
    return f'{row[1] or row[0]} ({row[0]}, {index}{", boss" if row[2] else ""})'


def lives_of(take: Take, unit: int) -> list[tuple[float, int]]:
    return [(f['t'], m[5]) for f in take.frames for m in f.get('m', ()) if m[0] == unit]


def slowest(lives: list[tuple[float, int]], start: float, end: float) -> str:
    """The SLOW_WINDOW s of the fight in which the target lost the least life."""
    inside = [(t, life) for t, life in lives if start <= t <= end]
    if not inside or end - start < SLOW_WINDOW:
        return '-'
    best: tuple[int, float, int, int] | None = None
    j = 0
    for t, life in inside:
        while j < len(inside) - 1 and inside[j][0] < t + SLOW_WINDOW:
            j += 1
        if inside[j][0] - t < SLOW_WINDOW * 0.9:
            break
        drop = life - inside[j][1]
        if best is None or drop < best[0]:
            best = (drop, t - start, life, inside[j][1])
    if best is None:
        return '-'
    return f'+{best[1]:.0f}s {best[2]}->{best[3]}'


def fights(take: Take, skip: list[tuple[float, float, str]], limits: Limits) -> list[Case]:
    """The targets struck at for more than limits.fight s (or an elite target's pack near it that long)."""
    lines = take.lines()
    struck: dict[int, list[tuple[float, int, str]]] = {}
    elites: dict[int, tuple[float, int, str]] = {}
    for t, text in lines:
        if (m := STRIKE.search(text)) is not None:
            struck.setdefault(int(m.group(3)), []).append((t, int(m.group(2)), m.group(1)))
        elif (m := ELITE_TARGET.search(text)) is not None:
            elites.setdefault(int(m.group(2)), (t, int(m.group(1)), m.group(3)))
    ends: dict[int, tuple[float, str]] = {}
    for e in take.events:
        if e.get('event') in ('kill', 'gone') and e.get('unit') not in ends:
            ends[e['unit']] = (e['t'], 'dead' if e['event'] == 'kill' else 'gone')
    casts = take.times('cast')
    landings = [t for t, _, _ in jumps_of(take)]
    found: list[Case] = []
    first = take.frames[0]['t'] if take.frames else 0.0

    def report(unit: int, cls: str, what: str, start: float, end: float, how: str, strikes: int) -> None:
        if end - start <= limits.fight or any(a <= start <= b for a, b, _ in skip):
            return
        lives = lives_of(take, unit)
        inside = [life for t, life in lives if start <= t <= end]
        life = f'{inside[0]}->{inside[-1]}' if inside else '?'
        span = end - start
        ours = [f['p'][7] for f in take.frames if start <= f['t'] <= end and f['p'][7] > 0]  # 0: a torn read
        lost = (ours[0] - min(ours)) if ours else 0
        tier = f'(agenda tier {elites[unit][2]}) ' if unit in elites else ''
        facts = (
            f'{what} {tier}{monster(int(cls))} unit {unit}, {how}; life {life}/128, slowest {SLOW_WINDOW:.0f}s '
            f'{slowest(lives, start, end)}; {strikes} strikes, {between(casts, start, end) / span:.2f} casts/s, '
            f'{between(landings, start, end)} jumps, our life -{max(lost, 0)}'
        )
        data = {'unit': unit, 'class': int(cls), 'what': what, 'end': how, 'life': life, 'strikes': strikes,
                'at': round(start - first, 1)}  # fmt: skip
        found.append(Case('LONG_FIGHT', take.name, take.local(start), take.local(end), facts,
                          kinds(lines, start, end), data))  # fmt: skip

    for unit, hits in struck.items():
        segment = [hits[0]]
        for hit in [*hits[1:], None]:
            if hit is not None and hit[0] - segment[-1][0] <= FIGHT_GAP:
                segment.append(hit)
                continue
            start, last = segment[0][0], segment[-1][0]
            end, how = last, 'let go'
            if unit in ends and last - 1.0 <= ends[unit][0] <= last + FIGHT_GAP:
                end, how = ends[unit]
            report(unit, str(segment[0][1]), segment[0][2], start, end, how, len(segment))
            if hit is not None:
                segment = [hit]
    reported = {case.data['unit'] for case in found}
    for unit, (named, cls, _) in elites.items():
        if unit in reported:
            continue
        place = [(f['t'], m[3:5], f['p'][3:5]) for f in take.frames if f['t'] >= named for m in f['m'] if m[0] == unit]
        close = [t for t, there, here in place if math.dist(there, here) <= limits.near]
        strikes = [t for hits in struck.values() for t, _, _ in hits if close and t >= close[0]]
        if not close or not strikes:
            continue
        start = min(strikes)
        end, how = ends.get(unit, (max(strikes), 'let go'))
        report(unit, str(cls), 'the pack of the elite', start, end, how, len([t for t in strikes if t <= end]))
    return found


def jumps_of(take: Take) -> list[tuple[float, float, float]]:
    """The landings: (t, x, y) where the character's place moved over JUMP_STEP units from the frame before."""
    found = []
    for a, b in zip(take.frames, take.frames[1:], strict=False):
        if outside(a) or outside(b) or a['p'][2] != b['p'][2]:
            continue
        if math.dist(a['p'][3:5], b['p'][3:5]) > JUMP_STEP:
            found.append((b['t'], b['p'][3], b['p'][4]))
    return found


def clusters(take: Take, skip: list[tuple[float, float, str]], limits: Limits) -> list[Case]:
    """limits.jumps landings or more in limits.jump_window s within limits.jump_radius of their centroid, <= 1 kill."""
    landings = [j for j in jumps_of(take) if not any(a <= j[0] <= b for a, b, why in skip if why == 'loop off')]
    kills = take.times('kill')
    marked: list[list[int]] = []
    for i, (t, _, _) in enumerate(landings):
        j = bisect.bisect_right([x[0] for x in landings], t + limits.jump_window) - 1
        if j - i + 1 < limits.jumps:
            continue
        group = landings[i : j + 1]
        cx, cy = sum(x for _, x, _ in group) / len(group), sum(y for _, _, y in group) / len(group)
        if max(math.dist((cx, cy), (x, y)) for _, x, y in group) > limits.jump_radius:
            continue
        if between(kills, t - 1e-9, landings[j][0]) > MAX_KILLS:
            continue
        if marked and i <= marked[-1][1]:
            marked[-1][1] = max(marked[-1][1], j)
        else:
            marked.append([i, j])
    lines = take.lines()
    found = []
    first = take.frames[0]['t'] if take.frames else 0.0
    for i, j in marked:
        group = landings[i : j + 1]
        start, end = group[0][0], group[-1][0]
        if end - start < limits.jump_least:
            continue
        cx, cy = sum(x for _, x, _ in group) / len(group), sum(y for _, _, y in group) / len(group)
        radius = max(math.dist((cx, cy), (x, y)) for _, x, y in group)
        casts = sum(1 for t, text in lines if start - 1.0 <= t <= end and JUMP_CAST.search(text))
        killed = between(kills, start - 1e-9, end)
        within = max(sum(math.dist((cx, cy), m[3:5]) <= limits.near for m in hostiles(f))
                     for f in take.frames if start <= f['t'] <= end)  # fmt: skip
        facts = (
            f'{len(group)} jumps round ({cx:.0f}, {cy:.0f}) within {radius:.0f}, {casts} jump casts said, '
            f'{killed} kills, {within} hostiles within {limits.near:.0f}, goal {goal_in(take, start, end)}'
        )
        data = {'jumps': len(group), 'x': cx, 'y': cy, 'radius': radius, 'kills': killed,
                'at': round(start - first, 1), 'cause': kinds(lines, start, end)}  # fmt: skip
        found.append(Case('JUMP_CLUSTER', take.name, take.local(start), take.local(end), facts,
                          reasons(lines, start - 1.0, end), data))  # fmt: skip
    return found


def strikes_of(take: Take) -> list[tuple[float, int, str]]:
    """Each strike the macro made, in time order: (t, the target's unit, 'elite' / 'monster' / '?'): the decisions'
    `Strike` with a target and the STRIKE lines (which also name the target's rank)."""
    found = [(e['t'], int(e['target']), '?') for e in take.events
             if e.get('event') == 'decision' and e.get('chosen') == 'Strike' and e.get('target')]  # fmt: skip
    found += [(t, int(m.group(3)), m.group(1)) for t, text in take.lines() if (m := STRIKE.search(text)) is not None]
    return sorted(found)


def blade_casts(take: Take) -> list[float]:
    """When each Echoing Strike cast's blades were first seen (BLADE births, BLADE_BIRTH s apart at most are one)."""
    seen: set[int] = set()
    births: list[float] = []
    for frame in take.frames:
        for x in frame.get('x') or ():
            if x[1] == BLADE and x[0] not in seen:
                seen.add(x[0])
                if not births or frame['t'] - births[-1] > BLADE_BIRTH:
                    births.append(frame['t'])
    return births


def cast_times(take: Take) -> tuple[list[float], str]:
    """The strike casts and what they were counted from: the blades, else the `cast` events (a take with no blades)."""
    blades = blade_casts(take)
    if blades:
        return blades, 'blade casts'
    return take.times('cast'), 'casts'


def owned(casts: list[float], strikes: list[tuple[float, int, str]]) -> dict[int, list[float]]:
    """Each cast given to the target struck last before it (within CAST_AFTER + STRIKE_GAP s)."""
    times = [t for t, _, _ in strikes]
    found: dict[int, list[float]] = {}
    for c in casts:
        i = bisect.bisect_right(times, c) - 1
        if i >= 0 and c - times[i] <= STRIKE_GAP + CAST_AFTER:
            found.setdefault(strikes[i][1], []).append(c)
    return found


def stretches(times: list[float], gap: float = STRIKE_GAP) -> list[tuple[float, float]]:
    """The sorted `times` cut where two are more than `gap` apart: (first, last) of each run."""
    found: list[tuple[float, float]] = []
    for t in times:
        if found and t - found[-1][1] <= gap:
            found[-1] = (found[-1][0], t)
        else:
            found.append((t, t))
    return found


def herald_tiers(directory: Path) -> dict[int, int]:
    """Each unit's Herald tier (itemstatcost 367 `heraldtier`) from units.jsonl, where it has one."""
    return {
        int(row['unit']): int(row['stats']['367'])
        for row in rows(directory, 'units.jsonl')
        if 'unit' in row and (row.get('stats') or {}).get('367')
    }


@dataclass
class Stretch:
    """Strikes at one target (`unit`; 0: strikes at anything), STRIKE_GAP s apart at most, with the casts given to it
    and what became of it up to DAMAGE_LAG s after the last."""

    unit: int
    start: float
    end: float  # the last strike or the last of its casts, whichever is later
    casts: list[float]
    hits: int = 0  # `hit` events on the target (on any hostile for unit 0)
    lost: int = 0  # its life of 128 at the start less its least
    killed: bool = False
    any_hits: int = 0  # `hit` events on any hostile

    @property
    def damaged(self) -> bool:
        return bool(self.hits or self.killed or self.lost >= HURT)


class StrikeRead:
    """A take's strikes, their casts and the life of what they struck at, indexed once (NO_DAMAGE, nodamage.py)."""

    def __init__(self, take: Take) -> None:
        self.take = take
        self.strikes = strikes_of(take)
        self.casts, self.counted = cast_times(take)
        self.by_target = owned(self.casts, self.strikes)
        self.hits: dict[int, list[float]] = {}
        for e in take.events:
            life = e.get('life') or [0, 0]
            if e.get('event') == 'hit' and life[1] < life[0]:
                self.hits.setdefault(int(e['unit']), []).append(e['t'])
        self.all_hits = sorted(t for ts in self.hits.values() for t in ts)
        self.kills = {int(e['unit']): e['t'] for e in take.events if e.get('event') == 'kill' and 'unit' in e}
        self.what = {unit: rank for _, unit, rank in self.strikes if rank != '?'}
        self.tiers = {int(m.group(2)): int(m.group(3)) for _, text in take.lines() if (m := ELITE_TARGET.search(text))}
        self.frame_times = [f['t'] for f in take.frames]

    def track(self, unit: int, a: float, b: float) -> list[tuple[float, list, list]]:
        """(t, the unit's row, the character's row) in the frames of [a, b] the cases count."""
        i, j = bisect.bisect_left(self.frame_times, a), bisect.bisect_right(self.frame_times, b)
        frames = self.take.frames[i:j]
        return [(f['t'], m, f['p']) for f in frames if not outside(f) for m in f.get('m', ()) if m[0] == unit]

    def judged(self, unit: int, start: float, end: float, casts: list[float]) -> Stretch:
        upto = end + DAMAGE_LAG
        found = Stretch(unit, start, end, casts, any_hits=between(self.all_hits, start, upto))
        if unit:
            found.hits = between(self.hits.get(unit, []), start, upto)
            found.killed = start <= self.kills.get(unit, -math.inf) <= upto
            lives = [m[5] for _, m, _ in self.track(unit, start - 0.2, upto)]
            found.lost = lives[0] - min(lives) if lives else 0
        else:
            found.hits = found.any_hits
        return found

    def stretches(self) -> list[Stretch]:
        """Every target's stretches, then the stretches of strikes at anything, in time order each."""
        found = []
        for unit in sorted({u for _, u, _ in self.strikes}):
            own = self.by_target.get(unit, [])
            for a, b in stretches(sorted({t for t, u, _ in self.strikes if u == unit})):
                mine = [c for c in own if a <= c <= b + CAST_AFTER]
                found.append(self.judged(unit, a, max([b, *mine]), mine))
        for a, b in stretches([t for t, _, _ in self.strikes]):
            mine = [c for c in self.casts if a <= c <= b + CAST_AFTER]
            found.append(self.judged(0, a, max([b, *mine]), mine))
        return found

    def case(self, stretch: Stretch, struck: int | None = None) -> Case:
        """The NO_DAMAGE case of `stretch`; `struck`: the target a stretch of strikes at anything names."""
        take, unit = self.take, stretch.unit or (struck or 0)
        a, b = stretch.start, stretch.end
        rows_in = self.track(unit, a - 0.2, b + DAMAGE_LAG) if unit else []
        lives = [m[5] for _, m, _ in rows_in]
        away = [math.dist(p[3:5], m[3:5]) for _, m, p in rows_in]
        life = f'{lives[0]}->{lives[-1]}/128' if lives else 'not in the read'
        far = f'{away[0]:.1f} away ({min(away):.0f}-{max(away):.0f})' if away else 'distance unknown'
        cls = int(rows_in[0][1][1]) if rows_in else None
        name = monster(cls) if cls is not None else 'class ?'
        tier = self.tiers.get(unit)
        if tier is None and unit:
            tier = herald_tiers(take.directory).get(unit)
        rank = self.what.get(unit, 'unit')
        target = f'the {rank} {name} unit {unit}{f", tier {tier}" if tier else ""}' if unit else 'every target'
        dry = not stretch.any_hits
        facts = (
            f'struck at {target}, {far}, {len(stretch.casts)} {self.counted}, life {life}'
            f'{", no hit on anything" if dry else ""}'
        )
        first = take.frames[0]['t']
        data = {'unit': unit, 'class': cls, 'what': rank, 'tier': tier, 'casts': len(stretch.casts),
                'counted': self.counted, 'life': [lives[0], lives[-1]] if lives else None,
                'away': [round(away[0], 1), round(min(away), 1), round(max(away), 1)] if away else None, 'dry': dry,
                'at': round(a - first, 1), 'from': round(a, 3), 'to': round(b, 3)}  # fmt: skip
        return Case('NO_DAMAGE', take.name, take.local(a), take.local(b), facts, kinds(take.lines(), a, b), data)


def no_damage(take: Take, skip: list[tuple[float, float, str]], limits: Limits) -> list[Case]:
    """The stretches of strikes at one target whose life did not fall, and of strikes at anything with no hit at all
    (when no target's case covers them); not while the loop is off or stands for a restart."""
    if not take.frames:
        return []
    read = StrikeRead(take)
    if not read.strikes:
        return []
    excluded = [(a, b) for a, b, why in skip if why in ('loop off', 'restart')]
    found: list[Case] = []
    reported: list[tuple[float, float]] = []
    for stretch in read.stretches():
        a, end = stretch.start, stretch.end
        if len(stretch.casts) < limits.dry_casts or end - a < limits.dry_seconds or stretch.damaged:
            continue
        if any(x <= a <= y for x, y in excluded):
            continue
        if stretch.unit:
            reported.append((a, end))
            found.append(read.case(stretch))
        elif not any(x <= a <= y or a <= x <= end for x, y in reported):
            struck = Counter(u for t, u, _ in read.strikes if a <= t <= end).most_common(1)
            found.append(read.case(stretch, struck[0][0] if struck else None))
    return found


def detect(
    directory: Path, on: bool | None = None, limits: Limits | None = None, runs: Path = logwords.RUNS
) -> list[Case]:
    """The take's cases in time order; `on`: the loop at the take's open (None: read from its session's probe.log, and
    taken as on when unknown)."""
    limits = limits or Limits()
    take = Take.load(directory)
    if not take.frames:
        return []
    serve = serve_of(directory.name, runs)
    if serve is not None:
        start, end = take.frames[0]['t'] + take.offset - LEAD, take.frames[-1]['t'] + take.offset + 1.0
        said = [(epoch - take.offset, text) for epoch, text in serve.between(start, end)]
        take.said = said or None
        if on is None:
            on = serve.states.get(directory.name)
    skip = windows(take, on)
    found = idles(take, skip, limits) + fights(take, skip, limits) + clusters(take, skip, limits)
    found += no_damage(take, skip, limits)
    return sorted(found, key=lambda case: case.start)


# --- The command ----------------------------------------------------------------------------------------------------


def takes_since(since: datetime, until: datetime | None, combat: Path = COMBAT) -> list[Path]:
    """The takes opened in the local window, by their UTC names."""
    low = since.astimezone(UTC).strftime('%Y%m%dT%H%M%S')
    high = until.astimezone(UTC).strftime('%Y%m%dT%H%M%S') if until is not None else '9'
    return [
        d for d in sorted(combat.glob('20*')) if low <= d.name.split('Z')[0] < high and (d / 'manifest.json').exists()
    ]


def summary(cases: list[Case], takes: int) -> str:
    counts = Counter(case.kind for case in cases)
    seconds: dict[str, float] = {}
    for case in cases:
        seconds[case.kind] = seconds.get(case.kind, 0.0) + case.seconds
    head = ', '.join(
        f'{kind} {counts[kind]} ({seconds.get(kind, 0.0):.0f}s)'
        for kind in ('IDLE', 'LONG_FIGHT', 'JUMP_CLUSTER', 'NO_DAMAGE')
    )
    longest = sorted(cases, key=lambda case: -case.seconds)[:10]
    return '\n'.join(
        [f'{len(cases)} cases in {takes} takes: {head}', 'the 10 longest:', *(f'  {case.line()}' for case in longest)]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('takes', nargs='*', help='take directories or names (runs/combat/<name>)')
    parser.add_argument('--since', type=logwords.local)
    parser.add_argument('--until', type=logwords.local)
    parser.add_argument('--idle', type=float, default=Limits.idle)
    parser.add_argument('--still', type=float, default=Limits.still)
    parser.add_argument('--near', type=float, default=Limits.near)
    parser.add_argument('--fight', type=float, default=Limits.fight)
    parser.add_argument('--jumps', type=int, default=Limits.jumps)
    parser.add_argument('--jump-window', type=float, default=Limits.jump_window)
    parser.add_argument('--jump-radius', type=float, default=Limits.jump_radius)
    parser.add_argument('--jump-least', type=float, default=Limits.jump_least)
    parser.add_argument('--dry-casts', type=int, default=Limits.dry_casts)
    parser.add_argument('--dry-seconds', type=float, default=Limits.dry_seconds)
    parser.add_argument('--kind', action='append', help='only these kinds (IDLE, LONG_FIGHT, JUMP_CLUSTER, NO_DAMAGE)')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--summary', action='store_true', help='the counts by kind and the 10 longest after the lines')
    args = parser.parse_args()
    limits = Limits(
        args.idle,
        args.still,
        args.near,
        args.fight,
        args.jumps,
        args.jump_window,
        args.jump_radius,
        args.jump_least,
        args.dry_casts,
        args.dry_seconds,
    )
    directories = [Path(t) if Path(t).is_dir() else COMBAT / t for t in args.takes]
    if args.since is not None:
        directories += takes_since(args.since, args.until)
    if not directories:
        parser.error('a take or --since')
    cases: list[Case] = []
    for directory in directories:
        try:
            found = [c for c in detect(directory, limits=limits) if not args.kind or c.kind in args.kind]
        except (OSError, ValueError, KeyError, IndexError) as error:
            print(f'{directory.name}: unread ({error})', file=sys.stderr)
            continue
        cases += found
        if not args.json:
            for case in found:
                print(case.line(), flush=True)
    if args.json:
        print(json.dumps([case.as_json() for case in cases], indent=1))
    elif args.summary:
        print(summary(cases, len(directories)))


if __name__ == '__main__':
    main()
