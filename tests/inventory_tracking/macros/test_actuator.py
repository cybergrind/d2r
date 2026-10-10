import random

import pytest

from inventory_tracking.macros.actuator import Abort, Actuator
from inventory_tracking.macros.timing import Pace


class FakeKeys:
    """Records every press and release of keys and mouse buttons in `events`; `reported` is what
    `held_keys` says is physically down, as the X connection would."""

    def __init__(self):
        self.events = []
        self.codes = {}
        self.reported = set()

    def keycodes(self, names):
        return [self.codes.setdefault(name.decode(), 100 + len(self.codes)) for name in names]

    def press(self, code):
        self.events.append(('press', code))
        return True

    def release(self, code):
        self.events.append(('release', code))
        return True

    def button(self, code, down):
        self.events.append(('button-down' if down else 'button-up', code))
        return True

    def sync(self):
        pass

    def held_keys(self):
        return frozenset(self.reported)

    def pointer(self):
        return (0, 0)

    def pointer_state(self):
        return (0, 0, 0)


def press_again_after_focus_lost(state, again):
    """The player alt-tabs away, then the macro presses the key again."""
    state['focus'] = False
    again()


def make(focus=True):
    keys = FakeKeys()
    state = {'focus': focus}
    actuator = Actuator(keys, lambda: state['focus'], Pace(random.Random(1), lambda seconds: None))
    return actuator, keys, state


def test_again_with_the_focus_kept_presses_again_and_releases_at_the_end():
    # The game casts once per press, so `again` must release and press the key once more.
    actuator, keys, _ = make()
    code = keys.codes.get('7') or keys.keycodes([b'7'])[0]
    with actuator.hold('7') as again:
        again()
    assert keys.events == [('press', code), ('release', code), ('press', code), ('release', code)]


def test_again_after_the_focus_was_lost_raises_without_a_second_press():
    # Nothing may be pressed into another window: the abort comes before the second press.
    actuator, keys, state = make()
    code = keys.keycodes([b'7'])[0]
    with pytest.raises(Abort, match='focus'), actuator.hold('7') as again:
        press_again_after_focus_lost(state, again)
    assert keys.events == [('press', code), ('release', code)]


def test_leaving_the_block_after_a_caught_focus_abort_releases_nothing_more():
    # Catching the abort inside the block: the block then ends normally and must not release twice.
    actuator, keys, state = make()
    code = keys.keycodes([b'7'])[0]
    caught = []
    with actuator.hold('7') as again:
        state['focus'] = False
        try:
            again()
        except Abort as error:
            caught.append(str(error))
    assert len(caught) == 1
    assert 'focus' in caught[0]
    assert keys.events == [('press', code), ('release', code)]


def test_leaving_the_block_after_an_uncaught_focus_abort_releases_nothing_more():
    # Catching the abort outside the block: the block exits by the abort and must not release twice.
    actuator, keys, state = make()
    code = keys.keycodes([b'7'])[0]
    with pytest.raises(Abort, match='focus'), actuator.hold('7') as again:
        press_again_after_focus_lost(state, again)
    assert keys.events == [('press', code), ('release', code)]


def test_a_held_key_is_the_macros_own_not_the_players():
    # The key the macro keeps down must not stop the macro as a key the player pressed, but once the
    # block has ended and the key is still reported down, it is the player's again.
    actuator, keys, _ = make()
    code = keys.keycodes([b'7'])[0]
    with actuator.hold('7'):
        keys.reported = {code}
        assert actuator.key_held() is False
    assert actuator.key_held() is True


def test_again_with_the_focus_kept_works_for_a_mouse_button():
    # A skill on a mouse button is pressed and released the same way as a key.
    actuator, keys, _ = make()
    with actuator.hold('Button3') as again:
        again()
    assert keys.events == [
        ('button-down', 3),
        ('button-up', 3),
        ('button-down', 3),
        ('button-up', 3),
    ]
