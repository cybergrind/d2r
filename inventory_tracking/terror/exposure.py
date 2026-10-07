"""Statistics for the threat level: the life lost per second against the monsters that stood there.

The probe logs an `around` event every second while live monsters stand within a screen of the
player: their live positions and modes, and the player's life (terror/probe.py). Two such events
in a row are one sample: who was there, and how much life went in between (drops only, so a
potion hides nothing). From the samples:

- by score: the life lost at each pack score of the model (danger.py). The bands are right when
  the loss rises with the score and the marked scores hold the heavy seconds.
- by type: the loss laid on the monster types that stood there (non-negative least squares over
  all samples), per monster and second, beside the model's threat of that type. `off` is how far
  the type is from the model's average: above 1 the model underrates it, below 1 it overrates.

- by state: the loss under each state on the player (curses, chill; unnamed ids are states the
  model does not use), against the seconds with none of the model's.

Nothing here changes the model; the factors in danger.py are tuned from these tables by hand.

    uv run --offline python -m inventory_tracking.terror.exposure inventory_tracking/runs/alt-d/*/terror-probe.jsonl
"""

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from inventory_tracking.terror.bursts import read, unit_of
from inventory_tracking.terror.danger import DANGER, STATES, Unit, packs, table, threat


GAP = 3.0  # seconds: two looks around further apart are not one sample
EDGES = (3.0, 6.0, DANGER.caution, DANGER.deadly, 20.0)
MIN_SECONDS = 30.0  # unit-seconds below which a type's row is not shown


@dataclass(frozen=True)
class Sample:
    t: float
    area: int
    seconds: float
    lost: float  # share of the most life
    units: tuple[Unit, ...]  # hostile, at their live positions
    score: float  # the highest pack score among them
    states: frozenset[int] = frozenset()  # on the player (states.txt ids)


@dataclass(frozen=True)
class ScoreRow:
    low: float
    high: float | None
    seconds: float
    lost: float  # share of the life per second, on average
    worst: float  # the most lost within one sample

    @property
    def line(self) -> str:
        band = f'{self.low:g}+' if self.high is None else f'{self.low:g}-{self.high:g}'
        return f'{band:>8} {self.seconds:9.0f} {self.lost:9.2%} {self.worst:8.0%}'


@dataclass(frozen=True)
class TypeRow:
    name: str
    unit_seconds: float
    threat: float  # the model's, per monster, on average
    lost: float  # share of the life per monster and second
    off: float | None = None  # lost / threat against the same over all types

    @property
    def line(self) -> str:
        off = '' if self.off is None else f'{self.off:6.1f}x'
        return f'{self.name:<24.24} {self.unit_seconds:9.0f} {self.threat:7.2f} {self.lost:9.3%} {off:>7}'


def samples(events, *, gap=GAP) -> list[Sample]:
    known: dict[int, Unit] = {}
    found: list[Sample] = []
    before = None  # the last `around` event
    lost, life = 0, 0
    for event in events:
        kind = event.get('event')
        if kind == 'left_game':
            known.clear()
            before = None
        elif kind == 'seen':
            if (unit := unit_of(event)) is not None:
                known[unit.unit_id] = unit
        elif kind == 'life' and before is not None:
            lost, life = lost + max(life - event['life'], 0), event['life']
        elif kind == 'around':
            if before is not None and event['area'] == before['area'] and 0 < event['t'] - before['t'] <= gap:
                lost += max(life - event['life'], 0)
                units = tuple(
                    replace(known[unit_id], x=x, y=y)
                    for unit_id, _txt, _mode, x, y in before['near']
                    if unit_id in known
                )
                if units and before['max'] > 0:
                    states = frozenset(before.get('states', ()))
                    score = max((pack.score for pack in packs(units, player=states)), default=0.0)
                    seconds = round(event['t'] - before['t'], 3)
                    share = lost / before['max']
                    found.append(Sample(before['t'], before['area'], seconds, share, units, score, states))
            before, lost, life = event, 0, event['life']
    return found


def by_score(found, *, edges=EDGES) -> list[ScoreRow]:
    rows = []
    for low, high in zip((0.0, *edges), (*edges, None), strict=True):
        inside = [s for s in found if s.score >= low and (high is None or s.score < high)]
        seconds = sum(s.seconds for s in inside)
        lost = sum(s.lost for s in inside) / seconds if seconds else 0.0
        rows.append(ScoreRow(low, high, seconds, lost, max((s.lost for s in inside), default=0.0)))
    return rows


