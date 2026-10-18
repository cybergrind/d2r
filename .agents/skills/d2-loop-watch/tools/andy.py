"""Andariel kills an hour of play of the KP_6 Andariel loop, and where the time between two kills goes.

Run with the repo's Python (it reads the combat takes):
`uv run --offline python .agents/skills/d2-loop-watch/tools/andy.py`.

A window is a stretch of local clock time (`--since`, `--until`; default the last 2 hours). Every serve session
(`runs/alt-d/<UTC>-<id>/probe.log`) overlapping it is read from its start, so the loop's state at the window's start is
known; a game a restart cut goes on in the next session (by its game name: `Creating <name>`, or the `game` of the
first combat take after the restart).

1. **Headline**: `Boss kill: Andariel` lines said while the loop was on and running Andariel, over the **hours of
   play**: the time the loop was on with the Andariel kind (the resume line's `run Andariel`, `Loop run:`, or its
   legs), without the stretches it was off (the player's KP_6, `loop stopped`), the gaps between sessions (restarts),
   and stalls the player sorted out (STALL_SECONDS and more with no leg line, ended by the player's KP_6 or a stop).
   `--against SINCE UNTIL`: the other window's rate and a 90% bootstrap interval of the difference (kill-to-kill
   cycles resampled), better / worse / no evidence.
2. **Cycle breakdown** (kill to the next kill, play time only): the seconds of each phase, median and p90 over the
   cycles that had it, and seconds a cycle. Phases change at the log's marks: the kill (loot after), Save and Exit
   (next game), `game loaded` (town, prebuff), the `to the Catacombs` leg (the waypoint), Catacombs 2's take (its
   arrival: the swap and Call to Arms), the `down the Catacombs` leg (the run to the stairs), `route Andariel: enter
   Next level` (the stairs press), Catacombs 3's take, Catacombs 4's take (to Andariel in reach), her first frame
   within the strike's reach in the take (in reach to dead; the take's kill event is her death's time). Trade
   sessions, trips for room and Gheed's swaps are phases of their own, counted with how often they come.
3. **Walks on the down legs**: per level and game, the `W walks` of its `leg time` lines, the walking stretches of the
   take (modes walk / run: combat/legs.py MOVING; those starting in the first second are the game's walk-out of the
   stairs), the distance from the stairs' mark when the press was made and the way walked into them (`door Next
   level: ... walked X`); the worst games with their clock time.
4. **The fight on Catacombs 4**: per game arrival to the kill, arrival to in reach, the strikes (Echoing Strike blade
   births in the take, five blades a strike), strikes a second with Andariel in reach, and the idle time with her in
   reach (neither casting nor moving).
5. **Missed kills**: a game of the window with no kill, and why when the log says (a recovery, a stop, the player's
   KP_6, a restart, a death).

    uv run --offline python .agents/skills/d2-loop-watch/tools/andy.py [--since 'YYYY-MM-DD HH:MM'] [--until ...]
        [--against 'YYYY-MM-DD HH:MM' 'YYYY-MM-DD HH:MM'] [--worst 8] [--no-takes] [--json]
"""

import argparse
import bisect
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE), str(ROOT)]

import games  # ruff: ignore[module-import-not-at-top-of-file] - the skill's own tool, beside this one
import speed  # ruff: ignore[module-import-not-at-top-of-file]
from logwords import (  # ruff: ignore[module-import-not-at-top-of-file]
    CREATING,
    DOOR_IN,
    DOOR_MARKED,
    GAME_LOADED,
    KILL,
    KIND,
    LEFT,
    LEG,
    LEG_TIME,
    LOOP_OFF,
    LOOP_ON,
    LOOP_RESUMED,
    OPENED,
    REQUEST_LOOP,
    RESUMED,
    ROUTE_ENTER,
    RUN_TO_NEXT,
    SAID,
    SAVE_AND_EXIT,
    STAMP_LEN,
    STOPPED,
    stamp,
)

from inventory_tracking.builds.warlock.echoing_strike.mechanics import (  # ruff: ignore[module-import-not-at-top-of-file]
    MISSILE,
    RANGE,
)
from inventory_tracking.combat.legs import CASTING, MOVING  # ruff: ignore[module-import-not-at-top-of-file]
from inventory_tracking.combat.takes import (  # ruff: ignore[module-import-not-at-top-of-file]
    Take,
    monsters_of,
    player_of,
)


RUNS = games.RUNS
COMBAT = ROOT / 'inventory_tracking' / 'runs' / 'combat'
ANDARIEL_TXT = 156  # monstats.txt *hcIdx of `andariel` (third-parties/d2data/json/monstats.json)
CATACOMBS_2, CATACOMBS_3, CATACOMBS_4 = 35, 36, 37  # levels.txt
STALL_SECONDS = 90.0  # no leg line this long, then the player's KP_6 or a stop: a stall the player sorted out
REQUEST_SECONDS = 2.0  # a Loop off this soon after `request loop` is the player's KP_6 (even past a resume line)
WALKOUT_SECONDS = 1.0  # a walk starting this soon after a take's first frame: the game's walk-out of the stairs
BIRTHS_APART = 0.08  # s: blade births closer than this are one strike

