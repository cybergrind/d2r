"""XTest key injection over ctypes. Libraries load once; each send opens one display connection."""

import ctypes
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from functools import cached_property
from typing import Any, Protocol


class KeyConnection(Protocol):
    def keycodes(self, names: Sequence[bytes]) -> list[int] | None: ...
    def any_key_held(self) -> bool: ...
    def press(self, key: int) -> bool: ...
    def release(self, key: int) -> bool: ...
    def sync(self) -> None: ...


class Keyboard(Protocol):
    def connect(self) -> Any: ...  # context manager yielding KeyConnection | None


class X11Connection:
    def __init__(self, x11: Any, xtst: Any, display: int) -> None:
        self.x11 = x11
        self.xtst = xtst
        self.display = display

    def keycodes(self, names: Sequence[bytes]) -> list[int] | None:
        keys = [self.x11.XKeysymToKeycode(self.display, self.x11.XStringToKeysym(name)) for name in names]
        return keys if all(keys) else None

    def any_key_held(self) -> bool:
        keymap = ctypes.create_string_buffer(32)
        self.x11.XQueryKeymap(self.display, keymap)
        return any(keymap.raw)

    def press(self, key: int) -> bool:
        return bool(self.xtst.XTestFakeKeyEvent(self.display, key, 1, 0))

    def release(self, key: int) -> bool:
        return bool(self.xtst.XTestFakeKeyEvent(self.display, key, 0, 0))

    def sync(self) -> None:
        self.x11.XSync(self.display, 0)


class X11Keyboard:
    """Loads libX11/libXtst lazily and declares their signatures once per process."""

    def __init__(self, x11: Any = None, xtst: Any = None) -> None:
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
        xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        return x11, xtst

    @contextmanager
    def connect(self) -> Iterator[X11Connection | None]:
        x11, xtst = self.libraries
        display = x11.XOpenDisplay(None)
        if not display:
            yield None
            return
        try:
            yield X11Connection(x11, xtst, display)
        finally:
            x11.XCloseDisplay(display)
