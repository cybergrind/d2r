"""A stopwatch of the stand after a Teleport: from the landing to the Death Mark, read from the game's state.

The player, 2026-10-24 ~20:11: "we already teleported and standing, daemon is with us ... we're not casting DM for an
extended period of time. not 300ms but way more than that. now it is the your real goal: measure this real delay
first". Then: "some kind of real-time memory reading would be better than a screenshot based solution"
(rca/2026-10-24/stopwatch-findings.md).

One analysis (`Stopwatch`) over a stream of `Sample`s. Each sample has the character's position, mode, skill in use,
life and mana; the companions (mercenary, pets); and the hostiles within NEAR with their mode and whether Death Mark
(state 212) is on them. Three sources make the stream:

- `live`: the combat take the service's recorder child is writing now (runs/combat/<UTC>-<area>/). That child is a
  process with its own memory handle and reads the game at 25 frames a second. Here its frames and unit records are
  followed as they reach the disk, about 0.5-1 s late (the files' buffers). The frames keep their own read times. This
  is the source that works from an agent's sandbox, which cannot see the game's process.
- `takes`: the same over closed takes (`--since`), to measure again after the fact;
- `memory`: the game's memory, read directly at RATE (100/s). Each sample is one process_vm_readv of the few fields
  needed: mode, position, the skill-in-use pointer, the stat list and one state word for each tracked unit. The units
  are found again every DISCOVER_SECONDS. It needs a process that can see D2R.exe (the recorder child, behind a
  switch: rca/2026-10-24/stopwatch-sampler.patch). It writes its samples to `samples.jsonl`, which `samples` reads
  back.

A landing is the character's position jumping more than JUMP_STEP units between two samples of one level (Teleport,
Blade Warp). For each landing a line is printed at once and appended to --out. Its times are from the landing:

    stand (the first neutral mode) | first cast and its skill | Death Mark's cast | state 212 on a monster (which)
    | the strike (Echoing Strike) | the next hop's cast and its landing | the hostiles near | stood without a mark

"stood X s without a Death Mark" runs from the stand to the Death Mark's cast start, or to the next hop's cast when no
mark came. It is flagged when a hostile was within STRIKE_REACH or SCREEN_REACH, with its Herald tier when that is
read. The service's probe.log lines of the same moment split the stand:
- notice: the landing to the macro's "landed at" line;
- deciding: that line to its "Death Mark on <key>" line, which it logs as it taps the key, with the act queue's judge
  times when it logged them;
- flight: the key to the cast start;
- curse: the cast start to state 212 showing.

Ids from the installed game's tables, never from memory (a test checks them): skills.txt Teleport 54, Death Mark 375,
Echoing Strike 388, Blade Warp 390; states.txt death_mark 212.

    python3 stopwatch.py live [--minutes 25] [--out FILE]
    python3 stopwatch.py takes --since 'YYYY-MM-DD HH:MM' [--until ...] [--out FILE] [--json]
    python3 stopwatch.py samples FILE...           # a memory run's samples
    uv run --offline python stopwatch.py memory --pid P --base B --table T --dir DIR [--rate 100] [--minutes M]
    python3 stopwatch.py summary FILE...           # stands written with --json: p50/p90/max, Heralds apart

Stdlib only, except `memory`, which imports the repo's readers.
"""

import argparse
import bisect
import gzip
import json
import math
import os
import re
import resource
import struct
import sys
import time
import zlib
from collections.abc import Callable, Iterable, Iterator
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from logwords import ACT, LANDED, MARK_KEY, STRIKE_LINE, WHY


ROOT = Path(__file__).resolve().parents[4]
COMBAT = ROOT / 'inventory_tracking' / 'runs' / 'combat'
SESSIONS = ROOT / 'inventory_tracking' / 'runs' / 'alt-d'
OUT = ROOT / 'inventory_tracking' / 'runs' / 'stopwatch'

TELEPORT, DEATH_MARK, ECHOING_STRIKE, BLADE_WARP = 54, 375, 388, 390  # skills.txt *Id
JUMPS = frozenset((TELEPORT, BLADE_WARP))
SKILL_NAMES = {
    TELEPORT: 'Teleport',
    DEATH_MARK: 'Death Mark',
    ECHOING_STRIKE: 'Echoing Strike',
    BLADE_WARP: 'Blade Warp',
}
MARK_STATE = 212  # states.txt `death_mark`
MARK_WORD, MARK_BIT = divmod(MARK_STATE, 32)  # word 6 of the state run (game/layout.py STATE_RUN): STATE_FLAGS
# The character's modes (game/layout.py ACTING; player modes 1 neutral, 5 town neutral, 0 and 17 dead)
ACTING = frozenset((7, 8, 10, 11, 12, 13, 14, 15, 16, 18))
NEUTRAL = frozenset((1, 5))
PLAYER_DEAD = frozenset((0, 17))
MONSTER_DEAD = frozenset((0, 12))
NO_OWNER = 4294967295
HIRELING = 338  # monstats.txt act2hire (native/layout.py HIRELING_CLASS_ID)
DEFILER = 744  # monstats.txt warbighead, the War Defiler (game/layout.py DEFILER_CLASS)
UNIQUE_FLAG = 8  # monster data type flags: the Herald (its members have 16; dm-truth-findings.md §2)
JUMP_STEP = 5.0  # units between two samples: a jump, not a walk (anomalies.py JUMP_STEP)
GAP = 0.25  # seconds between two samples past which a jump is not trusted (a load, a stall of the reader)
NEAR = 40.0  # units: the hostiles tracked
STRIKE_REACH = 22.0  # echoing_strike/mechanics.py RANGE (22.1)
SCREEN_REACH = 30.0  # casters.py ENGORGE_DANGER_REACH "on the screen still"; hunting/base.py SIGHT
WINDOW = 8.0  # seconds a stand is followed at most when no hop ends it
LINES_SLACK = 0.15  # seconds: probe.log lines this far before the landing still belong to it (its ms stamps)
TIER_STAT = 367  # itemstatcost `heraldtier` (game/layout.py HERALD_TIER_STAT)


# --- The stream ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Foe:
    unit: int
    cls: int
    mode: int
    x: float
    y: float
    flags: int = 0
    marked: bool | None = None  # state 212 on it; None: unread
    tier: int = 0  # its Herald tier (0: none or unread)


@dataclass(frozen=True)
class Sample:
    t: float  # monotonic seconds (CLOCK_MONOTONIC, the same in every process)
    wall: float  # epoch seconds
    area: int
    x: float
    y: float
    mode: int
    skill: int | None  # the skill in use; None: unread
    life: int = 0
    mana: int = 0
    companions: tuple[tuple[int, int, int, float, float], ...] = ()  # (unit, class, mode, x, y)
    foes: tuple[Foe, ...] = ()


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def local(wall: float) -> str:
    return datetime.fromtimestamp(wall).strftime('%H:%M:%S.%f')[:-3]


# --- The analysis ----------------------------------------------------------------------------------------------------


