from unittest.mock import Mock, patch

import pytest

from inventory_tracking.models import State
from inventory_tracking.osd.__main__ import main


@pytest.mark.parametrize('mode', ['--demo', '--once'])
def test_observation_modes_cannot_deliver_keys(tmp_path, mode, capsys):
    reader = Mock()
    reader.latest.return_value = State(100, 1000, 1000, belt_contents=(531,) * 16)
    flags = [mode] + (['--once'] if mode == '--demo' else [])
    with (
        patch('sys.argv', ['osd', *flags, '--output', str(tmp_path)]),
        patch('inventory_tracking.osd.__main__.LiveReader', return_value=reader) as constructor,
        patch('inventory_tracking.osd.__main__.PotionInput') as sender,
    ):
        assert main() == 0
    if mode == '--demo':
        constructor.assert_not_called()
        sender.assert_not_called()
        assert capsys.readouterr().out.strip() == 'PREVIEW · juv 3 · hp 1'
    else:
        automation = constructor.call_args.kwargs['automation']
        assert all(not controller.config.enabled for controller in automation.controllers)
        automation.step(State(100, 100, 1000))
        sender.return_value.assert_not_called()


def test_cli_resolves_configuration_before_opening_window(tmp_path):
    with (
        patch(
            'sys.argv',
            ['osd', '--demo', '--font-size', '12', '--y', '-180', '--max-age', '4', '--output', str(tmp_path)],
        ),
        patch('inventory_tracking.osd.window.show', return_value=0) as show,
    ):
        assert main() == 0
    config = show.call_args.args[1]
    assert (config.font_size, config.y, config.max_age) == (12, -180, 4)
    assert show.call_args.kwargs['demo']


def test_window_demo_uses_frame_timestamp_for_freshness(tmp_path):
    import time

    with (
        patch('sys.argv', ['osd', '--demo', '--output', str(tmp_path)]),
        patch('inventory_tracking.osd.window.show', return_value=0) as show,
    ):
        assert main() == 0
    render = show.call_args.args[0]
    assert render(now=time.monotonic()) == ['juv 3', 'hp 1']
