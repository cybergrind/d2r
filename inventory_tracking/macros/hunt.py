"""Attack mode and the seek step. The toggle turns attack mode on and off; the seek step goes toward
the nearest unique or champion and leaves attack mode on. The history of each rule is in macros/plan.md.

Attack mode (`Hunter.attack_mode`, a run that lives until cancelled): everything within the blades'
REACH with a clear shot (sight.py: the flight layer of the read grids, closed doors) is fought while
the player moves about as they like. The mouse, the keyboard and the character's own moves and casts
are not cancels: only its toggle or the macro request ends it, the game being left, or MISSES_IN_A_ROW fights
that stopped one after another. The player's hand is on the mouse all along, so the actuator aims
once and casts at once (`Actuator.steady` off). the teleport and seek steps work meanwhile: the runner pauses the
mode for the step and resumes it after (runner.py).

A fight (`Hunter.fight`) is one hold of the input that has Echoing Strike: the right mouse button
when it holds the skill, else its skill key, else a left click with Shift. The game casts at its own
rate; an input idle RETAP_SECONDS is released and pressed again. The pointer is kept on the combat
policy's line (combat/policy.py, the decision the simulator scores); a monster in reach the policy
finds no line for is aimed at directly, the elite first, then the nearest, AIM_BEYOND past it. An
elite gets Sigil: Lethargy under it once per SIGIL_SECONDS, the strongest monster in reach Death Mark
once per DEATH_MARK_SECONDS. The main weapon set is swapped in for a tough pack only (`tough`).

The player's move comes before any strike (`sense`, `serve_move`): a left click releases the strike
and blocks it until the character has gone and stands again; a click made while a cast ran, which
the game may have swallowed, is made again for the player. A held key or a running character makes
the mode wait.

The seek step (`Hunter.seek`, one request one step): toward the nearest elite the game holds in memory or the
terror tracker remembers alive in this level, onto the nearest spot with a shot at it
(sight.firing_spots, within STRIKE_REACH), by a click when that is within WALK_UNITS over clear
ground, by a teleport hop otherwise (teleport.hop_toward). None known: the unexplored room nearest by
the way (the potential from the character's own tile). An elite already in reach is only named.
"""

import math
import threading
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass

from inventory_tracking.combat.policy import (
    AIM_BEYOND,
    REACH,
    RUN_MODES,
    STRIKE_REACH,
    Choice,
    LinePolicy,
    Policy,
    observe,
)
from inventory_tracking.combat.score import LiveScore
from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground, Level, Room, Target
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import (
    ACTING,
    CHARACTERS,
    DEAD,
    TOWN_NPCS,
    on_screen,
    press_skill,
    screen_fraction,
    settle,
    take_battle_weapons,
)
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach
from inventory_tracking.macros.skills import DEATH_MARK, ECHOING_STRIKE, SIGIL_LETHARGY, SWAP_WEAPONS, skill_name
from inventory_tracking.macros.teleport import (
    MOVED,
    WALK_SECONDS,
    Way,
    ground_fraction,
    hop_toward,
    in_view,
    moved,
    ready,
)
from inventory_tracking.macros.world import NO_OWNER, Monster, World
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror.tracker import UNKILLABLE


