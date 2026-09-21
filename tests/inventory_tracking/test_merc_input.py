"""Potion input must release keys on failures and reject unfocused games."""

import io
from unittest.mock import Mock, call, patch

import pytest

from inventory_tracking.merc_input import MercInput, game_is_focused

from .test_merc_heal import state


def test_non_game_focus_never_queries_or_injects_into_game():
    with patch('inventory_tracking.merc_input.subprocess.check_output', return_value='{"app_id":"kitty"}') as query:
        assert not game_is_focused(state())
    assert query.call_count == 1


def test_failed_potion_press_releases_both_keys_and_closes_display(tmp_path):
    sender = MercInput(tmp_path)
    x11, xtst = Mock(), Mock()
    x11.XOpenDisplay.return_value = 123
    x11.XKeysymToKeycode.side_effect = [50, 12]
    xtst.XTestFakeKeyEvent.side_effect = [1, 0, 1, 1]
    with (
        patch('inventory_tracking.merc_input.ctypes.CDLL', side_effect=[x11, xtst]),
        patch('inventory_tracking.merc_input.game_is_focused', return_value=True),
        patch('inventory_tracking.merc_input.time.monotonic', return_value=100),
        pytest.raises(RuntimeError, match='Potion key press failed'),
    ):
        sender.press(state(), 3, io.StringIO())
    assert xtst.XTestFakeKeyEvent.call_args_list == [
        call(123, 50, 1, 0),
        call(123, 12, 1, 0),
        call(123, 12, 0, 0),
        call(123, 50, 0, 0),
    ]
    x11.XCloseDisplay.assert_called_once_with(123)


def test_shared_lock_prevents_two_instances_sending_inside_three_seconds(tmp_path):
    first, second = MercInput(tmp_path), MercInput(tmp_path)

    def press(state, column, lock):
        import json

        lock.seek(0)
        lock.truncate()
        lock.write(json.dumps({'boot': first.boot_id, 'sent_at': 100}))
        lock.flush()
        return True

    with (
        patch('inventory_tracking.merc_input.game_is_focused', return_value=True),
        patch('inventory_tracking.merc_input.time.monotonic', return_value=100),
        patch.object(first, 'press', side_effect=press),
        patch.object(second, 'press') as other,
    ):
        assert first(state(), 3)
        assert not second(state(), 4)
        other.assert_not_called()


def test_player_input_does_not_press_shift(tmp_path):
    sender = MercInput(tmp_path)
    x11, xtst = Mock(), Mock()
    x11.XOpenDisplay.return_value = 123
    x11.XKeysymToKeycode.return_value = 10
    with (
        patch('inventory_tracking.merc_input.ctypes.CDLL', side_effect=[x11, xtst]),
        patch('inventory_tracking.merc_input.game_is_focused', return_value=True),
        patch('inventory_tracking.merc_input.time.monotonic', return_value=100),
        patch('inventory_tracking.merc_input.time.sleep'),
    ):
        assert sender.press(state(), 1, io.StringIO(), target='player')
    assert xtst.XTestFakeKeyEvent.call_args_list == [call(123, 10, 1, 0), call(123, 10, 0, 0)]


@pytest.mark.parametrize('column', [1, 2, 3, 4])
def test_shared_cooldown_allows_only_player_rejuvenation_after_one_second(tmp_path, column):
    import json
    from dataclasses import replace

    sender = MercInput(tmp_path)
    sender.lock_path.write_text(json.dumps({'boot': sender.boot_id, 'sent_at': 100}))
    health_column = column % 4 + 1
    sample = replace(state(101), rejuvenation_cells=((column, 103),), healing_cells=((health_column, 104),))
    with (
        patch('inventory_tracking.merc_input.game_is_focused', return_value=True),
        patch('inventory_tracking.merc_input.time.monotonic', return_value=101),
        patch.object(sender, 'press', return_value=True) as press,
    ):
        assert not sender(sample, column)
        assert not sender(sample, health_column, target='player')
        assert sender(sample, column, target='player')
    assert press.call_count == 1
