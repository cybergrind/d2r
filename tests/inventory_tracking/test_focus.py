from unittest.mock import patch

from inventory_tracking.focus import FocusProbe
from inventory_tracking.models import SessionIdentity


SESSION = SessionIdentity(1, '2', 7)


def test_non_game_focus_stops_after_the_compositor_query():
    with patch('inventory_tracking.focus.subprocess.check_output', return_value='{"app_id":"kitty"}') as query:
        assert not FocusProbe()(SESSION)
    assert query.call_count == 1


def test_focus_requires_exact_pid_and_process_start():
    with (
        patch('inventory_tracking.focus.subprocess.check_output', side_effect=['{"app_id":"steam_app_2536520"}', '1']),
        patch('inventory_tracking.focus.is_game', return_value=True),
        patch('inventory_tracking.focus.identity', return_value={'pid': 1, 'start_ticks': 'different'}),
    ):
        assert not FocusProbe()(SESSION)
    with (
        patch('inventory_tracking.focus.subprocess.check_output', side_effect=['{"app_id":"steam_app_2536520"}', '2']),
        patch('inventory_tracking.focus.is_game', return_value=True),
        patch('inventory_tracking.focus.identity', return_value={'pid': 2, 'start_ticks': '2'}),
    ):
        assert not FocusProbe()(SESSION)


def test_matching_process_is_focused_and_tool_failures_are_not():
    with (
        patch('inventory_tracking.focus.subprocess.check_output', side_effect=['{"app_id":"steam_app_2536520"}', '1']),
        patch('inventory_tracking.focus.is_game', return_value=True),
        patch('inventory_tracking.focus.identity', return_value={'pid': 1, 'start_ticks': '2'}),
    ):
        assert FocusProbe()(SESSION)
    with patch('inventory_tracking.focus.subprocess.check_output', side_effect=OSError('no niri')):
        assert not FocusProbe()(SESSION)
