"""The LONG_FIGHT of 2026-10-24 10:58:54-10:59:33 (take 20261024T075622Z-106, area 106, the KP_6 terror zone loop;
rca/2026-10-24/cast-hold-findings.md) as a situation: danger_fights.py `cut` from 10:58:53.0, a tier 5 Pit Lord
Herald pack (Cursed, Fire Enchanted, Extra Strong) with Grizzlies and others about, under the Cursed pack's Amplify
Damage. The take: 39 s, the life -421 in all, "fight casts held: blows of 3909 of 2943 can come within 1.0 s" x47 and
15 better-place jumps (macros/hunt.py FIGHT_CAST_REACH by macros/safety.py CAST_SECONDS; FIGHT_CAST_OWN).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.cast_hold --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.cast_hold --seeds 20
"""

import argparse
import functools
import json
import logging
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from inventory_tracking.common import LOG
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import MERCENARY, Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load, once
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'cast-hold-1058'
TAKE = '20261024T075622Z-106'
FIGHT = (TAKE, '2026-10-24T10:58:53.0')
SECONDS = 42.0
PLAYED = 45.0
TIER = 5


def cut() -> Situation:
    found = fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about='2026-10-24 10:58:53.0: the tier 5 Pit Lord Herald pack of the LONG_FIGHT (cast_hold.py)',
    )  # fmt: skip
    if found.orders is not None:
        found.orders = replace(found.orders, ends=SECONDS + 120.0)
    found.scene.mobs = [
        replace(mob, life=mob.full) if mob.owner is not None and mob.txt == MERCENARY else mob
        for mob in found.scene.mobs
    ]
    found.assumed.update({
        'orders': 'Battle Orders up through the play',
        'scene.mercenary': 'the mercenary at its full life',
    })  # fmt: skip
    return found


class Said(logging.Handler):
    """Counts the log lines holding `part` (the hold's line is the log's, not said)."""

    def __init__(self, part: str) -> None:
        super().__init__(logging.INFO)
        self.part, self.count = part, 0

    def emit(self, record: logging.LogRecord) -> None:
        if self.part in record.getMessage():
            self.count += 1


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def pursued(situation: Situation | None = None, seconds: float = PLAYED) -> Situation:
    """The fight as the live loop played it: the TZ run's pursuit, one pickup press, `seconds` long."""
    return (situation or stored()).logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def play(
    values: Mapping[str, bool], seed: int, situation: Situation | None = None, lap: float | None = 0.02
) -> tuple[fights.Measures, float, Outcome]:
    """One play of the pursuit with the fixes `values`: its measures, the lowest share of life before potions and the
    outcome."""
    from tests.inventory_tracking.scenarios.arena.situations.fane_death import play as fane_play

    dips = Dips()

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        dips(stage, routed)

    outcome = fane_play(pursued(situation), values, seed, lap=lap, extra=extra)
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome


def summary(seed: int, values: Mapping[str, bool] = ALL_ON) -> dict[str, Any]:
    """One play's measures: deaths, the least life, the kills, the tier 5 pack's kills and when its last fell, the
    rejuvenations, the jumps and the casts held said."""
    held = Said('fight casts held')
    level = LOG.level
    LOG.addHandler(held)
    LOG.setLevel(logging.INFO)
    try:
        measured, dip, outcome = play(values, seed)
    finally:
        LOG.removeHandler(held)
        LOG.setLevel(level)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    situation = stored()
    pack = {mob.unit for mob in situation.scene.mobs if mob.tier == TIER}
    pack |= {mob.unit for spawn in situation.spawns for mob in spawn.mobs if mob.tier == TIER}
    fell = [at for unit, at in stage.fell.items() if unit in pack]
    return {
        'dead': measured.dead_at, 'low': dip, 'kills': measured.kills, 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'pack': len(pack), 'pack_dead': len(fell),
        'pack_last': round(max(fell), 2) if len(fell) == len(pack) else None,
        'held': held.count, 'strikes': len(outcome.strikes),
    }  # fmt: skip


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situation from its take into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
    for seed in range(1, args.seeds + 1):
        print(json.dumps({'seed': seed, **summary(seed)}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
