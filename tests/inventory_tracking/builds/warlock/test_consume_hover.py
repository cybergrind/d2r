"""Consume with something else under the pointer on the Defiler (casters.py CONSUME_HOVER_CHECK, 2026-10-24;
rca/2026-10-24/consume-miss-findings.md): the game's record of the unit under the pointer names an item's label, an
object or the mercenary, and the key casts nothing."""

import logging

import pytest

from inventory_tracking.builds.warlock import buffs as plan, casters
from inventory_tracking.builds.warlock.casters import renew_consume
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.routines import prebuff
from tests.inventory_tracking.macros.fakes import Game, world


POTION = 2190385010  # the super healing potion whose label lay over the Defiler (take 20261024T112707Z-101)
OBJECT = 3657335076  # the object under the pointer at 14:24:20 on 2026-10-24 (take 20261024T112253Z-117)
MERC = Monster(70, 338, 2, 5004.0, 4999.0, 0x10)  # monstats.txt act2hire, walking (13:06:51 on 2026-10-24)


def covered(game, run, over, times=1):
    """The first `times` new Defilers have `over` under the pointer on them for good (a drop's label, an object: they
    do not walk off): the record names it while the pointer is on such a Defiler, and Consume there casts nothing."""
    react, left, under = game.keys.on_event, [times], set()

    def on_event(event):
        if event == ('key', '6') and game.pet_under_pointer() in under:
            return
        react(event)
        if event == ('key', 'q') and left[0]:
            left[0] -= 1
            under.add(max(m.unit_id for m in game.world.monsters if m.txt_id == 744))

    game.keys.on_event = on_event
    shown = run.hovered
    assert shown is not None
    run.hovered = lambda: over if game.pet_under_pointer() in under else shown()


def walked_over(game, run, over):
    """`over` (the mercenary) is under the pointer on the Defiler at the first look there, by key or by the record,
    and walks off after it."""
    react, there = game.keys.on_event, [True]

    def on_event(event):
        if event == ('key', '6') and there[0]:
            there[0] = False
            return
        react(event)

    def hovered():
        if there[0] and game.pet_under_pointer() is not None:
            there[0] = False
            return over
        return shown()

    game.keys.on_event = on_event
    shown = run.hovered
    assert shown is not None
    run.hovered = hovered


def timed(game):
    """When each key went down, by key name, on the game's clock."""
    react, keyed = game.keys.on_event, {}

    def on_event(event):
        if event[0] == 'key':
            keyed.setdefault(event[1], []).append(game.clock.now)
        react(event)

    game.keys.on_event = on_event
    return keyed


@pytest.mark.parametrize('over', [(4, POTION), (2, OBJECT)])
def test_off_three_presses_under_a_label_or_an_object_show_nothing(monkeypatch, caplog, over):
    # 14:30:19.7-27.9 on 2026-10-24 (the Durance of Hate 2): three Consume keys with the potion's label under the
    # pointer on the Defiler, 8.2 s, the character standing; "no Consume ...; again in 20s"
    monkeypatch.setattr(casters, 'CONSUME_HOVER_CHECK', False)
    game = Game(world())
    run = game.run()
    covered(game, run, over)
    caplog.set_level(logging.INFO)
    began = game.clock.now
    prebuff(run)
    assert 'Consume: not seen in 2.5s, 3 times over' in caplog.text
    assert game.pressed() == ['q', '6', '6', '6', 'g', 'r']
    assert not game.character.consume
    assert game.clock.now - began > 7.5


@pytest.mark.parametrize('over', [(4, POTION), (2, OBJECT)])
def test_on_a_label_or_an_object_over_the_defiler_has_another_summoned_before_any_press(monkeypatch, caplog, over):
    monkeypatch.setattr(casters, 'CONSUME_HOVER_CHECK', True)
    game = Game(world())
    run = game.run()
    covered(game, run, over)
    keyed = timed(game)
    caplog.set_level(logging.INFO)
    prebuff(run)
    assert f'under the pointer on the Defiler: {over} (it stays: another is summoned)' in caplog.text
    assert game.pressed().count('6') == 1  # no key under the cover: one, on the next Defiler
    assert game.pressed()[:3] == ['q', 'q', '6']
    assert game.character.consume
    assert keyed['6'][-1] - keyed['q'][0] < 2.0  # against 8.1 s of keys that showed nothing (off)


def test_on_a_renewal_in_the_field_under_the_potions_label_takes_one_press(monkeypatch):
    # The scene of 14:30:18.6: the renewal (`renew_consume`) with the standing Defiler out
    monkeypatch.setattr(casters, 'CONSUME_HOVER_CHECK', True)
    monkeypatch.setattr(plan, 'CONSUME_STANDING', False)
    standing = Monster(900, 744, 1, 5010.0, 5000.0, 0xFFFFFFFF)
    game = Game(world(monsters=(standing,)))
    run = game.run()
    covered(game, run, (4, POTION))
    renew_consume(run)
    assert game.pressed().count('6') == 1
    assert game.character.consume
    assert len([m for m in game.world.monsters if m.txt_id == 744]) == 1


def test_on_a_label_over_every_defiler_gives_up_without_a_press(monkeypatch, caplog):
    monkeypatch.setattr(casters, 'CONSUME_HOVER_CHECK', True)
    game = Game(world())
    run = game.run()
    covered(game, run, (4, POTION), times=99)
    caplog.set_level(logging.INFO)
    prebuff(run)  # and the prebuff goes on without it, as before
    assert '6' not in game.pressed()
    assert 'Macro: prebuff: no Consume' in caplog.text
    assert game.pressed()[-2:] == ['g', 'r']


@pytest.mark.parametrize('check', [False, True])
def test_the_mercenary_walking_over_the_defiler(monkeypatch, caplog, check):
    # 13:06:51.6 on 2026-10-24: the mercenary (class 338, walking) 1.8 units off the Defiler, named under the pointer
    # at the key; the press showed nothing and the next, 2.7 s later, took. `crowd` leaves the mercenary out.
    monkeypatch.setattr(casters, 'CONSUME_HOVER_CHECK', check)
    game = Game(world(monsters=(MERC,)))
    run = game.run()
    walked_over(game, run, (1, MERC.unit_id))
    keyed = timed(game)
    caplog.set_level(logging.INFO)
    prebuff(run)
    assert game.character.consume
    assert ('(it walks: looked at again)' in caplog.text) is check
    assert game.pressed().count('6') == (1 if check else 2)
    took = keyed['6'][-1] - keyed['q'][0]  # from the summon to the key that took
    assert took < 2.0 if check else took > 2.5


def test_on_a_defiler_named_under_the_pointer_or_nothing_presses_as_before(monkeypatch):
    monkeypatch.setattr(casters, 'CONSUME_HOVER_CHECK', True)
    game = Game(world())
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert game.character.consume


@pytest.mark.parametrize('named', ['a Defiler', 'a unit not in the look'])
def test_on_another_defiler_or_an_unknown_unit_under_the_pointer_is_no_cover(monkeypatch, named):
    # CONSUME_ANY_DEFILER: a Consume taking the Defiler beside the one aimed at is a Consume
    monkeypatch.setattr(casters, 'CONSUME_HOVER_CHECK', True)
    game = Game(world())
    run = game.run()

    def hovered():
        if named == 'a unit not in the look':
            return (1, 12345)
        return (1, min(m.unit_id for m in game.world.monsters if m.txt_id == 744))

    run.hovered = hovered
    prebuff(run)
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert game.character.consume
