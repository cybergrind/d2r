"""The 16 threat scenes (scenes_threat.py) played by the production macro in the arena.

These tests state only that each scene plays and that the macro acts in it; what the macro does well or
badly is recorded in fixtures/THREAT-in-arena.md, not asserted.
"""

import functools

import pytest

from inventory_tracking.macros.runner import ATTACK
from tests.inventory_tracking.scenarios.arena.driver import Press, play
from tests.inventory_tracking.scenarios.arena.scenes_threat import auras, horizons, threat_scenes


NAMES = list(threat_scenes())
SECONDS = 0.5  # how far from the horizon a play that ended on time may fall
# 2026-10-21: with macros/safety.py ESCAPE_SAME_SPAN (on since the 10:11 restart; the player's Herald ruling "fix it
# first") the character at 600 life under four Oblivion Knights retreats twice, 16 units each ("no progress act fits
# the life budget", 0.05 s and 1.69 s), then idles to the horizon: "idle: 4 hostiles, none in reach; nearest the
# monster 312 (1) 33 away, shot clear", 0 casts (17 casts and clear at 5.9 s with the switch off). The retreat is the
# threat harness's own answer (standing, it dies: fixtures/THREAT-in-arena.md); the stand after it is the one-way
# retreat of rca/2026-10-21/arena-failures-findings.md T1 (attack mode alone never walks back), which waits for the
# player's ruling, as test_baal.py's waves do.
ONE_WAY_RETREAT = pytest.mark.xfail(
    reason='attack mode alone never walks back after a safety retreat (rca/2026-10-21/arena-failures-findings.md T1): '
    "waiting for the player's ruling",
    strict=False,
)
CASTING = [pytest.param(name, marks=ONE_WAY_RETREAT) if name == 'low_life_under_knights' else name for name in NAMES]


@functools.cache
def played(name: str, seed: int = 1):
    """The scene `name` played with ATTACK pressed at 0.0 to its horizon, once for the tests that read it. That a
    second play is the first is the arena's, tested once (situations/test_situations.py
    `test_the_example_plays_the_same_twice`) and for driver.py's `play` in test_driver.py."""
    return play(threat_scenes()[name], [Press(0.0, ATTACK)], horizons()[name], seed=seed, auras=auras().get(name))


@pytest.mark.parametrize('name', NAMES)
def test_a_threat_scene_plays_to_its_horizon(name: str):
    result = played(name)
    assert result.scene == name
    if result.alive and result.cleared_at is None:
        assert result.seconds == pytest.approx(horizons()[name], abs=SECONDS)
    else:
        assert result.seconds <= horizons()[name] + SECONDS


@pytest.mark.parametrize('name', CASTING)
def test_the_macro_casts_in_every_threat_scene(name: str):
    assert played(name).casts > 0
