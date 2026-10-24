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
# The runner's `_say` (runner.py MacroRunner._say: `LOG.info('Macro: %s', text)`): every `run.say(...)` line has
# this prefix, as has every `LOG.info('Macro: ...')`
SAID = 'Macro: '


def stamp(line: str) -> datetime | None:
    """The line's local date and time, None for a line without one (a traceback's). `fromisoformat` behind a shape
    check reads what `strptime(STAMP_FORMAT)` reads, ~30x faster: the tools stamp millions of lines a week."""
    if len(line) < STAMP_LEN or line[10] != ' ' or line[19] != ',':
        return None
    try:
        return datetime.fromisoformat(line[:STAMP_LEN])
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

# A leg starts: (game number, leg). loop.py Loop.leg `run.say(f'Loop: game {self.games + 1}, {leg}')`; the leg
# names are loop.py's constants (NEXT_GAME 'next game', 'the chests', 'town visit', ...).
# 2026-10-18 15:58:35,969 INFO Macro: Loop: game 1, what is left
LEG = re.compile(r'Macro: Loop: game (\d+), (.+)$')
# A leg that goes on: a teleport landed, a fight's kills, a pickup (watch.py: no STALL while these come, 2026-10-19)
PROGRESS = re.compile(r'Macro: (teleport aimed at .*; landed at|.*: [1-9]\d* down in \d+ casts|picked up )')
# The loop's own wait before its next leg (loop.py `leg`: the next terror zone's, up to 30 min): no STALL in it
# 2026-10-20 03:34:19,640 INFO Macro: loop: waiting 1560 s before the next leg (the next terror zone)
WAITING = re.compile(r'Macro: loop: waiting (\d+) s before the next leg')

# The player's KP_6 press reaches the runner. runner.py MacroRunner.request
# `'Macro: request %s, %.0f ms old, while %s'` with the routine `loop`.
# 2026-10-18 11:16:57,355 INFO Macro: request loop, 0 ms old, while loop
REQUEST_LOOP = 'Macro: request loop'

# The loop on / off by KP_6. runner.py MacroRunner._toggle_loop `self._say('Loop on')`, `('Loop off')`.
# 2026-10-18 15:58:35,938 INFO Macro: Loop on
# 2026-10-18 11:16:57,707 INFO Macro: Loop off
LOOP_ON = 'Macro: Loop on'
LOOP_OFF = 'Macro: Loop off'
# The loop on again by a restart's state. running/watch.py poll `self._say('Loop resumed after a restart')`.
# 2026-10-18 15:58:35,937 INFO Macro: Loop resumed after a restart
LOOP_RESUMED = 'Loop resumed'

# A new service's state taken from the restart request: (on|off, the run's kind). runner.py MacroRunner.resume
# `'Macro: resumed after a restart: loop %s, pickup %s, run %s'`.
# 2026-10-18 15:58:35,613 INFO Macro: resumed after a restart: loop on, pickup sure valuables, run Andariel
RESUMED = re.compile(r'Macro: resumed after a restart: loop (on|off)(?:.*, run (.+))?$')
RESUMED_ANY = 'resumed after a restart'
RESUMED_ON = 'resumed after a restart: loop on'
RESUMED_OFF = 'resumed after a restart: loop off'

# A restart in the middle of a game (restart.py --when town|safe; macros/midgame.py, 2026-10-21). The service armed it:
# runner.py MacroRunner.hold_restart `'Macro: loop: a restart waits for a safe point (%s)'` (town|safe); dropped:
# `cancel_restart` `'Macro: loop: the restart no longer waits for a safe point'`.
RESTART_HELD = 'a restart waits for a safe point'
RESTART_DROPPED = 'the restart no longer waits for a safe point'
# The loop stands at one, the service restarts at its next tick: (where, the game). loop.py Loop.hold_at_safe_point
# `'Macro: loop: safe point: %s, %s: the loop stands for the restart'`; not yet: (why), said when it changes.
# No such line in runs/alt-d up to 2026-10-21 14:50 (the test builds them).
SAFE_POINT = re.compile(r'Macro: loop: safe point: (.+?), (.+): the loop stands for the restart$')
NOT_SAFE = re.compile(r'Macro: loop: no safe point for the restart yet: (.+)$')
# restart.py --when trip (macros/midgame.py TRIP, 2026-10-24): the field level's safe moment, the loop's Town Portal
# for the restart: (where, the game). loop.py Loop.begin_restart_trip `'Macro: loop: safe moment for the restart: %s,
# %s: Town Portal to town for it, back through it after'`; the new service's return, `Loop.back_after_restart`
# `'Macro: loop: back through the portal left for the restart'`, and with the portal not taken (why) the loop's own way
# back from town. No such line in runs/alt-d up to 2026-10-24 13:40 (the test builds them).
TRIP_BEGUN = re.compile(r'Macro: loop: safe moment for the restart: (.+?), (.+): Town Portal to town for it')
TRIP_BACK = 'back through the portal left for the restart'
TRIP_NO_PORTAL = re.compile(
    r"Macro: loop: the portal left for the restart is not taken \((.+)\): the loop's own way back from town$"
)
# The new service took the game up at its first leg there: (the game). macros/midgame.py restore
# `'Macro: loop: game %s taken up after a restart: %.0f s into it, ...'`.
CARRIED = re.compile(r'Macro: loop: game (.+?) taken up after a restart: (-?\d+) s into it')

