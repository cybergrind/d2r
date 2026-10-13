"""Keys, typed text and the pointer for a macro, behind one guarded interface.

Every action first checks that the game still has the focus, that no key is physically held
and that the pointer is where the macro left it: a player who touches the keyboard or the
mouse stops the macro (`Abort`) before the next event is sent. Pointer targets are fractions
of the game window. Keys the OSD presses on its own (`allow`) are not the player's.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Event

from inventory_tracking.common import LOG
from inventory_tracking.input.keybindings import button_number
from inventory_tracking.input.keyboard import KeyConnection
from inventory_tracking.macros.timing import Pace
from inventory_tracking.models import InputMode


POINTER_DRIFT = 4  # pixels the pointer may differ from where the macro put it


# Pixels the pointer may be off the aim when the key goes down; further, it is aimed again. The player's
# hand works the mouse while tapping the keypad: two hops landed 18 and 23 units off their aim with the
# pointer far from it (host, 20:07 and 20:09 on 2026-10-09).
AIM_TOLERANCE = 25
AIM_TRIES = 3


class Abort(Exception):
    """The macro stops here; the message is shown to the player."""


class Cancelled(Abort):
    """The run was asked to stop: by a request (runner.py) or, for attack mode, by a step that waited
    for the fight to be over. The runner tells this from a failure by the type, not the message."""

    def __init__(self, message: str = 'cancelled') -> None:
        super().__init__(message)


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
        self.mark: Callable[[str], None] = lambda name: None  # a moment of the press's trace (latency.py)
        self.cancelled: Event | None = None  # the run's: set, no further input is made (`guard`)
        # The game's input mode (tracking/input_mode.py), when it is read: a mouse button pressed while it reads
        # controller, or while a flip is pending, would flip the client back to mouse mode (and be thrown away),
        # so none is pressed then (`mouse_guard`). None: not read, nothing is checked.
        self.mode: Callable[[], InputMode | None] | None = None
        # The run plays by the keys and the mouse in keyboard mode (runner.py `play_by`): the game leaving that
        # mode (the player's pad touched, a flip under way) stops it, as a key of the player's does.
        self.keyboard_run = False
        # The combat take's note (record.py `Recorder.note`), set by the runner: the pointer check's abort is a
        # `pointer_check` event with what it compared (rca/2026-10-13/run-2110-findings.md, moment 3). None: none.
        self.noted: Callable[..., None] | None = None

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
        # A run asked to stop makes no further input. Attack mode looked at the request only at its
        # next read of the game, and a strike it had worked out went down after the teleport step's
        # press: that step then waited for the strike's cast to end (Tower Cellar 1, 21:26:46 on
        # 2026-10-11: the press at .687, the strike at .849, the Teleport key at 47.273).
        if self.cancelled is not None and self.cancelled.is_set():
            raise Cancelled
        if not self.focused():
            raise Abort('the game lost the focus')
        if self.key_held():
            codes = sorted(self.keys.held_keys() - self.allowed - self.holding)
            raise Abort(f'a key was pressed (key code {", ".join(map(str, codes)) or "?"})')
        if self.keyboard_run and self.mode is not None:
            mode = self.mode()
            if mode is not None and (mode.controller or mode.pending):
                raise Abort('the game left keyboard mode (a pad was touched)')
        if self.left_at is not None:
            now = self.keys.pointer()
            if now is None or max(abs(now[0] - self.left_at[0]), abs(now[1] - self.left_at[1])) > self.drift:
                if self.noted is not None:
                    off = None if now is None else max(abs(now[0] - self.left_at[0]), abs(now[1] - self.left_at[1]))
                    self.noted(
                        'pointer_check',
                        left_at=list(self.left_at),
                        pointer=list(now) if now is not None else None,
                        drift=off,
                        limit=self.drift,
                    )
                raise Abort('the mouse was moved')

    def mouse_guard(self, inputs: list[tuple[bool, int]]) -> None:
        """No mouse button while the game is in controller mode or switching (rca/2026-10-13/controller-mode.md:
        a click flips it back and is thrown away). The pad's acts (macros/pad.py) are the way in controller mode."""
        if self.mode is None or not any(is_button for is_button, _ in inputs):
            return
        mode = self.mode()
        if mode is not None and (mode.controller or mode.pending):
            raise Abort('the game is in controller mode: a click would switch it back')

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
        self.mark('first_key')
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
        self.mouse_guard(inputs)
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
        that casts once per press; it leaves the keys up when the left mouse button is down by then."""
        inputs = self._inputs(names)
        own = frozenset(code for is_button, code in inputs if not is_button)
        own_buttons = frozenset(code for is_button, code in inputs if is_button)
        self.guard()
        self.mouse_guard(inputs)
        pressed = self._press(inputs)
        self.holding |= own
        self.holding_buttons |= own_buttons

        def release() -> None:
            """Let the keys go; `again` presses them anew. For a cast of the macro's own under a held
            strike: held, the character is free only for an instant between two casts."""
            nonlocal pressed
            released, pressed = pressed, []
            self._release(released)

        def again() -> None:
            nonlocal pressed
            released, pressed = pressed, []
            self._release(released)
            if self.cancelled is not None and self.cancelled.is_set():
                raise Cancelled  # nothing is pressed again for a run asked to stop
            self.pace.hold()
            if not self.focused():
                raise Abort('the game lost the focus')  # nothing is pressed into another window
            if self.button_held(1):
                # The player's click came down between the release and the press: no press over it
                # (review.md, finding 7; the caller's next look at the button yields to the click).
                return
            self.mouse_guard(inputs)
            pressed = self._press(inputs)

        again.release = release  # type: ignore[attr-defined]
        try:
            yield again
        finally:
            self.holding -= own
            self.holding_buttons -= own_buttons
            self._release(pressed)

    @contextmanager
    def held_act(self, drift: int = POINTER_DRIFT) -> Iterator[None]:
        """One act of the loop's own made as a step makes it: the pointer held where it is put (`steady`) and
        guarded at `drift` pixels, with the guard's mark (`left_at`) re-based to where the pointer is as the act
        begins. A hand that carries the pointer off during the act still stops it (I7); a hand that moved it
        before the act and let go does not (rca/2026-10-13/run-2110-findings.md moments M2b, M3: the mark was the
        macro's last aim, seconds old, and every priced move after the player's hand aborted "the mouse was
        moved" before any input, 8.3 and 9.3 s). The drift and steadiness the run had are put back after."""
        drift_was, steady_was = self.drift, self.steady
        self.drift, self.steady = drift, True
        now = self.keys.pointer()
        if now is not None:
            self.left_at = now
        try:
            yield
        finally:
            self.drift, self.steady = drift_was, steady_was

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
        self.mark('first_move')
        for point in eased_path(start, goal, steps, rng):
            if not self.keys.move_pointer(*point):
                raise Abort('a pointer move failed')
            self.keys.sync()
            self.pace.pointer_step()
        self.left_at = goal
        self.pace.pause('flick' if quick else 'aim')

    def aim(self, x: float, y: float, *, scatter: tuple[int, int] = (4, 3), near: int = 0) -> None:
        """A quick move to the window fraction (x, y) that holds: moved again, up to AIM_TRIES times,
        while the pointer is found more than AIM_TOLERANCE pixels off where it was put. The last try
        is a jump straight there, looked at at once: a hand sweeping the mouse carries the pointer off
        during a move's steps and the pause after it, three times in 0.4 s (host, 20:57 and 20:58 on
        2026-10-10, two seek steps stopped), and has no time to in a jump. With `steady` off (attack
        mode: the player's hand works the mouse all along) the move is made once and not checked: the
        game takes the pointer where the key finds it a moment later. `near` (pixels): a pointer the
        macro already put within that of the aim (macros/travel.py puts it on the next Blade Warp's aim
        during the flight) is corrected as `snap` does, in one step: the path and its pause were made then."""
        if near and self.steady and self.left_at is not None:
            rect, now = self.keys.focused_window_rect(), self.keys.pointer()
            put = self.left_at
            if (
                rect is not None
                and now is not None
                and max(abs(now[0] - put[0]), abs(now[1] - put[1])) <= AIM_TOLERANCE  # where the macro left it
            ):
                goal = (rect[0] + rect[2] * x, rect[1] + rect[3] * y)
                if max(abs(now[0] - goal[0]), abs(now[1] - goal[1])) <= near:
                    self.snap(x, y, scatter=scatter)
                    return
        for attempt in range(AIM_TRIES):
            if attempt == AIM_TRIES - 1 and self.steady:
                self.jump(x, y, scatter=scatter)
            else:
                self.move(x, y, scatter=scatter, quick=True)
            if not self.steady:
                return
            now, goal = self.keys.pointer(), self.left_at
            if now is None or goal is None or max(abs(now[0] - goal[0]), abs(now[1] - goal[1])) <= AIM_TOLERANCE:
                return
            LOG.info('Macro: the pointer was found at %s, %s aimed (try %d); aiming again', now, goal, attempt + 1)
        raise Abort('the mouse is being moved')

    def snap(self, x: float, y: float, *, scatter: tuple[int, int] = (4, 3)) -> None:
        """The pointer put at the window fraction (x, y) in one step and held there, for a key the
        player has just pressed: the press is the player's own, and what follows it is to come at
        once (user, 2026-10-12: human-like delays are for what the macro does by itself; the
        teleport key is to work instantly). `aim`'s path and pause took 70 to 125 ms of every hop.
        Looked at after a few milliseconds and put again when a hand has carried it off; the last
        try is looked at at once, as `aim`'s is."""
        for attempt in range(AIM_TRIES):
            self.jump(x, y, scatter=scatter)
            if attempt < AIM_TRIES - 1 or not self.steady:
                self.pace.pause('snap')
            if not self.steady:
                return
            now, goal = self.keys.pointer(), self.left_at
            if now is None or goal is None or max(abs(now[0] - goal[0]), abs(now[1] - goal[1])) <= AIM_TOLERANCE:
                return
            LOG.info('Macro: the pointer was found at %s, %s aimed (try %d); aiming again', now, goal, attempt + 1)
        raise Abort('the mouse is being moved')

    def jump(self, x: float, y: float, *, scatter: tuple[int, int] = (4, 3)) -> None:
        """Put the pointer at the window fraction (x, y) in one step, with no pause after."""
        self.guard()
        rect = self.keys.focused_window_rect()
        if rect is None:
            raise Abort('no game window or pointer position')
        rng = self.pace.rng
        goal = (
            rect[0] + round(rect[2] * x) + rng.randint(-scatter[0], scatter[0]),
            rect[1] + round(rect[3] * y) + rng.randint(-scatter[1], scatter[1]),
        )
        self.mark('first_move')
        if not self.keys.move_pointer(*goal):
            raise Abort('a pointer move failed')
        self.keys.sync()
        self.left_at = goal

    def click(self, *holding: str) -> None:
        """A left click where the pointer is, with the named keys held (Shift: attack in place)."""
        self.tap(*holding, 'Button1')
