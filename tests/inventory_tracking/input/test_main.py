import json
from unittest.mock import Mock

import pytest

from inventory_tracking.input import __main__ as cli
from inventory_tracking.input.focus import FocusTracker, NiriFocusProbe
from tests.inventory_tracking.input.fakes import FakeKeyboard


@pytest.mark.parametrize('cause', ['ready', 'unfocused', 'key_held', 'no_display', 'unknown_key', 'cleanup'])
def test_check_cli_reports_each_binding_without_sending(cause, monkeypatch, capsys, tmp_path):
    keyboard = FakeKeyboard(held=cause == 'key_held', display=cause != 'no_display')
    keyboard.owner_pid = 42
    if cause == 'unknown_key':
        keyboard.keycodes = lambda names: None
    if cause == 'cleanup':
        keyboard.exit_error = OSError('close')
    probe = NiriFocusProbe()
    app_id = 'kitty' if cause == 'unfocused' else 'steam_app_2536520'
    probe._query = Mock(side_effect=lambda *cmd: json.dumps({'app_id': app_id}) if cmd[0] == 'niri' else '42')
    tracker = FocusTracker(fallback=probe, autostart=False)
    tracker.wait_ready = Mock(return_value=False)
    monkeypatch.setattr(cli, 'FocusTracker', lambda config: tracker)
    monkeypatch.setattr(cli, 'X11Keyboard', lambda: keyboard)
    monkeypatch.setattr(cli, 'find_game_processes', lambda: [42])
    monkeypatch.setattr(cli, 'identity', lambda pid: {'pid': pid, 'start_ticks': '23'})
    monkeypatch.setattr(cli, 'is_game', lambda pid: True)
    monkeypatch.setattr('inventory_tracking.input.focus.identity', cli.identity)
    monkeypatch.setattr('inventory_tracking.input.focus.is_game', cli.is_game)
    report = tmp_path / 'check.json'
    assert cli.main(['--check', '--output', str(report)]) == (0 if cause == 'ready' else 2)
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(lines) == 8
    assert {(line['actor'], line['column']) for line in lines} == {
        (actor, col) for actor in ('player', 'merc') for col in range(1, 5)
    }
    assert all(line['result'] == ('input_error' if cause == 'cleanup' else cause) for line in lines)
    if cause == 'ready':
        assert lines[6]['keycodes'] == {'Shift_L': 50, '3': 12}
        assert lines[6]['app_id'] == 'steam_app_2536520'
        assert lines[6]['owner_pid'] == 42
        assert lines[6]['identity_match'] is True
        assert lines[6]['held'] is False
        assert lines[6]['display_open_ms'] == pytest.approx(0.25)
    assert keyboard.events == []
    assert keyboard.connections == keyboard.closed == 8
    saved = json.loads(report.read_text())
    assert saved['state'] == 'complete'
    assert saved['checks'] == lines


@pytest.mark.parametrize('pids', [[], [1, 2]])
def test_check_cli_requires_one_game(pids, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'find_game_processes', lambda: pids)
    assert cli.main(['--check']) == 1
    assert 'one game process' in capsys.readouterr().err


def test_pinned_non_game_is_refused(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'is_game', lambda pid: False)
    assert cli.main(['--check', '--pid', '42']) == 1
    assert 'not a game process' in capsys.readouterr().err


def test_timed_check_records_cached_focus_changes_and_closes_tracker(monkeypatch, capsys, tmp_path, clock):
    from tests.inventory_tracking.input.test_focus import snapshot

    keyboard = FakeKeyboard()
    tracker = FocusTracker(clock=clock, autostart=False)
    tracker._state.apply(snapshot())
    tracker._alive_at = clock()
    tracker.wait_ready = Mock(return_value=True)
    close = Mock(wraps=tracker.close)
    tracker.close = close

    def advance(seconds):
        clock.now += seconds
        tracker._state.apply(b'{"WindowFocusChanged":{"id":2}}')
        tracker._alive_at = clock()

    monkeypatch.setattr(cli, 'FocusTracker', lambda config: tracker)
    monkeypatch.setattr(cli, 'X11Keyboard', lambda: keyboard)
    monkeypatch.setattr(cli, 'find_game_processes', lambda: [1])
    monkeypatch.setattr(cli, 'identity', lambda pid: {'pid': pid, 'start_ticks': '2'})
    monkeypatch.setattr(cli, 'is_game', lambda pid: True)
    monkeypatch.setattr(cli.time, 'monotonic', clock)
    monkeypatch.setattr(cli.time, 'sleep', advance)
    output = tmp_path / 'trace.json'
    code = cli.main(['--check', '--duration', '0.25', '--interval', '0.125', '--output', str(output)])
    assert code == 2
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(rows) == 24
    assert all(row['source'] == 'cache' for row in rows)
    assert all(row['result'] == 'ready' for row in rows[:8])
    assert all(row['result'] == 'unfocused' for row in rows[8:])
    assert not keyboard.events
    close.assert_called_once()
    assert json.loads(output.read_text())['state'] == 'complete'


@pytest.mark.parametrize('args', [['--duration', 'nan'], ['--duration', '-1'], ['--interval', '0']])
def test_timed_check_rejects_invalid_bounds(args):
    with pytest.raises(SystemExit) as caught:
        cli.main(['--check', *args])
    assert caught.value.code == 2