# The run's kind chosen by a triple KP_6 or the `loop-kind` request, or taking at the next game: runner.py
# `MacroRunner._say_kind`, loop.py `Loop.leg`. No such line in runs/alt-d up to 2026-10-18 (the test builds one).
KIND = re.compile(r'Macro: Loop run: (.+)$')

# A fight's end and its length (hunt.py `fight`), and the TZ agenda's target and its kind (hunting/choice.py
# `agenda_cleared`): elites.py's activities (engaging, approach, explore, chests, pickup)
FIGHT = re.compile(r'Macro: fight \([^)]*\): \d+ casts? seen in ([\d.]+)s')
TARGET = re.compile(r'Macro: agenda: target .* \((\w+), tier \d+')

# A leg's stop ends the loop: (why). running/recovery.py _loop_stopped `'Macro: loop stopped: %s'`; with a
# valuable on the ground `why` ends in "...: the loop stops here" (running/recovery.py).
# 2026-10-18 15:53:19,020 INFO Macro: loop stopped: Ring at (22553, 9560) was not picked up after 2 trips back; Ring
#     lies on the ground: the loop stops here
STOPPED = re.compile(r'Macro: loop stopped: (.*)$')
LOOP_STOPPED = 'loop stopped'
STOPS_HERE = 'stops here'
# A leg's stop recovered: the game is left and the loop goes on: (why). running/recovery.py _loop_stopped
# `'Macro: loop: %s: the game is left and the loop goes on'`.
# 2026-10-18 14:42:14,194 INFO Macro: loop: the waypoint is not under the pointer at any aim: the game is left and the
#     loop goes on
LEFT = re.compile(r'Macro: loop: (.*): the game is left and the loop goes on')
GAME_LEFT = 'game is left'
# A door no click takes on a terror zone's way on: its trip skipped, the game not left (no GAME_LEFT in it), the zone
# goes on. tzloop.py skip_door `'Macro: loop: %s: the trip to %s is skipped, the game is not left and the zone goes on'`
# (SKIP_DOOR, 2026-10-21). The EVENT and NOW lines carry it.
# 2026-10-21 09:00:00,000 INFO Macro: loop: no click took Crypt: the trip to Crypt is skipped, the game is not left and
#     the zone goes on

# Zone navigation (macros/zonenav.py, the switch `ACTS`): a level's verdict, the graph once a game, the old rule's
# verdicts said (stage 0). tzloop.py zone_choose `'Macro: zone: %s'`, zone_judged `'Macro: zone: graph %s: %s; ...'`,
# zone_note `'Macro: zone: done by the old rule: %s'`.
# 2026-10-21 10:00:00,000 INFO Macro: zone: Upper Kurast (81) cleared, without [97]
ZONE = re.compile(r'Macro: zone: (.*)$')
# A child of the zone that cannot be done in this game: (the level, why). tzloop.py zone_choose's verdict
# `'Macro: zone: %s'` with zonenav.py `said`: `<name> (<area>) blocked: <why>`; a door no click takes, tzloop.py
# zone_door `'Macro: zone: %s: %s blocked, %s goes on'` (no GAME_LEFT: the zone goes on). EVENT and NOW carry both.
# 2026-10-21 10:00:00,000 INFO Macro: zone: Forgotten Reliquary (96) blocked: its map was never read in 2 runs
# 2026-10-21 10:00:00,000 INFO Macro: zone: no click took Forgotten Temple: Forgotten Temple blocked, Upper Kurast goes
#     on
# Also a way in made over zonenav.py WAY_TRIES legs with no arrival (tzloop.py way_spent) and a child skipped for the
# game's time (TIME_BUDGET, tzloop.py zone_budget), both `'Macro: zone: %s (%d) blocked: %s'` (2026-10-21).
# 2026-10-21 14:00:00,000 INFO Macro: zone: Kurast Causeway (82) blocked: its way in from Upper Kurast was made 6 times
#     with no arrival
ZONE_BLOCKED = re.compile(r'Macro: zone: (?:.*: )?(.+?)(?: \(\d+\))? blocked(?:: (.*)|, .* goes on)$')

# A drop no click took that the loop keeps no game for, given up for the game (no GAME_LEFT: the press goes on);
# pickup.py give_up `'Macro: pickup: %s at (%.0f, %.0f) given up for this game (%s); the game is kept and the press
# goes on'` (GIVE_UP_CHEAP, 2026-10-21). A stop answered by keeping the game: running/recovery.py _loop_stopped
# `'Macro: loop: %s: the game is kept (%s): the leg is made again'` (stops.py KEEP). EVENT and NOW carry both.
# 2026-10-21 14:00:00,000 INFO Macro: pickup: a super healing potion at (4769, 2633) given up for this game (a super
#     healing potion was under the pointer at 3 aims and no click picked it up); the game is kept and the press goes on

