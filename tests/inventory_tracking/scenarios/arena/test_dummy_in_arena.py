"""The second build fights in the arena: the proof that the framework positions and aims by the build it is
given, not by Echoing Strike's blades (framework-plan.md, Task 2.5; green in Stage 3.7)."""

from dataclasses import replace

import pytest

from inventory_tracking.macros.runner import ATTACK
from inventory_tracking.macros.skills import ATTACK as PLAIN_ATTACK
from tests.inventory_tracking.builds.dummy import DUMMY
from tests.inventory_tracking.scenarios.arena.driver import Press, play
from tests.inventory_tracking.scenarios.arena.scenes_basic import one_in_the_open


def dummy_scene():
    """One monster in the open and a character that has the plain attack on a key and nothing else."""
    scene = one_in_the_open()
    scene.hero = replace(scene.hero, name='Dummy', slots=(PLAIN_ATTACK,), right_skill=PLAIN_ATTACK)
    return scene


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today the hunt holds Echoing Strike whatever the build (hunt.py strike_input), aims by LinePolicy '
        '(controller.py aim_choice), prices a place by the blades (stance.py taken), and the arena deals the '
        "blades' damage: with the plain attack alone the mode stops with the strike on no key"
    ),
)
def test_the_second_build_clears_a_scene_with_its_own_attack():
    result = play(dummy_scene(), [Press(0.0, ATTACK)], 20.0, build=DUMMY)
    assert result.alive
    assert result.cleared_at is not None
    assert result.casts > 0
