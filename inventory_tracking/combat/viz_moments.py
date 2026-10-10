"""Find the moments worth a second look when a recorded fight is replayed with an attack policy.

A moment is an inclusive tick range (start <= first <= last <= end) where the recorded run and the policy run of one
fight differ in a way a viewer should see. Each moment has a short label and the number that label quotes. The five
kinds are:

- policy_ahead: a stretch where the policy's casts took more life than the recorded casts did.
- recorded_ahead: the same stretch measured the other way round, where the recorded casts took more life.
- idle: a long gap in which the player did not cast, while the policy cast on monsters at least twice.
- miss: a run of recorded casts in one stretch of play that touched no monster, lasting until their blades would
  have expired.
- kill: an elite that died at clearly different ticks in the two runs.

Ticks are integers at a fixed rate (25 a second by default). Only the standard library is used.
"""

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import fsum


POLICY_AHEAD, RECORDED_AHEAD, IDLE, MISS, KILL = 'policy_ahead', 'recorded_ahead', 'idle', 'miss', 'kill'
KINDS = (POLICY_AHEAD, RECORDED_AHEAD, IDLE, MISS, KILL)

# A candidate life window: (difference in life, first tick, last tick).
Window = tuple[float, int, int]


@dataclass(frozen=True)
class Trace:
    """One run reduced to what the moments need."""

    name: str  # 'recorded', 'live', 'yield', ...
    taken: Sequence[tuple[int, float]]  # (tick, life points taken at that tick); ticks ascending, a tick may repeat
    casts: Sequence[tuple[int, int]]  # (tick the cast's blades appear, monsters those blades touched); ticks ascending
    deaths: dict[int, int]  # monster unit id -> tick it died in this run


@dataclass(frozen=True)
class Moment:
    """A tick range worth looking at, with its kind, a one-sentence label and the number the label quotes."""

    first: int  # inclusive, start <= first <= last <= end
    last: int
    kind: str  # one of KINDS
    label: str  # short plain-English sentence, no trailing full stop
    value: float  # the number the label quotes; its meaning depends on the kind


def find_moments(
    start: int,
    end: int,
    recorded: Trace,
    policy: Trace,
    *,
    elites: frozenset[int] = frozenset(),
    rate: float = 25.0,
    window: int = 75,
    idle_gap: int = 50,
    blade_life: int = 38,
    kill_gap: int = 25,
    miss_gap: int = 75,
    per_kind: int = 5,
) -> list[Moment]:
    """Return up to per_kind moments of each kind inside [start, end], sorted by (first, last, kind).

    The arguments are not modified. An end before start gives an empty list.
    """
    if end < start:
        return []
    moments: list[Moment] = []
    for diff, first, last in _pick_windows(_life_candidates(start, end, policy, recorded, window), per_kind):
        seconds = (last - first + 1) / rate
        label = f'{policy.name} took {diff:,.0f} more life in {seconds:.1f} s'
        moments.append(Moment(first, last, POLICY_AHEAD, label, diff))
    for diff, first, last in _pick_windows(_life_candidates(start, end, recorded, policy, window), per_kind):
        seconds = (last - first + 1) / rate
        label = f'recorded casts took {diff:,.0f} more life than {policy.name} in {seconds:.1f} s'
        moments.append(Moment(first, last, RECORDED_AHEAD, label, diff))
    moments += _idle_moments(start, end, recorded, policy, idle_gap=idle_gap, rate=rate, per_kind=per_kind)
    moments += _miss_moments(start, end, recorded, blade_life=blade_life, miss_gap=miss_gap, per_kind=per_kind)
    moments += _kill_moments(
        start, end, recorded, policy, elites=elites, kill_gap=kill_gap, rate=rate, per_kind=per_kind
    )
    return sorted(moments, key=lambda moment: (moment.first, moment.last, moment.kind))


def _clamp(tick: int, start: int, end: int) -> int:
    """Return the tick limited to the range [start, end]."""
    return min(max(tick, start), end)


def _split_taken(trace: Trace) -> tuple[list[int], list[float]]:
    """Return the tick and the life amount of each take as two parallel lists."""
    return [tick for tick, _ in trace.taken], [float(amount) for _, amount in trace.taken]


def _life_in(ticks: list[int], amounts: list[float], first: int, last: int) -> float:
    """Return the exact sum of the life taken with first <= tick <= last."""
    lo = bisect_left(ticks, first)
    hi = bisect_right(ticks, last)
    return fsum(amounts[lo:hi])


