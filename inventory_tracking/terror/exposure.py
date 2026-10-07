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
- by pack: where the model and the loss disagree. Each sample belongs to the type of its highest
  pack, and its loss is held against what the samples of all other types lost at the same score.
  A warned player is more careful (user, 2026-10-07), so the seconds with a danger mark shown
  (`marked` of the `around` event; the replayed band in logs without it) are only held against
  other warned seconds, and the unwarned against the unwarned. A type `OFF` times off either way
  with at least `--min-pack-seconds` behind it is called `underrated` or `overrated`.

Nothing here changes the model; the factors in danger.py are tuned from these tables by hand.

    uv run --offline python -m inventory_tracking.terror.exposure    (every run's log; or name the logs)
"""

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from inventory_tracking.terror.bursts import log_paths, read, unit_of
from inventory_tracking.terror.danger import BANDS, DANGER, STATES, Unit, packs, table, threat


GAP = 3.0  # seconds: two looks around further apart are not one sample
EDGES = (3.0, 6.0, DANGER.caution, DANGER.deadly, 20.0)
MIN_SECONDS = 30.0  # unit-seconds below which a type's row is not shown
MIN_PACK_SECONDS = 60.0  # seconds a pack type needs, warned or not, for a verdict
OFF = 2.0  # a pack type that loses this many times more or less life than others at its score is off


@dataclass(frozen=True)
class Sample:
    t: float
    area: int
    seconds: float
    lost: float  # share of the most life
    units: tuple[Unit, ...]  # hostile, at their live positions
    score: float  # the highest pack score among them
    states: frozenset[int] = frozenset()  # on the player (states.txt ids)
    pack: str = ''  # the type the highest pack is named after
    warned: bool = False  # a danger mark was shown on a monster there


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
                    top = next(iter(packs(units, player=states)), None)
                    score, name = (top.score, top.name) if top else (0.0, '')
                    shown = before.get('marked')  # logs before 2026-10-07 lack it: the replayed band stands in
                    warned = bool(top and top.band) if shown is None else any(shown.get(band) for band in BANDS)
                    seconds = round(event['t'] - before['t'], 3)
                    share = lost / before['max']
                    found.append(
                        Sample(before['t'], before['area'], seconds, share, units, score, states, name, warned)
                    )
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


@dataclass(frozen=True)
class PackRow:
    name: str
    warned: bool
    seconds: float
    score: float  # of the highest pack, on average
    lost: float  # share of the life per second, on average
    expected: float | None  # what the other types lost a second at the same scores; None where no other stood
    verdict: str = ''
    held: float = 0.0  # the life lost in the seconds that could be compared
    compared: float = 0.0  # those seconds

    @property
    def off(self) -> float | None:
        return self.held / self.compared / self.expected if self.expected else None

    @property
    def line(self) -> str:
        expected = '' if self.expected is None else f'{self.expected:.2%}'
        off = '' if self.off is None else f'{self.off:.1f}x'
        warned = 'yes' if self.warned else 'no'
        start = f'{self.name:<24.24} {warned:>6} {self.seconds:9.0f} {self.score:6.1f} {self.lost:9.2%}'
        return f'{start} {expected:>9} {off:>7}  {self.verdict}'.rstrip()


def by_pack(found, *, edges=EDGES, min_seconds=MIN_PACK_SECONDS, off=OFF) -> list[PackRow]:
    """One row per type of the highest pack, warned and unwarned apart, the furthest off first."""

    def band(sample) -> int:
        return sum(sample.score >= edge for edge in edges)

    totals: dict[tuple[bool, int], list[float]] = {}  # (warned, score band) -> seconds, lost
    own: dict[tuple[str, bool], dict[int, list[float]]] = {}  # the same of one type, by score band
    scores: dict[tuple[str, bool], float] = {}
    for sample in found:
        if not sample.pack:
            continue
        key = (sample.pack, sample.warned)
        for total in (totals.setdefault((sample.warned, band(sample)), [0.0, 0.0]),
                      own.setdefault(key, {}).setdefault(band(sample), [0.0, 0.0])):  # fmt: skip
            total[0] += sample.seconds
            total[1] += sample.lost
        scores[key] = scores.get(key, 0.0) + sample.score * sample.seconds
    rows = []
    for (name, warned), bands in own.items():
        seconds = sum(mine[0] for mine in bands.values())
        lost = sum(mine[1] for mine in bands.values()) / seconds
        expected, compared, held = 0.0, 0.0, 0.0  # over the score bands where another type stood too
        for index, mine in bands.items():
            others = [all_ - own_ for all_, own_ in zip(totals[warned, index], mine, strict=True)]
            if others[0] > 0:
                expected += others[1] / others[0] * mine[0]
                compared += mine[0]
                held += mine[1]
        rate = expected / compared if compared else None
        verdict = ''
        if rate and compared >= min_seconds:
            verdict = 'underrated' if held >= off * expected else 'overrated' if held * off <= expected else ''
        rows.append(PackRow(name, warned, seconds, scores[name, warned] / seconds, lost, rate, verdict, held, compared))

    def distance(row) -> float:
        return max(row.off, 1 / row.off) if row.off else 1.0 if row.off is None else float('inf')

    return sorted(rows, key=lambda row: (not row.verdict, -distance(row), row.name))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('logs', nargs='*', type=Path, help='terror-probe.jsonl files (default: every run)')
    parser.add_argument('--min-seconds', type=float, default=MIN_SECONDS, help='monster-seconds a type needs for a row')
    parser.add_argument(
        '--min-pack-seconds', type=float, default=MIN_PACK_SECONDS, help='seconds a pack type needs for a verdict'
    )
    args = parser.parse_args(argv)
    args.logs = log_paths(args.logs)
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
    rows = [row for row in by_pack(found, min_seconds=args.min_pack_seconds) if row.seconds >= args.min_pack_seconds]
    print(f'\n{"highest pack":<24} {"warned":>6} {"seconds":>9} {"score":>6} {"life/s":>9} {"others":>9} {"off":>7}')
    print('\n'.join(row.line for row in rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