@dataclass
class Stand:
    """One landing and what followed it. Times are seconds from the landing; None: did not happen."""

    landed: float  # monotonic
    wall: float
    area: int
    at: tuple[float, float]
    hop: float | None = None  # the hop's cast start, before the landing (negative)
    hop_skill: int | None = None
    stand: float | None = None  # the first neutral mode
    first_cast: float | None = None
    first_skill: int | None = None
    mark_cast: float | None = None  # skill in use = Death Mark, a cast starting
    mark_on: float | None = None  # state 212 newly on a hostile
    mark_unit: int | None = None
    mark_cls: int | None = None
    strike: float | None = None
    next_hop: float | None = None  # the next hop's cast start
    next_landing: float | None = None
    end: float = 0.0  # where the stand was closed
    why_closed: str = ''
    strike_near: int = 0  # hostiles within STRIKE_REACH at the landing or the stand
    screen_near: int = 0
    nearest: float | None = None
    tier: int = 0  # the highest Herald tier among the hostiles within SCREEN_REACH
    herald: bool = False  # the Herald itself within SCREEN_REACH
    marked_near: int = 0  # hostiles within SCREEN_REACH already marked when it stood
    neutral: float = 0.0  # seconds in a neutral mode before the mark's cast (or the stand's end)
    companions: list[str] = field(default_factory=list)  # 'merc 6.1', 'pet 3.2': their distance at the stand
    casts: list[tuple[float, int | None]] = field(default_factory=list)  # every cast start after the landing
    life: int = 0
    # joined from probe.log (seconds from the landing)
    noticed: float | None = None  # the "landed at" line
    key: float | None = None  # the "Death Mark on <key>" line (the key tapped)
    strike_line: float | None = None
    judge_ms: list[float] = field(default_factory=list)  # the act queue's per-act judge times within the stand
    input_ms: list[float] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    herald_line: int = 0  # the tier a "tier N Herald" line around it names

    @property
    def stood(self) -> float | None:
        """The stand to the Death Mark's cast, or to the next hop / the end when no mark came."""
        start = self.stand if self.stand is not None else 0.0
        stop = self.mark_cast
        if stop is None:
            stop = self.next_hop if self.next_hop is not None else self.end
        return max(0.0, stop - start)

    @property
    def near(self) -> bool:
        return self.screen_near > 0

    @property
    def heralded(self) -> int:
        return max(self.tier, self.herald_line)

    def parts(self) -> dict[str, float | None]:
        """The stand split: the macro noticing the landing, deciding (to its key), the key's flight, the curse."""

        def gap(a: float | None, b: float | None) -> float | None:
            return None if a is None or b is None else b - a

        return {
            'notice': self.noticed,
            'deciding': gap(self.noticed, self.key),
            'flight': gap(self.key, self.mark_cast),
            'curse': gap(self.mark_cast, self.mark_on),
        }


def seconds(value: float | None) -> str:
    return '-' if value is None else f'{value:+.2f}'


def skill_name(skill: int | None) -> str:
    return SKILL_NAMES.get(skill, f'skill {skill}') if skill is not None else 'skill ?'


def say(stand: Stand) -> str:
    """The stand's one line."""
    hop = f'hop {skill_name(stand.hop_skill)} cast {seconds(stand.hop)}' if stand.hop is not None else 'hop ?'
    first = f'{seconds(stand.first_cast)} {skill_name(stand.first_skill)}' if stand.first_cast is not None else '-'
    mark_on = '-'
    if stand.mark_on is not None:
        mark_on = f'{seconds(stand.mark_on)} on {stand.mark_cls} ({stand.mark_unit})'
    near = f'near {stand.strike_near}/{STRIKE_REACH:.0f} {stand.screen_near}/{SCREEN_REACH:.0f}'
    if stand.nearest is not None:
        near += f' nearest {stand.nearest:.1f}'
    if stand.heralded:
        near += f' T{stand.heralded}' + (' Herald' if stand.herald else ' pack')
    if stand.marked_near:
        near += f' {stand.marked_near} marked already'
    stood = stand.stood
    flag = ''
    if stand.near and stood is not None:
        flag = f' | STOOD {stood:.2f} s without a Death Mark' + ('' if stand.mark_cast is not None else ' (none came)')
    parts = stand.parts()
    macro = ' | macro: ' + ', '.join(f'{name} {seconds(value)}' for name, value in parts.items())
    if stand.judge_ms:
        macro += ' judge ' + '/'.join(f'{ms:.0f}' for ms in stand.judge_ms) + ' ms'
    return (
        f'{local(stand.wall)} L{stand.area} {hop} | stand {seconds(stand.stand)} | first cast {first} | '
        f'DM cast {seconds(stand.mark_cast)} | 212 {mark_on} | strike {seconds(stand.strike)} | '
        f'next hop {seconds(stand.next_hop)} | {near} | neutral {stand.neutral:.2f}{flag}{macro}'
    )


class Stopwatch:
    """The stands of a sample stream: `feed` each sample in time order, `finish` at its end. Each closed stand goes to
    `emit`."""

    def __init__(self, emit: Callable[[Stand], None], pets: Callable[[PetStand], None] | None = None) -> None:
        self.emit = emit
        self.pets = PetWatch(pets) if pets is not None else None
        self.landed_at = -math.inf  # the last landing (monotonic)
        self.before: Sample | None = None
        self.open: Stand | None = None
        self.acting_skill: int | None = None  # the skill of the cast under way (None: no cast)
        self.cast_start: tuple[float, int | None] | None = None  # the cast under way: start, skill
        self.marked: dict[int, bool] = {}  # hostile -> state 212 at the sample before
        self.stood_at: Sample | None = None

    def feed(self, sample: Sample) -> None:
        before = self.before
        self.before = sample
        if before is None or sample.area != before.area or sample.t - before.t > GAP:
            self.close(before.t if before is not None else sample.t, 'level or gap')
            if self.pets is not None:
                self.pets.close(before.t if before is not None else sample.t, 'level or gap')
            self.cast_start = None
            self.marked = {foe.unit: bool(foe.marked) for foe in sample.foes}
            return
        started = self.cast(before, sample)
        jumped = distance(before.x, before.y, sample.x, sample.y) > JUMP_STEP
        if jumped and sample.mode not in PLAYER_DEAD:
            self.land(before, sample)
            self.landed_at = sample.t
        marked = [
            f for f in sample.foes if f.marked and self.marked.get(f.unit) is False and f.mode not in MONSTER_DEAD
        ]
        stand = self.open
        if stand is not None and not jumped:
            self.follow(stand, before, sample, started, marked)
        if self.pets is not None:
            self.pets.step(before, sample, started, marked, self.landed_at)
        self.marked = {foe.unit: bool(foe.marked) for foe in sample.foes if foe.marked is not None}
        if stand is not None and self.open is stand and sample.t - stand.landed > WINDOW:
            self.close(sample.t, 'window')

    def cast(self, before: Sample, sample: Sample) -> tuple[float, int | None] | None:
        """A cast starting at this sample: the mode entering a cast, or the skill in use changing within one (a cast
        chained in another with no change of mode)."""
        if sample.mode not in ACTING:
            self.cast_start = None
            return None
        chained = before.mode in ACTING and self.cast_start is not None and sample.skill != self.cast_start[1]
        if before.mode not in ACTING or self.cast_start is None or (chained and sample.skill is not None):
            self.cast_start = (sample.t, sample.skill)
            return self.cast_start
        return None

    def land(self, before: Sample, sample: Sample) -> None:
        if self.open is not None:
            self.open.next_landing = sample.t - self.open.landed
            self.close(sample.t, 'next landing')
        stand = Stand(sample.t, sample.wall, sample.area, (round(sample.x, 1), round(sample.y, 1)), life=sample.life)
        if self.cast_start is not None:
            stand.hop, stand.hop_skill = self.cast_start[0] - sample.t, self.cast_start[1]
        self.open = stand
        self.stood_at = None
        self.measure(stand, sample)

    def measure(self, stand: Stand, sample: Sample) -> None:
        """The hostiles and companions around the character at `sample` (the landing, then the stand)."""
        hostile = [f for f in sample.foes if f.mode not in MONSTER_DEAD]
        reach = [(distance(sample.x, sample.y, f.x, f.y), f) for f in hostile]
        stand.strike_near = sum(d <= STRIKE_REACH for d, _ in reach)
        screen = [f for d, f in reach if d <= SCREEN_REACH]
        stand.screen_near = len(screen)
        stand.nearest = round(min((d for d, _ in reach), default=math.inf), 1) if reach else None
        stand.tier = max((f.tier for f in screen), default=0)
        stand.herald = any(f.tier and f.flags & UNIQUE_FLAG for f in screen)
        stand.marked_near = sum(bool(f.marked) for f in screen)
        stand.companions = [
            f'{"merc" if cls == HIRELING else f"pet {cls}"} {distance(sample.x, sample.y, x, y):.1f}'
            for _, cls, mode, x, y in sample.companions
            if mode not in MONSTER_DEAD
        ]

    def follow(
        self, stand: Stand, before: Sample, sample: Sample, started: tuple[float, int | None] | None, marked: list[Foe]
    ) -> None:
        at = sample.t - stand.landed
        if stand.stand is None and sample.mode in NEUTRAL:
            stand.stand = at
            self.measure(stand, sample)
        if sample.mode in NEUTRAL and stand.mark_cast is None:
            stand.neutral += sample.t - before.t
        if started is not None:
            _, skill = started
            stand.casts.append((round(at, 3), skill))
            if stand.first_cast is None:
                stand.first_cast, stand.first_skill = at, skill
            if skill == DEATH_MARK and stand.mark_cast is None:
                stand.mark_cast = at
            if skill == ECHOING_STRIKE and stand.strike is None:
                stand.strike = at
            if skill in JUMPS and stand.next_hop is None:
                stand.next_hop = at
        if stand.mark_on is None and marked:
            stand.mark_on, stand.mark_unit, stand.mark_cls = at, marked[0].unit, marked[0].cls
        if sample.mode in PLAYER_DEAD:
            self.close(sample.t, 'dead')

    def close(self, t: float, why: str) -> None:
        stand = self.open
        if stand is None:
            return
        self.open = None
        stand.end, stand.why_closed = max(0.0, t - stand.landed), why
        self.emit(stand)

    def finish(self) -> None:
        if self.before is not None:
            self.close(self.before.t, 'end')
            if self.pets is not None:
                self.pets.close(self.before.t, 'end')


