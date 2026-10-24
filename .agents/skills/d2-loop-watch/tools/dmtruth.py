"""The ground truth of Teleport -> Death Mark from a combat take: the GAME's state, not the macro's words.

The player, 2026-10-24 ~19:21 and 19:24: "DM comes after tp with a way longer delay that you're measured ... we need to
make sure that you actually also can measure it: the real delay". The macro's own lines ("teleport aimed at ... landed
at", "Death Mark on d, player mode N") say when it decided and sent; this tool reads what the game did
(rca/2026-10-24/dm-truth-findings.md).

Read from a take (`runs/combat/<UTC>-<area>/`, the plain file while it exists, else the gzip; anomalies.py `rows`):

- frames (25/s): the character's mode and position (`p`), the hostiles (`m`), the pointer (`in`), the hovered unit
  (`h`, written at a change) and the game's own millisecond clock (`k`, u32 at byte 8: the frame clock's check);
- records.jsonl: the character's skill in use (the u16 its skills.txt row begins with: 54 Teleport, 375 Death Mark,
  388 Echoing Strike), written at each change of its mode, and each monster's state words, written in the frame they
  change: Death Mark is state 212 (states.txt `death_mark`, word 6 bit 20), so the frame the mark shows on a unit;
- events: the service's `sent` inputs (key down/up, buttons, pointer moves) at their send time, and its `log` lines.

Per landing (a jump of the character's position > JUMP_STEP units between two frames, in a Teleport's or a Blade
Warp's cast):

    move start (the first hop's key of the move) -> hop key -> cast start -> JUMP (position) -> cast end
    -> the mark key down -> the Death Mark cast start (mode into a cast, skill 375) -> its end -> state 212 on a unit

with the aimed unit (the macro's "Death Mark on the <kind> <class> (<unit>)" line, the game's hovered unit at the key,
the hostile whose body is drawn nearest the pointer), a wrong target (the state on another unit), the keys that gave no
cast (LOST), the retries, the casts made between the jump and the mark, and, when no mark key followed, the macro's
mark/safety lines that say why. A move is the hops since the last Death Mark cast, each within --move-gap s of the one
before. Also every mark key of the take (cast? state?) and the clock checks: the frame clock against the game's own
clock, the take's log events against probe.log's stamps, the key sent against the key seen down.

Stdlib only (run with a plain python3, like anomalies.py beside it).

    python3 .agents/skills/d2-loop-watch/tools/dmtruth.py <take>... | --since 'YYYY-MM-DD HH:MM' [--until ...]
        [--herald 5] [--marked] [--move-gap 2.0] [--json] [--summary]
"""

import argparse
import bisect
import json
import re
import struct
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import anomalies  # pyrefly: ignore[missing-import] - beside this tool
import logwords  # pyrefly: ignore[missing-import] - beside this tool


COMBAT = anomalies.COMBAT
TELEPORT, BLADE_WARP, DEATH_MARK = 54, 390, 375  # skills.txt *Id (pricing/raw/game-excel/skills.txt)
JUMPS = frozenset((TELEPORT, BLADE_WARP))
# The path record's target unit (inventory_tracking/takes/hurts.py TARGET_UNIT): whom a monster or a pet goes for.
TARGET_UNIT = 0x7C
MARK_STATE = 212  # states.txt `death_mark` (pricing/raw/game-excel/states.txt, *ID 212)
# The character's cast modes (inventory_tracking/game/layout.py ACTING).
ACTING = frozenset((7, 8, 10, 11, 12, 13, 14, 15, 16, 18))
DEAD = (0, 12)
NO_OWNER = 4294967295
JUMP_STEP = 5.0  # units between two frames: a jump, not a walk (anomalies.py JUMP_STEP)
WINDOW = 3.0  # seconds after a jump the mark is looked for at most (or up to the next hop)
LOST = 0.4  # seconds after the cast under way at the key ends (or after the key) with no mark cast: the key is lost
# The Death Mark cast's start to its state on the unit: 280 ms (p50 and p90 of 14 casts with a mode change, take
# 20261024T161813Z-108): the game's own, fixed; a cast chained in another (no mode change) is dated back by it.
CAST_TO_STATE = 0.28
SHOWS = 1.5  # seconds after the mark's cast start its state may show
MOVE_GAP = 2.0  # seconds between a jump and the next hop's cast that keep them one move
CLOCK_BYTE = 8  # the u32 game millisecond clock in the tick head (`k`): within ±10 ms of the frame clock
# The record's mode (u32 at +0x0C), as the frames have it; only a fallback.
RECORD_MODE = 0x0C
# Where a unit's body is drawn (inventory_tracking/game/view.py Viewport.body: FEET, UNIT_PIXELS, BODY_LIFT).
FEET, UNIT_PIXELS, BODY_LIFT = (0.5, 0.494), (16 / 600, 8 / 600), 0.035
# The macro's lines read (runner.py `_say`'s prefix from logwords.SAID; the words could move into logwords.py)
SAID = re.escape(logwords.SAID)
MARK_ON = re.compile(SAID + r'Death Mark on the (\w+) (\d+) \((\d+)\)')
MARK_KEY = re.compile(SAID + r'Death Mark on (\S+), player mode \d+')
JUMP_KEY = re.compile(SAID + r'(?:Teleport|Blade Warp) on (\S+), player mode \d+')
LANDED = logwords.SAID + 'teleport aimed at'
FIRST = 'first at the landing'  # hunt.py, HERALD_MARK_FIRST's line
WHY = re.compile(
    SAID + r'(mark: |safety: |buff: Death Mark|.*keeping range|.*Herald|Retreating|Escorting|pursuit: retreat)'
)
HERALD = re.compile(r'tier (\d) Herald')


