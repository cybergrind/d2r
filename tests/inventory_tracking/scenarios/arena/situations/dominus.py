"""The Dominus Herald's burst after the portal return (2026-10-23 04:35:48, Icy Cellar; take 20261023T013533Z-119;
rca/2026-10-23/dominus-burst-findings.md) as a situation: danger_fights.py `cut` from 04:35:40 for 20 s (the walls,
each unit's stat 25, the Terror Zone's level, the take's pace, the curses as the frames show them), with the pack's
bolts as the take shows them, since the arena's pooled shooter fit (2.4 % of shots take life, one missile a shot at
20.6 units a second) holds none of it:

- every Dominus (txt 636) shoots `succubusmiss` (missiles.txt 665) volleys of VOLLEY bolts (monumod 29 Multiple
  Shots on every member) at BOLT_SPEED (sim/monsters.py `Pack.bolts`), read in flight by the macro as the live
  client's missile list is (mobs.py `Mobs.flights`);
- the take's 20 s had 32 bolts read in flight, 12 reach the character and 7 take life (one volley of 3 among them);
  the pooled fit's pack lets go some 30 volleys in that time, 22 at the character: the gap between a Dominus' shots
  is GAP times the fit's, and a volley sent at the character takes life with LANDS, one roll for its bolts;
- a bolt's raw points SHOT (physical, magic): the take's four big bolts took 326-749 with the ward down, the
  physical part through the character's 18 % reduction and the ward's pool.

The recording: life 2672 -> 971 in 0.17 s at 15.0-15.2 s of the take (7.4-7.6 s into the play), lowest share 0.33.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.dominus --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.dominus --seeds 20
"""

import argparse
import functools
from collections.abc import Mapping
from typing import Any

from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'dominus-0535'
FIGHT = ('20261023T013533Z-119', '2026-10-23T04:35:40')
DOMINUS, BOLT = 636, 665
VOLLEY = 3
BOLT_SPEED = 10.1  # units a second (the take's frames)
LANDS = 0.35
GAP = 3.0
SHOT = {'physical': 380.0, 'magic': 380.0}  # raw points of a bolt at its most (the module text)
RECORDED_LOW = 971 / 2943


def cut() -> Situation:
    found = fights.cut(NAME, fight=FIGHT, about='2026-10-23 04:35:40: the Dominus Herald burst (dominus.py)')
    found.assumed.update({
        'bolts': f'every Dominus shoots volleys of {VOLLEY} bolts (class {BOLT}) at {BOLT_SPEED} units a second, '
        f'{GAP} times the gap, a volley at the character takes life with {LANDS}, {SHOT} raw at most (dominus.py)',
    })  # fmt: skip
    return found


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def armed(stage: Stage, _routed: Any) -> None:
    """At each tick: every Dominus shoots the take's bolts (the module text), from its first shot on."""
    pack = stage.cast.pack
    for unit, walker in pack.walkers.items():
        if walker.txt == DOMINUS and unit not in pack.bolts and unit in pack.shots:
            pack.bolts[unit] = (BOLT, VOLLEY, BOLT_SPEED, LANDS, GAP)
            pack.shots[unit] = dict(SHOT)


class Dips:
    """The lowest share of the most life the blows of a tick leave before that tick's potions (a Rejuvenation the
    healer drinks at the tick of the burst fills the life before `Measures.low_share` samples it)."""

    def __init__(self) -> None:
        self.life: float | None = None
        self.taken = 0.0
        self.low = 1.0

    def __call__(self, stage: Stage, routed: Any) -> None:
        armed(stage, routed)
        if self.life is not None and stage.max_life:
            self.low = min(self.low, (self.life - (stage.taken - self.taken)) / stage.max_life)
        self.life, self.taken = stage.life, stage.taken


def play(values: Mapping[str, bool], seed: int, situation: Situation | None = None) -> tuple[fights.Measures, float]:
    """One play: its measures and the lowest share of life before potions (`Dips`)."""
    from tests.inventory_tracking.scenarios.arena.situations.fane_death import play as fane_play

    dips = Dips()
    measured = fights.measures(fane_play(situation or stored(), values, seed, extra=dips))
    return measured, round(max(dips.low, 0.0), 3)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situation from its take into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
    for seed in range(1, args.seeds + 1):
        print(play(ALL_ON, seed))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
