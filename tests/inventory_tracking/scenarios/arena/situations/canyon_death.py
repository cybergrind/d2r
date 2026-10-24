"""The death in the Canyon of the Magi, 2026-10-23 14:52:24.7 (take 20261023T115109Z-46, area 46, the KP_6 terror zone
loop; rca/2026-10-23/death-canyon-findings.md) as a situation: danger_fights.py `cut` from 14:52:11.5, the stand the
run waited at for the Herald (the walls, each unit's stat 25, the Terror Zone's level, the take's pace, Amplify Damage
as the frames show it), with the tier 5 Herald pack's javelins as the take shows them, since the arena's pooled shooter
fit (2.4 % of shots take life, 0.42 shots a second, one missile at 20.6 units a second) holds none of it:

- every Hell Slinger (txt 376, AI PantherJavelin, no read model) throws `pantherjav4` (missiles.txt 229) at
  JAVELIN_SPEED (sim/monsters.py `Pack.bolts`), read in flight by the macro as the live client's missile list is
  (mobs.py `Mobs.flights`) wherever the look reads that class (combat/bolts.py READ_THROWS);
- the take's pack threw 8-12 javelins a second, every one at the character's place, from 63 s on (the first 6 s at
  the bound demon standing on it), 30 of them after the demon fell at 69.9 s, and 17 hurts took 254-980 each: a throw
  at the character lands with LANDS, the gap between a Slinger's throws GAP times the fit's (0.58 a second each);
- a throw's raw points: the game's even roll over the table blow THROW (A1 50-85 x monlvl DM(H) 109 at level 96 x the
  tier 5 minion's 1.5: 82-139) times THROW_RAISE as physical, Fire Enchanted's fire a third to a half of it, fitted so
  the arena's hurts under Amplify Damage (physical -82: x1.82) less the Psychic Ward's pool sit on the take's.

The recording: life 2943 -> 952 in 0.62 s at 70.08-70.70 s of the take (8.6-9.2 s into the play, the Rejuvenation at
70.73), 1350 at 73.01, 16 at 74.63, dead at 74.99 (13.5 s into the play).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.canyon_death --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.canyon_death --seeds 20
"""

import argparse
import functools
import math
import random
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from inventory_tracking.game.records import NO_OWNER
from inventory_tracking.levels.geometry import Point
from tests.inventory_tracking.scenarios.arena.mobs import body_of
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load, once
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


NAME = 'canyon-death-1452'
TAKE = '20261023T115109Z-46'
FIGHT = (TAKE, '2026-10-23T14:52:11.5')
SECONDS = 16.0
SLINGER, JAVELIN = 376, 229
JAVELIN_SPEED = 23.5  # units a second (the take's frames: the median over 109 javelins, 22.9-24.5)
LANDS = 0.6  # of the throws at the character after the demon fell, the share that took life (17 hurts of ~30)
GAP = 0.73  # the fit's 0.42 throws a second a Slinger over the take's 0.58 (8.7 a second from 15)
MERCENARY, MERCENARY_LIFE = 338, 4314.0  # the Act 5 mercenary's type and its most life (the take's row)
# A throw's raw points: the game's roll, uniform between the table's least and most (A1 50-85 x monlvl DM(H) 109 at
# level 96 x the tier 5 minion's 1.5: 82-139) times THROW_RAISE as physical, Fire Enchanted's fire a third to a half of
# that (`Javelins`). The take's 16 hurts: 372 / 467 / 645 at the 10th / 50th / 90th percentile, 980 the most; x3.3 plays
# them at a median 413 and a 90th percentile 793 (x2.2: 259; stat 25's x3.85: 754). The Herald's throws the same: no
# hurt of the take, the Herald 4-12 off for the last four, went over 980 (mobs.py SHOT_TIER). The fitted size spread
# (sim/monsters.py `spread`, x0.3 to x4.6) is not played on them
THROW = (82.0, 139.0)
THROW_RAISE = 3.3
FIRE_SHARE = (1 / 3, 1 / 2)
UNCUT = 1e6  # the shot's own points (mobs.py `_shot_cut` cuts at the larger of them and the table's): no cut
# Seconds a play runs: the take's 16 and as long again, so a fight the belt's 8 rejuvenations only put off is played to
# its end (the take's belt: 8 rejuvenations, 8 healing potions)
PLAYED = 32.0
# Units round a javelin's way a body takes it within, beside its own radius (`Javelins`)
JAVELIN_BODY = 0.5
DIED_AT = 13.5  # seconds into the play the take's character died (74.99 s of the take)
# The companions' deaths as the take shows them (mode 0 in the frames), seconds into the play: the bound demon (361)
# at 68.67 s of the take, the mercenary (338) at 69.68 s; the Defiler (744) lived past the character (76.31 s). A
# companion falls at its time, sooner if the arena's blows on it end it (game.py PETS_FIGHT, MERC_HURT; `Falls`)
FALLS = {361: 68.67 - 62.36, MERCENARY: 69.68 - 62.36}
RECORDED_LOW = 16 / 2943