SIGIL_SECONDS = 10.0  # between two sigils under the same monster
DEATH_MARK_SECONDS = 8.0  # between two Death Marks; the debuff lasts 125 + 13/level frames (skills.txt)
WALK_CLICKS = 2  # clicks for one walk to a firing spot
WALK_UNITS = 10.0  # a firing spot this near, over clear ground, is walked to, not teleported to (as NEAR_WARP)
RETAP_SECONDS = 0.25  # the held input idle this long between casts: released and pressed again
FIGHT_SECONDS = 60.0  # one fight ends here at the latest; attack mode looks again right after
POLL = 0.1  # seconds between looks in attack mode while nothing is fought
FRAME = 0.04  # seconds between looks during a fight: one game frame, so a move of the player's is yielded to at once
DECIDE_SECONDS = 0.12  # between two askings of the policy while its monster lives (a decision costs up to 50 ms)
REAIM_UNITS = 1.0  # the focal point this far from where the pointer was put: aimed again
STRAY_PIXELS = 25  # the pointer this far from where it was put (the player's hand): aimed again
SIGHT = 30.0  # world units: hostiles further off are not part of the decision
HAND_REST = 0.2  # seconds the pointer must rest where the player's hand left it before it is aimed again
SLICE = 0.01  # seconds between looks at the left mouse button while the mode waits or fights
MOVE_SETTLE = 0.12  # seconds the character stands free after a move was asked for before the click is made again
MOVE_QUIET = 0.4  # seconds the strikes wait on a click the game took and that has moved nothing
MOVE_RETRY = 0.3  # seconds between two clicks made for the player
MOVE_CLICKS = 2  # clicks made for the player per move asked for
MOVE_SECONDS = 2.0  # a move asked for that has shown nothing after this long is dropped
MOVED_UNITS = 1.0  # world units the character has gone: the move is under way
TOUGH_POINTS = 40_000.0  # life points in reach from which a pack is worth the main weapons
ELITE_LIFE = 2.0  # a unique's or champion's life in Hell, in its type's points (the tables hold the plain monster's)
MAIN_AFTER = 1.0  # seconds after a step before the main weapons are swapped in for a fight
SWAP_RETRY_SECONDS = 5.0  # after a swap to the main weapons that did not come
INPUT_SECONDS = 1.0  # Echoing Strike on no input for this long (another skill selected) before it is a stopped fight
MISSES_IN_A_ROW = 5  # fights that stopped one after another before attack mode gives up
CAST_SECONDS = 0.8  # for the first cast animation to show after the press
IDLE_LOG_SECONDS = 3.0  # between log lines on what attack mode sees while nothing is in reach

Remembered = Callable[[int], list[tuple[int, float, float, bool]]]  # area -> (unit id, x, y, leader)


def hostiles(world: World) -> list[Monster]:
    """Live monsters the hunt may strike: not owned, not allied, not townsfolk or scenery, placed."""
    return [
        m
        for m in world.monsters
        if m.owner == NO_OWNER
        and not m.ally
        and (m.x or m.y)
        and m.txt_id not in UNKILLABLE
        and m.txt_id not in TOWN_NPCS
    ]


def label(monster: Monster) -> str:
    return f'{"the elite" if monster.leader else "the monster"} {monster.txt_id} ({monster.unit_id})'


def life(monster: Monster | None) -> str:
    if monster is None:
        return 'gone'
    return f'{monster.life}/{monster.max_life}' if monster.max_life else 'life unknown'


def strike_input(run: Run, world: World, key_names) -> tuple[tuple[str, ...], str]:
    """(what to hold, how to say it) for Echoing Strike: the right mouse button when it holds the
    skill (as the player casts it), else its skill key, else the left button with Shift."""
    player = world.player
    assert player is not None
    if player.right_skill == ECHOING_STRIKE:
        return ('Button3',), 'right click'
    if ECHOING_STRIKE in world.slots:
        try:
            run.keys.update(key_names(world, (ECHOING_STRIKE,)))
            return (run.keys[ECHOING_STRIKE],), f'key {run.keys[ECHOING_STRIKE]}'
        except Abort as problem:
            LOG.info('Macro: %s; trying the left mouse button', problem)
    if player.left_skill == ECHOING_STRIKE:
        return ('Shift_L', 'Button1'), 'Shift+click'
    raise Abort(
        f'Echoing Strike is on no skill key and on neither mouse button '
        f'(left {skill_name(player.left_skill)}, right {skill_name(player.right_skill)})'
    )


@dataclass
class Move:
    """A move the player asked for with the left mouse button while attack mode ran."""

    at: float  # clock time of the press
    pixel: tuple[int, int] | None  # where the pointer was (root coordinates)
    origin: tuple[float, float] | None = None  # where the character stood, once read
    under_way: bool = False  # the character has been seen going
    free_at: float | None = None  # since when the character has stood free with the button up
    swallowed: bool = False  # pressed while a cast ran or the strike was held: the game may not have taken it
    clicks: int = 0  # clicks made for the player
    clicked_at: float = -math.inf


