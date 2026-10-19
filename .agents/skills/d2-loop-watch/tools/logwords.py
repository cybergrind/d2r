"""The serve log's lines the loop-watch tools read, in one place: every pattern, the code that says it, a real line.

The prose log (runs/alt-d/<session>/probe.log) is the tools' only source today, and its wording is an API nobody
versioned: about 30 shapes said at ~30 places in inventory_tracking, read by watch, games, trade, speed, andy and
restart with regexes each of its own (rca/2026-10-18/arch-observability.md §1; migration step 1, 2026-10-18). Here
each shape is written once, with the producing line (`file:line function`, as of 2026-10-18: the lines move, the
function names less) and a line copied from a real log; tests/skills/test_loop_watch_lines.py matches every example
and builds the core lines from the production format strings, so a rewording fails a test instead of a measure.

A tool matches a log line through a name from here, never a regex or substring of its own. Stdlib only: watch, games,
trade and restart run with a plain python3.

Times: every line starts with the logger's local `%Y-%m-%d %H:%M:%S,%f` (common.py), 23 characters (`stamp`).
"""

import re
from datetime import UTC, datetime
from pathlib import Path


RUNS = Path(__file__).resolve().parents[4] / 'inventory_tracking' / 'runs' / 'alt-d'  # serve's sessions
STAMP_FORMAT = '%Y-%m-%d %H:%M:%S,%f'
STAMP_LEN = 23
# The runner's `_say` (runner.py:1026 MacroRunner._say: `LOG.info('Macro: %s', text)`): every `run.say(...)` line has
# this prefix, as has every `LOG.info('Macro: ...')`
SAID = 'Macro: '


def stamp(line: str) -> datetime | None:
    """The line's local date and time, None for a line without one (a traceback's)."""
    try:
        return datetime.strptime(line[:STAMP_LEN], STAMP_FORMAT)
    except ValueError:
        return None


def local(text: str) -> datetime:
    """A tool's `--since`/`--until`: local 'YYYY-MM-DD HH:MM'."""
    return datetime.strptime(text, '%Y-%m-%d %H:%M')


def sessions(since: datetime, until: datetime | None = None, runs: Path = RUNS) -> list[Path]:
    """The serve sessions whose log overlaps the window: written after `since`, started before `until` (by the
    directory's UTC name; `until` naive is local)."""
    if not runs.exists():
        return []
    high = until.astimezone(UTC).strftime('%Y%m%dT%H%M%S') if until is not None else None
    found = []
    for directory in sorted(d for d in runs.iterdir() if d.is_dir() and d.name.startswith('20')):
        log = directory / 'probe.log'
        if not log.exists() or (high is not None and directory.name.split('Z')[0] > high):
            continue
        if datetime.fromtimestamp(log.stat().st_mtime) >= since:
            found.append(directory)
    return found


def newest(runs: Path = RUNS) -> Path | None:
    """The newest session's probe.log, None with no session."""
    dirs = sorted(d for d in runs.iterdir() if d.is_dir() and d.name.startswith('20')) if runs.exists() else []
    return dirs[-1] / 'probe.log' if dirs else None


# --- The loop's legs and state ---------------------------------------------------------------------------------------

# A leg starts: (game number, leg). loop.py:544 Loop.leg `run.say(f'Loop: game {self.games + 1}, {leg}')`; the leg
# names are loop.py's constants (NEXT_GAME 'next game', 'the chests', 'town visit', ...).
# 2026-10-18 15:58:35,969 INFO Macro: Loop: game 1, what is left
LEG = re.compile(r'Macro: Loop: game (\d+), (.+)$')

# The player's KP_6 press reaches the runner. runner.py:357 MacroRunner.request
# `'Macro: request %s, %.0f ms old, while %s'` with the routine `loop`.
# 2026-10-18 11:16:57,355 INFO Macro: request loop, 0 ms old, while loop
REQUEST_LOOP = 'Macro: request loop'