# --- Reading ---------------------------------------------------------------------------------------------------------


def states_on(words: bytes, state: int) -> bool:
    """`state` set in a unit's state words read raw from the first (32 states to a little-endian word)."""
    word, bit = divmod(state, 32)
    if len(words) < (word + 1) * 4:
        return False
    return bool(int.from_bytes(words[word * 4 : word * 4 + 4], 'little') >> bit & 1)


def skill_of(raw: str) -> int | None:
    """The skill id of a record row's skill-in-use bytes (game/decode.py `skill_in_use`); None: none."""
    found = bytes.fromhex(raw) if raw else b''
    return int.from_bytes(found[:2], 'little') if len(found) >= 2 else None


@dataclass
class Cast:
    start: float
    end: float | None  # None: still in a cast when the take ends
    skill: int | None  # None: unread (no record row in its first frame)
    chained: bool = False  # begun inside a cast with no mode change (seen only by a record refresh)


@dataclass
class Truth:
    """One take, read."""

    name: str
    offset: float  # wall - the take's clock
    player: int
    frames: list[dict]
    times: list[float]
    casts: list[Cast]
    marks_on: list[tuple[float, int]]  # (t, unit): state 212 set where the frame before had it clear
    marks: dict[int, list[tuple[float, bool]]]  # unit -> its record rows' (t, state 212 on), in time order
    sent: list[dict]
    lines: list[tuple[float, str]]
    hovered: list[tuple[float, Any]]  # (t, [type, unit] | None), as written at changes
    units: dict[int, tuple[int, int]] = field(default_factory=dict)  # unit -> (class, flags)
    targets: dict[int, list[tuple[float, int | None]]] = field(default_factory=dict)  # unit -> (t, its path's target)
    companions: frozenset[int] = frozenset()  # the character's pets and mercenary
    mark_key: str = 'd'
    jump_keys: frozenset[str] = frozenset({'t'})

    def local(self, t: float) -> str:
        return datetime.fromtimestamp(t + self.offset).strftime('%H:%M:%S.%f')[:-3]

    def frame_at(self, t: float) -> dict | None:
        """The first frame at or after t."""
        i = bisect.bisect_left(self.times, t - 1e-6)
        return self.frames[i] if i < len(self.frames) else None

    def marked_at(self, unit: int, t: float) -> bool | None:
        """Whether `unit` had state 212 at t, by its last record row before t; None: no row yet."""
        rows = self.marks.get(unit, [])
        i = bisect.bisect_right([r[0] for r in rows], t) - 1
        return rows[i][1] if i >= 0 else None

    def hover_at(self, t: float) -> Any:
        i = bisect.bisect_right([h[0] for h in self.hovered], t + 1e-6) - 1
        return self.hovered[i][1] if i >= 0 else None


