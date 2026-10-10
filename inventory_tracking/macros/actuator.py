"""Keys, typed text and the pointer for a macro, behind one guarded interface.

Every action first checks that the game still has the focus, that no key is physically held
and that the pointer is where the macro left it: a player who touches the keyboard or the
mouse stops the macro (`Abort`) before the next event is sent. Pointer targets are fractions
of the game window. Keys the OSD presses on its own (`allow`) are not the player's.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from inventory_tracking.common import LOG
from inventory_tracking.input.keybindings import button_number
from inventory_tracking.input.keyboard import KeyConnection
from inventory_tracking.macros.timing import Pace


POINTER_DRIFT = 4  # pixels the pointer may differ from where the macro put it


# Pixels the pointer may be off the aim when the key goes down; further, it is aimed again. The player's
# hand works the mouse while tapping the keypad: two hops landed 18 and 23 units off their aim with the
# pointer far from it (host, 20:07 and 20:09 on 2026-10-09).
AIM_TOLERANCE = 25
AIM_TRIES = 3


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
        self.drift = POINTER_DRIFT  # a routine that runs while the player's hand is on the mouse allows more
        self.steady = True  # `aim` holds the pointer where it put it; off, it moves once and the key follows at once
        self.allowed: frozenset[int] = frozenset()  # key codes that may be down: see `allow`
        self.holding: frozenset[int] = frozenset()  # key codes this actuator holds down itself (`hold`)
        self.holding_buttons: frozenset[int] = frozenset()  # mouse buttons it holds down itself

    def allow(self, *names: str) -> None:
        """Keys another service presses by itself are not the player's. The OSD turns Show Items
        on a second or two into a new game, and its `z` stopped the first summon there (host,
        13:11 on 2026-10-07, and seven runs before it)."""
        self.allowed |= frozenset(self.keys.keycodes([name.encode() for name in names]) or ())

    def key_held(self) -> bool:
        return bool(self.keys.held_keys() - self.allowed - self.holding)

    def button_held(self, button: int) -> bool:
        """Whether the player holds mouse `button` down (the left one: a move; XQueryPointer's mask)."""
        state = self.keys.pointer_state()
        return bool(state and state[2] & (1 << (7 + button))) and button not in self.holding_buttons

    def guard(self) -> None:
        if not self.focused():
            raise Abort('the game lost the focus')
        if self.key_held():
            codes = sorted(self.keys.held_keys() - self.allowed - self.holding)
            raise Abort(f'a key was pressed (key code {", ".join(map(str, codes)) or "?"})')
        if self.left_at is not None:
            now = self.keys.pointer()
            if now is None or max(abs(now[0] - self.left_at[0]), abs(now[1] - self.left_at[1])) > self.drift:
                raise Abort('the mouse was moved')

    def wait_released(self, timeout: float = 1.5, step: float = 0.03) -> None:
        """The hotkey that started the macro is still down for a moment."""
        waited = 0.0
        while self.key_held():
            if waited >= timeout:
                raise Abort('a key is held')
            self.pace.sleep(step)
            waited += step

    def _inputs(self, names: tuple[str, ...]) -> list[tuple[bool, int]]:
        """(is a mouse button, X11 button or key code) per name, in order."""
        buttons = [button_number(name) for name in names]
        keys = [name for name, button in zip(names, buttons, strict=True) if button is None]
        codes = (self.keys.keycodes([name.encode() for name in keys]) if keys else []) or []
        if len(codes) != len(keys):
            raise Abort(f'no key code for {"+".join(names)}')
        held = iter(codes)
        return [(True, button) if button is not None else (False, next(held)) for button in buttons]

    def _press(self, inputs: list[tuple[bool, int]]) -> list[tuple[bool, int]]:
        """Press `inputs` in order; those down so far are returned when one fails."""
        pressed: list[tuple[bool, int]] = []
        for is_button, code in inputs:
            pressed.append((is_button, code))
            if not (self.keys.button(code, True) if is_button else self.keys.press(code)):
                self._release(pressed)
                raise Abort('a key press failed')
        self.keys.sync()
        return pressed

    def _release(self, pressed: list[tuple[bool, int]]) -> None:
        for is_button, code in reversed(pressed):
            if is_button:
                self.keys.button(code, False)
            else:
                self.keys.release(code)
        self.keys.sync()

    def tap(self, *names: str) -> None:
        """Press the named keys in order, hold, release in reverse. A `Button<n>` name (a skill on a
        mouse button, input/keybindings.py) is a press of that button where the pointer is."""
        inputs = self._inputs(names)
        own_buttons = frozenset(code for is_button, code in inputs if is_button)
        self.guard()
        pressed = self._press(inputs)
        self.holding_buttons |= own_buttons  # the macro's own click is not the player's (`button_held`)
        try:
            self.pace.hold()
        finally:
            self._release(pressed)
            self.holding_buttons -= own_buttons

    @contextmanager
    def hold(self, *names: str) -> Iterator[Callable[[], None]]:
        """The named keys pressed in order and kept down through the block, as the player holds the
        mouse button on a skill: the game casts it again and again at its own rate and takes the
        pointer where it is at each cast (user, 2026-10-09 night). The keys this actuator holds are
        not the player's for `guard`. Yields a callable that releases and presses again, for a game
        that casts once per press."""
        inputs = self._inputs(names)
        own = frozenset(code for is_button, code in inputs if not is_button)
        own_buttons = frozenset(code for is_button, code in inputs if is_button)
        self.guard()
        pressed = self._press(inputs)
        self.holding |= own
        self.holding_buttons |= own_buttons

        def again() -> None:
            nonlocal pressed
            self._release(pressed)
            self.pace.hold()
            pressed = self._press(inputs)

        try:
            yield again
        finally:
            self.holding -= own
            self.holding_buttons -= own_buttons
            self._release(pressed)

    def type_text(self, text: str) -> None:
        for character in text:
            self.tap(character)
            self.pace.pause('type')

    def move(self, x: float, y: float, *, scatter: tuple[int, int] = (6, 4), quick: bool = False) -> None:
        """Move the pointer to the window fraction (x, y), give or take `scatter` pixels. `quick`: a
        flick in a few steps with a short pause after, for a key the player presses again and again."""
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
        steps = max(3, min(6, distance // 150)) if quick else max(4, min(18, distance // 45))
        for point in eased_path(start, goal, steps, rng):
            if not self.keys.move_pointer(*point):
                raise Abort('a pointer move failed')
            self.keys.sync()
            self.pace.pointer_step()
        self.left_at = goal
        self.pace.pause('flick' if quick else 'aim')

    def aim(self, x: float, y: float, *, scatter: tuple[int, int] = (4, 3)) -> None:
        """A quick move to the window fraction (x, y) that holds: moved again, up to AIM_TRIES times,
        while the pointer is found more than AIM_TOLERANCE pixels off where it was put. With `steady`
        off (attack mode: the player's hand works the mouse all along) the move is made once and not
        checked: the game takes the pointer where the key finds it a moment later."""
        for attempt in range(AIM_TRIES):
            self.move(x, y, scatter=scatter, quick=True)
            if not self.steady:
                return
            now, goal = self.keys.pointer(), self.left_at
            if now is None or goal is None or max(abs(now[0] - goal[0]), abs(now[1] - goal[1])) <= AIM_TOLERANCE:
                return
            LOG.info('Macro: the pointer was found at %s, %s aimed (try %d); aiming again', now, goal, attempt + 1)
        raise Abort('the mouse is being moved')

    def click(self, *holding: str) -> None:
        """A left click where the pointer is, with the named keys held (Shift: attack in place)."""
        self.tap(*holding, 'Button1')
