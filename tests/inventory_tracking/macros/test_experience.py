"""TZ leveling's measure, the experience (macros/experience.py; the player, 2026-10-19: "we should log experience in tz
leveling"): the reading from the stats, a level's gain once it is left, a game's gain and the rate since the loop
turned on, and the loop's hook (loop.py `Loop.look_at_experience`, `Loop.leave`)."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Loot
from inventory_tracking.macros import loop as loop_module
from inventory_tracking.macros.experience import EXPERIENCE_STAT, LEVEL_STAT, NEXT_LEVEL_AT, Ledger, Reading, reading
from inventory_tracking.macros.loop import LK, TZ, Loop
from tests.inventory_tracking.macros.fakes import Game, player, world


FORTRESS, RIVER, CHAOS = 103, 107, 108


def test_the_table_is_experience_txts_with_its_cap():
    assert (NEXT_LEVEL_AT[1], NEXT_LEVEL_AT[93], NEXT_LEVEL_AT[94], NEXT_LEVEL_AT[99]) == (
        500,
        2286478756,
        2492671933,
        3837739017,
    )
    assert list(NEXT_LEVEL_AT) == sorted(NEXT_LEVEL_AT)


def test_experience_past_two_to_the_31_is_read_unsigned():
    # The player's level 94 Warlock as the collection read it (runs/collection 20261019T184230Z: -1934888316)
    found = reading({LEVEL_STAT: 94, EXPERIENCE_STAT: -1934888316})
    assert found == Reading(2360078980, 94)
    assert found is not None
    assert found.to_next == 2492671933 - 2360078980


@pytest.mark.parametrize(
    'stats', [None, {}, {LEVEL_STAT: 94}, {EXPERIENCE_STAT: 5}, {LEVEL_STAT: 0, EXPERIENCE_STAT: 5}]
)
def test_stats_without_both_are_unread(stats):
    assert reading(stats) is None


def test_no_next_level_at_the_cap():
    assert Reading(3837739017, 99).to_next is None


def test_a_level_left_says_its_gain_and_a_town_says_none():
    ledger = Ledger()
    assert ledger.look('g1', FORTRESS, Reading(1000, 94), 0.0) == []
    assert ledger.look('g1', RIVER, Reading(1000, 94), 10.0) == []  # the town left: no line
    assert ledger.look('g1', RIVER, Reading(4000, 94), 50.0) == []  # the same level
    assert ledger.look('g1', CHAOS, Reading(6500, 94), 70.0) == ['experience: River of Flame: +5,500 in 60s (level 94)']


def test_each_tal_rashas_tomb_is_named_by_its_number_for_its_experience_an_hour():
    # The game shows "Tal Rasha's Tomb" on all seven; the player, 2026-10-20 ~14:03: "we need to utilize smaller tombs
    # too - it gives a great ext/hour rate"
    ledger = Ledger()
    ledger.look('g1', 46, Reading(1000, 94), 0.0)
    ledger.look('g1', 69, Reading(9000, 94), 90.0)
    assert ledger.look('g1', 46, Reading(19000, 94), 130.0) == [
        "experience: Tal Rasha's Tomb 4: +10,000 in 40s (level 94)"
    ]
    assert ledger.look('g1', 66, Reading(19000, 94), 140.0) == ['experience: Canyon of the Magi: +0 in 10s (level 94)']
    lines = ledger.game_over(1, Reading(25000, 94), 200.0)
    assert lines[0] == "experience: Tal Rasha's Tomb 1: +6,000 in 60s (level 94)"


def test_an_unread_look_changes_nothing():
    ledger = Ledger()
    ledger.look('g1', RIVER, Reading(1000, 94), 0.0)
    assert ledger.look('g1', CHAOS, None, 5.0) == []
    assert ledger.look('g1', CHAOS, Reading(3000, 94), 9.0) == ['experience: River of Flame: +2,000 in 9s (level 94)']


def test_a_game_says_its_gain_the_level_left_by_it_and_the_rate_since_the_loop_turned_on():
    ledger = Ledger()
    ledger.look('g1', FORTRESS, Reading(2_000_000, 94), 0.0)
    ledger.look('g1', CHAOS, Reading(2_000_000, 94), 60.0)
    assert ledger.game_over(1, Reading(3_000_000, 94), 600.0) == [
        'experience: The Chaos Sanctuary: +1,000,000 in 540s (level 94)',
        f'experience: game 1: +1,000,000 (level 94, {NEXT_LEVEL_AT[94] - 3_000_000:,} to the next), '
        '6,000,000 an hour over 1 game',
    ]
    # The next game counts from its own first look; the rate from the loop's
    ledger.look('g2', FORTRESS, Reading(3_100_000, 94), 700.0)
    ledger.look('g2', CHAOS, Reading(3_100_000, 94), 710.0)
    lines = ledger.game_over(2, Reading(5_000_000, 95), 1200.0)
    assert lines[-1].startswith('experience: game 2: +1,900,000 (level 95, up 1, ')
    assert lines[-1].endswith(', 9,000,000 an hour over 2 games')


def test_a_death_shows_the_loss():
    ledger = Ledger()
    ledger.look('g1', CHAOS, Reading(5_000_000, 94), 0.0)
    (_, line) = ledger.game_over(1, Reading(4_000_000, 94), 3600.0)
    assert line.startswith('experience: game 1: -1,000,000 (level 94')
    assert line.endswith(', -1,000,000 an hour over 1 game')


def test_a_game_ended_unread_says_so_and_counts_no_game():
    ledger = Ledger()
    ledger.look('g1', CHAOS, Reading(5_000_000, 94), 0.0)
    assert ledger.game_over(1, None, 10.0) == ['experience: game 1: unread']
    assert ledger.games == 0


# --- The loop's hook -------------------------------------------------------------------------------------------------


def stats(experience: int, level: int = 94) -> tuple[tuple[int, int], ...]:
    return ((LEVEL_STAT, level), (EXPERIENCE_STAT, experience))


def test_a_tz_game_logs_its_levels_and_its_end(monkeypatch, caplog):
    monkeypatch.setattr(loop_module, 'leave_game', lambda run: None)
    play = Game(world(RIVER))
    play.loot = Loot(stats=stats(1_000))
    loop = Loop(on=True, kind=TZ)
    run = play.run()
    with caplog.at_level(logging.INFO):
        loop.look_at_experience(run, play.world)
        play.loot = Loot(stats=stats(41_000))
        play.world = replace(play.world, player=player(CHAOS))
        loop.look_at_experience(run, play.world)
        play.loot = Loot(stats=stats(61_000))
        loop.leave(run, 'cyber32')
    said = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: experience: ')]
    assert said[0].startswith('Macro: experience: River of Flame: +40,000 in ')
    assert said[1].startswith('Macro: experience: The Chaos Sanctuary: +20,000 in ')
    assert said[2].startswith('Macro: experience: game 1: +60,000 (level 94, ')
    assert said[2].endswith(', ? an hour over 1 game')  # under a minute since the loop turned on
    assert loop.games == 1


def test_an_unread_character_never_stops_the_loop(monkeypatch, caplog):
    monkeypatch.setattr(loop_module, 'leave_game', lambda run: None)
    play = Game(world(CHAOS))
    play.loot = Loot()  # no stats read
    loop = Loop(on=True, kind=TZ)
    run = play.run()
    with caplog.at_level(logging.INFO):
        loop.look_at_experience(run, play.world)
        loop.leave(run, 'cyber32')
    assert 'Macro: experience: game 1: unread' in caplog.messages
    assert loop.games == 1


def test_other_kinds_log_no_experience(monkeypatch, caplog):
    monkeypatch.setattr(loop_module, 'leave_game', lambda run: None)
    play = Game(world(79))
    play.loot = Loot(stats=stats(1_000))
    loop = Loop(on=True, kind=LK)
    run = play.run()
    with caplog.at_level(logging.INFO):
        loop.look_at_experience(run, play.world)
        loop.leave(run, 'cyber32')
    assert not [m for m in caplog.messages if 'experience' in m]
    assert loop.experience.first is None


def test_the_loop_turned_on_again_counts_afresh():
    loop = Loop(kind=TZ)
    loop.experience.look('g1', CHAOS, Reading(5, 94), 0.0)
    loop.start()
    assert loop.experience.first is None


def test_the_games_going_rate_counts_from_its_first_reading_to_the_last():
    ledger = Ledger()
    assert ledger.game_rate() is None  # unread
    ledger.look('g1', CHAOS, Reading(1_000_000, 96), 100.0)
    ledger.look('g1', CHAOS, Reading(1_000_100, 96), 110.0)
    assert ledger.game_rate() is None  # under a minute
    ledger.look('g1', 1, Reading(1_600_000, 96), 100.0 + 360.0)
    assert ledger.game_rate() == pytest.approx(6_000_000)  # +600,000 in 6 min, the town's look too
    ledger.look('g2', CHAOS, Reading(2_000_000, 96), 1000.0)
    assert ledger.game_rate() is None  # a new game counts afresh
