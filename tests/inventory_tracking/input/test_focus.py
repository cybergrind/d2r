from unittest.mock import patch

import pytest

from inventory_tracking.input.focus import NiriFocusProbe, owns_process
from inventory_tracking.models import SessionIdentity


SESSION = SessionIdentity(1, '2', 7)


@pytest.mark.parametrize('app_id', ['kitty', 'steam_app_2536520', None])
def test_niri_probe_reads_only_compositor_focus(app_id):
    import json

    with patch(
        'inventory_tracking.input.focus.subprocess.check_output', return_value=json.dumps({'app_id': app_id})
    ) as query:
        probe = NiriFocusProbe()
        assert probe(SESSION) == (app_id == 'steam_app_2536520')
        assert probe.status.app_id == app_id
    assert query.call_count == 1
    assert query.call_args.args[0] == ('niri', 'msg', '--json', 'focused-window')


@pytest.mark.parametrize(
    ('pid', 'start', 'game', 'expected'),
    [
        (1, '2', True, True),
        (2, '2', True, False),
        (1, 'different', True, False),
        (1, '2', False, False),
        (None, '2', True, False),
    ],
)
def test_owner_requires_exact_game_pid_and_start(pid, start, game, expected):
    with (
        patch('inventory_tracking.input.focus.is_game', return_value=game),
        patch('inventory_tracking.input.focus.identity', return_value={'pid': pid, 'start_ticks': start}),
    ):
        assert owns_process(pid, SESSION) == expected


def test_missing_tools_and_disappearing_process_refuse():
    with patch('inventory_tracking.input.focus.subprocess.check_output', side_effect=OSError('no niri')):
        assert not NiriFocusProbe()(SESSION)
    with (
        patch('inventory_tracking.input.focus.is_game', return_value=True),
        patch('inventory_tracking.input.focus.identity', side_effect=OSError('exited')),
    ):
        assert not owns_process(1, SESSION)


def snapshot(app_id='steam_app_2536520'):
    import json

    return (
        json.dumps(
            {
                'WindowsChanged': {
                    'windows': [
                        {'id': 1, 'app_id': app_id, 'is_focused': True},
                        {'id': 2, 'app_id': 'kitty', 'is_focused': False},
                    ]
                }
            }
        ).encode()
        + b'\n'
    )


class PipeProcess:
    def __init__(self):
        import os

        self.read_fd, write_fd = os.pipe()
        self.write_fd: int | None = write_fd
        self.stdout = os.fdopen(self.read_fd, 'rb', buffering=0)
        self.exited = False
        self.terminated = False

    def poll(self):
        return 0 if self.exited else None

    def terminate(self):
        self.terminated = True
        self.exited = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.terminate()

    def close(self):
        import os

        self.stdout.close()
        if self.write_fd is not None:
            os.close(self.write_fd)
            self.write_fd = None


def run_stream(actions, clock, fallback=None):
    import os
    from unittest.mock import Mock

    from inventory_tracking.input.focus import FocusTracker

    process = PipeProcess()
    tracker = FocusTracker(clock=clock, fallback=fallback or Mock(return_value=False), autostart=False)
    steps = iter(actions)

    def select(read, write, errors, timeout):
        assert timeout <= 0.25
        action = next(steps)
        if isinstance(action, bytes):
            if action:
                assert process.write_fd is not None
                os.write(process.write_fd, action)
            return read, [], []
        action(tracker, process)
        return [], [], []

    tracker._select = select
    try:
        tracker._consume(process)
    finally:
        process.close()
    return tracker


def test_tracker_initial_snapshot_then_minutes_of_silence_remains_focused(clock):
    from unittest.mock import Mock

    fallback = Mock(return_value=False)

    def silence(tracker, process):
        assert tracker(SESSION)
        clock.now += 0.25

    def stop(tracker, process):
        assert tracker(SESSION)
        assert tracker.status.source == 'cache'
        tracker._stop.set()

    run_stream([snapshot(), *([silence] * 1200), stop], clock, fallback)
    fallback.assert_not_called()


def test_tracker_focus_changes_and_window_metadata_updates(clock):
    def check_unfocused(tracker, process):
        assert not tracker(SESSION)
        assert tracker.status.app_id == 'kitty'

    def stop(tracker, process):
        assert tracker(SESSION)
        tracker._stop.set()

    run_stream(
        [
            snapshot(),
            b'{"WindowFocusChanged":{"id":2}}\n',
            check_unfocused,
            b'{"WindowOpenedOrChanged":{"window":{"id":2,"app_id":"steam_app_2536520","is_focused":true}}}\n',
            stop,
        ],
        clock,
    )