# --- The player's measure: standing with the demons -------------------------------------------------------------------

PET_NEAR = 4.5  # units: a pet this near the character stands with it (the 20:18:41 fight: 0.1 after a warp, 3.7 idle)
PET_ENGAGED = 5.0  # units: a pet with a live hostile this near it is in the fight, not standing with the character
PET_GAP = 0.2  # seconds a pet may be off (or no hostile near) without ending the stand
PET_IDLE = frozenset((1,))  # monster mode neutral


@dataclass
class PetStand:
    """The demons standing with the character while a hostile lives within SCREEN_REACH: a pet within PET_NEAR of the
    character with no live hostile within PET_ENGAGED of it (a melee scrum at the character is a fight, not a stand),
    from the pets coming to the character (or a landing that brings them) to their leaving it or going into the fight.
    Times are seconds from the start."""

    start: float  # monotonic
    wall: float
    area: int
    by: str  # 'landing' (one within PET_GAP before) or 'pets came'
    pets: list[str] = field(default_factory=list)  # the pets with the character at the start
    length: float = 0.0
    why_ended: str = ''
    idle: float = 0.0  # seconds a pet near was idle (mode neutral)
    still: float = 0.0  # seconds the character was in a neutral mode
    strikes: int = 0  # Echoing Strike casts seen in it
    casts: list[tuple[float, int | None]] = field(default_factory=list)
    marked_at_start: int = 0  # hostiles within SCREEN_REACH that had the mark already
    marked_live: float = 0.0  # seconds a marked hostile lived within SCREEN_REACH while the pets stood
    curse: float | None = None  # state 212 newly on a hostile
    curse_unit: int | None = None
    curse_cls: int | None = None
    left_after_curse: float | None = None  # the pets' leaving after the curse (seconds)
    mark_casts: list[float] = field(default_factory=list)  # Death Mark cast starts
    keys: list[float] = field(default_factory=list)  # the macro's "Death Mark on <key>" lines (joined)
    reasons: list[str] = field(default_factory=list)
    tier: int = 0
    herald: bool = False
    hostiles: int = 0  # within SCREEN_REACH at the start
    nearest: float | None = None
    herald_line: int = 0

    @property
    def waited(self) -> float:
        """The start to the curse landing, or the whole stand without one: the time the player sees wasted."""
        return self.curse if self.curse is not None else self.length

    @property
    def heralded(self) -> int:
        return max(self.tier, self.herald_line)


def pet_name(cls: int) -> str:
    return {HIRELING: 'merc', DEFILER: 'Defiler'}.get(cls, f'bound {cls}')


def say_pets(stand: PetStand) -> str:
    curse = '-'
    if stand.curse is not None:
        left = seconds(stand.left_after_curse)
        curse = f'{seconds(stand.curse)} on {stand.curse_cls} ({stand.curse_unit}), pets left {left} after'
    keys = ' '.join(f'{k:+.2f}' for k in stand.keys) or 'none'
    casts = ' '.join(f'{c:+.2f}' for c in stand.mark_casts) or 'none'
    tier = f' T{stand.heralded}' + (' Herald' if stand.herald else ' pack') if stand.heralded else ''
    return (
        f'PETS {local(stand.wall)} L{stand.area} {stand.length:.2f} s with {",".join(stand.pets)} ({stand.by}) | '
        f'curse {curse} | DM keys {keys} | DM casts {casts} | strikes {stand.strikes} | pets idle {stand.idle:.2f} s, '
        f'character still {stand.still:.2f} s | {stand.hostiles} hostiles within {SCREEN_REACH:.0f}{tier}, '
        f'{stand.marked_at_start} marked at the start, a marked one alive {stand.marked_live:.2f} s | {stand.why_ended}'
    )


class PetWatch:
    """The pet stands of a sample stream (`Stopwatch` feeds it)."""

    def __init__(self, emit: Callable[[PetStand], None]) -> None:
        self.emit = emit
        self.open: PetStand | None = None
        self.off_since: float | None = None  # the condition first failed (within PET_GAP it is forgiven)
        self.off_why = ''

    def step(
        self, before: Sample, sample: Sample, started: tuple[float, int | None] | None, marked: list[Foe],
        landed_at: float,
    ) -> None:  # fmt: skip
        pets = [c for c in sample.companions if c[1] != HIRELING and c[2] not in MONSTER_DEAD]
        live = [f for f in sample.foes if f.mode not in MONSTER_DEAD]
        close = [
            c
            for c in pets
            if distance(sample.x, sample.y, c[3], c[4]) <= PET_NEAR
            and not any(distance(c[3], c[4], f.x, f.y) <= PET_ENGAGED for f in live)
        ]
        reach = [(distance(sample.x, sample.y, f.x, f.y), f) for f in live]
        reach = [(d, f) for d, f in reach if d <= SCREEN_REACH]
        stand = self.open
        holds = bool(close) and bool(reach) and sample.mode not in PLAYER_DEAD
        if stand is None:
            if holds:
                self.begin(sample, close, reach, landed_at)
            return
        step = sample.t - before.t
        at = sample.t - stand.start
        if stand.curse is None and marked:  # the pets go for the cursed one in the frame its curse shows
            stand.curse, stand.curse_unit, stand.curse_cls = at, marked[0].unit, marked[0].cls
        if started is not None:
            stand.casts.append((round(at, 3), started[1]))
            if started[1] == ECHOING_STRIKE:
                stand.strikes += 1
            if started[1] == DEATH_MARK:
                stand.mark_casts.append(round(at, 3))
        if not holds:
            if self.off_since is None:
                self.off_since, self.off_why = sample.t, ('no hostile near' if close else 'pets left or fight')
            if sample.t - self.off_since > PET_GAP:
                self.close(self.off_since, self.off_why)
            return
        self.off_since = None
        if any(c[2] in PET_IDLE for c in close):
            stand.idle += step
        if sample.mode in NEUTRAL:
            stand.still += step
        if any(f.marked for _, f in reach):
            stand.marked_live += step

    def begin(self, sample: Sample, close: list, reach: list, landed_at: float) -> None:
        by = 'landing' if sample.t - landed_at <= PET_GAP else 'pets came'
        stand = PetStand(sample.t, sample.wall, sample.area, by, [pet_name(c[1]) for c in close])
        stand.hostiles = len(reach)
        stand.nearest = round(min(d for d, _ in reach), 1)
        stand.marked_at_start = sum(bool(f.marked) for _, f in reach)
        stand.tier = max((f.tier for _, f in reach), default=0)
        stand.herald = any(f.tier and f.flags & UNIQUE_FLAG for _, f in reach)
        self.open, self.off_since = stand, None

    def close(self, t: float, why: str) -> None:
        stand = self.open
        if stand is None:
            return
        self.open, self.off_since = None, None
        stand.length = max(0.0, t - stand.start)
        stand.why_ended = why
        if stand.curse is not None and stand.curse > stand.length + 1e-6:  # a curse after the pets had gone
            stand.curse = stand.curse_unit = stand.curse_cls = None
        stand.casts = [c for c in stand.casts if c[0] <= stand.length + 1e-6]
        stand.mark_casts = [c for c in stand.mark_casts if c <= stand.length + 1e-6]
        stand.strikes = sum(skill == ECHOING_STRIKE for _, skill in stand.casts)
        if stand.curse is not None:
            stand.left_after_curse = round(stand.length - stand.curse, 3)
        self.emit(stand)