def load(directory: Path) -> Truth:
    manifest = json.loads((directory / 'manifest.json').read_text())
    frames = [f for f in anomalies.rows(directory, 'frames.jsonl') if f.get('p') and 't' in f]
    frames.sort(key=lambda f: f['t'])
    events = sorted((e for e in anomalies.rows(directory, 'events.jsonl') if 't' in e), key=lambda e: e['t'])
    records = anomalies.rows(directory, 'records.jsonl')
    clock = manifest.get('clock') or {}
    offset = clock['wall'] - clock['monotonic'] if clock else 0.0
    player = frames[0]['p'][0] if frames else 0
    by_frame: dict[int, int | None] = {}
    refresh: list[tuple[float, int | None]] = []  # the character's rows: (t, skill)
    marks_on: list[tuple[float, int]] = []
    marked: dict[int, bool] = {}
    marks: dict[int, list[tuple[float, bool]]] = {}
    for row in sorted(records, key=lambda r: r.get('t', 0.0)):
        for unit, _record, words, skill in row.get('u', []):
            if unit == player:
                by_frame[row['n']] = skill_of(skill)
                refresh.append((row['t'], skill_of(skill)))
                continue
            on = states_on(bytes.fromhex(words), MARK_STATE) if words else False
            if on and marked.get(unit) is False:
                marks_on.append((row['t'], unit))
            marked[unit] = on
            marks.setdefault(unit, []).append((row['t'], on))
    hovered = [(f['t'], f['h']) for f in frames if 'h' in f]
    targets: dict[int, list[tuple[float, int | None]]] = {}
    for row in sorted(anomalies.rows(directory, 'paths.jsonl'), key=lambda r: r.get('t', 0.0)):
        for unit, path in row.get('m', []):
            raw = bytes.fromhex(path[: 2 * (TARGET_UNIT + 4)])
            target = struct.unpack_from('<I', raw, TARGET_UNIT)[0] if len(raw) >= TARGET_UNIT + 4 else None
            if not targets.get(unit) or targets[unit][-1][1] != target:
                targets.setdefault(unit, []).append((row['t'], target))
    companions = frozenset(m[0] for f in frames for m in f.get('m', []) if m[8] == player or m[9])
    units: dict[int, tuple[int, int]] = {}
    for f in frames:
        for m in f.get('m', []):
            units.setdefault(m[0], (m[1], m[7]))
    lines = [(e['t'], e.get('text', '')) for e in events if e.get('event') == 'log']
    truth = Truth(
        directory.name,
        offset,
        player,
        frames,
        [f['t'] for f in frames],
        casts_of(frames, by_frame, refresh),
        marks_on,
        marks,
        [e for e in events if e.get('event') == 'sent'],
        lines,
        hovered,
        units,
        targets,
        companions,
    )
    keys = [m.group(1) for _, text in lines if (m := MARK_KEY.search(text))]
    if keys:
        truth.mark_key = max(set(keys), key=keys.count)
    jumps = {m.group(1) for _, text in lines if (m := JUMP_KEY.search(text))}
    if jumps:
        truth.jump_keys = frozenset(jumps)
    return truth


def casts_of(
    frames: list[dict], by_frame: dict[int, int | None], refresh: list[tuple[float, int | None]]
) -> list[Cast]:
    """The character's casts: a mode into ACTING to its leaving it, the skill from the record row of the cast's first
    frame (the recorder writes one at a change of mode); a record row inside a cast naming another skill is a chained
    cast (queued under the one before, no mode change between; its start is seen only as late as that row)."""
    casts: list[Cast] = []
    acting = False
    for f in frames:
        mode = f['p'][1]
        now = mode in ACTING
        if now and not acting:
            casts.append(Cast(f['t'], None, by_frame.get(f['n'])))
        elif acting and not now and casts:
            casts[-1].end = f['t']
        acting = now
    found: list[Cast] = []
    times = [t for t, _ in refresh]
    for cast in casts:
        found.append(cast)
        a = bisect.bisect_right(times, cast.start + 1e-6)
        b = bisect.bisect_left(times, cast.end) if cast.end is not None else len(times)
        for t, skill in refresh[a:b]:
            if skill is not None and skill != found[-1].skill:
                found[-1] = Cast(found[-1].start, t, found[-1].skill, found[-1].chained)
                found.append(Cast(t, cast.end, skill, chained=True))
    return found


# --- The pointer -----------------------------------------------------------------------------------------------------