@pytest.mark.parametrize(
    'bad',
    [
        b'not json\n',
        b'{"UnknownEvent":{}}\n',
        b'{"WindowFocusChanged":{"id":99}}\n',
        b'{"WindowsChanged":{"windows":[{"id":1,"app_id":"game"}]}}\n',
        b'{"WindowClosed":{}}\n',
    ],
)
def test_invalid_stream_clears_cache_before_falling_back(bad, clock):
    from unittest.mock import Mock

    fallback = Mock(return_value=False)
    tracker = run_stream([snapshot(), bad], clock, fallback)
    assert not tracker(SESSION)
    assert tracker.status.source == 'fallback'
    assert not tracker.status.ready
    fallback.assert_called_once_with(SESSION)


def test_stalled_reader_falls_back_and_partial_lines_are_not_trusted(clock):
    from unittest.mock import Mock

    fallback = Mock(return_value=False)

    def stalled(tracker, process):
        clock.now += 2
        assert not tracker(SESSION)
        assert tracker.status.source == 'fallback'

    def partial(tracker, process):
        assert not tracker(SESSION)
        tracker._stop.set()

    run_stream([snapshot(), stalled, b'{"WindowFocusChanged":', partial], clock, fallback)
    assert fallback.call_count == 2


def test_eof_invalidates_snapshot(clock):
    import os

    def eof(tracker, process):
        os.close(process.write_fd)
        process.write_fd = None

    tracker = run_stream([snapshot(), eof, b''], clock)
    assert not tracker(SESSION)
    assert not tracker.status.ready


def test_daemon_reconnect_requires_new_snapshot_and_stops_child(clock):
    import os
    from unittest.mock import Mock

    from inventory_tracking.input.focus import FocusTracker

    first, second = PipeProcess(), PipeProcess()
    processes = iter([first, second])
    delays = []
    tracker = FocusTracker(
        clock=clock,
        fallback=Mock(return_value=False),
        spawn=lambda: next(processes),
        autostart=False,
    )
    selects = 0

    def select(read, write, errors, timeout):
        nonlocal selects
        selects += 1
        if selects == 1:
            assert first.write_fd is not None
            os.write(first.write_fd, snapshot())
        elif selects == 2:
            assert tracker(SESSION)
            first.exited = True
            return [], [], []
        elif selects == 3:
            assert not tracker(SESSION)
            assert second.write_fd is not None
            os.write(second.write_fd, b'{"WindowFocusChanged":{"id":1}}\n')
        elif selects == 4:
            assert not tracker(SESSION)
            assert second.write_fd is not None
            os.write(second.write_fd, snapshot())
        else:
            assert tracker(SESSION)
            tracker._stop.set()
            return [], [], []
        return read, [], []

    tracker._select = select
    tracker._backoff = lambda seconds: delays.append(seconds) or False
    try:
        tracker._run()
        assert delays == [0.5]
        assert second.terminated
        assert first.stdout.closed
        assert second.stdout.closed
    finally:
        first.close()
        second.close()


def test_start_failure_retries_with_bounded_backoff(clock):
    from unittest.mock import Mock

    from inventory_tracking.input.focus import FocusTracker

    tracker = FocusTracker(clock=clock, spawn=Mock(side_effect=OSError('no niri')), autostart=False)
    delays = []

    def backoff(seconds):
        delays.append(seconds)
        return len(delays) == 6

    tracker._backoff = backoff
    tracker._run()
    assert delays == [0.5, 1, 2, 4, 5, 5]
    assert not tracker.status.ready


def test_daemon_consumes_real_pipe_and_close_reaps_child():
    import os
    from unittest.mock import Mock

    from inventory_tracking.input.focus import FocusTracker

    process = PipeProcess()
    assert process.write_fd is not None
    os.write(process.write_fd, snapshot())
    tracker = FocusTracker(spawn=lambda: process, fallback=Mock(return_value=False))
    try:
        assert tracker.wait_ready(timeout=1)
        assert tracker(SESSION)
        assert tracker.status.source == 'cache'
    finally:
        tracker.close()
        process.close()
    assert process.terminated
    assert tracker._thread is not None
    assert not tracker._thread.is_alive()


def test_one_burst_is_fully_drained_before_cache_is_trusted(clock):
    def stop(tracker, process):
        assert not tracker(SESSION)
        assert tracker.status.app_id is None
        tracker._stop.set()

    run_stream([snapshot() + b'{"WindowFocusChanged":{"id":null}}\n', stop], clock)