# The legs, as macros/loop.py says them (the HUD's words)
NEXT_GAME, LEAVE, WAYPOINT_LEG, DOWN, FIGHT, PICK_UP = (
    'next game',
    'Save and Exit',
    'to the Catacombs',
    'down the Catacombs',
    'Andariel',
    'what is left',
)
# 'town visit' since 2026-10-18 (macros/visit.py): one leg for Cain, the stash, Jamella and Halbu; the four before it
# kept for the older logs
TRADE_LEGS = {
    'to Pandemonium Fortress',
    'town visit',
    'scrolls and keys',
    'identify',
    'the stash',
    "the staff's charges",
}
TRIP_LEGS = {'to town for room', 'to the Rogue Encampment', 'back through the portal'}
SWAP_LEGS = {"Gheed's Fortune away", "Gheed's Fortune back"}
ANDARIEL_LEGS = {WAYPOINT_LEG, DOWN, FIGHT} | TRIP_LEGS | SWAP_LEGS
LK_LEGS = {'to Lower Kurast', 'the chests', 'Town Portal'}

# The phases of a kill-to-kill cycle, in their order
LOOT = 'loot after the kill'
LOBBY = 'next game (Save and Exit to loaded)'
TOWN = 'town, prebuff'
WAYPOINT = 'to the Catacombs (waypoint)'
ARRIVAL = 'Catacombs 2 arrival (swap, CTA, prebuff)'
RUN2 = 'Catacombs 2 run to the stairs'
STAIRS2 = 'Catacombs 2 stairs press'
RUN3 = 'Catacombs 3 run to the stairs'
STAIRS3 = 'Catacombs 3 stairs press'
TO_REACH = 'Catacombs 4 arrival to Andariel in reach'
IN_REACH = 'Catacombs 4 in reach to dead'
TRADE = 'trade session (Fortress)'
TRIP = 'trip to town for room'
SWAP = "Gheed's swap"
RECOVERY = 'recovery (game left)'
PHASES = [LOOT, LOBBY, TOWN, WAYPOINT, ARRIVAL, RUN2, STAIRS2, RUN3, STAIRS3, TO_REACH, IN_REACH]
EXTRA = [TRADE, TRIP, SWAP, RECOVERY]
RUNS_BY_AREA = {CATACOMBS_2: RUN2, CATACOMBS_3: RUN3}
STAIRS_BY_AREA = {CATACOMBS_2: STAIRS2, CATACOMBS_3: STAIRS3}


@dataclass
class Event:
    at: datetime
    kind: str  # 'leg', 'kill', 'on', 'off', 'request', 'area', 'create', 'loaded', 'save', 'route', 'run', 'left',
    # 'stopped', 'marked', 'door', 'legtime', 'reach', 'loopkind', 'end'
    data: Any = None
    run: str | None = None  # the loop's kind then: 'andariel', 'lk', None


@dataclass
class Level:
    """One game's visit of Catacombs 2 or 3: what the log and the take say of its walks and its stairs."""

    take: str | None = None
    entered: datetime | None = None
    log_walks: int = 0
    log_jumps: int = 0
    presses: int = 0
    stand_off: float | None = None  # units from the stairs' mark at the first press
    walked_in: float = 0.0  # units walked into the stairs, all presses
    take_walks: int | None = None
    take_walk_s: float | None = None
    walkout_s: float | None = None


@dataclass
class Game:
    name: str
    first: datetime
    session: str
    levels: dict[int, Level] = field(default_factory=dict)
    fight_take: str | None = None
    killed: datetime | None = None
    kills: int = 0
    notes: list[str] = field(default_factory=list)
    legs: Counter[str] = field(default_factory=Counter)
    played: datetime | None = None  # its first leg made in the window with the loop on


def local(text: str) -> datetime:
    return datetime.strptime(text, '%Y-%m-%d %H:%M')


def utc_name(when: datetime) -> str:
    return when.astimezone(UTC).strftime('%Y%m%dT%H%M%S')


def sessions(since: datetime, until: datetime) -> list[Path]:
    """The serve sessions whose log overlaps the window (started before its end, written after its start)."""
    high = utc_name(until)
    found = []
    for directory in sorted(d for d in RUNS.iterdir() if d.is_dir() and d.name.startswith('20')):
        log = directory / 'probe.log'
        if directory.name.split('Z')[0] > high or not log.exists():
            continue
        if datetime.fromtimestamp(log.stat().st_mtime) >= since:
            found.append(directory)
    return found


