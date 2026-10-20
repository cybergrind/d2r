"""Buff mode's rules, pure (the player, 2026-10-19: "KP_3 - toggle attack mode, let's add double tap to cycle different
active modes (ATTACK, BUFF - where buff - we keep desired buffs active)"). The routine is macros/running/buffing.py.

The active mode is what the attack mode key turns on: ATTACK or BUFF, a double press cycling them (`next_active`). Buff
mode keeps the build's upkeep rows up (macros/buffs.py, macros/cta.py) while the player plays by hand: no strike, no
move, nothing in town or with a panel open (`held_back`), a cast only once the hand has rested REST s (`Rest`), and a
weapon swap only with no hostile within SWAP_CLEAR (`castable`).
"""

import math
from dataclasses import dataclass

from inventory_tracking.combat.policy import RUN_MODES
from inventory_tracking.game.records import Monster, World
from inventory_tracking.macros.actuator import POINTER_DRIFT
from inventory_tracking.macros.build import Buff
from inventory_tracking.macros.cta import ROWS as CTA_ROWS
from inventory_tracking.macros.goals import CLEAR_WAY
from inventory_tracking.macros.pursuit import SETTLE
from inventory_tracking.macros.routines import ACTING
from inventory_tracking.macros.running.base import ATTACK, BUFF


ACTIVE = (ATTACK, BUFF)  # the double press's cycle
WORDS = {ATTACK: 'ATT', BUFF: 'BUFF'}  # the HUD's mode word (runner.py `run_badge`)
NAMES = {ATTACK: 'ATTACK', BUFF: 'BUFF'}  # said by the double press, as `Pickup: GOOD`
REST = SETTLE  # seconds the hand rests before a cast, as a paused level run waits (pursuit.py SETTLE)
OWN_CAST = 1.0  # seconds the character's cast after a key of the mode's own is the mode's, not the hand's
SWAP_CLEAR = CLEAR_WAY  # units: no weapon swap with a hostile this near (the quiet of hunting/base.py QUIET_UNITS)
# Seconds before a self-ending buff ends it is cast again (buffs.py `lapsing`): no boss fight is known ahead by hand
RENEW_AHEAD = 15.0
LOOK = 0.1  # seconds between looks
OWED_SECONDS = 10.0  # a weapon set a stopped cast left in hand is swapped back within this, if still in hand


def next_active(mode: str) -> str:
    """The active mode after `mode` in the cycle."""
    return ACTIVE[(ACTIVE.index(mode) + 1) % len(ACTIVE)] if mode in ACTIVE else ACTIVE[0]


def held_back(world: World, *, pad: bool, focused: bool) -> str | None:
    """Why no buff is cast now whatever the hand does, or None."""
    player = world.player
    if not world.in_game:
        return 'not in a game'
    if player is None:
        return 'no character read'
    if player.in_town:
        return 'in town'
    if world.open_panels:
        return f'{", ".join(world.open_panels)} open'
    if pad:
        return 'controller mode'
    if not focused:
        return 'the game window is not in front'
    return None


def swaps_weapons(row: Buff) -> bool:
    """Whether the row's cast changes the weapon set in hand: a set of its own (`Buff.needs`), the Call to Arms."""
    return row.needs is not None or row in CTA_ROWS


def castable(row: Buff, world: World, foes: list[Monster]) -> bool:
    """Whether buff mode may cast `row` now: one that swaps weapons only with no hostile within SWAP_CLEAR."""
    player = world.player
    if player is None:
        return False
    if not swaps_weapons(row):
        return True
    return all(math.dist((player.x, player.y), (m.x, m.y)) > SWAP_CLEAR for m in foes)


@dataclass
class Rest:
    """The player's hand as buff mode sees it: when last at work (`at`), the pointer at the last look, and until when
    the character's cast is the mode's own (`own_until`)."""

    at: float = -math.inf
    pointer: tuple[int, int] | None = None
    own_until: float = -math.inf

    def look(self, now: float, *, pointer: tuple[int, int] | None, pressed: bool, mode: int | None) -> None:
        """One look: the pointer moved, a key or button the player holds, the character moving or casting (not by
        the mode's own key) are the hand at work."""
        moved = (
            self.pointer is not None
            and pointer is not None
            and max(abs(pointer[0] - self.pointer[0]), abs(pointer[1] - self.pointer[1])) > POINTER_DRIFT
        )
        acting = mode is not None and mode in ACTING and now > self.own_until
        if moved or pressed or acting or (mode is not None and mode in RUN_MODES):
            self.at = now
        self.pointer = pointer

    def rested(self, now: float) -> bool:
        """Whether the hand has rested REST s."""
        return now - self.at >= REST

    def cast(self, now: float, pointer: tuple[int, int] | None) -> None:
        """The mode's own cast ended at `now`, the pointer where it left it: neither is the hand's."""
        self.own_until, self.pointer = now + OWN_CAST, pointer

    def stopped(self, now: float) -> None:
        """The hand stopped a cast of the mode's: it is at work."""
        self.at = now
