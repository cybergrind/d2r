import json
from unittest.mock import Mock, call

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
    assert output.focused
    now[0] = 1
    assert output() is None
    assert not output.focused


def test_game_window_size_is_read_with_the_output_and_cleared_without_focus():
    now = [0.0]
    query = Mock(
        side_effect=[
            json.dumps({'app_id': 'steam_app_2536520', 'workspace_id': 8, 'layout': {'window_size': [2560, 1418]}}),
            json.dumps([{'id': 8, 'output': 'DP-5'}]),
            json.dumps({'app_id': 'terminal', 'workspace_id': 8}),
        ]
    )
    output = GameOutput(query=query, clock=lambda: now[0])
    assert output() == 'DP-5'
    assert output.window_size == (2560, 1418)
    now[0] = 1
    assert output() is None
    assert output.window_size is None


def test_mark_placement_uses_window_height_units_from_the_bottom_left():
    from inventory_tracking.osd.monitor import place_mark
    from inventory_tracking.osd.widgets.repair_mark import Mark

    window, area, layer, monitor = Mock(), Mock(), Mock(), Mock()
    mark = Mark('repair', 0.542, 0.300, 0.085, '#ff3b3b', 1.2)
    assert place_mark(window, area, monitor, layer, (2560, 1418), mark) == 121
    layer.set_monitor.assert_called_with(window, monitor)
    assert layer.set_margin.call_args_list == [
        call(window, layer.Edge.LEFT, 708),
        call(window, layer.Edge.BOTTOM, 365),
    ]
    area.set_size_request.assert_called_with(121, 121)
    window.set_default_size.assert_called_with(121, 121)


def test_floating_game_position_is_kept_and_tiled_has_none():
    import json

    from inventory_tracking.osd.monitor import GameOutput

    def niri(layout):
        window = {'app_id': 'steam_app_2536520', 'workspace_id': 1, 'layout': layout}
        replies = {'focused-window': window, 'workspaces': [{'id': 1, 'output': 'DP-1'}]}
        return lambda argv, **kw: json.dumps(replies[argv[-1]])

    floating = {
        'window_size': [1600, 900],
        'tile_pos_in_workspace_view': [300.0, 118.5],
        'window_offset_in_tile': [0.0, 2.0],
    }
    output = GameOutput(query=niri(floating), clock=lambda: 0.0)
    assert output() == 'DP-1'
    assert output.window_position == (300.0, 120.5)

    tiled = {'window_size': [1920, 1182], 'tile_pos_in_workspace_view': None, 'window_offset_in_tile': [0.0, 0.0]}
    output = GameOutput(query=niri(tiled), clock=lambda: 0.0)
    output()
    assert output.window_position is None
    assert output.window_size == (1920, 1182)


def test_focused_output_is_read_from_niri_and_cached_briefly():
    from inventory_tracking.osd.monitor import FocusedOutput

    now = [0.0]
    query = Mock(side_effect=[json.dumps({'name': 'DP-5'}), json.dumps(None), OSError('gone')])
    output = FocusedOutput(query=query, clock=lambda: now[0])

    assert output() == 'DP-5'
    assert output() == 'DP-5'
    assert query.call_count == 1
    assert query.call_args.args[0] == ['niri', 'msg', '--json', 'focused-output']
    now[0] = 1
    assert output() is None  # no output focused
    now[0] = 2
    assert output() is None  # niri unreachable
