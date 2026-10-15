import random
from collections.abc import Sequence

import pytest

from inventory_tracking.macros.actuator import Abort, Actuator
from inventory_tracking.macros.timing import Pace
from tests.inventory_tracking.macros.fakes import Game, world


class FakeKeys:
    """Records every press and release of keys and mouse buttons in `events`; `reported` is what
    `held_keys` says is physically down, as the X connection would."""

    def __init__(self) -> None:
        self.open_ms = 0.0
        self.events: list[tuple[str, int]] = []
        self.codes: dict[str, int] = {}
        self.reported: set[int] = set()

    def keycodes(self, names: Sequence[bytes]) -> list[int]:
        return [self.codes.setdefault(name.decode(), 100 + len(self.codes)) for name in names]

    def press(self, key: int) -> bool:
        self.events.append(('press', key))
        return True

    def release(self, key: int) -> bool:
        self.events.append(('release', key))
        return True

    def button(self, button: int, down: bool) -> bool:
        self.events.append(('button-down' if down else 'button-up', button))
        return True

    def sync(self) -> None:
        pass

    def any_key_held(self) -> bool:
        return bool(self.reported)

    def held_keys(self) -> frozenset[int]:
        return frozenset(self.reported)

    def modifier_keys(self) -> frozenset[int]:
        return frozenset()

    def focused_window_pid(self) -> int | None:
        return 1

    def focused_window_rect(self) -> tuple[int, int, int, int] | None:
        return None

    def pointer(self) -> tuple[int, int]:
        return (0, 0)

    def pointer_state(self) -> tuple[int, int, int]:
        return (0, 0, 0)

    def move_pointer(self, x: int, y: int) -> bool:
        return True


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


def test_a_run_asked_to_stop_makes_no_further_input():
    # Tower Cellar 1, 21:26:46 on 2026-10-11: attack mode pressed a strike 160 ms after the teleport
    # step's request, and the step waited for the strike's cast to end before its own key.
    import threading

    from inventory_tracking.macros.actuator import Cancelled

    actuator, keys, _ = make()
    cancelled = actuator.cancelled = threading.Event()
    code = keys.keycodes([b'7'])[0]

    def stop_then_again(again):
        cancelled.set()
        again()

    with pytest.raises(Cancelled), actuator.hold('7') as again:
        stop_then_again(again)
    assert keys.events == [('press', code), ('release', code)]
    with pytest.raises(Cancelled):
        actuator.tap('7')
    assert len(keys.events) == 2


def test_the_pointer_checks_abort_is_noted_with_what_it_compared():
    # rca/2026-10-13/run-2110-findings.md, moment 3: the take shows each `the mouse was moved` with its numbers.
    actuator, _, _ = make()
    noted = []
    actuator.noted = lambda kind, **fields: noted.append((kind, fields))
    actuator.left_at = (30, 2)  # the fake pointer stays at (0, 0)
    with pytest.raises(Abort, match='the mouse was moved'):
        actuator.guard()
    assert noted == [('pointer_check', {'left_at': [30, 2], 'pointer': [0, 0], 'drift': 30, 'limit': 4})]
    actuator.left_at = (3, 1)  # within the limit: nothing is noted
    actuator.guard()
    assert len(noted) == 1


def test_a_pointer_the_macro_left_near_its_aim_is_put_there_in_one_step():
    # A Blade Warp's next aim is put during the flight before (macros/travel.py `aim_ahead`); after the landing
    # the aim is a step away, not a path and its pause again.
    play = Game(world())
    actuator = play.run().actuator
    moves = []
    move = play.keys.move_pointer

    def counted(x, y):
        moves.append((x, y))
        return move(x, y)

    play.keys.move_pointer = counted
    actuator.aim(0.5, 0.5)
    assert len(moves) >= 3  # from afar: a path
    moves.clear()
    actuator.aim(0.52, 0.51, near=120)  # 51 px across, 14 down
    assert len(moves) == 1
    moves.clear()
    actuator.aim(0.9, 0.9, near=120)
    assert len(moves) >= 3  # further than `near`: the path
