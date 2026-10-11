"""How long a press takes, from the request script to the first input and the landing.

One record per press of a macro key, one JSON line each in `latency.jsonl` beside probe.log:

- `spawn_ms`, `spawn_cpu_ms`: the request script's process from its start to its stamp (request.py; the
  start is known to a clock tick, 10 ms) and the CPU it used on the way. The key itself is not seen:
  the compositor swallows it, and the input devices are not readable without the `input` group.
- `ms`: the marks, in milliseconds after the stamp. `received` (the service read the datagram),
  `accepted` (runner.request decided), `thread` (its run began: at once, or after the run it queued
  behind), `locked` (the capture lock was had), `ready` (the run was built), `settled` and `planned`
  (the hop: the cast before is over, the landing is chosen), `first_move` and `first_key` (the
  actuator's first pointer move and first key or button down), `landed`, `done`.
- `during`: the routine working when it came; `outcome`: started, queued behind what, cancelled what,
  dropped and why; `ended`: how its run ended.
- `pass`, `pass_ms`: the service loop's step under way when the datagram came and for how long.
- `cpu_ms`, `switches`: the run thread's CPU time and involuntary context switches; `load`.

    uv run --offline python -m inventory_tracking.macros.latency [run directory or latency.jsonl ...]

prints per routine and state the spread of every stage and the slowest presses.
"""

import argparse
import json
import os
import resource
import threading
import time
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from inventory_tracking.common import LOG


FILE = 'latency.jsonl'
MARKS = (
    'received', 'accepted', 'thread', 'locked', 'ready', 'settled', 'planned', 'first_move', 'first_key',
    'landed', 'done',
)  # fmt: skip
# What the time up to a mark was spent on.
STAGES = {
    'received': 'socket wait',
    'accepted': 'decision',
    'thread': 'queue and thread start',
    'locked': 'capture lock',
    'ready': 'run setup',
    'settled': 'cast before over',
    'planned': 'route',
    'first_move': 'before the pointer',
    'first_key': 'pointer and pause',
    'landed': 'game',
    'done': 'after the landing',
}
FIRST_INPUT = ('first_move', 'first_key')  # whichever comes first is the first thing the game sees
SLOW_MS = 150.0  # a press whose first input came later than this after its stamp is logged
BUDGET_MS = {'p50': 80.0, 'p99': 150.0}  # the stamp to the first input, with nothing running


class Press:
    def __init__(self, number: int, routine: str, stamp: float, clock: Callable[[], float]) -> None:
        self.number, self.routine, self.stamp, self.clock = number, routine, stamp, clock
        self.marks: dict[str, float] = {}
        self.notes: dict[str, object] = {}
        self.usage: tuple[float, int] | None = None  # the run thread's CPU seconds and switches at its start
        self.closed = False

    def mark(self, name: str, at: float | None = None) -> None:
        """Note `name` now (or at `at`); the first time counts."""
        self.marks.setdefault(name, self.clock() if at is None else at)

    def first_input(self) -> float | None:
        found = [self.marks[name] for name in FIRST_INPUT if name in self.marks]
        return min(found) - self.stamp if found else None

    def record(self) -> dict[str, object]:
        return {
            'at': datetime.now().isoformat(timespec='milliseconds'),
            'n': self.number,
            'routine': self.routine,
            **self.notes,
            'ms': {name: round(1000 * (at - self.stamp), 1) for name, at in self.marks.items()},
        }


def thread_usage() -> tuple[float, int]:
    return time.thread_time(), resource.getrusage(resource.RUSAGE_THREAD).ru_nivcsw


