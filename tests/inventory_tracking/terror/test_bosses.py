"""Boss kills of one game launch: count, average time between kills, time since the last one."""

import json

from inventory_tracking.terror.bosses import BOSSES, BossTracker, usual_gap


GAME = {'pid': 7, 'start_ticks': '100'}
ANDARIEL, MEPHISTO, FALLEN = 156, 242, 19


def died(unit_id, txt_id=ANDARIEL):
    return {'event': 'died', 'unit_id': unit_id, 'txt_id': txt_id, 'area': 37}


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


def tracker(path=None, clock=None):
    return BossTracker(path, clock=clock or Clock())


def run(bosses, clock, *kills, game=GAME):
    """Each kill is (seconds later, event); a new game starts after every kill."""
    for later, event in kills:
        clock.now += later
        bosses.apply(game, [event, {'event': 'left_game'}])


def test_the_boss_ids_are_the_act_bosses_of_the_monster_table():
    # d2data monstats.json *hcIdx (2026-10-05): andariel 156, duriel 211, mephisto 242, diablo 243, baalcrab 544
    assert {BOSSES[i] for i in (156, 211, 242, 243, 544)} == {'Andariel', 'Duriel', 'Mephisto', 'Diablo', 'Baal'}


def test_a_boss_line_gives_kills_the_average_time_between_them_and_the_time_since_the_last():
    clock = Clock()
    bosses = tracker(clock=clock)

    run(bosses, clock, (0, died(5)))
    clock.now += 35
    assert bosses.lines() == ['Andariel · 1 kill · last 0:35 ago']

    run(bosses, clock, (55, died(5)), (110, died(5)))  # kills 90 s and 110 s apart
    clock.now += 500
    assert bosses.lines() == ['Andariel · 3 kills · avg 1:40 · last 8:20 ago']


def test_a_long_stop_between_two_kills_does_not_count_towards_the_average():
    clock = Clock()
    bosses = tracker(clock=clock)

    run(bosses, clock, (0, died(5)), (90, died(5)), (1800, died(5)))  # a break after the second kill
    assert bosses.lines() == ['Andariel · 3 kills · avg 1:30 · last 0:00 ago']

    run(bosses, clock, (110, died(5)), (224, died(5)))  # 224 s is under 2.5 x the usual 90-110 s: a slow run
    assert bosses.lines() == ['Andariel · 5 kills · avg 2:21 · last 0:00 ago']
    assert usual_gap([0.0, 90.0]) == 90.0


def test_a_boss_not_killed_for_a_while_is_no_longer_shown_until_its_next_kill():
    clock = Clock()
    bosses = tracker(clock=clock)
    run(bosses, clock, (0, died(5)), (90, died(5)))

    clock.now += 600
    assert bosses.lines() == ['Andariel · 2 kills · avg 1:30 · last 10:00 ago']
    clock.now += 1
    assert bosses.lines() == []  # farming something else now

    run(bosses, clock, (3600, died(5)))  # back to Andariel: the stats are still there
    assert bosses.lines() == ['Andariel · 3 kills · avg 1:30 · last 0:00 ago']

    slow = tracker(clock=clock)  # long runs: three usual gaps count as still farming
    run(slow, clock, (0, died(5)), (400, died(5)))
    clock.now += 1200
    assert slow.lines() == ['Andariel · 2 kills · avg 6:40 · last 20:00 ago']
    clock.now += 1
    assert slow.lines() == []


def test_other_monsters_do_not_count_and_a_boss_counts_once_per_game():
    clock = Clock()
    bosses = tracker(clock=clock)

    bosses.apply(GAME, [died(5, FALLEN), died(6), died(6), {'event': 'died', 'unit_id': 9, 'area': 1}])
    bosses.apply(GAME, [died(6)])

    assert bosses.lines() == ['Andariel · 1 kill · last 0:00 ago']


def test_bosses_are_listed_most_recent_first():
    clock = Clock()
    bosses = tracker(clock=clock)

    run(bosses, clock, (0, died(5)), (60, died(8, MEPHISTO)))

    assert [line.split(' · ')[0] for line in bosses.lines()] == ['Mephisto', 'Andariel']


def test_a_relaunched_game_starts_from_nothing():
    clock = Clock()
    bosses = tracker(clock=clock)
    run(bosses, clock, (0, died(5)))

    bosses.apply({'pid': 9, 'start_ticks': '500'}, [])

    assert bosses.lines() == []


def test_a_restarted_service_keeps_the_kills_of_the_game_still_running(tmp_path):
    clock = Clock()
    path = tmp_path / 'boss-kills.json'
    run(tracker(path, clock), clock, (0, died(5)), (90, died(5)))
    assert json.loads(path.read_text())['game'] == GAME

    again = tracker(path, clock)
    again.apply(GAME, [])
    assert again.lines() == ['Andariel · 2 kills · avg 1:30 · last 0:00 ago']

    other = tracker(path, clock)
    other.apply({'pid': 7, 'start_ticks': '999'}, [])  # the pid reused by a new launch
    assert other.lines() == []


def test_an_unreadable_state_file_is_ignored(tmp_path):
    path = tmp_path / 'boss-kills.json'
    path.write_text('{"game": ')
    bosses = tracker(path)

    bosses.apply(GAME, [died(5)])

    assert bosses.lines() == ['Andariel · 1 kill · last 0:00 ago']


# The Countess as first seen in Tower Cellar Level 5 (probe log): type flags 0x0a at +0x1A, super unique 6 at +0x2A.
COUNTESS_DATA = '9c8077640000000000020101000a00020201000000000000f01a0a0000000000091b11160000000000000600ffffffff'
MINION_DATA = COUNTESS_DATA[:0x34] + '10' + COUNTESS_DATA[0x36:]
CORRUPT_ROGUE, PINDLE_CLASS = 45, 440  # monstats corruptrogue3, reanimatedhorde5: one super unique each


def seen(unit_id, txt_id, data_hex):
    return {'event': 'seen', 'unit_id': unit_id, 'txt_id': txt_id, 'area': 25, 'data_hex': data_hex}


def test_pindleskin_and_the_countess_are_the_super_uniques_of_their_class():
    bosses = tracker()

    bosses.apply(
        GAME,
        [
            seen(3, CORRUPT_ROGUE, COUNTESS_DATA),
            seen(4, CORRUPT_ROGUE, MINION_DATA),
            seen(5, PINDLE_CLASS, COUNTESS_DATA),
            seen(6, PINDLE_CLASS, None),  # unreadable monster data: not known to be Pindleskin
        ],
    )
    bosses.apply(GAME, [died(4, CORRUPT_ROGUE), died(6, PINDLE_CLASS), died(3, CORRUPT_ROGUE), died(5, PINDLE_CLASS)])

    assert sorted(line.split(' · ')[:2] for line in bosses.lines()) == [
        ['Countess', '1 kill'],
        ['Pindleskin', '1 kill'],
    ]

    bosses.apply(GAME, [{'event': 'left_game'}, died(3, CORRUPT_ROGUE)])  # the next game's unit 3 is someone else
    assert sorted(line.split(' · ')[:2] for line in bosses.lines()) == [
        ['Countess', '1 kill'],
        ['Pindleskin', '1 kill'],
    ]
