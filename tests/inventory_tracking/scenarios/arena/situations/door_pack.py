"""A tier 5 Mana Burn Herald pack behind a closed door, given up with no strike, as situations
(rca/2026-10-25/door-pack-findings.md, rca/2026-10-25/tactics/apply-door.md): danger_fights.py `cut` of

- `door-pack-1112`: Catacombs Level 3, 11:12:50 on 2026-10-25 (take 20261025T081241Z-36): 15 members (txt 7) north of
  a closed DoorWoodenRight at (22540, 8250), every approach vetoed by the burn keep range, the pack passed at 11:13:04
  and 11:13:45 (STILL_BUDGET, DANCE_BUDGET) with life 2908/2908 throughout;
- `door-viper-0326`: Claw Viper Temple Level 1, 03:26:11 on 2026-10-23 (take 20261023T002432Z-58,
  rca/2026-10-23/approach-veto-findings.md): 15 Claw Vipers (txt 74) of a tier 5 Mana Burn pack 2.5 behind a closed
  door at (15121, 9585), 330 jumps and no strike in 5 minutes,

played as the live run did (the TZ run's pursuit, one pickup press, its legs, the level a terror zone: full clear),
with the arena's doors opened by a click (game.py DOORS_OPEN) and the pets as the game plays them.
macros/hunting/moves.py DOOR_FIGHT is the arm.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.door_pack --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.door_pack --seeds 20
"""

import argparse
import functools
import json
from collections.abc import Mapping
from typing import Any

from inventory_tracking.macros.hunting import moves
from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON, play as fane_play
from tests.inventory_tracking.scenarios.arena.situations.halls_death import Legs
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load, once
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


SECONDS = 40.0
CUTS: dict[str, tuple[str, str]] = {
    'door-pack-1112': ('20261025T081241Z-36', '2026-10-25T11:12:50.0'),
    'door-viper-0326': ('20261023T002432Z-58', '2026-10-23T03:26:11.0'),
}
PACK_TIER = 4


def cut(name: str) -> Situation:
    return fights.cut(
        name, fight=CUTS[name], seconds=SECONDS,
        about=f'{CUTS[name][1]}: a tier 5 Mana Burn pack behind a closed door, given up with no strike (door_pack.py)',
    )  # fmt: skip


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


def pursued(situation: Situation, seconds: float = SECONDS) -> Situation:
    """The look as the live loop played it: the TZ run's pursuit, one pickup press, `seconds` long."""
    return situation.logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def play(
    on: bool, seed: int, name: str = 'door-pack-1112', values: Mapping[str, bool] = ALL_ON, *, pets: bool = True
) -> tuple[fights.Measures, float, Outcome, dict[str, Any]]:
    """One play with DOOR_FIGHT `on` (the arena's doors open by a click, the pets as the game plays them with every
    one taken along): its measures, the lowest share of life, the outcome and the door's measures (the doors opened,
    the pack's members killed, the first of them)."""
    found = stored(name)
    dips, legs = Dips(), Legs()

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        legs(stage, routed)
        dips(stage, routed)

    names = ('DOORS_OPEN', 'ALONG_ALL', *(game.PETS_AS_GAME if pets else ()))
    saved = {attr: getattr(game, attr) for attr in names}
    kept = moves.DOOR_FIGHT
    for attr in names:
        setattr(game, attr, True)
    moves.DOOR_FIGHT = on  # pyrefly: ignore[bad-assignment]
    try:
        outcome = fane_play(pursued(found), values, seed, lap=0.02, extra=extra)
    finally:
        moves.DOOR_FIGHT = kept
        for attr, value in saved.items():
            setattr(game, attr, value)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    pack = {unit for unit, mob in stage.mobs.mobs.items() if mob.tier >= PACK_TIER}
    fell = sorted(at for unit, at in stage.fell.items() if unit in pack)
    door = {'opened': list(stage.doors_opened), 'pack_killed': len(fell), 'first': fell[0] if fell else None}
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome, door


def summary(seed: int, on: bool, name: str) -> dict[str, Any]:
    measured, dip, outcome, door = play(on, seed, name)
    return {
        'name': name, 'seed': seed, 'on': on, 'dead': measured.dead_at, 'low': dip, 'kills': measured.kills,
        'rejuv': measured.rejuvenations, 'hops': measured.hops, 'strikes': len(outcome.strikes), **door,
    }  # fmt: skip


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situations from their takes into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--name', action='append', choices=sorted(CUTS))
    args = parser.parse_args(argv)
    names = args.name or sorted(CUTS)
    if args.cut:
        for name in names:
            dump(cut(name), FIXTURES / f'{name}.json')
        stored.cache_clear()
    for name in names:
        for seed in range(args.first, args.first + args.seeds):
            for on in (False, True):
                print(json.dumps(summary(seed, on, name)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