def fit(columns: dict[str, dict[int, float]], target: list[float], *, sweeps=200) -> dict[str, float]:
    """Non-negative least squares by coordinate descent: target[i] ~ sum(weight[c] * columns[c][i])."""
    weights = dict.fromkeys(columns, 0.0)
    left = list(target)
    squares = {name: sum(value * value for value in column.values()) for name, column in columns.items()}
    for _ in range(sweeps):
        for name, column in columns.items():
            if not squares[name]:
                continue
            step = sum(value * left[i] for i, value in column.items()) / squares[name]
            new = max(weights[name] + step, 0.0)
            if new != weights[name]:
                for i, value in column.items():
                    left[i] -= (new - weights[name]) * value
                weights[name] = new
    return weights


def by_type(found, *, min_seconds=0.0) -> list[TypeRow]:
    """One row per monster type, the most life lost per monster first."""
    threats = table()
    columns: dict[str, dict[int, float]] = {}  # type -> sample index -> monster-seconds
    scored: dict[str, float] = {}  # type -> model threat x seconds
    for index, sample in enumerate(found):
        for unit in sample.units:
            row = threats.monsters.get(unit.txt_id)
            if row is None:
                continue
            column = columns.setdefault(row.name, {})
            column[index] = column.get(index, 0.0) + sample.seconds
            value = threat(unit, sample.units, threats, DANGER, sample.states)[0]
            scored[row.name] = scored.get(row.name, 0.0) + value * sample.seconds
    weights = fit(columns, [sample.lost for sample in found])
    seconds = {name: sum(column.values()) for name, column in columns.items()}
    lost_all = sum(weights[name] * seconds[name] for name in columns)
    scale = lost_all / sum(scored.values()) if sum(scored.values()) else 0.0  # life per threat, all types
    rows = []
    for name in columns:
        if seconds[name] < min_seconds:
            continue
        mean = scored[name] / seconds[name]
        off = weights[name] / (mean * scale) if mean and scale else None
        rows.append(TypeRow(name, seconds[name], mean, weights[name], off))
    return sorted(rows, key=lambda row: -row.lost)


@dataclass(frozen=True)
class StateRow:
    name: str
    seconds: float
    lost: float  # share of the life per second, on average

    @property
    def line(self) -> str:
        return f'{self.name:<24.24} {self.seconds:9.0f} {self.lost:9.2%}'


def by_state(found) -> list[StateRow]:
    """The life lost per second under each state on the player, and with none of the model's."""
    totals: dict[str, list[float]] = {}
    for sample in found:
        names = [STATES.get(state, str(state)).removesuffix(' on you') for state in sample.states]
        for name in names if any(state in STATES for state in sample.states) else [*names, 'none']:
            seconds, lost = totals.setdefault(name, [0.0, 0.0])
            totals[name] = [seconds + sample.seconds, lost + sample.lost]
    rows = [StateRow(name, seconds, lost / seconds if seconds else 0.0) for name, (seconds, lost) in totals.items()]
    return sorted(rows, key=lambda row: -row.lost)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('logs', nargs='+', type=Path, help='terror-probe.jsonl files')
    parser.add_argument('--min-seconds', type=float, default=MIN_SECONDS, help='monster-seconds a type needs for a row')
    args = parser.parse_args(argv)
    found = [sample for path in args.logs for sample in samples(read(path))]
    seconds = sum(sample.seconds for sample in found)
    print(f'{len(found)} samples, {seconds:.0f} s with monsters within a screen, in {len(args.logs)} logs')
    if not found:
        print('No `around` events yet: they are logged by `make serve` from 2026-10-07 on.')
        return 0
    print(f'\n{"score":>8} {"seconds":>9} {"life/s":>9} {"worst":>8}')
    print('\n'.join(row.line for row in by_score(found)))
    print(f'\n{"type":<24} {"unit-sec":>9} {"threat":>7} {"life/s":>9} {"off":>7}')
    print('\n'.join(row.line for row in by_type(found, min_seconds=args.min_seconds)))
    print(f'\n{"state on the player":<24} {"seconds":>9} {"life/s":>9}')
    print('\n'.join(row.line for row in by_state(found)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
