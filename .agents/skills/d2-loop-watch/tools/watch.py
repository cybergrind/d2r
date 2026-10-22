"""Follow the KP_6 loop live: the newest serve probe.log, across restarts of `make serve`.

Prints (one stdout line = one event, for a Monitor):
- `game N: Ts (chests Cs, <leg> Ss...); <notes>` when a game ends (legs over SLOW seconds named), `game N: Ts, +X exp
  (...)` for a terror zone game that logged its experience (logwords.py EXPERIENCE_GAME);
- the loop's stops, recoveries ("the game is left"), guard stops ("stops here"), full stacks, sales, repairs, errors and
  tracebacks, the moment they are logged;
- `MISSED: ...` when a game ends with an item the sure mode takes never picked up (games.py `Seen.missed`): the loss
  the player's hard rule is about, to trace at once;
- `PET LOST: ...` the moment the bound demon dies (logwords.py PET_LOST; the player, 2026-10-21 ~15:45: "we have lost
  our daemon"), and the game's line notes it;
- `PLAYER: loop off` / `PLAYER: loop on` when the player toggles it with KP_6;
- `STALL: ...` when the loop is on, no leg has started for --stall seconds (wall clock) and no teleport, kill or pickup
  was logged in them, or one leg runs past LONG_LEG seconds; again every --again;
- `ANOMALY: ...` when a combat take closes (TAKE_CLOSED): anomalies.py's cases in it (IDLE, LONG_FIGHT, JUMP_CLUSTER),
  found on a worker thread so the watch never waits for it (the player, 2026-10-21 ~21:08: "this should become a part
  of monitoring loop");
- `== following <session>` when a new service starts (a restart);
- `RATE: ...` every RATE_EVERY cycles: chests an hour over the last 20 and 60 cycles (a cycle from one Lower Kurast
  arrival to the next, everything between counted; the chests from the takes, `combat.legs`), against the baseline:
  the sliding measure to steer by (the player, 2026-10-17: "maybe chest per hour, some sliding metric to steer if
  we're moving into good direction or not"). A cycle the player paused or a restart cut is left out. Needs the repo's
  Python for the takes: `uv run --offline python -u ...`; with plain python3 there is no RATE.

On start the current log is read quietly up to its end, so a re-armed watch knows the game in progress and whether the
loop is on. `--from-start` prints the whole current log's games instead.

    uv run --offline python -u .agents/skills/d2-loop-watch/tools/watch.py [--stall 75] [--again 120] [--from-start]
"""

import argparse
import queue
import sys
import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path

import anomalies
import games
import logwords
from logwords import (
    AIMED,
    BOUND_WORD,
    EXPERIENCE_GAME,
    FIELD_DROP,
    FULL_DOWN,
    GROUND,
    LEG,
    LOOP_OFF,
    LOOP_ON,
    LOOP_RESUMED,
    LOOP_STOPPED,
    NOTE,
    NOW,
    OPENED,
    PET_LOST,
    PICKED,
    PROGRESS,
    REQUEST_LOOP,
    RESUMED_OFF,
    SAID,
    TAKE_CLOSED,
    TOWN_DROP,
    WAITING,
    stamp,
)


RUNS = Path(__file__).resolve().parents[4] / 'inventory_tracking' / 'runs' / 'alt-d'
SLOW = 25.0
LONG_LEG = 300.0  # seconds: one leg this long is a STALL even while it moves and fights
COMBAT = Path(__file__).resolve().parents[4] / 'inventory_tracking' / 'runs' / 'combat'
BASELINE = 279  # chests an hour of cycles, 02:43-04:31 on 2026-10-17 (the journal)
RATE_EVERY = 5
TAKE_LEAD = 20.0  # seconds: a stay's take starts this much before its `the chests` leg at most


def chests_between(start: datetime, end: datetime) -> int | None:
    """The chests the Lower Kurast takes started between `start` and `end` (local) opened; None without the repo."""
    try:
        sys.path.insert(0, str(COMBAT.parents[2]))
        from inventory_tracking.takes.legs import CHESTS, legs_of
        from inventory_tracking.takes.takes import Take
    except ImportError:
        return None
    low = (start - timedelta(seconds=TAKE_LEAD)).astimezone(UTC).strftime('%Y%m%dT%H%M%S')
    high = (end - timedelta(seconds=TAKE_LEAD)).astimezone(UTC).strftime('%Y%m%dT%H%M%S')
    found = 0
    for directory in COMBAT.glob('*-79'):
        if low <= directory.name.split('Z')[0] < high:
            try:
                found += sum(leg.to in CHESTS for leg in legs_of(Take.load(directory)))
            except OSError, ValueError, KeyError:
                continue
    return found