# --- probe.log -------------------------------------------------------------------------------------------------------

STAMP = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) \w+ (.*)$')
HERALD = re.compile(r'tier (\d) Herald')


class Lines:
    """probe.log's lines that a stand is joined to, by wall time: (wall, text), in order."""

    def __init__(self) -> None:
        self.walls: list[float] = []
        self.texts: list[str] = []

    def add(self, line: str) -> None:
        found = STAMP.match(line)
        if found is None:
            return
        text = found[3]
        if not text.startswith('Macro'):
            return
        wanted = LANDED in text or 'Death Mark' in text or STRIKE_LINE in text or 'act queue: ' in text
        if not (wanted or WHY.search(text) or HERALD.search(text)):
            return
        wall = datetime.strptime(found[1], '%Y-%m-%d %H:%M:%S').timestamp() + int(found[2]) / 1000
        at = bisect.bisect_right(self.walls, wall)
        self.walls.insert(at, wall)
        self.texts.insert(at, text)

    def between(self, a: float, b: float) -> Iterator[tuple[float, str]]:
        for i in range(bisect.bisect_left(self.walls, a), bisect.bisect_right(self.walls, b)):
            yield self.walls[i], self.texts[i]

    def join(self, stand: Stand) -> None:
        """The stand's macro moments from the lines of its time (seconds from the landing)."""
        wall = stand.wall
        stop = stand.mark_cast if stand.mark_cast is not None else stand.next_hop
        stop = stand.end if stop is None else stop
        for line_wall, text in self.between(wall - LINES_SLACK, wall + stand.end + 0.05):
            at = line_wall - wall
            if LANDED in text and stand.noticed is None and at <= 1.5:
                stand.noticed = at
            elif MARK_KEY.search(text) and stand.key is None and at <= stop + 0.1:
                stand.key = at
            elif STRIKE_LINE in text and stand.strike_line is None:
                stand.strike_line = at
            act = ACT.search(text)
            if act is not None and at <= stop + 0.1:
                stand.judge_ms.append(float(act[3]))
                stand.input_ms.append(float(act[2]))
            if WHY.search(text) and at <= stop + 0.1 and len(stand.reasons) < 4:
                stand.reasons.append(f'{at:+.2f} {text[7:180]}')
        for _, text in self.between(wall - 5.0, wall + 5.0):
            herald = HERALD.search(text)
            if herald is not None:
                stand.herald_line = max(stand.herald_line, int(herald[1]))

    def join_pets(self, stand: PetStand) -> None:
        """A pet stand's Death Mark keys and the macro's reasons from the lines of its time."""
        for line_wall, text in self.between(stand.wall - 0.05, stand.wall + stand.length + 0.05):
            at = line_wall - stand.wall
            if MARK_KEY.search(text):
                stand.keys.append(round(at, 3))
            elif WHY.search(text) and len(stand.reasons) < 5:
                stand.reasons.append(f'{at:+.2f} {text[7:180]}')
        for _, text in self.between(stand.wall - 5.0, stand.wall + stand.length + 5.0):
            herald = HERALD.search(text)
            if herald is not None:
                stand.herald_line = max(stand.herald_line, int(herald[1]))


def session_logs(since: float | None = None) -> list[Path]:
    """The sessions' probe.logs written since `since` (epoch), oldest first; the newest alone without it."""
    logs = sorted(SESSIONS.glob('*/probe.log'), key=lambda p: p.stat().st_mtime)
    if since is None:
        return logs[-1:]
    return [p for p in logs if p.stat().st_mtime >= since]


# --- The take source -------------------------------------------------------------------------------------------------


def opened(path: Path) -> Any:
    if path.exists():
        return path.open('rb')
    gz = path.with_name(path.name + '.gz')
    return gzip.open(gz, 'rb') if gz.exists() else None


def json_lines(path: Path) -> Iterator[dict]:
    handle = opened(path)
    if handle is None:
        return
    with handle:
        try:
            for raw in handle:
                try:
                    yield json.loads(raw)
                except ValueError:
                    continue
        except EOFError, OSError, zlib.error:  # a gzip still being packed, or cut
            return


CUT = b',"x":'  # a frame's missiles and what follows them: not needed here, and most of its bytes
ROW = re.compile(rb'\[(\d+),"[0-9a-f]*","([0-9a-f]*)","([0-9a-f]*)"\]')  # a records row: unit, record, states, skill


def frame_of(raw: bytes) -> dict | None:
    """A frame line's head (time, number, the character, the units), parsed without its missiles and the rest."""
    cut = raw.find(CUT)
    try:
        return json.loads(raw[:cut] + b'}' if cut > 0 else raw)
    except ValueError:
        return None


def record_of(raw: bytes) -> dict | None:
    """A records line as {'n', 'u': [[unit, '', states, skill]]}: the raw records are not kept."""
    head = re.match(rb'\{"t":([\d.]+),"n":(\d+)', raw)
    if head is None:
        return None
    rows = [[int(unit), '', states.decode(), skill.decode()] for unit, states, skill in ROW.findall(raw)]
    return {'t': float(head[1]), 'n': int(head[2]), 'u': rows}


def lines_of(path: Path) -> Iterator[bytes]:
    handle = opened(path)
    if handle is None:
        return
    with handle:
        try:
            yield from handle
        except EOFError, OSError, zlib.error:  # a gzip still being packed, or cut
            return


def state_on(words_hex: str) -> bool | None:
    if not words_hex:
        return None
    raw = bytes.fromhex(words_hex)
    if len(raw) < (MARK_WORD + 1) * 4:
        return None
    return bool(int.from_bytes(raw[MARK_WORD * 4 : MARK_WORD * 4 + 4], 'little') >> MARK_BIT & 1)


def skill_of(raw_hex: str) -> int | None:
    raw = bytes.fromhex(raw_hex) if raw_hex else b''
    return int.from_bytes(raw[:2], 'little') if len(raw) >= 2 else None


