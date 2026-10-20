"""The jump: one teleport press goes all the way to the next goal (the player, 2026-10-19: "KP_4 - force jump to the
next goal, probably ignore mobs to make things faster"; asked to choose: "Ignore mobs, resume on arrival"). A part of
macros/runner.py `MacroRunner`, its methods bound there.

The press hops again and again toward the teleport key's goal, the one the HUD shows as NEXT (hunt.py `pursued`, named
by hunting/moves.py `pursue_once`), each look priced with attack mode off: no hold for a fight and no strike gap, so
nothing in reach stops it. The safety stays: a hop the arbiter vetoes is not made (pursuit.py `arbitrate`), and a
retreat or a firing stand it makes instead ends the jump; the drinker looks at every hop (drinking.py `Drinker.look`)
and a life under the safety's floor ends it. A valuable within a stop's reach is picked up first (pickup.py
`worth_a_stop`). With no pursuit to name a goal (another build) each hop is the plain step toward the card's mark
(`_teleport_step`) until the character stops moving; a goal that is the route's own step (a door, the loot, the leaving,
the town) is that step, once.

It ends at the goal (the navigator's arrival, the object used, the level changed), at the player's hand (a key, a mouse
button, the pointer moved, a panel: `Hand`), at a death (nothing more is pressed: routines.py `Dead`, the loop stopped),
and after JUMP_HOPS hops or JUMP_SECONDS from the last press. A press of the key during the jump extends it (a fresh
JUMP_SECONDS) and queues nothing (runner.py `_dispatch`). Attack mode resumes after it as after a step, and on its own
end (not the hand's) it is turned on when a level run is held or the goal is a fight, unless the player turned it off
(`attack_declined`) or the loop is on. One line a jump: `Macro: jump: <goal>: N hops in S s, <why it ended>`.
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Player
from inventory_tracking.macros.actuator import Abort, Cancelled, Expired, Hand
from inventory_tracking.macros.build import NoWay
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import PICK_UP
from inventory_tracking.macros.hunting.base import Judged
from inventory_tracking.macros.pickup import pick_up, worth_a_stop
from inventory_tracking.macros.pursuit import FRESH, PASSAGE, Hold, Move, Operate
from inventory_tracking.macros.routines import DEAD, Dead
from inventory_tracking.macros.teleport import MOVED, ready
from inventory_tracking.routes.model import FIGHT


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


JUMP_HOPS = 60  # hops a press makes at most (a long level: 30 hops of ~0.5 s)
JUMP_SECONDS = 30.0  # from the last press
# Seconds with no act moving the character MOVED or more: no way on (a Blade Warp's delay is waited out by looks that
# move nothing, ~1.1 s from key to key in the scripted level, hunting/moves.py `advance`)
STILL_SECONDS = 3.0
SAFE_APPROACH = 'safe approach'  # safety.py `approach`: a shorter move on the same way, the jump goes on
# Seconds between presses of a key held on (pursuit.py FRESH): one after the jump's own end is that press, and attack
# mode fights on at the goal (runner.py `_dispatch`; a key held every 0.3 s paused the boss's fight for a jump each)
HELD = FRESH


@dataclass
class Jump:
    """The jump working now; `presses`: the key's presses during it, each a fresh JUMP_SECONDS (`extend`)."""

    presses: int = 0

    def extend(self) -> None:
        self.presses += 1


@dataclass(frozen=True)
class Leap:
    """One act of the jump: whether it goes on, why it ended, whether at its goal, the goal named, whether a fight."""

    on: bool
    why: str = ''
    arrived: bool = False
    goal: str | None = None
    fight: bool = False


