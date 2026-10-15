"""input/sent.py: every key, pointer move, button and pad event this process sends is told to one listener,
right after the send; with none set nothing changes, and a listener that fails never fails the input."""

import os
import struct

import pytest

from inventory_tracking.input import gamepad, sent
from inventory_tracking.input.keyboard import X11Keyboard
from tests.inventory_tracking.input.test_keyboard import libraries


@pytest.fixture
def heard():
    found = []
    before = sent.listen(lambda kind, what: found.append((kind, what)))
    yield found
    sent.listen(before)


def test_each_xtest_input_is_told_with_what_was_sent(heard):
    x11, xtst = libraries()
    xtst.XTestFakeMotionEvent.return_value = 1
    xtst.XTestFakeButtonEvent.return_value = 1
    with X11Keyboard(x11, xtst).connect() as keys:
        assert keys is not None
        assert keys.press(50)
        assert keys.release(50)
        assert keys.move_pointer(2400, 700)
        assert keys.button(1, True)
        assert keys.button(1, False)
    assert heard == [
        ('key', (50, 1)),
        ('key', (50, 0)),
        ('move', (2400, 700)),
        ('button', (1, 1)),
        ('button', (1, 0)),
    ]


def test_each_pad_event_is_told_and_the_reports_are_not(heard):
    read_end, write_end = os.pipe()
    pad = gamepad.Pad(sleep=lambda s: None, clock=lambda: 100.0, open_device=lambda: write_end)
    pad.tap_record(9, hold=0.0)
    pad.stick('left', 1.0, 0.0)
    written = os.read(read_end, 65536)
    os.close(read_end)
    os.close(write_end)
    size = struct.calcsize('llHHi')
    assert len(written) // size == len(heard) + 5  # one report after each of the five changes
    assert heard == [
        ('pad', (gamepad.EV_ABS, gamepad.ABS_Z, 255)),
        ('pad', (gamepad.EV_KEY, gamepad.BUTTONS['y'], 1)),
        ('pad', (gamepad.EV_KEY, gamepad.BUTTONS['y'], 0)),
        ('pad', (gamepad.EV_ABS, gamepad.ABS_Z, 0)),
        ('pad', (gamepad.EV_ABS, gamepad.ABS_X, 32767)),
        ('pad', (gamepad.EV_ABS, gamepad.ABS_Y, 0)),
    ]


def test_a_listener_that_fails_does_not_fail_the_input():
    x11, xtst = libraries()

    def broken(kind, what):
        raise RuntimeError('the recorder broke')

    before = sent.listen(broken)
    try:
        with X11Keyboard(x11, xtst).connect() as keys:
            assert keys is not None
            assert keys.press(50)
    finally:
        sent.listen(before)
    assert sent.listener is before
    assert xtst.XTestFakeKeyEvent.call_count == 1