class TakeState:
    """A take's frames turned into samples: the records' skill in use and state words, units.jsonl's tiers."""

    def __init__(self, manifest: dict) -> None:
        clock = manifest.get('clock') or {}
        self.offset = clock.get('wall', 0.0) - clock.get('monotonic', 0.0)
        self.skill: int | None = None
        self.marks: dict[int, bool] = {}
        self.tiers: dict[int, int] = {}

    def unit(self, row: dict) -> None:
        tier = (row.get('stats') or {}).get(str(TIER_STAT))
        if tier:
            self.tiers[row['unit']] = int(tier)

    def record(self, row: dict, player: int | None) -> None:
        for unit, _record, states, skill in row.get('u', ()):
            if unit == player:
                found = skill_of(skill)
                self.skill = found if found is not None else self.skill
            else:
                on = state_on(states)
                if on is not None:
                    self.marks[unit] = on

    def sample(self, frame: dict) -> Sample | None:
        p = frame.get('p')
        if not p or not frame.get('game', True):
            return None
        unit, mode, area, x, y = p[:5]
        life = p[7] if len(p) > 7 else 0
        mana = p[9] if len(p) > 9 else 0
        companions, foes = [], []
        for m in frame.get('m', ()):
            m_unit, cls, m_mode, mx, my, *rest = m
            flags = rest[2] if len(rest) > 2 else 0
            owner = rest[3] if len(rest) > 3 else NO_OWNER
            ally = rest[4] if len(rest) > 4 else 0
            # the mercenary, the Defiler, the bound demon (alignment, not owner); an unowned ally that is no demon is
            # not ours: the Bloody Foothills' barbarians, monstats 522/523 (rca/2026-10-24/engorge-findings.md)
            if owner == unit or (ally and cls in demon_classes()):
                companions.append((m_unit, cls, m_mode, mx, my))
            elif not ally and owner == NO_OWNER and distance(x, y, mx, my) <= NEAR:
                foes.append(Foe(m_unit, cls, m_mode, mx, my, flags, self.marks.get(m_unit), self.tiers.get(m_unit, 0)))
        t = frame['t']
        return Sample(t, t + self.offset, area, x, y, mode, self.skill, life, mana, tuple(companions), tuple(foes))


@cache
def demon_classes() -> frozenset[int]:
    """monstats.txt rows with `demon` 1 (the d2data dump): the classes a bound ally may be."""
    rows = json.loads((ROOT / 'third-parties' / 'd2data' / 'json' / 'monstats.json').read_text())
    return frozenset(int(row['*hcIdx']) for row in rows.values() if row.get('demon') == 1)


def take_samples(take: Path) -> Iterator[Sample]:
    """A closed (or open) take's samples, in frame order."""
    try:
        manifest = json.loads((take / 'manifest.json').read_text())
    except OSError, ValueError:
        return
    state = TakeState(manifest)
    for row in json_lines(take / 'units.jsonl'):
        state.unit(row)
    records = (row for row in map(record_of, lines_of(take / 'records.jsonl')) if row is not None)
    pending = next(records, None)
    for frame in map(frame_of, lines_of(take / 'frames.jsonl')):
        if frame is None:
            continue
        player = frame['p'][0] if frame.get('p') else None
        while pending is not None and pending.get('n', 0) <= frame.get('n', 0):
            state.record(pending, player)
            pending = next(records, None)
        sample = state.sample(frame)
        if sample is not None:
            yield sample


def takes_between(since: float, until: float) -> list[Path]:
    found = []
    for take in sorted(COMBAT.iterdir()) if COMBAT.exists() else ():
        try:
            opened_at = datetime.strptime(take.name.split('-')[0], '%Y%m%dT%H%M%SZ').timestamp() + local_offset()
        except ValueError:
            continue
        if since - 3600 <= opened_at <= until:
            found.append(take)
    return found


def local_offset() -> float:
    """Seconds to add to a UTC-named stamp read as local time to get its epoch (the take names are UTC)."""
    now = time.time()
    return datetime.fromtimestamp(now).astimezone().utcoffset().total_seconds()  # pyrefly: ignore[missing-attribute]