# The loop on / off by KP_6. runner.py:641 / :638 MacroRunner._toggle_loop `self._say('Loop on')`, `('Loop off')`.
# 2026-10-18 15:58:35,938 INFO Macro: Loop on
# 2026-10-18 11:16:57,707 INFO Macro: Loop off
LOOP_ON = 'Macro: Loop on'
LOOP_OFF = 'Macro: Loop off'
# The loop on again by a restart's state. runner.py:817 MacroRunner.poll `self._say('Loop resumed after a restart')`.
# 2026-10-18 15:58:35,937 INFO Macro: Loop resumed after a restart
LOOP_RESUMED = 'Loop resumed'

# A new service's state taken from the restart request: (on|off, the run's kind). runner.py:973 MacroRunner.resume
# `'Macro: resumed after a restart: loop %s, pickup %s, run %s'`.
# 2026-10-18 15:58:35,613 INFO Macro: resumed after a restart: loop on, pickup sure valuables, run Andariel
RESUMED = re.compile(r'Macro: resumed after a restart: loop (on|off)(?:.*, run (.+))?$')
RESUMED_ANY = 'resumed after a restart'
RESUMED_ON = 'resumed after a restart: loop on'
RESUMED_OFF = 'resumed after a restart: loop off'

# The run's kind chosen by a triple KP_6. runner.py:625 MacroRunner._judge_loop_taps
# `self._say(f'Loop run: {self.loop.kind.name}')`. No such line in runs/alt-d up to 2026-10-18 (the test builds one).
KIND = re.compile(r'Macro: Loop run: (.+)$')

# A fight's end and its length (hunt.py `fight`), and the TZ agenda's target and its kind (hunting/choice.py
# `agenda_cleared`): elites.py's activities (engaging, approach, explore, chests, pickup)
FIGHT = re.compile(r'Macro: fight \([^)]*\): \d+ casts? seen in ([\d.]+)s')
TARGET = re.compile(r'Macro: agenda: target .* \((\w+), tier \d+')

# A leg's stop ends the loop: (why). runner.py:700 MacroRunner._loop_stopped `'Macro: loop stopped: %s'`; with a
# valuable on the ground `why` ends in "...: the loop stops here" (runner.py:693).
# 2026-10-18 15:53:19,020 INFO Macro: loop stopped: Ring at (22553, 9560) was not picked up after 2 trips back; Ring
#     lies on the ground: the loop stops here
STOPPED = re.compile(r'Macro: loop stopped: (.*)$')
LOOP_STOPPED = 'loop stopped'
STOPS_HERE = 'stops here'
# A leg's stop recovered: the game is left and the loop goes on: (why). runner.py:695 MacroRunner._loop_stopped
# `'Macro: loop: %s: the game is left and the loop goes on'`.
# 2026-10-18 14:42:14,194 INFO Macro: loop: the waypoint is not under the pointer at any aim: the game is left and the
#     loop goes on
LEFT = re.compile(r'Macro: loop: (.*): the game is left and the loop goes on')
GAME_LEFT = 'game is left'

# A routine's own stop or crash. runner.py:1071-1084 MacroRunner._guarded `'Macro stopped: %s'`; runner.py:1095
# `LOG.exception('Macro failed')` (ERROR, a traceback after it).
# 2026-10-18 15:58:40,662 INFO Macro stopped: Ring was under the pointer at 3 aims and no click picked it up
# 2026-10-17 01:37:07,758 ERROR Macro failed
MACRO_STOPPED = 'Macro stopped'

