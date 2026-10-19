"""Follow the KP_6 loop live: the newest serve probe.log, across restarts of `make serve`.

Prints (one stdout line = one event, for a Monitor):
- `game N: Ts (chests Cs, <leg> Ss...); <notes>` when a game ends (legs over SLOW seconds named);
- the loop's stops, recoveries ("the game is left"), guard stops ("stops here"), full stacks, sales, repairs, errors and
  tracebacks, the moment they are logged;
- `MISSED: ...` when a game ends with an item the sure mode takes never picked up (games.py `Seen.missed`): the loss
  the player's hard rule is about, to trace at once;
- `PLAYER: loop off` / `PLAYER: loop on` when the player toggles it with KP_6;
- `STALL: ...` when the loop is on and no leg has started for --stall seconds (wall clock), again every --again;
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
import sys
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path

import games
from logwords import (
    AIMED,
    FULL,
    GROUND,
    LEG,
    LOOP_OFF,
    LOOP_ON,
    LOOP_RESUMED,
    LOOP_STOPPED,
    NOTE,
    NOW,
    PICKED,
    REQUEST_LOOP,
    RESUMED_OFF,
    SAID,
    stamp,
)


RUNS = Path(__file__).resolve().parents[4] / 'inventory_tracking' / 'runs' / 'alt-d'
SLOW = 25.0
COMBAT = Path(__file__).resolve().parents[4] / 'inventory_tracking' / 'runs' / 'combat'
BASELINE = 279  # chests an hour of cycles, 02:43-04:31 on 2026-10-17 (the journal)
RATE_EVERY = 5
TAKE_LEAD = 20.0  # seconds: a stay's take starts this much before its `the chests` leg at most


def chests_between(start: datetime, end: datetime) -> int | None:
    """The chests the Lower Kurast takes started between `start` and `end` (local) opened; None without the repo."""
    try:
        sys.path.insert(0, str(COMBAT.parents[2]))
        from inventory_tracking.combat.legs import CHESTS, legs_of
        from inventory_tracking.combat.takes import Take
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
    dirs = sorted(d for d in RUNS.iterdir() if d.is_dir() and d.name.startswith('20'))
    return dirs[-1] / 'probe.log' if dirs else None


class Watch:
    def __init__(self, stall: float, again: float):
        self.stall, self.again = stall, again
        self.loud = True
        self.on = False
        self.last_leg_wall = time.time()
        self.last_leg = ''
        self.alarmed = 0.0
        self.game: tuple[int, datetime] | None = None
        self.legs: dict[str, datetime] = {}
        self.notes: list[str] = []
        self.asked_loop = False
        # The game's ground census, pickups and their aims, as games.py `read` matches them
        self.items: dict[tuple, games.Seen] = {}
        self.picks: list[str] = []
        self.aims: dict[str, set[tuple[int, int]]] = {}
        self.clicks: list[tuple[tuple[int, int], int]] = []  # games.py `clicked`: the press's clicks, by line number
        self.number = 0
        # The full stacks: the file as it is at each game's end (a stash visit or an agent may change it while the watch
        # runs: 02:10 on 2026-10-19) and those the log said full since
        self.full = games.full_stacks()
        self.said_full: set[str] = set()
        # The cycles (RATE): the one under way (its game and start), whether a pause or a restart cut it, the last 60
        self.cycle: tuple[int, datetime] | None = None
        self.cut = False
        self.cycles: deque[tuple[float, int]] = deque(maxlen=60)
        self.counted = 0
        self.next_health = 0.0

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
        if self.on and time.time() - self.last_leg_wall >= self.stall:
            state += ', stalled'
        self.say(f'HEALTH {datetime.now():%Y-%m-%d %H:%M:%S}: {state}; {evidence}; {self.last_leg or "no loop leg"}')

    def say(self, text: str) -> None:
        if self.loud:
            print(text, flush=True)

    def ground(self, whole: bool) -> None:
        """Say the game's items the sure mode takes and no pickup took (`whole`: the game ended by the next one; a
        pause or a stop leaves them to the player, said as such)."""
        self.full = games.full_stacks() | self.said_full
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
        if (m := FULL.search(line)) is not None:
            self.full.add(m.group(1))
            self.said_full.add(m.group(1))
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
            item = self.items.setdefault(
                (quality, name, place), games.Seen(line[11:19], '', number, quality, name, m.group(5) or '', place)
            )
            item.last = self.number
            if m.group(8):
                item.verdicts.add(m.group(8))

    def finish(self, at: datetime, whole: bool = True) -> None:
        if self.game is None:
            return
        self.ground(whole)
        number, started = self.game
        order = list(self.legs.items())
        spans = [
            (name, (nxt[1] - t).total_seconds())
            for (name, t), nxt in zip(order, [*order[1:], ('end', at)], strict=True)
        ]
        chests = sum(s for n, s in spans if n == 'the chests')
        slow = ', '.join(f'{n} {s:.0f}s' for n, s in spans if s > SLOW and n != 'the chests')
        notes = '; '.join(self.notes)
        seconds = (at - started).total_seconds()
        self.say(f'game {number}: {seconds:.0f}s (chests {chests:.0f}s{", " + slow if slow else ""})'
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
            if self.game is None or self.game[0] != number:
                self.finish(at)
                self.game, self.legs, self.notes = (number, at), {}, []
            self.legs.setdefault(leg, at)
            if leg == 'the chests' and (self.cycle is None or self.cycle[0] != number):
                self.close_cycle(number, at)
        if NOTE.search(line) and self.game is not None:
            self.notes.append(line[line.index(SAID) + len(SAID) :].strip()[:80])
        if NOW.search(line):
            self.say(line[11:300].rstrip())

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

    def idle(self) -> None:
        now = time.time()
        if self.on and now - self.last_leg_wall > self.stall and now - self.alarmed > self.again:
            self.alarmed = now
            self.say(f'STALL: no loop leg for {now - self.last_leg_wall:.0f}s; last: {self.last_leg}')


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
