"""One UI action (macros/act.py): nothing pressed when its effect is there already, each try waited for, a bounded
number of tries, a typed failure naming the open panels; and `until`, the one wait every look of which honours the
run's cancel."""

from dataclasses import replace

import pytest

from inventory_tracking.macros.act import NOT_DONE, Action, Failed, perform, until
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.game.records import Pack
from tests.inventory_tracking.macros.fakes import Game, world


def stash_open(w) -> bool:
    return 'stash' in w.open_panels


def game() -> Game:
    return Game(world(103))


def opens_on(play: Game, at: float, panels=('inventory', 'stash')) -> None:
    """The game opens `panels` on its own at clock time `at` (an earlier click's effect still coming)."""
    play.arrivals.append((at, lambda: setattr(play, 'world', replace(play.world, open_panels=panels))))


def test_until_returns_the_first_look_in_which_it_holds():
    play = game()
    opens_on(play, 0.3)

    seen = until(play.run(), stash_open, 1.0)

    assert seen is not None
    assert stash_open(seen)
    assert 0.3 <= play.clock.now < 0.4


def test_until_gives_none_once_its_seconds_are_out():
    play = game()

    assert until(play.run(), stash_open, 1.0) is None
    assert play.clock.now == pytest.approx(1.0)


def test_until_with_no_seconds_looks_once():
    play = game()
    looks = []
    run = play.run()
    read = run.read
    run.read = lambda: looks.append(1) or read()

    assert until(run, stash_open, 0.0) is None
    assert looks == [1]
    assert play.clock.now == 0.0


def test_until_stops_at_the_first_look_after_a_cancel():
    play = game()
    run = play.run()
    play.arrivals.append((0.2, run.cancelled.set))

    with pytest.raises(Cancelled):
        until(run, stash_open, 5.0)

    assert play.clock.now < 0.3


def test_until_reads_what_it_is_given_a_none_being_no_look():
    """The stash's and the cube's item waits (`_until`): the carried items, an unread pack waited past."""
    play = game()
    run = play.run()
    packs = iter([None, Pack(), Pack(pointer=7)])

    def pointed(pack: Pack) -> bool:
        return pack.pointer == 7

    seen = until(run, pointed, 1.0, read=lambda: next(packs))

    assert seen == Pack(pointer=7)
    assert play.clock.now == pytest.approx(0.1)


def test_until_reading_its_own_honours_the_cancel_too():
    play = game()
    run = play.run()
    run.cancelled.set()

    with pytest.raises(Cancelled):
        until(run, lambda p: True, 1.0, read=Pack)


def clicks(play: Game, works_on: int | None = 1, opens=('inventory', 'stash')):
    """An act that clicks once a try, its effect showing on the try numbered `works_on` (from 1); None: never."""
    tries: list[int] = []

    def act(run, attempt: int) -> None:
        tries.append(attempt)
        if works_on is not None and len(tries) >= works_on:
            opens_on(play, play.clock.now + 0.1, opens)

    return act, tries


def test_an_effect_there_already_presses_nothing():
    """14:42:09 on 2026-10-18 as the action layer sees it: the walk's click opened the panel; no try is made."""
    play = game()
    play.world = replace(play.world, open_panels=('inventory', 'stash'))
    act, tries = clicks(play)

    outcome = perform(play.run(), Action('the stash', stash_open, act, wait=1.5))

    assert outcome.already
    assert outcome.tries == 0
    assert tries == []


def test_an_effect_coming_within_the_grace_presses_nothing():
    play = game()
    opens_on(play, 0.15)
    act, tries = clicks(play)

    outcome = perform(play.run(), Action('the stash', stash_open, act, wait=1.5, grace=0.25))

    assert outcome.already
    assert tries == []


def test_the_second_try_brings_it():
    play = game()
    act, tries = clicks(play, works_on=2)

    outcome = perform(play.run(), Action('the stash', stash_open, act, wait=0.5, tries=3))

    assert not outcome.already
    assert outcome.tries == 2
    assert tries == [0, 1]


def test_the_repair_between_tries_is_made_with_the_last_look():
    play = game()
    act, _ = clicks(play, works_on=2)
    repairs = []

    perform(play.run(), Action('the stash', stash_open, act, wait=0.5, tries=2, between=lambda r, w: repairs.append(w)))

    assert len(repairs) == 1
    assert not stash_open(repairs[0])


def test_an_effect_the_repair_brought_takes_no_next_try():
    """A repair that is itself the effect (a step back whose click lands on the waypoint): no click onto it."""
    play = game()
    act, tries = clicks(play, works_on=None)

    def repair(run, w):
        play.world = replace(play.world, open_panels=('inventory', 'stash'))

    outcome = perform(play.run(), Action('the stash', stash_open, act, wait=0.5, tries=3, between=repair))

    assert outcome.tries == 1
    assert tries == [0]


def test_a_late_effect_after_the_last_try_is_accepted():
    play = game()
    tries = []

    def slow(run, attempt):
        tries.append(attempt)
        opens_on(play, play.clock.now + 0.7)

    outcome = perform(play.run(), Action('the stash', stash_open, slow, wait=0.5, late=0.5))

    assert outcome.tries == 1
    assert not outcome.already


def test_no_effect_fails_by_type_naming_the_open_panels():
    play = game()
    act, tries = clicks(play, works_on=None)
    play.world = replace(play.world, open_panels=('inventory',))

    with pytest.raises(Failed) as failed:
        perform(play.run(), Action('the stash', stash_open, act, wait=0.5, tries=2))

    assert tries == [0, 1]
    assert failed.value.action == 'the stash'
    assert failed.value.reason == NOT_DONE
    assert 'open panels: inventory' in str(failed.value)


def test_a_cancel_during_the_wait_stops_the_action():
    play = game()
    run = play.run()
    act, tries = clicks(play, works_on=None)
    play.arrivals.append((0.2, run.cancelled.set))

    with pytest.raises(Cancelled):
        perform(run, Action('the stash', stash_open, act, wait=1.0, tries=3))

    assert tries == [0]


def test_one_log_line_per_action(caplog):
    play = game()
    act, _ = clicks(play, works_on=2)

    with caplog.at_level('INFO'):
        perform(play.run(), Action('the stash', stash_open, act, wait=0.5, tries=2))

    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: act ')]
    assert len(lines) == 1
    assert lines[0].startswith('Macro: act the stash: done after 2 tries in ')
