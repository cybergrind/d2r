"""The sweep: the drops attack mode goes for between fights, the steps it asks. A part of macros/hunt.py
`Hunter`, its methods bound there."""

import math
from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from inventory_tracking.combat.stance import CAMP_REACH
from inventory_tracking.common import LOG
from inventory_tracking.game.records import HEALING, REJUVENATION, VALUABLE, Monster, World, has_room
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros import lootpolicy
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunting.base import (
    FOLLOW_SECONDS,
    GATHER_CHECK,
    GATHER_CLEAR,
    GATHER_SECONDS,
    HOLD_SIGHT,
    HOLD_UNITS,
    QUIET_UNITS,
    STAND_OFF,
    SWEEP_UNITS,
    VANISH_UNITS,
    WAIT_LOG_SECONDS,
    threat,
)
from inventory_tracking.macros.pickup import choose, unshunned
from inventory_tracking.macros.travel import OWN_MOVE, Point, Step, label, step_line


if TYPE_CHECKING:
    from inventory_tracking.macros.hunt import Hunter


def leaves(self: Hunter, spot: Point, now: float) -> bool:
    """Whether a sweep step to `spot` goes further than HOLD_UNITS from the held valuable
    (user, 2026-10-11: "stay in radius, clear around to be safe")."""
    held = self.held
    if held is None or math.dist(spot, (held.x, held.y)) <= HOLD_UNITS:
        return False
    if now - self.held_logged >= 1.0:
        self.held_logged = now
        LOG.info(
            'Macro: the sweep stays by %s at (%.0f, %.0f): no step to (%.1f, %.1f), %.0f from it',
            held.label, held.x, held.y, *spot, math.dist(spot, (held.x, held.y)),
        )  # fmt: skip
    return True


def gather(self: Hunter, run: Run, here: Point, foes: Sequence[Monster] = ()) -> None:
    """Pick up on the way (user, 2026-10-11: "we should also auto-pickup items/gold"): with something
    pickup.choose takes, pause the mode for the pickup step (Cancelled) and sweep on after. A drop is
    tried GATHER_TRIES times at most, then given up: neither chosen nor stayed by."""
    now = run.clock()
    if self.pick is None or run.loot is None or not self.sweep.steps or now > self.sweep.until:
        self.held = None
        return
    if now - self.gather_looked < GATHER_CHECK:
        return
    self.gather_looked = now
    loot = unshunned(run.loot(), now)
    self.again(run, loot.drops, here)
    spent = {d.unit_id for d in loot.drops if self.drops.spent(d.unit_id)}
    for found in loot.drops:
        if found.unit_id in spent:
            self.left(found, here, self.drops.given_up(found.unit_id), 'the sweep')
    loot = replace(loot, drops=tuple(d for d in loot.drops if d.unit_id not in spent))
    plan = choose(loot, here)
    guarded: tuple[int, int] | None = None  # (the drop left for later, the hostiles near it or the character)
    if plan is not None:
        # Not with a hostile by the character or the drop: the stop ends the fight (a death in
        # Tower Cellar 5, 2026-10-11 22:50:55). The drop waits until the place is clear.
        drop = (plan.drop.x, plan.drop.y)
        close = [m for m in foes if min(math.dist((m.x, m.y), here), math.dist((m.x, m.y), drop)) <= GATHER_CLEAR]
        if close:
            if now - self.gather_waited >= WAIT_LOG_SECONDS:
                self.gather_waited = now
                LOG.info(
                    'Macro: the sweep leaves %s for later: %d hostiles within %.0f of it or the character',
                    plan.drop.label, len(close), GATHER_CLEAR,
                )  # fmt: skip
            guarded = (plan.drop.unit_id, len(close))
            plan = None
    # A valuable in sight not taken now (no room, hostiles by it) is stayed by; not one given up (its tries
    # are spent, run-0025-findings.md §2.3). Which to hold is lootpolicy.verdict's (rca/2026-10-18/
    # arch-level-behaviour.md step 4): not shown gear without room (user: "allow moving when the item isn't
    # very valuable"); in the KP_6 loop a plain valuable without room too (the player, 2026-10-18: "we should
    # stop and clear inventory with our designated town routine").
    looped = self.looping()
    sight = [d for d in loot.drops if d.kind == VALUABLE and math.dist(here, (d.x, d.y)) <= HOLD_SIGHT]
    facts = {d.unit_id: {'room': has_room(loot.room, d.size), 'shown': d.unit_id in loot.shown} for d in sight}
    # Out of the loop what a trip is made for is held too: the shared no-room routine (running/room.py; the player,
    # 2026-10-19: "EVERY loop and activity should have the same routines")
    hand = bool(sight) and self.trips_by_hand(run)
    near = [
        d
        for d in sight
        if lootpolicy.verdict(d, lootpolicy.SWEEP, **facts[d.unit_id], looped=looped).hold
        or (hand and not facts[d.unit_id]['room'] and lootpolicy.trip_for(d, shown=facts[d.unit_id]['shown']))
    ]
    self.held = min(near, key=lambda d: math.dist(here, (d.x, d.y))) if near else None
    if plan is None:
        held = self.held
        if held is not None and not looped and not has_room(loot.room, held.size):
            # The cube, then a trip (running/room.py): only in the quiet; room made, the next look takes it
            quiet = all(math.dist(here, (m.x, m.y)) > QUIET_UNITS for m in foes)
            if self.no_room(run, None, held, loot, quiet=quiet):
                return
        if held is not None and held.unit_id not in self.held_said:
            if len(self.held_said) > 200:
                self.held_said.clear()
            self.held_said.add(held.unit_id)
            if not has_room(loot.room, held.size):
                why = 'the inventory has no room for it'
            elif guarded is not None and guarded[0] == held.unit_id:
                why = f'{guarded[1]} hostiles within {GATHER_CLEAR:.0f} of it or the character'
            else:
                why = 'left for later'
            away = math.dist(here, (held.x, held.y))
            LOG.info('Macro: the sweep stays by %s, %.0f away: %s', held.label, away, why)
            run.say(f'Staying by {held.label}: {why}')
        return
    if len(self.drops.gathered) > 200:
        self.drops.gathered.clear()
    self.drops.gathered[plan.drop.unit_id] = self.drops.gathered.get(plan.drop.unit_id, 0) + 1
    LOG.info(
        'Macro: the sweep stops for %s, %.0f away from (%.1f, %.1f)',
        plan.drop.label, math.dist(here, (plan.drop.x, plan.drop.y)), *here,
    )  # fmt: skip
    self.sweep.until = now + FOLLOW_SECONDS + GATHER_SECONDS  # the sweep goes on after the pickup
    self.pick()
    raise Cancelled