def body(origin: tuple[float, float], x: float, y: float, aspect: float) -> tuple[float, float]:
    """Where a unit at world (x, y) is drawn, as window fractions (view.py `Viewport.body`)."""
    dx, dy = x - origin[0], y - origin[1]
    return FEET[0] + (dx - dy) * UNIT_PIXELS[0] / aspect, FEET[1] + (dx + dy) * UNIT_PIXELS[1] - BODY_LIFT


def under_pointer(frame: dict, most: int = 3) -> list[tuple[int, float]]:
    """The hostiles whose bodies are drawn nearest the frame's pointer: (unit, distance in pixels of a 600-high
    view), nearest first."""
    pointer = frame.get('in') or []
    rect = frame.get('rect')
    if len(pointer) < 5 or pointer[3] is None or not rect or not rect[3]:
        return []
    aspect = rect[2] / rect[3]
    origin = (frame['p'][3], frame['p'][4])
    found = []
    for m in frame.get('m', []):
        if m[8] != NO_OWNER or m[9] or m[2] in DEAD:
            continue
        across, down = body(origin, m[3], m[4], aspect)
        found.append((m[0], round(600 * ((across - pointer[3]) ** 2 * aspect**2 + (down - pointer[4]) ** 2) ** 0.5, 1)))
    return sorted(found, key=lambda u: u[1])[:most]


# --- The rows --------------------------------------------------------------------------------------------------------


@dataclass
class Key:
    """One mark key down sent, and what the game made of it."""

    take: str
    at: str  # local time
    t: float
    held: float | None  # s the key was held (its up sent)
    busy: int | None  # the skill of the cast under way at the key; None: none
    left: float | None  # s of that cast left at the key (to its mode change; a chain of casts counts whole)
    aimed: int | None  # the macro's line's unit
    hovered: int | None  # the game's hovered monster at the key
    nearest: list = field(default_factory=list)  # (unit, px) of the hostiles drawn nearest the pointer
    cast: float | None = None  # the Death Mark cast's start (s after the key)
    chained: bool = False
    state: float | None = None  # the state on a unit (s after the key)
    unit: int | None = None  # the unit it showed on
    # took; wrong target (the state on another unit than the aimed); already on (the aimed unit had it);
    # no state (a cast, no state anywhere); unseen cast (no 375 cast seen, the state showed: a chain's cast);
    # lost (no cast, no state)
    outcome: str = ''


@dataclass
class Landing:
    take: str
    at: str  # local time of the jump
    t: float
    skill: int | None  # the hop's cast skill
    hop: int  # 1-based in its move
    hops: int  # in its move
    move_start: float | None  # s before the jump: the move's first hop key (else its first cast)
    first_jump: float  # s before the jump: the move's first jump (0 for the first hop)
    hop_key: float | None  # s before the jump: this hop's key down sent
    cast_start: float  # s before the jump
    cast_end: float | None  # s after the jump
    landed_line: float | None  # s after the jump: the macro's "landed at" line
    herald: int | None  # the Herald pack's tier the log names around it
    first: bool  # HERALD_MARK_FIRST's line between the jump and the mark key
    between: list = field(default_factory=list)  # skills cast between the jump and the mark's cast
    key: float | None = None  # s after the jump: the first mark key down sent
    keys: int = 0  # mark keys sent in the window
    lost: int = 0  # of those, keys with no Death Mark cast and no state
    retries: int = 0  # keys after the first one at the same aimed unit
    outcome: str = ''  # the first key's (Key.outcome)
    cast_seen: bool = False  # the mark's cast start seen (a mode change); else from the state, CAST_TO_STATE before
    ahead: bool = False  # no cast of the character's between the jump and the mark's key: the mark went first
    mark_cast: float | None = None  # s after the jump
    mark_end: float | None = None  # s after the jump (None: chained into the next cast)
    state: float | None = None  # s after the jump: state 212 on a unit
    unit: int | None = None
    aimed: int | None = None
    wrong: bool = False
    why: list = field(default_factory=list)  # with no mark key: the macro's lines that say why
    # The mark's effect (paths.jsonl targets), s after the state: the first companion going for the marked unit, and
    # the marked unit turning onto a companion; its target as the state showed (character, companion, other, None)
    pets_on: float | None = None
    turned: float | None = None
    was_on: str | None = None
    next_hop: float | None = None  # s after the jump: the next hop's cast start, inside the window

    def applied(self) -> float | None:
        """s after the jump the mark's cast re-applies a mark the aimed unit had already ('already on')."""
        if self.outcome != 'already on' or self.mark_cast is None:
            return None
        return self.mark_cast + CAST_TO_STATE

    def stages(self) -> dict[str, float | None]:
        """The intervals in ms."""

        def ms(value: float | None) -> float | None:
            return None if value is None else round(1000 * value)

        def gap(a: float | None, b: float | None) -> float | None:
            return None if a is None or b is None else round(1000 * (b - a))

        return {
            'move->jump': ms(self.move_start),
            'hop key->jump': ms(self.hop_key),
            'jump->tp end': ms(self.cast_end),
            'jump->landed line': ms(self.landed_line),
            'jump->key': ms(self.key),
            'key->cast': gap(self.key, self.mark_cast),
            'cast->state': gap(self.mark_cast, self.state) if self.cast_seen else None,
            'jump->cast': ms(self.mark_cast),
            'jump->state': ms(self.state),
            # the state shown, or for a unit that had it already, the moment the cast re-applies it (CAST_TO_STATE)
            'jump->applied': ms(self.state if self.state is not None else self.applied()),
            # from the last hop's cast start: the Teleport's animation the player sees begin
            'tp cast->mark cast': None if self.mark_cast is None else ms(self.cast_start + self.mark_cast),
            'tp cast->state': None if self.state is None else ms(self.cast_start + self.state),
            'state->pets on it': ms(self.pets_on),
            'state->it turns': ms(self.turned),
            'move->state': None if self.state is None or self.move_start is None else ms(self.move_start + self.state),
            'first jump->state': None if self.state is None else ms(self.first_jump + self.state),
            'landed line->key': gap(self.landed_line, self.key),
        }


