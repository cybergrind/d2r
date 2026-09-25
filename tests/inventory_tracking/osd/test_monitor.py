import json
from unittest.mock import Mock

from inventory_tracking.osd.monitor import GameOutput, choose_monitor


def test_game_output_uses_window_workspace_and_follows_moves():
    query = Mock(
        side_effect=[
            json.dumps({'app_id': 'steam_app_2536520', 'workspace_id': 8}),
            json.dumps([{'id': 8, 'output': 'DP-5'}, {'id': 10, 'output': 'eDP-1'}]),
            json.dumps({'app_id': 'steam_app_2536520', 'workspace_id': 10}),
            json.dumps([{'id': 8, 'output': 'DP-5'}, {'id': 10, 'output': 'eDP-1'}]),
        ]
    )
    now = [0.0]
    output = GameOutput(query=query, clock=lambda: now[0])
    assert output() == 'DP-5'
    assert output() == 'DP-5'
    assert query.call_count == 2
    now[0] = 1
    assert output() == 'eDP-1'


def test_output_unavailable_does_not_fall_back_to_first_monitor():
    output = GameOutput(query=Mock(side_effect=OSError('disconnected')))
    monitors = Mock()
    monitors.get_n_items.return_value = 2
    monitors.get_item.side_effect = [Mock(get_connector=lambda: 'eDP-1'), Mock(get_connector=lambda: 'DP-5')]
    assert choose_monitor(monitors, None, output()) is None


def test_connector_selection_ignores_monitor_order_and_explicit_override_wins():
    laptop = Mock(get_connector=lambda: 'eDP-1')
    game = Mock(get_connector=lambda: 'DP-5')
    monitors = Mock()
    monitors.get_n_items.return_value = 2
    monitors.get_item.side_effect = [laptop, game, laptop]
    assert choose_monitor(monitors, None, 'DP-5') is game
    assert choose_monitor(monitors, 0, 'DP-5') is laptop


def test_non_game_focus_clears_cached_output():
    now = [0.0]
    query = Mock(
        side_effect=[
            json.dumps({'app_id': 'steam_app_2536520', 'workspace_id': 8}),
            json.dumps([{'id': 8, 'output': 'DP-5'}]),
            json.dumps({'app_id': 'terminal', 'workspace_id': 10}),
        ]
    )
    output = GameOutput(query=query, clock=lambda: now[0])
    assert output() == 'DP-5'
    now[0] = 1
    assert output() is None


def test_moving_card_retargets_surface_and_recomputes_size():
    from inventory_tracking.osd.monitor import place_assessment

    window, label, layer = Mock(), Mock(), Mock()
    laptop = Mock(get_geometry=lambda: Mock(width=1920, height=1080))
    game = Mock(get_geometry=lambda: Mock(width=2560, height=1440))
    place_assessment(window, label, laptop, layer, 16)
    label.set_size_request.assert_called_with(920, -1)
    place_assessment(window, label, game, layer, 16)
    layer.set_monitor.assert_called_with(window, game)
    label.set_size_request.assert_called_with(1240, -1)
    window.set_visible.assert_called_with(False)