# A Worldstone Shard over the limit (its stack at the cap) used in an act kind's game after the kind's own (actloop.py
# OVERFLOW, 2026-10-21): (shard, stack, act, played after); refused or stopped: (shard, stack, why, act). actloop.py
# overflow `'Macro: act: %s shard over the limit (%d)%s: act %d terrorized too, played after %s'`, `'... (%d): refused
# (%s): act %d not played; the shard %s'`, `'... (%d): not used (%s): act %d not played'`. DID and NOW carry them.
# 2026-10-21 15:40:00,000 INFO Macro: act: Northern shard over the limit (99): act 5 terrorized too, played after act 3
OVERFLOW = re.compile(
    r'Macro: act: (\w+) shard over the limit \((\d+)\)(?:, a carried one)?: '
    r'(?:act (\d) terrorized too, played after (.+)|(?:refused|not used) \((.*?)\): act (\d) not played)'
)

# A routine's own stop or crash. runner.py MacroRunner._guarded `'Macro stopped: %s'`; runner.py
# `LOG.exception('Macro failed')` (ERROR, a traceback after it).
# 2026-10-18 15:58:40,662 INFO Macro stopped: Ring was under the pointer at 3 aims and no click picked it up
# 2026-10-17 01:37:07,758 ERROR Macro failed
MACRO_STOPPED = 'Macro stopped'

# The merc lost or the belt low on healing potions: a town trip at the first safe moment, a recovery of its own
# (macros/merc.py, 2026-10-21; the player: "we have lost merc -> probably better retreat to the town and refill hp
# potions in the belt"). merc.py `trip` `'Macro: merc lost: a town trip to refill the belt and revive the merc (%s)'`,
# `'Macro: belt low: a town trip to refill the belt (%s; %s)'`; `revive` `'Macro: merc: carried gold %s does not
# cover the revive ...'`. EVENT and NOW carry them; NOW also the death read (`MercWatch.see` `'Macro: merc: dead:
# ...'`), the wait for the safe moment and the revive (`'Macro: merc: revived at Tyrael ...'`, `'... not revived'`).
# 2026-10-21 19:40:00,000 INFO Macro: merc lost: a town trip to refill the belt and revive the merc (no hostile within
#     30)

# The stops, recoveries and errors a game's notes and the events list carry (games.py `read`): the whole matched text.
EVENT = re.compile(
    r'Macro: (loop stopped.*|loop: .*(game is left|game is kept|stops here|trip to .* is skipped).*|zone: .* blocked.*'
    r'|pickup: .* given up for this game.*'
    r'|merc lost: a town trip.*|belt low: a town trip.*|merc: carried gold .* does not cover the revive.*)'
    r'|Macro failed.*|Traceback.*|\bERROR\b.*'
)
# What the loop did besides its legs (games.py `did`): the stash (stash.py unload, visit.py stash_stop), a
# repair (repair.py), a sale and the keys bought (shop.py restock), the cube (cube.py stash), a gamble session
# (gamble.py `gamble`, GAMBLED).
# 2026-10-18 16:00:01,499 INFO Macro: stash: by the view: 6 items put in (pages 2,4), 0 dropped, 0 left for the scan,
#     2 openings, 12.6s
# 2026-10-18 16:03:49,890 INFO Macro: cube: 4 of 4 of the loop's items moved in
DID = re.compile(
    r'Macro: (stash: .*put in.*|repair: the staff .*|shop: sold .*|shop: keys .*|cube: .*moved.*'
    r'|gamble: session done.*|shop: potions: .*|act: .* shard over the limit.*)'
)
# The lines the live watch says the moment they come (watch.py `NOW`): stops, recoveries, full stacks, sales, repairs,
# the restart's resume (and the game taken back from its record after it, the zone's facts with it: midgame.py
# `restore` CARRIED, 2026-10-22; before it tzloop.py zone_resume's `'Macro: zone: %s resumed after a restart'`),
# identification, the trade session's report, errors.
# Producers as for EVENT, DID, FULL, SOLD,
# REPAIRED, IDENTIFIED, VISIT_STOPS; `shop: the item %d is no longer at` shop.py restock; `repair: the stash gold
# went` repair.py and `repair: the cost` repair.py; a gamble session's end and a price no gold stat paid (gamble.py
# `gamble`, `Session._unread_price`, a WARNING).
NOW = re.compile(
    r'Macro: (loop stopped|loop: .*(game is left|game is kept|stops here|trip to .* is skipped)|zone: .* blocked'
    r'|pickup: .* given up for this game'
    r'|stash: the .* stack is full'
    r'|shop: (sold|could not)|repair: the (staff|stash|cost)|resumed after a restart'
    r'|loop: game .* taken up after a restart|zone: .* resumed after a restart'
    r'|identify: '
    r'|shop: the item .* no longer'
    r'|trade session done|gamble: session done|gamble: .*gambling stopped|act: .* shard over the limit'
    r'|merc lost: |belt low: |merc: (dead|revived|not revived|carried gold))'
    r'|Macro failed|Traceback|ERROR'
)
# A game's notes in the live watch (watch.py `NOTE`): the cube's moves, the stash's puts, the shop's keys and healing
# potions (shop.py `_potions`, BUY_POTIONS 2026-10-21).
# 2026-10-18 16:00:10,027 INFO Macro: shop: keys 17 -> 17, portals 0 -> 0 (Town Portal from the Sling: none bought),
#     identifies 20 -> 20
# 2026-10-21 14:00:00,000 INFO Macro: shop: potions: belt short 5 -> 0, bought 5 Super Healing Potion for 2250 gold
NOTE = re.compile(r'Macro: (cube: .*moved|stash: .*put in|shop: keys|shop: potions)')