def parse(directory: Path) -> list[Event]:
    """A session's log as the events this tool reads, the loop's kind set on each."""
    events: list[Event] = []
    for line in (directory / 'probe.log').read_text(errors='replace').splitlines():
        at = stamp(line)
        if at is None:
            continue
        text = line[STAMP_LEN:]
        if (m := LEG.search(text)) is not None:
            events.append(Event(at, 'leg', (int(m.group(1)), m.group(2).strip())))
        elif KILL.search(text):
            events.append(Event(at, 'kill'))
        elif (m := OPENED.search(text)) is not None:
            events.append(Event(at, 'area', (int(m.group(2)), m.group(1))))
        elif (m := CREATING.search(text)) is not None:
            events.append(Event(at, 'create', m.group(1)))
        elif (m := RESUMED.search(text)) is not None:
            events.append(Event(at, 'loopkind', (m.group(2) or '').strip() or None))
        elif (m := KIND.search(text)) is not None:
            events.append(Event(at, 'loopkind', m.group(1).strip()))
        elif LOOP_ON in text or SAID + LOOP_RESUMED in text:
            events.append(Event(at, 'on'))
        elif LOOP_OFF in text:
            events.append(Event(at, 'off', 'player'))
        elif (m := STOPPED.search(text)) is not None:
            events.append(Event(at, 'stopped', m.group(1)))
        elif REQUEST_LOOP in text:
            events.append(Event(at, 'request'))
        elif (m := LEFT.search(text)) is not None:
            events.append(Event(at, 'left', m.group(1)))
        elif GAME_LOADED in text:
            events.append(Event(at, 'loaded'))
        elif text.rstrip().endswith(SAVE_AND_EXIT):
            events.append(Event(at, 'save'))
        elif ROUTE_ENTER in text:
            events.append(Event(at, 'route'))
        elif RUN_TO_NEXT in text:
            events.append(Event(at, 'run'))
        elif (m := DOOR_MARKED.search(text)) is not None:
            events.append(Event(at, 'marked', float(m.group(1))))
        elif (m := DOOR_IN.search(text)) is not None:
            events.append(Event(at, 'door', (float(m.group(1)), float(m.group(2)))))
        elif (m := LEG_TIME.search(text)) is not None:
            events.append(Event(at, 'legtime', (int(m.group(3)), int(m.group(4)))))
    if events:
        events.append(Event(events[-1].at, 'end'))
    kind: str | None = None
    for event in events:
        if event.kind == 'loopkind' and event.data:
            kind = 'andariel' if event.data == 'Andariel' else 'lk'
        elif event.kind == 'leg':
            name = event.data[1]
            kind = 'andariel' if name in ANDARIEL_LEGS else 'lk' if name in LK_LEGS else kind
        event.run = kind
    first = next((e.run for e in events if e.run is not None), None)
    for event in events:
        if event.run is not None:
            break
        event.run = first
    return events


# The takes


def wall_of(take: Take, t: float) -> datetime:
    """A take's monotonic time as local clock time (its manifest's `clock`)."""
    clock = take.manifest['clock']
    return datetime.fromtimestamp(clock['wall'] + t - clock['monotonic'])


def take_game(name: str) -> str | None:
    try:
        return json.loads((COMBAT / name / 'manifest.json').read_text()).get('game')
    except OSError, ValueError:
        return None


def strikes_of(take: Take) -> list[float]:
    """The times of the character's Echoing Strikes: its blades' births, BLADES at once."""
    births = sorted(m['t'] for m in take.missiles if m.get('txt_id') == MISSILE)
    found: list[float] = []
    for t in births:
        if not found or t - found[-1] > BIRTHS_APART:
            found.append(t)
    return found


def walks_of(take: Take, until: float | None = None) -> tuple[int, float, float]:
    """Walking stretches (modes walk / run) of a take: their count, seconds, and the seconds of those starting within
    WALKOUT_SECONDS of the first frame (the game's walk-out of the stairs)."""
    count, seconds, walkout = 0, 0.0, 0.0
    start = take.frames[0]['t'] if take.frames else 0.0
    began: float | None = None
    for before, after in pairwise(take.frames):
        if until is not None and before['t'] >= until:
            break
        player = player_of(before)
        step = after['t'] - before['t']
        if player is not None and player.mode in MOVING:
            if began is None:
                count += 1
            began = before['t'] if began is None else began
            seconds += step
            if began - start < WALKOUT_SECONDS:
                walkout += step
        else:
            began = None
    return count, seconds, walkout


@dataclass
class Fight:
    take: str
    arrived: datetime
    reach: datetime | None
    killed: datetime | None
    strikes: int  # arrival to the kill
    in_reach_s: float
    strikes_in_reach: int
    idle_in_reach_s: float
    moving_in_reach_s: float

    @property
    def to_kill(self) -> float | None:
        return (self.killed - self.arrived).total_seconds() if self.killed else None

    @property
    def to_reach(self) -> float | None:
        return (self.reach - self.arrived).total_seconds() if self.reach else None

    @property
    def rate(self) -> float | None:
        return self.strikes_in_reach / self.in_reach_s if self.in_reach_s > 0.2 else None