class Tail:
    """New whole lines of a growing file (or none once it is gone)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.at = 0
        self.rest = b''

    def lines(self) -> list[bytes]:
        try:
            with self.path.open('rb') as handle:
                handle.seek(self.at)
                chunk = handle.read()
        except OSError:
            return []
        self.at += len(chunk)
        data = self.rest + chunk
        whole, _, self.rest = data.rpartition(b'\n')
        return whole.split(b'\n') if whole else []


class LiveTake:
    """The open take that the recorder child is writing, followed: `poll` gives the samples that came to disk since the
    last poll. A frame waits for the records up to its number, or HOLD seconds past the newest frame."""

    HOLD = 1.0

    def __init__(self, take: Path) -> None:
        self.take = take
        manifest = json.loads((take / 'manifest.json').read_text())
        self.state = TakeState(manifest)
        self.frames = Tail(take / 'frames.jsonl')
        self.records = Tail(take / 'records.jsonl')
        self.units = Tail(take / 'units.jsonl')
        self.waiting: list[dict] = []
        self.records_n = 0
        self.held: list[dict] = []  # records rows not yet applied (ahead of the frames given)
        self.player: int | None = None

    def poll(self) -> list[Sample]:
        for raw in self.units.lines():
            try:
                self.state.unit(json.loads(raw))
            except ValueError:
                continue
        for raw in self.records.lines():
            row = record_of(raw)
            if row is None:
                continue
            self.held.append(row)
            self.records_n = max(self.records_n, row.get('n', 0))
        for raw in self.frames.lines():
            frame = frame_of(raw)
            if frame is not None:
                self.waiting.append(frame)
        out = []
        newest = self.waiting[-1]['t'] if self.waiting else 0.0
        while self.waiting:
            frame = self.waiting[0]
            if frame.get('n', 0) > self.records_n and newest - frame['t'] < self.HOLD:
                break
            self.waiting.pop(0)
            if frame.get('p'):
                self.player = frame['p'][0]
            while self.held and self.held[0].get('n', 0) <= frame.get('n', 0):
                self.state.record(self.held.pop(0), self.player)
            sample = self.state.sample(frame)
            if sample is not None:
                out.append(sample)
        return out

    def gone(self) -> bool:
        return not (self.take / 'frames.jsonl').exists()


def newest_take() -> Path | None:
    """The take being written: the newest by name (a UTC stamp) of the last few, with its frames file open. Not a stat
    of every take (over 3000 directories: a glob and a stat each was most of the live mode's CPU)."""
    if not COMBAT.exists():
        return None
    for name in sorted(n for n in os.listdir(COMBAT) if n[:1].isdigit())[-3:][::-1]:
        if (COMBAT / name / 'frames.jsonl').exists():
            return COMBAT / name
    return None


# --- The memory source -----------------------------------------------------------------------------------------------

RATE = 100.0  # samples a second
DISCOVER_SECONDS = 0.25  # between walks of the unit table (new units, the level)
# Offsets of the unit record and around it (native/units.py walk_units, game/layout.py, game/decode.py)
MODE_AT = 0x0C
SKILL_LIST, SKILL_IN_USE = 0x100, 0x18
FULL_STATS = 0xE8
STATE_FLAGS = 0xB48  # state words 192-223: Death Mark is bit 20
LIFE, MANA = 6, 8  # itemstatcost
ALIGNMENT, TIER = 172, TIER_STAT


@dataclass
class Tracked:
    unit: int
    cls: int
    address: int
    path: int
    stats: int
    owner: int = NO_OWNER
    flags: int = 0
    ally: bool = False
    tier: int = 0


class MemorySampler:
    """The fields a stand needs, read from the game's memory: the units are found by a walk of the unit table every
    DISCOVER_SECONDS (the repo's readers); each `sample` is then one batched read of them (`spans`: (address, size)
    list -> bytes or None each, process_vm_readv). The skill-in-use pointer's skill id is read once a pointer."""

    def __init__(
        self,
        read: Callable[[int, int], bytes],
        spans: Callable[[list[tuple[int, int]]], list],
        table: int,
        walk: Callable[..., Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.read, self.spans, self.table, self.clock = read, spans, table, clock
        self.walk = walk or self.repo_walk
        self.player: Tracked | None = None
        self.area = 0
        self.skills_at = 0  # the player's skill list
        self.units: dict[int, Tracked] = {}
        self.skill_ids: dict[int, int | None] = {}  # skill-in-use record pointer -> skill id
        self.found_at = -math.inf
        self.where: tuple[float, float] = (0.0, 0.0)

    def repo_walk(self) -> tuple[Any, list[dict]]:
        """(the character as decode.player_among has it, the monster units walked)."""
        from inventory_tracking.game.decode import monster_table, player_among
        from inventory_tracking.game.units import walked

        players = walked(self.read, self.table, 0, records=True)['units']
        player = player_among(self.read, players)
        unit = next((u for u in players if player is not None and u['unit_id'] == player.unit_id), None)
        return (player, unit), monster_table(self.read, self.table)['units']

    def stats(self, at: int) -> dict[int, int]:
        pointer, count = struct.unpack('<QQ', self.read(at + FULL_STATS, 16))
        if not pointer or count > 1024:
            return {}
        raw = self.read(pointer, count * 8)
        return {stat: value for layer, stat, value in struct.iter_unpack('<HHi', raw) if layer == 0}

    def discover(self) -> None:
        (player, unit), monsters = self.walk()
        if player is None or unit is None:
            self.player = None
            return
        self.area = player.area
        self.where = (player.x, player.y)
        self.player = Tracked(player.unit_id, 0, unit['address'], unit['path_pointer'], unit['stats_pointer'])
        record = unit.get('record') or self.read(unit['address'], 0x160)
        self.skills_at = struct.unpack_from('<Q', record, SKILL_LIST)[0]
        kept = {}
        for m in monsters:
            if m['mode'] in MONSTER_DEAD or not m['path_pointer'] or not m['data_pointer']:
                continue
            known = self.units.get(m['unit_id'])
            if known is None or known.address != m['address']:
                try:
                    data = self.read(m['data_pointer'], 0x30)
                    stats = self.stats(m['stats_pointer']) if m['stats_pointer'] else {}
                except OSError, ValueError, struct.error:
                    continue
                known = Tracked(
                    m['unit_id'], m['txt_id'], m['address'], m['path_pointer'], m['stats_pointer'],
                    owner=struct.unpack_from('<I', data, 0x0C)[0] if len(data) >= 0x10 else NO_OWNER,
                    flags=data[0x1A] if len(data) > 0x1A else 0,
                    ally=bool(stats.get(ALIGNMENT)), tier=int(stats.get(TIER, 0)),
                )  # fmt: skip
            kept[m['unit_id']] = known
        self.units = kept

    def skill_id(self, used: int) -> int | None:
        if not used:
            return None
        if used not in self.skill_ids:
            try:
                row = struct.unpack('<Q', self.read(used, 8))[0]
                self.skill_ids[used] = struct.unpack('<H', self.read(row, 2))[0] if row else None
            except OSError, ValueError, struct.error:
                return None
        return self.skill_ids[used]

    def sample(self) -> Sample | None:
        now = self.clock()
        if now - self.found_at >= DISCOVER_SECONDS:
            self.found_at = now
            try:
                self.discover()
            except OSError, ValueError, struct.error:
                self.player = None
        player = self.player
        if player is None:
            return None
        near = list(self.units.values())
        spans = [
            (player.address + MODE_AT, 4), (player.path, 8), (self.skills_at + SKILL_IN_USE, 8),
            (player.stats + FULL_STATS, 16),
        ]  # fmt: skip
        for unit in near:
            spans += [(unit.address + MODE_AT, 4), (unit.path, 8), (unit.stats + STATE_FLAGS, 4)]
        got = self.spans(spans)
        wall = time.time()
        if got is None or got[0] is None or got[1] is None:
            return None
        mode = struct.unpack('<I', got[0])[0]
        x, y = position(got[1])
        skill = self.skill_id(struct.unpack('<Q', got[2])[0]) if got[2] else None
        life = mana = 0
        if got[3]:
            with_stats = struct.unpack('<QQ', got[3])
            if with_stats[0] and with_stats[1] <= 1024:
                try:
                    raw = self.read(with_stats[0], with_stats[1] * 8)
                    stats = {s: v for layer, s, v in struct.iter_unpack('<HHi', raw) if layer == 0}
                    life, mana = stats.get(LIFE, 0) >> 8, stats.get(MANA, 0) >> 8
                except OSError, ValueError, struct.error:
                    pass
        companions, foes = [], []
        for index, unit in enumerate(near):
            mode_raw, path_raw, state_raw = got[4 + 3 * index : 7 + 3 * index]
            if mode_raw is None or path_raw is None:
                continue
            m_mode = struct.unpack('<I', mode_raw)[0]
            mx, my = position(path_raw)
            if unit.owner == player.unit or unit.ally:
                companions.append((unit.unit, unit.cls, m_mode, mx, my))
            elif not unit.ally and unit.owner == NO_OWNER and distance(x, y, mx, my) <= NEAR:
                marked = None if state_raw is None else bool(struct.unpack('<I', state_raw)[0] >> MARK_BIT & 1)
                foes.append(Foe(unit.unit, unit.cls, m_mode, mx, my, unit.flags, marked, unit.tier))
        return Sample(now, wall, self.area, x, y, mode, skill, life, mana, tuple(companions), tuple(foes))


def position(path: bytes) -> tuple[float, float]:
    """A path record's position (game/decode.py `position`)."""
    x_fraction, x, y_fraction, y = struct.unpack_from('<HHHH', path)
    return x + x_fraction / 65536, y + y_fraction / 65536


def sample_row(sample: Sample) -> str:
    row = {
        't': round(sample.t, 4), 'w': round(sample.wall, 4), 'a': sample.area,
        'p': [round(sample.x, 2), round(sample.y, 2), sample.mode, sample.skill, sample.life, sample.mana],
        'c': [[u, c, m, round(x, 1), round(y, 1)] for u, c, m, x, y in sample.companions],
        'f': [[f.unit, f.cls, f.mode, round(f.x, 1), round(f.y, 1), f.flags, f.marked, f.tier] for f in sample.foes],
    }  # fmt: skip
    return json.dumps(row, separators=(',', ':'))


def row_sample(row: dict) -> Sample:
    x, y, mode, skill, life, mana = row['p']
    return Sample(
        row['t'], row['w'], row['a'], x, y, mode, skill, life, mana,
        tuple(tuple(c) for c in row.get('c', ())),  # pyrefly: ignore[bad-argument-type]
        tuple(Foe(*f) for f in row.get('f', ())),
    )  # fmt: skip


def run_memory(args: argparse.Namespace) -> int:
    """`memory`: sample the game at --rate into --dir/samples.jsonl and the stands into --dir/stands.*."""
    sys.path.insert(0, str(ROOT))
    from inventory_tracking.native.memory import ProcessMemory, vm_call, vm_read_spans

    os.nice(10)
    memory = ProcessMemory(args.pid)
    call = vm_call()

    def spans(found: list[tuple[int, int]]) -> list:
        if call is None:
            return [memory.read(a, s) for a, s in found]
        return vm_read_spans(call, args.pid, found, calls=4) or [None] * len(found)

    sampler = MemorySampler(memory.read, spans, args.table)
    directory = Path(args.dir)
    directory.mkdir(parents=True, exist_ok=True)
    report = Report(directory / 'stands.txt', directory / 'stands.jsonl', None)
    watch = Stopwatch(report.emit, report.emit_pets)
    period = 1.0 / args.rate
    stop_at = time.monotonic() + args.minutes * 60 if args.minutes else math.inf
    count, started, cpu0 = 0, time.monotonic(), time.process_time()
    with (directory / 'samples.jsonl').open('a', encoding='utf-8') as out:
        next_at = time.monotonic()
        while time.monotonic() < stop_at:
            if args.parent and os.getppid() != args.parent:
                break
            try:
                sample = sampler.sample()
            except OSError, ValueError, struct.error:
                sample = None
            if sample is not None:
                out.write(sample_row(sample) + '\n')
                watch.feed(sample)
                count += 1
            next_at = max(next_at + period, time.monotonic())
            time.sleep(max(0.0, next_at - time.monotonic()))
    watch.finish()
    elapsed = time.monotonic() - started
    print(f'{count} samples in {elapsed:.0f} s ({count / max(elapsed, 1e-9):.0f}/s), '
          f'CPU {100 * (time.process_time() - cpu0) / max(elapsed, 1e-9):.1f} %')  # fmt: skip
    return 0


# --- Reporting -------------------------------------------------------------------------------------------------------


class Report:
    """Each stand: joined to probe.log, printed, appended as a line and as JSON."""

    def __init__(self, text: Path | None, rows: Path | None, lines: Lines | None, quiet: bool = False) -> None:
        self.text, self.rows, self.lines, self.quiet = text, rows, lines, quiet
        self.stands: list[Stand] = []
        self.pet_stands: list[PetStand] = []
        for path in (text, rows):
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, stand: Stand) -> None:
        if self.lines is not None:
            self.lines.join(stand)
        self.stands.append(stand)
        line = say(stand)
        if not self.quiet:
            print(line, flush=True)
        if self.text is not None:
            with self.text.open('a', encoding='utf-8') as out:
                out.write(line + '\n')
        if self.rows is not None:
            with self.rows.open('a', encoding='utf-8') as out:
                out.write(json.dumps(stand_row(stand)) + '\n')

    def emit_pets(self, stand: PetStand) -> None:
        if self.lines is not None:
            self.lines.join_pets(stand)
        self.pet_stands.append(stand)
        line = say_pets(stand)
        if not self.quiet:
            print(line, flush=True)
        if self.text is not None:
            with self.text.open('a', encoding='utf-8') as out:
                out.write(line + '\n')
        if self.rows is not None:
            with self.rows.open('a', encoding='utf-8') as out:
                out.write(json.dumps(pet_row(stand)) + '\n')


def pet_row(stand: PetStand) -> dict:
    row = asdict(stand)
    row.update(kind='pets', waited=stand.waited, local=local(stand.wall))
    return row


def stand_row(stand: Stand) -> dict:
    row = asdict(stand)
    row['stood'] = stand.stood
    row['parts'] = stand.parts()
    row['local'] = local(stand.wall)
    row['kind'] = 'landing'
    return row


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * (len(ordered) - 1) + 0.5))]


