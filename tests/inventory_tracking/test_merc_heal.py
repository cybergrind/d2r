"""Threshold, no-dead-merc input, cooldown and acknowledgement policy."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from inventory_tracking.merc_heal import MercHealController
from inventory_tracking.mercenary import Mercenary
from inventory_tracking.osd.state import State


def state(now=100, **changes):
    value = State(
        now,
        1000,
        1000,
        player_id=7,
        process_id=1,
        process_start='2',
        merc=Mercenary(99, 500, 1000, 16384, True),
        healing_cells=((3, 101), (4, 102)),
        belt_ids=(101, 102),
        gameplay_ready=True,
    )
    return replace(value, **changes)


def test_cooldown_shared_across_columns_and_acknowledgement_required():
    controller = MercHealController()
    send = Mock(return_value=True)
    controller.step(state(), 100, send)
    controller.step(state(101, belt_ids=(102,), healing_cells=((4, 102),)), 101, send)
    controller.step(state(102, belt_ids=(102,), healing_cells=((4, 102),)), 102, send)
    assert send.call_count == 1
    controller.step(state(103, belt_ids=(102,), healing_cells=((4, 102),)), 103, send)
    assert send.call_count == 2
    assert send.call_args.args[1] == 4


@pytest.mark.parametrize(
    'changes',
    [
        {'merc': None},
        {'merc': Mercenary(99, 0, 1000, 0, False)},
        {'merc': Mercenary(99, 500, 1000, 16384, False)},
        {'merc': Mercenary(99, 600, 1000, 19661, True)},
        {'gameplay_ready': False},
        {'current_raw': 0},
        {'healing_cells': ()},
        {'sampled_at': 90},
    ],
)
def test_unknown_dead_threshold_empty_or_stale_never_sends(changes):
    send = Mock()
    MercHealController().step(state(**changes), 100, send)
    send.assert_not_called()


def test_unacknowledged_potion_suspends_instead_of_repeating():
    controller = MercHealController()
    send = Mock(return_value=True)
    for now in [100, 103, 106]:
        controller.step(state(now), now, send)
    assert send.call_count == 1
    assert controller.suspended


def test_new_session_drops_pending_action_but_preserves_cooldown():
    controller = MercHealController()
    send = Mock(return_value=True)
    controller.step(state(), 100, send)
    controller.step(state(101, player_id=8), 101, send)
    assert send.call_count == 1
    controller.step(state(103, player_id=8), 103, send)
    assert send.call_count == 2


def test_invalid_sample_does_not_clear_unacknowledged_suspension():
    controller = MercHealController()
    send = Mock(return_value=True)
    controller.step(state(), 100, send)
    controller.step(state(103), 103, send)
    controller.step(State(104, reason='incomplete read'), 104, send)
    controller.step(state(106), 106, send)
    assert controller.suspended
    assert send.call_count == 1


@pytest.mark.parametrize(
    ('target', 'percent', 'column'),
    [
        ('player', 65, None),
        ('player', 64, 3),
        ('player', 40, 3),
        ('player', 39, 1),
        ('merc', 55, None),
        ('merc', 54, 3),
        ('merc', 20, 3),
        ('merc', 19, 1),
    ],
)
def test_recipient_thresholds_and_rejuvenation_priority(target, percent, column):
    sample = state(
        current_raw=percent * 100,
        maximum_raw=10000,
        merc=Mercenary(99, percent * 100, 10000, (percent * 32768 + 99) // 100, True),
        rejuvenation_cells=((1, 103),),
        belt_ids=(101, 102, 103),
    )
    send = Mock(return_value=True)
    MercHealController(target).step(sample, 100, send)
    if column is None:
        send.assert_not_called()
    else:
        assert send.call_args.args[1] == column


def test_player_rejuvenation_repeats_after_one_second_with_acknowledgement():
    controller = MercHealController('player')
    send = Mock(return_value=True)
    first = state(current_raw=300, rejuvenation_cells=((1, 103),), belt_ids=(103, 104), merc=None)
    controller.step(first, 100, send)
    next_sample = replace(first, sampled_at=100.9, rejuvenation_cells=((2, 104),), belt_ids=(104,))
    controller.step(next_sample, 100.9, send)
    assert send.call_count == 1
    controller.step(replace(next_sample, sampled_at=101), 101, send)
    assert send.call_count == 2
    assert send.call_args.args[1] == 2


def test_player_emergency_falls_back_to_health_and_never_heals_dead_player():
    send = Mock(return_value=True)
    MercHealController('player').step(state(current_raw=300, merc=None), 100, send)
    assert send.call_args.args[1] == 3
    send.reset_mock()
    MercHealController('player').step(state(current_raw=0), 100, send)
    send.assert_not_called()
