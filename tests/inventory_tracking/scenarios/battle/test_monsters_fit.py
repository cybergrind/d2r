"""How near the walking monsters of the simulator (combat/sim/monsters.py) come to those of the take.

Every half second of the fight the model is started from the take's frame and run on with the take's
character and companions as its targets; where it has each monster 1, 2 and 4 s later is held against
where the take has it. Two yardsticks: the monster left where it stood, and the monster walking
straight at the character at its speed (what the threat scenarios do).
"""

import bisect
import functools
import math
import statistics

import pytest

from inventory_tracking.combat.sim.monsters import REACH, STOP, Pack, Traits, Walker
from inventory_tracking.takes.takes import monsters_of
from tests.inventory_tracking.scenarios.battle import tower_cellar5 as battle
from tests.inventory_tracking.scenarios.battle.replay import Replay, character


RATE = 25
BLOOD_CLAN, DEVILKIN = 55, 21


@functools.cache
def errors(horizon: float) -> dict[tuple[int, str], list[float]]:
    """Units between a monster's place `horizon` seconds on and where each way of guessing has it,
    by (type, way): 'model', 'stay', 'straight'."""
    replay = Replay(battle.FIXTURE, battle.script())
    frames, times = replay.frames, replay.times

    def at(seconds: float) -> dict:
        return frames[bisect.bisect_right(times, seconds) - 1]

    def targets(frame: dict) -> list[tuple[float, float]]:
        row = character(frame)
        return [(row.x, row.y), *((m.x, m.y) for m in monsters_of(frame) if m.companion)]

    found: dict[tuple[int, str], list[float]] = {}
    for half in range(1, int((battle.DEATH - horizon) * 2)):
        start = half / 2
        rows = {m.unit: m for m in monsters_of(at(start)) if m.hostile and Traits.of(m.txt).melee}
        after = {m.unit: m for m in monsters_of(at(start + horizon)) if m.hostile and m.alive}
        for seed in (1, 2, 3):
            pack = Pack([Walker(unit, m.txt, m.x, m.y) for unit, m in rows.items()], seed)
            straight = {unit: [m.x, m.y] for unit, m in rows.items()}
            for step in range(1, round(horizon * RATE) + 1):
                aims = targets(at(start + step / RATE))
                pack.step(step, aims)
                for unit, place in straight.items():
                    gap, stride = math.dist(place, aims[0]), Traits.of(rows[unit].txt).speed
                    if gap > REACH * STOP:
                        place[0] += (aims[0][0] - place[0]) / gap * min(stride, gap)
                        place[1] += (aims[0][1] - place[1]) / gap * min(stride, gap)
            for unit, m in rows.items():
                if unit in after:
                    end = (after[unit].x, after[unit].y)
                    found.setdefault((m.txt, 'model'), []).append(math.dist(pack.walkers[unit].at, end))
                    found.setdefault((m.txt, 'stay'), []).append(math.dist((m.x, m.y), end))
                    found.setdefault((m.txt, 'straight'), []).append(math.dist(straight[unit], end))
    return found


def mean(horizon: float, way: str, txt: int | None = None) -> float:
    return statistics.mean(
        e for (kind, how), values in errors(horizon).items() if how == way and txt in (None, kind) for e in values
    )


def test_the_model_is_four_times_nearer_than_monsters_that_walk_straight_at_the_character():
    # 1 s on: 2.9 units against 10.4; 2 s: 3.9 against 17.2. (2.5 and 3.8 before the refit of 2026-10-12 to all
    # takes: whom a monster goes for is now the share the 330 train takes show, one roll a monster, where this
    # take's own rule was the nearest and the character first for a Blood Clan; and a monster in reach rests
    # after a swing. The bounds are as they were.)
    assert mean(1.0, 'model') < mean(1.0, 'straight') / 3.5
    assert mean(2.0, 'model') < mean(2.0, 'straight') / 4


def test_a_blood_clan_is_placed_as_well_as_by_leaving_it_where_it_stood():
    # 2 s on, the Herald's pack among them: 4.2 units against 4.5 (4.1 before the refit); 4 s on: 4.6 against 6.5.
    assert mean(2.0, 'model', BLOOD_CLAN) <= mean(2.0, 'stay', BLOOD_CLAN)
    assert mean(4.0, 'model', BLOOD_CLAN) <= 0.8 * mean(4.0, 'stay', BLOOD_CLAN)


@pytest.mark.xfail(
    strict=True,
    reason='a Devilkin is 3.8 units from where the model has it 2 s on (1.9 by leaving it where it stood), 9 when it '
    'began 5 to 20 units from its target: it closes 3.6 units in those 2 s and the model 9.9. Its AI (Fallen: in and '
    'out, away when a leader falls) is not modelled, and one take of 24 s has too few of its walks to fit it',
)
def test_every_monster_is_placed_better_than_by_leaving_it_where_it_stood():
    assert mean(1.0, 'model') <= mean(1.0, 'stay')  # 2.9 against 2.0
    assert mean(2.0, 'model') <= mean(2.0, 'stay')  # 3.9 against 2.9
