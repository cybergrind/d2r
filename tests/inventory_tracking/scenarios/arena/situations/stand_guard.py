"""The stand after a stop of the loop's own, with the stand guard off and on (macros/guard.py; rca/2026-10-22/
guard-findings.md). The player, 2026-10-22 ~20:50: "we're standing without enabled fight under heavy damage".

20:48:09 on 2026-10-22, cyberg65 (Shard: Act 1), the Arcane Sanctuary: the loop stopped itself by a Superior Flail it
had no room for ("... lies on the ground: the loop stops here"), attack mode off; the character stood 3.5 min under
three hostiles' fire (take 20261022T174637Z-74). `stand-arcane-2048` is that stand, cut from 20:48:10 for SECONDS
with danger_fights.py's steps (the level's walls, the blows capped and raised by each unit's stat 25, the Terror Zone's
level, the takes' pace, the client's 0.4 s life read, an awareness of 35): no press, attack mode off.

Each play arms the guard as the loop's stop does (running/recovery.py `_stop_loop`, the production path, at the play's
first tick) and gives it the service poll's looks every POLL seconds from POLL_FIRST (running/watch.py `poll`; the
arena plays no poll: `look` makes the poll's look from the arena's world and the client's life read). Off: the switch
GUARD off, the stand as it was. On: the guard's verdicts act on the production runner (`MacroRunner.guard_watch`).

The other dangerous fights (fane-death-24, -20 and the thirteen danger fights, fane_death.py, danger_fights.py) are
played the same way as stands: the loop stopped itself at the cut's start, attack mode off, no press.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.stand_guard --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.stand_guard --seeds 20 [--jobs 3]
"""

import argparse
import functools
import statistics
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any

from inventory_tracking.macros import guard
from inventory_tracking.macros.actuator import Abort
from tests.inventory_tracking.scenarios.arena.situations import danger_fights, fane_death
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'stand-arcane-2048'
TAKE = '20261022T174637Z-74'
CLOCK = '2026-10-22T20:48:10'  # local (+03:00): a second after the stop
SECONDS = 60.0
# The stop's own line (probe.log 20:48:09.052)
STOP = (
    'Superior Flail at (25088, 5474) was not picked up after 2 trips back; Superior Flail lies on the ground: the '
    'loop stops here'
)
POLL = 1.0  # the service poll's beat (running/base.py JOURNEY_SECONDS)
POLL_FIRST = 1.0  # the first look a whole beat after the stop: the latest a poll comes
# The stands played: the 20:48 one, then the other dangerous fights as stands
STANDS = (NAME, 'fane-death-24', 'fane-death-20', *sorted(danger_fights.FIGHTS))


def cut() -> Situation:
    return danger_fights.cut(
        NAME, (TAKE, CLOCK), SECONDS,
        about=f'{CLOCK}: the stand after the loop stopped itself by a Superior Flail (stand_guard.py)',
    )  # fmt: skip


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


def stand(name: str) -> Situation:
    """The situation `name` as a stand: no press, attack mode off at the start (the loop's stop left it off)."""
    return stored(name).variant(f'{name}, standing', presses=(), attack=False)


def play(situation: Situation, on: bool, seed: int, *, lap: float | None = 0.02) -> Outcome:
    """One stand with the guard `on` or off, every fix of fane_death.py on."""
    state: dict[str, Any] = {'next': POLL_FIRST, 'armed': False}

    def extra(stage: Stage, routed: Any) -> None:
        runner = routed.runner
        if not state['armed']:
            state['armed'] = True
            with runner.lock:
                runner.loop.on = True  # the loop that stops itself
                runner._stop_loop(Abort(STOP))
        now = stage.clock.now
        if now + 1e-9 < state['next'] or stage.over is not None:
            return
        state['next'] = now + POLL
        life = (int(stage.loot.life), int(stage.loot.max_life))
        with runner.lock:
            runner.guard_watch(runner.guard_look_of(stage.world, now, life))

    kept = guard.GUARD
    guard.GUARD = on
    try:
        return fane_death.play(situation, ALL_ON, seed, lap=lap, extra=extra)
    finally:
        guard.GUARD = kept


@dataclass(frozen=True)
class Measures:
    seed: int
    dead_at: float | None
    low_share: float
    taken: float
    kills: int
    retreats: int
    fights: int  # the guard's FIGHTs

    @property
    def dead(self) -> bool:
        return self.dead_at is not None


def measures(outcome: Outcome) -> Measures:
    found = danger_fights.measures(outcome)
    return Measures(
        seed=outcome.seed,
        dead_at=outcome.dead_at,
        low_share=found.low_share,
        taken=outcome.taken,
        kills=found.kills,
        retreats=found.retreats,
        fights=outcome.said_count('Guard: fighting back'),
    )


def played(name: str, on: bool, seeds: Sequence[int]) -> list[Measures]:
    return [measures(play(stand(name), on, seed)) for seed in seeds]


HEAD_ROW = (
    '| stand, guard | deaths | first death, s | lowest life (least / median) | life taken (mean) | kills (mean) '
    '| retreats (mean) | guard fights (mean) |\n| --- | --- | --- | --- | --- | --- | --- | --- |'
)


def row_text(label: str, plays: Sequence[Measures]) -> str:
    died = [p.dead_at for p in plays if p.dead_at is not None]
    lows = [p.low_share for p in plays]
    return (
        f'| {label} | {len(died)}/{len(plays)} | {"-" if not died else f"{min(died):.1f}"} | '
        f'{min(lows):.0%} / {statistics.median(lows):.0%} | {statistics.fmean(p.taken for p in plays):.0f} | '
        f'{statistics.fmean(p.kills for p in plays):.1f} | {statistics.fmean(p.retreats for p in plays):.1f} | '
        f'{statistics.fmean(p.fights for p in plays):.1f} |'
    )


def _row(job: tuple[str, bool, tuple[int, ...]]) -> tuple[str, bool, list[Measures]]:
    name, on, seeds = job
    return name, on, played(name, on, seeds)


def table(names: Sequence[str], seeds: Sequence[int], jobs: int = 1) -> Mapping[tuple[str, bool], list[Measures]]:
    work = [(name, on, tuple(seeds)) for name in names for on in (False, True)]
    if jobs <= 1:
        return {(name, on): plays for name, on, plays in map(_row, work)}
    with ProcessPoolExecutor(jobs) as pool:
        return {(name, on): plays for name, on, plays in pool.map(_row, work)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help=f'cut {NAME} again from its take')
    parser.add_argument('--seeds', type=int, default=5)
    parser.add_argument('--jobs', type=int, default=1, help='processes (3 at most while the game runs)')
    parser.add_argument('--name', action='append', choices=STANDS)
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
        return 0
    names = args.name or list(STANDS)
    found = table(names, range(1, args.seeds + 1), args.jobs)
    print(HEAD_ROW)
    for name in names:
        for on in (False, True):
            print(row_text(f'{name}, {"on" if on else "off"}', found[name, on]), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
