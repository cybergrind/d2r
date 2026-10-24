"""A broken Psychic Ward first in a fight (builds/warlock/buffs.py WARD_BROKEN_FIRST, 2026-10-24): the T4-5 fights of
2026-10-24 lost 76 % of their life in the 6.3 % of the time the ward was down (rca/2026-10-24/aggro-findings.md)."""

from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as warlock_buffs
from inventory_tracking.builds.warlock.buffs import WARD_MANA, ward_broken
from inventory_tracking.builds.warlock.skills import PSYCHIC_WARD
from tests.inventory_tracking.builds.warlock.test_buffs import HEX_RETRY, game, rotation_of


def broken_row(rotation):
    return rotation.buffs.rows('fight')[0]


def worlds(play):
    gone = replace(play.world, player=replace(play.character, ward=False, cooldown=False))
    return gone, replace(gone, player=replace(gone.player, ward=True))


def test_off_a_broken_ward_waits_out_ward_seconds_in_a_fight_as_before(monkeypatch) -> None:
    monkeypatch.setattr(warlock_buffs, 'WARD_BROKEN_FIRST', False)  # on in live since 2026-10-24 ~17:30
    play = game()
    rotation, run = rotation_of(), play.run()
    gone, _ = worlds(play)
    rotation.warded_at, rotation.wards_unseen = play.clock.now, 1
    play.clock.now += HEX_RETRY + 0.1
    assert not rotation.ward_due(run, gone, fighting=True)
    facts = rotation.buffs.facts(run, gone)
    assert not rotation.buffs.before_strike(facts)
    assert not ward_broken(facts)
    assert rotation.buffs.due(run, broken_row(rotation), facts) is None


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(warlock_buffs, 'WARD_BROKEN_FIRST', True)


def test_on_a_broken_ward_is_due_at_once_first_in_the_fight_and_before_the_strike(on) -> None:
    play = game()
    rotation, run = rotation_of(), play.run()
    gone, shown = worlds(play)
    rotation.warded_at, rotation.wards_unseen = play.clock.now, 1
    play.clock.now += HEX_RETRY + 0.1  # the cast's state not shown after the retry wait: the ward broke
    assert rotation.ward_due(run, gone, fighting=True)
    facts = rotation.buffs.facts(run, gone)
    assert rotation.buffs.before_strike(facts)
    row = broken_row(rotation)
    assert row.skill == PSYCHIC_WARD
    assert row.before_strike is not None
    assert rotation.buffs.due(run, row, facts) is not None
    first = rotation.buffs.first(run, 'fight', facts)
    assert first is not None
    assert first.row is row  # ahead of Engorge, the sigil and Death Mark
    assert not rotation.buffs.before_strike(rotation.buffs.facts(run, shown))  # shown: nothing to do


def test_on_no_cast_while_the_casting_delay_runs_or_the_mana_is_short(on) -> None:
    play = game()
    rotation, run = rotation_of(), play.run()
    gone, _ = worlds(play)
    play.clock.now += HEX_RETRY + 0.1
    cooled = replace(gone, player=replace(gone.player, cooldown=True))
    assert not ward_broken(rotation.buffs.facts(run, cooled))
    short = replace(rotation.buffs.facts(run, gone), mana=lambda: WARD_MANA - 1)
    assert not ward_broken(short)
    unread = replace(rotation.buffs.facts(run, gone), mana=lambda: None)
    assert ward_broken(unread)
    assert not ward_broken(rotation.buffs.facts(run, replace(gone, slots=())))  # not on a key: never asked for


def test_on_the_ward_state_unread_is_no_break(on) -> None:
    play = game()
    rotation, run = rotation_of(), play.run()
    unread = replace(play.world, player=replace(play.character, ward=None, cooldown=False))
    assert not ward_broken(rotation.buffs.facts(run, unread))