def follow_on(self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, key_names) -> bool:
    """The sweep with nothing in reach: the next place worth it, else a stride toward the nearest
    hostile within SWEEP_UNITS, else (a wall between) the seek move onto a firing spot. Whether a step was taken."""
    player = world.player
    rect = run.actuator.keys.focused_window_rect()
    if run.clock() > self.sweep.until or player is None or rect is None:
        self.sweep.end()
        return False
    here = (player.x, player.y)
    near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SWEEP_UNITS]
    if not near:
        return False
    aspect = rect[2] / rect[3]
    found = self.next_step(run, world, near, ground, aspect, fighting=False)
    LOG.info(
        'Macro: sweeping with %d hostiles near and none in reach, from (%.1f, %.1f): %s',
        len(near), *here, step_line(found, here),
    )  # fmt: skip
    if found is not None:
        self.sweep_to(run, found)
        self.take_step(run, aspect, key_names, ground)
        return True
    level = self.known_level(player)
    if level is None:
        self.sweep.end()
        return False
    # A wall between: onto a firing spot at the nearest, the pointer held as a step holds it.
    nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
    if self.leaves((nearest.x, nearest.y), run.clock()):
        return False
    self.sweep.spend(run.clock())
    try:
        with run.actuator.held_act():
            at = (nearest.x, nearest.y)
            self.go(run, level, ground, player, rect, at, label(nearest), world.doors, key_names)
    except Abort as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: the sweep ends: no way to %s (%s)', label(nearest), stop)
        self.sweep.end()
        return False
    self.sweep.looked = run.clock()
    return True


def sweep_to(self: Hunter, run: Run, found: Step) -> None:
    """One of the sweep's own steps is to be taken."""
    self.sweep.spend(run.clock())
    self.stepping = found


