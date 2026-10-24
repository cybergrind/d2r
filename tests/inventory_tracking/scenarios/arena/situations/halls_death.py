"""The death in Halls of the Dead Level 2, 2026-10-23 23:31:06 (take 20261023T202950Z-57, area 57, the KP_6 terror zone
loop; rca/2026-10-23/death-halls-findings.md) as a situation: danger_fights.py `cut` from 23:30:44.0, the run about
to end (23:30:44.38: "nothing is left to go to on this level: no route stage"), the character on the omen's stand with
the tier 5 Herald pack of Returned (txt 1, a Herald and 14 minions, there since 23:30:41.5) round it, its reviver 101
(3504444985) "raising its pack", with what the cut does not hold put in as the take and its log show it:

- the drops by the stand the log names (DROPS): two super healing potions and two gold piles;
- the belt as the frames show it then (BELT, 13 of 16): short, so a healing potion is the run's side goal, its guards
  "the fight first" (hunting/choice.py `goal`: `first_fight`, `guarded`), the goal the reviver's then took over
  (hunting/revive.py `reviver_goal`) with `guarded` dropped: no route stage (pursuit.py `routed`);
- the loop's legs (`Legs`): a level run that ends is posted again LEG_GAP s later with attack mode off between, as
  the loop's "TZ next level" legs were (23:30:44.4-23:31:06.3: 37 legs, each "the route's own step takes the press");
- the mercenary fell at 23:31:05.4 (FALLS); the Defiler and the bound demon lived past the character.

The run's agenda (the stand the run waited at for the omen) is not the arena's: the cut starts after it. The
recording: no strike and no move for 22 s, the gold picked at 47.3 and 56.9 with the pack on the character, the 8
rejuvenations gone (the character's and the healer's), dead at 23:31:06.3 (22.3 s into the play).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.halls_death --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.halls_death --seeds 20
"""

import argparse
import functools
import json
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from inventory_tracking.game.layout import FULL_REJUVENATION, SUPER_HEALING
from inventory_tracking.game.records import NO_OWNER
from inventory_tracking.macros.runner import ATTACK, PICKUP
from tests.inventory_tracking.scenarios.arena.driver import Press
from tests.inventory_tracking.scenarios.arena.game import POTIONS
from tests.inventory_tracking.scenarios.arena.scene import Drop
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import MERCENARY, Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import (
    FIXTURES,
    Outcome,
    Situation,
    dump,
    load,
    once,
)
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'halls-death-2331'
TAKE = '20261023T202950Z-57'
FIGHT = (TAKE, '2026-10-23T23:30:44.0')
SECONDS = 23.0
PLAYED = 35.0  # the take's 23 s and half as long again, so a fight the belt only puts off is played to its end
DIED_AT = 22.3
REVIVER = 3504444985
FALLS = {MERCENARY: 21.4}  # the mercenary's mode 12 from 23:31:05.4
# The drops by the stand as the log names them (23:30:40.5): (label, place, gold)
DROPS = (
    ('potion', (15197.0, 8081.0), 0),
    ('potion', (15199.0, 8086.0), 0),
    ('gold', (15199.0, 8088.0), 5648),
    ('gold', (15197.0, 8085.0), 6210),
)
LEG_GAP = 0.4  # s from a run's end to the loop's next leg (the log: 0.3-0.5)
LEG_POSTED = 1.0  # s a leg's press is given to start its run before the leg counts as over
# The belt as the take's frames show it at 23:30:44.2, as the run ended: a healing potion and two rejuvenations gone
# (to the character at 23:30:42.2 and the healer's mercenary), so a healing potion on the ground is the run's side goal
_, R, H = None, FULL_REJUVENATION, SUPER_HEALING
BELT = (R, R, H, H, R, R, H, H, R, R, H, H, _, _, _, H)


def potion_code() -> str:
    """The super healing potion's code in the arena's table (never from memory: potions.json, from d2data)."""
    return str(POTIONS[SUPER_HEALING]['code'])