class Hunter:
    """The hunt's state across presses: the level and what is remembered of it come from the level
    guide and the terror tracker (callables, set by the service), sigils and marks from the clock."""

    def __init__(
        self,
        level: Callable[[], Level | None] | None = None,
        remembered: Remembered | None = None,
        explored: Callable[[int], set[tuple]] | None = None,
        policy: Policy | None = None,
    ) -> None:
        self.level = level
        self.remembered = remembered
        self.explored = explored
        self.sigiled: dict[int, float] = {}  # unit id -> clock time of the last sigil under it
        self.policy: Policy = policy or LinePolicy()  # where to cast (combat/policy.py)
        self.score = LiveScore()  # the last minute of attack mode: damage and kills (combat/score.py)
        self.marked_at = -math.inf  # clock time of the last Death Mark
        self.swap_failed_at = -math.inf  # clock time a swap to the main weapons last did not come
        self.move: Move | None = None  # the move the player asked for and has not got yet: before any strike
        self.left_down = False  # the left mouse button at the last look
        self.fresh_press = False  # a press seen since `nap` last began
        self.casting = False  # a cast runs or the strike input is held: a click now may be swallowed
        # The pickup step during attack mode (runner): the mode pauses itself once nothing is left in reach.
        self.after_fight = threading.Event()

    def known_level(self, player) -> Level | None:
        level = self.level() if self.level is not None else None
        return level if level is not None and level.area == player.area else None

    def seek(self, run: Run, key_names) -> None:
        """One seek step: a move toward the nearest elite, or into the unexplored."""
        player, rect = ready(run)
        if player.in_town:
            raise Abort('in town: nothing to hunt')
        level = self.known_level(player)
        if level is None:
            raise Abort('no level map for this level yet (Win+C shows it)')
        aspect = rect[2] / rect[3]
        ground = Ground(level.ground)
        here = (player.x, player.y)
        world = run.world()
        foes, doors = hostiles(world), world.doors
        leaders = [m for m in foes if m.leader]
        LOG.info(
            'Macro: seek: %d hostiles, %d elites, at (%.1f, %.1f); left %s, right %s',
            len(foes), len(leaders), *here, skill_name(player.left_skill), skill_name(player.right_skill),
        )  # fmt: skip
        # The blades' own reach, not the firing spots': a step toward an elite attack mode already
        # fights would break that fight off.
        near = [m for m in leaders if in_reach(ground, here, (m.x, m.y), REACH, doors)]
        if near:
            run.say(f'{label(near[0])} is in reach: attack mode takes it')
            return
        quarry = self.quarry(level.area, here, foes)
        if quarry is None:
            self.explore(run, level, ground, player, rect, key_names)
            return
        spot, name = quarry
        target = self.firing_target(level, ground, here, spot, name, doors)
        goal = (target.point[0] * TILE_UNITS, target.point[1] * TILE_UNITS)
        if math.dist(here, goal) < MOVED:
            # Already on a firing spot (the shot from the character's exact place may still read blocked):
            # a click under its feet moves nothing and would stop the step.
            run.say(f'{name} is in reach: attack mode takes it')
            return
        if math.dist(here, goal) <= WALK_UNITS and clear_shot(ground, here, goal, doors):
            walk_to(run, goal, player, aspect, name)
        else:
            hop_toward(run, target, player, rect, key_names)

    def quarry(self, area: int, here, foes: list[Monster]) -> tuple[tuple[float, float], str] | None:
        """((x, y), name) of the nearest elite: live in memory first, then remembered."""
        leaders = [m for m in foes if m.leader]
        if leaders:
            nearest = min(leaders, key=lambda m: math.dist(here, (m.x, m.y)))
            return (nearest.x, nearest.y), label(nearest)
        known = self.remembered(area) if self.remembered is not None else []
        live = {m.unit_id for m in foes}
        kept = [(x, y) for unit_id, x, y, leader in known if leader and unit_id not in live]
        if not kept:
            return None
        return min(kept, key=lambda found: math.dist(here, found)), 'the remembered elite'

    def attack_mode(self, run: Run, key_names) -> None:
        """Attack mode: fight whatever comes into reach until cancelled. Every pause the mode makes, in its own
        loop and inside a mark, a sigil or a swap, looks at the left mouse button every SLICE
        (`watchful`), so no click of the player's goes unseen."""
        plain = run.pace.sleep

        def watchful(seconds: float) -> None:
            until = run.clock() + seconds
            while True:
                self.sense(run)
                left = until - run.clock()
                if left <= 0:
                    return
                plain(min(SLICE, left))

        run.pace.sleep = watchful
        try:
            self._attack_mode(run, key_names)
        finally:
            run.pace.sleep = plain

    def _attack_mode(self, run: Run, key_names) -> None:
        misses, logged_at = 0, -math.inf
        self.after_fight.clear()  # a wait left over from a run that ended another way
        entered = run.clock()  # the mode starts anew after every teleport and seek step
        unready_since: float | None = None  # since when Echoing Strike has been on no input (see below)
        run.say('Attack mode on')
        while True:
            world = run.world()  # Abort('cancelled') when the runner ends the mode
            self.score.note(run.clock(), world.player, hostiles(world), world.dead)
            if not world.in_game:
                # The lobby or the menu: the mode ends, so the macro request there starts the macro at once.
                raise Abort('attack mode off: the game was left')
            player = world.player
            self.casting = player is not None and player.mode in ACTING
            self.sense(run)
            if self.move is not None and player is not None:
                self.serve_move(run, world)  # the player's move first: no strike while it is pending
                self.nap(run, FRAME)
                continue
            if player is None or world.open_panels or player.in_town or self.moving(run, world):
                self.step_aside()
                self.nap(run, POLL)  # the player's move (a key, the left button, a run): waited through
                continue
            level = self.known_level(player)
            ground = Ground(level.ground if level is not None else ())
            here = (player.x, player.y)
            foes = hostiles(world)
            if not any(in_reach(ground, here, (m.x, m.y), REACH, world.doors) for m in foes):
                self.step_aside()
                if foes and run.clock() - logged_at >= IDLE_LOG_SECONDS:
                    logged_at = run.clock()
                    nearest = min(foes, key=lambda m: math.dist(here, (m.x, m.y)))
                    LOG.info(
                        'Macro: idle: %d hostiles, none in reach; nearest %s %.0f away, shot %s, from (%.0f, %.0f)',
                        len(foes), label(nearest), math.dist(here, (nearest.x, nearest.y)),
                        'clear' if clear_shot(ground, here, (nearest.x, nearest.y), world.doors) else 'blocked', *here,
                    )  # fmt: skip
                self.nap(run, POLL)
                continue
            rect = run.actuator.keys.focused_window_rect()
            if rect is None:
                self.nap(run, POLL)
                continue
            try:
                strike_input(run, world, key_names)
                unready_since = None
            except Abort:
                # Right after a hop the right button still holds Teleport, after a mark Death Mark: the
                # game puts the skill back within a moment, so wait; only an input that stays away is a
                # stopped fight.
                unready_since = run.clock() if unready_since is None else unready_since
                if run.clock() - unready_since < INPUT_SECONDS:
                    self.nap(run, FRAME)
                    continue
            try:
                # The main weapons for a tough pack, and only once the mode has run MAIN_AFTER since the
                # last step: a swap after every hop of a chain of seek steps, and the staff back for the
                # next, costs more standing than it gains. A fight begun earlier is fought with what is
                # held and stops for the swap at that time.
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), REACH, world.doors)]
                tough = self.tough(world, reachable)
                settled = run.clock() - entered >= MAIN_AFTER
                held = self.main_weapons(run, world, key_names, swap=settled and tough)
                pause = entered + MAIN_AFTER if tough and not held else None
                self.fight(run, ground, rect[2] / rect[3], key_names, until=pause)
                misses = 0
            except Abort as stop:
                if run.cancelled.is_set():
                    raise
                misses += 1
                LOG.info('Macro: the fight stopped (%s), %d in a row', stop, misses)
                if misses >= MISSES_IN_A_ROW:
                    raise Abort(f'attack mode off: {misses} fights stopped in a row, the last on "{stop}"') from stop
                self.nap(run, POLL)

    def step_aside(self) -> None:
        """Nothing is being fought: a step that waited for the fight (the pickup step) gets its turn, as a cancel
        the runner reads as a pause."""
        if self.after_fight.is_set():
            self.after_fight.clear()
            raise Abort('cancelled')

    def firing_target(self, level: Level, ground: Ground, here, mob, name: str, doors=()) -> Target:
        """The target of a hop toward `mob`: the nearest spot on a room with a shot at it, or the monster
        itself. A spot the character all but stands on leaves the hop nothing to gain, which the landing says."""
        spots = firing_spots(ground, mob, STRIKE_REACH, here, doors) or [mob]
        spot = next((s for s in spots if room_at(level.rooms, (s[0] / TILE_UNITS, s[1] / TILE_UNITS))), spots[0])
        tile = (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS)
        LOG.info(
            'Macro: hunting %s at (%.1f, %.1f), %.0f away from (%.1f, %.1f), firing spot (%.1f, %.1f) of %d',
            name, mob[0], mob[1], math.dist(here, mob), here[0], here[1], spot[0], spot[1], len(spots),
        )  # fmt: skip
        return Target(level.area, level.rooms, tile, name, 'hunt', False, level.ground)

    def explore(self, run: Run, level: Level, ground: Ground, player, rect, key_names) -> None:
        """A hop toward the unexplored room nearest by the way there: its cheapest landable tile is the mark."""
        seen = self.explored(level.area) if self.explored is not None else set()
        here = (player.x / TILE_UNITS, player.y / TILE_UNITS)
        rooms = [
            room
            for room in level.rooms
            if (room.x, room.y, room.width, room.height) not in seen and room_at((room,), here) is None
        ]
        if not rooms:
            raise Abort('the level is explored and nothing is left to hunt')
        origin = Way(Target(level.area, level.rooms, here, 'here', 'explore', False, level.ground))
        best: tuple[float, Room, tuple[int, int]] | None = None
        for room in rooms:
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    cost = origin.cost.get((x, y))
                    if cost is not None and (best is None or cost < best[0]):
                        best = (cost, room, (x, y))
        if best is None:
            raise Abort(f'no way over the rooms to the {len(rooms)} unexplored rooms')
        cost, room, (x, y) = best
        LOG.info(
            'Macro: exploring toward room %s at (%d, %d), %.0f tiles by the way, %d unexplored of %d',
            room.preset, x, y, cost, len(rooms), len(level.rooms),
        )  # fmt: skip
        target = Target(
            level.area, level.rooms, (x + 0.5, y + 0.5), 'an unexplored room', 'explore', False, level.ground
        )
        hop_toward(run, target, player, rect, key_names)

    def main_weapons(self, run: Run, world: World, key_names, *, swap: bool = True) -> bool:
        """The main weapon set in hand for a fight (it has the skill levels and the damage; a hop
        leaves the teleport set in hand); whether it is held, or nothing is known to want. With `swap`
        off it only looks. The next hop swaps the staff back in by itself (teleport.take_teleport). A
        character the macros do not know, or hands that cannot be read, are left as they are; a swap
        that did not come is not asked for again for SWAP_RETRY_SECONDS."""
        loadout = CHARACTERS.get(world.player.name) if world.player is not None else None
        if loadout is None or run.hands is None or run.clock() - self.swap_failed_at < SWAP_RETRY_SECONDS:
            return True
        held = set(run.hands())
        if not held or loadout.battle & held:
            return True
        if not swap:
            return False
        run.keys.update(key_names(world, (SWAP_WEAPONS,)))
        run.battle_hands = loadout.battle
        run.say('Main weapons for the fight')
        take_battle_weapons(run)
        if not loadout.battle & set(run.hands()):
            self.swap_failed_at = run.clock()
        return True

    def sense(self, run: Run) -> bool:
        """Look at the left mouse button; a press is a move asked for (`self.move`). True on a new press."""
        down = run.actuator.button_held(1)
        pressed = down and not self.left_down
        self.left_down = down
        if pressed:
            self.move = Move(run.clock(), run.actuator.keys.pointer(), swallowed=self.casting)
            self.fresh_press = True
        return pressed

    def nap(self, run: Run, seconds: float) -> bool:
        """Sleep `seconds`, looking at the left button every SLICE (a click is down for 60-120 ms);
        cut short, and True, on a press."""
        until = run.clock() + seconds
        self.fresh_press = False
        while True:
            self.sense(run)
            if self.fresh_press:  # seen here or inside the sleep (attack mode's own `watchful`)
                return True
            left = until - run.clock()
            if left <= 0:
                return False
            run.pace.sleep(min(SLICE, left))

    def serve_move(self, run: Run, world: World) -> None:
        """The move the player asked for comes before any strike. The game takes no click while a
        cast runs, and a click is over before the cast is: so the strike input is let go at the press
        (the caller), nothing is cast while the move is pending, and when the character stands free
        with the button up and has not gone anywhere, a click the cast may have swallowed is made
        again for the player where they made it (a walk, an item picked up, a door: whatever was under
        the pointer), MOVE_CLICKS times at most. The move is done when the character has gone and
        stands again, or dropped after MOVE_SECONDS with nothing to show."""
        move, player, now = self.move, world.player, run.clock()
        if move is None or player is None:
            self.move = None
            return
        here = (player.x, player.y)
        if move.origin is None:
            move.origin = here
        if player.mode in RUN_MODES or math.dist(here, move.origin) > MOVED_UNITS:
            move.under_way = True
        if move.under_way:
            if player.mode not in RUN_MODES and not self.left_down:
                self.move = None  # arrived: the strikes may go on
            return
        if self.left_down or player.mode in ACTING:
            move.free_at = None  # the button still down (the game sees it), or the cast still running
            if now - move.at > MOVE_SECONDS and not self.left_down:
                self.move = None
            return
        if move.free_at is None:
            move.free_at = now
        if not move.swallowed:
            # The character was free at the press: the game took the click, and a click that moves nothing
            # (an item picked up, a chest) is not made again. The strikes wait MOVE_QUIET for a walk to show.
            if now - move.at >= MOVE_QUIET:
                self.move = None
            return
        if now - move.free_at < MOVE_SETTLE or now - move.clicked_at < MOVE_RETRY:
            return
        if move.clicks >= MOVE_CLICKS or now - move.at > MOVE_SECONDS or move.pixel is None:
            LOG.info('Macro: the move asked for %.1fs ago showed nothing after %d clicks', now - move.at, move.clicks)
            self.move = None
            return
        keys = run.actuator.keys
        back = keys.pointer()
        try:
            keys.move_pointer(*move.pixel)
            keys.sync()
            run.actuator.click()
            if back is not None:
                keys.move_pointer(*back)
                keys.sync()
        except Abort as stop:
            if run.cancelled.is_set():
                raise
            LOG.info('Macro: the click for the player was not made (%s)', stop)
            self.move = None
            return
        move.clicks += 1
        move.clicked_at = run.clock()
        LOG.info(
            'Macro: the click the cast swallowed made again at %s, %.2fs after the press (%d of %d)',
            move.pixel, move.clicked_at - move.at, move.clicks, MOVE_CLICKS,
        )  # fmt: skip

    def tough(self, world: World, reachable: list[Monster]) -> bool:
        """Whether what is in reach is worth a swap to the main weapons: TOUGH_POINTS of life between
        them, an elite's counted ELITE_LIFE times. An elite alone is not: the Catacombs packs died
        within a second or two of the swap, which costs most of a second there and back."""
        if world.player is None:
            return False
        seen = observe(world.player, reachable, ())
        return sum(foe.left * (ELITE_LIFE if foe.elite else 1.0) for foe in seen.foes.values()) >= TOUGH_POINTS

    def moving(self, run: Run, world: World, *, keys: bool = True) -> str | None:
        """Why the pointer is the player's right now, or None: a key of theirs is down, the left mouse
        button is down (a move), or the character is walking or running somewhere. Attack mode yields
        to all three: it must never get in the way of moving. With `keys` off a held key is no reason
        (a fight under way: the strike stays held through the player's own key taps)."""
        if keys and run.actuator.key_held():
            return 'a key is held'
        if run.actuator.button_held(1):
            return 'the left button is down'
        if world.player is not None and world.player.mode in RUN_MODES:
            return 'the character is on the move'
        return None

    def choose(self, world: World, foes: list[Monster], reachable: list[Monster], ground: Ground) -> Choice:
        """Where to cast now: the policy's line over the hostiles in sight (combat/policy.py, the one
        the simulator scores), else straight at what is in reach: the elite first, then the nearest,
        AIM_BEYOND past it (a monster in reach is never left standing for want of a line)."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT]
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        found = self.policy(observe(player, near, companions, ground, world.doors))
        if found is not None:
            return found
        prey = min(reachable, key=lambda m: (not m.leader, math.dist(here, (m.x, m.y))))
        away = math.dist(here, (prey.x, prey.y)) or 1.0
        beyond = (prey.x + (prey.x - here[0]) / away * AIM_BEYOND, prey.y + (prey.y - here[1]) / away * AIM_BEYOND)
        return Choice(beyond, prey.unit_id, 0.0)

    def fight(self, run: Run, ground: Ground, aspect: float, key_names, until: float | None = None) -> None:
        """Strike while anything is in reach and the player stands: one hold of the strike input
        through the whole fight, the pointer kept on the policy's line, which is asked again every
        DECIDE_SECONDS and when its monster is gone. Ends when nothing is in reach, when the player
        moves (the mode yields and comes back after), at `until` (the caller's swap to the main
        weapons), or after FIGHT_SECONDS."""
        started = run.clock()
        held, how = strike_input(run, run.world(), key_names)  # before any cast: no key, no fight
        casts = down = 0
        acting, idle_since, began = False, None, started
        choice: Choice | None = None
        decided_at = -math.inf
        aimed: tuple[tuple[float, float], tuple[float, float]] | None = None  # (focal, the character's place)
        again: Callable[[], None] | None = None
        watched: set[int] = set()  # the hostiles seen in reach while the input was held
        lined: int | None = None  # the monster the line last logged went through
        hand: tuple[tuple[int, int] | None, float] = (run.actuator.keys.pointer(), -math.inf)  # pointer, since when
        ended = f'Fight stopped after {FIGHT_SECONDS:.0f}s'
        with ExitStack() as stack:
            while run.clock() - started < FIGHT_SECONDS:
                world = run.world()
                player = world.player
                if player is None:
                    raise Abort('not in a game')
                if player.mode in DEAD:
                    raise Abort('the character is dead')
                alive = {m.unit_id for m in world.monsters}
                down += len(watched - alive)
                watched &= alive
                if again is not None:
                    if player.mode in ACTING:
                        casts += not acting
                        acting, idle_since = True, None
                    else:
                        acting = False
                        if not casts and run.clock() - began > CAST_SECONDS:
                            raise Abort(f'no cast seen after the {how} (Echoing Strike not on {how}?)')
                        if idle_since is None:
                            idle_since = run.clock()
                        elif run.clock() - idle_since > RETAP_SECONDS:
                            again()
                            idle_since = None
                self.casting = again is not None or player.mode in ACTING
                self.sense(run)
                why = 'a move was asked for' if self.move is not None else self.moving(run, world, keys=again is None)
                if why is not None:
                    ended = f'Yielded ({why})'
                    break
                here = (player.x, player.y)
                foes = hostiles(world)
                self.score.note(run.clock(), player, foes, world.dead)
                reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), REACH, world.doors)]
                if not reachable:
                    ended = 'Nothing left in reach'
                    break
                if until is not None and run.clock() >= until:
                    if self.tough(world, reachable):
                        ended = 'Stopping for the main weapons'  # attack mode takes them and fights on
                        break
                    until = None  # what is left is not worth the swap any more: fought on as it is
                if again is not None and run.actuator.key_held():
                    # A key of the player's (a skill of their own, a potion): the strike stays held, as
                    # their own hand would hold it, and the macro's own aims and keys wait for the release.
                    if self.nap(run, FRAME):
                        ended = 'Yielded (a move was asked for)'
                        break
                    continue
                if choice is None or choice.unit not in alive or run.clock() - decided_at >= DECIDE_SECONDS:
                    choice, decided_at = self.choose(world, foes, reachable, ground), run.clock()
                prey = next(m for m in foes if m.unit_id == choice.unit)
                if run.clock() - self.marked_at > DEATH_MARK_SECONDS and DEATH_MARK in world.slots:
                    strongest = max(reachable, key=lambda m: (m.leader, m.max_life, -math.dist(here, (m.x, m.y))))
                    self.casting = True  # the mark's own cast swallows a click as a strike does
                    self.death_mark(run, strongest, aspect, key_names)
                    aimed = None
                    began = run.clock() if not casts else began  # the mark's own cast is no missing strike
                if prey.leader and run.clock() - self.sigiled.get(prey.unit_id, -math.inf) > SIGIL_SECONDS:
                    self.casting = True
                    self.sigil(run, world, prey, aspect, key_names)
                    aimed = None
                    began = run.clock() if not casts else began
                pointer, left_at = run.actuator.keys.pointer(), run.actuator.left_at
                strayed = pointer is None or left_at is None or math.dist(pointer, left_at) > STRAY_PIXELS
                if pointer != hand[0]:
                    hand = (pointer, run.clock())  # the pointer is somewhere new
                # The player's hand is taking the pointer somewhere (to click a spot): it is not pulled
                # back to the line until it has rested HAND_REST, or the click would land on the line.
                busy_hand = strayed and aimed is not None and run.clock() - hand[1] < HAND_REST
                stale = aimed is None or strayed or math.dist(aimed[0], choice.focal) > REAIM_UNITS or aimed[1] != here
                if stale and not busy_hand:
                    where = aim_in_view(player, choice.focal, aspect)
                    if where is None:
                        ended = f'Nothing in view to aim at ({label(prey)} is off the screen)'
                        break
                    run.actuator.aim(*where, scatter=(3, 3))
                    aimed = (choice.focal, here)
                    hand = (run.actuator.keys.pointer(), hand[1])  # put there by the macro: no news of the hand
                if again is None:
                    run.say(f'Echoing Strike ({how}) at {label(prey)}, {life(prey)}')
                    again = stack.enter_context(run.actuator.hold(*held))
                    began = run.clock()
                    self.casting = True  # the strike is held from here to the end of the fight
                if prey.unit_id != lined:
                    lined = prey.unit_id
                    LOG.info(
                        'Macro: line through %s, %s, %.1f away, focal (%.1f, %.1f), worth %.0f, pointer %s',
                        label(prey), life(prey), math.dist(here, (prey.x, prey.y)), *choice.focal, choice.worth,
                        run.actuator.keys.pointer(),
                    )  # fmt: skip
                watched |= {m.unit_id for m in reachable}
                if self.nap(run, FRAME):
                    ended = 'Yielded (a move was asked for)'
                    break
        down += len(watched - {m.unit_id for m in run.world().monsters})
        seconds = run.clock() - started
        LOG.info('Macro: fight (%s): %d casts seen in %.1fs, %d down; %s', how, casts, seconds, down, ended)
        run.say(f'{ended}: {down} down in {casts} casts')
        if casts:
            run.say(f'Last minute: {self.score.line()}')  # the HUD card's standing line between fights

    def sigil(self, run: Run, world: World, prey: Monster, aspect: float, key_names) -> None:
        """Sigil: Lethargy on the ground under an elite (slows it, lowers its defence)."""
        assert world.player is not None
        run.keys.update(key_names(world, (SIGIL_LETHARGY,)))
        where = ground_fraction(world.player, prey.x, prey.y, aspect)
        if not on_screen(where):
            # Off the screen (the blades reach further than it shows): no sigil now, asked again in a second.
            self.sigiled[prey.unit_id] = run.clock() - SIGIL_SECONDS + 1.0
            return
        run.actuator.aim(*where, scatter=(4, 3))
        press_skill(run, SIGIL_LETHARGY)
        self.sigiled[prey.unit_id] = run.clock()
        run.pause('key')

    def death_mark(self, run: Run, target: Monster, aspect: float, key_names) -> None:
        """Death Mark on `target`: the pointer on its body, then the key (Quick Cast)."""
        world = run.world()
        if world.player is None:
            raise Abort('not in a game')
        run.keys.update(key_names(world, (DEATH_MARK,)))
        point = screen_fraction(world.player, target.x, target.y, aspect)
        if not on_screen(point):
            return
        run.actuator.aim(*point, scatter=(3, 3))
        press_skill(run, DEATH_MARK)
        self.marked_at = run.clock()
        run.say(f'Death Mark on {label(target)}, {life(target)}')
        run.pause('key')


def aim_in_view(player, focal: tuple[float, float], aspect: float) -> tuple[float, float] | None:
    """Where to put the pointer for a cast at `focal` (window fractions): the focal point's ground, or,
    when that is off the screen, the furthest point of the same line that is on it (the blades fly
    their 22 units along the line whatever the focal distance; only where they meet moves)."""
    dx, dy = focal[0] - player.x, focal[1] - player.y
    for share in (1.0, 0.85, 0.7, 0.55, 0.4, 0.25):
        where = ground_fraction(player, player.x + dx * share, player.y + dy * share, aspect)
        if on_screen(where):
            return where
    return None


def walk_to(run: Run, goal, player, aspect: float, name: str) -> None:
    """A click on the ground at `goal` (world units): the character walks there."""
    where = ground_fraction(player, goal[0], goal[1], aspect)
    if not in_view(where):
        raise Abort(f'the spot near {name} is not in view')
    run.say(f'Walking {math.dist((player.x, player.y), goal):.0f} toward {name}')
    # A click made while attack mode's last cast ends is swallowed (host, 19:40 on 2026-10-10: "Walking 7",
    # "the character did not move"): the character is waited free first and the click made twice at most.
    for _ in range(WALK_CLICKS):
        settle(run)
        run.actuator.aim(*where, scatter=(4, 3))
        run.actuator.click()
        if run.seen(lambda w: w.player is not None and moved(w.player, player), WALK_SECONDS) is not None:
            return
    raise Abort('the character did not move')