def fight_of(path: Path) -> Fight | None:
    """Catacombs 4's take: when Andariel was first within the strike's reach (RANGE) and alive, her death (the take's
    kill event), the strikes, and the seconds with her in reach split into casting, moving and idle."""
    try:
        take = Take.load(path)
    except (OSError, ValueError, KeyError) as error:
        print(f'  {path.name}: not read ({error})', file=sys.stderr)
        return None
    if len(take.frames) < 2:
        return None
    kill_t = next((e['t'] for e in take.events if e['event'] == 'kill' and e.get('txt') == ANDARIEL_TXT), None)
    end = kill_t if kill_t is not None else take.frames[-1]['t']
    strikes = strikes_of(take)
    reach_t: float | None = None
    in_reach = idle = moving = 0.0
    spans: list[tuple[float, float]] = []
    for before, after in pairwise(take.frames):
        if before['t'] >= end:
            break
        player = player_of(before)
        her = next((m for m in monsters_of(before) if m.txt == ANDARIEL_TXT and m.alive), None)
        if player is None or her is None or math.dist(player.at, her.at) > RANGE:
            continue
        if reach_t is None:
            reach_t = before['t']
        step = min(after['t'], end) - before['t']
        spans.append((before['t'], before['t'] + step))
        in_reach += step
        if player.mode in MOVING:
            moving += step
        elif player.mode not in CASTING:
            idle += step
    starts = [s for s, _ in spans]
    struck = 0
    for t in strikes:
        i = bisect.bisect_right(starts, t) - 1
        struck += i >= 0 and spans[i][0] <= t < spans[i][1] + 0.05
    return Fight(
        path.name,
        wall_of(take, take.frames[0]['t']),
        wall_of(take, reach_t) if reach_t is not None else None,
        wall_of(take, kill_t) if kill_t is not None else None,
        sum(t < end for t in strikes),
        in_reach,
        struck,
        idle,
        moving,
    )


# The pass over the events


@dataclass
class Window:
    since: datetime
    until: datetime
    pieces: list[tuple[datetime, datetime, str]] = field(default_factory=list)  # play time by phase
    excluded: list[tuple[datetime, datetime, str]] = field(default_factory=list)
    kills: list[datetime] = field(default_factory=list)
    kills_off: list[datetime] = field(default_factory=list)  # said with the loop off or on another run
    marks: list[tuple[datetime, str]] = field(default_factory=list)  # restarts, pauses, recoveries, stops
    games: dict[str, Game] = field(default_factory=dict)
    fights: dict[str, Fight] = field(default_factory=dict)
    sessions: list[str] = field(default_factory=list)

    def inside(self, at: datetime) -> bool:
        return self.since <= at <= self.until


def read(since: datetime, until: datetime, takes: bool = True) -> Window:
    window = Window(since, until)
    every: list[tuple[str, list[Event]]] = []
    for directory in sessions(since, until):
        every.append((directory.name, parse(directory)))
        window.sessions.append(directory.name)
    if takes:
        # Her reach and her death from Catacombs 4's takes: a reach event, and the kill line moved to the take's time
        for _, events in every:
            added = []
            for event in events:
                if event.kind == 'area' and event.data[0] == CATACOMBS_4 and window.inside(event.at):
                    fight = fight_of(COMBAT / event.data[1])
                    if fight is None:
                        continue
                    window.fights[fight.take] = fight
                    if fight.reach is not None:
                        added.append(Event(fight.reach, 'reach', fight.take, event.run))
                    if fight.killed is not None:
                        line = next(
                            (
                                e
                                for e in events
                                if e.kind == 'kill' and timedelta(0) <= e.at - fight.killed <= timedelta(seconds=3)
                            ),
                            None,
                        )
                        if line is not None:
                            line.at = fight.killed
            events += added
            events.sort(key=lambda e: e.at)
    previous: str | None = None
    for name, events in every:
        previous = walk(window, name, events, previous)
    if takes:
        for game in window.games.values():
            for level in game.levels.values():
                if level.take is None:
                    continue
                try:
                    take = Take.load(COMBAT / level.take)
                except OSError, ValueError, KeyError:
                    continue
                if take.frames:
                    level.take_walks, level.take_walk_s, level.walkout_s = walks_of(take)
    return window


