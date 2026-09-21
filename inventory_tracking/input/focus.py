"""Compositor focus and exact process identity; X11 ownership comes from the open connection."""

import json
import os
import select
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Protocol

from ..common import LOG
from ..config import INPUT, InputConfig
from ..linux_process import identity, is_game
from ..models import SessionIdentity


class FocusProbe(Protocol):
    def __call__(self, session: SessionIdentity) -> bool: ...


@dataclass
class FocusStatus:
    app_id: str | None = None


def owns_process(pid: int | None, session: SessionIdentity) -> bool:
    try:
        return (
            pid == session.process_id
            and is_game(pid)
            and identity(pid) == {'pid': pid, 'start_ticks': session.process_start}
        )
    except OSError, ValueError:
        return False


class NiriFocusProbe:
    """The compositor guard remains necessary when a native Wayland window takes focus."""

    def __init__(self, config: InputConfig = INPUT) -> None:
        self.config = config
        self.status = FocusStatus()

    def _query(self, *command: str) -> str:
        return subprocess.check_output(command, timeout=self.config.focus_timeout, text=True)

    def __call__(self, session: SessionIdentity) -> bool:
        self.status = FocusStatus()
        try:
            window = json.loads(self._query('niri', 'msg', '--json', 'focused-window'))
            self.status.app_id = window.get('app_id') if isinstance(window, dict) else None
            return self.status.app_id == self.config.game_app_id
        except OSError, ValueError, subprocess.SubprocessError:
            return False


# Known events outside the windows/focus state. Missing fields or new event types
# force a reconnect/fallback rather than retaining a possibly obsolete interpretation.
_OTHER_EVENTS = {
    'WorkspacesChanged': 'workspaces',
    'WorkspaceUrgencyChanged': 'id urgent',
    'WorkspaceActivated': 'id focused',
    'WorkspaceActiveWindowChanged': 'workspace_id active_window_id',
    'WindowFocusTimestampChanged': 'id focus_timestamp',
    'WindowUrgencyChanged': 'id urgent',
    'WindowLayoutsChanged': 'changes',
    'KeyboardLayoutsChanged': 'keyboard_layouts',
    'KeyboardLayoutSwitched': 'idx',
    'OverviewOpenedOrClosed': 'is_open',
    'ConfigLoaded': 'failed',
    'ScreenshotCaptured': 'path',
    'CastsChanged': 'casts',
    'CastStartedOrChanged': 'cast',
    'CastStopped': 'stream_id',
}


class StreamPipe(Protocol):
    def fileno(self) -> int: ...
    def close(self) -> None: ...


class StreamProcess(Protocol):
    @property
    def stdout(self) -> StreamPipe | None: ...

    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def wait(self, timeout: float | None = None) -> int: ...


@dataclass
class TrackerStatus(FocusStatus):
    source: str = 'fallback'
    ready: bool = False
    alive_at: float | None = None
    heartbeat_age: float | None = None
    changed_at: float | None = None
    update_ms: float | None = None
    connections: int = 0
    error: str | None = None


class _FocusState:
    def __init__(self) -> None:
        self.windows: dict[int, str | None] = {}
        self.focused: int | None = None
        self.ready = False

    @property
    def app_id(self) -> str | None:
        return self.windows.get(self.focused) if self.focused is not None else None

    @staticmethod
    def window(raw) -> tuple[int, str | None, bool]:
        if (
            not isinstance(raw, dict)
            or type(raw.get('id')) is not int
            or 'app_id' not in raw
            or not isinstance(raw['app_id'], str | None)
            or type(raw.get('is_focused')) is not bool
        ):
            raise ValueError('Invalid window state')
        return raw['id'], raw['app_id'], raw['is_focused']

    def apply(self, line: bytes) -> None:
        event = json.loads(line)
        if not isinstance(event, dict) or len(event) != 1:
            raise ValueError('Invalid event envelope')
        name, body = next(iter(event.items()))
        if not isinstance(body, dict):
            raise ValueError('Invalid event payload')
        if name == 'WindowsChanged':
            if not isinstance(body.get('windows'), list):
                raise ValueError('Invalid window snapshot')
            windows = [self.window(raw) for raw in body['windows']]
            focused = [wid for wid, _, active in windows if active]
            if len(focused) > 1 or len({wid for wid, _, _ in windows}) != len(windows):
                raise ValueError('Ambiguous window snapshot')
            self.windows = {wid: app for wid, app, _ in windows}
            self.focused = focused[0] if focused else None
            # Niri's full snapshot includes is_focused; there is no separate
            # initial WindowFocusChanged event in its replication contract.
            self.ready = True
        elif name == 'WindowOpenedOrChanged':
            wid, app, active = self.window(body.get('window'))
            self.windows[wid] = app
            if active:
                self.focused = wid
            elif self.focused == wid:
                self.focused = None
        elif name in ('WindowClosed', 'WindowFocusChanged'):
            if 'id' not in body or not (
                type(body['id']) is int or (name == 'WindowFocusChanged' and body['id'] is None)
            ):
                raise ValueError('Invalid focus/window id')
            wid = body['id']
            if self.ready and wid is not None and wid not in self.windows:
                raise ValueError('Unknown window id')
            if name == 'WindowClosed' and wid is not None:
                self.windows.pop(wid, None)
                if self.focused == wid:
                    self.focused = None
            else:
                self.focused = wid
        elif name not in _OTHER_EVENTS or not set(_OTHER_EVENTS[name].split()) <= body.keys():
            raise ValueError(f'Unknown event shape: {name}')


