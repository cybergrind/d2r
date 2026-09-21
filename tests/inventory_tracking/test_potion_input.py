from unittest.mock import Mock, call, patch

import pytest

from inventory_tracking.models import Actor, BeltCell, PotionRequest, PotionType
from inventory_tracking.potion_input import PotionInput, game_is_focused


def request(actor=Actor.MERC):
    return PotionRequest(actor, PotionType.HEALING, BeltCell(3, 101))


def test_non_game_focus_never_queries_or_injects_into_game(sample):
    with patch('inventory_tracking.potion_input.subprocess.check_output', return_value='{"app_id":"kitty"}') as query:
        assert not game_is_focused(sample())
    assert query.call_count == 1


@pytest.mark.parametrize('actor', [Actor.PLAYER, Actor.MERC])
def test_key_sequence_and_reservation_before_delivery(actor, sample):
    x11, xtst = Mock(), Mock()
    x11.XOpenDisplay.return_value = 123
    x11.XKeysymToKeycode.side_effect = [50, 12] if actor == Actor.MERC else [12]
    events = []
    xtst.XTestFakeKeyEvent.side_effect = lambda *args: events.append(args) or 1
    sender = PotionInput(clock=lambda: 100)
    with (
        patch('inventory_tracking.potion_input.ctypes.CDLL', side_effect=[x11, xtst]),
        patch('inventory_tracking.potion_input.game_is_focused', return_value=True),
        patch('inventory_tracking.potion_input.time.sleep'),
    ):
        assert sender(sample(), request(actor), max_age=1, before_send=lambda: events.append('reserved'))
    assert events[0] == 'reserved'
    keys = [50, 12] if actor == Actor.MERC else [12]
    assert events[1:] == [(123, k, 1, 0) for k in keys] + [(123, k, 0, 0) for k in reversed(keys)]
    x11.XCloseDisplay.assert_called_once_with(123)


def test_failed_press_releases_both_keys_and_closes_display(sample):
    x11, xtst = Mock(), Mock()
    x11.XOpenDisplay.return_value = 123
    x11.XKeysymToKeycode.side_effect = [50, 12]
    xtst.XTestFakeKeyEvent.side_effect = [1, 0, 1, 1]
    with (
        patch('inventory_tracking.potion_input.ctypes.CDLL', side_effect=[x11, xtst]),
        patch('inventory_tracking.potion_input.game_is_focused', return_value=True),
        pytest.raises(RuntimeError, match='Potion key press failed'),
    ):
        PotionInput(clock=lambda: 100)(sample(), request(), max_age=1, before_send=Mock())
    assert xtst.XTestFakeKeyEvent.call_args_list == [
        call(123, 50, 1, 0),
        call(123, 12, 1, 0),
        call(123, 12, 0, 0),
        call(123, 50, 0, 0),
    ]
    x11.XCloseDisplay.assert_called_once_with(123)


@pytest.mark.parametrize('max_age', [0.01, 0.1])
def test_injected_freshness_prevents_input(sample, max_age):
    with patch('inventory_tracking.potion_input.ctypes.CDLL') as libraries:
        assert not PotionInput(clock=lambda: 101)(sample(), request(), max_age=max_age, before_send=Mock())
    libraries.assert_not_called()


def test_failed_release_attempts_remaining_keys_and_reports_uncertain_delivery(sample):
    x11, xtst = Mock(), Mock()
    x11.XOpenDisplay.return_value = 123
    x11.XKeysymToKeycode.side_effect = [50, 12]
    xtst.XTestFakeKeyEvent.side_effect = [1, 1, 0, 1]
    with (
        patch('inventory_tracking.potion_input.ctypes.CDLL', side_effect=[x11, xtst]),
        patch('inventory_tracking.potion_input.game_is_focused', return_value=True),
        patch('inventory_tracking.potion_input.time.sleep'),
        pytest.raises(RuntimeError, match='release'),
    ):
        PotionInput(clock=lambda: 100)(sample(), request(), max_age=1, before_send=Mock())
    assert xtst.XTestFakeKeyEvent.call_args_list[-1] == call(123, 50, 0, 0)
    x11.XCloseDisplay.assert_called_once_with(123)


@pytest.mark.parametrize('reason', ['held_key', 'focus_changed', 'sample_aged'])
def test_last_moment_checks_prevent_reservation_and_input(reason, sample):
    x11, xtst = Mock(), Mock()
    x11.XOpenDisplay.return_value = 123
    x11.XKeysymToKeycode.return_value = 12
    if reason == 'held_key':
        x11.XQueryKeymap.side_effect = lambda display, buffer: setattr(buffer, 'value', b'\x01')
    clock = Mock(side_effect=[100, 102] if reason == 'sample_aged' else [100, 100])
    reserve = Mock()
    with (
        patch('inventory_tracking.potion_input.ctypes.CDLL', side_effect=[x11, xtst]),
        patch('inventory_tracking.potion_input.game_is_focused', side_effect=[True, reason != 'focus_changed']),
    ):
        assert not PotionInput(clock=clock)(sample(), request(), max_age=1, before_send=reserve)
    reserve.assert_not_called()
    xtst.XTestFakeKeyEvent.assert_not_called()


def test_focus_requires_exact_pid_and_process_start(sample):
    with (
        patch(
            'inventory_tracking.potion_input.subprocess.check_output',
            side_effect=['{"app_id":"steam_app_2536520"}', '1'],
        ),
        patch('inventory_tracking.potion_input.is_game', return_value=True),
        patch('inventory_tracking.potion_input.identity', return_value={'pid': 1, 'start_ticks': 'different'}),
    ):
        assert not game_is_focused(sample())