def walk(window: Window, session: str, events: list[Event], game_name: str | None) -> str | None:
    """One session's events in order: play time by phase, kills, the games and their levels. Returns the game the
    session ended in (a restart's next session goes on with it)."""
    on = False
    asked: datetime | None = None  # the player's last KP_6 request
    phase = LOBBY
    area: int | None = None
    last: datetime | None = None  # the time accounted up to
    progress: datetime | None = None  # the last leg line
    trip = False
    game = window.games.get(game_name) if game_name else None
    first_area_seen = False

    def account(upto: datetime, run: str | None) -> None:
        nonlocal last
        if last is not None and on and run == 'andariel':
            start, end = max(last, window.since), min(upto, window.until)
            if end > start:
                window.pieces.append((start, end, phase))
        last = upto

    def ensure(name: str, at: datetime) -> Game:
        found = window.games.get(name)
        if found is None:
            found = window.games[name] = Game(name, at, session)
        return found

    def note(text: str, at: datetime) -> None:
        if game is not None:
            game.notes.append(f'{at:%H:%M:%S} {text}')
        if window.inside(at):
            window.marks.append((at, text))

    for event in events:
        at = event.at
        account(at, event.run)
        kind = event.kind
        if kind == 'request':
            asked = at
        elif kind == 'on':
            on = True
            if progress is None or progress < at:
                progress = at
        elif kind in ('off', 'stopped'):
            if on:
                theirs = asked is not None and (at - asked).total_seconds() <= REQUEST_SECONDS
                why = f'stopped: {event.data}' if kind == 'stopped' else 'the player (KP_6)' if theirs else 'off'
                if progress is not None and (at - progress).total_seconds() >= STALL_SECONDS:
                    window.excluded.append((max(progress, window.since), min(at, window.until), f'stall, then {why}'))
                note(f'loop off: {why}', at)
            on, asked = False, None
        elif kind == 'end':
            if on:
                note('restart (the session ended with the loop on)', at)
            on = False
        elif kind == 'loopkind':
            pass
        elif kind == 'create':
            game = ensure(event.data, at)
        elif kind == 'area':
            number, take = event.data
            area = number
            if not first_area_seen:
                first_area_seen = True
                name = take_game(take)
                if name is not None and (game is None or game.name != name):
                    game = ensure(name, at)
            if game is not None and number in (CATACOMBS_2, CATACOMBS_3):
                game.levels.setdefault(number, Level(take, at))
            if game is not None and number == CATACOMBS_4 and game.fight_take is None:
                game.fight_take = take
            if number == CATACOMBS_2:
                phase = ARRIVAL if phase == WAYPOINT else RUN2
                trip = False
            elif number == CATACOMBS_3:
                phase, trip = RUN3, False
            elif number == CATACOMBS_4:
                phase = TO_REACH if game is None or game.killed is None else LOOT
                trip = False
        elif kind == 'leg':
            progress = at
            _, name = event.data
            if game is not None and on and window.inside(at) and event.run == 'andariel':
                game.played = game.played or at
                game.legs[name] += 1
            if name == NEXT_GAME:
                phase = LOBBY
            elif name == LEAVE:
                phase = RECOVERY if phase == RECOVERY else LOBBY
            elif name in TRIP_LEGS or (trip and name in TRADE_LEGS):
                phase, trip = TRIP, True
            elif name in TRADE_LEGS:
                phase = TRADE
            elif name in SWAP_LEGS:
                phase = SWAP
            elif name == WAYPOINT_LEG:
                phase = WAYPOINT
            elif name == FIGHT and phase not in (TO_REACH, IN_REACH):
                phase = TO_REACH
            elif name == PICK_UP and game is not None and game.killed is not None:
                phase = LOOT
        elif kind == 'loaded':
            if phase == LOBBY:
                phase = TOWN
        elif kind == 'route':
            phase = STAIRS_BY_AREA.get(area, phase) if area is not None else phase
            if game is not None and area in game.levels:
                game.levels[area].presses += 1
        elif kind == 'run':
            phase = RUNS_BY_AREA.get(area, phase) if area is not None else phase
        elif kind == 'reach':
            if phase == TO_REACH:
                phase = IN_REACH
        elif kind == 'kill':
            phase = LOOT
            if game is not None:
                game.kills += 1
                game.killed = at
            if window.inside(at):
                (window.kills if on and event.run == 'andariel' else window.kills_off).append(at)
        elif kind == 'left':
            phase = RECOVERY
            note(f'recovery: {event.data}', at)
        elif kind == 'marked':
            if game is not None and area in game.levels and game.levels[area].stand_off is None:
                game.levels[area].stand_off = event.data
        elif kind == 'door':
            if game is not None and area in game.levels:
                game.levels[area].walked_in += event.data[1]
        elif kind == 'legtime' and game is not None and area in game.levels:
            game.levels[area].log_jumps += event.data[0]
            game.levels[area].log_walks += event.data[1]
    if events and window.inside(events[0].at) and window.sessions and session != window.sessions[0]:
        window.marks.append((events[0].at, f'session {session} began'))
    return game.name if game is not None else game_name


# The measures


def subtract(pieces: list[tuple[datetime, datetime, str]], cuts: list[tuple[datetime, datetime, str]]):
    """The pieces of play without the excluded stretches."""
    found = []
    for start, end, phase in pieces:
        parts = [(start, end)]
        for low, high, _ in cuts:
            parts = [part for a, b in parts for part in ((a, min(b, low)), (max(a, high), b)) if part[1] > part[0]]
        found += [(a, b, phase) for a, b in parts]
    return found