def toward(self: Hunter, run: Run, world: World, near: list[Monster], ground: Ground, aspect: float) -> Step | None:
    """A stride toward the nearest hostile, ending STAND_OFF short of it; None when a wall is between."""
    player = world.player
    assert player is not None
    here = (player.x, player.y)
    nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
    intent = replace(OWN_MOVE, short=STAND_OFF, shot=True, shuns=self.sweep.shuns)
    return self.travel.stride(run, world, ground, aspect, (nearest.x, nearest.y), intent)


def asked_step(self: Hunter, run: Run, world: World, foes: list[Monster], reachable, ground, aspect) -> Step | None:
    """The pickup request inside a fight: with anything pickup.choose takes, pause the fight for the
    pickup step at once (Cancelled); with nothing, the step to take now, if one is worth it."""
    player = world.player
    assert player is not None
    here = (player.x, player.y)
    plan = choose(unshunned(run.loot(), run.clock()), here) if run.loot is not None else None
    if plan is not None and plan.drop.kind in (HEALING, REJUVENATION) and threat(run)(here, (plan.drop.x, plan.drop.y)):
        plan = None  # the pickup step leaves a potion among monsters too
    if plan is not None:
        # The press comes before the fight: waiting for its end, the steps meanwhile carried the
        # character away (user, 2026-10-11: "we left gold on the ground and moved away").
        LOG.info(
            'Macro: pickup asked in the fight with %d of %d hostiles in reach: %s first, %.0f away',
            len(reachable), len(foes), plan.drop.label, math.dist(here, (plan.drop.x, plan.drop.y)),
        )  # fmt: skip
        self.after_fight.clear()
        raise Cancelled
    if run.loot is not None and plan is None:
        self.after_fight.clear()  # nothing to pick up: no pickup (nor seek) step after the fight
        if self.unwait is not None:
            self.unwait()
    found = self.next_step(run, world, foes, ground, aspect, fighting=True)
    self.sweep.start(run.clock())
    LOG.info(
        'Macro: step asked in the fight with %d of %d hostiles in reach, from (%.1f, %.1f): %s; pickup after: %s',
        len(reachable), len(foes), *here, step_line(found, here), self.after_fight.is_set(),
    )  # fmt: skip
    if found is None:
        run.say(f'Standing well: no better place within {CAMP_REACH:.0f}')
    return found


def take_step(self: Hunter, run: Run, aspect: float, key_names=None, ground: Ground | None = None) -> None:
    """Take the chosen step (`travel`). The player's own move drops it; a failed step's place is
    left alone for a while."""
    found, self.stepping = self.stepping, None
    world = run.world()
    player = world.player
    if found is None or player is None:
        return
    why = 'a move was asked for' if self.move is not None else self.moving(run, world)
    if why is not None:
        LOG.info('Macro: the step is dropped (%s)', why)
        self.sweep.end()
        return
    try:
        self.travel.make(run, found, world, aspect, key_names, ground)
    except Abort as stop:
        if run.stops(stop):
            raise
        self.sweep.failed(run.clock(), found.spot if found.skill is None else None)
        run.say(f'No step: {stop}')
        LOG.info('Macro: the step to (%.1f, %.1f) failed (%s), %d in a row', *found.spot, stop, self.sweep.fails)
        return
    self.sweep.fails = 0
    self.step_asked_at = self.sweep.looked = run.clock()


def quarry(
    self: Hunter, area: int, here, foes: list[Monster], any_hostile: bool = False
) -> tuple[tuple[float, float], str] | None:
    """((x, y), name) of the nearest elite (with `any_hostile`: hostile of any kind): live in
    memory first, then remembered."""
    wanted = foes if any_hostile else [m for m in foes if m.leader]
    if wanted:
        nearest = min(wanted, key=lambda m: math.dist(here, (m.x, m.y)))
        return (nearest.x, nearest.y), label(nearest)
    known = self.remembered(area) if self.remembered is not None else []
    live = {m.unit_id for m in foes}
    self.vanished |= {
        unit_id for unit_id, x, y, _ in known if unit_id not in live and math.dist(here, (x, y)) <= VANISH_UNITS
    }
    kept = [
        (x, y)
        for unit_id, x, y, leader in known
        if (leader or any_hostile)
        and unit_id not in live
        and unit_id not in self.vanished
        and unit_id not in self.untouchable
    ]
    if not kept:
        return None
    return min(kept, key=lambda found: math.dist(here, found)), 'the remembered ' + (
        'monster' if any_hostile else 'elite'
    )