# --- TZ leveling's experience (games.py, watch.py) -------------------------------------------------------------------

# A terror zone game's experience at its Save and Exit: (game, gain, level, to the next or None, an hour since the loop
# turned on or '?', games over). loop.py Loop.leave with experience.py Ledger.game_over `f'experience: game {number}:
# ...'`, said `'Macro: %s'` (loop.py say_experience); `, up N` after the level when it rose. 'experience: game N:
# unread' when the stats were not read. New on 2026-10-19 21:37 (the player: "we should log experience in tz
# leveling"); the test builds the line.
# 2026-10-19 22:00:00,000 INFO Macro: experience: game 3: +1,234,567 (level 94, 130,000,000 to the next), 6,000,000 an
#     hour over 3 games
EXPERIENCE_GAME = re.compile(
    r'Macro: experience: game (\d+): ([+-][\d,]+) \(level (\d+)(?:, up \d+)?(?:, ([\d,]+) to the next)?\), '
    r'(-?[\d,]+|\?) an hour over (\d+) games?'
)
# A terror zone level left: (its name, gain, seconds, level). experience.py Ledger._level `f'experience: {name}: ...'`.
# 2026-10-19 21:58:10,000 INFO Macro: experience: The Chaos Sanctuary: +912,000 in 140s (level 94)
# The seven Tal Rasha's Tombs are numbered (levels/presets.py `numbered_name`, 2026-10-20: the Canyon's tour of them):
# 2026-10-20 14:10:00,000 INFO Macro: experience: Tal Rasha's Tomb 4: +410,000 in 52s (level 94)
EXPERIENCE_LEVEL = re.compile(r'Macro: experience: (?!game \d+:)(.+?): ([+-][\d,]+) in (\d+)s \(level (\d+)\)')


def amount(text: str) -> int:
    """A number as the experience lines write it: '+1,234,567' -> 1234567."""
    return int(text.replace(',', ''))


# --- The safety among exploding dolls (combat/threats/dolls.py DOLL_LAND, off since 2026-10-21 ~14:55) ----------------

# Jump landings near a live doll left out, said once a goal: (how many, the goal, what was done). safety.py
# Safety.dolls_waited `'Macro: safety: dolls: %d landing%s near a live doll left out (%s); %s'`.
# 2026-10-21 14:40:15,416 INFO Macro: safety: dolls: 1 landing near a live doll left out (full clear: a group of 7); a
#     jump of 9 to (17856.9, 6549.7), safe approach
DOLLS_LEFT_OUT = re.compile(r'Macro: safety: dolls: (\d+) landings? near a live doll left out \((.+?)\); (.+)$')
# The asked move's bar lifted after dolls.PATIENCE with nothing in reach: (the goal). The same function's
# `'Macro: safety: dolls: %s held %.0f s with nothing in reach: its landing is no longer barred; %s'`.
# 2026-10-21 14:40:51,637 INFO Macro: safety: dolls: full clear: the elite 216 (510263862) held 4 s with nothing in
#     reach: its landing is no longer barred; a jump of 24 to (17818.0, 6686.7), toward the goal
DOLLS_PATIENT = re.compile(r'Macro: safety: dolls: (.+?) held \d+ s with nothing in reach: its landing is no longer')


# --- The pets (builds/warlock/pets.py, 2026-10-21) ------------------------------------------------------------------

