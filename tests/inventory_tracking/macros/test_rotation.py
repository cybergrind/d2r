"""The casts under the held strike (macros/rotation.py): when each is due."""

from dataclasses import replace

from inventory_tracking.combat.policy import LinePolicy
from inventory_tracking.macros.rotation import HEX_DISTRUST, HEX_RETRY, HEX_TRIES, SIGIL_SECONDS, WARD_SECONDS, Rotation
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, world


def game():
    return Game(world(area=101, slots=HUNT_SLOTS))


def test_a_sigil_is_due_under_an_elite_once_the_last_one_under_it_is_old():
    play = game()
    rotation, run = Rotation(LinePolicy), play.run()
    elite, plain = Monster(1, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, 0x0C), Monster(2, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, 0)
    assert rotation.sigil_due(run, elite)
    assert not rotation.sigil_due(run, plain)
    rotation.sigiled[1] = play.clock.now
    assert not rotation.sigil_due(run, elite)
    play.clock.now += SIGIL_SECONDS + 0.1
    assert rotation.sigil_due(run, elite)


def test_hex_purge_is_due_while_the_state_does_not_show_it_and_distrusted_after_unseen_casts():
    play = game()
    rotation, run = Rotation(LinePolicy), play.run()
    shown = replace(play.world, player=replace(play.world.player, hex_purge=True))
    gone = replace(play.world, player=replace(play.world.player, hex_purge=False))
    assert not rotation.purge_due(run, shown)
    assert rotation.purge_due(run, gone)
    rotation.purged_at, rotation.purges_unseen = play.clock.now, 1
    assert not rotation.purge_due(run, gone)
    play.clock.now += HEX_RETRY + 0.1
    assert rotation.purge_due(run, gone)
    rotation.purged_at, rotation.purges_unseen = play.clock.now, HEX_TRIES
    play.clock.now += HEX_RETRY + 0.1
    assert not rotation.purge_due(run, gone)  # cast and never seen: not every few seconds
    play.clock.now += HEX_DISTRUST
    assert rotation.purge_due(run, gone)


def test_psychic_ward_is_due_while_the_state_does_not_show_it_and_in_a_fight_once_in_five_seconds():
    play = game()
    rotation, run = Rotation(LinePolicy), play.run()
    shown = replace(play.world, player=replace(play.world.player, ward=True))
    gone = replace(play.world, player=replace(play.world.player, ward=False))
    unread = replace(play.world, player=replace(play.world.player, ward=None))
    assert not rotation.ward_due(run, shown)
    assert not rotation.ward_due(run, unread)
    assert rotation.ward_due(run, gone)
    assert rotation.ward_due(run, gone, fighting=True)
    rotation.warded_at, rotation.wards_unseen = play.clock.now, 1
    play.clock.now += HEX_RETRY + 0.1
    assert rotation.ward_due(run, gone)
    assert not rotation.ward_due(run, gone, fighting=True)  # a pack breaks it faster than it is cast
    play.clock.now += WARD_SECONDS
    assert rotation.ward_due(run, gone, fighting=True)
    assert not rotation.ward_due(run, replace(gone, slots=()))  # not on a key: never asked for