# The stops, recoveries and errors a game's notes and the events list carry (games.py `read`): the whole matched text.
EVENT = re.compile(
    r'Macro: (loop stopped.*|loop: .*(game is left|stops here).*)|Macro failed.*|Traceback.*|\bERROR\b.*'
)
# What the loop did besides its legs (games.py `did`): the stash (stash.py:372 unload, visit.py:223 stash_stop), a
# repair (repair.py:355), a sale and the keys bought (shop.py:295, :322 restock), the cube (cube.py:397 stash).
# 2026-10-18 16:00:01,499 INFO Macro: stash: by the view: 6 items put in (pages 2,4), 0 dropped, 0 left for the scan,
#     2 openings, 12.6s
# 2026-10-18 16:03:49,890 INFO Macro: cube: 4 of 4 of the loop's items moved in
DID = re.compile(r'Macro: (stash: .*put in.*|repair: the staff .*|shop: sold .*|shop: keys .*|cube: .*moved.*)')
# The lines the live watch says the moment they come (watch.py `NOW`): stops, recoveries, full stacks, sales, repairs,
# the restart's resume, identification, the trade session's report, errors. Producers as for EVENT, DID, FULL, SOLD,
# REPAIRED, IDENTIFIED, VISIT_STOPS; `shop: the item %d is no longer at` shop.py:278 restock; `repair: the stash gold
# went` repair.py:352 and `repair: the cost` repair.py:219/319/323.
NOW = re.compile(
    r'Macro: (loop stopped|loop: .*(game is left|stops here)|stash: the .* stack is full|shop: (sold|could not)'
    r'|repair: the (staff|stash|cost)|resumed after a restart|identify: |shop: the item .* no longer'
    r'|trade session done)'
    r'|Macro failed|Traceback|ERROR'
)
# A game's notes in the live watch (watch.py `NOTE`): the cube's moves, the stash's puts, the shop's keys.
# 2026-10-18 16:00:10,027 INFO Macro: shop: keys 17 -> 17, portals 0 -> 0 (Town Portal from the Sling: none bought),
#     identifies 20 -> 20
NOTE = re.compile(r'Macro: (cube: .*moved|stash: .*put in|shop: keys)')


# --- The ground and the pickups --------------------------------------------------------------------------------------

# The ground census: (quality, base, ' eth', ' socketed', the filter's label, x, y, the rule's word after "taken").
# game/memory.py GameMemory._census `'Macro: ground: %s'` with game/decode.py `census()`: quality, base, ' eth',
# ' socketed', a base's rolls (' 3os ...'), ' "label"' when the label differs from the base, ' at (x, y): ', then
# 'taken (rule)' or 'left'. A base's rolls (`rolls`, after the marks) fold into the base and its marks into it too:
# 'Sacred Rondache 0os', 'Dagger socketed 3os' (the label, which the pickup names, is still read apart).
# 2026-10-18 03:09:41,993 INFO Macro: ground: magic Sacred Rondache 0os "Magic Sacred Rondache" at (5172, 3022):
#     taken (shown)
# 2026-10-18 15:58:35,988 INFO Macro: ground: magic Ring at (22562, 9539): taken (material)
# 2026-10-18 15:59:23,732 INFO Macro: ground: magic Assault Helmet "Magic Assault Helmet" at (22557, 9558): taken
#     (shown)
# 2026-10-18 15:25:55,457 INFO Macro: ground: superior Broad Axe eth socketed at (22577, 9586): left
GROUND = re.compile(
    r'Macro: ground: (\w+) (.+?)( eth)?( socketed)?(?: "([^"]*)")? at \((-?\d+), (-?\d+)\): (?:taken \((\w+)\)|left)'
)

# An item picked up: (its label). pickup.py:584 click `'Macro: picked up %s %.2fs after the click %s pixels from its
# ground, ...'`, and pickup.py:457 late `'Macro: picked up %s %.2fs after the click, late: ...'` (said so for this
# pattern: pickup.py's docstring).
# 2026-10-18 15:58:41,388 INFO Macro: picked up Ring 0.08s after the click (0, -24) pixels from its ground, from 0.7
#     away; under the pointer (4, 1235397469)
# 2026-10-18 15:58:41,402 INFO Macro: picked up Ring 1.18s after the click, late: carried at a later look; at
#     (22553.0, 9560.0)
PICKED = re.compile(r'Macro: picked up (.+?) [\d.]+s after')

# Where a pickup aimed: the press's choice before the click (label, x, y) or its aims after it (label, x, y; groups
# 4-6). pickup.py:707 pick_up `'Macro: pickup: %d drops (%s), belt short %s, life %d/%d; %s'` with the choice
# `f'{label} at ({x:.0f}, {y:.0f})'`; pickup.py:368 take `'Macro: aims for %s (unit %d) at (%.1f, %.1f), ...'`.
# 2026-10-18 15:58:35,995 INFO Macro: pickup: 3 drops (healing, valuable), belt short (0, 0), life 1751/1751; Ring at
#     (22553, 9560)
# 2026-10-18 15:58:40,661 INFO Macro: aims for Ring (unit 1235397469) at (22553.0, 9560.0), 1 wanted and 2 other drops:
#     (0, -24) wanted [flag 0x101 type 4 id 1235397469 tail 0x160016] clicked clicked; ...
AIMED = re.compile(
    r'Macro: (?:pickup: .*?; (.+?) at \((-?\d+), (-?\d+)\)$|aims for (.+?) \(unit \d+\) at \((-?[\d.]+), (-?[\d.]+)\))'
)
# The press's choice alone, unanchored (trade.py: the pickup's start of an item it later names picked up).
PICKUP = re.compile(r'Macro: pickup: .*?; (.+?) at \(')

