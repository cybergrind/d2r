"""The approach/retreat dance by an idle tier 5 Herald pack, Maggot Lair Level 3, 03:55:31 on 2026-10-25 (take
20261025T005528Z-64, area 64, the KP_6 terror zone loop; rca/2026-10-25/approach-retreat-findings.md) as a situation:
danger_fights.py `cut` from 03:55:31.2, the character at (17678, 8076) with full life (2908), the pack of txt 93 (the
elite 1466204337 and 14 of his pack, Invaders) 9-45 off, the loop's legs (halls_death.py `Legs`) and the run marked as
the loop's (harem_helm.py `looped`), as the live loop posts it.

The recording: from 03:55:31 to 03:58:36 a safe approach and a retreat by turns (21 of 37 looks "every progress act is
vetoed (kept at range: ...)"), each goal given up by STILL_BUDGET after ~5 s and the next one (the agenda's chest by
the same pack) danced on: 125 s, 24 strikes. pursuit.py STAND_NOT_RETREAT is the arm.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.maggot_approach --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.maggot_approach --seeds 20
"""

import argparse
import functools
import json
import math
from collections.abc import Mapping
from typing import Any

from inventory_tracking.macros import pursuit
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON, play as fane_play
from tests.inventory_tracking.scenarios.arena.situations.halls_death import Legs
from tests.inventory_tracking.scenarios.arena.situations.harem_helm import looped
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'maggot-approach-0355'
TAKE = '20261025T005528Z-64'
FIGHT = (TAKE, '2026-10-25T03:55:31.2')
SECONDS = 40.0
ELITE = 1466204337


def cut() -> Situation:
    return fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about='2026-10-25 03:55:31.2: the approach/retreat dance by an idle tier 5 Herald pack in Maggot Lair Level 3 '
        '(maggot_approach.py)',
    )  # fmt: skip


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def holding(situation: Situation | None = None) -> Situation:
    """The pack holding its ground (the take: 11 of its 15 moved under 2 units over the dance), the worst case for the
    dance: the arena's walkers close on the character within their awareness, which these did not."""
    found = situation or stored()
    pack = {mob.txt for mob in found.scene.mobs if not mob.ally and mob.owner is None}
    return found.variant(f'{NAME}-holding', speeds={**(found.speeds or {}), **dict.fromkeys(pack, 0.0)})


def pursued(situation: Situation | None = None, seconds: float = SECONDS) -> Situation:
    """The look as the live loop played it: the TZ run's pursuit, one pickup press, `seconds` long (`Legs` the rest)."""
    from tests.inventory_tracking.scenarios.arena.situations.situation import once

    return (situation or stored()).logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def play(
    stand: bool, seed: int, situation: Situation | None = None, values: Mapping[str, bool] = ALL_ON
) -> tuple[fights.Measures, float, Outcome, int]:
    """One play with STAND_NOT_RETREAT `stand`: its measures, the lowest share of life, the outcome and the hops made
    within 25 units of the start in the first 20 s (the take's dance)."""
    found = situation or stored()
    dips, legs = Dips(), Legs()
    hero = found.scene.hero

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        looped(routed)
        legs(stage, routed)
        dips(stage, routed)

    kept = pursuit.STAND_NOT_RETREAT
    setattr(pursuit, 'STAND_NOT_RETREAT', stand)  # ruff: ignore[set-attr-with-constant] - the arm of this play
    try:
        outcome = fane_play(pursued(found), values, seed, lap=0.02, extra=extra)
    finally:
        setattr(pursuit, 'STAND_NOT_RETREAT', kept)  # ruff: ignore[set-attr-with-constant]
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    dance = sum(1 for at, _, spot in stage.hops if at <= 20.0 and math.dist(spot, hero.at) <= 25.0)
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome, dance


def summary(seed: int, stand: bool, situation: Situation | None = None) -> dict[str, Any]:
    measured, dip, outcome, dance = play(stand, seed, situation)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    return {
        'seed': seed, 'stand': stand, 'dead': measured.dead_at, 'low': dip, 'kills': measured.kills,
        'first_kill': measured.first_kill, 'elite': stage.fell.get(ELITE), 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'dance': dance, 'strikes': len(outcome.strikes),
    }  # fmt: skip


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situation from its take into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--holding', action='store_true', help='the pack holds its ground (`holding`)')
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
    for seed in range(args.first, args.first + args.seeds):
        for stand in (False, True):
            found = holding() if args.holding else None
            print(json.dumps(summary(seed, stand, found)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