def cycles(window: Window, pieces: list[tuple[datetime, datetime, str]]) -> list[dict]:
    """Kill to the next kill: play seconds by phase, and what else happened in it."""
    kills = sorted(window.kills)
    found = []
    for low, high in pairwise(kills):
        by: dict[str, float] = defaultdict(float)
        for start, end, phase in pieces:
            a, b = max(start, low), min(end, high)
            if b > a:
                by[phase] += (b - a).total_seconds()
        marks = [text for at, text in window.marks if low <= at < high]
        found.append(
            {
                'start': low,
                'seconds': sum(by.values()),
                'wall': (high - low).total_seconds(),
                'phases': dict(by),
                'marks': marks,
            }
        )
    return found


def rate(found: list[dict]) -> float:
    seconds = sum(c['seconds'] for c in found)
    return 3600 * len(found) / seconds if seconds else 0.0


def rate_shift(before: list[dict], after: list[dict]) -> str:
    """Kills an hour of cycles, before -> after, with a 90% bootstrap interval of the difference."""
    if len(before) < speed.MINIMUM or len(after) < speed.MINIMUM:
        return f'too few cycles ({len(before)} / {len(after)})'
    rng = random.Random(7)
    draws = sorted(
        rate(rng.choices(after, k=len(after))) - rate(rng.choices(before, k=len(before))) for _ in range(speed.DRAWS)
    )
    low, high = draws[int(0.05 * speed.DRAWS)], draws[int(0.95 * speed.DRAWS)]
    was, now = rate(before), rate(after)
    verdict = 'better' if low > 0 else 'worse' if high < 0 else 'no evidence'
    interval = f'90% [{low:+.1f}, {high:+.1f}]: {verdict}'
    return f'{was:.1f} -> {now:.1f} kills an hour of cycles ({now - was:+.1f}, {interval})'


def spread(values: list[float]) -> str:
    if not values:
        return '-'
    return f'{statistics.median(values):5.1f} {games.quantile(values, 0.9):5.1f}'


def measure(window: Window) -> dict:
    pieces = subtract(window.pieces, window.excluded)
    hours = sum((b - a).total_seconds() for a, b, _ in pieces) / 3600
    kills = len(window.kills)
    found = cycles(window, pieces)
    played = [g for g in window.games.values() if g.played]
    return {
        'pieces': pieces,
        'hours': hours,
        'kills': kills,
        'per_hour': kills / hours if hours else None,
        'cycles': found,
        'games': played,
    }


def phase_rows(found: list[dict]) -> list[dict]:
    rows = []
    n = len(found)
    for name in PHASES + EXTRA:
        values = [c['phases'][name] for c in found if c['phases'].get(name, 0) > 0]
        if not values:
            continue
        rows.append(
            {
                'phase': name,
                'cycles': len(values),
                'median': statistics.median(values),
                'p90': games.quantile(values, 0.9),
                'a_cycle': sum(values) / n,
            }
        )
    return rows


def level_rows(window: Window, played: list[Game]) -> list[dict]:
    rows = []
    for game in played:
        for number, level in sorted(game.levels.items()):
            if level.entered is None or not window.inside(level.entered):
                continue
            rows.append({'game': game.name, 'level': number, **level.__dict__})
    return rows


def fight_rows(window: Window, played: list[Game]) -> list[Fight]:
    return [window.fights[g.fight_take] for g in played if g.fight_take in window.fights]


def missed(window: Window, played: list[Game]) -> list[tuple[Game, str]]:
    found = []
    names = [g.name for g in played]
    for game in played:
        if game.kills:
            continue
        ended = any(n.split(' ', 1)[1].startswith(('loop off', 'recovery')) for n in game.notes)
        if game.name == names[-1] and not ended:
            found.append((game, 'in progress at the window end'))
            continue
        why = '; '.join(game.notes) or 'the log says nothing (no kill line)'
        found.append((game, why))
    return found


