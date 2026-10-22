"""The Ancient's Way pack (ancients.py; rca/2026-10-14/run-1932-findings.md §4): against a low-danger pack a level run
stands at the edge of the strike's reach and takes it one by one. With the fight's own look at a better place priced
by the safety (macros/safety.py `Safety.offer`), the stand the approach plans on the attack's engage ring and the
casts priced by how often they land that far (combat/stance.py `taken`), it closes in and kills the pack sooner.

Before the change (the same arena, 10 seeds): 15 kills in 20 s at the median, the aimed monster 17.0 units off at
the median, 54% of the casts hitting it; after: 21, 15.4 and 68%.

The pack's Yetis (447) carry Extra Fast (monumod 6) as champions and a unique's minions: an Extra Fast melee pack,
which the player has kept at range since 2026-10-21 ~16:30 ("Yes, 18 for Extra Fast"; combat/threats/manaburn.py
FAST_RANGE, FAST_KEEP 18), and since ~21:20 only under a threat (THREAT_GATE, the coordinator from the herald-left
findings: "there were EASY heralds", "we were FULL health and full potions"). This pack is no threat: the closing in
is played with THREAT_GATE on, and the keep range with it off
(`test_the_extra_fast_yetis_are_kept_at_range_without_the_threat_gate`)."""

import functools
import math
import statistics

from pydantic import BaseModel

from inventory_tracking.combat.threats import manaburn
from inventory_tracking.config import with_overrides
from tests.inventory_tracking.scenarios.arena import game, kp4
from tests.inventory_tracking.scenarios.arena.situations import ancients
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome


SEEDS = (1, 2, 3)


@functools.cache
def played(seed: int, *, gated: bool = True) -> tuple[Outcome, tuple[float, ...]]:
    """The level run (KP_1 once, the pursuit loop on), and the distance of the hostile nearest each cast's focal
    point from the character at the cast. `gated`: manaburn.py THREAT_GATE for the play (the module text)."""
    situation, presses = next((s, p) for label, s, p in ancients.variants() if label == 'KP_1 once: new')
    aways: list[float] = []
    plain, gate = game.Arena.strike, manaburn.THREAT_GATE

    def strike(self):
        origin, focal = self.here, self.ground_under_pointer()
        live = [self.mobs.mobs[unit].at for unit in self.mobs.live()]
        if live:
            aways.append(math.dist(origin, min(live, key=lambda at: math.dist(at, focal))))
        plain(self)

    game.Arena.strike = strike
    manaburn.THREAT_GATE = gated  # pyrefly: ignore[bad-assignment] # the module switch, typed as its literal
    try:
        outcome = situation.play(presses, seed=seed)
    finally:
        game.Arena.strike = plain
        manaburn.THREAT_GATE = gate
    return outcome, tuple(aways)


def test_the_level_run_closes_in_on_the_low_danger_pack_and_kills_it_sooner():
    kills = [len(played(seed)[0].kills) for seed in SEEDS]
    aways = [statistics.median(played(seed)[1]) for seed in SEEDS]
    assert statistics.median(kills) >= 18  # 15 before
    # 17.0 before; 16.0 until 2026-10-21, when the arena showed the sigil (game.py `Arena.lay_sigil`) and SIGIL_KEEPS
    # (builds/warlock/buffs.py) played its own cadence: 16.80, 16.75, 16.19 by seed
    # (rca/2026-10-21/arena-failures-findings.md). With FAST_RANGE and THREAT_GATE on (2026-10-21 ~21:20, the module
    # text): 7.47, 15.23, 12.06; FAST_RANGE on alone (16:30-21:20) kept this pack at 20.22, 20.82, 20.11
    assert statistics.median(aways) <= 16.8
    assert all(played(seed)[0].dead_at is None for seed in SEEDS)
    assert all(played(seed)[0].said_count('Firing spot') >= 1 for seed in SEEDS)  # the safety's move, said


def test_the_extra_fast_yetis_are_kept_at_range_without_the_threat_gate():
    """FAST_RANGE alone, THREAT_GATE off (the player, 2026-10-21 ~16:30: "Yes, 18 for Extra Fast"): the Extra Fast
    Yetis are struck from FAST_KEEP or farther (20.22, 20.82, 20.11 by seed on 2026-10-21), and the run still kills as
    many as the closing in did before it and lives."""
    kills = [len(played(seed, gated=False)[0].kills) for seed in SEEDS]
    aways = [statistics.median(played(seed, gated=False)[1]) for seed in SEEDS]
    assert statistics.median(kills) >= 18
    assert statistics.median(aways) >= manaburn.FAST_KEEP
    assert all(played(seed, gated=False)[0].dead_at is None for seed in SEEDS)


def units_a_cast(seed: int, *, look: bool) -> tuple[float, Outcome]:
    """The level run of `played` (THREAT_GATE on), with the fight's look for a better place on or off
    (`BuildSettings.fight_look`): the distinct hostiles the blades of a cast touched, on the mean, and the outcome."""
    situation, presses = next((s, p) for label, s, p in ancients.variants() if label == 'KP_1 once: new')
    flights: list = []
    plain, overrides, gate = game.Arena.strike, kp4.with_overrides, manaburn.THREAT_GATE

    def strike(self):
        before = len(self.flights)
        plain(self)
        flights.extend(self.flights[before:])

    def looking[M: BaseModel](model: M, **changes: object) -> M:
        return with_overrides(model, **changes, fight_look=look)

    game.Arena.strike = strike
    kp4.with_overrides = looking
    manaburn.THREAT_GATE = True
    try:
        outcome = situation.play(presses, seed=seed)
    finally:
        game.Arena.strike, kp4.with_overrides = plain, overrides
        manaburn.THREAT_GATE = gate
    units = [len({unit for blade in flight.touched for unit, _ in blade}) for flight in flights]
    return sum(units) / max(len(units), 1), outcome


def test_the_fights_look_for_a_better_place_hits_more_with_each_cast():
    # run-2040-findings.md "Fixes: walls, better place, far boss": with the blades stopping at walls in a place's
    # price, the look kept on (20 seeds: 2.69 units a cast against 1.45 off, 63 kills a minute against 54)
    for seed in (1, 2):
        on, played_on = units_a_cast(seed, look=True)
        off, played_off = units_a_cast(seed, look=False)
        # 1.4 until 2026-10-21, when the arena showed the sigil and SIGIL_KEEPS played its own cadence: seed 1 2.25
        # against 1.39 (1.62), seed 2 2.15 against 1.54 (1.40) (rca/2026-10-21/arena-failures-findings.md). With
        # THREAT_GATE on (2026-10-21 ~21:20, the module text): 2.39 against 1.43 (1.67), 2.00 against 1.19 (1.68); with
        # FAST_RANGE alone the Extra Fast Yetis kept at 18 left the look little to gain (1.10, 1.07)
        assert on >= 1.39 * off, (seed, on, off)
        assert played_on.said_count('Firing spot') >= 1
        assert played_off.said_count('Firing spot') == 0
        assert played_on.dead_at is None
        assert played_off.dead_at is None