def spread(values: list[float]) -> str:
    if not values:
        return 'none'
    return (
        f'n {len(values)}, p50 {percentile(values, 0.5):.2f}, p90 {percentile(values, 0.9):.2f}, max {max(values):.2f}'
    )


def pet_summary(rows: list[dict], worst: int = 5) -> list[str]:
    """The pet stands (the player's measure): their length and the wait to the curse, Herald fights apart, the worst."""
    out = []
    for name, chosen in (
        ('pet stands (pets within 4.5 of the character, a hostile within 30)', rows),
        ('  in Herald fights', [r for r in rows if max(r['tier'], r['herald_line'])]),
        ('  in other fights', [r for r in rows if not max(r['tier'], r['herald_line'])]),
    ):
        out.append(f'{name}: length {spread([r["length"] for r in chosen])}')
        out.append(f'    start -> curse or the end (waited): {spread([r["waited"] for r in chosen])}')
        cursed = [r for r in chosen if r['curse'] is not None]
        out.append(f'    with a curse in it ({len(cursed)}): start -> curse {spread([r["curse"] for r in cursed])}; '
                   f'pets leave after it {spread([r["left_after_curse"] for r in cursed])}')  # fmt: skip
        keys = [r['keys'][0] for r in chosen if r['keys']]
        out.append(f'    a DM key in it: {len(keys)} of {len(chosen)}; first key {spread(keys)}')
        live = [r['marked_live'] for r in chosen if r['marked_live'] > PET_GAP]
        out.append(f'    a marked hostile alive while the pets stood: {len(live)}, for {spread(live)}')
    out.append(f'worst {worst} pet stands (waited):')
    for r in sorted(rows, key=lambda r: -r['waited'])[:worst]:
        curse = '-' if r['curse'] is None else f'{r["curse"]:+.2f} (pets left {r["left_after_curse"]:+.2f} after)'
        out.append(
            f'  {r["local"]} L{r["area"]} {r["length"]:.2f} s with {",".join(r["pets"])} ({r["by"]}); curse {curse}; '
            f'DM keys {r["keys"]}, casts {r["mark_casts"]}; strikes {r["strikes"]}; pets idle {r["idle"]:.2f} s; '
            f'{r["hostiles"]} hostiles, T{max(r["tier"], r["herald_line"])}, marked at start {r["marked_at_start"]}, '
            f'a marked one alive {r["marked_live"]:.2f} s; {r["why_ended"]}'
        )
        out.extend(f'      {reason}' for reason in r['reasons'])
    return out


def summary(rows: list[dict], worst: int = 5) -> str:
    """p50/p90/max of the stands with hostiles near, Herald fights apart, the parts, and the worst cases."""
    pets = [r for r in rows if r.get('kind') == 'pets']
    rows = [r for r in rows if r.get('kind', 'landing') == 'landing']
    near = [r for r in rows if r['screen_near'] > 0 and r['stood'] is not None]
    out = pet_summary(pets, worst) if pets else []
    for name, chosen in (
        ('all stands with a hostile within 30', near),
        ('Herald fights (a tier read or said)', [r for r in near if max(r['tier'], r['herald_line'])]),
        ('other fights', [r for r in near if not max(r['tier'], r['herald_line'])]),
        ('  of the Herald fights, the Herald itself within 30', [r for r in near if r['herald']]),
    ):
        out.append(f'{name}: stood without a Death Mark: {spread([r["stood"] for r in chosen])}')
        marked = [r for r in chosen if r['mark_cast'] is not None]
        out.append(f'  with a mark cast ({len(marked)}): landing -> DM cast {spread([r["mark_cast"] for r in marked])}')
        on = [r for r in chosen if r['mark_on'] is not None]
        out.append(f'  landing -> state 212 ({len(on)}): {spread([r["mark_on"] for r in on])}')
        for part in ('notice', 'deciding', 'flight', 'curse'):
            values = [r['parts'][part] for r in chosen if r['parts'][part] is not None]
            out.append(f'  {part}: {spread(values)}')
        none = [r for r in chosen if r['mark_cast'] is None]
        out.append(f'  no mark before the next hop / the end: {len(none)} of {len(chosen)}')
    out.append(f'worst {worst} (stood without a Death Mark, hostiles near):')
    for r in sorted(near, key=lambda r: -r['stood'])[:worst]:
        parts = ', '.join(f'{k} {seconds(v)}' for k, v in r['parts'].items())
        out.append(
            f'  {r["local"]} L{r["area"]} stood {r["stood"]:.2f} s; stand {seconds(r["stand"])}, casts '
            f'{[(round(t, 2), skill_name(s)) for t, s in r["casts"][:6]]}, DM {seconds(r["mark_cast"])}, 212 '
            f'{seconds(r["mark_on"])}, next hop {seconds(r["next_hop"])}; near {r["strike_near"]}/{r["screen_near"]} '
            f'T{max(r["tier"], r["herald_line"])} marked already {r["marked_near"]}; {parts}; judge {r["judge_ms"]}'
        )
        out.extend(f'      {reason}' for reason in r['reasons'])
    return '\n'.join(out)