def report(window: Window, result: dict, args: argparse.Namespace) -> None:
    w = window
    print(
        f'window {w.since:%Y-%m-%d %H:%M} .. {w.until:%H:%M}: sessions {len(w.sessions)} '
        f'({w.sessions[0][:16] if w.sessions else "-"} .. {w.sessions[-1][:16] if w.sessions else "-"})'
    )
    rate_text = f'{result["per_hour"]:.1f}' if result['per_hour'] is not None else '-'
    print(
        f'HEADLINE: {result["kills"]} Andariel kills in {result["hours"]:.2f} h of play: **{rate_text} kills an hour**'
    )
    excluded = sum((b - a).total_seconds() for a, b, _ in w.excluded)
    print(
        f'  play = the loop on with the Andariel run, inside sessions; excluded besides the off time: '
        f'{excluded:.0f} s of stalls the player sorted out ({len(w.excluded)})'
    )
    for a, b, why in w.excluded:
        print(f'    {a:%H:%M:%S} .. {b:%H:%M:%S} {why}')
    if w.kills_off:
        print(f'  not counted: {len(w.kills_off)} kills with the loop off or on another run '
              f'({", ".join(f"{k:%H:%M:%S}" for k in w.kills_off)})')  # fmt: skip
    found = result['cycles']
    if found:
        clean = [c for c in found if not c['marks']]
        seconds = [c['seconds'] for c in found]
        print(
            f'  cycles (kill to kill, play time): {len(found)}, median {statistics.median(seconds):.1f}'
            f' s, p90 {games.quantile(seconds, 0.9):.1f} s; {rate(found):.1f} kills an hour of '
            f'cycles; clean (no restart, pause, recovery) {len(clean)}, median '
            f'{statistics.median(c["seconds"] for c in clean) if clean else 0:.1f} s'
        )
    print('\nCYCLE BREAKDOWN (s; median and p90 over the cycles with the phase; s a cycle over all):')
    print(f'  {"phase":44} {"cycles":>6} {"med":>5} {"p90":>5} {"a cycle":>7}')
    rows = phase_rows(found)
    for row in rows:
        print(f'  {row["phase"]:44} {row["cycles"]:6} {row["median"]:5.1f} {row["p90"]:5.1f} {row["a_cycle"]:7.1f}')
    if rows:
        print(f'  {"sum":44} {"":6} {"":5} {"":5} {sum(r["a_cycle"] for r in rows):7.1f}')
    unusual = [c for c in found if c['marks']]
    if unusual:
        print(f'  cycles with a restart, pause, stop or recovery ({len(unusual)}):')
        for c in unusual:
            marks = '; '.join(c['marks'])[:160]
            print(f'    {c["start"]:%H:%M:%S} {c["seconds"]:.0f} s (wall {c["wall"]:.0f} s): {marks}')

    played: list[Game] = result['games']
    levels = level_rows(window, played)
    print('\nWALKS ON THE DOWN LEGS (per level visit; log: `leg time` walks; take: walking stretches, s; walk-out: the')
    print("  game's walk out of the stairs in the first second (Catacombs 2: off the waypoint); stairs: units from the")
    print('  mark at the first press, units walked in over all presses)')
    for number in (CATACOMBS_2, CATACOMBS_3):
        mine = [r for r in levels if r['level'] == number]
        if not mine:
            continue
        taken = [r for r in mine if r['take_walk_s'] is not None]
        line = (
            f'  Catacombs {number - 33}: {len(mine)} visits; log walks {sum(r["log_walks"] for r in mine)} '
            f'(in {sum(r["log_walks"] > 0 for r in mine)} visits), jumps {sum(r["log_jumps"] for r in mine)}'
        )
        if taken:
            walk_s = [r['take_walk_s'] - r['walkout_s'] for r in taken]
            line += (
                f'; take: walks {sum(r["take_walks"] for r in taken)}, s a visit (no walk-out) median/p90 '
                f'{spread(walk_s)}, walk-out median/p90 {spread([r["walkout_s"] for r in taken])}'
            )
        print(line)
        stand = [r['stand_off'] for r in mine if r['stand_off'] is not None]
        walked = [r['walked_in'] for r in mine if r['presses']]
        presses = Counter(r['presses'] for r in mine)
        print(f'    stairs: from the mark median/p90 {spread(stand)} u; walked in median/p90 {spread(walked)} u; '
              f'presses a visit {dict(sorted(presses.items()))}')  # fmt: skip
    worst = sorted(
        levels,
        key=lambda r: -((r['take_walk_s'] or 0) - (r['walkout_s'] or 0) + r['walked_in'] / 10 + r['log_walks']),
    )[: args.worst]
    if worst:
        print(f'  the {len(worst)} worst visits (walk s without the walk-out, walk-out s, log walks, stairs):')
        for r in worst:
            take_s = '-' if r['take_walk_s'] is None else f'{r["take_walk_s"] - r["walkout_s"]:.2f}'
            walkout = '-' if r['walkout_s'] is None else f'{r["walkout_s"]:.2f}'
            stand = '-' if r['stand_off'] is None else f'{r["stand_off"]:.1f}'
            print(f'    {r["entered"]:%H:%M:%S} {r["game"]:9} Catacombs {r["level"] - 33} {r["take"]}: '
                  f'walk {take_s} s, '
                  f'walk-out {walkout} s, log walks {r["log_walks"]}, stairs from {stand} walked {r["walked_in"]:.1f}, '
                  f'presses {r["presses"]}')  # fmt: skip

    fights = fight_rows(window, played)
    print(f'\nFIGHT ON CATACOMBS 4 ({len(fights)} takes; reach = Andariel alive within {RANGE:.1f} units):')
    if fights:
        cols = {
            'arrival to kill s': [f.to_kill for f in fights if f.to_kill is not None],
            'arrival to in reach s': [f.to_reach for f in fights if f.to_reach is not None],
            'in reach s (to the kill)': [f.in_reach_s for f in fights if f.reach is not None],
            'strikes, arrival to kill': [float(f.strikes) for f in fights if f.killed is not None],
            'strikes in reach': [float(f.strikes_in_reach) for f in fights if f.reach is not None],
            'strikes a second in reach': [r for f in fights if (r := f.rate) is not None],
            'idle in reach s': [f.idle_in_reach_s for f in fights if f.reach is not None],
            'walking in reach s': [f.moving_in_reach_s for f in fights if f.reach is not None],
        }
        for name, values in cols.items():
            print(f'  {name:28} median/p90 {spread(values)}  (n {len(values)})')
        no_kill = [f for f in fights if f.killed is None]
        if no_kill:
            print(f'  takes with no kill of her: {", ".join(f.take for f in no_kill)}')
        print(f'  the {min(args.worst, len(fights))} slowest:')
        for f in sorted((f for f in fights if f.to_kill), key=lambda f: -(f.to_kill or 0))[: args.worst]:
            print(f'    {f.arrived:%H:%M:%S} {f.take}: kill {f.to_kill or 0:.1f} s, reach {f.to_reach or 0:.1f} s, '
                  f'in reach {f.in_reach_s:.1f} s, strikes {f.strikes} ({f.strikes_in_reach} in reach, '
                  f'{f.rate or 0:.2f}/s), idle in reach {f.idle_in_reach_s:.1f} s')  # fmt: skip

    lost = missed(window, played)
    print(f'\nGAMES: {len(played)} played, {sum(g.kills > 0 for g in played)} with a kill; MISSED ({len(lost)}):')
    for game, why in lost:
        when = game.played or game.first
        print(f'  {when:%H:%M:%S} {game.name} ({game.session[:16]}): legs {dict(game.legs)}: {why[:220]}')