class FocusTracker:
    """A healthy quiet stream keeps focus valid; failed/stalled readers use the one-shot guard."""

    def __init__(
        self,
        config: InputConfig = INPUT,
        *,
        clock: Callable[[], float] = time.monotonic,
        fallback: FocusProbe | None = None,
        spawn: Callable[[], StreamProcess] | None = None,
        autostart: bool = True,
    ) -> None:
        self.config = config
        self.clock = clock
        self.fallback = fallback if fallback is not None else NiriFocusProbe(config)
        self._spawn = spawn if spawn is not None else self._start_process
        self._select: Callable[[list[int], list[int], list[int], float], tuple[list[int], list[int], list[int]]] = (
            select.select
        )
        self._stop = Event()
        self._initialized = Event()
        self._backoff: Callable[[float], bool] = self._stop.wait
        self._lock = Lock()
        self._state = _FocusState()
        self._pending = False
        self._alive_at: float | None = None
        self._changed_at: float | None = None
        self._update_ms: float | None = None
        self._connections = 0
        self._established = False
        self._error: str | None = None
        self.status = TrackerStatus()
        self._thread: Thread | None = None
        if autostart:
            self._thread = Thread(target=self._run, name='niri-focus', daemon=True)
            self._thread.start()

    @staticmethod
    def _start_process() -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            ['niri', 'msg', '--json', 'event-stream'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

    def _invalidate(self, error: str | None = None) -> None:
        with self._lock:
            self._state = _FocusState()
            self._pending = False
            self._alive_at = None
            self._error = error
            self._initialized.clear()

    def __call__(self, session: SessionIdentity) -> bool:
        with self._lock:
            age = None if self._alive_at is None else self.clock() - self._alive_at
            healthy = self._state.ready and not self._pending and age is not None and 0 <= age <= 1
            status = TrackerStatus(
                app_id=self._state.app_id,
                source='cache' if healthy else 'fallback',
                ready=self._state.ready and not self._pending,
                alive_at=self._alive_at,
                heartbeat_age=age,
                changed_at=self._changed_at,
                update_ms=self._update_ms,
                connections=self._connections,
                error=self._error,
            )
        if healthy:
            result = status.app_id == self.config.game_app_id
        else:
            result = self.fallback(session)
            observed = getattr(getattr(self.fallback, 'status', None), 'app_id', None)
            status.app_id = observed if isinstance(observed, str) else None
        self.status = status
        return result

    def wait_ready(self, timeout: float = 1) -> bool:
        return self._initialized.wait(timeout)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._invalidate('closed')

    def _consume(self, process: StreamProcess) -> None:
        if process.stdout is None:
            raise OSError('Missing event stream pipe')
        fd = process.stdout.fileno()
        os.set_blocking(fd, False)
        pending = b''
        while not self._stop.is_set():
            if process.poll() is not None:
                self._invalidate('event stream exited')
                return
            readable, _, _ = self._select([fd], [], [], 0.25)
            try:
                if readable:
                    with self._lock:
                        self._pending = True
                    # Drain the raw fd, not buffered readline: several lines may
                    # arrive in one write, or a line may be split across writes.
                    received_at = self.clock()
                    while True:
                        try:
                            chunk = os.read(fd, 65536)
                        except BlockingIOError:
                            break
                        if not chunk:
                            self._invalidate('event stream EOF')
                            return
                        pending += chunk
                        if len(pending) > 1024 * 1024:
                            raise ValueError('Oversized event stream buffer')
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            with self._lock:
                                previous = (self._state.ready, self._state.focused, self._state.app_id)
                                self._state.apply(line)
                                if previous != (self._state.ready, self._state.focused, self._state.app_id):
                                    self._changed_at = self.clock()
                                    self._update_ms = (self._changed_at - received_at) * 1000
                        if self._stop.is_set():
                            return
                with self._lock:
                    self._alive_at = self.clock()
                    self._pending = bool(pending)
                    if self._state.ready and not pending:
                        self._established = True
                        self._initialized.set()
                    else:
                        self._initialized.clear()
            except (OSError, ValueError, UnicodeError) as exc:
                self._invalidate(str(exc))
                return

    @staticmethod
    def _close_process(process: StreamProcess) -> None:
        try:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=0.5)
        finally:
            if process.stdout is not None:
                process.stdout.close()

    def _run(self) -> None:
        delay = 0.5
        while not self._stop.is_set():
            process = None
            self._established = False
            self._invalidate()
            try:
                process = self._spawn()
                with self._lock:
                    self._connections += 1
                self._consume(process)
            except Exception as exc:
                self._invalidate(str(exc))
                LOG.warning('Focus stream unavailable: %s', exc)
            finally:
                if process is not None:
                    try:
                        self._close_process(process)
                    except (OSError, subprocess.SubprocessError) as exc:
                        LOG.warning('Focus stream cleanup failed: %s', exc)
                self._invalidate(self._error)
            if self._established:
                delay = 0.5
            if self._error and not self._stop.is_set():
                LOG.warning('Focus stream disconnected: %s', self._error)
            if self._stop.is_set() or self._backoff(delay):
                break
            delay = min(delay * 2, 5)
