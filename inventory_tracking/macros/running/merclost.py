"""The service's merc look and the trip it makes due (macros/merc.py): the merc lost, or no healing potion on the belt
in a dangerous fight, a town trip at the first safe moment. A part of macros/runner.py `MacroRunner`, its methods bound
there; `poll` (running/watch.py) calls `_merc_poll` once a second."""

from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import World
from inventory_tracking.macros import merc
from inventory_tracking.native.memory import one_unit_table


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner

# A look: the world (monsters and corpses read), the belt's cells, the merc's level (None unread)
Look = tuple[World, tuple[int | None, ...] | None, int | None]


def _merc_poll(self: MacroRunner, now: float) -> bool:
    """The merc look every merc.LOOK_SECONDS while the loop is on in a kind that takes packages (loop.py
    `Kind.packaged`: the terror zone kinds, the shard acts, Lower Kurast); the trip pushed at its safe moment and the
    level run ended for it, as running/recovery.py `_field_trip` ends it. Whether a trip was pushed. The player's KP_6
    off wins: nothing is looked at with the loop off."""
    if not (merc.MERC_LOST_TRIP or merc.BELT_EMPTY_TRIP) or now - self.merc.looked_at < merc.LOOK_SECONDS:
        return False
    loop = self.loop
    if not loop.on or not loop.kind.packaged or self.closed:
        return False
    self.merc.looked_at = now
    try:
        look = self.merc_read()
    except Exception as exc:
        LOG.info('Macro: merc: the look could not be read (%s)', exc)
        return False
    if look is None:
        return False
    world, belt, level = look
    why = self.merc.see(world, belt, now, level)
    player = world.player
    if why is None or player is None or player.in_town:
        return False
    with self.lock:
        if not loop.on or loop.abandon or loop.agenda.stack or loop.done == world.game_name:
            return False  # off by the player meanwhile, a game given up or ending, a package under way
        moment = self.merc.moment(world, self.life_seen, now)
        if moment is None:
            return False
        loop.agenda.begin(loop.game_id or world.game_name)
        merc.trip(loop.agenda.push, player.area, why, moment)
        self.merc.tripped()
        self.stand_answered = now  # a stand by a valuable is answered by the trip (watch.py `stood_after_cube`)
        self.attack_mode = False
        if self.working:
            self.cancelled.set()
        return True


def _merc_read(self: MacroRunner) -> Look | None:
    """A full look of its own (a GameMemory, as `_attacker_near`): the world, the belt, the merc's level."""
    table = one_unit_table(self.source.capture)
    if table is None:
        return None
    memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
    try:
        world = memory.world()
        found = merc.owned_merc(world)
        level = memory.stats(found.stats_at).get(merc.LEVEL_STAT) if found is not None and found.stats_at else None
        return world, memory.belt(), level
    finally:
        memory.close()