def summary(window: Window, result: dict) -> dict:
    return {
        'since': window.since,
        'until': window.until,
        'sessions': window.sessions,
        'kills': result['kills'],
        'hours': round(result['hours'], 3),
        'kills_per_hour': round(result['per_hour'], 2) if result['per_hour'] else None,
        'excluded': [(a, b, why) for a, b, why in window.excluded],
        'kills_not_counted': window.kills_off,
        'cycles': [{**c, 'phases': {k: round(v, 2) for k, v in c['phases'].items()}} for c in result['cycles']],
        'phases': phase_rows(result['cycles']),
        'levels': level_rows(window, result['games']),
        'fights': [f.__dict__ for f in fight_rows(window, result['games'])],
        'missed': [{'game': g.name, 'first': g.first, 'why': why} for g, why in missed(window, result['games'])],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--since', type=local)
    parser.add_argument('--until', type=local)
    parser.add_argument('--against', nargs=2, type=local, metavar=('SINCE', 'UNTIL'))
    parser.add_argument('--worst', type=int, default=8)
    parser.add_argument(
        '--no-takes', action='store_true', help='the log alone: no reach (Catacombs 4 is one phase), strikes or walks'
    )
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    until = args.until or datetime.now()
    since = args.since or until - timedelta(hours=2)
    window = read(since, until, takes=not args.no_takes)
    result = measure(window)
    other = None
    if args.against:
        other_window = read(*args.against, takes=not args.no_takes)
        other = (other_window, measure(other_window))
    if args.json:
        out = summary(window, result)
        if other is not None:
            out['against'] = summary(*other)
            out['against']['shift'] = rate_shift(other[1]['cycles'], result['cycles'])
        print(json.dumps(out, indent=1, default=str))
        return
    report(window, result, args)
    if other is not None:
        before_window, before = other
        print(f'\nAGAINST {before_window.since:%Y-%m-%d %H:%M} .. {before_window.until:%H:%M}: before -> now')
        was = f'{before["per_hour"]:.1f}' if before['per_hour'] else '-'
        now = f'{result["per_hour"]:.1f}' if result['per_hour'] else '-'
        print(f'  kills an hour of play: {was} ({before["kills"]} in {before["hours"]:.2f} h) -> {now} '
              f'({result["kills"]} in {result["hours"]:.2f} h)')  # fmt: skip
        print(f'  RATE: {rate_shift(before["cycles"], result["cycles"])}')
        cycle_s = speed.shift([c['seconds'] for c in before['cycles']], [c['seconds'] for c in result['cycles']])
        print(f'  {"cycle s":44} {cycle_s}')
        for name in PHASES:
            a = [c['phases'][name] for c in before['cycles'] if c['phases'].get(name)]
            b = [c['phases'][name] for c in result['cycles'] if c['phases'].get(name)]
            print(f'  {name:44} {speed.shift(a, b)}')
        fa, fb = fight_rows(before_window, before['games']), fight_rows(window, result['games'])
        print(f'  {"fight: arrival to kill s":44} '
              f'{speed.shift([f.to_kill for f in fa if f.to_kill], [f.to_kill for f in fb if f.to_kill])}')  # fmt: skip
        rates = speed.shift([r for f in fa if (r := f.rate)], [r for f in fb if (r := f.rate)], more_better=True)
        print(f'  {"fight: strikes a second in reach":44} {rates}')


if __name__ == '__main__':
    main()
