from unittest.mock import Mock, call

from inventory_tracking.keyboard import X11Keyboard


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