def cut() -> Situation:
    found = fights.cut(
        NAME, fight=FIGHT, seconds=SECONDS,
        about='2026-10-23 14:52:11.5: the tier 5 Hell Slinger Herald pack in the Canyon of the Magi (canyon_death.py)',
    )  # fmt: skip
    # The take's death ends Battle Orders and the curses at 12.61 s (state 32, 9, 28 off with the life at 0): no part of
    # the fight. Battle Orders up through the play, the curses as they were before the death
    assert found.orders is not None
    found.orders = replace(found.orders, ends=SECONDS + 120.0)
    found.curses = tuple(row for row in found.curses if row[0] < DIED_AT - 0.5)
    # The mercenary: cut.py gives a companion the row's numbers (its life in 128ths, 128 of 4314), so the arena's would
    # die to the first throw; the take's stood at 128/128 until 69.9 s
    found.scene.mobs = [
        replace(mob, life=mob.full) if mob.owner is not None and mob.txt == MERCENARY else mob
        for mob in found.scene.mobs
    ]
    found.assumed.update({
        'orders': 'Battle Orders up through the play (its state went off with the death at 12.61 s)',
        'curses.death': 'the curses as the frames show them before the death (Amplify Damage from the start, '
        'Conviction at 11.93 s as the Herald came within 4); the death\'s ends left out',
        'scene.mercenary': f'the mercenary at its full {MERCENARY_LIFE:.0f} '
        '(the take: 128/128 until it fell at 69.9 s)',
        'javelins': f'every Hell Slinger throws `pantherjav4` (class {JAVELIN}) at {JAVELIN_SPEED} units a second, '
        f'{GAP} times the fit\'s gap, a throw at the character takes life with {LANDS}, {THROW} x {THROW_RAISE} '
        'raw, rolled evenly (canyon_death.py)',
    })  # fmt: skip
    return found


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def armed(stage: Stage, _routed: Any) -> None:
    """At each tick: every Hell Slinger throws the take's javelins (the module text), from its first throw on."""
    pack = stage.cast.pack
    for unit, walker in pack.walkers.items():
        if walker.txt == SLINGER and unit in pack.shots and walker.mark < 0:
            # Every throw of the take's went at the character's place (`Javelins` gives those met first to a companion)
            walker.mark = 0
        if walker.txt == SLINGER and unit not in pack.bolts and unit in pack.shots:
            pack.bolts[unit] = (JAVELIN, 1, JAVELIN_SPEED, LANDS, GAP)
            pack.shots[unit] = {'physical': UNCUT, 'fire': UNCUT}


class Dips:
    """The lowest share of the most life the blows of a tick leave before that tick's potions (dominus.py `Dips`,
    without its Dominus)."""

    def __init__(self) -> None:
        self.life: float | None = None
        self.taken = 0.0
        self.low = 1.0

    def __call__(self, stage: Stage, _routed: Any) -> None:
        if self.life is not None and stage.max_life:
            self.low = min(self.low, (self.life - (stage.taken - self.taken)) / stage.max_life)
        self.life, self.taken = stage.life, stage.taken


