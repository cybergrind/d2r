"""Guarded key delivery, with explicit refusal and uncertain-delivery boundaries."""

import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from dataclasses import dataclass
from typing import Protocol

from inventory_tracking.config import INPUT, InputConfig
from inventory_tracking.input.bindings import keys_for
from inventory_tracking.input.focus import FocusProbe, FocusTracker, owns_process
from inventory_tracking.input.keyboard import Keyboard, KeyConnection, X11Keyboard
from inventory_tracking.models import PotionRequest, Refusal, SessionIdentity


@dataclass(frozen=True)
class Target:
    session: SessionIdentity
    sampled_at: float
    max_age: float


class Refused(Exception):
    """Clean refusal from send: no key event was attempted."""

    def __init__(self, refusal: Refusal) -> None:
        self.refusal = refusal
        super().__init__(refusal.value)


class InputError(RuntimeError):
    """Delivery is uncertain or the backend failed unexpectedly."""


class Attempt(Protocol):
    refusal: Refusal | None

    def send(self) -> float: ...


class Delivery(Protocol):
    def attempt(self, target: Target, request: PotionRequest) -> AbstractContextManager[Attempt]: ...


class _Attempt:
    def __init__(self, owner: PotionInput, target: Target, keys: KeyConnection | None, names: list[bytes]) -> None:
        self.owner = owner
        self.target = target
        self.keys = keys
        self.display_open_ms = keys.open_ms if keys is not None else None
        self.codes: list[int] = []
        self.keycodes: dict[str, int | None] = {name.decode(): None for name in names}
        self.held: bool | None = None
        self.owner_pid: int | None = None
        self.identity_match: bool | None = None
        self.refusal: Refusal | None = None
        self.active = True
        self.used = False
        if keys is None:
            self.refusal = Refusal.NO_DISPLAY
        else:
            self.codes = keys.keycodes(names) or []
            if self.codes:
                self.keycodes = dict(zip((name.decode() for name in names), self.codes, strict=True))
            self.refusal = self.guard() if self.codes else Refusal.UNKNOWN_KEY

    def guard(self) -> Refusal | None:
        focused = self.owner.focus(self.target.session)
        self.owner_pid = self.keys.focused_window_pid() if self.keys is not None else None
        self.identity_match = owns_process(self.owner_pid, self.target.session)
        if not focused or not self.identity_match:
            return Refusal.UNFOCUSED
        self.held = self.keys.any_key_held() if self.keys is not None else None
        if self.held:
            return Refusal.KEY_HELD
        age = self.owner.clock() - self.target.sampled_at
        if not 0 <= age <= self.target.max_age:
            return Refusal.STALE
        return None

    def send(self) -> float:
        if self.used or self.refusal is not None or not self.active or self.keys is None:
            raise InputError('Attempt cannot send')
        self.used = True
        try:
            refusal = self.guard()
        except Exception as exc:
            raise InputError('Input guard failed') from exc
        if refusal is not None:
            raise Refused(refusal)
        # Include an attempted press even if it raises/returns false: it may have reached X11.
        pressed: list[int] = []
        try:
            try:
                for code in self.codes:
                    pressed.append(code)
                    if not self.keys.press(code):
                        raise InputError('Potion key press failed')
                self.keys.sync()
                self.owner.sleep(self.owner.config.key_hold_seconds)
            finally:
                release_failed = False
                for code in reversed(pressed):
                    try:
                        if not self.keys.release(code):
                            release_failed = True
                    except Exception:
                        release_failed = True
                self.keys.sync()
                if release_failed:
                    raise InputError('Potion key release failed')
            return self.owner.clock()
        except Exception as exc:
            raise InputError('Potion key delivery failed') from exc


class PotionInput:
    def __init__(
        self,
        config: InputConfig = INPUT,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        focus: FocusProbe | None = None,
        keyboard: Keyboard | None = None,
    ) -> None:
        self.config = config
        self.clock = clock
        self.sleep = sleep
        self.focus = focus if focus is not None else FocusTracker(config, clock=clock)
        self._owned_tracker = self.focus if focus is None else None
        self.keyboard = keyboard if keyboard is not None else X11Keyboard()

    def close(self) -> None:
        if isinstance(self._owned_tracker, FocusTracker):
            self._owned_tracker.close()

    @contextmanager
    def attempt(self, target: Target, request: PotionRequest) -> Iterator[_Attempt]:
        stack = ExitStack()
        attempt = None
        try:
            try:
                keys = stack.enter_context(self.keyboard.connect())
                names = [name.encode() for name in keys_for(self.config, request)]
                attempt = _Attempt(self, target, keys, names)
            except Exception as exc:
                raise InputError('Input entry failed') from exc
            # Exceptions in the caller's body (especially ledger saves) must pass through unchanged.
            yield attempt
        finally:
            if attempt is not None:
                attempt.active = False
            try:
                stack.close()
            except Exception as exc:
                raise InputError('Input cleanup failed') from exc
