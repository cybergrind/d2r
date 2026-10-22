"""Bind Demon again in a tier 4-5 Herald pack fight, and the Defiler summoned between the character and the pack
(builds/warlock/bind.py, defiler.py `pack_spot`; combat/pack.py REBIND_DEMON, PETS_BETWEEN). The player, 2026-10-21
~09:40: "keep them busy with a daemon ... keep group on our daemon, not ourselves or merc"; ~10:00 (Q6): "the bound
demon holds the pack as the Defiler does", "summoned even under attack, from range". Bind Demon (skills.txt 382:
pettype binddemon, petmax 1, TargetableOnly) takes a monster that monstats calls a demon (`demon` 1)."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import bind, defiler as defiler_module
from inventory_tracking.builds.warlock.buffs import BUFFS
from inventory_tracking.builds.warlock.casters import CASTERS
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import BIND_DEMON
from inventory_tracking.combat import pack
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Casting
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, WINDOW, Game, world


NOW = 100.0
GREAT_MARSH = 77
NOBODY = 0xFFFFFFFF
UNIQUE, MINION = 0x08, 0x10
URDAR, PIT_LORD, DEFILER = 189, 361, 744


@pytest.fixture(autouse=True)
def binds_cast(monkeypatch):
    """The rebind as built (bind.py BIND_DEMON_CASTS on): the player's ruling of 2026-10-21 ~16:30 keeps it off live,
    tested in test_pets.py."""
    monkeypatch.setattr(bind, 'BIND_DEMON_CASTS', True)


def hulk(unit: int, x: float, y: float, flags: int = MINION, tier: int = 5) -> Monster:
    return Monster(unit, 128, 1, x, y, NOBODY, flags, life=128, max_life=128, tier=tier)


def pet(unit: int, txt: int, x: float, y: float) -> Monster:
    return Monster(unit, txt, 1, x, y, NOBODY, 0, ally=True, life=128, max_life=230)


HERALD = hulk(1, 5016.0, 5000.0, UNIQUE)
MINIONS = (hulk(2, 5018.0, 5003.0), hulk(3, 5017.0, 4996.0))
WILD_URDAR = Monster(40, URDAR, 1, 5010.0, 4992.0, NOBODY, 0, life=128, max_life=128)  # a plain demon, 12.8 off
DEFILER_OUT = pet(70, DEFILER, 5001.5, 5001.0)  # by the character: it holds nobody (combat/pack.py DEMON_APART)
BOUND = pet(71, URDAR, 5004.0, 4999.0)


def facts(*monsters: Monster, cast_at=None) -> BuffFacts:
    seen = world(GREAT_MARSH, slots=HUNT_SLOTS, monsters=monsters)
    foes = tuple(m for m in monsters if not m.ally)
    return BuffFacts(seen, NOW, foes, foes, cast_at=cast_at or {})


def test_the_game_data_calls_the_urdar_and_the_pit_lord_demons_and_the_bramble_hulk_not():
    rows = tables()['monsters']
    assert rows[str(URDAR)]['demon'] == '1'
    assert rows[str(PIT_LORD)]['demon'] == '1'
    assert 'demon' not in rows['128']
    assert bind.bindable(WILD_URDAR)
    assert not bind.bindable(HERALD)
    assert not bind.bindable(replace(WILD_URDAR, flags=UNIQUE))  # a leader: not taken (not verified in the game)
    assert not bind.bindable(BOUND)  # the character's own


def test_the_bound_demon_is_the_character_s_demon_that_is_no_summon():
    seen = facts(HERALD, DEFILER_OUT, BOUND).world
    assert bind.bound(seen) == [BOUND]
    assert bind.bound(facts(HERALD, DEFILER_OUT).world) == []


def test_with_the_bound_demon_gone_in_a_pack_fight_a_demon_in_reach_is_bound_again():
    asked = facts(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT)
    assert bind.bind_due(asked)
    assert bind.bind_target(asked) == WILD_URDAR


def test_no_bind_while_the_bound_demon_lives_with_no_pack_or_with_no_demon_to_bind():
    assert not bind.bind_due(facts(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT, BOUND))
    plain = tuple(replace(m, tier=3) for m in (HERALD, *MINIONS))
    assert not bind.bind_due(facts(*plain, WILD_URDAR, DEFILER_OUT))
    assert bind.bind_target(facts(HERALD, *MINIONS, DEFILER_OUT)) is None


def test_no_bind_with_the_pack_on_the_character_within_10_the_hop_back_comes_first():
    close = hulk(5, 5006.0, 5000.0)
    assert not bind.bind_due(facts(HERALD, *MINIONS, close, WILD_URDAR, DEFILER_OUT))


def test_a_bind_that_did_not_bring_a_demon_is_tried_again_after_its_retry():
    soon = {(BIND_DEMON, None): NOW - bind.BIND_RETRY + 0.5}
    assert not bind.bind_due(facts(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT, cast_at=soon))
    later = {(BIND_DEMON, None): NOW - bind.BIND_RETRY - 0.1}
    assert bind.bind_due(facts(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT, cast_at=later))


def test_the_switches_stop_the_bind(monkeypatch):
    monkeypatch.setattr(pack, 'REBIND_DEMON', False)
    assert not bind.bind_due(facts(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT))
    monkeypatch.setattr(pack, 'REBIND_DEMON', True)
    monkeypatch.setattr(pack, 'PACK_TACTIC', False)
    assert not bind.bind_due(facts(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT))


def test_the_fight_plan_has_the_bind_row_on_a_monster_after_the_defiler():
    rows = [row for row in BUFFS if row.phase == 'fight']
    skills = [row.skill for row in rows]
    found = rows[skills.index(BIND_DEMON)]
    assert found.on == 'monster'
    assert found.caster == 'bind'
    assert skills.index(BIND_DEMON) > skills.index(defiler_module.SUMMON_DEFILER)


def test_the_defiler_is_summoned_between_the_character_and_the_pack():
    asked = facts(HERALD, *MINIONS)
    here = (5000.0, 5000.0)
    spot = defiler_module.pack_spot(asked)
    assert spot is not None
    middle = pack.centre(here, pack.members(asked.foes))
    assert math.dist(spot, middle) < math.dist(here, middle)
    assert math.dist(spot, here) <= pack.PET_SPOT + 1e-6
    assert all(math.dist(spot, m.at) >= pack.SURROUND_RADIUS for m in pack.members(asked.foes))


def test_no_spot_between_with_no_pack_or_with_the_switch_off(monkeypatch):
    plain = tuple(replace(m, tier=3) for m in (HERALD, *MINIONS))
    assert defiler_module.pack_spot(facts(*plain)) is None
    monkeypatch.setattr(pack, 'PETS_BETWEEN', False)
    assert defiler_module.pack_spot(facts(HERALD, *MINIONS)) is None


def casting(play: Game, skill: int, target: Monster | None = None, key_names=None) -> Casting:
    row = next(r for r in BUFFS if r.skill == skill and r.phase == 'fight')
    names = key_names or (lambda w, skills: {s: KEYS[s] for s in skills})
    return Casting(play.run(), row, Buffs(ECHOING_STRIKE_BUILD), play.world, target, WINDOW[2] / WINDOW[3], names)


def test_the_fight_s_defiler_lands_between_the_character_and_the_pack():
    play = Game(world(GREAT_MARSH, slots=HUNT_SLOTS, monsters=(HERALD, *MINIONS)))
    tried = CASTERS['defiler'](casting(play, defiler_module.SUMMON_DEFILER))
    assert tried.cast
    came = next(m for m in play.world.monsters if m.txt_id == DEFILER)
    here = (5000.0, 5000.0)
    middle = pack.centre(here, pack.members((HERALD, *MINIONS)))
    assert math.dist((came.x, came.y), middle) < math.dist(here, middle) - 3.0


def test_the_bind_caster_presses_its_key_on_the_demon():
    play = Game(world(GREAT_MARSH, slots=HUNT_SLOTS, monsters=(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT)))
    tried = CASTERS['bind'](casting(play, BIND_DEMON, WILD_URDAR))
    assert tried.cast
    assert KEYS[BIND_DEMON] in play.pressed()


def test_a_bind_demon_on_no_key_is_said_and_tried_again_later_not_a_stop():
    def no_key(w, skills):
        raise Abort('Bind Demon has no key the macro can press')

    play = Game(world(GREAT_MARSH, slots=HUNT_SLOTS, monsters=(HERALD, *MINIONS, WILD_URDAR, DEFILER_OUT)))
    tried = CASTERS['bind'](casting(play, BIND_DEMON, WILD_URDAR, no_key))
    assert not tried.cast
    assert tried.at is not None
    assert tried.at > play.clock.now  # counted ahead: the row waits BIND_NO_KEY
    assert play.pressed() == []
