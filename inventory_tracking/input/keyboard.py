"""XTest key injection over ctypes. Libraries load once; each send opens one display connection."""

import ctypes
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from functools import cached_property
from threading import RLock
from typing import Any, Protocol


# XSetErrorHandler is process-global. Serialize our Xlib connections while a
# temporary read-only ownership error trap is active.
_X11_LOCK = RLock()
_ERROR_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
_XA_CARDINAL = 6


class KeyConnection(Protocol):
    open_ms: float

    def keycodes(self, names: Sequence[bytes]) -> list[int] | None: ...
    def any_key_held(self) -> bool: ...
    def focused_window_pid(self) -> int | None: ...
    def press(self, key: int) -> bool: ...
    def release(self, key: int) -> bool: ...
    def sync(self) -> None: ...


class Keyboard(Protocol):
    def connect(self) -> AbstractContextManager[KeyConnection | None]: ...


class X11Connection:
    def __init__(self, x11: Any, xtst: Any, display: int, open_ms: float = 0) -> None:
        self.x11 = x11
        self.xtst = xtst
        self.display = display
        self.open_ms = open_ms

    def keycodes(self, names: Sequence[bytes]) -> list[int] | None:
        keys = [self.x11.XKeysymToKeycode(self.display, self.x11.XStringToKeysym(name)) for name in names]
        return keys if all(keys) else None

    def any_key_held(self) -> bool:
        keymap = ctypes.create_string_buffer(32)
        self.x11.XQueryKeymap(self.display, keymap)
        return any(keymap.raw)

    def _window_pid(self, window: int, atom: int) -> int | None:
        actual, count, remaining = ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_ulong()
        format_bits = ctypes.c_int()
        data = ctypes.POINTER(ctypes.c_ubyte)()
        try:
            status = self.x11.XGetWindowProperty(
                self.display,
                window,
                atom,
                0,
                1,
                0,
                _XA_CARDINAL,
                ctypes.byref(actual),
                ctypes.byref(format_bits),
                ctypes.byref(count),
                ctypes.byref(remaining),
                ctypes.byref(data),
            )
            if status != 0 or actual.value != _XA_CARDINAL or format_bits.value != 32 or count.value != 1 or not data:
                return None
            # Xlib expands 32-bit properties into native longs on LP64.
            pid = ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))[0]
            return pid if pid > 0 else None
        finally:
            if data:
                self.x11.XFree(data)

    def _parent(self, window: int) -> int | None:
        root, parent = ctypes.c_ulong(), ctypes.c_ulong()
        children = ctypes.POINTER(ctypes.c_ulong)()
        count = ctypes.c_uint()
        try:
            ok = self.x11.XQueryTree(
                self.display,
                window,
                ctypes.byref(root),
                ctypes.byref(parent),
                ctypes.byref(children),
                ctypes.byref(count),
            )
            return parent.value if ok and parent.value != window else None
        finally:
            if children:
                self.x11.XFree(children)

    def _focused_owner(self) -> int | None:
        window, revert = ctypes.c_ulong(), ctypes.c_int()
        self.x11.XGetInputFocus(self.display, ctypes.byref(window), ctypes.byref(revert))
        atom = self.x11.XInternAtom(self.display, b'_NET_WM_PID', 1)
        if not atom:
            return None
        current = window.value
        for _ in range(16):
            # None and PointerRoot are special values, not client windows.
            if current in (0, 1):
                return None
            pid = self._window_pid(current, atom)
            if pid is not None:
                return pid
            parent = self._parent(current)
            if parent is None:
                return None
            current = parent
        return None

    def focused_window_pid(self) -> int | None:
        failed = False

        @_ERROR_HANDLER
        def on_error(display, event):
            nonlocal failed
            failed = True
            return 0

        # A window can disappear between XGetInputFocus and XGetWindowProperty.
        # Treat protocol errors as unknown ownership rather than letting Xlib exit.
        with _X11_LOCK:
            previous = self.x11.XSetErrorHandler(on_error)
            try:
                pid = self._focused_owner()
                self.x11.XSync(self.display, 0)
                return None if failed else pid
            finally:
                self.x11.XSetErrorHandler(previous)

    def press(self, key: int) -> bool:
        return bool(self.xtst.XTestFakeKeyEvent(self.display, key, 1, 0))

    def release(self, key: int) -> bool:
        return bool(self.xtst.XTestFakeKeyEvent(self.display, key, 0, 0))

    def sync(self) -> None:
        self.x11.XSync(self.display, 0)


class X11Keyboard:
    """Loads libX11/libXtst lazily and declares their signatures once per process."""

    def __init__(self, x11: Any = None, xtst: Any = None, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self._injected = (x11, xtst) if x11 is not None and xtst is not None else None

    @cached_property
    def libraries(self) -> tuple[Any, Any]:
        x11, xtst = self._injected or (ctypes.CDLL('libX11.so.6'), ctypes.CDLL('libXtst.so.6'))
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        x11.XStringToKeysym.restype = ctypes.c_ulong
        x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        x11.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XGetInputFocus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int)]
        x11.XGetInputFocus.restype = ctypes.c_int
        x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XGetWindowProperty.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_long,
            ctypes.c_long,
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
        ]
        x11.XGetWindowProperty.restype = ctypes.c_int
        x11.XQueryTree.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),
            ctypes.POINTER(ctypes.c_uint),
        ]
        x11.XQueryTree.restype = ctypes.c_int
        x11.XFree.argtypes = [ctypes.c_void_p]
        x11.XFree.restype = ctypes.c_int
        x11.XSetErrorHandler.argtypes = [ctypes.c_void_p]
        x11.XSetErrorHandler.restype = ctypes.c_void_p
        xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        return x11, xtst

    @contextmanager
    def connect(self) -> Iterator[X11Connection | None]:
        with _X11_LOCK:
            x11, xtst = self.libraries
            started = self.clock()
            display = x11.XOpenDisplay(None)
            if not display:
                yield None
                return
            try:
                open_ms = (self.clock() - started) * 1000
                yield X11Connection(x11, xtst, display, open_ms)
            finally:
                x11.XCloseDisplay(display)
