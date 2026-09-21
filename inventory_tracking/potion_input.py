"""Focused XWayland key delivery; cooldown policy is owned by PotionsController."""

import time
from collections.abc import Callable

from .config import INPUT, InputConfig
from .focus import FocusProbe
from .keyboard import Keyboard, X11Keyboard
from .models import Actor, PotionRequest, SessionIdentity, State


class PotionInput:
    """Last-moment guards, one press/release sequence and a guaranteed release. Nothing else."""

    def __init__(
        self,
        config: InputConfig = INPUT,
        *,
        clock: Callable[[], float] = time.monotonic,
        focused: Callable[[SessionIdentity], bool] | None = None,
        keyboard: Keyboard | None = None,
    ) -> None:
        self.config = config
        self.clock = clock
        self.focused = focused if focused is not None else FocusProbe(config)
        self.keyboard = keyboard if keyboard is not None else X11Keyboard()

    def __call__(
        self, state: State, request: PotionRequest, *, max_age: float, before_send: Callable[[], None]
    ) -> bool:
        session = state.session
        player = state.health_for(Actor.PLAYER)
        if (
            session is None
            or request.actor not in Actor
            or request.item.column not in (1, 2, 3, 4)
            or request.item not in state.usable_cells(request.potion)
            or not state.fresh(self.clock(), max_age)
            or player is None
            or player[0] <= 0
        ):
            return False
        if not self.focused(session):
            return False
        column = str(request.item.column).encode()
        names = [b'Shift_L', column] if request.actor == Actor.MERC else [column]
        with self.keyboard.connect() as keys:
            if keys is None:
                return False
            codes = keys.keycodes(names)
            if not codes:
                return False
            # Never disturb keys physically held by the player; re-check focus and age right before sending.
            if keys.any_key_held() or not self.focused(session) or not state.fresh(self.clock(), max_age):
                return False
            before_send()
            try:
                for key in codes:
                    if not keys.press(key):
                        raise RuntimeError('Potion key press failed')
                keys.sync()
                time.sleep(self.config.key_hold_seconds)
            finally:
                release_failed = False
                for key in reversed(codes):
                    try:
                        if not keys.release(key):
                            release_failed = True
                    except Exception:
                        release_failed = True
                keys.sync()
                if release_failed:
                    raise RuntimeError('Potion key release failed')
            return True
