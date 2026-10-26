"""The mana leave's bounce in Tal Rasha's tomb, 2026-10-26 01:38:51-01:39:08 (take 20261025T223823Z-71, area 71, the
KP_6 terror zone loop; combat/threats/manaburn.py RECOVERING) as a situation: danger_fights.py `cut` from 01:38:51.0,
as the character Teleported into a pack of plain Extra Fast Apparitions (monstats 41, wraith4: their A1 carries the
mana element, El1Pct(H) 60, 200-300, combat/threats/drain_escape.py MANA_ELEMENT) with the Preserved Dead (94) and
Steel Weevils (99) about. The take: 496 of 750 mana burnt at 01:38:54.15 with four Apparitions 2-3 off, then 22
leaves and 13 Teleports back in over 13 s, 0 kills, the mana 265 -> 383; the pack died at 01:39:08-09.

The mana the arena does not count is played as manaburn_death.py's `Mana` plays it (the regeneration, the costs, a
Rejuvenation's fill), with the burn of this take's type: each Apparition within CONTACT of the character lands a
burning blow CONTACT_RATE a second (`Burns`), its row's chance and roll (MANA_BLOW); their life damage is the arena's
own melee. CONTACT is wider than the take's 2-3: the arena's bodies keep the members farther off.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.tomb_drain --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.tomb_drain --seeds 20
"""

import argparse
import functools
import json
import math
import random
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from inventory_tracking.combat.sim.monsters import GAME_RATE
from inventory_tracking.combat.threats import drain_escape
from tests.inventory_tracking.scenarios.arena.game import MANA_SHOWN
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights, manaburn_death as burnt
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load, once
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'tomb-drain-0138'
TAKE = '20261025T223823Z-71'
FIGHT = (TAKE, '2026-10-26T01:38:51.0')
SECONDS = 18.0
PLAYED = 30.0
APPARITION = 41
MANA_BLOW = {APPARITION: drain_escape.MANA_ELEMENT[APPARITION]}
# Units within which an Apparition's blow lands: the take's burn came from four 2-3 off the character (01:38:54.15);
# the arena's bodies keep a melee member 4-6 off it (seed 1: 5.2-5.7 at 2-3 s)
CONTACT = 6.0
CONTACT_RATE = burnt.CONTACT_RATE


def cut() -> Situation:
    found = fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about='2026-10-26 01:38:51.0: plain Extra Fast Apparitions in Tal Rasha\'s tomb (tomb_drain.py)',
    )  # fmt: skip
    hero = found.scene.hero
    found.scene.hero = replace(hero, mana=hero.max_mana or 750.0, max_mana=hero.max_mana or 750.0)
    found.rules = tuple(sorted({*found.rules, MANA_SHOWN}))
    found.assumed.update({
        'mana': f'regenerated at {burnt.REGEN}/s, spent {burnt.COSTS}, burnt by each blow of an Apparition within '
        f'{CONTACT} ({CONTACT_RATE} a second, {MANA_BLOW}), filled by a Rejuvenation (tomb_drain.py `Burns`)',
    })  # fmt: skip
    return found


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


class Mana(burnt.Mana):
    """manaburn_death.py's mana with this take's burning type (MANA_BLOW)."""

    def __call__(self, stage: Stage, _routed: Any) -> None:
        if not self.hooked:
            self.hook(stage)
        if stage.over is not None:
            return
        now = stage.clock.now
        mana = self.get(stage) + burnt.REGEN / GAME_RATE
        for txt in self.blows:
            chance, least, most = MANA_BLOW[txt]
            if self.rolls.random() < chance:
                points = self.rolls.uniform(least, most)
                mana -= points
                self.burns.append((now, points))
        self.blows = []
        self.put(stage, mana)
        self.series.append((now, self.get(stage)))
        stage.show()


class Burns:
    """Each tick each live Apparition within CONTACT of the character lands a blow with CONTACT_RATE / GAME_RATE, its
    type handed to `Mana` for the burn."""

    def __init__(self, seed: int, mana: Mana) -> None:
        self.rolls = random.Random(seed * 3_571 + 71)
        self.mana = mana

    def __call__(self, stage: Stage, _routed: Any) -> None:
        if stage.over is not None:
            return
        here, mobs = stage.here, stage.cast.mobs
        for unit in stage.cast.live():
            mob = mobs[unit]
            near = mob.txt in MANA_BLOW and math.dist(mob.at, here) <= CONTACT
            if near and self.rolls.random() < CONTACT_RATE / GAME_RATE:
                self.mana.blows.append(mob.txt)


def pursued(situation: Situation | None = None, seconds: float = PLAYED) -> Situation:
    """The fight as the live loop played it: the TZ run's pursuit, one KP_1 press, `seconds` long."""
    return (situation or stored()).logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def play(
    values: Mapping[str, bool], seed: int, situation: Situation | None = None, lap: float | None = 0.02
) -> tuple[fights.Measures, float, Outcome, Mana]:
    from tests.inventory_tracking.scenarios.arena.situations.fane_death import play as fane_play

    dips, mana = Dips(), Mana(seed)
    burns = Burns(seed, mana)

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        burns(stage, routed)
        mana(stage, routed)
        dips(stage, routed)

    outcome = fane_play(pursued(situation), values, seed, lap=lap, extra=extra)
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome, mana


def summary(seed: int, values: Mapping[str, bool] = ALL_ON) -> dict[str, Any]:
    measured, dip, outcome, mana = play(values, seed)
    del outcome
    zero = next((t for t, m in mana.series if m < burnt.COSTS['teleport']), None)
    least = min((m for _, m in mana.series), default=None)
    return {
        'seed': seed, 'dead': measured.dead_at, 'low': dip, 'kills': measured.kills, 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'burns': len(mana.burns), 'first_burn': mana.burns[0][0] if mana.burns else None,
        'mana_out': zero, 'least_mana': None if least is None else round(least), 'refused': len(mana.refused),
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
        print(json.dumps(summary(seed)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
