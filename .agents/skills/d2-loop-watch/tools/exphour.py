"""Experience an hour of the KP_6 loop (TZ leveling, Baal): its measure (the player, 2026-10-24 20:28: "our goal is to
have best exp/hour we can"; "this involves: killing many mobs as fast as possible; do not die").

Run with the repo's Python: `uv run --offline python .agents/skills/d2-loop-watch/tools/exphour.py`.

- **Play** is elites.py's play time of the kind (`--kind`, default `tz`): the loop on with that kind, town, lobby and
  travel counted, without the stretches it was off, the gaps between sessions and the stalls the player sorted out.
- **Wall** is the clock from the first piece of play in the window to the last; the stretches out of play over
  GAP_SECONDS are listed with what the log said in them (a stop, the loop's request, a restart).
- **Experience** is the per-level lines (`Macro: experience: <level>: +X in Ts`, logwords.py EXPERIENCE_LEVEL; the
  game's line only closes the last level) that end in play. The loop says them for the TZ kinds only (macros/loop.py
  TZ_KINDS); a game without them (Baal, Andariel) gets its experience from the **combat takes** (`runs/combat/<UTC>-
  <area>/manifest.json`, takes/record.py: one take a level stay, the character's stats as it opens): a take's gain is
  the experience (stat 13) at the next take's opening less its own, so a level's kills (the Throne's waves, Baal) land
  on the take they were made in; a town take's zero gain is no stay. The takes' `kill` events (events.jsonl.gz: every
  monster seen dying, once a unit and a take) are the **kills**; elites.py's elite kills (terror-probe.jsonl) split
  into **elites** and **bosses** (terror/bosses.py BOSSES). Each stay also gets the play time since the previous stay
  of the same game ended (town, waypoint, Town Portal, loading): its **travel**. A stay is a **shard** act's when its
  act is an `ActN-Manual` part of the game's last plan line (logwords.py TZ_ZONE: an act a shard over the limit
  terrorized), **natural** when it is in the game's own zone.
- **Time sinks**: elites.py's activities (engaging, approach, explore, pickup, chests, travel, town, lobby, trip) as
  shares and seconds an hour of play.
- `--against SINCE UNTIL`: the other window's exp an hour of play and a 90% bootstrap interval of the difference
  (games resampled, as elites.py and andy.py do): better / worse / no evidence; the same for kills an hour, each
  side's games counted.
- **Baal games** (`--kind baal`, or `any` over them): each game's play seconds by phase, from its legs (elites.py
  pieces): lobby (next game, Save and Exit), town (the Fortress, the town visit, the Gheed's swap), shard (`a
  Northern shard for act 5`), keep (the waypoint and the Keep's Levels 2 and 3), throne (the waves, a fight back
  before Baal), portal (the Throne's way on while the portal is shut), baal (his fight), loot (every pickup leg, the
  Throne's and the Chamber's), trip (a Town Portal trip for room, its town legs included); a game is terrorized when
  a `terrorize: ... used for act 5` line fell in it (logwords.py TERRORIZED). The medians are over whole games (from
  `next game` to Save and Exit, Baal fought).
- `--weak-out FILE`: the weak levels (`weak`) written as JSON, the list macros/tzroutine.py SHORT_LEVELS reads
  (`inventory_tracking/macros/data/short_levels.json`; the player, 2026-10-25 ~10:15: "Shorten them: clear only the
  elites, bosses and big packs on those levels, then move on"): under `--weak-below` exp a second with the travel
  (default WEAK_BELOW), under the window's average on the level itself (a level slow only by its travel is not
  shortened), WEAK_SECONDS on it and WEAK_STAYS stays at least.
- **SHORT_LEVELS replay** (`shortened`): on the weak areas (the data file's, or `--weak-areas`), the seconds of each
  stay's agenda targets agenda.py SHORT drops (logwords.py TARGET_GOAL: an unexplored room, a group under SHORT_PACK;
  each target timed to the next, the next leg or the stay's end), and the exp an hour that time would add at the
  window's average less what the level made in it (its own rate on the level). A group's label does not say whether a
  leader stands in it (SHORT keeps those): an upper bound. With the switch on the same window's numbers measure it.

    uv run --offline python .agents/skills/d2-loop-watch/tools/exphour.py [--since 'YYYY-MM-DD HH:MM'] [--until ...]
        [--kind tz|baal|any|...] [--against SINCE UNTIL] [--levels 12] [--json] [--runs DIR] [--combat DIR]
        [--weak-out FILE [--weak-below 1600]]

First built for rca/2026-10-25/exp-hour-findings.md (7.51 M an hour of play, 6.82 M a wall hour, 10-24 10:36 to
10-25 05:38).
"""

import argparse
import bisect
import gzip
import json
import os
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE), str(ROOT)]

import elites  # ruff: ignore[module-import-not-at-top-of-file] - the skill's own tool, beside this one
import logwords  # ruff: ignore[module-import-not-at-top-of-file] - beside this tool
from logwords import (  # ruff: ignore[module-import-not-at-top-of-file] - beside this tool
    EXPERIENCE_LEVEL,
    LEG,
    REQUEST_LOOP,
    RESUMED,
    SAFE_POINT,
    STAMP_LEN,
    STOPPED,
    TARGET_GOAL,
    TERRORIZED,
    TZ_ZONE,
    amount,
    stamp,
)

from inventory_tracking.levels.presets import DISPLAY_NAMES, numbered_name  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.macros import loop as loop_module  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.macros.agenda import EXPLORE, SHORT_PACK  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.macros.tzroutine import weak_areas  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.terror.bosses import BOSSES  # ruff: ignore[module-import-not-at-top-of-file]