def cast_at(truth: Truth, t: float) -> Cast | None:
    """The cast under way at t."""
    for cast in truth.casts:
        if cast.start <= t and (cast.end is None or t < cast.end):
            return cast
    return None


def mark_casts(truth: Truth, start: float, end: float) -> list[Cast]:
    return [c for c in truth.casts if c.skill == DEATH_MARK and start <= c.start < end]


def keys_of(truth: Truth) -> list[Key]:
    """Every mark key down sent, followed to its cast and its state."""
    downs = [e for e in truth.sent if e.get('input') == 'key' and e.get('name') == truth.mark_key]
    found = []
    for i, e in enumerate(downs):
        if not e.get('down'):
            continue
        t = e['t']
        up = next((u['t'] for u in downs[i + 1 :] if not u.get('down')), None)
        later = [d['t'] for d in downs[i + 1 :] if d.get('down')]
        upto = later[0] if later else t + 3.0
        busy = cast_at(truth, t)
        busy_end = busy.end if busy is not None and busy.end is not None else t
        deadline = min(upto, max(t, busy_end) + LOST)
        aimed = next(
            (int(m.group(3)) for lt, text in truth.lines if t <= lt <= t + 0.3 and (m := MARK_ON.search(text))), None
        )
        frame = truth.frame_at(t)
        hover = truth.hover_at(t)
        key = Key(
            truth.name,
            truth.local(t),
            t,
            round(up - t, 3) if up is not None and up - t < 2.0 else None,
            busy.skill if busy is not None else None,
            round(busy_end - t, 3) if busy is not None else None,
            aimed,
            hover[1] if isinstance(hover, list) and len(hover) == 2 and hover[0] == 1 else None,
            under_pointer(frame) if frame is not None else [],
        )
        found.append(key)
        casts = mark_casts(truth, t - 0.01, deadline)
        start = casts[0].start if casts else t
        # Up to SHOWS s after the cast, and never as late as the next key's own state (CAST_TO_STATE after it)
        last = min(start + SHOWS, upto + CAST_TO_STATE - 0.03)
        shown = [(st, unit) for st, unit in truth.marks_on if start - 0.05 <= st <= last]
        if aimed is not None and any(unit == aimed for _, unit in shown):
            shown = [s for s in shown if s[1] == aimed]
        if shown:
            key.state, key.unit = round(shown[0][0] - t, 3), shown[0][1]
        if casts:
            key.cast, key.chained = round(casts[0].start - t, 3), casts[0].chained
        if not casts and not shown:
            key.outcome = 'lost'
        elif not casts:
            key.outcome = 'unseen cast'
        elif aimed is not None and not shown and truth.marked_at(aimed, t):
            key.outcome = 'already on'
        elif not shown:
            key.outcome = 'no state'
        else:
            key.outcome = 'took' if aimed in (None, key.unit) else 'wrong target'
    return found


