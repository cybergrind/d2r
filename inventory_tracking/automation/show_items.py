"""Turn the game's Show Items toggle (item labels on the ground) on once per game.

The OSD reads the toggle's byte (tracking/show_items.py, `SHOW_ITEMS_RVA`); a new game starts
with it off (captures 2026-09-21). Once the game has settled, an off byte gets one press of the
Show Items key, retried a few times if the byte stays off. The key is the character's own
binding from its key file (the game keeps them per character; user, 2026-10-05: usually Z)
unless the config names keys. Once the byte is seen on, the game is left alone: turning labels
off later is the player's choice (user, 2026-10-05).
"""

import time
from collections.abc import Callable
from functools import partial

from inventory_tracking.common import LOG
from inventory_tracking.config import ShowItemsConfig
from inventory_tracking.input import InputError, Refused, Target
from inventory_tracking.input.keybindings import show_items_key
from inventory_tracking.models import State


class ShowItemsController:
    def __init__(
        self,
        config: ShowItemsConfig,
        delivery,
        *,
        clock: Callable[[], float] = time.monotonic,
        lookup: Callable[[str], str | None] | None = None,
    ) -> None:
        self.config = config
        self.delivery = delivery
        self.clock = clock
        self.lookup = lookup or partial(show_items_key, config.saved_games)
        self.keys: tuple[str, ...] | None = None
        self.game: tuple[int, str, int] | None = None
        self.entered = 0.0
        self.done = False
        self.attempts = 0
        self.last_press: float | None = None

    def step(self, state: State) -> None:
        if not self.config.enabled or state.session is None:
            return
        now = self.clock()
        if state.session.core != self.game:
            self.game, self.entered, self.done, self.attempts, self.last_press = state.session.core, now, False, 0, None
            self.keys = None
        observed = state.show_items
        if self.done or not observed.fresh(now, self.config.sample_max_age):
            return
        if observed.value:
            self.done = True
            return
        if now - self.entered < self.config.settle_seconds:
            return
        if self.last_press is not None and now - self.last_press < self.config.retry_seconds:
            return
        if self.attempts >= self.config.max_attempts:
            LOG.info('Show Items still off after %s presses; leaving it to the player', self.attempts)
            self.done = True
            return
        keys = self._keys(state)
        if not keys:
            self.done = True
            return
        self._press(state, now, keys)

    def _keys(self, state: State) -> tuple[str, ...]:
        if self.config.key_names:
            return self.config.key_names
        if self.keys is None:
            key = self.lookup(state.player_name) if state.player_name else None
            self.keys = (key,) if key else ()
            if not key:
                LOG.info('Show Items is off, but %s has no pressable Show Items key; not pressing', state.player_name)
        return self.keys

    def _press(self, state: State, now: float, keys: tuple[str, ...]) -> None:
        assert state.session is not None
        try:
            with self.delivery.attempt_keys(
                Target(state.session, state.sampled_at, self.config.sample_max_age), keys
            ) as attempt:
                if attempt.refusal is not None:
                    return  # not focused, a key held, ...: no press, try on a later pass
                self.attempts += 1
                self.last_press = now
                attempt.send()
                LOG.info('Show Items was off: pressed %s', '+'.join(keys))
        except Refused:
            return
        except InputError:
            LOG.exception('Show Items: key delivery failed; not trying again in this game')
            self.done = True
