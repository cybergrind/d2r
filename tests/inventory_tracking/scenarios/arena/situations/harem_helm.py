"""The helm by the idle tier 5 Herald pack, Harem Level 2, 03:35:24 on 2026-10-25 (take 20261025T003442Z-51, area 51,
the KP_6 terror zone loop; rca/2026-10-25/pickup-veto-pingpong-findings.md) as a situation: danger_fights.py `cut` from
03:35:24.2, the look after the fight's "Nothing left in reach", the character at (10066.5, 5607.5), full life (2908)
and mana, the Herald (the elite 31, unit 2412395574, Extra Fast) and 13 of his pack 15-30 off, with what the cut does
not hold put in as the log shows it:

- the Magic Alpha Helm at (10091, 5635) the run took on its way (03:35:10.6 "taken (shown)"), 18 from the Herald: a
  valuable under its code (dr6, the d2data dump's Alpha Helm), within buffs.py QUIET_BY_THE_BOSS's reach of him;
- the loop's legs (halls_death.py `Legs`): a level run that ends is posted again, as the loop's "TZ next level" legs.

The recording: 62 Teleports in 64 s with 0 kills (the goal by turns the helm and the Herald's fight across the
strike's reach, 22.1 from him), the fight from 03:36:28 when the pack came on, the helm taken at 03:36:37.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.harem_helm --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.harem_helm --seeds 20
"""

import argparse
import functools
import json
import math
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from inventory_tracking.macros import hunt
from tests.inventory_tracking.scenarios.arena.scene import Drop
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON, play as fane_play
from tests.inventory_tracking.scenarios.arena.situations.halls_death import Legs
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'harem-helm-0335'
TAKE = '20261025T003442Z-51'
FIGHT = (TAKE, '2026-10-25T03:35:24.2')
SECONDS = 64.0  # the take's dance and the fight after it
HERALD = 2412395574
HELM_AT = (10091.0, 5635.0)
HELM_CODE = 'dr6'  # Alpha Helm in pricing/raw/d2data-armor.json (never from memory)


def cut() -> Situation:
    found = fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about='2026-10-25 03:35:24.2: a helm 18 from an idle tier 5 Herald pack in Harem Level 2 (harem_helm.py)',
    )  # fmt: skip
    units = max([mob.unit for mob in found.scene.mobs] + [mob.unit for s in found.spawns for mob in s.mobs]) + 1
    found.scene.drops = [Drop(units, HELM_CODE, HELM_AT)]
    found.assumed['drops'] = f'the Magic Alpha Helm at {HELM_AT} (the log, 03:35:10.6), a valuable under its code'
    return found


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def holding(situation: Situation | None = None) -> Situation:
    """The pack holding its ground, as the take shows it for the dance (its members 15-30 off from 03:35:24 to
    03:35:43, none nearer than 12): the arena's walkers close on the character within their awareness, which these
    did not. The worst case for the dance: they never come."""
    found = situation or stored()
    pack = {mob.txt for mob in found.scene.mobs if not mob.ally and mob.owner is None}
    return found.variant(f'{NAME}-holding', speeds={**(found.speeds or {}), **dict.fromkeys(pack, 0.0)})


def pursued(situation: Situation | None = None, seconds: float = SECONDS) -> Situation:
    """The look as the live loop played it: the TZ run's pursuit, one pickup press, `seconds` long (`Legs` the rest)."""
    from tests.inventory_tracking.scenarios.arena.situations.situation import once

    return (situation or stored()).logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def helm_taken(stage: Stage) -> float | None:
    """The clock the helm was picked up at (`Stage.picks`), None: never."""
    return next((at for at, label in stage.picks if label == HELM_CODE), None)


def looped(routed: Any) -> None:
    """The level run as the KP_6 loop's leg posts it (runner.py `_loop_level_run`: `Pursuit.looped`), so a valuable
    Teleport brings in LOOP_PICK_SECONDS is on the way (hunting/choice.py `teleport_reach`), as the helm was."""
    hunter = getattr(routed, 'hunter', None)
    posted = getattr(hunter, 'pursuit', None)
    if hunter is not None and posted is not None and posted.leashed and not posted.looped:
        hunter.swap(posted, replace(posted, looped=True))


def play(
    hold: bool,
    seed: int,
    situation: Situation | None = None,
    values: Mapping[str, bool] = ALL_ON,
    *,
    loop: bool = True,
) -> tuple[fights.Measures, float, Outcome, int]:
    """One play with QUIET_HOLD `hold`: its measures, the lowest share of life, the outcome and the hops made within
    20 units of the start in the first 30 s (the take's dance: 62)."""
    found = situation or stored()
    dips, legs = Dips(), Legs()
    hero = found.scene.hero

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        if loop:
            looped(routed)
        if getattr(stage, 'held_at', None) is None and getattr(getattr(routed, 'hunter', None), 'quiet_holds', None):
            stage.held_at = round(stage.clock.now, 2)  # type: ignore[attr-defined]  # QUIET_HOLD's first hold
        legs(stage, routed)
        dips(stage, routed)

    kept = hunt.QUIET_HOLD
    setattr(hunt, 'QUIET_HOLD', hold)  # ruff: ignore[set-attr-with-constant] - the arm of this play
    try:
        outcome = fane_play(pursued(found), values, seed, lap=0.02, extra=extra)
    finally:
        setattr(hunt, 'QUIET_HOLD', kept)  # ruff: ignore[set-attr-with-constant]
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    dance = sum(1 for at, _, spot in stage.hops if at <= 30.0 and math.dist(spot, hero.at) <= 20.0)
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome, dance


def summary(seed: int, hold: bool, situation: Situation | None = None, loop: bool = True) -> dict[str, Any]:
    measured, dip, outcome, dance = play(hold, seed, situation, loop=loop)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    return {
        'seed': seed, 'hold': hold, 'loop': loop, 'held_at': getattr(stage, 'held_at', None),
        'dead': measured.dead_at, 'low': dip, 'kills': measured.kills,
        'first_kill': measured.first_kill, 'herald': stage.fell.get(HERALD), 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'dance': dance, 'helm': helm_taken(stage), 'strikes': len(outcome.strikes),
    }  # fmt: skip


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situation from its take into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--no-loop', action='store_true', help="a plain KP_1 run, not the loop's (`looped`)")
    parser.add_argument('--holding', action='store_true', help='the pack holds its ground (`holding`)')
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
    for seed in range(args.first, args.first + args.seeds):
        for hold in (False, True):
            found = holding() if args.holding else None
            print(json.dumps(summary(seed, hold, found, loop=not args.no_loop)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