def segment_gap(point: Point, start: Point, end: Point) -> tuple[float, float]:
    """(how far along the way from `start` to `end` `point` lies, 0 to 1; how far off the way it is)."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = dx * dx + dy * dy
    if length <= 0:
        return 0.0, math.dist(point, start)
    along = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length))
    return along, math.dist(point, (start[0] + along * dx, start[1] + along * dy))


def falls(stage: Stage, _routed: Any) -> None:
    """At each tick: a companion of a type FALLS names is gone from its time on, as in the take."""
    now = stage.clock.now
    kept, gone = [], []
    for monster in stage.world.monsters:
        due = FALLS.get(monster.txt_id) if monster.ally or monster.owner != NO_OWNER else None
        (gone if due is not None and now >= due else kept).append(monster)
    if gone:
        stage.pet_deaths.extend((now, m.unit_id, m.txt_id) for m in gone)
        stage.world = replace(stage.world, monsters=tuple(kept))


class Javelins:
    """Each javelin as it is let go (the module text): its points rolled as the game rolls them (THROW, THROW_RAISE,
    FIRE_SHARE), and one thrown at the character landing on the first companion whose body stands on its way: within its
    body (mobs.py `body_of`) and JAVELIN_BODY of the line from the thrower to the character's place, and nearer the
    thrower than that place (a blow on it, PETS_FIGHT's for the demons). Each missile is looked at once."""

    def __init__(self, seed: int) -> None:
        self.seen: set[int] = set()
        self.rolls = random.Random(seed * 104_729 + 46)

    def __call__(self, stage: Stage, _routed: Any) -> None:
        pack = stage.cast.pack
        mates = [m for m in stage.world.monsters if m.ally or m.owner != NO_OWNER]
        flying = []
        for missile in pack.flying:
            if id(missile) in self.seen or missile.kind != JAVELIN:
                flying.append(missile)
                continue
            self.seen.add(id(missile))
            physical = self.rolls.uniform(*THROW) * THROW_RAISE
            missile = replace(missile, parts={'physical': physical, 'fire': physical * self.rolls.uniform(*FIRE_SHARE)})
            met = []
            if missile.target == 0 and missile.origin is not None:
                for index, mate in enumerate(mates, 1):
                    spot = (mate.x, mate.y)
                    along, off = segment_gap(spot, missile.origin, missile.at)
                    if off <= body_of(mate.txt_id) + JAVELIN_BODY and math.dist(missile.origin, spot) < math.dist(
                        missile.origin, missile.at
                    ):
                        met.append((along, index, spot))
            if met:
                _, index, spot = min(met)
                missile = replace(missile, target=index, at=spot, takes=True)
            flying.append(missile)
        pack.flying = flying
        self.seen &= {id(missile) for missile in pack.flying}


def pursued(situation: Situation | None = None, seconds: float = PLAYED) -> Situation:
    """The fight as the live loop played it: the TZ run's pursuit, one KP_1 press (the full clear the KP_6 loop's
    level run is), `seconds` long."""
    return (situation or stored()).logic('new').variant(presses=(once('pickup'),), seconds=seconds)


def play(
    values: Mapping[str, bool], seed: int, situation: Situation | None = None, lap: float | None = None
) -> tuple[fights.Measures, float, Outcome]:
    """One play of the pursuit (`pursued`) with the fixes `values`: its measures, the lowest share of life before
    potions (dominus.py `Dips`) and the outcome."""
    from tests.inventory_tracking.scenarios.arena.situations.fane_death import play as fane_play

    dips, javelins = Dips(), Javelins(seed)

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        armed(stage, routed)
        falls(stage, routed)
        javelins(stage, routed)
        dips(stage, routed)

    outcome = fane_play(pursued(situation), values, seed, lap=lap, extra=extra)
    return fights.measures(outcome), round(max(dips.low, 0.0), 3), outcome


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situation from its take into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    parser.add_argument('--lap', type=float, default=None)
    args = parser.parse_args(argv)
    if args.cut:
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
    for seed in range(1, args.seeds + 1):
        measured, dip, _ = play(ALL_ON, seed, lap=args.lap)
        print(measured, dip, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