RUNS = elites.RUNS
GAP_SECONDS = 60.0  # a stretch out of play this long between two pieces is listed (wall time lost)
STAY_SLACK = 5.0  # s: a level line this soon after a piece of play ends is still that piece's (the leg after it)
MINIMUM = 8  # games a side for a comparison
WHOLE_MINIMUM = 5  # whole Baal games a side for theirs (a few games a window: its interval says how wide)
WEAK_BELOW = 1600.0  # exp a second with the travel: the player's "under about 1,600" (2026-10-25)
WEAK_SECONDS = 120  # seconds on the level at least, for a rate worth a ruling
WEAK_STAYS = 3
DRAWS = 2000
# levels.txt Ids by act: act N's first level (towns 1, 40, 75, 103, 109)
ACT_STARTS = (1, 40, 75, 103, 109)
# The level lines' names (presets.py `numbered_name`) back to their areas
AREAS = {numbered_name(area): area for area in sorted(DISPLAY_NAMES, reverse=True)} | {
    numbered_name(area): area for area in range(66, 73)
}
TOWNS = frozenset(ACT_STARTS)  # the act towns' areas: a take there gains nothing of its own
# The combat takes (takes/record.py): `<UTC>-<area>` directories beside the sessions'
TAKE_STAMP = '%Y%m%dT%H%M%S'
TAKE_BEFORE = timedelta(minutes=15)  # a take opened this long before the window may end in it
TAKE_AFTER = timedelta(minutes=30)  # takes read past the window: the next take's opening closes the last one's gain
CARRY = timedelta(minutes=30)  # a game carried over restarts this long after its shard line is still its
TAKE_GAP = 600.0  # s: a take's next one opened this much later (serve down, another character) says no gain
EXPERIENCE_KEY, LEVEL_KEY = '13', '12'  # itemstatcost.txt (macros/experience.py EXPERIENCE_STAT, LEVEL_STAT)
KILL_EVENT = b'"event": "kill"'  # a take's kill event as json.dumps writes it (takes/record.py `'kill'`)
READERS = 4  # threads decompressing the takes' events (zlib lets go of the GIL)
# Baal's phases (the module text), by leg; FIGHT_BACK is the throne's before Baal's fight, his after
BAAL_PHASES = ('lobby', 'town', 'shard', 'keep', 'throne', 'portal', 'baal', 'loot', 'trip', 'other')
BAAL_PHASE = {
    loop_module.NEXT_GAME: 'lobby',
    loop_module.LEAVE: 'lobby',
    loop_module.TOWN: 'town',
    loop_module.TO_THE_FORTRESS: 'town',
    loop_module.TO_HARROGATH: 'town',
    loop_module.SWAP_OUT: 'town',
    loop_module.GHEED_STASH: 'town',
    loop_module.SWAP_BACK: 'town',
    loop_module.GHEED_CHOOSE: 'town',
    loop_module.GHEED_PICK: 'town',
    loop_module.BAAL_SHARD: 'shard',
    loop_module.TO_THE_KEEP: 'keep',
    loop_module.DOWN_THE_KEEP: 'keep',
    loop_module.FIGHT_THRONE: 'throne',
    loop_module.TO_THE_CHAMBER: 'portal',
    loop_module.FIGHT_BAAL: 'baal',
    loop_module.PICK_UP: 'loot',
    loop_module.PICK_BACK: 'loot',
    loop_module.TRIP: 'trip',
    loop_module.THROUGH_PORTAL: 'trip',
    loop_module.MERC_TRIP: 'trip',
}
MANUAL = re.compile(r'Act(\d)-Manual')
OWN_PART = re.compile(r'Act(\d)-')
GROUP = re.compile(r'a group of (\d+)$')


def act_of(area: int | None) -> int | None:
    return None if area is None else bisect.bisect_right(ACT_STARTS, area) or None


@dataclass
class Stay:
    """One level stay: the experience line's end, its level and the seconds and exp it says."""

    end: datetime
    name: str
    gain: int
    seconds: int
    game: str = ''  # elites.py's game key (session/number); '' out of play
    travel: float = 0.0  # play seconds since the game's previous stay ended
    kind: str = '?'  # 'shard', 'natural' or '?' (no plan line); a take's: 'shard' in an act terrorized, else 'plain'
    take: bool = False  # from the combat takes, not a level line

    @property
    def area(self) -> int | None:
        return AREAS.get(self.name)

    @property
    def act(self) -> int | None:
        return act_of(self.area)


@dataclass
class Take:
    """One combat take (takes/record.py: one stay in a level): its clock, area and the character's experience as it
    opened (None unread)."""

    start: datetime
    end: datetime
    area: int
    character: str
    experience: int | None
    directory: Path

    @property
    def seconds(self) -> float:
        return (self.end - self.start).total_seconds()

    @property
    def middle(self) -> datetime:
        """Where the take is placed in play (a game, or out of play)."""
        return self.start + (self.end - self.start) / 2


@dataclass
class Zone:
    at: datetime
    manual: frozenset[int]  # the acts a shard terrorized
    own: frozenset[int]  # the acts of the game's own zone
    parts: tuple[str, ...]  # the own zone's parts ('Act2-Sewers')
    areas: frozenset[int]  # every area of the plan's trips