# A pet dead: (its name, its unit, its life at the look). pets.py PetWatch.say_lost `'Macro: pet: %s (%d) lost at
# %d/%d, %d/%d before%s'`: the bound demon always, a Defiler only when it was hurt before (not one Consume took). The
# watch says `PET LOST` for the bound demon (the player, 2026-10-21 ~15:45: "we have lost our daemon").
# 2026-10-21 15:41:39,800 INFO Macro: pet: bound Urdar (2147553209) lost at 0/128, 1/128 before; the last Engorge 3.2s
#     before
PET_LOST = re.compile(r'Macro: pet: (bound .+?|Defiler|\w+) \((\d+)\) lost at (\d+)/\d+')
BOUND_WORD = 'bound '  # the bound demon's name begins so (pets.py `name_of`)
# A pet's life falling fast or under a share: (name, life, why, what is done). pets.py PetWatch.tell `'Macro: pet: %s
# %d/%d, %s: %s'`.
# 2026-10-21 15:41:30,600 INFO Macro: pet: bound Urdar 73/128, -55 in 1.4s: Engorge now
PET_DANGER = re.compile(r'Macro: pet: (.+?) (\d+)/\d+, (.+): (Engorge now|no Engorge now)$')


# --- Battle Orders through a fight (macros/cta.py REBUFF, 2026-10-22) ----------------------------------------------

# What the rebuff did: (the state: 'N s left', 'age not known' or 'expired[ N s ago]'; the action: 'retreat', 'cast in
# place' or 'a retreat first'). cta.py say_orders `'Macro: %s: %s: %s'` with ORDERS_SAID 'buff: Battle Orders' (a run
# out in a fight), safety.py Safety.rebuff_chosen `'Macro: buff: Battle Orders: %s: retreat to (%.1f, %.1f), ...'` and
# buffs.py Buffs.cast `'Macro: buff: %s: %s: cast again now'` with cta.py renew_orders' reason (a renewal in a fight).
# Not yet in a real log (2026-10-22): the lines as the production formats make them.
# 2026-10-22 12:00:00,000 INFO Macro: buff: Battle Orders: 6 s left: retreat to (15062.2, 5630.1), 18 clear of the
#     hostiles, to cast it there (1 of 3)
# 2026-10-22 12:00:00,900 INFO Macro: buff: Battle Orders: 6 s left: cast in place (nothing within 10, at the rebuff
#     landing): cast again now
# 2026-10-22 12:00:05,000 INFO Macro: buff: Battle Orders: expired 0.4 s ago: a retreat first (a hostile within 10)
ORDERS = re.compile(
    r'Macro: buff: Battle Orders: (\d+ s left|age not known|expired(?: [\d.]+ s ago)?): (retreat|cast in place|a '
    r'retreat first)'
)

# --- The anomalies in a take (anomalies.py, 2026-10-21) -------------------------------------------------------------

# The player, 2026-10-21 ~21:08: "monitor all time that we weren't moving/killing/doing something"; anomalies.py reads
# the take's own `log` events (the same lines, without the stamp) and these from probe.log.
# A take closed: (take, why). takes/record.py Recorder.close `'Combat take %s closed (%s): %s'`; watch.py runs the
# detector on it.
# 2026-10-21 20:45:08,925 INFO Combat take 20261021T174501Z-131 closed (changed level): {'frames': 176, ...}
TAKE_CLOSED = re.compile(r'Combat take (\S+) closed \(([^)]*)\)')
# The run waits for a Herald where it comes (no IDLE in it, up to its N s): (seconds). hunt.py's omens
# `'Macro: run: a Herald comes at (%.1f, %.1f) in 5 s: the run waits for it there'`.
# 2026-10-21 18:40:00,000 INFO Macro: run: a Herald comes at (5120.5, 4310.5) in 5 s: the run waits for it there
HERALD_WAIT = re.compile(r'Macro: run: a Herald comes at \(.*?\) in (\d+) s: the run waits for it there')
# The Throne's wave wait (no IDLE after it in the Throne): the hall clear, or the stand at Lister's place.
# hunting/throne.py `waves.say('the hall is clear: waiting for the waves at the Throne')`, WAVES_STAND's goal.
# 2026-10-21 19:12:00,000 INFO Macro: run: Throne of Destruction: the hall is clear: waiting for the waves at the Throne
# 2026-10-21 19:12:01,000 INFO Macro: At Lister the Tormentor: the stand for the waves
WAVES = re.compile(r'Macro: (?:run: .*waiting for the waves|.*: the stand for the waves)')
# A strike aimed at a unit, or its line through it: (what: monster|elite, its class, its unit, its life of 128).
# The fight's strike line (`<skill> (right click) at <the unit>, N/128`) and hunt.py's `'Macro: line through %s, %s,
# %.1f away, ...'`.
# 2026-10-21 18:27:48,375 INFO Macro: Echoing Strike (right click) at the monster 142 (1181201124), 126/128
# 2026-10-21 18:27:57,919 INFO Macro: Echoing Strike (right click) at the elite 99 (730608447), 23/128
# 2026-10-21 20:57:10,800 INFO Macro: line through the monster 673 (719323509), 27/128, 19.4 away, focal (...)
STRIKE = re.compile(r'Macro: (?:[A-Z][\w ]*? \(\w+ click\) at|line through) the (\w+) (\d+) \((\d+)\), (\d+)/128')
# The agenda's elite target (a pack or a Herald's leader): (class, unit, tier). hunting/choice.py.
# 2026-10-19 09:27:40,514 INFO Macro: agenda: target the elite 279 (1817783950) (kill, tier 4, 2 leaders known here)
ELITE_TARGET = re.compile(r'Macro: agenda: target the elite (\d+) \((\d+)\) \(\w+, tier (\d+)')
# A jump cast: (the skill). The skill's press `'Macro: %s on %s, player mode %d'` (Teleport on t, Blade Warp on s).
# 2026-10-21 20:57:07,300 INFO Macro: Teleport on t, player mode 1
JUMP_CAST = re.compile(r'Macro: (Teleport|Blade Warp) on \w+, player mode \d+')
# A jump's reason: the goal it went toward (folded), a better place in the fight, keeping range from a pack (and why).
# teleport.py hop_to `'Teleport toward {label}: {left} left after this'`, the Blade Warp's twin, hunt.py's run line,
# pack.py's `'Macro: Pack: keeping range: %s'`.
# 2026-10-21 20:57:12,300 INFO Macro: Teleport toward full clear: a group of 13: 19 left after this
# 2026-10-21 20:57:13,400 INFO Macro: run: a better place in the fight with 1 of 62 hostiles in reach, from (...)
# 2026-10-21 18:27:49,373 INFO Macro: Pack: keeping range: extra fast: 2 of the pack on the character within 18 (...)
JUMP_REASON = re.compile(
    r'Macro: (?:(?:Teleport|Blade Warp) toward (.+?)(?:: \d+ left after this.*)?$|run: (a better place) in the fight'
    r'|Pack: (keeping range)(?:: ([a-z ]+):)?)'
)
# The lines that name no cause for a still or a long fight (the census, gold, the shadow verdicts, the strike's line,
# the minute's rate, the keys' echo, the level's experience): left out of `cause?:`
NOISE = re.compile(
    r'Macro: (?:ground: |gold pile |loot: shadow|line through |Last minute|Teleport$|Blade Warp$|\w[\w ]* on \w, player'
    r' mode|experience: |shrine: |door .* marked|teleport aimed at |Blade Warp aimed at )'
)
NUMBER = re.compile(r'-?\d+(?:\.\d+)?')  # a log line's numbers, folded to N for its kind
PLACE = re.compile(r' ?(?:at |from )?\(N(?:, N)*\)')  # a folded place or unit, '(N, N)', left out of the kind


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

