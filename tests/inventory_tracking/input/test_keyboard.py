from unittest.mock import Mock, call

import pytest

from inventory_tracking.input.keyboard import X11Keyboard


def libraries(display=123):
    x11, xtst = Mock(), Mock()
    x11.XOpenDisplay.return_value = display
    x11.XKeysymToKeycode.side_effect = lambda display, keysym: {b'Shift_L': 50, b'3': 12}.get(keysym, 0)
    x11.XStringToKeysym.side_effect = lambda name: name
    xtst.XTestFakeKeyEvent.return_value = 1
    return x11, xtst


def test_connection_maps_calls_and_closes_the_display():
    x11, xtst = libraries()
    keyboard = X11Keyboard(x11, xtst)
    with keyboard.connect() as keys:
        assert keys is not None
        assert keys.keycodes([b'Shift_L', b'3']) == [50, 12]
        assert keys.keycodes([b'Shift_L', b'unknown']) is None
        assert keys.press(50)
        assert keys.release(50)
        keys.sync()
        assert not keys.any_key_held()
    assert xtst.XTestFakeKeyEvent.call_args_list == [call(123, 50, 1, 0), call(123, 50, 0, 0)]
    x11.XSync.assert_called_once_with(123, 0)
    x11.XCloseDisplay.assert_called_once_with(123)


def test_held_key_is_detected_from_the_keymap():
    x11, xtst = libraries()
    x11.XQueryKeymap.side_effect = lambda display, buffer: setattr(buffer, 'value', b'\x01')
    with X11Keyboard(x11, xtst).connect() as keys:
        assert keys is not None
        assert keys.any_key_held()


def test_missing_display_yields_none_without_closing():
    x11, xtst = libraries(display=None)
    with X11Keyboard(x11, xtst).connect() as keys:
        assert keys is None
    x11.XCloseDisplay.assert_not_called()


def test_library_signatures_are_declared_once_per_process():
    x11, xtst = libraries()
    keyboard = X11Keyboard(x11, xtst)
    for _ in range(2):
        with keyboard.connect():
            pass
    assert keyboard.libraries == (x11, xtst)
    assert x11.XOpenDisplay.argtypes is not None
    assert x11.XOpenDisplay.call_count == 2


def owner_libraries(*, focused=10, owners=None, parents=None, atom=99, format_bits=32):
    import ctypes

    x11, xtst = libraries()
    owners = owners or {}
    parents = parents or {}
    allocations = []

    def set_value(pointer, typ, value):
        ctypes.cast(pointer, ctypes.POINTER(typ))[0] = value

    def focus(display, window, revert):
        set_value(window, ctypes.c_ulong, focused)
        return 1

    def prop(display, window, atom, offset, length, delete, requested, actual, fmt, count, remaining, data):
        pid = owners.get(window)
        if pid is None:
            return 0
        value = (ctypes.c_ulong * 1)(pid)
        allocations.append(value)
        set_value(actual, ctypes.c_ulong, 6)
        set_value(fmt, ctypes.c_int, format_bits)
        set_value(count, ctypes.c_ulong, 1)
        set_value(data, ctypes.POINTER(ctypes.c_ubyte), ctypes.cast(value, ctypes.POINTER(ctypes.c_ubyte)))
        return 0

    def tree(display, window, root, parent, children, count):
        set_value(root, ctypes.c_ulong, 2)
        set_value(parent, ctypes.c_ulong, parents.get(window, 2))
        # Exercise freeing the allocated child list as well as the property buffer.
        value = (ctypes.c_ulong * 1)(7)
        allocations.append(value)
        set_value(children, ctypes.POINTER(ctypes.c_ulong), ctypes.cast(value, ctypes.POINTER(ctypes.c_ulong)))
        set_value(count, ctypes.c_uint, 1)
        return 1

    x11.XGetInputFocus.side_effect = focus
    x11.XInternAtom.return_value = atom
    x11.XGetWindowProperty.side_effect = prop
    x11.XQueryTree.side_effect = tree
    x11.XSetErrorHandler.return_value = None
    return x11, xtst


def test_focused_owner_walks_ancestors_and_frees_allocations():
    x11, xtst = owner_libraries(owners={20: 42}, parents={10: 20})
    with X11Keyboard(x11, xtst).connect() as keys:
        assert keys is not None
        assert keys.focused_window_pid() == 42
    assert [call.args[1] for call in x11.XGetWindowProperty.call_args_list] == [10, 20]
    assert x11.XFree.call_count == 2


@pytest.mark.parametrize(
    'kwargs',
    [
        {},
        {'owners': {10: 42}, 'format_bits': 8},
        {'atom': 0},
        {'focused': 1},
        {'focused': 0},
    ],
)
def test_no_owner_or_invalid_property_refuses(kwargs):
    x11, xtst = owner_libraries(**kwargs)
    with X11Keyboard(x11, xtst).connect() as keys:
        assert keys is not None
        assert keys.focused_window_pid() is None


def test_ancestor_walk_is_bounded_even_with_a_cycle():
    x11, xtst = owner_libraries(parents={10: 11, 11: 10})
    with X11Keyboard(x11, xtst).connect() as keys:
        assert keys is not None
        assert keys.focused_window_pid() is None
    assert x11.XQueryTree.call_count <= 16


def test_owner_protocol_error_refuses_and_restores_handler():
    x11, xtst = owner_libraries(owners={10: 42})

    def sync(display, discard):
        handler = x11.XSetErrorHandler.call_args_list[0].args[0]
        handler(display, None)

    x11.XSync.side_effect = sync
    with X11Keyboard(x11, xtst).connect() as keys:
        assert keys is not None
        assert keys.focused_window_pid() is None
    assert x11.XSetErrorHandler.call_count == 2
    assert x11.XSetErrorHandler.call_args.args == (None,)


def test_connection_closes_if_timing_fails_after_open():
    x11, xtst = libraries()
    clock = Mock(side_effect=[100, OSError('clock')])
    with pytest.raises(OSError, match='clock'), X11Keyboard(x11, xtst, clock=clock).connect():
        pass
    x11.XCloseDisplay.assert_called_once_with(123)
