"""Radament in Sewers Level 3, 23:16:01 on 2026-10-22, as a situation (rca/2026-10-22/walled-boss-findings.md §2).

The take is 20261022T201417Z-49 (game cyberg65, the KP_6 terror zone loop's run). From 23:15:49 to 23:20:17 the
character made 98 safe approaches and 96 retreats round Radament (monstats 229, unit 881231773: Extra Fast, Mana Burn,
Extra Strong) with life 2943 of 2943 throughout: the harm model's conservative stand-in for a boss with no read AI
(combat/harm.py `stood_in`) priced every place within its radius near-lethal. Struck from 21 units at 23:20:17, he died
at 23:20:30.

The cut is danger_fights.py's (the level's walls, the blows capped at the game's most, the take's readings, the
terror zone's level, the takes' pace, awareness 35) at 23:16:01, the dance 12 s old, with the route's boss named
(record.py `bosses`), the pursuit loop on and the KP_1 level run pressed at the start, so the run's goal is the route's
own Radament fight as the loop's was; SECONDS long. Two things the arena would play otherwise are set as the take
shows them (`stored`): Radament holds his ground (HOLDS; the arena's walkers close on the character within their
awareness, his Greater Mummy AI did not), and the mana is shown (game.py MANA_SHOWN; the take read 587-745 of 745),
without which the safety keeps every Mana Burn hostile at range whatever it does.

24 seeds, 2026-10-23 (the fixes: macros/safety.py STAND_IN_EVIDENCE, combat/harm.py STAND_IN_TEMPER):

| fixes | deaths | Radament killed | median kill, s | lowest life | Teleports | retreats said |
| --- | --- | --- | --- | --- | --- | --- |
| off | 0/24 | 2/24 | 25.8 | 97% | 16.2 | 0.5 |
| on | 0/24 | 24/24 | 37.1 | 99% | 24.6 | 1.9 |

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.radament --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.radament --seeds 20
"""

import argparse
import functools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from tests.inventory_tracking.scenarios.arena.game import MANA_SHOWN
from tests.inventory_tracking.scenarios.arena.situations import danger_fights
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON, play
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load


NAME = 'radament-sewers'
TAKE = '20261022T201417Z-49'
CLOCK = '2026-10-22T23:16:01'
SECONDS = 90.0
RADAMENT = 881231773
HOLDS = 0.0  # units a second Radament walks in the play (`stored`)
# The fixes of this case (rca/2026-10-22/walled-boss-findings.md): their modules and names
FIXES = {
    'STAND_IN_EVIDENCE': ('inventory_tracking.macros.safety', 'STAND_IN_EVIDENCE'),
    'STAND_IN_TEMPER': ('inventory_tracking.combat.harm', 'STAND_IN_TEMPER'),
}


def cut() -> Situation:
    found = danger_fights.cut(
        NAME, (TAKE, CLOCK), SECONDS,
        about='Sewers Level 3, 2026-10-22 23:16:01: Radament priced by the stand-in, the dance 12 s old',
    )  # fmt: skip
    found.bosses = ((RADAMENT, 'Radament'),)
    found.pursuit = True
    found.presses = ((0.0, 'pickup'),)
    found.assumed.update({
        'route.bosses': 'Radament (monstats 229) is unit 881231773, the route\'s boss',
        'presses': 'the KP_1 level run pressed at the start: the loop\'s run, its goal the route\'s Radament fight',
        'pursuit': 'the pursuit loop on, as the KP_6 loop plays',
    })  # fmt: skip
    return found


@functools.cache
def stored() -> Situation:
    found = load(FIXTURES / f'{NAME}.json')
    found.pursuit = True  # not in the fixture's file (situation.py `dump`)
    # Radament holds his ground as the take shows him (HOLDS): the arena's walkers close on the character within
    # their awareness, which a Greater Mummy's AI did not do
    found.speeds = {**(found.speeds or {}), 229: HOLDS}
    # The mana as the live read showed it (691 of 699 at the cut, 587-745 through the fight): game.py MANA_SHOWN
    found.rules = (*found.rules, MANA_SHOWN)
    found.assumed['rules.mana shown'] = 'the mana shown and never spent: the take read 587-745 of 745 throughout'
    found.assumed['speeds.229'] = (
        'Radament stands: in the take (frames 23:15:49-23:20:17) he kept within 26 units of (7700, 8018) for 4.5 '
        'minutes and never came nearer the character than 14; his Greater Mummy AI is not read'
    )
    return found


@dataclass(frozen=True)
class Plays:
    seed: int
    dead: bool
    radament_at: float | None  # seconds into the play Radament died, None: alive at the end
    low_share: float
    teleports: int
    retreats: int


def fixes(on: bool) -> dict[str, bool]:
    return dict.fromkeys(FIXES, on)


@functools.cache
def switch_table() -> dict[str, tuple[object, str]]:
    import importlib

    return {name: (importlib.import_module(module), attr) for name, (module, attr) in FIXES.items()}


def played(on: bool, seed: int, base: Mapping[str, bool] = ALL_ON) -> Plays:
    table = switch_table()
    saved = {name: getattr(*table[name]) for name in table}
    for name in table:
        setattr(*table[name], on)
    try:
        outcome: Outcome = play(stored(), base, seed, lap=0.02)
    finally:
        for name, value in saved.items():
            setattr(*table[name], value)
    stage = outcome.stage_  # type: ignore[attr-defined]
    lows = getattr(stage, 'low_shares', [])
    return Plays(
        seed=seed,
        dead=outcome.dead_at is not None,
        radament_at=stage.fell.get(RADAMENT),
        low_share=round(min(lows, default=1.0), 3),
        teleports=len(stage.hops),
        retreats=outcome.said_count('retreat'),
    )


def row(label: str, plays: Sequence[Plays]) -> str:
    killed = [p.radament_at for p in plays if p.radament_at is not None]
    return (
        f'| {label} | {sum(p.dead for p in plays)}/{len(plays)} | {len(killed)}/{len(plays)} | '
        f'{(sorted(killed)[len(killed) // 2] if killed else float("nan")):.1f} | '
        f'{min(p.low_share for p in plays):.0%} | {sum(p.teleports for p in plays) / len(plays):.1f} | '
        f'{sum(p.retreats for p in plays) / len(plays):.1f} |'
    )


HEAD = (
    '| fixes | deaths | Radament killed | median kill, s | lowest life | Teleports | retreats said |\n'
    '| --- | --- | --- | --- | --- | --- | --- |'
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true')
    parser.add_argument('--seeds', type=int, default=5)
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
        return 0
    seeds = range(1, args.seeds + 1)
    print(HEAD)
    for label, on in (('off', False), ('on', True)):
        print(row(label, [played(on, seed) for seed in seeds]), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
