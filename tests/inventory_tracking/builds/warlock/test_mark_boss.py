"""A Death Mark cast again on a boss whose last mark still shows is judged by its state after MARK_SHOWS, not by the old
mark's state (macros/buffs.py `Buffs.settle`, SHOWN_BEFORE_WAITS). The player, 2026-10-21 ~17:41: "note: we haven't used
death mark on baal, that is incorrect".

The take 20261021T143818Z-132 (the Worldstone Chamber): the first key at 17:38:22.16 took (state 212 on 17:38:22.51 to
17:38:34.81); the second at 17:38:34.16, 0.65 s before the first ran out, brought no cast and no state, and was taken
as landed by the old mark's state: Baal fought unmarked from 34.81 to his death at 44.6."""

import logging
from dataclasses import replace

from inventory_tracking.builds.warlock.buffs import BUFFS
from inventory_tracking.builds.warlock.mark import MARK_SHOWS
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import buffs as executor
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Build
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, WINDOW, Game, world


BAAL = Monster(324081540, 544, 1, 5000.0, 5012.0, flags=0x08, life=56, max_life=128)
DEFILER = Monster(72923, 744, 1, 4996.0, 5000.0, 1, ally=True, life=124, max_life=128)
MARKED = bytes(26) + b'\x10' + bytes(5)  # state 212: word 6, bit 20
ROW = next(row for row in BUFFS if row.skill == DEATH_MARK)


def fight(buffs, play):
    seen = replace(world(area=131, slots=(*HUNT_SLOTS, DEATH_MARK)), monsters=(BAAL, DEFILER))
    play.world = seen
    return BuffFacts(seen, play.clock.now, foes=(BAAL,), reachable=(BAAL,), prey=BAAL, cast_at=buffs.cast_at)


def recast_on_a_mark_that_still_shows(caplog):
    """The second key of the take: Baal's old mark still on at the key and 0.65 s after, then off; (lines, the next
    ask's target)."""
    buffs = Buffs(Build(name='warlock', applies=lambda w: True, attack=None, movement=(), buffs=(ROW,)))
    play = Game(world(area=131))
    run = play.run()
    shown = {'words': MARKED}
    run.unit_states = lambda m: shown['words']
    play.clock.now = 34.16
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        due = buffs.due(run, ROW, fight(buffs, play))
        assert due is not None
        assert due.target is not None
        assert due.target.unit_id == BAAL.unit_id
        tried = buffs.cast(run, due, lambda w, skills: {DEATH_MARK: 'd'}, WINDOW[2] / WINDOW[3])
        assert tried.cast
        assert tried.at is not None
        # the old mark on 0.65 s past the key (17:38:34.16 -> 34.81), then off
        for after, words in ((0.1, MARKED), (0.5, MARKED), (0.7, bytes(32)), (MARK_SHOWS + 0.05, bytes(32))):
            play.clock.now = tried.at + after
            shown['words'] = words
            again = buffs.due(run, ROW, fight(buffs, play))
    return [r.getMessage() for r in caplog.records if 'did not take' in r.getMessage()], again


def test_a_recast_on_a_mark_that_still_shows_is_judged_after_the_old_one_ends(caplog):
    lines, again = recast_on_a_mark_that_still_shows(caplog)
    assert len(lines) == 1
    assert lines[0].startswith('Macro: buff: Death Mark on the elite 544 (324081540)')
    assert lines[0].endswith('cast again (try 2)')
    assert again is not None
    assert again.target is not None
    assert again.target.unit_id == BAAL.unit_id  # Baal marked again


def test_without_the_switch_the_old_marks_state_counts_as_the_new_one(monkeypatch, caplog):
    monkeypatch.setattr(executor, 'SHOWN_BEFORE_WAITS', False)
    lines, again = recast_on_a_mark_that_still_shows(caplog)
    assert lines == []  # the take's silent miss
    assert again is None
