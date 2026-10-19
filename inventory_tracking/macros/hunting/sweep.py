"""The sweep: the drops attack mode goes for between fights, the steps it asks. A part of macros/hunt.py
`Hunter`, its methods bound there."""

import math
from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from inventory_tracking.combat.stance import CAMP_REACH
from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros import lootpolicy
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.game.records import HEALING, REJUVENATION, VALUABLE, Monster, World, has_room
from inventory_tracking.macros.hunting.base import (
    FOLLOW_SECONDS,
    GATHER_CHECK,
    GATHER_CLEAR,
    GATHER_SECONDS,
    HOLD_SIGHT,
    HOLD_UNITS,
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
    """Whether a step of the sweep's own to `spot` would leave the valuable it stays by (`held`):
    further than HOLD_UNITS from it. The sweep clears what it reaches from within that radius
    (user, 2026-10-11: "we shouldn't move away from valuable drops", "stay in radius, clear
    around to be safe")."""
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
    """The sweep picks up on its way (user, 2026-10-11: "when doing KP_1 auto-movement, we should also
    auto-pickup items/gold"): with the sweep on and something the pickup step would take
    (pickup.choose), the mode pauses for that step as for a press (Cancelled) and sweeps on after.
    A drop is stopped for GATHER_TRIES times at most: one no click takes must not hold the mode, and once
    given up it is neither chosen nor stayed by (said once, with why: `given_up`)."""
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
        # Not with a hostile beside the character or the drop: the stop ends the fight for the
        # walk and the clicks. Tower Cellar 5, 22:50:55 on 2026-10-11: the sweep stopped for a
        # potion 15 away with four hostiles within 10 (eight a second later), the clicks took
        # nothing for 5 s with a monster over the label, and the character died there, the
        # last 1000 of its life in under a second. The drop waits until the place is clear.
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
    # A valuable in sight the sweep does not take now (no room for it, or hostiles by it) is stayed by: the
    # Tower, 17:56:14 on 2026-10-11, a Grand Charm came down 20 away, the sweep said nothing, jumped twice
    # and stood 31 from it; the player went back for it by hand. Not one given up (above): its tries are
    # spent, and staying by it holds the sweep for nothing (River of Flame, 00:26:49 on 2026-10-14: 3.9 s
    # of "no better place" by a Large Charm with six hostiles near, run-0025-findings.md §2.3).
    # Not by gear the filter shows that there is no room for (game/records.py `prized`): the mode goes on to
    # the hostiles (Drifter Cavern, 19:59:52 on 2026-10-12: "the sweep stays by Magic Kriss", 13
    # hostiles 39 away and attack mode idle; user: "allow moving when the item isn't very valuable").
    # The sweep's "must not leave it" is the policy's (macros/lootpolicy.py `verdict`, step 4 of rca/2026-10-18/
    # arch-level-behaviour.md); in the KP_6 loop a plain valuable with no room is held too (the player, 2026-10-18
    # 17:50: "we should stop and clear inventory with our designated town routine"). The loop's attack mode ends
    # with its level run (runner.py `_run_over`) and the sweep runs only outside one: the loop's press holds it
    # first (macros/pickup.py `pick_up`), and a stand here is the watchdog's 45 s 'stall', a room cause.
    looped = self.looping()
    sight = [d for d in loot.drops if d.kind == VALUABLE and math.dist(here, (d.x, d.y)) <= HOLD_SIGHT]
    facts = {d.unit_id: {'room': has_room(loot.room, d.size), 'shown': d.unit_id in loot.shown} for d in sight}
    near = [d for d in sight if lootpolicy.verdict(d, lootpolicy.SWEEP, **facts[d.unit_id], looped=looped).hold]
    self.held = min(near, key=lambda d: math.dist(here, (d.x, d.y))) if near else None
    if plan is None:
        held = self.held
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
    """The sweep with nothing in reach: the next place if one is worth it, else a stride toward
    the nearest hostile within SWEEP_UNITS, else (a wall between) the seek step's own move onto a
    firing spot at it. Whether a step was taken."""
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
    # A wall between: onto a firing spot at the nearest, as the seek step goes to an elite, with
    # the pointer held as a step holds it (the mode itself aims once and casts at once).
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
    """The sweep with no place worth going to and nothing in reach: a stride toward the nearest
    hostile, to end STAND_OFF short of it. None when there is none (a wall between: the firing
    spot's to find)."""
    player = world.player
    assert player is not None
    here = (player.x, player.y)
    nearest = min(near, key=lambda m: math.dist(here, (m.x, m.y)))
    intent = replace(OWN_MOVE, short=STAND_OFF, shot=True, shuns=self.sweep.shuns)
    return self.travel.stride(run, world, ground, aspect, (nearest.x, nearest.y), intent)


def asked_step(self: Hunter, run: Run, world: World, foes: list[Monster], reachable, ground, aspect) -> Step | None:
    """The pickup request inside a fight. With anything to pick up (pickup.choose: a valuable, gold
    within a jump, a potion the belt wants) the fight stops for the pickup step at once (Cancelled,
    which the runner reads as the mode's pause). With nothing: the step to take now, if one is
    worth it."""
    player = world.player
    assert player is not None
    here = (player.x, player.y)
    plan = choose(unshunned(run.loot(), run.clock()), here) if run.loot is not None else None
    if plan is not None and plan.drop.kind in (HEALING, REJUVENATION) and threat(run)(here, (plan.drop.x, plan.drop.y)):
        plan = None  # a potion among monsters is left by the pickup step too: no pause of the fight for it
    if plan is not None:
        # What the press asks for comes before the fight: the mode pauses for the pickup step now,
        # as it does with nothing in reach, and fights on after it. First only a valuable did; gold
        # and potions waited for the fight's end, and the steps the same presses made meanwhile
        # took the character away from them (Halls of Vaught, 13:57:08 on 2026-10-11: 5221 gold
        # 12 away, "pickup after: True" three times, then a Blade Warp of 19 and one of 16, and
        # the pile was out of a jump's reach; user: "we left gold on the ground and moved away").
        LOG.info(
            'Macro: pickup asked in the fight with %d of %d hostiles in reach: %s first, %.0f away',
            len(reachable), len(foes), plan.drop.label, math.dist(here, (plan.drop.x, plan.drop.y)),
        )  # fmt: skip
        self.after_fight.clear()
        raise Cancelled
    if run.loot is not None and plan is None:
        self.after_fight.clear()  # nothing to pick up: no pickup step, and so no seek step, after the fight
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
    """Go to the place the fight stopped for, or the stride's end, by the way it was chosen for
    (`travel`). The player's own move comes first: a press of theirs, a held key or a character
    already going drops the step. A step that fails leaves its place alone for a while."""
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