# A kind whose stash stack is full: (its base name). stash.py:351 unload `'Macro: stash: the %s stack is full'`, and
# visit.py:445 _drops `'Macro: stash: the %s put down: its stack is full and no vendor buys it'` (2026-10-18: the
# pattern took "X put down: its" for the name before, so the kind never counted full).
# 2026-10-18 11:46:36,925 INFO Macro: stash: the Twisted Essence of Suffering stack is full
FULL = re.compile(r'Macro: stash: the (.+?)(?: put down: its)? stack is full')

# Teleport casts (trade.py, speed.py, tz.py count them in the log and the takes' `log` events). teleport.py:1288 hop_to
# `run.say(f'Teleport toward {target.label}: {left:.0f} left after this{charges}')`.
# 2026-10-18 15:58:40,742 INFO Macro: Teleport toward Ring: 0 left after this
TELEPORT = 'Macro: Teleport toward'


# --- Trading: identify, appraise, sell, repair, the town visit -------------------------------------------------------

# An item appraised after identification: (txt when unnamed, quality, base, txt, verdict). runner.py:1579
# MacroRunner.perform.identify_loot `'Macro: identify: appraised %s at (%d, %d): %s'` and junk.py:125 junk
# `said(f'appraised {named(item)} at ({x}, {y}): {verdict}')`.
# 2026-10-18 15:59:48,821 INFO Macro: identify: appraised magic Large Charm (619) at (3, 0): vendor
# 2026-10-17 11:23:48,179 INFO Macro: identify: appraised the item 380 at (3, 0): vendor
APPRAISED = re.compile(r'Macro: identify: appraised (?:the item (\d+)|(\w+) (.+?) \((\d+)\)) at \(\d+, \d+\): (\w+)')
# Items identified: (done, tried). junk.py:111 identify `'Macro: identify: %d of %d items identified'` (the tome) and,
# since the town visit (2026-10-18), cain.py:97 identify_all `'Macro: Cain: %d of %d items identified'`.
# 2026-10-17 11:47:44,494 INFO Macro: identify: 1 of 1 items identified
# 2026-10-18 15:59:47,997 INFO Macro: Cain: 7 of 7 items identified
IDENTIFIED = re.compile(r'Macro: (?:identify|Cain): (\d+) of (\d+) items identified')
# A sale: (txt, gold, what). shop.py:295 restock `'Macro: shop: %s the item %d at (%d, %d)%s: %s'` ('sold' or 'could
# not sell'; `%s` ' for N gold' when the gold was read).
# 2026-10-18 16:00:08,028 INFO Macro: shop: sold the item 658 at (4, 1) for 962 gold: magic Jewel (658)
# 2026-10-17 11:23:55,380 INFO Macro: shop: sold the item 380 at (3, 0)
SOLD = re.compile(r'Macro: shop: sold the item (\d+) at \(\d+, \d+\)(?: for (-?\d+) gold)?(?:: (.+))?$')
# 2026-10-18 12:43:02,825 INFO Macro: shop: could not sell the item 669 at (2, 3): white Twisted Essence of Suffering
#     (669)
UNSOLD = re.compile(r'Macro: shop: could not sell the item (\d+)')
# The carried gold over a visit's sales: (before, after). shop.py:301 restock.
# 2026-10-18 16:00:09,961 INFO Macro: shop: carried gold 500083 -> 507731 after the sales
AFTER = re.compile(r'Macro: shop: carried gold (\d+) -> (\d+) after the sales')
# A repair: (charges before, after, gold before, after). repair.py:355 repair `'Macro: repair: the staff %s -> %s
# charges (of %s), the most worn item %s -> %s, gold %s -> %s'`; before 8accb7d (2026-10-18) without the worn item.
# 2026-10-17 21:46:23,212 INFO Macro: repair: the staff 9 -> 69 charges (of 69), gold 254382 -> 152270
REPAIRED = re.compile(
    r'Macro: repair: the staff (\d+) -> (\S+) charges \(of \d+\)(?:, the most worn item .*?)?, gold (\d+) -> (\d+)'
)
# The town visit's report: each stop's seconds, '-' for a stop not made: (cain, jamella). visit.py:762 visit
# `'Macro: trade session done%s: cube %d items, ..., %.1f s (%s)'`, the stops in visit.py STOPS' order.
# 2026-10-18 16:00:12,913 INFO Macro: trade session done: cube 0 items, block 2x4 free, 9 inventory cells free, junk
#     left 0, keys 17, portals from the Sling, staff ?, ground clear, 27.6 s (cain 3.5, stash 12.7, jamella 8.4,
#     halbu -, walk 2.9)
VISIT_STOPS = re.compile(r'Macro: trade session done.*\(cain (\S+), stash \S+, jamella (\S+), halbu \S+, walk \S+\)$')