# An item of the loop's own put down in town (cube.py `drop_item`, visit.py DROP_CAPPED_JUNK since 2026-10-20): the
# census sees it on the ground a few lines before this one, and it is no miss.
# 2026-10-20 09:23:02,883 INFO Macro: inventory: 537 (3504973515) at (3, 3) dropped in town: the gold is at its cap and
#     no sale is made
TOWN_DROP = re.compile(r'Macro: inventory: \d+ \(\d+\) at \(\d+, \d+\) dropped in town')

# An item the loop picked for the field identify, identified and put down at its feet (loot/api.py `Field`, M4 since
# 2026-10-20; cube.py `drop_item`): the census sees it lying there just after this line, and it is no miss either. Its
# decision is the line before it (`Macro: loot: field: <item> (unit N): drop K8 ...`).
# 2026-10-20 12:00:00,000 INFO Macro: inventory: 447 (1728653239) at (3, 0) dropped in the field: K8 worthless (no
#     price, worthless, verdict vendor), no want
FIELD_DROP = re.compile(r'Macro: inventory: \d+ \(\d+\) at \(\d+, \d+\) dropped in the field')
# The field identify's summary (loot/api.py `Field.settle`): '<site>: N identified, D dropped, K kept[, W wait ...]'
# 2026-10-20 12:00:00,100 INFO Macro: loot: field: Town Portal: 1 identified, 1 dropped, 0 kept
FIELD_SETTLED = re.compile(r'Macro: loot: field: (.+?): (\d+) identified, (\d+) dropped, (\d+) kept')

# An item picked up: (its label). pickup.py click `'Macro: picked up %s %.2fs after the click %s pixels from its
# ground, ...'`, and pickup.py late `'Macro: picked up %s %.2fs after the click, late: ...'` (said so for this
# pattern: pickup.py's docstring).
# 2026-10-18 15:58:41,388 INFO Macro: picked up Ring 0.08s after the click (0, -24) pixels from its ground, from 0.7
#     away; under the pointer (4, 1235397469)
# 2026-10-18 15:58:41,402 INFO Macro: picked up Ring 1.18s after the click, late: carried at a later look; at
#     (22553.0, 9560.0)
PICKED = re.compile(r'Macro: picked up (.+?) [\d.]+s after')