def _life_candidates(start: int, end: int, more: Trace, less: Trace, window: int) -> list[Window]:
    """Return every window in which `more` took strictly more life than `less`, with the difference."""
    step = max(1, window // 5)
    more_ticks, more_amounts = _split_taken(more)
    less_ticks, less_amounts = _split_taken(less)
    found: list[Window] = []
    for first in range(start, end + 1, step):
        last = min(first + window - 1, end)
        diff = _life_in(more_ticks, more_amounts, first, last) - _life_in(less_ticks, less_amounts, first, last)
        if diff > 0:
            found.append((diff, first, last))
    return found


def _pick_windows(candidates: list[Window], per_kind: int) -> list[Window]:
    """Greedily pick the largest windows (earlier first on ties) that share no tick, up to per_kind."""
    picked: list[Window] = []
    for candidate in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if len(picked) >= per_kind:
            break
        _, first, last = candidate
        if any(first <= other_last and other_first <= last for _, other_first, other_last in picked):
            continue
        picked.append(candidate)
    return picked


def _idle_moments(
    start: int, end: int, recorded: Trace, policy: Trace, *, idle_gap: int, rate: float, per_kind: int
) -> list[Moment]:
    """Return the quiet player gaps in which the policy cast on monsters at least twice."""
    policy_ticks = [tick for tick, _ in policy.casts]
    policy_touched = [touched for _, touched in policy.casts]
    bounds = [start - 1, *(tick for tick, _ in recorded.casts), end + 1]
    found: list[Moment] = []
    for gap_start, gap_end in pairwise(bounds):
        if gap_end - gap_start < idle_gap:
            continue
        lo = bisect_right(policy_ticks, gap_start)
        hi = bisect_left(policy_ticks, gap_end)
        hits = [tick for tick, touched in zip(policy_ticks[lo:hi], policy_touched[lo:hi], strict=True) if touched >= 1]
        if len(hits) < 2:
            continue
        seconds = (_clamp(gap_end, start, end) - _clamp(gap_start, start, end)) / rate
        label = f'{policy.name} cast {len(hits)} times on monsters while the player did not cast for {seconds:.1f} s'
        found.append(Moment(_clamp(hits[0], start, end), _clamp(hits[-1], start, end), IDLE, label, float(len(hits))))
    found.sort(key=lambda moment: (-moment.value, moment.first, moment.last))
    return found[:per_kind]


def _miss_moments(
    start: int, end: int, recorded: Trace, *, blade_life: int, miss_gap: int, per_kind: int
) -> list[Moment]:
    """Return the runs of consecutive recorded casts that touched nothing; a cast more than miss_gap ticks
    after the one before it starts a run of its own, so a run stays one stretch of play."""
    runs: list[tuple[int, int, int]] = []  # (first tick, last tick, number of casts)
    in_run = False
    for tick, touched in recorded.casts:
        if touched:
            in_run = False
        elif in_run and tick - runs[-1][1] <= miss_gap:
            first, _, count = runs[-1]
            runs[-1] = (first, tick, count + 1)
        else:
            runs.append((tick, tick, 1))
            in_run = True
    found: list[Moment] = []
    for first_tick, last_tick, count in runs:
        label = '1 recorded cast hit nothing' if count == 1 else f'{count} recorded casts in a row hit nothing'
        found.append(
            Moment(
                _clamp(first_tick, start, end),
                _clamp(last_tick + blade_life, start, end),
                MISS,
                label,
                float(count),
            )
        )
    found.sort(key=lambda moment: (-moment.value, moment.first, moment.last))
    return found[:per_kind]


def _kill_moments(
    start: int,
    end: int,
    recorded: Trace,
    policy: Trace,
    *,
    elites: frozenset[int],
    kill_gap: int,
    rate: float,
    per_kind: int,
) -> list[Moment]:
    """Return the elites whose death tick differs by at least kill_gap between the two runs."""
    found: list[Moment] = []
    for unit in sorted(elites):
        if unit not in recorded.deaths or unit not in policy.deaths:
            continue
        recorded_tick = recorded.deaths[unit]
        policy_tick = policy.deaths[unit]
        delta = recorded_tick - policy_tick
        if abs(delta) < kill_gap:
            continue
        seconds = abs(delta) / rate
        if delta > 0:
            label = f'an elite dies {seconds:.1f} s earlier under {policy.name}'
        else:
            label = f'an elite dies {seconds:.1f} s later under {policy.name}'
        first = _clamp(min(recorded_tick, policy_tick), start, end)
        last = _clamp(max(recorded_tick, policy_tick), start, end)
        found.append(Moment(first, last, KILL, label, delta / rate))
    found.sort(key=lambda moment: (-abs(moment.value), moment.first, moment.last))
    return found[:per_kind]