@dataclass
class Window:
    since: datetime
    until: datetime
    plays: elites.Window
    stays: list[Stay] = field(default_factory=list)
    outside: list[Stay] = field(default_factory=list)  # level lines that end out of play
    zones: list[Zone] = field(default_factory=list)
    # own zone part -> its areas, from a plan of it alone
    known: dict[str, frozenset[int]] = field(default_factory=dict)
    said: list[tuple[datetime, str]] = field(default_factory=list)  # stops, requests, restarts
    targets: list[tuple[datetime, str, str]] = field(default_factory=list)  # the agenda's (at, label, kind)
    legs: list[datetime] = field(default_factory=list)  # the loop's leg lines: a target's time ends at the next
    terrorized: set[tuple[str, int]] = field(default_factory=set)  # (game, act) a shard terrorized
    kills: Counter[str] = field(default_factory=Counter)  # game -> its takes' monster kills
    takes: int = 0  # takes ending in play
    takes_out: list[tuple[Take, int | None]] = field(default_factory=list)  # ending out of play: not counted


def parse_zone(at: datetime, parts: str, trips: str) -> Zone:
    names = [part.strip() for part in parts.split('+')]
    manual = frozenset(int(m.group(1)) for name in names if (m := MANUAL.fullmatch(name)))
    own = frozenset(int(m.group(1)) for name in names if not MANUAL.fullmatch(name) and (m := OWN_PART.match(name)))
    parts_own = tuple(name for name in names if not MANUAL.fullmatch(name))
    areas = frozenset(int(x) for x in re.findall(r'\d+', trips))
    return Zone(at, manual, own, parts_own, areas)


