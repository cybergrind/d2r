"""Keys, typed text and the pointer for a macro, behind one guarded interface.

Every action first checks that the game still has the focus, that no key is physically held
and that the pointer is where the macro left it: a player who touches the keyboard or the
mouse stops the macro (`Abort`) before the next event is sent. Pointer targets are fractions
of the game window.
"""

from collections.abc import Callable

from inventory_tracking.input.keyboard import KeyConnection
from inventory_tracking.macros.timing import Pace


POINTER_DRIFT = 4  # pixels the pointer may differ from where the macro put it


class Abort(Exception):
    """The macro stops here; the message is shown to the player."""


def eased_path(start, end, steps: int, rng) -> list[tuple[int, int]]:
    """Points from `start` to `end`: slow, fast, slow, with a little sideways wobble on the way."""
    points = []
    for step in range(1, steps + 1):
        t = step / steps
        ease = t * t * (3 - 2 * t)
        wobble = 0 if step == steps else rng.uniform(-2, 2)
        points.append(
            (round(start[0] + (end[0] - start[0]) * ease + wobble), round(start[1] + (end[1] - start[1]) * ease))
        )
    return points


class Actuator:
    def __init__(self, keys: KeyConnection, focused: Callable[[], bool], pace: Pace) -> None:
        self.keys = keys
        self.focused = focused
        self.pace = pace
        self.left_at: tuple[int, int] | None = None  # where the macro last put the pointer

    def guard(self) -> None:
        if not self.focused():
            raise Abort('the game lost the focus')
        if self.keys.any_key_held():
            raise Abort('a key was pressed')
        if self.left_at is not None:
            now = self.keys.pointer()
            if now is None or max(abs(now[0] - self.left_at[0]), abs(now[1] - self.left_at[1])) > POINTER_DRIFT:
                raise Abort('the mouse was moved')

    def wait_released(self, timeout: float = 1.5, step: float = 0.03) -> None:
        """The hotkey that started the macro is still down for a moment."""
        waited = 0.0
        while self.keys.any_key_held():
            if waited >= timeout:
                raise Abort('a key is held')
            self.pace.sleep(step)
            waited += step

    def tap(self, *names: str) -> None:
        """Press the named keys in order, hold, release in reverse."""
        codes = self.keys.keycodes([name.encode() for name in names])
        if not codes:
            raise Abort(f'no key code for {"+".join(names)}')
        self.guard()
        pressed = []
        try:
            for code in codes:
                pressed.append(code)
                if not self.keys.press(code):
                    raise Abort('a key press failed')
            self.keys.sync()
            self.pace.hold()
        finally:
            for code in reversed(pressed):
                self.keys.release(code)
            self.keys.sync()

    def type_text(self, text: str) -> None:
        for character in text:
            self.tap(character)
            self.pace.pause('type')

    def move(self, x: float, y: float, *, scatter: tuple[int, int] = (6, 4)) -> None:
        """Move the pointer to the window fraction (x, y), give or take `scatter` pixels."""
        self.guard()
        rect = self.keys.focused_window_rect()
        start = self.keys.pointer()
        if rect is None or start is None:
            raise Abort('no game window or pointer position')
        rng = self.pace.rng
        goal = (
            rect[0] + round(rect[2] * x) + rng.randint(-scatter[0], scatter[0]),
            rect[1] + round(rect[3] * y) + rng.randint(-scatter[1], scatter[1]),
        )
        distance = max(abs(goal[0] - start[0]), abs(goal[1] - start[1]))
        for point in eased_path(start, goal, max(4, min(18, distance // 45)), rng):
            if not self.keys.move_pointer(*point):
                raise Abort('a pointer move failed')
            self.keys.sync()
            self.pace.pointer_step()
        self.left_at = goal
        self.pace.pause('aim')

    def click(self) -> None:
        self.guard()
        try:
            if not self.keys.button(1, True):
                raise Abort('a click failed')
            self.keys.sync()
            self.pace.hold()
        finally:
            self.keys.button(1, False)
            self.keys.sync()