# --- Commands --------------------------------------------------------------------------------------------------------


def parse_time(text: str) -> float:
    return datetime.strptime(text, '%Y-%m-%d %H:%M').timestamp()


def load_lines(paths: Iterable[Path]) -> Lines:
    lines = Lines()
    for path in paths:
        with path.open(encoding='utf-8', errors='replace') as handle:
            for line in handle:
                lines.add(line)
    return lines


def run_takes(args: argparse.Namespace) -> int:
    since = parse_time(args.since)
    until = parse_time(args.until) if args.until else time.time()
    lines = load_lines(session_logs(since - 6 * 3600))
    report = Report(Path(args.out) if args.out else None, Path(args.json) if args.json else None, lines, args.quiet)
    for take in takes_between(since, until):
        watch = Stopwatch(report.emit, report.emit_pets)
        for sample in take_samples(take):
            if since <= sample.wall <= until:
                watch.feed(sample)
        watch.finish()
    print(summary([stand_row(s) for s in report.stands] + [pet_row(s) for s in report.pet_stands]))
    return 0


def run_samples(args: argparse.Namespace) -> int:
    rows: list[Sample] = []
    for path in args.files:
        with Path(path).open(encoding='utf-8') as handle:
            rows += [row_sample(json.loads(line)) for line in handle if line.strip()]
    rows.sort(key=lambda s: s.t)
    lines = load_lines(session_logs(rows[0].wall - 6 * 3600)) if rows else Lines()
    report = Report(Path(args.out) if args.out else None, Path(args.json) if args.json else None, lines, args.quiet)
    watch = Stopwatch(report.emit, report.emit_pets)
    for sample in rows:
        watch.feed(sample)
    watch.finish()
    print(summary([stand_row(s) for s in report.stands] + [pet_row(s) for s in report.pet_stands]))
    return 0


TAKE_LOOK = 1.0  # seconds between looks for a new take


def run_live(args: argparse.Namespace) -> int:
    """`live`: follow the newest take and probe.log; a stand's line once its next landing (or window) closes it, and
    once the probe.log lines of its time are in."""
    with suppress(OSError):
        os.nice(19)
    stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    text = Path(args.out) if args.out else OUT / f'{stamp}-stands.txt'
    rows = Path(args.json) if args.json else text.with_suffix('.jsonl')
    lines = Lines()
    logs = session_logs()
    log_tail = Tail(logs[0]) if logs else None
    if log_tail is not None:  # the lines from before are not needed: start at the end
        log_tail.at = log_tail.path.stat().st_size
    report = Report(text, rows, lines)
    pending: list[Any] = []

    def emit(stand: Any) -> None:
        pending.append(stand)

    take: LiveTake | None = None
    watch = Stopwatch(emit, emit)
    stop_at = time.monotonic() + args.minutes * 60
    started, cpu0, frames = time.monotonic(), time.process_time(), 0
    said_at = started
    print(f'stopwatch: stands to {text}', flush=True)
    looked_at = -math.inf
    while time.monotonic() < stop_at:
        newest = take.take if take is not None else None
        if time.monotonic() - looked_at >= TAKE_LOOK:
            looked_at, newest = time.monotonic(), newest_take()
        if newest is not None and (take is None or newest != take.take):
            if take is not None:
                for sample in take.poll():
                    watch.feed(sample)
            watch.finish()
            watch = Stopwatch(emit, emit)
            try:
                take = LiveTake(newest)
                take.frames.at = max(0, (newest / 'frames.jsonl').stat().st_size - 200_000)  # from about now
                take.records.at = max(0, (newest / 'records.jsonl').stat().st_size - 400_000)
            except OSError, ValueError:
                take = None
        if take is not None:
            for sample in take.poll():
                watch.feed(sample)
                frames += 1
        if log_tail is not None:
            for raw in log_tail.lines():
                lines.add(raw.decode('utf-8', errors='replace'))
        latest = lines.walls[-1] if lines.walls else 0.0
        while pending and (latest >= pending[0].wall + span(pending[0]) + 0.2 or time.time() > pending[0].wall + 20):
            given = pending.pop(0)
            (report.emit if isinstance(given, Stand) else report.emit_pets)(given)
        if time.monotonic() - said_at >= 300:
            said_at = time.monotonic()
            elapsed = said_at - started
            print(f'stopwatch: {frames} frames in {elapsed:.0f} s, CPU {cpu_share(cpu0, elapsed):.1f} %', flush=True)
        time.sleep(args.poll)
    watch.finish()
    for given in pending:
        (report.emit if isinstance(given, Stand) else report.emit_pets)(given)
    elapsed = time.monotonic() - started
    print(f'stopwatch: {frames} frames in {elapsed:.0f} s, CPU {cpu_share(cpu0, elapsed):.1f} %; '
          f'max RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024} MB', flush=True)  # fmt: skip
    print(summary([stand_row(s) for s in report.stands] + [pet_row(s) for s in report.pet_stands]), flush=True)
    return 0


def span(stand: Any) -> float:
    return stand.end if isinstance(stand, Stand) else stand.length


def cpu_share(cpu0: float, elapsed: float) -> float:
    return 100 * (time.process_time() - cpu0) / max(elapsed, 1e-9)


def run_summary(args: argparse.Namespace) -> int:
    rows = []
    for path in args.files:
        with Path(path).open(encoding='utf-8') as handle:
            rows += [json.loads(line) for line in handle if line.strip()]
    if args.tier is not None:
        rows = [r for r in rows if max(r['tier'], r['herald_line']) == args.tier]
    print(summary(rows, args.worst))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    live = commands.add_parser('live')
    live.add_argument('--minutes', type=float, default=25.0)
    live.add_argument('--poll', type=float, default=0.25)
    live.add_argument('--out')
    live.add_argument('--json')
    takes = commands.add_parser('takes')
    takes.add_argument('--since', required=True)
    takes.add_argument('--until')
    takes.add_argument('--out')
    takes.add_argument('--json')
    takes.add_argument('--quiet', action='store_true')
    samples = commands.add_parser('samples')
    samples.add_argument('files', nargs='+')
    samples.add_argument('--out')
    samples.add_argument('--json')
    samples.add_argument('--quiet', action='store_true')
    memory = commands.add_parser('memory')
    memory.add_argument('--pid', type=int, required=True)
    memory.add_argument('--base', type=lambda s: int(s, 0), required=True)
    memory.add_argument('--table', type=lambda s: int(s, 0), required=True)
    memory.add_argument('--dir', required=True)
    memory.add_argument('--rate', type=float, default=RATE)
    memory.add_argument('--minutes', type=float, default=0.0)
    memory.add_argument('--parent', type=int, default=0)  # stop when this process is no longer the parent
    report = commands.add_parser('summary')
    report.add_argument('files', nargs='+')
    report.add_argument('--worst', type=int, default=5)
    report.add_argument('--tier', type=int, help='only the fights of this Herald tier (read or said)')
    args = parser.parse_args(argv)
    return {'live': run_live, 'takes': run_takes, 'samples': run_samples, 'memory': run_memory,
            'summary': run_summary}[args.command](args)  # fmt: skip


if __name__ == '__main__':
    raise SystemExit(main())