def local(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone().replace(tzinfo=None)


def takes_in(since: datetime, until: datetime, combat: Path) -> list[Take]:
    """The takes opened from TAKE_BEFORE before `since` to TAKE_AFTER after `until`, by their opening."""
    if not combat.is_dir():
        return []
    low = (since - TAKE_BEFORE).astimezone(UTC).strftime(TAKE_STAMP)
    high = (until + TAKE_AFTER).astimezone(UTC).strftime(TAKE_STAMP)
    found = []
    with os.scandir(combat) as entries:
        for entry in entries:
            if not low <= entry.name[: len(low)] <= high or not entry.is_dir():
                continue
            try:
                manifest = json.loads((Path(entry.path) / 'manifest.json').read_text())
                start = local(manifest['started_at'])
            except OSError, ValueError, KeyError, TypeError:
                continue
            finished = manifest.get('finished_at')
            end = local(finished) if finished else start + timedelta(seconds=float(manifest.get('seconds') or 0))
            stats = manifest.get('character_stats') or {}
            raw = stats.get(EXPERIENCE_KEY)
            experience = int(raw) & 0xFFFFFFFF if raw is not None and stats.get(LEVEL_KEY) else None  # unsigned
            found.append(Take(start, end, int(manifest.get('area') or 0), str(manifest.get('character') or ''),
                              experience, Path(entry.path)))  # fmt: skip
    return sorted(found, key=lambda take: take.start)


def gains(takes: list[Take]) -> list[int | None]:
    """Each take's experience gain: the next take's opening reading less its own (the same character, within
    TAKE_GAP); None unknown."""
    out: list[int | None] = []
    for i, a in enumerate(takes):
        b = takes[i + 1] if i + 1 < len(takes) else None
        if (
            b is None
            or a.experience is None
            or b.experience is None
            or a.character != b.character
            or (b.start - a.end).total_seconds() > TAKE_GAP
        ):
            out.append(None)
        else:
            out.append(b.experience - a.experience)
    return out


def kills_of(take: Take) -> int:
    """The take's monster kills (its `kill` events; a take still written or cut short: none)."""
    for name, opener in (('events.jsonl.gz', gzip.open), ('events.jsonl', open)):
        path = take.directory / name
        if path.exists():
            try:
                with opener(path, 'rb') as stream:
                    return stream.read().count(KILL_EVENT)
            except OSError, EOFError, gzip.BadGzipFile:
                return 0
    return 0


def read(since: datetime, until: datetime, kind: str = 'tz', runs: Path = RUNS, combat: Path | None = None) -> Window:
    """The window's play (elites.py), its stays (the level lines, else the takes) and kills. `combat`: the takes'
    directory (default: `runs`' sibling `combat`)."""
    window = Window(since, until, elites.read(since, until, kind, runs))
    combat = runs.parent / 'combat' if combat is None else combat
    found: list[Stay] = []
    used: list[tuple[datetime, str, int]] = []  # the shard lines: (at, game number, act)
    directories = logwords.sessions(since, until, runs)
    for directory in directories:
        game, number = f'{directory.name}/0', '0'
        for line in (directory / 'probe.log').read_text(errors='replace').splitlines():
            if 'Macro' not in line:
                continue
            at = stamp(line)
            if at is None or at > until:
                continue
            text = line[STAMP_LEN:]
            if (m := LEG.search(text)) is not None:
                number = m.group(1)
                game = f'{directory.name}/{number}'  # the game a shard line falls in, before the window too
            elif (m := TERRORIZED.search(text)) is not None:
                window.terrorized.add((game, int(m.group(2))))
                used.append((at, number, int(m.group(2))))
            if at < since:
                continue
            if (m := EXPERIENCE_LEVEL.search(text)) is not None:
                found.append(Stay(at, m.group(1), amount(m.group(2)), int(m.group(3))))
            elif (m := TARGET_GOAL.search(text)) is not None:
                window.targets.append((at, m.group(1), m.group(2)))
            elif LEG.search(text) is not None:
                window.legs.append(at)
            elif (m := TZ_ZONE.search(text)) is not None:
                zone = parse_zone(at, m.group(1), m.group(2))
                window.zones.append(zone)
                if not zone.manual and len(zone.parts) == 1:
                    window.known[zone.parts[0]] = zone.areas
            elif (m := STOPPED.search(text)) is not None:
                window.said.append((at, f'loop stopped: {m.group(1)}'))
            elif REQUEST_LOOP in text:
                window.said.append((at, 'the loop switched by a request (KP_6 or a tool)'))
            elif (m := RESUMED.search(text)) is not None:
                window.said.append((at, f'restart (loop {m.group(1)})'))
            elif (m := SAFE_POINT.search(text)) is not None:
                window.said.append((at, f'safe point for a restart: {m.group(1)}'))
    # a game a restart carried on (`CARRIED`) is a later session's of the same number: terrorized there too, in the
    # sessions begun within CARRY of its shard line
    for directory in directories:
        begun = datetime.strptime(directory.name[:16], '%Y%m%dT%H%M%SZ').replace(tzinfo=UTC).astimezone()
        begun = begun.replace(tzinfo=None)
        for at, number, act in used:
            if at < begun <= at + CARRY:
                window.terrorized.add((f'{directory.name}/{number}', act))
    window.zones.sort(key=lambda z: z.at)
    window.said.sort()
    window.targets.sort()
    window.legs.sort()
    pieces = sorted(window.plays.pieces, key=lambda p: p.start)
    starts = [p.start for p in pieces]

    def game_at(at: datetime) -> str | None:
        """The game of the piece of play `at` falls in (or ended STAY_SLACK before), None out of play."""
        i = bisect.bisect_right(starts, at) - 1
        return None if i < 0 or (at - pieces[i].end).total_seconds() > STAY_SLACK else pieces[i].game

    told = {game for stay in found if (game := game_at(stay.end)) is not None}  # games with level lines
    takes = takes_in(since, until, combat)
    placed: list[tuple[Take, str]] = []
    for take, gain in zip(takes, gains(takes), strict=True):
        if not since <= take.end <= until:
            continue
        game = game_at(take.middle)  # its end comes a moment after the next leg (Baal's take: Save and Exit's)
        if game is None:
            window.takes_out.append((take, gain))
            continue
        placed.append((take, game))
        if gain is None or game in told or (take.area in TOWNS and not gain):
            continue
        found.append(Stay(take.end, numbered_name(take.area), gain, round(take.seconds), take=True))
    window.takes = len(placed)
    with ThreadPoolExecutor(READERS) as pool:
        for (_, game), kills in zip(placed, pool.map(kills_of, [take for take, _ in placed]), strict=True):
            window.kills[game] += kills
    found.sort(key=lambda s: s.end)
    zone_at = [z.at for z in window.zones]
    last_end: dict[str, datetime] = {}
    for stay in found:
        game = game_at(stay.end - timedelta(seconds=stay.seconds / 2) if stay.take else stay.end)
        if game is None:
            window.outside.append(stay)
            continue
        stay.game = game
        begun = stay.end - timedelta(seconds=stay.seconds)
        before = last_end.get(stay.game)
        if before is not None and begun > before:
            stay.travel = play_between(pieces, starts, before, begun)
        last_end[stay.game] = stay.end
        z = bisect.bisect_right(zone_at, begun) - 1
        stay.kind = classify(window.zones[z], stay, window.known) if z >= 0 and not stay.take else '?'
        if stay.kind == '?' and stay.take and stay.act is not None:
            stay.kind = 'shard' if (stay.game, stay.act) in window.terrorized else 'plain'
        window.stays.append(stay)
    return window


def classify(zone: Zone, stay: Stay, known: dict[str, frozenset[int]]) -> str:
    """'natural' in the game's own zone (its areas known from a plan of it alone, else its act), 'shard' in an act a
    shard terrorized, '?' otherwise."""
    if stay.act is None:
        return '?'
    if any(stay.area in known.get(part, frozenset()) for part in zone.parts):
        return 'natural'
    if stay.act in zone.manual:
        return 'shard'
    return 'natural' if stay.act in zone.own else '?'


def play_between(pieces: list[elites.Piece], starts: list[datetime], a: datetime, b: datetime) -> float:
    total = 0.0
    i = max(0, bisect.bisect_right(starts, a) - 1)
    while i < len(pieces) and pieces[i].start < b:
        low, high = max(pieces[i].start, a), min(pieces[i].end, b)
        if high > low:
            total += (high - low).total_seconds()
        i += 1
    return total


def gaps(window: Window) -> list[dict]:
    """The stretches out of play over GAP_SECONDS between the first and the last piece, with what the log said."""
    pieces = sorted(window.plays.pieces, key=lambda p: p.start)
    found = []
    for a, b in pairwise(pieces):
        seconds = (b.start - a.end).total_seconds()
        if seconds > GAP_SECONDS:
            why = [text for at, text in window.said if a.end <= at <= b.start]
            found.append({'from': a.end, 'to': b.start, 'seconds': seconds, 'said': why[:3]})
    return found


def baal_phases(pieces: list[elites.Piece]) -> dict[str, float]:
    """One game's play seconds by Baal phase (BAAL_PHASE by its legs; `pieces` in order): a fight back is the
    throne's before Baal's fight, his after; a trip's town legs are the trip's until it is back through the portal."""
    out: dict[str, float] = dict.fromkeys(BAAL_PHASES, 0.0)
    after_baal, tripping = False, False
    for piece in pieces:
        leg = piece.leg
        after_baal = after_baal or leg == loop_module.FIGHT_BAAL
        if leg == loop_module.TRIP:
            tripping = True
        elif leg not in (loop_module.TO_THE_FORTRESS, loop_module.TOWN, loop_module.TO_HARROGATH,
                         loop_module.THROUGH_PORTAL):  # fmt: skip
            tripping = False
        if leg == loop_module.FIGHT_BACK:
            phase = 'baal' if after_baal else 'throne'
        elif tripping:
            phase = 'trip'
        else:
            phase = BAAL_PHASE.get(leg, 'other')
        out[phase] += piece.seconds
    return out


def games_of(window: Window) -> list[dict]:
    """Per game (elites.py's key), in order: its play seconds, the experience of its stays, its kills (the takes'),
    elite and boss kills; a Baal game's (one of its legs Baal's) phases, whether a shard terrorized it, and whether
    it is whole (from `next game` to Save and Exit, Baal fought)."""
    pieces: dict[str, list[elites.Piece]] = defaultdict(list)
    for piece in sorted(window.plays.pieces, key=lambda p: p.start):
        pieces[piece.game].append(piece)
    gained: dict[str, int] = defaultdict(int)
    for stay in window.stays:
        gained[stay.game] += stay.gain
    elite: Counter[str] = Counter()
    boss: Counter[str] = Counter()
    for kill in window.plays.kills:
        game = next((p.game for p in window.plays.pieces if p.start <= kill.at <= p.end), None)
        if game is not None:
            (boss if kill.txt in BOSSES else elite)[game] += 1
    terrorized = {game for game, _ in window.terrorized}
    out = []
    for game, mine in pieces.items():
        seconds = sum(p.seconds for p in mine)
        if seconds <= 0:
            continue
        legs = {p.leg for p in mine}
        row: dict[str, Any] = {'game': game, 'start': mine[0].start, 'seconds': seconds, 'exp': gained[game],
               'kills': window.kills[game], 'elites': elite[game], 'bosses': boss[game]}  # fmt: skip
        if legs & elites.BAAL_LEGS:
            row['baal'] = baal_phases(mine)
            row['terrorized'] = game in terrorized
            row['whole'] = (
                mine[0].leg == loop_module.NEXT_GAME
                and {loop_module.FIGHT_BAAL, loop_module.LEAVE} <= legs
                and window.since < mine[0].start
                and mine[-1].end < window.until
            )
        out.append(row)
    return out


def rate(games: list[dict], key: str = 'exp') -> float:
    seconds = sum(g['seconds'] for g in games)
    return 3600 * sum(g[key] for g in games) / seconds if seconds else 0.0


def shift(before: list[dict], after: list[dict], key: str = 'exp', minimum: int = MINIMUM) -> str:
    """`key` (exp, kills) an hour of play, before -> after, with a 90% bootstrap interval of the difference (games
    resampled)."""
    if len(before) < minimum or len(after) < minimum:
        return f'too few games ({len(before)} / {len(after)}) for a comparison'
    rng = random.Random(7)
    draws = sorted(
        rate(rng.choices(after, k=len(after)), key) - rate(rng.choices(before, k=len(before)), key)
        for _ in range(DRAWS)
    )
    low, high = draws[int(0.05 * DRAWS)], draws[int(0.95 * DRAWS)]
    verdict = 'better' if low > 0 else 'worse' if high < 0 else 'no evidence'
    was, now = rate(before, key), rate(after, key)
    if key != 'exp':
        return (
            f'{was:.0f} -> {now:.0f} {key} an hour of play ({now - was:+.0f}, 90% [{low:+.0f}, {high:+.0f}]: {verdict})'
        )
    return (
        f'{was / 1e6:.2f} M -> {now / 1e6:.2f} M exp an hour of play ({(now - was) / 1e6:+.2f} M, '
        f'90% [{low / 1e6:+.2f}, {high / 1e6:+.2f}]: {verdict})'
    )


def whole_baal(games: list[dict]) -> list[dict]:
    return [g for g in games if g.get('whole')]


def baal_summary(games: list[dict]) -> dict:
    """The Baal games' counts and, over the whole ones, each phase's median seconds, the game's median and the
    exp and kills a game."""
    baal = [g for g in games if 'baal' in g]
    whole = [g for g in baal if g['whole']]
    median = {phase: statistics.median(g['baal'][phase] for g in whole) if whole else 0.0 for phase in BAAL_PHASES}
    return {
        'games': len(baal),
        'whole': len(whole),
        'terrorized': sum(1 for g in baal if g['terrorized']),
        'median': median,
        'median_game': statistics.median(g['seconds'] for g in whole) if whole else 0.0,
        'exp_a_game': statistics.mean(g['exp'] for g in whole) if whole else 0.0,
        'kills_a_game': statistics.mean(g['kills'] for g in whole) if whole else 0.0,
        # the whole games by the shard: the window's own split (a window's games need not all be one or the other)
        'split': {
            name: {'games': len(side), 'per_play_hour': rate(side), 'kills_per_hour': rate(side, 'kills')}
            for name, side in (
                ('terrorized', [g for g in whole if g['terrorized']]),
                ('plain', [g for g in whole if not g['terrorized']]),
            )
        },
    }


def per_level(stays: list[Stay]) -> list[dict]:
    """Each level's exp, seconds on it and travel before it, by exp a second with the travel (best first)."""
    rows: dict[str, dict] = {}
    for stay in stays:
        row = rows.setdefault(stay.name, {'level': stay.name, 'act': stay.act, 'exp': 0, 'on': 0, 'travel': 0.0,
                                          'stays': 0})  # fmt: skip
        row['exp'] += stay.gain
        row['on'] += stay.seconds
        row['travel'] += stay.travel
        row['stays'] += 1
    for row in rows.values():
        spent = row['on'] + row['travel']
        row['a_second'] = row['exp'] / spent if spent else 0.0
        row['on_level'] = row['exp'] / row['on'] if row['on'] else 0.0
    return sorted(rows.values(), key=lambda r: -r['a_second'])


def by_class(stays: list[Stay]) -> dict[str, dict]:
    """Exp a second with travel by class (shard / natural / ?) and act."""
    out: dict[str, dict] = {}
    for stay in stays:
        for key in (stay.kind, f'{stay.kind} act {stay.act}'):
            row = out.setdefault(key, {'exp': 0, 'seconds': 0.0})
            row['exp'] += stay.gain
            row['seconds'] += stay.seconds + stay.travel
    for row in out.values():
        row['a_second'] = row['exp'] / row['seconds'] if row['seconds'] else 0.0
    return dict(sorted(out.items()))


def measure(window: Window, areas: frozenset[int] | None = None) -> dict:
    pieces = window.plays.pieces
    areas = weak_areas() if areas is None else areas
    play = sum(p.seconds for p in pieces)
    wall = (max(p.end for p in pieces) - min(p.start for p in pieces)).total_seconds() if pieces else 0.0
    exp = sum(s.gain for s in window.stays)
    doing: dict[str, float] = defaultdict(float)
    for piece in pieces:
        doing[piece.activity or piece.phase] += piece.seconds
    on = sum(s.seconds for s in window.stays)
    travel = sum(s.travel for s in window.stays)
    games = games_of(window)
    kills = sum(g['kills'] for g in games)
    elite = sum(g['elites'] for g in games)
    boss = sum(g['bosses'] for g in games)
    return {
        'kind': window.plays.kind,
        'play_seconds': play,
        'wall_seconds': wall,
        'exp': exp,
        'per_play_hour': 3600 * exp / play if play else None,
        'per_wall_hour': 3600 * exp / wall if wall else None,
        'stays': len(window.stays),
        'from_takes': sum(1 for s in window.stays if s.take),
        'lost': [{'end': s.end, 'level': s.name, 'exp': s.gain} for s in window.stays if s.gain < 0],
        'kills': kills,
        'elites': elite,
        'bosses': boss,
        'kills_per_hour': 3600 * kills / play if play else None,
        'elites_per_hour': 3600 * elite / play if play else None,
        'bosses_per_hour': 3600 * boss / play if play else None,
        'takes': {
            'in_play': window.takes,
            'out': [
                {'end': take.end, 'level': numbered_name(take.area), 'exp': gain}
                for take, gain in window.takes_out
                if take.area not in TOWNS or gain
            ],
        },
        'on_level_seconds': on,
        'travel_seconds': travel,
        'outside': {'stays': len(window.outside), 'exp': sum(s.gain for s in window.outside)},
        'activities': {name: doing.get(name, 0.0) for name in elites.ACTIVITIES},
        'levels': per_level(window.stays),
        'classes': by_class(window.stays),
        'gaps': gaps(window),
        'games': games,
        'baal': baal_summary(games),
        'shortened': shortened(window, areas, exp / play if play else 0.0),
    }


def weak(result: dict, below: float = WEAK_BELOW) -> list[dict]:
    """The levels to shorten: under `below` exp a second with the travel, under the window's average exp a second of
    play on the level itself, WEAK_SECONDS and WEAK_STAYS at least, its area known; slowest first."""
    average = result['exp'] / result['play_seconds'] if result['play_seconds'] else 0.0
    found = [
        row
        for row in result['levels']
        if row['a_second'] < below
        and row['on_level'] < average
        and row['on'] >= WEAK_SECONDS
        and row['stays'] >= WEAK_STAYS
        and AREAS.get(row['level']) is not None
    ]
    return sorted(found, key=lambda row: row['a_second'])


def weak_file(result: dict, since: datetime, until: datetime, below: float = WEAK_BELOW) -> dict:
    """The JSON macros/tzroutine.py `weak_areas` reads: the weak levels with their rates, and how they were found."""
    average = result['exp'] / result['play_seconds'] if result['play_seconds'] else 0.0
    return {
        'about': (
            'Weak TZ levels for macros/tzroutine.py SHORT_LEVELS (the player, 2026-10-25 ~10:15: "Shorten them: clear '
            'only the elites, bosses and big packs on those levels, then move on"). Made by the d2-loop-watch skill\'s '
            'exphour.py --weak-out; do not edit by hand.'
        ),
        'made': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'window': [f'{since:%Y-%m-%d %H:%M}', f'{until:%Y-%m-%d %H:%M}'],
        'rule': {
            'below_with_travel': below,
            'on_level_under_average': round(average),
            'seconds_at_least': WEAK_SECONDS,
            'stays_at_least': WEAK_STAYS,
        },
        'levels': [
            {
                'area': AREAS[row['level']],
                'name': row['level'],
                'a_second': round(row['a_second']),
                'on_level': round(row['on_level']),
                'exp': row['exp'],
                'on': row['on'],
                'travel': round(row['travel']),
                'stays': row['stays'],
            }
            for row in weak(result, below)
        ],
    }


def dropped(label: str, kind: str) -> bool:
    """Whether agenda.py SHORT leaves this target: an unexplored room, a group under SHORT_PACK."""
    group = GROUP.search(label)
    return kind == EXPLORE or (group is not None and int(group.group(1)) < SHORT_PACK)


def shortened(window: Window, areas: frozenset[int], average: float) -> dict:
    """The SHORT_LEVELS replay: per weak level, its seconds and exp, the seconds of the targets SHORT drops, and the
    exp an hour of play gained if that time went at `average` exp a second instead of the level's own rate."""
    times = [at for at, _, _ in window.targets]
    rows: dict[str, dict] = {}
    for stay in window.stays:
        if stay.area not in areas or not stay.seconds:
            continue
        begun = stay.end - timedelta(seconds=stay.seconds)
        row = rows.setdefault(stay.name, {'level': stay.name, 'area': stay.area, 'stays': 0, 'on': 0, 'exp': 0,
                                          'dropped': 0.0})  # fmt: skip
        row['stays'] += 1
        row['on'] += stay.seconds
        row['exp'] += stay.gain
        i, j = bisect.bisect_left(times, begun), bisect.bisect_right(times, stay.end)
        inside = window.targets[i:j]
        for (at, label, kind), after in zip(inside, [*times[i + 1 : j], stay.end], strict=False):
            leg = bisect.bisect_right(window.legs, at)
            if leg < len(window.legs):
                after = min(after, window.legs[leg])  # the run's leg ended (loot, Town Portal)
            if dropped(label, kind):
                row['dropped'] += (after - at).total_seconds()
    play = sum(p.seconds for p in window.plays.pieces)
    gain = 0.0
    for row in rows.values():
        own = row['exp'] / row['on']
        row['gain_exp'] = row['dropped'] * max(average - own, 0.0)
        gain += row['gain_exp']
    return {
        'levels': sorted(rows.values(), key=lambda r: -r['dropped']),
        'dropped': sum(r['dropped'] for r in rows.values()),
        'per_play_hour': 3600 * gain / play if play else 0.0,
    }


def report(result: dict, levels: int) -> None:
    play, wall = result['play_seconds'], result['wall_seconds']
    if not play:
        print(f'{result["kind"]}: no play in the window')
        return
    print(f"{result['kind']}: {result['exp']:,} exp in {play / 3600:.2f} h of play = "
          f"{result['per_play_hour'] / 1e6:.2f} M an hour ({result['exp'] / play:,.0f}/s); "
          f"{wall / 3600:.2f} h of wall clock = {result['per_wall_hour'] / 1e6:.2f} M a wall hour")  # fmt: skip
    print(f"  {result['stays']} level stays ({result['from_takes']} from the combat takes): "
          f"{result['on_level_seconds']:,} s on levels, "
          f"{result['travel_seconds']:,.0f} s of travel before them")  # fmt: skip
    print(f"  kills: {result['kills']:,} monsters (the takes') = {result['kills_per_hour']:,.0f} an hour of play; "
          f"{result['elites']} elites = {result['elites_per_hour']:.1f} an hour; {result['bosses']} bosses = "
          f"{result['bosses_per_hour']:.1f} an hour")  # fmt: skip
    for out in result['takes']['out']:
        print(f"  (a take on {out['level']} ended out of play at {out['end']:%H:%M:%S}, the loop off or a restart: "
              f"its {out['exp'] or 0:,} exp and its kills not counted)")  # fmt: skip
    for lost in result['lost']:
        print(f'  experience lost on {lost["level"]} by {lost["end"]:%H:%M:%S}: {lost["exp"]:,} (a death?)')
    if result['outside']['stays']:
        outside = result['outside']
        print(f'  ({outside["stays"]} level lines out of play, {outside["exp"]:,} exp: not counted)')
    print(f'  {"activity":12} {"seconds":>8} {"share":>6} {"s/h":>6}')
    for name, seconds in result['activities'].items():
        print(f'  {name:12} {seconds:8.0f} {seconds / play:6.0%} {3600 * seconds / play:6.0f}')
    print('  class            exp/s with travel   seconds')
    for name, row in result['classes'].items():
        print(f'  {name:16} {row["a_second"]:8,.0f}/s {row["seconds"]:12,.0f}')
    rows = [r for r in result['levels'] if r['on'] >= 60]
    if rows:
        print(f'  levels (60 s or more on them), exp a second with the travel before them; best {levels}:')
        for row in rows[:levels]:
            print(level_row(row))
        print(f'  worst {levels}:')
        for row in rows[-levels:][::-1]:
            print(level_row(row))
    short = result['shortened']
    if short['levels']:
        print(f"  SHORT_LEVELS replay: {short['dropped']:,.0f} s on the weak levels' rooms and small groups; at the "
              f"average instead: +{short['per_play_hour'] / 1e6:.2f} M an hour of play (an upper bound)")  # fmt: skip
        for row in short['levels']:
            print(f"    {row['level']:24} {row['stays']:2d} stays, {row['on']:5d} s on it, {row['dropped']:5.0f} s "
                  f"dropped ({row['dropped'] / row['on']:.0%})")  # fmt: skip
    baal_report(result)
    lost = sum(g['seconds'] for g in result['gaps'])
    print(f'  out of play between pieces (over {GAP_SECONDS:.0f} s): {lost:,.0f} s = {lost / wall:.1%} of the wall '
          'clock')  # fmt: skip
    for gap in result['gaps']:
        print(f"    {gap['from']:%m-%d %H:%M:%S} -> {gap['to']:%H:%M:%S} {gap['seconds']:6.0f} s  "
              f"{' | '.join(text[:100] for text in gap['said'])}")  # fmt: skip


def baal_report(result: dict) -> None:
    """The Baal games, one a line (T: terrorized, *: whole), and the medians over the whole ones."""
    summary = result['baal']
    if not summary['games']:
        return
    print(f"  Baal games: {summary['games']} ({summary['terrorized']} terrorized, {summary['whole']} whole); "
          f"a whole game {summary['median_game']:.0f} s (median), {summary['exp_a_game']:,.0f} exp and "
          f"{summary['kills_a_game']:.0f} kills (mean)")  # fmt: skip
    head = ''.join(f'{phase:>7}' for phase in BAAL_PHASES)
    print(f'    {"start":8} {"game":24}   {"s":>5} {"exp":>9} {"kills":>5} {"el":>3} {"bo":>2}{head}')
    for game in result['games']:
        if 'baal' not in game:
            continue
        flags = ('T' if game['terrorized'] else ' ') + ('*' if game['whole'] else ' ')
        phases = ''.join(f'{game["baal"][phase]:7.0f}' for phase in BAAL_PHASES)
        print(f"    {game['start']:%H:%M:%S} {game['game']:24} {flags} {game['seconds']:5.0f} {game['exp']:9,} "
              f"{game['kills']:5d} {game['elites']:3d} {game['bosses']:2d}{phases}")  # fmt: skip
    medians = ''.join(f'{summary["median"][phase]:7.0f}' for phase in BAAL_PHASES)
    print(f'    {"median":8} {"(whole games)":24}    {summary["median_game"]:5.0f}{"":24}{medians}')
    print('  whole games by the shard: ' + '; '.join(
        f"{name} {side['games']}: {side['per_play_hour'] / 1e6:.2f} M exp and {side['kills_per_hour']:,.0f} kills an "
        'hour of play' for name, side in summary['split'].items() if side['games']))  # fmt: skip


def level_row(row: dict) -> str:
    return (
        f'    {row["level"]:32} a{row["act"] or "?"} {row["exp"]:>12,} on {row["on"]:5d} s + {row["travel"]:5.0f} s '
        f'({row["stays"]:2d}) {row["a_second"]:6,.0f}/s (on the level {row["on_level"]:6,.0f}/s)'
    )


def against_report(result: dict, against: list[datetime]) -> None:
    other = result['against']
    print(f'\nagainst {against[0]:%Y-%m-%d %H:%M}-{against[1]:%H:%M}: {other["games"]} games in '
          f'{other["play_seconds"] / 3600:.2f} h of play there, {len(result["games"])} games in '
          f'{result["play_seconds"] / 3600:.2f} h here')  # fmt: skip
    print(f'  {other["shift"]}')
    print(f'  {other["kills_shift"]}')
    was, now = other['baal'], result['baal']
    if was['games'] or now['games']:
        print(f'  Baal games: {was["games"]} there ({was["terrorized"]} terrorized, {was["whole"]} whole), '
              f'{now["games"]} here ({now["terrorized"]} terrorized, {now["whole"]} whole); the whole ones alone: '
              f'{other["whole_shift"]}')  # fmt: skip
        for name, summary in (('there', was), ('here', now)):
            print(f'    {name}: ' + '; '.join(
                f"{side} {row['games']} whole: {row['per_play_hour'] / 1e6:.2f} M exp, {row['kills_per_hour']:,.0f} "
                'kills an hour of play' for side, row in summary['split'].items() if row['games']))  # fmt: skip
    if was['whole'] and now['whole']:
        print(f'  Baal phases, median seconds of the whole games ({was["whole"]} there -> {now["whole"]} here):')
        print('    ' + ', '.join(f'{phase} {was["median"][phase]:.0f} -> {now["median"][phase]:.0f}'
                                 for phase in BAAL_PHASES if was['median'][phase] or now['median'][phase]))  # fmt: skip
        print(f'    a game {was["median_game"]:.0f} -> {now["median_game"]:.0f} s; {was["exp_a_game"]:,.0f} -> '
              f'{now["exp_a_game"]:,.0f} exp and {was["kills_a_game"]:.0f} -> {now["kills_a_game"]:.0f} kills a '
              'game (mean)')  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    now = datetime.now()
    parser.add_argument('--since', type=logwords.local, default=now - timedelta(hours=2))
    parser.add_argument('--until', type=logwords.local, default=now)
    parser.add_argument(
        '--kind', default='tz', choices=('tz', 'tzclear', *elites.ACT_KINDS, 'andariel', 'lk', 'baal', 'any')
    )
    parser.add_argument('--against', nargs=2, type=logwords.local, metavar=('SINCE', 'UNTIL'))
    parser.add_argument('--levels', type=int, default=12, help='best and worst levels shown')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--runs', type=Path, default=RUNS, help="the sessions directory (default: this checkout's)")
    parser.add_argument('--combat', type=Path, help="the combat takes' directory (default: beside --runs)")
    parser.add_argument('--weak-out', type=Path, help='write the weak levels (SHORT_LEVELS) to this JSON file')
    parser.add_argument('--weak-below', type=float, default=WEAK_BELOW)
    parser.add_argument('--weak-areas', type=int, nargs='+', help="the replay's areas (default: the data file's)")
    args = parser.parse_args()
    window = read(args.since, args.until, args.kind, args.runs, args.combat)
    result = measure(window, frozenset(args.weak_areas) if args.weak_areas else None)
    if args.weak_out:
        made = weak_file(result, args.since, args.until, args.weak_below)
        args.weak_out.write_text(json.dumps(made, indent=1) + '\n')
        print(f'{len(made["levels"])} weak levels written to {args.weak_out}: '
              + ', '.join(f"{row['name']} {row['a_second']:,}/s" for row in made['levels']))  # fmt: skip
    if args.against:
        other = measure(read(args.against[0], args.against[1], args.kind, args.runs, args.combat))
        result['against'] = {
            'per_play_hour': other['per_play_hour'],
            'per_wall_hour': other['per_wall_hour'],
            'kills_per_hour': other['kills_per_hour'],
            'games': len(other['games']),
            'play_seconds': other['play_seconds'],
            'baal': other['baal'],
            'shift': shift(other['games'], result['games']),
            'kills_shift': shift(other['games'], result['games'], 'kills'),
            'whole_shift': shift(whole_baal(other['games']), whole_baal(result['games']), minimum=WHOLE_MINIMUM),
        }
    if args.json:
        print(json.dumps(result, default=str, indent=1))
        return
    report(result, args.levels)
    if args.against:
        against_report(result, args.against)


if __name__ == '__main__':
    main()