def landings(truth: Truth, keys: list[Key], move_gap: float = MOVE_GAP) -> list[Landing]:
    jumps: list[tuple[float, Cast]] = []
    for before, now in zip(truth.frames, truth.frames[1:], strict=False):
        a, b = before['p'], now['p']
        if a[2] != b[2]:
            continue
        if ((b[3] - a[3]) ** 2 + (b[4] - a[4]) ** 2) ** 0.5 > JUMP_STEP:
            cast = cast_at(truth, now['t'])
            if cast is not None and cast.skill in JUMPS:
                jumps.append((now['t'], cast))
    hop_downs = [
        e['t'] for e in truth.sent if e.get('input') == 'key' and e.get('down') and e.get('name') in truth.jump_keys
    ]
    moves: list[list[int]] = []
    for i, (_, cast) in enumerate(jumps):
        if moves:
            last_t = jumps[moves[-1][-1]][0]
            if cast.start - last_t <= move_gap and not mark_casts(truth, last_t, cast.start):
                moves[-1].append(i)
                continue
        moves.append([i])
    rows = []
    for move in moves:
        first_cast = jumps[move[0]][1]
        first_key = key_before(hop_downs, first_cast.start)
        move_start = first_key if first_key is not None else first_cast.start
        first_jump = jumps[move[0]][0]
        for hop, i in enumerate(move, 1):
            t, cast = jumps[i]
            hop_key = key_before(hop_downs, cast.start)
            next_cast = jumps[i + 1][1].start if i + 1 < len(jumps) else None
            end = min(t + WINDOW, next_cast) if next_cast is not None else t + WINDOW
            rows.append(
                landing(truth, keys, t, cast, (hop, len(move)), (move_start, first_jump), hop_key, end, next_cast)
            )
    return rows


def key_before(downs: list[float], start: float, within: float = 0.6) -> float | None:
    """The last hop key down sent before a cast's start, within `within` s (a key under a cast waits for its end)."""
    i = bisect.bisect_right(downs, start + 0.005) - 1
    return downs[i] if i >= 0 and start - downs[i] <= within else None


def landing(
    truth: Truth,
    keys: list[Key],
    t: float,
    cast: Cast,
    place: tuple[int, int],
    move: tuple[float, float],
    hop_key: float | None,
    end: float,
    next_cast: float | None,
) -> Landing:
    near = [text for lt, text in truth.lines if t - 3.0 <= lt <= t + 4.0]
    tiers = [int(m.group(1)) for text in near if (m := HERALD.search(text))]
    landed = next((lt for lt, text in truth.lines if cast.start <= lt <= t + 1.0 and text.startswith(LANDED)), None)
    row = Landing(
        truth.name,
        truth.local(t),
        t,
        cast.skill,
        *place,
        round(t - move[0], 3),
        round(t - move[1], 3),
        round(t - hop_key, 3) if hop_key is not None else None,
        round(t - cast.start, 3),
        round(cast.end - t, 3) if cast.end is not None else None,
        round(landed - t, 3) if landed is not None else None,
        max(tiers) if tiers else None,
        False,
        next_hop=round(next_cast - t, 3) if next_cast is not None and next_cast <= t + WINDOW else None,
    )
    mine = [k for k in keys if cast.start <= k.t < end]
    row.keys, row.lost = len(mine), sum(1 for k in mine if k.outcome == 'lost')
    if not mine:
        row.why = [text[len(logwords.SAID) :][:160] for lt, text in truth.lines if t <= lt < end and WHY.search(text)]
        row.why = row.why[:4]
        row.between = [c.skill for c in truth.casts if t < c.start < end and c is not cast]
        return row
    first = mine[0]
    row.key, row.outcome = round(first.t - t, 3), first.outcome
    row.first = any(FIRST in text for lt, text in truth.lines if t <= lt <= first.t + 0.3)
    row.retries = sum(1 for k in mine[1:] if k.aimed == first.aimed)
    took = next((k for k in mine if k.state is not None or k.cast is not None), None)
    if took is not None:
        if took.cast is not None:
            start, row.cast_seen = took.t + took.cast, True
        else:  # a cast chained inside another (no mode change): its start by the state's fixed lag
            start = took.t + (took.state or 0.0) - CAST_TO_STATE
        row.mark_cast = round(start - t, 3)
        mark = next((c for c in truth.casts if row.cast_seen and abs(c.start - start) < 1e-6), None)
        if (
            mark is not None
            and mark.end is not None
            and not any(c.chained and c.start == mark.end for c in truth.casts)
        ):
            row.mark_end = round(mark.end - t, 3)
        if took.state is not None:
            row.state, row.unit = round(took.t + took.state - t, 3), took.unit
        row.aimed, row.wrong = took.aimed, took.outcome == 'wrong target'
    row.between = [c.skill for c in truth.casts if t < c.start < first.t and c is not cast]
    row.ahead = not row.between
    if row.state is not None and row.unit is not None:
        effects(truth, row, t + row.state)
    return row


