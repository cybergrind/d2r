"""The production macro played in the arena (driver.py): attack mode and the pickup step, started by
presses as the runner starts them, on the arena's clock alone."""

import time
from dataclasses import replace

import pytest

from inventory_tracking.builds.generic import GENERIC
from inventory_tracking.config import PLAYER_HEALING
from inventory_tracking.game.layout import DEFILER_CLASS, FULL_REJUVENATION, SUPER_HEALING
from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.runner import ATTACK, HUNT_ELITES, PICKUP, PREBUFF, TELEPORT
from tests.inventory_tracking.macros.fakes import BUILD, runner_modules
from tests.inventory_tracking.scenarios.arena import driver
from tests.inventory_tracking.scenarios.arena.driver import Play, Press, play
from tests.inventory_tracking.scenarios.arena.game import OSD, SERVE, Arena
from tests.inventory_tracking.scenarios.arena.scenes_basic import (
    BELT,
    HELL_BOVINE,
    LIFE,
    SCENES,
    archer_behind_a_wall,
    gloams,
    hero,
    mob,
    one_in_the_open,
    pack_at_low_life,
    potion_on_the_ground,
)


def lines(result) -> list[str]:
    return [text for _, text in result.said]


def test_attack_mode_clears_one_monster_in_the_open():
    result = play(one_in_the_open(), [Press(0, ATTACK)], 20.0)
    assert result.alive
    assert result.kills == [1]
    assert result.casts > 0
    assert result.cleared_at is not None
    assert result.cleared_at < 5.0
    assert result.seconds == 20.0
    assert lines(result)[0] == 'Macro: Attack mode on'
    assert any(line.startswith('Macro: Echoing Strike (right click)') for line in lines(result))


def test_with_no_press_nothing_is_cast_and_the_monster_walks_in():
    result = play(one_in_the_open(), [], 6.0, seed=4)
    assert result.casts == 0
    assert result.kills == []
    assert result.taken > 0.0
    assert result.said == []
    assert result.cleared_at is None


def test_a_press_comes_at_its_time():
    result = play(one_in_the_open(), [Press(2.0, ATTACK)], 10.0)
    assert result.said[0] == (2.0, 'Macro: Attack mode on')
    assert result.kills == [1]


def test_a_second_press_of_the_toggle_ends_the_mode():
    result = play(one_in_the_open(), [Press(0, ATTACK), Press(0.6, ATTACK)], 5.0)
    assert lines(result)[-1] == 'Macro: Attack mode off'
    assert result.said[-1][0] == pytest.approx(0.6, abs=0.1)
    assert 0 < result.casts <= 3
    assert result.kills == []


def test_the_arena_can_kill():
    result = play(pack_at_low_life(), [Press(0, ATTACK)], 20.0, seed=14)
    assert not result.alive
    assert result.dead_at is not None
    assert result.dead_at < 2.0
    assert result.seconds == result.dead_at  # the play ends at the death
    assert result.taken == pytest.approx(LIFE / 6)
    assert result.kills == []


def test_a_pickup_press_takes_the_potion_the_belt_is_short_of():
    arena = Arena(potion_on_the_ground())
    result = Play(arena, [Press(0, PICKUP)], 5.0, 1).run()
    assert arena.picked == ['a super healing potion']
    assert arena.loot.belt == BELT
    assert result.moved > 0.0
    assert lines(result) == [
        'Macro: Picking up a super healing potion, 7 away',
        'Macro: a super healing potion: picked up',
    ]


def test_a_pickup_press_in_a_fight_pauses_the_mode_and_the_mode_resumes():
    scene = potion_on_the_ground()
    scene.mobs = one_in_the_open().mobs
    result = play(scene, [Press(0, ATTACK), Press(0.5, PICKUP)], 10.0)
    said = lines(result)
    paused, picked = said.index('Macro: Attack mode paused'), said.index('Macro: a super healing potion: picked up')
    assert paused < picked < len(said) - 1
    assert said[picked + 1] == 'Macro: Attack mode on'  # the runner's own: the mode follows the step
    assert result.kills == [1]


def test_a_pickup_press_with_nothing_to_pick_up_is_a_step_and_the_mode_follows():
    result = play(one_in_the_open(), [Press(0, PICKUP)], 10.0)
    assert lines(result)[0] == 'Macro: Attack mode on'
    assert result.kills == [1]


def test_the_healer_plays_beside_the_macro():
    scene = replace(one_in_the_open(), hero=hero(0.3 * LIFE), mobs=[mob(1, HELL_BOVINE, 1.5, 0.0)])
    result = play(scene, [Press(0, ATTACK)], 10.0, osd=PLAYER_HEALING)
    assert result.alive
    # At 30% of the life the healer's rejuvenation is due at its first look (under 40%), before the macro's own
    # drinking has a second reading to judge by (macros/drinking.py).
    assert (FULL_REJUVENATION, OSD) in [potion[1:] for potion in result.potions]
    # Without the healer the macro drinks by itself, a healing potion first: nothing is being lost yet.
    alone = play(scene, [Press(0, ATTACK)], 10.0)
    assert alone.potions
    assert {who for _, _, who in alone.potions} == {SERVE}


def test_the_healing_scale_reaches_the_arena():
    scene = replace(one_in_the_open(), hero=hero(0.6 * LIFE), mobs=[])
    whole = play(scene, [], 10.0, osd=PLAYER_HEALING)
    weak = play(scene, [], 10.0, osd=PLAYER_HEALING, healing_scale=0.1)
    assert [(kind, who) for _, kind, who in whole.potions] == [(SUPER_HEALING, OSD)]  # one brings it over 65%
    assert len(weak.potions) > 1


