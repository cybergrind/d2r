"""Keys, typed text and the pointer for a macro, behind one guarded interface.

Every action first checks the game's focus, that no key is held and that the pointer is where the macro left it: a
player who touches keyboard or mouse stops the macro (`Hand`) before the next event. Pointer targets are fractions of
the game window.
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from threading import Event
from typing import Literal

from inventory_tracking.common import LOG
from inventory_tracking.input.keybindings import button_number
from inventory_tracking.input.keyboard import KeyConnection
from inventory_tracking.macros.timing import Pace
from inventory_tracking.models import InputMode


POINTER_DRIFT = 4  # pixels the pointer may differ from where the macro put it


# Pixels the pointer may be off the aim when the key goes down; further, it is aimed again (the player's hand works
# the mouse while tapping the keypad)
AIM_TOLERANCE = 25
AIM_TRIES = 3


# Why a macro stopped, for the KP_6 loop's stop rules (runner.py `classify`): the player's hand, a Gheed's Fortune
# carry-one refusal, no inventory room, the watchdog's stand, a keeper no stash page takes, hit outside a fight
# (fought back or left: stops.py `first`), nothing to play (a terror zone with no excursion, games with no level run:
# macros/tzloop.py `choose`, 2026-10-19), a drop no click took (pickup.py `Missed`, 2026-10-21), anything else
# (rca/2026-10-18/arch-loop-orchestration.md Option A)
Cause = Literal[
    'hand', 'refused', 'room', 'stall', 'stash', 'beset', 'idle', 'zone', 'lobby', 'door', 'pickup', 'other'
]


class Abort(Exception):
    """The macro stops here; the message is shown to the player. `cause`: why, None told by type and message."""

    def __init__(self, *args: object, cause: Cause | None = None) -> None:
        super().__init__(*args)
        self.cause: Cause | None = cause


class Expired(Abort):
    """An act's allowed time elapsed: observe and choose again, not a failed game input."""


class Cancelled(Abort):
    """The run was asked to stop (a request, or a step waiting out attack mode's fight); not a failure."""

    def __init__(self, message: str = 'cancelled') -> None:
        super().__init__(message)


class Flipped(Abort):
    """The game's input mode changed under the run: it ends wherever caught (not retried in place,
    rca/2026-10-14/run-1904-findings.md §3.2) and the runner repeats the request in the new mode (`_guarded`)."""