def target_at(truth: Truth, unit: int, t: float) -> int | None:
    rows = truth.targets.get(unit, [])
    i = bisect.bisect_right([r[0] for r in rows], t) - 1
    return rows[i][1] if i >= 0 else None


def effects(truth: Truth, row: Landing, shown: float, within: float = WINDOW) -> None:
    """The mark's effect on the targets after its state showed at `shown` (the paths' target unit, written at a
    change): the first companion's target becoming the marked unit, the marked unit's becoming a companion."""
    unit = row.unit
    assert unit is not None
    now = target_at(truth, unit, shown)
    row.was_on = (
        None
        if now is None
        else 'character'
        if now == truth.player
        else 'companion'
        if now in truth.companions
        else 'other'
    )
    pets = [
        t
        for pet in truth.companions
        for t, target in truth.targets.get(pet, [])
        if shown - 0.3 <= t <= shown + within and target == unit and target_at(truth, pet, t - 1e-3) != unit
    ]
    row.pets_on = round(min(pets) - shown, 3) if pets else None
    if row.was_on != 'companion':
        turns = [
            t
            for t, target in truth.targets.get(unit, [])
            if shown <= t <= shown + within and target in truth.companions
        ]
        row.turned = round(turns[0] - shown, 3) if turns else None


# --- The clocks ------------------------------------------------------------------------------------------------------


def quantiles(values: list[float], marks: tuple[float, ...] = (0.5, 0.9)) -> list[float | None]:
    ordered = sorted(v for v in values if v is not None)
    if not ordered:
        return [None for _ in marks]
    return [round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 1) for q in marks]