def test_ten_plays_with_one_seed_are_equal():
    scene = gloams()
    scene.mobs += [mob(3, HELL_BOVINE, -9.0, 4.0), mob(4, HELL_BOVINE, 5.0, -11.0)]
    scene.drops = potion_on_the_ground().drops
    presses = [Press(0, ATTACK), Press(3.0, PICKUP), Press(6.0, ATTACK), Press(6.5, ATTACK)]
    results = [play(scene, presses, 9.0, osd=PLAYER_HEALING, seed=3) for _ in range(10)]
    assert all(result == results[0] for result in results)
    first = results[0]
    assert first.casts > 0
    assert first.taken > 0.0
    assert first.swaps > 0
    assert len(first.said) > 5
    other = play(scene, presses, 9.0, osd=PLAYER_HEALING, seed=5)
    assert other.said != first.said  # another seed: other pauses, other rolls


def test_every_basic_scene_plays_to_its_end_or_the_death():
    for make in SCENES:
        result = play(make(), [Press(0, ATTACK)], 20.0)
        assert result.seconds == (20.0 if result.alive else result.dead_at)
        assert result == play(make(), [Press(0, ATTACK)], 20.0)


def test_a_monster_behind_a_wall_is_waited_for_and_struck_when_it_comes_round():
    result = play(archer_behind_a_wall(), [Press(0, ATTACK)], 20.0)
    struck = next(at for at, text in result.said if text.startswith('Macro: Echoing Strike'))
    assert struck > 1.0  # no cast at the wall
    assert result.kills == [1]


def test_attack_mode_casts_its_buffs_with_nothing_near():
    scene = one_in_the_open()
    scene.mobs = [mob(1, HELL_BOVINE, 45.0, 0.0)]  # too far to come or to be struck
    scene.hero = replace(scene.hero, consume=False, hex_purge=False, ward=False)
    arena = Arena(scene)
    result = Play(arena, [Press(0, ATTACK)], 6.0, 1).run()
    stand = arena.world.player
    assert stand is not None
    assert (stand.consume, stand.hex_purge, stand.ward) == (True, True, True)
    assert [m.txt_id for m in arena.world.monsters if m.ally] == [DEFILER_CLASS]  # the one summoned after Consume
    assert 'Macro: Consume ran out: casting it again' in lines(result)
    assert result.casts == 0


def test_the_teleport_step_is_not_played_yet():
    with pytest.raises(NotImplementedError, match='the teleport step comes to the arena in Stage 5'):
        play(one_in_the_open(), [Press(0, ATTACK), Press(1.0, TELEPORT)], 5.0)


@pytest.mark.parametrize('routine', [PREBUFF, HUNT_ELITES, 'dance'])
def test_other_routines_are_refused(routine):
    with pytest.raises(ValueError, match='the attack mode toggle and the pickup step'):
        play(one_in_the_open(), [Press(0, routine)], 5.0)


def test_the_build_handed_in_is_the_one_played():
    # The build played when none is named, handed in with its blades: the same play, blade for blade.
    assert play(one_in_the_open(), [Press(0, ATTACK)], 5.0, build=BUILD, blades=True) == play(
        one_in_the_open(), [Press(0, ATTACK)], 5.0
    )


def test_a_build_without_an_attack_ends_attack_mode_with_that_said():
    result = play(one_in_the_open(), [Press(0, ATTACK)], 5.0, build=GENERIC)
    assert result.casts == 0
    assert any('attack mode off: the build (generic) has no attack of its own' in line for line in lines(result))
    assert lines(result).count('Macro: Attack mode on') == 1  # said before the first look, which names the build


def test_the_runners_time_is_the_arenas_for_the_play_and_put_back_after(monkeypatch):
    seen = []
    real = Play.execute

    def looking(self, cancelled, routine):
        seen.append((runner_module.time.monotonic(), self.arena.clock.now))
        return real(self, cancelled, routine)

    monkeypatch.setattr(Play, 'execute', looking)
    play(one_in_the_open(), [Press(1.0, ATTACK)], 3.0)
    assert seen == [(1.0, 1.0)]
    assert all(module.time is time for module in runner_modules() if hasattr(module, 'time'))


def test_wall_time_decides_nothing(monkeypatch):
    """A machine a thousand times slower by the wall's clock plays the same."""
    plain = play(gloams(), [Press(0, ATTACK), Press(1.0, PICKUP)], 6.0)
    started = time.monotonic()
    monkeypatch.setattr(driver, 'WALL_LIMIT', 1e9)
    monkeypatch.setattr(time, 'monotonic', lambda: started + 1000.0 * (time.perf_counter() - started))
    assert play(gloams(), [Press(0, ATTACK), Press(1.0, PICKUP)], 6.0) == plain


def test_a_fault_is_raised_not_played_as_a_result(monkeypatch):
    def broken(*args):
        raise ZeroDivisionError('a fault of the arena')

    monkeypatch.setattr(driver, 'pick_up', broken)
    with pytest.raises(ZeroDivisionError, match='a fault of the arena'):
        play(potion_on_the_ground(), [Press(0, PICKUP)], 5.0)
    assert all(module.time is time for module in runner_modules() if hasattr(module, 'time'))