class Hand(Abort):
    """The player's own input stopped the act (key, pointer, focus): not a failure of what the act tried
    (rca/2026-10-14/run-1932-findings.md §1.2.4)."""


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
        self.drift = POINTER_DRIFT  # more while the player's hand is on the mouse
        self.steady = True  # `aim` holds the pointer where it put it; off, it moves once
        self.allowed: frozenset[int] = frozenset()  # key codes that may be down (`allow`)
        self.holding: frozenset[int] = frozenset()  # key codes held by `hold`
        self.holding_buttons: frozenset[int] = frozenset()  # mouse buttons it holds down itself
        self.mark: Callable[[str], None] = lambda name: None  # a moment of the press's trace (latency.py)
        self.cancelled: Event | None = None  # the run's: set, no further input (`guard`)
        # The game's input mode (tracking/input_mode.py), None unread: no click in controller mode (`mouse_guard`)
        self.mode: Callable[[], InputMode | None] | None = None
        self.keyboard_run = False  # a keyboard-mode run (runner.py `play_by`): the game leaving that mode stops it
        # The combat take's note (record.py `Recorder.note`): the pointer check's abort as a `pointer_check` event
        self.noted: Callable[..., None] | None = None

    def allow(self, *names: str) -> None:
        """Keys another service presses by itself are not the player's (the OSD's Show Items `z`)."""
        self.allowed |= frozenset(self.keys.keycodes([name.encode() for name in names]) or ())

    def key_held(self) -> bool:
        return bool(self.keys.held_keys() - self.allowed - self.holding)

    def button_held(self, button: int) -> bool:
        """Whether the player holds mouse `button` down (the left one: a move; XQueryPointer's mask)."""
        state = self.keys.pointer_state()
        return bool(state and state[2] & (1 << (7 + button))) and button not in self.holding_buttons

    def guard(self) -> None:
        # A run asked to stop makes no further input: a strike sent after the request delays the next step's cast
        if self.cancelled is not None and self.cancelled.is_set():
            raise Cancelled
        if not self.focused():
            raise Hand('the game lost the focus')
        if self.key_held():
            codes = sorted(self.keys.held_keys() - self.allowed - self.holding)
            raise Hand(f'a key was pressed (key code {", ".join(map(str, codes)) or "?"})')
        if self.keyboard_run and self.mode is not None:
            mode = self.mode()
            if mode is not None and (mode.controller or mode.pending):
                raise Flipped('the game left keyboard mode (a pad was touched)')
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
                raise Hand('the mouse was moved')

    def mouse_guard(self, inputs: list[tuple[bool, int]]) -> None:
        """No mouse button in controller mode or a pending flip: it flips back and is thrown away
        (rca/2026-10-13/controller-mode.md); pad.py acts there."""
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
                raise Hand('a key is held')
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
        """Press the named keys in order, hold, release in reverse; `Button<n>` presses that mouse button."""
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
    def hold(self, *names: str) -> Generator[Callable[[], None]]:
        """The named keys kept down through the block, as the player holds a skill: the game recasts at its own rate
        at the pointer. Yields `again` (release and press anew; left up while the player's left button is down) with
        `again.release`. Held keys are not the player's for `guard`."""
        inputs = self._inputs(names)
        own = frozenset(code for is_button, code in inputs if not is_button)
        own_buttons = frozenset(code for is_button, code in inputs if is_button)
        self.guard()
        self.mouse_guard(inputs)
        pressed = self._press(inputs)
        self.holding |= own
        self.holding_buttons |= own_buttons

        def release() -> None:
            """Let the keys go, for a cast of the macro's own under a held strike."""
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
                raise Hand('the game lost the focus')  # nothing is pressed into another window
            if self.button_held(1):
                return  # the player's click came down between release and press: no press over it
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
    def closing(self) -> Generator[None]:
        """Input that closes a panel the run opened goes through the run's cancel; the player's hand and the focus
        still stop it (`guard`). A fight back cancelled the cube's room at 23:34:19 on 2026-10-19 with its Escape
        refused: the inventory and cube stayed open, read as the player's hand, and the loop stood 40 s beset."""
        saved, self.cancelled = self.cancelled, None
        try:
            yield
        finally:
            self.cancelled = saved

    def rebase(self) -> None:
        """The guard's mark (`left_at`) moved to the pointer: opening or closing a panel moves it by itself."""
        now = self.keys.pointer()
        if now is not None and self.left_at is not None:
            self.left_at = now

    @contextmanager
    def held_act(self, drift: int = POINTER_DRIFT) -> Generator[None]:
        """One act of the loop's own: `steady`, guarded at `drift`, the mark re-based as it begins, so a hand moving
        the pointer during the act stops it but one before it does not (rca/2026-10-13/run-2110-findings.md M2b, M3).
        The run's drift and steadiness are restored after."""
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
        """Move the pointer to the window fraction (x, y), give or take `scatter` pixels; `quick`: a few-step flick."""
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
        """A quick move to (x, y) that holds: retried up to AIM_TRIES while the pointer is over AIM_TOLERANCE off, the
        last try a `jump` (a sweeping hand cannot carry it off in a jump). `steady` off (attack mode): one move,
        unchecked. `near`: a pointer the macro already put within that many pixels is `snap`ped (travel.py pre-aims)."""
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
        raise Hand('the mouse is being moved')

    def snap(self, x: float, y: float, *, scatter: tuple[int, int] = (4, 3)) -> None:
        """The pointer put at (x, y) in one step and held, re-put when a hand carries it off, for a key the player
        just pressed (the player, 2026-10-12: human-like delays are for what the macro does by itself; the teleport
        key is to work instantly)."""
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
        raise Hand('the mouse is being moved')

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
