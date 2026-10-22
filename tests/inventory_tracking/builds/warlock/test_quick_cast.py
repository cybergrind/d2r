"""A Quick Cast key under a held strike: pressed QUICK_SETTLE_SECONDS after the strike's release, and a Death Mark key
the game cast nothing for pressed once more at once (macros/buffs.py QUICK_SETTLE, QUICK_CONFIRM). The player,
2026-10-21 ~17:41: "note: we haven't used death mark on baal, that is incorrect".

The takes of 2026-10-21: a key pressed within 10 ms of the release while the character was free or its cast was
ending brought no cast in 58 of 184 (the right button showed the skill one frame, then the character stood);
6 of 47 at 10-50 ms; 0 of 8 later. Baal's second mark, 17:38:34.16: 3 ms."""

import logging
from dataclasses import replace

from inventory_tracking.builds.warlock.buffs import BUFFS
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import buffs as executor
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Build
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, WINDOW, Game, world


BAAL = Monster(324081540, 544, 1, 5000.0, 5012.0, flags=0x08, life=56, max_life=128)
DEFILER = Monster(72923, 744, 1, 4996.0, 5000.0, 1, ally=True, life=124, max_life=128)
ROW = next(row for row in BUFFS if row.skill == DEATH_MARK)


def marking(monkeypatch, *, cast_seen: bool):
    """A Death Mark on Baal under a held strike, the presses and sleeps recorded in order; (calls, log lines)."""
    buffs = Buffs(Build(name='warlock', applies=lambda w: True, attack=None, movement=(), buffs=(ROW,)))
    play = Game(world(area=131))
    run = play.run()
    run.unit_states = lambda m: bytes(32)
    seen = replace(world(area=131, slots=(*HUNT_SLOTS, DEATH_MARK)), monsters=(BAAL, DEFILER))
    play.world = seen
    calls: list[tuple] = []
    buffs.let_go = lambda: calls.append(('let go',))
    monkeypatch.setattr(run.actuator, 'holding', frozenset((1,)))
    sleep = run.pace.sleep
    monkeypatch.setattr(run.pace, 'sleep', lambda s: (calls.append(('sleep', round(s, 3))), sleep(s)))
    monkeypatch.setattr(executor, 'press_through', lambda r, skill: calls.append(('through', skill)))
    monkeypatch.setattr(executor, 'press_skill', lambda r, skill, *a, **k: calls.append(('again', skill)))
    monkeypatch.setattr(executor, 'AIM_CHECK', False)
    monkeypatch.setattr(run, 'seen', lambda *a, **k: seen if cast_seen else None)
    facts = BuffFacts(seen, play.clock.now, foes=(BAAL,), reachable=(BAAL,), prey=BAAL, cast_at=buffs.cast_at)
    due = buffs.due(run, ROW, facts)
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: {DEATH_MARK: 'd'}, WINDOW[2] / WINDOW[3])
    assert tried.cast
    return calls


def key_release(calls: list[tuple]) -> int:
    """The release the key makes: the last. Since 2026-10-21 (executor.LET_GO_FIRST) the strike is let go before the
    pointer goes onto the target too, and the key's own release finds it let go."""
    assert calls.count(('let go',)) == 2
    return len(calls) - 1 - calls[::-1].index(('let go',))


def test_the_key_waits_out_the_release_of_the_strike(monkeypatch):
    calls = marking(monkeypatch, cast_seen=True)
    at = key_release(calls)
    assert calls[at + 1] == ('sleep', executor.QUICK_SETTLE_SECONDS)
    assert calls[at + 2] == ('through', DEATH_MARK)


def test_without_the_settle_the_key_follows_the_release(monkeypatch):
    monkeypatch.setattr(executor, 'QUICK_SETTLE', False)
    calls = marking(monkeypatch, cast_seen=True)
    at = key_release(calls)
    assert calls[at + 1] == ('through', DEATH_MARK)


def test_a_mark_key_the_game_cast_nothing_for_is_pressed_again(monkeypatch, caplog):
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        calls = marking(monkeypatch, cast_seen=False)
    assert ('again', DEATH_MARK) in calls
    assert calls.index(('again', DEATH_MARK)) > calls.index(('through', DEATH_MARK))
    lines = [r.getMessage() for r in caplog.records if 'cast nothing' in r.getMessage()]
    assert lines == [
        'Macro: buff: the game cast nothing after the Death Mark key on the elite 544 (324081540): pressed again'
    ]


def test_a_mark_key_cast_is_not_pressed_again(monkeypatch):
    calls = marking(monkeypatch, cast_seen=True)
    assert ('again', DEATH_MARK) not in calls


def test_without_the_confirm_a_key_cast_nothing_for_waits_for_the_settle(monkeypatch):
    monkeypatch.setattr(executor, 'QUICK_CONFIRM', False)
    calls = marking(monkeypatch, cast_seen=False)
    assert ('again', DEATH_MARK) not in calls
