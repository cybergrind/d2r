"""The second build fights in the arena: the proof that the framework positions and aims by the build it is
given, not by Echoing Strike's blades (framework-plan.md, Task 2.5; green in Stage 3.7)."""

from dataclasses import replace

from inventory_tracking.macros.runner import ATTACK
from inventory_tracking.macros.skills import ATTACK as PLAIN_ATTACK
from tests.inventory_tracking.builds.dummy import BOLT, DUMMY
from tests.inventory_tracking.scenarios.arena.driver import Press, play
from tests.inventory_tracking.scenarios.arena.scenes_basic import one_in_the_open


BOLTS = 5  # bolts the scene's monster takes


def dummy_scene():
    """One monster in the open and a character that has the plain attack on a key and nothing else.
    The monster has the life of BOLTS of the dummy's bolts left: a Hell Bovine's full 10,936 points
    are 110 bolts, more than the play's 20 seconds hold, and the blades would take them in five casts."""
    scene = one_in_the_open()
    scene.hero = replace(scene.hero, name='Dummy', slots=(PLAIN_ATTACK,), right_skill=PLAIN_ATTACK)
    scene.mobs = [replace(mob, life=BOLTS * BOLT) for mob in scene.mobs]
    return scene


def test_the_second_build_clears_a_scene_with_its_own_attack():
    result = play(dummy_scene(), [Press(0.0, ATTACK)], 20.0, build=DUMMY)
    assert result.alive
    assert result.cleared_at is not None
    # Its own bolt's damage, cast by cast (a bolt aimed where the monster stood misses it once it has come
    # on): the blades would have done with fewer
    assert result.casts >= BOLTS
    assert result.kills == [1]
    assert [text for _, text in result.said][1].startswith('Macro: Attack (right click) at ')


def test_the_same_scene_is_one_cast_for_the_blades():
    """The scene tells the two attacks apart: the default build's blades clear it with the first cast."""
    scene = dummy_scene()
    scene.hero = one_in_the_open().hero
    result = play(scene, [Press(0.0, ATTACK)], 20.0)
    assert result.cleared_at is not None
    assert result.casts < BOLTS