# Where a pickup aimed: the press's choice before the click (label, x, y) or its aims after it (label, x, y; groups
# 4-6). pickup.py pick_up `'Macro: pickup: %d drops (%s), belt short %s, life %d/%d; %s'` with the choice
# `f'{label} at ({x:.0f}, {y:.0f})'`; pickup.py take `'Macro: aims for %s (unit %d) at (%.1f, %.1f), ...'`.
# 2026-10-18 15:58:35,995 INFO Macro: pickup: 3 drops (healing, valuable), belt short (0, 0), life 1751/1751; Ring at
#     (22553, 9560)
# 2026-10-18 15:58:40,661 INFO Macro: aims for Ring (unit 1235397469) at (22553.0, 9560.0), 1 wanted and 2 other drops:
#     (0, -24) wanted [flag 0x101 type 4 id 1235397469 tail 0x160016] clicked clicked; ...
AIMED = re.compile(
    r'Macro: (?:pickup: .*?; (.+?) at \((-?\d+), (-?\d+)\)$|aims for (.+?) \(unit \d+\) at \((-?[\d.]+), (-?[\d.]+)\))'
)
# The press's choice alone, unanchored (trade.py: the pickup's start of an item it later names picked up).
PICKUP = re.compile(r'Macro: pickup: .*?; (.+?) at \(')

# A kind whose stash stack is full: (its base name). stash.py unload `'Macro: stash: the %s stack is full'`, and
# visit.py _drops `'Macro: stash: the %s put down: its stack is full and no vendor buys it'` (2026-10-18: the
# pattern took "X put down: its" for the name before, so the kind never counted full).
# 2026-10-18 11:46:36,925 INFO Macro: stash: the Twisted Essence of Suffering stack is full
FULL = re.compile(r'Macro: stash: the (.+?)(?: put down: its)? stack is full')
# The visit's own put-down of a full stack's material (visit.py `_drops`): the census sees it lying in town after this
# line, a drop of the loop's own like TOWN_DROP's (games.py, watch.py; since 2026-10-22 the tools keep no list of full
# kinds of their own: the service's stash snapshot alone, game/stash.py)
FULL_DOWN = re.compile(r'Macro: stash: the (.+?) put down: its stack is full')

# Teleport casts (trade.py, speed.py, tz.py count them in the log and the takes' `log` events). teleport.py hop_to
# `run.say(f'Teleport toward {target.label}: {left:.0f} left after this{charges}')`.
# 2026-10-18 15:58:40,742 INFO Macro: Teleport toward Ring: 0 left after this
TELEPORT = 'Macro: Teleport toward'


# --- Trading: identify, appraise, sell, repair, the town visit -------------------------------------------------------

# An item appraised after identification: (txt when unnamed, quality, base, txt, verdict). running/legs.py
# _identify_loot `'Macro: identify: appraised %s at (%d, %d): %s'` and junk.py junk
# `said(f'appraised {named(item)} at ({x}, {y}): {verdict}')`.
# 2026-10-18 15:59:48,821 INFO Macro: identify: appraised magic Large Charm (619) at (3, 0): vendor
# 2026-10-17 11:23:48,179 INFO Macro: identify: appraised the item 380 at (3, 0): vendor
APPRAISED = re.compile(r'Macro: identify: appraised (?:the item (\d+)|(\w+) (.+?) \((\d+)\)) at \(\d+, \d+\): (\w+)')
# Items identified: (done, tried). junk.py identify `'Macro: identify: %d of %d items identified'` (the tome) and,
# since the town visit (2026-10-18), cain.py identify_all `'Macro: Cain: %d of %d items identified'`.
# 2026-10-17 11:47:44,494 INFO Macro: identify: 1 of 1 items identified
# 2026-10-18 15:59:47,997 INFO Macro: Cain: 7 of 7 items identified
IDENTIFIED = re.compile(r'Macro: (?:identify|Cain): (\d+) of (\d+) items identified')
# A sale: (txt, gold, what). shop.py restock `'Macro: shop: %s the item %d at (%d, %d)%s: %s'` ('sold' or 'could
# not sell'; `%s` ' for N gold' when the gold was read).
# 2026-10-18 16:00:08,028 INFO Macro: shop: sold the item 658 at (4, 1) for 962 gold: magic Jewel (658)
# 2026-10-17 11:23:55,380 INFO Macro: shop: sold the item 380 at (3, 0)
SOLD = re.compile(r'Macro: shop: sold the item (\d+) at \(\d+, \d+\)(?: for (-?\d+) gold)?(?:: (.+))?$')
# 2026-10-18 12:43:02,825 INFO Macro: shop: could not sell the item 669 at (2, 3): white Twisted Essence of Suffering
#     (669)
UNSOLD = re.compile(r'Macro: shop: could not sell the item (\d+)')
# The carried gold over a visit's sales: (before, after). shop.py restock.
# 2026-10-18 16:00:09,961 INFO Macro: shop: carried gold 500083 -> 507731 after the sales
AFTER = re.compile(r'Macro: shop: carried gold (\d+) -> (\d+) after the sales')
# A repair: (charges before, after, gold before, after). repair.py repair `'Macro: repair: the staff %s -> %s
# charges (of %s), the most worn item %s -> %s, gold %s -> %s'`; before 8accb7d (2026-10-18) without the worn item.
# 2026-10-17 21:46:23,212 INFO Macro: repair: the staff 9 -> 69 charges (of 69), gold 254382 -> 152270
REPAIRED = re.compile(
    r'Macro: repair: the staff (\d+) -> (\S+) charges \(of \d+\)(?:, the most worn item .*?)?, gold (\d+) -> (\d+)'
)
# The town visit's report: each stop's seconds, '-' for a stop not made: (cain, jamella). visit.py visit
# `'Macro: trade session done%s: cube %d items, ..., %.1f s (%s)'`, the stops in visit.py STOPS' order.
# 2026-10-18 16:00:12,913 INFO Macro: trade session done: cube 0 items, block 2x4 free, 9 inventory cells free, junk
#     left 0, keys 17, portals from the Sling, staff ?, ground clear, 27.6 s (cain 3.5, stash 12.7, jamella 8.4,
#     halbu -, walk 2.9)
# (gamble.py's stop since 2026-10-21, before jamella: optional, older logs have none)
VISIT_STOPS = re.compile(
    r'Macro: trade session done.*\(cain (\S+), stash \S+, (?:gamble \S+, )?jamella (\S+), halbu \S+, walk \S+\)$'
)
# A gamble session's end: (bought, kept, sold, paid, back, spent). gamble.py `gamble` `'%s session done: %s'` with
# `Gambled.said`.
# 2026-10-21 10:30:00,000 INFO Macro: gamble: session done: 3 rings bought, 1 kept (unique Ring), 2 sold; gold paid
#     150000, back 6000, spent 144000; carried 950000 -> 806000, personal stash 2500000 -> 2500000; 12.5 s; stop: 3
#     rings
GAMBLED = re.compile(
    r'Macro: gamble: session done: (\d+) rings bought, (\d+) kept.*?, (\d+) sold; gold paid (\d+), back (\d+), '
    r'spent (-?\d+)'
)