def leap_of(found: Judged) -> Leap:
    """What one look of the teleport key's pursuit (hunting/moves.py `pursue_once`, made) means for the jump."""
    act, goal = found.act, found.goal
    label = goal.label if goal is not None else None
    fight = goal is not None and goal.do == FIGHT
    if isinstance(act, Move):
        if act.reason in ('', SAFE_APPROACH) or PASSAGE in act.reason:
            return Leap(True, goal=label, fight=fight)
        return Leap(False, f'safety: {act.reason}', goal=label, fight=fight)  # a retreat or a stand, made
    if isinstance(act, Operate):
        if act.goal.do == PICK_UP:
            return Leap(True, goal=label, fight=fight)  # a drop on the way taken: on to the goal
        return Leap(False, f'arrived: {act.goal.label} ({act.goal.do})', arrived=True, goal=label, fight=fight)
    if isinstance(act, NoWay):
        if act.arrived:
            return Leap(False, f'arrived: {act.reason}', arrived=True, goal=label, fight=fight)
        return Leap(False, act.reason, goal=label, fight=fight)
    if isinstance(act, Hold):
        return Leap(False, f'safety: {act.reason or "the fight here"}', goal=label, fight=fight)
    return Leap(False, type(act).__name__.lower(), goal=label, fight=fight)


def _jump(self: MacroRunner, run: Run, key_names) -> None:
    """The teleport press as a jump to the next goal (module doc)."""
    jump = Jump()
    with self.lock:
        self.jumping, self.jump_over = jump, False
    began = run.clock()
    hops, goal, fight, why, own_end, dead = 0, None, False, 'stopped', False, False
    try:
        player, _ = ready(run)
        run.in_time('the jump')  # a press too old for its key starts nothing (runner.py EXPIRES)
        run.deadline = math.inf  # the hops after are the jump's own, none late for the key
        area = player.area
        with self.lock:
            held = self.hunter is not None and self.hunter.leashed  # a level run: its attack mode on after
        presses, until, moved_at = 0, began + JUMP_SECONDS, began
        while True:
            if jump.presses != presses:
                presses, until = jump.presses, run.clock() + JUMP_SECONDS
            player = self._jump_look(run)
            if player.area != area:
                why = 'arrived: the level changed'
                break
            if hops >= JUMP_HOPS or run.clock() >= until:
                why = f'{hops} hops in {run.clock() - began:.0f} s: the next takes a press'
                break
            low = self._jump_life(run, player)
            if low is not None:
                why = low
                break
            if self._jump_drop(run, key_names):
                continue
            here = (player.x, player.y)
            try:
                leap = self._leap(run, key_names)
            except Expired:
                continue  # the act's priced time was up: the next look prices what happened (hunting/moves.py)
            goal, fight = leap.goal or goal, leap.fight or fight
            now = run.world().player
            if now is not None and (now.area != area or math.dist((now.x, now.y), here) >= MOVED):
                hops, moved_at = hops + 1, run.clock()  # a hop, a warp or a walk: the acts that moved the character
            if not leap.on:
                why = leap.why
                break
            if run.clock() - moved_at >= STILL_SECONDS:
                why = f'nothing moved the character for {run.clock() - moved_at:.1f} s: no way on'
                break
        own_end = True
        if not fight and not held:
            return
        with self.lock:
            if not self.attack_declined and not self.attack_mode and not self.loop.on:
                # "resume on arrival": the level run's mode, or the fight the goal is (`pursues` turned it on too)
                self.attack_mode = True
                LOG.info('Macro: jump: attack mode on: %s', 'the level run' if held else f'{goal} is a fight')
    except Cancelled:
        why = 'cancelled'
        raise
    except Hand as stop:
        why = f"the player's hand: {stop}"
        raise
    except Abort as stop:
        dead = isinstance(stop, Dead) or self._jump_dead(run)
        why = 'the character died' if dead else f'stopped: {stop}'
        if dead and not isinstance(stop, Dead):
            raise Dead(f'the character is dead ({stop})') from stop
        raise
    finally:
        with self.lock:
            self.jumping, self.jump_over = None, own_end
            if dead:
                # The player, 2026-10-19: "if we died - we MUST not take ANY other actions" (routines.py `Dead`)
                self.attack_mode = self.buff_mode = False
                self._end_run('the character died')
                if self.loop.on:
                    self._stop_loop(Dead('the character is dead'))
        line = f'jump: {goal or "no goal named"}: {hops} hops in {run.clock() - began:.1f} s, {why}'
        if own_end:
            run.say(line)  # the card too; `_say` logs it as `Macro: jump: …`
        else:
            LOG.info('Macro: %s', line)