# --- The Andariel run (andy.py) --------------------------------------------------------------------------------------

# terror/bosses.py:124 BossTracker.apply `'Boss kill: %s, %s this launch'`.
# 2026-10-18 15:59:24,412 INFO Boss kill: Andariel, 284 this launch
KILL = re.compile(r'Boss kill: Andariel, \d+ this launch')
# A combat take opened: (take, area). takes/record.py:767 Recorder.open `'Combat take %s opened in area %d'`.
# 2026-10-18 15:58:36,182 INFO Combat take 20261018T125836Z-37 opened in area 37
OPENED = re.compile(r'Combat take (\S+) opened in area (\d+)')
# The next game made: (its name). routines.py:500 create_next_game `run.say(f'Creating {name}')`.
# 2026-10-18 15:58:42,386 INFO Macro: Creating cyberr4
CREATING = re.compile(r'Macro: Creating (\S+)')
# routines.py:554 create_next_game `'Macro: game loaded %.2fs after Enter'`.
# 2026-10-18 15:58:49,111 INFO Macro: game loaded 5.15s after Enter
GAME_LOADED = 'Macro: game loaded'
# routines.py:420 leave_game `run.say('Save and Exit')`: the line ends with it.
# 2026-10-18 15:58:41,505 INFO Macro: Save and Exit
SAVE_AND_EXIT = 'Macro: Save and Exit'
# The stairs' press on the Andariel route: macros/route.py:86 and routes/model.py:51 (`enter {mark}`).
# 2026-10-18 15:59:04,350 INFO Macro: route Andariel: enter Next level
ROUTE_ENTER = 'Macro: route Andariel: enter Next level'
# hunt.py:1759 `run.say(f'Run: {line}')`.
# 2026-10-18 15:58:57,453 INFO Macro: Run: to Next level, clearing the way
RUN_TO_NEXT = 'Macro: Run: to Next level'
# The stairs' mark: (units from it). teleport.py:715 walk_into.
# 2026-10-18 15:59:04,365 INFO Macro: door Next level marked at (22592.5, 6517.5); the character at (22591.5, 6522.5),
#     5.1 from the mark; entry remembered -1.0, +5.0 from the mark
DOOR_MARKED = re.compile(r'Macro: door Next level marked at .*?; the character at .*?, ([\d.]+) from the mark')
# Through the stairs: (seconds, units walked). teleport.py:772 walk_into.press.
# 2026-10-18 15:59:04,641 INFO Macro: door Next level: in after 0.28s, walked 0.0 from (22591.5, 6522.5) to (22591.5,
#     6522.5); the entry at -1.0, +5.0 from the mark, 5.1 away (remembered)
DOOR_IN = re.compile(r'Macro: door Next level: in after ([\d.]+)s, walked ([\d.]+) from')
# A level run's pace: (units, seconds, jumps, walks). travel.py:1446 Travel.paced.
# 2026-10-18 15:59:04,238 INFO Macro: leg time: level run (at Next level: going through takes a press): 0 units in
#     6.6s since its first leg, 0.0 units/s; 0 jumps, 0 walks; key to key none
LEG_TIME = re.compile(r'Macro: leg time: level run .*?: (\d+) units in ([\d.]+)s since .*?; (\d+) jumps, (\d+) walks')
