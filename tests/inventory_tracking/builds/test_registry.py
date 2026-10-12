"""The one list of the builds (builds/__init__.py) and the characters' layers (builds/characters.py):
whose build the character in the game gets from them (macros/build.py `choose`)."""

from dataclasses import replace

from inventory_tracking.builds import BUILDS, FALLBACK
from inventory_tracking.builds.characters import CHARACTERS, LAYERS, PLAYS, played_by
from inventory_tracking.builds.generic import GENERIC
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.macros.build import Loadout, choose
from inventory_tracking.macros.movement import SHARED
from inventory_tracking.macros.skills import TELEPORT
from tests.inventory_tracking.macros.fakes import BUILD, HUNT_SLOTS, PREBUFF_SET, player, world


OFF_KEYS = (TELEPORT, None)  # no Echoing Strike on a key


def chosen(found):
    return choose(BUILDS, found, FALLBACK)


def test_the_character_the_macros_know_gets_the_warlock_with_its_weapon_sets():
    build = chosen(world(slots=HUNT_SLOTS))
    assert build is BUILD
    assert build is LAYERS[0]
    assert build.weapons == Loadout(prebuff=frozenset(PREBUFF_SET), battle=frozenset(PREBUFF_SET))
    assert build.weapons is CHARACTERS['CybergrindAA']
    # the rest is the build below it, part for part
    for part in ('name', 'attack', 'movement', 'buffs', 'tactics', 'casters', 'settings'):
        assert getattr(build, part) is getattr(ECHOING_STRIKE_BUILD, part)


def test_the_same_build_is_chosen_at_every_asking():
    assert chosen(world(slots=HUNT_SLOTS)) is chosen(world(slots=HUNT_SLOTS, area=101))


def test_it_is_that_characters_whatever_its_keys_hold():
    # As before the runner chose: the macro request, the main weapons and attack mode's own word on a
    # strike that is on no input were CybergrindAA's by its name alone.
    assert chosen(world(slots=OFF_KEYS)) is BUILD


def test_another_character_with_the_strike_gets_the_warlock_without_weapon_sets():
    on_a_key = replace(world(slots=HUNT_SLOTS), player=player(name='Someone'))
    on_a_button = replace(world(slots=OFF_KEYS), player=player(name='Someone', right_skill=ECHOING_STRIKE))
    for found in (on_a_key, on_a_button):
        build = chosen(found)
        assert build is ECHOING_STRIKE_BUILD
        assert build.weapons is None


def test_a_character_with_the_strike_nowhere_gets_the_generic_build():
    assert chosen(replace(world(slots=OFF_KEYS), player=player(name='Someone'))) is GENERIC
    assert FALLBACK is GENERIC


def test_with_no_character_in_the_world_it_is_the_generic_build_and_no_build_claims_it():
    nobody = replace(world(slots=HUNT_SLOTS), player=None)
    assert chosen(nobody) is GENERIC
    assert not any(build.applies(nobody) for build in (*BUILDS, FALLBACK))


def test_the_layers_come_before_the_builds_they_are_layers_of():
    assert (*LAYERS, ECHOING_STRIKE_BUILD) == BUILDS
    assert [build.weapons for build in LAYERS] == [CHARACTERS[name] for name in PLAYS]
    assert set(PLAYS) == set(CHARACTERS)


def test_a_character_without_a_row_is_a_layer_with_no_weapon_sets():
    layer = played_by(ECHOING_STRIKE_BUILD, 'Someone')
    assert layer.weapons is None
    assert layer.applies(replace(world(slots=OFF_KEYS), player=player(name='Someone')))
    assert not layer.applies(world(slots=HUNT_SLOTS))  # CybergrindAA
    assert not layer.applies(replace(world(slots=HUNT_SLOTS), player=None))
    assert ECHOING_STRIKE_BUILD.weapons is None  # the build below is as it was


def test_the_generic_build_moves_by_the_shared_sets_and_has_no_fight_buffs_or_weapon_sets():
    assert GENERIC.movement == SHARED
    assert GENERIC.attack is None
    assert GENERIC.buffs == ()
    assert GENERIC.weapons is None
