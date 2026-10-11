"""The death in Tower Cellar 5 (22:50:37 on 2026-10-11), replayed to the production macro.

"Red" first (user, 2026-10-12): the test that reproduces what happened, action by action, before any
better decision is tried against it. 108 of the 110 recorded actions are replayed, in order and at
their moments; the one strike that is not is a strict xfail with its reason.
"""

import functools

import pytest

from inventory_tracking.combat.takes import monsters_of
from tests.inventory_tracking.scenarios.battle import evidence, tower_cellar5 as battle
from tests.inventory_tracking.scenarios.battle.replay import Replay, character


HERALD = 2960229440
AS_IT_WAS = {'inventory_tracking.macros.hunt.GATHER_CLEAR': 0.0}  # the sweep's rule of that evening
END = 22.7  # just before the teleport key (22.77 s), whose handling has changed since


def record() -> list[evidence.Action]:
    return evidence.read([(at, text) for at, text in battle.recorded() if 0.4 <= at <= END])


@functools.cache
def played(as_it_was: bool, until: float = END) -> list[evidence.Action]:
    replay = Replay(battle.FIXTURE, battle.script(patches=AS_IT_WAS if as_it_was else {}))
    replay.key_names = battle.key_names
    said = replay.run(until)
    actions = evidence.read([(line.at, line.text) for line in said if line.at <= until])
    # The mode's start is the replay's own first press (battle.script), not a key of the player's.
    return [action for action in actions if (action.kind, action.what) != ('press', 'hunt any')]


def compared(as_it_was: bool = True) -> evidence.Compared:
    return evidence.compare(record(), played(as_it_was))


def kinds(actions, *wanted):
    return [(round(action.at, 1), action.kind, action.what) for action in actions if action.kind in wanted]


def test_the_fixture_holds_the_fight_to_the_death():
    replay = Replay(battle.FIXTURE, battle.script())
    died = next(at for at, frame in zip(replay.times, replay.frames, strict=True) if character(frame).mode in (0, 17))
    assert died == pytest.approx(battle.DEATH, abs=0.05)
    seen = [
        (at, m)
        for at, frame in zip(replay.times, replay.frames, strict=True)
        for m in monsters_of(frame)
        if m.unit == HERALD
    ]
    assert seen[0][0] == pytest.approx(13.1, abs=0.1)  # the Herald comes 13 s in
    assert seen[0][1].elite
    at_death = min(seen, key=lambda pair: abs(pair[0] - died))[1]
    assert at_death.life == 82  # of 128: it was never close to dead
    assert len(battle.presses()) == 14  # thirteen pickup keys and the teleport key 0.3 s before the death


def test_the_log_reads_as_actions_with_nothing_unknown_left_out():
    actions = record()
    assert [action.what for action in actions if action.kind == 'press'].count('pickup') == 13
    assert kinds(actions, 'sweep stops', 'drink', 'picking') == [
        (18.2, 'sweep stops', 'a super healing potion'),
        (18.2, 'drink', '3'),
        (18.4, 'picking', 'a super healing potion'),
    ]
    unknown = [action.text for action in actions if action.kind == 'other' and action.at <= battle.DEATH]
    assert all(
        text.startswith(('step asked in the fight', 'pickup: a super healing', 'no aim had'))
        or ' ' not in text.strip()
        or text in ('Blade Warp', 'Sigil: Lethargy')
        for text in unknown
    ), unknown


def test_the_replay_makes_the_decision_that_killed_the_character():
    found = compared()
    same = [recorded for recorded, _ in found.same]
    # The fight is stopped for a potion with the pack around, a potion is drunk for room, the
    # pickup begins and its first click takes nothing: 18.2 to 20.6 s.
    assert kinds(same, 'sweep stops', 'drink', 'picking', 'click missed') == [
        (18.2, 'sweep stops', 'a super healing potion'),
        (18.2, 'drink', '3'),
        (18.4, 'picking', 'a super healing potion'),
        (20.6, 'click missed', '0, 0'),
    ]
    # And before it: the stand is judged good five times beside the pack ("Standing well").
    assert len(kinds(same, 'stand')) >= 5


def test_the_replay_does_what_the_game_did_action_by_action():
    found = compared()
    # 110 recorded actions in 22.7 s; all but one strike and its line are replayed, in order.
    assert len(found.same) >= 108, found.table()
    assert [(action.kind, action.what) for action in found.missing] == [('strike', '740045072'), ('line', '740045072')]
    assert [(action.kind, action.what) for action in found.extra] == [('strike', '46244625')]


def test_the_replay_keeps_the_games_time_without_being_held_to_its_log():
    gaps = sorted(abs(recorded.at - replayed.at) for recorded, replayed in compared().same)
    assert gaps[len(gaps) // 2] <= 0.04  # the median action is 19 ms from its recorded moment
    assert gaps[int(0.9 * len(gaps))] <= 0.12
    assert gaps[-1] <= 0.3


def test_the_slow_keys_under_the_held_strike_are_replayed_at_their_moments():
    # The Sigil came 1.2 s and the Engorge 1.4 s after they were due: a key under the held strike
    # waits for the instant between two casts, and a look every 0.03 s catches one in three or four.
    same = {
        (recorded.kind, recorded.what, round(recorded.at, 1)): replayed.at for recorded, replayed in compared().same
    }
    assert same[('skill', 'Sigil: Lethargy', 7.8)] == pytest.approx(7.82, abs=0.05)
    assert same[('key wait', 'Sigil: Lethargy', 8.8)] == pytest.approx(8.83, abs=0.05)
    assert same[('skill', 'Engorge', 10.2)] == pytest.approx(10.22, abs=0.05)


def test_two_replays_are_the_same():
    played.cache_clear()
    first = [(round(action.at, 3), action.kind, action.what) for action in played(True)]
    played.cache_clear()
    assert [(round(action.at, 3), action.kind, action.what) for action in played(True)] == first


@pytest.mark.xfail(
    strict=True,
    reason='one strike of 110 actions: at 13.67 s the game struck through the monster 740045072 (worth 32327) and '
    'the replay through 46244625 (worth 32048); the two lines are 0.9% apart and the monsters move between the '
    'frame of 13.48 s, which the game read, and that of 13.52 s, which the replay reads 20 ms later',
)
def test_every_recorded_action_is_replayed():
    found = compared()
    assert not found.missing, found.table()
    assert not found.extra, found.table()


def test_with_todays_rule_the_sweep_leaves_the_potion_and_the_fight_goes_on():
    replayed = played(False)
    assert kinds(replayed, 'sweep stops') == []
    assert kinds(replayed, 'sweep leaves')[0][2] == 'a super healing potion'
