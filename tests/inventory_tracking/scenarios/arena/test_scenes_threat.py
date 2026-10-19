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


@pytest.mark.parametrize('name', NAMES)
def test_the_macro_casts_in_every_threat_scene(name: str):
    assert played(name).casts > 0
