"""The stand guard's hands (macros/guard.py): armed by the loop's own stop, its looks from the service loop's poll and
what it does with their verdict. A part of macros/runner.py `MacroRunner`, its methods bound there."""

import math
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.macros.guard import Act, Look
from inventory_tracking.macros.hunting.base import SIGHT, hostiles
from inventory_tracking.macros.routines import DEAD, Dead
from inventory_tracking.macros.running.base import ATTACK
from inventory_tracking.native.layout import TOWN_IDS


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


def _guard_arm(self: MacroRunner, why: object) -> None:
    """A stop of the loop's own (running/recovery.py `_stop_loop`): the guard armed, never for a death."""
    if isinstance(why, Dead) or self.closed:
        return
    if self.guard.arm(why):
        LOG.info('Macro: guard: the loop stopped itself: the life and the hostiles are watched until the player acts')


def _guard_disarm(self: MacroRunner, why: str) -> None:
    """The guard's watch over (the player's key, the loop on); its own attack mode off. Under the lock."""
    if not self.guard.armed:
        return
    if self.guard.disarm():
        _calm(self, why)
    LOG.info('Macro: guard: off (%s)', why)


def _guard_poll(self: MacroRunner, now: float, game: str | None, area: int | None) -> None:
    """The poll's look for the guard: the last read's life and mode, a hostile within SIGHT read only while it is
    armed in a level. Under the lock."""
    guard = self.guard
    if not guard.armed:
        return
    in_town = area is not None and area in TOWN_IDS
    dead = self.dead_mode in DEAD
    near = (
        not in_town and not dead and game is not None and area is not None and not self.loop.on and self.attacker_near()
    )
    look = Look(now, game, in_town, dead, self.life_seen, near, self.loop.on)
    guard_watch(self, look)


def guard_look_of(self: MacroRunner, world: World, now: float, life: tuple[int, int] | None) -> Look:
    """A `Look` from a read `world` and `life` (points, most) (the arena's looks; the poll reads its own:
    `_guard_poll`)."""
    player = world.player
    here = (player.x, player.y) if player is not None else None
    near = here is not None and any(math.dist((m.x, m.y), here) <= SIGHT for m in hostiles(world))
    return Look(
        now,
        world.game_name if world.in_game else None,
        player is not None and player.in_town,
        player is not None and player.mode in DEAD,
        life,
        near,
        self.loop.on,
    )


def guard_watch(self: MacroRunner, look: Look) -> None:
    """One look's verdict acted on (macros/guard.py `Guard.look`). Under the lock."""
    guard = self.guard
    if not guard.armed or self.closed:
        return
    if guard.fighting and not self.attack_mode:
        guard.fighting = False  # its fight ended by itself (the mode gave up): the next threat starts it again
    busy = self.working or self.attack_mode or self.buff_mode
    act = guard.look(Look(look.now, look.game, look.in_town, look.dead, look.life, look.near, look.loop_on, busy))
    if act is Act.FIGHT:
        seen = f'a hostile within {SIGHT:.0f}' if look.near else 'hit'
        LOG.info('Macro: guard: %s after the loop stopped itself: fighting back in place (%s)', seen, guard.why)
        self._end_run('the guard: the fight in place')  # no level run the stop left posted goes on
        self.attack_mode, self.attack_declined = True, False
        self._say('Guard: fighting back')
        if not self.working:
            self._start(ATTACK)
    elif act is Act.CALM:
        _calm(self, f'no hit and no hostile within {SIGHT:.0f}' if not look.in_town else 'in town')
    elif act is Act.DISARM:
        why = (
            'the character is dead: nothing is pressed'
            if look.dead
            else 'the loop is on'
            if look.loop_on
            else 'the game was left'
        )
        if guard.disarm():
            _calm(self, why)  # its run cancelled: after a death nothing more is pressed
        LOG.info('Macro: guard: off (%s)', why)


def _calm(self: MacroRunner, why: str) -> None:
    """The guard's attack mode off again (no key: the mode's run is cancelled). Under the lock."""
    if not self.attack_mode:
        return
    LOG.info("Macro: guard: the fight is over (%s): the guard's attack mode off", why)
    self.attack_mode = False
    self._end_run('the guard: the fight is over')
    if self.working and self.routine == ATTACK:
        self.cancelled.set()