def newest() -> Path | None:
    return logwords.newest(RUNS)


class Watch:
    def __init__(self, stall: float, again: float):
        self.stall, self.again = stall, again
        self.loud = True
        self.on = False
        self.last_leg_wall = time.time()
        self.last_progress_wall = 0.0  # a teleport landed, a kill, a pickup: a long leg that goes on
        self.waiting_until = 0.0  # the loop's own wait before its next leg (WAITING)
        self.last_leg = ''
        self.alarmed = 0.0
        self.game: tuple[int, datetime] | None = None
        self.legs: list[tuple[str, datetime]] = []  # each leg as it starts; a name may come back
        self.notes: list[str] = []
        self.exp = ''  # the game's experience gain, as its EXPERIENCE_GAME line wrote it
        self.asked_loop = False
        # The game's ground census, pickups and their aims, as games.py `read` matches them
        self.items: dict[tuple, games.Seen] = {}
        self.picks: list[str] = []
        self.aims: dict[str, set[tuple[int, int]]] = {}
        self.clicks: list[tuple[tuple[int, int], int]] = []  # games.py `clicked`: the press's clicks, by line number
        self.number = 0
        self.field_drop: int | None = None  # the last field drop's line (games.py `field_dropped`)
        # The keys of the items the loop put down in the game under way, kept across a restart of the service (games.py
        # `inherited`) and cleared when another game begins; `carried_for` is that game's number
        self.carried: set[tuple] = set()
        self.carried_for: int | None = None
        # The full stacks: the service's stash snapshot as it is at each game's end (runs/alt-d/stash.json,
        # game/stash.py; never a list of the watch's own: 2026-10-22)
        self.full = games.full_stacks()
        # The cycles (RATE): the one under way (its game and start), whether a pause or a restart cut it, the last 60
        self.cycle: tuple[int, datetime] | None = None
        self.cut = False
        self.cycles: deque[tuple[float, int]] = deque(maxlen=60)
        self.counted = 0
        self.next_health = 0.0
        # The anomalies of each closed take (anomalies.py): the loop's state at each take's open, the takes waiting for
        # the worker, its lines waiting to be said by the main loop (one printer: no torn lines)
        self.opened: dict[str, bool] = {}
        self.closed: queue.Queue[str] = queue.Queue()
        self.found: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

    def health(self, source: Path | None) -> None:
        """Minute check independent of log traffic; old logs cannot prove an active loop."""
        now = time.monotonic()
        if now < self.next_health:
            return
        self.next_health = now + 60.0
        try:
            age = max(0.0, time.time() - source.stat().st_mtime) if source is not None else None
        except OSError:
            age = None
        state = 'loop on' if self.on else 'loop off'
        if age is None:
            evidence = 'log unavailable; service state unknown'
        elif age >= 60:
            evidence = f'log stale ({age:.0f}s); service state unknown'
        else:
            evidence = f'log fresh ({age:.0f}s)'
        if self.on and self.stalled(time.time()):
            state += ', stalled'
        self.say(f'HEALTH {datetime.now():%Y-%m-%d %H:%M:%S}: {state}; {evidence}; {self.last_leg or "no loop leg"}')

    def say(self, text: str) -> None:
        if self.loud:
            print(text, flush=True)

    def ground(self, whole: bool) -> None:
        """Say the game's items the sure mode takes and no pickup took (`whole`: the game ended by the next one; a
        pause or a stop leaves them to the player, said as such)."""
        self.full = games.full_stacks()
        seen = list(self.items.values())
        games.clicked(seen, self.clicks)
        games.reconcile(seen, self.picks, self.aims)
        for item in seen:
            why = None if item.picked else item.missed(self.full)
            if why:
                state = 'MISSED' if whole else 'on the ground at a stop'
                self.say(
                    f'{state}: game {item.game}, {item.quality} {item.name} at {item.place} seen {item.when}: {why}'
                )
        self.items.clear()
        self.picks.clear()
        self.aims.clear()
        self.clicks.clear()

    def track(self, line: str) -> None:
        self.number += 1
        if TOWN_DROP.search(line) or FIELD_DROP.search(line) or FULL_DOWN.search(line):
            games.put_down(self.items.values(), self.number, not FIELD_DROP.search(line))
            if FIELD_DROP.search(line) or FULL_DOWN.search(line):
                self.field_drop = self.number  # its sighting comes after the line (games.py `field_dropped`)
            self.carried |= games.carried_keys(self.items.values())
        elif (m := PICKED.search(line)) is not None:
            self.picks.append(m.group(1))
        elif (m := AIMED.search(line)) is not None:
            label = m.group(1) or m.group(4)
            x, y = (m.group(2), m.group(3)) if m.group(1) else (m.group(5), m.group(6))
            self.aims.setdefault(label, set()).add((round(float(x)), round(float(y))))
            if m.group(4):
                self.clicks.append(((round(float(x)), round(float(y))), self.number))
        elif (m := GROUND.search(line)) is not None:
            quality, name, place = m.group(1), m.group(2), (int(m.group(6)), int(m.group(7)))
            number = self.game[0] if self.game is not None else None
            fresh = (quality, name, place) not in self.items
            item = self.items.setdefault(
                (quality, name, place),
                games.Seen(line[11:19], '', number, quality, name, m.group(5) or '', place, first=self.number),
            )
            if fresh:
                games.field_dropped(item, self.field_drop)
                if not item.put_down:
                    games.carry_over(item, self.carried)
                self.carried |= games.carried_keys(self.items.values())
            item.last = self.number
            if m.group(8):
                item.verdicts.add(m.group(8))

    def finish(self, at: datetime, whole: bool = True) -> None:
        if self.game is None:
            return
        self.ground(whole)
        number, started = self.game
        order = self.legs
        spans: dict[str, float] = {}  # each leg's seconds summed over its stretches (2026-10-19)
        for (name, t), nxt in zip(order, [*order[1:], ('end', at)], strict=True):
            spans[name] = spans.get(name, 0.0) + (nxt[1] - t).total_seconds()
        chests = spans.get('the chests', 0.0)
        slow = ', '.join(f'{n} {s:.0f}s' for n, s in spans.items() if s > SLOW and n != 'the chests')
        notes = '; '.join(self.notes)
        seconds = (at - started).total_seconds()
        exp = f', {self.exp} exp' if self.exp else ''
        self.say(f'game {number}: {seconds:.0f}s{exp} (chests {chests:.0f}s{", " + slow if slow else ""})'
                 f'{"; " + notes if notes else ""}')  # fmt: skip
        self.game = None

    def line(self, line: str) -> None:
        at = stamp(line)
        self.track(line)
        if REQUEST_LOOP in line:
            self.asked_loop = True
        if LOOP_ON in line or LOOP_RESUMED in line:
            self.on, self.last_leg_wall = True, at.timestamp() if at is not None else time.time()
            if self.asked_loop:
                self.say(f'PLAYER: loop on at {line[11:19]}')
            self.asked_loop = False
        if LOOP_OFF in line or LOOP_STOPPED in line or RESUMED_OFF in line:
            self.on = False
            if LOOP_OFF in line and self.asked_loop:
                self.say(f'PLAYER: loop off at {line[11:19]}')
                if self.game is not None:
                    self.notes.append('paused by the player')
            elif self.game is not None:
                self.notes.append('stopped')
            self.asked_loop = False
            self.cut = True
            if at is not None:
                self.finish(at, whole=False)
        if (m := LEG.search(line)) and at is not None:
            number, leg = int(m.group(1)), m.group(2).strip()
            self.on, self.last_leg_wall, self.last_leg = True, at.timestamp(), f'game {number}, {leg} at {line[11:19]}'
            if self.carried_for != number:
                if self.carried_for is not None:
                    self.carried.clear()
                self.carried_for = number
            if self.game is None or self.game[0] != number:
                self.finish(at)
                self.game, self.legs, self.notes, self.exp = (number, at), [], [], ''
            if not self.legs or self.legs[-1][0] != leg:
                self.legs.append((leg, at))
            if leg == 'the chests' and (self.cycle is None or self.cycle[0] != number):
                self.close_cycle(number, at)
        if PROGRESS.search(line) and at is not None:
            self.last_progress_wall = at.timestamp()
        if (m := WAITING.search(line)) and at is not None:
            self.waiting_until = at.timestamp() + float(m.group(1))
        if (m := EXPERIENCE_GAME.search(line)) and self.game is not None and self.game[0] == int(m.group(1)):
            self.exp = m.group(2)
        if NOTE.search(line) and self.game is not None:
            self.notes.append(line[line.index(SAID) + len(SAID) :].strip()[:80])
        if NOW.search(line):
            self.say(line[11:300].rstrip())
        if (m := OPENED.search(line)) is not None:
            self.opened[m.group(1)] = self.on
        if (m := TAKE_CLOSED.search(line)) is not None and self.loud:
            self.take_closed(m.group(1))
        if (m := PET_LOST.search(line)) and m.group(1).startswith(BOUND_WORD):
            self.say(f'PET LOST: {m.group(1)} ({m.group(2)}) at {line[11:19]}, {m.group(3)}/128')
            if self.game is not None:
                self.notes.append(f'{m.group(1)} lost')

    def take_closed(self, take: str) -> None:
        """Queue the take for anomalies.py on the worker thread (started at the first close)."""
        self.closed.put(take)
        if self.worker is None:
            self.worker = threading.Thread(target=self.find_anomalies, name='anomalies', daemon=True)
            self.worker.start()

    def find_anomalies(self) -> None:
        while True:
            take = self.closed.get()
            try:
                cases = anomalies.detect(COMBAT / take, on=self.opened.pop(take, None))
            except Exception as error:  # a take that does not read must not end the watch
                self.found.put(f'{anomalies.PREFIX} {take} not read: {type(error).__name__}: {error}'[:300])
                continue
            for case in cases:
                self.found.put(case.line())

    def drain(self) -> None:
        """Say the anomalies found since the last call."""
        while True:
            try:
                self.say(self.found.get_nowait())
            except queue.Empty:
                return

    def close_cycle(self, number: int, at: datetime) -> None:
        """The cycle that ends at this Lower Kurast arrival counted (unless cut), the next begun; RATE said."""
        if self.cycle is not None and not self.cut:
            seconds = (at - self.cycle[1]).total_seconds()
            chests = chests_between(self.cycle[1], at)
            if chests is not None and 0 < seconds < 600:
                self.cycles.append((seconds, chests))
                self.counted += 1
                if self.counted % RATE_EVERY == 0:
                    self.say(f'RATE: {self.rate(20)}; {self.rate(60)} (baseline {BASELINE})')
        self.cycle, self.cut = (number, at), False

    def rate(self, n: int) -> str:
        last = list(self.cycles)[-n:]
        seconds = sum(s for s, _ in last)
        chests = sum(c for _, c in last)
        return f'last {len(last)} cycles {3600 * chests / seconds:.0f} chests/h' if seconds else 'no cycles'

    def stalled(self, now: float) -> bool:
        """No leg for --stall s and nothing done in it (a TZ level's legs run minutes while it explores and fights),
        or one leg past LONG_LEG s whatever it does."""
        if now < self.waiting_until:
            return False  # the loop's own wait (the next terror zone)
        quiet = now - max(self.last_leg_wall, self.last_progress_wall, self.waiting_until)
        return quiet > self.stall or now - max(self.last_leg_wall, self.waiting_until) > LONG_LEG

    def idle(self) -> None:
        now = time.time()
        if self.on and self.stalled(now) and now - self.alarmed > self.again:
            self.alarmed = now
            quiet = now - max(self.last_leg_wall, self.last_progress_wall)
            self.say(f'STALL: no loop leg for {now - self.last_leg_wall:.0f}s, nothing done for {quiet:.0f}s; '
                     f'last: {self.last_leg}')  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--stall', type=float, default=75.0)
    parser.add_argument('--again', type=float, default=120.0)
    parser.add_argument('--from-start', action='store_true')
    args = parser.parse_args()
    watch = Watch(args.stall, args.again)
    current = handle = None
    first = True
    while True:
        latest = newest()
        if latest is not None and latest != current and latest.exists():
            current, handle = latest, open(latest, errors='replace')  # ruff: ignore[open-file-with-context-handler] - followed for the run's life
            print(f'== following {current.parent.name}', flush=True)
            watch.cut = True  # a restart: the cycle under way is not counted
            watch.carried |= games.inherited(current.parent)  # a game taken up after a restart: what was put down
            if first and not args.from_start:
                watch.loud = False
                for old in handle:
                    watch.line(old)
                watch.loud = True
                state = f'loop {"on" if watch.on else "off"}'
                print(f'== {state}; {watch.last_leg or "no leg yet"}', flush=True)
            first = False
        text = handle.readline() if handle else ''
        watch.health(current)
        watch.drain()
        if not text:
            watch.idle()
            time.sleep(0.5)
            continue
        watch.line(text)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
