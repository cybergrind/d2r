"""halls_death.py's fight cut EARLY: from 2026-10-23 23:30:22.0, before Amplify Damage came on (23:30:27.41), with the
Cursed (monumod 7) unique Hollow One 1316109150 and its pack alive, to price combat/harm.py CURSED_PRICED against the
death (the coordinator, 2026-10-24: "We need off to die and on to survive, before CURSED_PRICED can go live under the
survival rule"; rca/2026-10-24/cast-hold-findings.md §3-4).

The take (V): Amplify Damage (state 9) on from the take's start until 23:29:57.7 (the level before's), off until
23:30:27.41, then on to the death (23:31:06.44), physical resistance 18 -> -82 (x1.82 through). No hurt was recorded at
the onset: the curse was cast, not struck on. The Hollow One was targeted at 23:30:24.2, dead at 23:30:31.2; the
omen showed at 23:30:36.08 (missile 737, its spot the log's (15202.5, 8087.5)), the Herald pack at 23:30:41.5.

What the cut does not hold, put in:

- the curse by rule, not at the take's time (`Cursing`): each live Cursed hostile within CURSE_RANGE of the character
  puts Amplify Damage on it at 1 / CURSE_SECONDS a second; on, the physical share the take read (x1.82) holds to the
  play's end. The numbers are the takes' (scratchpad hold/curse.py, 2026-10-24: 21 onsets of state 9, 13 with a Cursed
  hostile about, a median 1.1 s after the nearest came within 20), not harm.py's (15, 1.0 s);
- the omen (herald_omen.py `Omen`) at its time and spot, so the level run waits on the stand as in the take;
- the drops by the stand (halls_death.py DROPS) from the start: in the take they fell in the fight there (23:30:32-40);
- the loop's legs, the mercenary's fall and the Terror Zone as halls_death.py plays them.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.halls_curse --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.halls_curse --seeds 20
"""

import argparse
import functools
import json
import math
import random
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from tests.inventory_tracking.scenarios.arena.scene import Drop
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights, halls_death as halls
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.herald_omen import Omen
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'halls-curse-2330'
CLOCK = '2026-10-23T23:30:22.0'
FIGHT = (halls.TAKE, CLOCK)
EARLY = 22.0  # s before halls_death.py's cut (23:30:44.0)
SECONDS = halls.SECONDS + EARLY
PLAYED = halls.PLAYED + EARLY
HOLLOW_ONE = 1316109150
CURSED = 7  # monumod 'curse' (evidence/curses.py CURSED)
CURSE_RANGE = 20.0  # units: the takes' onsets (module text)
CURSE_SECONDS = 1.1  # s a Cursed hostile within CURSE_RANGE takes to put the curse on, on the mean
OMEN_SPOT = (15202.5, 8087.5)
OMEN_SHOWS = 14.08  # s into the play: 23:30:36.08
AMPLIFIED = 1.82  # the physical share through under the curse: the take's resistance -82 (`cut` checks it)
FALLS = {txt: at + EARLY for txt, at in halls.FALLS.items()}


def cut() -> Situation:
    found = fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about="2026-10-23 23:30:22.0: the Cursed Hollow One's pack in Halls of the Dead Level 2, then the omen and "
        'the tier 5 Herald pack on its stand (halls_curse.py)',
    )  # fmt: skip
    if found.orders is not None:  # Battle Orders went off with the death only
        found.orders = replace(found.orders, ends=SECONDS + 120.0)
    physical = [row for row in found.curses if row[1] == 'physical']
    assert physical, found.curses
    assert round(physical[0][2], 2) == AMPLIFIED, physical
    found.curses = tuple(row for row in found.curses if row[1] != 'physical')  # the rule's (`Cursing`)
    found.assumed['curses'] = f"Amplify Damage by `Cursing`, not the take's onset {physical[:1]}"
    found.scene.mobs = [
        replace(mob, life=mob.full) if mob.owner is not None and mob.txt == halls.MERCENARY else mob
        for mob in found.scene.mobs
    ]
    units = max([mob.unit for mob in found.scene.mobs] + [mob.unit for s in found.spawns for mob in s.mobs]) + 1
    code = halls.potion_code()
    found.scene.drops = [
        Drop(units + index, code if kind == 'potion' else 'gold', at, gold=gold)
        for index, (kind, at, gold) in enumerate(halls.DROPS)
    ]
    found.assumed.update({
        'orders': 'Battle Orders up through the play (its state went off with the death)',
        'scene.mercenary': 'the mercenary at its full life',
        'drops': f'the drops by the stand from the start (the take: fallen there 23:30:32-40): {list(halls.DROPS)}',
        'omen': f'the omen at {OMEN_SPOT} from {OMEN_SHOWS} s to the pack (herald_omen.py `Omen`)',
    })  # fmt: skip
    return found


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


