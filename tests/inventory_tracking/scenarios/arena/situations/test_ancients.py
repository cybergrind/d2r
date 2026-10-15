"""The Ancient's Way pack (ancients.py; rca/2026-10-14/run-1932-findings.md §4): against a low-danger pack a level run
stands at the edge of the strike's reach and takes it one by one. With the fight's own look at a better place priced
by the safety (macros/safety.py `Safety.offer`), the stand the approach plans on the attack's engage ring and the
casts priced by how often they land that far (combat/stance.py `taken`), it closes in and kills the pack sooner.

Before the change (the same arena, 10 seeds): 15 kills in 20 s at the median, the aimed monster 17.0 units off at
the median, 54% of the casts hitting it; after: 21, 15.4 and 68%."""

import functools
import math
import statistics

from pydantic import BaseModel

from inventory_tracking.config import with_overrides
from tests.inventory_tracking.scenarios.arena import game, kp4
from tests.inventory_tracking.scenarios.arena.situations import ancients
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome


SEEDS = (1, 2, 3)


@functools.cache
def played(seed: int) -> tuple[Outcome, tuple[float, ...]]:
    """The level run (KP_1 once, the pursuit loop on), and the distance of the hostile nearest each cast's focal
    point from the character at the cast."""
    situation, presses = next((s, p) for label, s, p in ancients.variants() if label == 'KP_1 once: new')
    aways: list[float] = []
    plain = game.Arena.strike

    def strike(self):
        origin, focal = self.here, self.ground_under_pointer()
        live = [self.mobs.mobs[unit].at for unit in self.mobs.live()]
        if live:
            aways.append(math.dist(origin, min(live, key=lambda at: math.dist(at, focal))))
        plain(self)

    game.Arena.strike = strike
    try:
        outcome = situation.play(presses, seed=seed)
    finally:
        game.Arena.strike = plain
    return outcome, tuple(aways)


def test_the_level_run_closes_in_on_the_low_danger_pack_and_kills_it_sooner():
    kills = [len(played(seed)[0].kills) for seed in SEEDS]
    aways = [statistics.median(played(seed)[1]) for seed in SEEDS]
    assert statistics.median(kills) >= 18  # 15 before
    assert statistics.median(aways) <= 16.0  # 17.0 before
    assert all(played(seed)[0].dead_at is None for seed in SEEDS)
    assert all(played(seed)[0].said_count('Firing spot') >= 1 for seed in SEEDS)  # the safety's move, said


def units_a_cast(seed: int, *, look: bool) -> tuple[float, Outcome]:
    """The level run of `played`, with the fight's look for a better place on or off (`BuildSettings.fight_look`):
    the distinct hostiles the blades of a cast touched, on the mean, and the outcome."""
    situation, presses = next((s, p) for label, s, p in ancients.variants() if label == 'KP_1 once: new')
    flights: list = []
    plain, overrides = game.Arena.strike, kp4.with_overrides

    def strike(self):
        before = len(self.flights)
        plain(self)
        flights.extend(self.flights[before:])

    def looking[M: BaseModel](model: M, **changes: object) -> M:
        return with_overrides(model, **changes, fight_look=look)

    game.Arena.strike = strike
    kp4.with_overrides = looking
    try:
        outcome = situation.play(presses, seed=seed)
    finally:
        game.Arena.strike, kp4.with_overrides = plain, overrides
    units = [len({unit for blade in flight.touched for unit, _ in blade}) for flight in flights]
    return sum(units) / max(len(units), 1), outcome


def test_the_fights_look_for_a_better_place_hits_more_with_each_cast():
    # run-2040-findings.md "Fixes: walls, better place, far boss": with the blades stopping at walls in a place's
    # price, the look kept on (20 seeds: 2.69 units a cast against 1.45 off, 63 kills a minute against 54)
    for seed in (1, 2):
        on, played_on = units_a_cast(seed, look=True)
        off, played_off = units_a_cast(seed, look=False)
        assert on >= 1.4 * off, (seed, on, off)
        assert played_on.said_count('Firing spot') >= 1
        assert played_off.said_count('Firing spot') == 0
        assert played_on.dead_at is None
        assert played_off.dead_at is None