class Trace:
    """The presses of one service run. Without a path nothing is written (tests, the CLI)."""

    def __init__(self, path: Path | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.path, self.clock = path, clock
        self.lock = threading.Lock()
        self.count = 0
        self.closed: list[Press] = []  # the last few, for tests and a look from a debugger

    def press(self, routine: str, stamp: float, received: float, **notes: object) -> Press:
        with self.lock:
            self.count += 1
            press = Press(self.count, routine, stamp, self.clock)
        press.mark('received', received)
        press.notes.update({name: value for name, value in notes.items() if value is not None})
        return press

    def begin(self, press: Press | None) -> None:
        """The run of `press` begins on this thread."""
        if press is not None:
            press.mark('thread')
            press.usage = thread_usage()

    def close(self, press: Press | None, **notes: object) -> None:
        """`press` is over: written once, with the notes."""
        if press is None or press.closed:
            return
        press.closed = True
        press.notes.update({name: value for name, value in notes.items() if value is not None})
        if press.usage is not None:
            cpu, switches = thread_usage()
            press.mark('done')
            press.notes.update(
                cpu_ms=round(1000 * (cpu - press.usage[0]), 1),
                switches=switches - press.usage[1],
                load=round(os.getloadavg()[0], 2),
            )
        record = press.record()
        first = press.first_input()
        if first is not None and 1000 * first >= SLOW_MS:
            LOG.warning('Macro: slow press: %s', json.dumps(record))
        with self.lock:
            self.closed = [*self.closed[-49:], press]
            if self.path is None:
                return
            try:
                with self.path.open('a') as out:
                    out.write(json.dumps(record) + '\n')
            except OSError as exc:
                LOG.warning('Macro: the press could not be written (%s)', exc)
                self.path = None


# -- the report -------------------------------------------------------------------------------------


def load(paths: Iterable[Path]) -> list[dict]:
    records = []
    for path in paths:
        file = path / FILE if path.is_dir() else path
        if not file.exists():
            continue
        for line in file.read_text().splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def stages(record: dict) -> dict[str, float]:
    """The milliseconds each stage took: from the mark before (the stamp for the first) to its own."""
    marks, taken, before = record.get('ms', {}), {}, 0.0
    if 'spawn_ms' in record:
        taken['script start'] = record['spawn_ms']
    for name in MARKS:
        if name in marks:
            taken[STAGES[name]] = marks[name] - before
            before = marks[name]
    return taken


def first_input(record: dict) -> float | None:
    found = [record.get('ms', {})[name] for name in FIRST_INPUT if name in record.get('ms', {})]
    return min(found) if found else None


def quantile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def spread(values: list[float]) -> str:
    return (
        f'{len(values):5d}  {quantile(values, 0.5):7.0f} {quantile(values, 0.9):7.0f} '
        f'{quantile(values, 0.99):7.0f} {max(values):7.0f}'
    )


def report(records: list[dict], worst: int = 20) -> str:
    lines = [f'{len(records)} presses']
    outcomes: dict[str, int] = {}
    for record in records:
        outcome = str(record.get('outcome', '?')).split(':')[0]
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    lines += [f'  {count:5d}  {outcome}' for outcome, count in sorted(outcomes.items(), key=lambda item: -item[1])]
    groups: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        if first_input(record) is not None:
            groups.setdefault((record['routine'], record.get('during') or 'nothing'), []).append(record)
    for (routine, during), group in sorted(groups.items()):
        lines += [
            '',
            f'{routine}, pressed while {during} ran: milliseconds',
            f'{"":26}    n      p50     p90     p99     max',
        ]
        totals = [value for record in group if (value := first_input(record)) is not None]
        lines.append(f'{"stamp to first input":26}{spread(totals)}')
        whole = [
            value + record['spawn_ms']
            for record in group
            if 'spawn_ms' in record and (value := first_input(record)) is not None
        ]
        if whole:
            lines.append(f'{"  with the script start":26}{spread(whole)}')
        names = ['script start', *STAGES.values()]
        for name in names:
            values = [taken[name] for record in group if name in (taken := stages(record))]
            if values:
                lines.append(f'{"  " + name:26}{spread(values)}')
        if during == 'nothing':
            for name, limit in BUDGET_MS.items():
                got = quantile(totals, 0.5 if name == 'p50' else 0.99)
                lines.append(f'  budget {name} {limit:.0f} ms: {got:.0f} ms, {"kept" if got <= limit else "MISSED"}')
    slow = sorted(
        (record for record in records if first_input(record) is not None),
        key=lambda record: first_input(record) or 0.0,
        reverse=True,
    )
    if slow:
        lines += ['', f'The {min(worst, len(slow))} slowest to a first input:']
        lines += [f'  {json.dumps(record)}' for record in slow[:worst]]
    return '\n'.join(lines)


def latest(root: Path) -> list[Path]:
    found = sorted(path.parent for path in root.glob(f'*/{FILE}'))
    return found[-1:]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Where the time of a macro key press goes.')
    parser.add_argument(
        'paths', nargs='*', type=Path, help='run directories or latency.jsonl files (default: the latest run)'
    )
    parser.add_argument('--worst', type=int, default=20)
    args = parser.parse_args(argv)
    paths = args.paths or latest(Path(__file__).resolve().parents[1] / 'runs' / 'alt-d')
    records = load(paths)
    if not records:
        print('No presses recorded.')
        return 1
    print(report(records, args.worst))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