# --- The Andariel run (andy.py) --------------------------------------------------------------------------------------

# terror/bosses.py BossTracker.apply `'Boss kill: %s, %s this launch'`.
# 2026-10-18 15:59:24,412 INFO Boss kill: Andariel, 284 this launch
KILL = re.compile(r'Boss kill: Andariel, \d+ this launch')
# A combat take opened: (take, area). takes/record.py Recorder.open `'Combat take %s opened in area %d'`.
# 2026-10-18 15:58:36,182 INFO Combat take 20261018T125836Z-37 opened in area 37
OPENED = re.compile(r'Combat take (\S+) opened in area (\d+)')
# The next game made: (its name). routines.py create_next_game `run.say(f'Creating {name}')`.
# 2026-10-18 15:58:42,386 INFO Macro: Creating cyberr4
CREATING = re.compile(r'Macro: Creating (\S+)')
# routines.py create_next_game `'Macro: game loaded %.2fs after Enter'`.
# 2026-10-18 15:58:49,111 INFO Macro: game loaded 5.15s after Enter
GAME_LOADED = 'Macro: game loaded'
# routines.py leave_game `run.say('Save and Exit')`: the line ends with it.
# 2026-10-18 15:58:41,505 INFO Macro: Save and Exit
SAVE_AND_EXIT = 'Macro: Save and Exit'
# The stairs' press on the Andariel route: macros/route.py and routes/model.py (`enter {mark}`).
# 2026-10-18 15:59:04,350 INFO Macro: route Andariel: enter Next level
ROUTE_ENTER = 'Macro: route Andariel: enter Next level'
# hunt.py `run.say(f'Run: {line}')`.
# 2026-10-18 15:58:57,453 INFO Macro: Run: to Next level, clearing the way
RUN_TO_NEXT = 'Macro: Run: to Next level'
# The stairs' mark: (units from it). teleport.py walk_into.
# 2026-10-18 15:59:04,365 INFO Macro: door Next level marked at (22592.5, 6517.5); the character at (22591.5, 6522.5),
#     5.1 from the mark; entry remembered -1.0, +5.0 from the mark
DOOR_MARKED = re.compile(r'Macro: door Next level marked at .*?; the character at .*?, ([\d.]+) from the mark')
# Through the stairs: (seconds, units walked). teleport.py walk_into.press.
# 2026-10-18 15:59:04,641 INFO Macro: door Next level: in after 0.28s, walked 0.0 from (22591.5, 6522.5) to (22591.5,
#     6522.5); the entry at -1.0, +5.0 from the mark, 5.1 away (remembered)
DOOR_IN = re.compile(r'Macro: door Next level: in after ([\d.]+)s, walked ([\d.]+) from')
# A level run's pace: (units, seconds, jumps, walks). travel.py Travel.paced.
# 2026-10-18 15:59:04,238 INFO Macro: leg time: level run (at Next level: going through takes a press): 0 units in
#     6.6s since its first leg, 0.0 units/s; 0 jumps, 0 walks; key to key none
LEG_TIME = re.compile(r'Macro: leg time: level run .*?: (\d+) units in ([\d.]+)s since .*?; (\d+) jumps, (\d+) walks')