def clocks(truth: Truth, directory: Path, runs: Path = logwords.RUNS) -> dict[str, Any]:
    """The harness's own checks (ms): the frame clock against the game's millisecond clock (residual about its median),
    the take's log events against probe.log's stamps of the same lines, a key sent against the frame that first has it
    down, and the hop's key against its cast."""
    found: dict[str, Any] = {}
    residual = []
    for f in truth.frames:
        raw = f.get('k')
        if raw and len(raw) >= 2 * (CLOCK_BYTE + 4):
            residual.append(struct.unpack_from('<I', bytes.fromhex(raw), CLOCK_BYTE)[0] / 1000 - f['t'])
    if residual:
        middle = sorted(residual)[len(residual) // 2]
        spread = [1000 * (r - middle) for r in residual]
        found['game clock - frame clock (p1, p50, p99, ms)'] = quantiles(spread, (0.01, 0.5, 0.99))
    serve = anomalies.serve_of(directory.name, runs)
    if serve is not None and truth.lines:
        start, end = truth.lines[0][0] + truth.offset - 2.0, truth.lines[-1][0] + truth.offset + 2.0
        stamped: dict[str, list[float]] = {}
        for epoch, text in serve.between(start, end):
            stamped.setdefault(text[logwords.STAMP_LEN :].split(' ', 2)[-1], []).append(epoch)
        gaps = []
        for t, text in truth.lines:
            near = [epoch - (t + truth.offset) for epoch in stamped.get(text, [])]
            if near:
                gaps.append(1000 * min(near, key=abs))
        found['probe.log - take log (p1, p50, p99, ms)'] = quantiles(gaps, (0.01, 0.5, 0.99))
        found['log lines matched'] = len(gaps)
    seen = []
    keys_down = [(f['t'], set(f['in'][5]) if len(f.get('in', [])) > 5 and f['in'][5] else set()) for f in truth.frames]
    names = {v: int(k) for k, v in json.loads((directory / 'manifest.json').read_text()).get('keys', {}).items()}
    times = [k[0] for k in keys_down]
    for e in truth.sent:
        if e.get('input') != 'key' or not e.get('down') or e.get('name') not in names:
            continue
        i = bisect.bisect_left(times, e['t'])
        for t, down in keys_down[i : i + 6]:
            if e['code'] in down:
                seen.append(1000 * (t - e['t']))
                break
    found['key sent -> seen down (p50, p90, ms)'] = quantiles(seen)
    return found


# --- The command -----------------------------------------------------------------------------------------------------


def summary(rows: list[Landing]) -> list[str]:
    lines = []
    keys = rows[0].stages().keys() if rows else []
    for name in keys:
        values = [r.stages()[name] for r in rows]
        present = [v for v in values if v is not None]
        p50, p90 = quantiles(present)
        lines.append(f'  {name:18s} n={len(present):4d}  p50 {p50}  p90 {p90}')
    return lines


def row_line(row: Landing) -> str:
    s = row.stages()

    def v(name: str) -> str:
        value = s[name]
        return '-' if value is None else f'{value:.0f}'

    tail = (
        f'key +{v("jump->key")} cast +{v("jump->cast")} state +{v("jump->state")} (move +{v("move->state")})'
        if row.keys
        else f'no mark key; why: {" | ".join(row.why) or "none said"}'
    )
    extra = []
    if row.keys:
        extra.append(row.outcome + ('' if row.cast_seen or row.mark_cast is None else ', cast dated by its state'))
    if row.lost:
        extra.append(f'{row.lost} lost')
    if row.retries:
        extra.append(f'{row.retries} retries')
    if row.keys > 1:
        extra.append(f'{row.keys} keys')
    if row.wrong:
        extra.append(f'WRONG target {row.unit} (aimed {row.aimed})')
    if row.between:
        extra.append(f'between {row.between}')
    if row.first or row.ahead:
        extra.append('mark first' + (' (its line)' if row.first else ''))
    return (
        f'{row.take} {row.at} hop {row.hop}/{row.hops} T{row.herald or "-"}: move -{v("move->jump")} '
        f'tp end +{v("jump->tp end")} line +{v("jump->landed line")}; {tail}'
        + (f' [{"; ".join(extra)}]' if extra else '')
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('takes', nargs='*', help='take directories or names (runs/combat/<name>)')
    parser.add_argument('--since', type=logwords.local)
    parser.add_argument('--until', type=logwords.local)
    parser.add_argument('--herald', type=int, help='only landings by a Herald pack of this tier or more')
    parser.add_argument('--marked', action='store_true', help='only landings a mark key followed')
    parser.add_argument('--move-gap', type=float, default=MOVE_GAP)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--summary', action='store_true', help='p50/p90 of each stage after the lines')
    args = parser.parse_args()
    directories = [Path(t) if Path(t).is_dir() else COMBAT / t for t in args.takes]
    if args.since is not None:
        directories += anomalies.takes_since(args.since, args.until)
    if not directories:
        parser.error('a take or --since')
    rows: list[Landing] = []
    all_keys: list[Key] = []
    checks: dict[str, Any] = {}
    for directory in directories:
        try:
            truth = load(directory)
        except (OSError, ValueError, KeyError, IndexError) as error:
            print(f'{directory.name}: unread ({error})', file=sys.stderr)
            continue
        keys = keys_of(truth)
        found = landings(truth, keys, args.move_gap)
        if args.herald is not None:
            found = [r for r in found if r.herald is not None and r.herald >= args.herald]
        if args.marked:
            found = [r for r in found if r.keys]
        rows += found
        all_keys += keys
        if args.json or args.summary:
            checks[directory.name] = clocks(truth, directory)
        if not args.json:
            for row in found:
                print(row_line(row), flush=True)
    if args.json:
        print(
            json.dumps(
                {
                    'landings': [asdict(r) | {'stages': r.stages()} for r in rows],
                    'keys': [asdict(k) for k in all_keys],
                    'clocks': checks,
                },
                indent=1,
            )
        )
        return
    if args.summary:
        print(f'{len(rows)} landings; stages (ms):')
        print('\n'.join(summary(rows)))
        outcomes: dict[str, int] = {}
        for key in all_keys:
            outcomes[key.outcome] = outcomes.get(key.outcome, 0) + 1
        print(f'mark keys: {outcomes}')
        for name, check in checks.items():
            print(f'clocks {name}: {check}')


if __name__ == '__main__':
    main()