def _leap(self: MacroRunner, run: Run, key_names) -> Leap:
    """One act toward the next goal: the pursuit's look with attack mode off, else the plain teleport step."""
    walker = self.hunter
    if walker is not None and walker.pursuing:
        found = walker.pursue_once(run, key_names, attacking=False)  # "ignore mobs": no hold, no strike gap
        if found is None:
            # The route's own step (a door, the loot, the leaving) or the town: that step, once (`_teleport_step`)
            self._teleport_step(run, key_names)
            return Leap(False, "arrived: the route's own step", arrived=True)
        if found.goal is not None:
            return leap_of(found)
        # No goal known: the plain step toward the card's mark (the route's stage, its way out), as before the jump
    before = run.world().player
    self._teleport_step(run, key_names)
    after = run.world().player
    moved = (
        before is not None
        and after is not None
        and after.area == before.area
        and math.dist((after.x, after.y), (before.x, before.y)) >= MOVED
    )
    target = self.target() if self.target is not None else None
    label = target.label if target is not None else None
    if moved:
        return Leap(True, goal=label)
    return Leap(False, 'arrived: the step moved nothing more', arrived=True, goal=label)


def _jump_look(self: MacroRunner, run: Run) -> Player:
    """The character before each act; `Dead` when it is dead, `Hand` when the player's hand is at work."""
    world = run.world()  # Cancelled when the runner stops the jump
    player = world.player
    if player is None:
        raise Abort('not in a game')
    if player.mode in DEAD:
        raise Dead('the character is dead')
    actuator = run.actuator
    if actuator.button_held(1) or actuator.button_held(3):
        raise Hand('a mouse button was pressed')
    actuator.guard()  # a key, the focus, the pointer moved off where the last hop left it
    return player


def _jump_life(self: MacroRunner, run: Run, player: Player) -> str | None:
    """The drinker's look (it drinks as attack mode's does); why the jump ends: life under the safety's floor."""
    walker = self.hunter
    if walker is None:
        return None
    walker.drinker.look(run, (player.x, player.y))
    loot = walker.drinker.last
    floor = walker.build.settings.safety.floor
    if loot is None or not loot.max_life or not 0 < loot.life < loot.max_life * floor / 100:
        return None
    return f'life {loot.life}/{loot.max_life}, under the safety floor of {floor:g}%'


def _jump_drop(self: MacroRunner, run: Run, key_names) -> bool:
    """A valuable or gold within a stop's reach is picked up before the next hop (`_teleport_step`'s rule); whether
    one was."""
    walker = self.hunter
    drop = worth_a_stop(run) if walker is not None else None
    if drop is None or walker is None:
        return False
    LOG.info('Macro: jump: %s is taken first', drop.label)
    pick_up(run, walker.level() if walker.level is not None else None, key_names, lambda: None)
    return True


def _at_the_fight(self: MacroRunner) -> bool:
    """Attack mode's last look was at its goal's fight: the goal a fight (the boss) and the character within its reach.
    A press then is posted to the mode as before the jump, and the fight costs nothing (no pause for a jump to where
    the character stands: a key held every 0.3 s by the Vizier killed him 3.4 s later). Under the lock."""
    hunter = self.hunter
    goal = hunter.pursued if hunter is not None else None
    here = hunter.stands if hunter is not None else None
    return goal is not None and here is not None and goal.do == FIGHT and math.dist(here, goal.place) <= goal.near


def _jump_dead(self: MacroRunner, run: Run) -> bool:
    """Whether the character reads dead after a stop; False when the game is not read."""
    try:
        player = run.world().player
    except Abort:
        return False
    return player is not None and player.mode in DEAD