def cut() -> Situation:
    found = fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about='2026-10-23 23:30:44.0: the tier 5 Herald pack on the omen stand in Halls of the Dead Level 2, the run '
        'about to end (halls_death.py)',
    )  # fmt: skip
    if found.orders is not None:  # Battle Orders went off with the death only
        found.orders = replace(found.orders, ends=SECONDS + 120.0)
    found.curses = tuple(row for row in found.curses if row[0] < DIED_AT - 0.5)
    found.scene.mobs = [
        replace(mob, life=mob.full) if mob.owner is not None and mob.txt == MERCENARY else mob
        for mob in found.scene.mobs
    ]
    units = max([mob.unit for mob in found.scene.mobs] + [mob.unit for s in found.spawns for mob in s.mobs]) + 1
    code = potion_code()
    found.scene.drops = [
        Drop(units + index, code if kind == 'potion' else 'gold', at, gold=gold)
        for index, (kind, at, gold) in enumerate(DROPS)
    ]
    found.scene.hero = replace(found.scene.hero, belt=BELT)
    found.assumed.update({
        'belt': 'the take\'s belt at 23:30:44.2 (`b`), 13 of 16: the run ended with it',
        'orders': 'Battle Orders up through the play (its state went off with the death)',
        'scene.mercenary': 'the mercenary at its full life (the take: 128/128 until 23:31:02)',
        'drops': f'the log\'s drops by the stand at 23:30:40.5: {list(DROPS)}',
    })  # fmt: skip
    return found


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def falls(stage: Stage, _routed: Any) -> None:
    """A companion of a type FALLS names is gone from its time on, as in the take."""
    now = stage.clock.now
    kept, gone = [], []
    for monster in stage.world.monsters:
        due = FALLS.get(monster.txt_id) if monster.ally or monster.owner != NO_OWNER else None
        (gone if due is not None and now >= due else kept).append(monster)
    if gone:
        stage.pet_deaths.extend((now, m.unit_id, m.txt_id) for m in gone)
        stage.world = replace(stage.world, monsters=tuple(kept))


class Legs:
    """The KP_6 loop's legs (the module text): once the level run is over, attack mode off at once (the loop's
    "Attack mode off"), and LEG_GAP s on attack mode on and the pickup key again, a new leg of the same level (the
    loop's "TZ next level" leg: "Attack mode on", "Run: the agenda, then Next level"). Counts the legs posted."""

    def __init__(self) -> None:
        self.legs = 0
        self.due: float | None = None  # the clock the next leg is posted at
        self.posted: float | None = None  # the clock the last leg was posted at, until its run is up

    def __call__(self, stage: Stage, routed: Any) -> None:
        hunter, runner = getattr(routed, 'hunter', None), getattr(routed, 'runner', None)
        if stage.over is not None or hunter is None or runner is None or routed.pending:
            return
        now, posted = stage.clock.now, hunter.pursuit
        if posted is not None and posted.leashed:
            self.posted = None
            return
        if self.posted is not None and now - self.posted < LEG_POSTED:
            return  # the leg's press is still being taken up
        if self.due is None:
            if runner.attack_mode:
                routed.pending.append(Press(round(now, 3), ATTACK))
            self.due = now + LEG_GAP
            return
        if now < self.due:
            return
        if not runner.attack_mode:
            routed.pending.append(Press(round(now, 3), ATTACK))
        routed.pending.append(Press(round(now + 0.05, 3), PICKUP))
        self.due, self.posted = None, now
        self.legs += 1


def pursued(situation: Situation | None = None, seconds: float = PLAYED) -> Situation:
    """The fight as the live loop played it: the TZ run's pursuit, one pickup press, `seconds` long (`Legs` the
    rest)."""
    return (situation or stored()).logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def play(
    values: Mapping[str, bool], seed: int, situation: Situation | None = None, lap: float | None = 0.02
) -> tuple[fights.Measures, float, Outcome, Legs]:
    """One play of the pursuit with the fixes `values`: its measures, the lowest share of life before potions, the
    outcome and the legs."""
    from tests.inventory_tracking.scenarios.arena.situations.fane_death import play as fane_play

    found = situation or stored()
    dips, legs = Dips(), Legs()

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        falls(stage, routed)
        legs(stage, routed)
        dips(stage, routed)

    outcome = fane_play(pursued(found), values, seed, lap=lap, extra=extra)
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome, legs


def summary(seed: int, values: Mapping[str, bool] = ALL_ON) -> dict[str, Any]:
    measured, dip, outcome, legs = play(values, seed)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    return {
        'seed': seed, 'dead': measured.dead_at, 'low': dip, 'kills': measured.kills, 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'legs': legs.legs, 'strikes': len(outcome.strikes), 'ended': outcome.said_count('over'),
        'reviver': stage.fell.get(REVIVER),
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