class Cursing:
    """An `each_tick`: Amplify Damage on the character by the rule of the module text, with its own random stream (the
    pack's rolls untouched). `at`: when it came on; None: never."""

    def __init__(self, seed: int, share: float, on: bool = True) -> None:
        self.rng = random.Random(seed * 104_729 + 7)
        self.share, self.on = share, on
        self.at: float | None = None
        self.last: float | None = None

    def __call__(self, stage: Stage, _routed: Any) -> None:
        now = stage.clock.now
        tick, self.last = (0.0 if self.last is None else now - self.last), now
        if not self.on or self.at is not None or stage.world.player is None or tick <= 0:
            return
        me = (stage.world.player.x, stage.world.player.y)
        near = sum(
            1 for m in stage.world.monsters
            if not m.ally and CURSED in m.modifiers and math.dist((m.x, m.y), me) <= CURSE_RANGE
        )  # fmt: skip
        if near and self.rng.random() < 1.0 - math.exp(-near * tick / CURSE_SECONDS):
            self.at = now
            for resist in stage.resists:
                resist['physical'] = self.share


def play(
    values: Mapping[str, bool],
    seed: int,
    situation: Situation | None = None,
    lap: float | None = 0.02,
    curse: bool = True,
) -> tuple[fights.Measures, float, Any, halls.Legs, Cursing, Omen]:
    """One play with the fixes `values` (halls_death.py `play`, with `Cursing` and the omen); `curse` False: none."""
    from tests.inventory_tracking.scenarios.arena.situations.fane_death import play as fane_play

    found = situation or stored()
    spawn = min((s.at for s in found.spawns if s.at is not None), default=SECONDS)
    dips, legs = Dips(), halls.Legs()
    cursing = Cursing(seed, AMPLIFIED, on=curse)
    omen = Omen(OMEN_SPOT, OMEN_SHOWS, spawn)
    gone = dict(halls.FALLS)

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        omen(stage, routed)
        cursing(stage, routed)
        halls.falls(stage, routed)
        legs(stage, routed)
        dips(stage, routed)

    halls.FALLS.clear()
    halls.FALLS.update(FALLS)
    try:
        outcome = fane_play(halls.pursued(found, PLAYED), values, seed, lap=lap, extra=extra)
    finally:
        halls.FALLS.clear()
        halls.FALLS.update(gone)
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome, legs, cursing, omen


def summary(seed: int, values: Mapping[str, bool] = ALL_ON, curse: bool = True) -> dict[str, Any]:
    measured, dip, outcome, legs, cursing, _ = play(values, seed, curse=curse)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    return {
        'seed': seed, 'dead': measured.dead_at, 'low': dip, 'kills': measured.kills, 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'legs': legs.legs, 'strikes': len(outcome.strikes), 'ended': outcome.said_count('over'),
        'cursed_at': None if cursing.at is None else round(cursing.at, 2), 'hollow': stage.fell.get(HOLLOW_ONE),
        'reviver': stage.fell.get(halls.REVIVER),
    }  # fmt: skip


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situation from its take into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    parser.add_argument('--no-curse', action='store_true')
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
    for seed in range(1, args.seeds + 1):
        print(json.dumps(summary(seed, curse=not args.no_curse)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
