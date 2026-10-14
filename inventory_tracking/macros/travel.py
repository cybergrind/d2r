"""One move of the hunt's own (macros/hunt.py): a step to a place, made by a jump or by one click's walk.

`Step` is the order: where to, and the skill it is jumped by (None: a walk); it is defined with the
contracts (macros/build.py) and named here as before. The choice of a move is pure, made from
`MoveFacts` and the jumps the character can make now: a straight stride toward a goal (`stride_of`)
and the walked way round a wall (`around_of`), each with the reason when there is none (`NoWay`).
Which jumps those are is a movement set's answer (macros/movement.py for the shared sets; a build
adds its own): the build's sets are handed to `Travel`, which asks the first that applies
(`navigator`) with the facts as they are now (`move_facts`) and within the caller's intent
(`PLAYER_STEP`, `SEEK`, `OWN_MOVE`), remembers the jumps made and failed, and makes a step by the way
it names (`make`). The place itself is chosen in combat/stance.py (`camp`), priced by these jumps.

The intents and the navigator are here and not with the sets because `Travel` asks by them and the
sets are built on the choice below: movement.py imports this module, not the other way round.
"""

import heapq
import math
import statistics
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass, field, replace
from functools import lru_cache, partial

from inventory_tracking.combat.stance import Camp, Jump, no_footing, way
from inventory_tracking.common import LOG
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Room, Target, Walkable
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import Intent, Leg, MoveFacts, MovementSet, NoWay, Step, nowhere
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import ACTING, DEAD, ONE_CAST, SWAP_SETTLE, press_skill, settle
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.skills import TELEPORT, skill_name
from inventory_tracking.macros.teleport import (
    HOVER_SECONDS,
    MOVED,
    Covered,
    ground_fraction,
    hop_to,
    in_view,
    landed_from,
    moved,
)
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import NO_OWNER, Monster, Player, Teleport, World
from inventory_tracking.native.layout import TILE_UNITS


MONSTER_UNIT_TYPE = 1  # the unit type of a monster, alive or dead, in the record of what is under the pointer
STRIDE = 16.0  # units of one stride: the click has to be in view
# A walk is a click; the character must be seen moving within STEP_WALK_SECONDS.
STEP_WALK_SECONDS = 0.7
# A hurried walk (`step_walk` `hurry`): its first click is made at the first look that reads the cast over (one poll
# free, not the settle's 0.2 s), and when the character is not seen going within HURRY_SECONDS of it the game took no
# notice (a click as a cast ends is swallowed now and then): it is made again, settled. Live, the click to the
# character seen going takes under 0.1 s (a free walk's leg 0.25-0.29 s, p10-p90, of which the aim, the hover and
# the press are some 0.2 s; rca/2026-10-14/diablo-handling.md fix 3); the arena's 0.11 s.
HURRY_FREE = 0.02
HURRY_SECONDS = 0.3
HOVER_UNITS = 12.0  # a monster named as under the pointer stands this near the ground aimed at, or is not there
# A stride is a jump when a skill makes one without a weapon swap: Blade Warp first (skills.txt 390, a casting
# delay of 20 frames, spends no charges), else Teleport when in hand or a skill of the character's own (Enigma).
JUMP_REACH = 26.0  # units of a jump: in view, and within the blade's range
JUMP_LEAST = 8.0  # a stride shorter than this is walked
JUMP_SECONDS = 1.5  # for the character to be seen somewhere else after the key
# A jump's casting delay (`JumpSource.delay`) as the game shows it: the character's state 185 (world.py
# `Player.cooldown`) is set at the cast's action frame and cleared when the delay is over. Blade Warp in the
# four takes of 21:42 on 2026-10-13, 123 keys counted from the key's down: set after 0.17 to 0.24 s (p10 to p90;
# p99 0.35, the most 0.40), cleared after 0.96 to 1.03 s (p50 1.00; p99 1.09 in a clean take, 1.17 with the
# recorder starved or the cast begun late). A key before the clear is refused (36 of 46 keys 0.8 to 1.0 s after
# the one before, 2026-10-11 to 13). With the state read a jump's key waits for the clear (`Travel.left`): a clear
# state DELAY_SHOWN after the key is the delay over, before that it is a cast that has not thrown yet.
DELAY_SHOWN = ONE_CAST  # no cast lasts longer, and every state above was set by then
DELAY_STALE = 2.5  # seconds after its key a delay state still set is not that key's: the clock decides
DELAY_TICK = 0.04  # a delay state still set ends at the next game tick at the soonest
ROUNDING = 1e-6  # seconds: a sum of clock times this near a floor has reached it (a float's rounding, no more)
# With no state read the delay is timed by the clock from the key's release, the rule before the state was read
# (`JumpSource.delay`; 2 keys refused of 296, 2026-10-11 to 13). Counted from the key's down it would refuse some:
# 1.05 s is under the clear's p99 above.
# An intent that may wait a casting delay out (`Intent.may_wait`) is offered the jump PLAN_AHEAD seconds before
# its delay is over: the look and the choice of the leg are made while it runs (130 to 150 ms in a clean game,
# 500 to 770 under load: rca/2026-10-13/latency-findings.md §2.2), and the jump holds its key, the pointer on the
# aim, until it is (`Travel.delay_over`). The jump is the one priced: no other leg is made in its place.
PLAN_AHEAD = 0.25
KEY_POLL = 0.02  # seconds between the light looks that wait for a delay's end (a tick is 0.04), or for a throw
# Pixels: a pointer the macro put within this of a jump's aim (during the flight before: `Travel.aim_ahead`) is
# put on it in one step (`Actuator.aim` `near`). A landing is off its aim by 1.0 units at the median, 2.6 at p90.
NEAR_AIM = 120
REAIM = 0.5  # units the character moved while a jump waited for its delay that have the pointer put again
LEG_GAP = 2.5  # seconds: two moves further apart than this are not legs of one travel (`Tally`)
# Charges of the Teleport staff the mode's own moves leave alone (user, 2026-10-11: "track number of tp
# charges when using staff, and leverage warp more when low on charges"): under it the sweep
# does not jump by Teleport, and the seek step goes by Blade Warp or a walk where one leads on. The
# player's own teleport step spends them to the last. A staff of 69 came to 2 clearing a level after
# Nihlathak (15:10 that day); some 20 are needed to reach him.
LOW_CHARGES = 10
JUMP_DISTRUST = 30.0  # seconds a way of jumping that did not move the character is left alone
WARP_CHARGES = 15  # with fewer charges on the staff the teleport step hops by Blade Warp where it can
WARP_RETRY = 3.0  # seconds the teleport step leaves Blade Warp alone after one that moved nobody
# The walked way round a wall (`Travel.around`), for a staff with no charge left: Dijkstra over the
# walkable unit cells within AROUND_REACH of the character, AROUND_DETOUR times the straight line at most.
AROUND_REACH = 70
AROUND_DETOUR = 4.0
AROUND_LEAST = 3.0  # units a move along that way has to make
NEIGHBOURS = tuple((dx, dy, math.hypot(dx, dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
NO_ASPECT = 0.0  # the window's shape in facts asked only for the jumps: not read
Point = tuple[float, float]


# What the caller of a move allows, one for each kind of caller (architecture.md 4.3). A movement set
# reads `reserve`, `distrust`, `may_wait`, `waits_blind`, `short`, `shot`, `shuns` and `detour`; the
# rest say what the caller itself does around the set's answer (hunt.py `afoot`, `warp_hop`), which
# is not one `leg`: `sparing` and `walks_under` there, and `may_swap`, which only tells that the
# caller's own hop (teleport.py `take_teleport`) changes the weapon set where a set's jump never does.
# Every one of them asks a set's own jumps with the same floor of charges, LOW_CHARGES: the charges
# the player's step spends to the last are spent by its Teleport hop (teleport.py `hop_toward`), which
# no set makes.
#
# The sweep and the choice of a place to stand: no wait, no swap, a straight stride only.
OWN_MOVE = Intent(
    'own move', reserve=LOW_CHARGES, may_swap=False, may_wait=False, distrust=JUMP_DISTRUST, sparing=math.inf
)
# Safety asks for alternatives with every currently usable means, including a
# charged set on the back. The caller prices the swap before authorizing a leg.
SAFE_MOVE = replace(OWN_MOVE, name='priced move', may_swap=True, reserve=1)
# The seek step (hunt.py `afoot`): a casting delay is waited out where the line toward the goal is
# clear, and with fewer than LOW_CHARGES a walk too comes before the hop.
SEEK = Intent(
    'seek',
    reserve=LOW_CHARGES,
    may_swap=True,
    may_wait=True,
    distrust=JUMP_DISTRUST,
    sparing=math.inf,
    walks_under=LOW_CHARGES,
)
# The player's own teleport step (hunt.py `warp_hop`, `empty_hop`): under WARP_CHARGES a jump that
# spares the staff comes first, one that moved nothing is tried again after WARP_RETRY, a walk is
# made only with the staff empty, and a casting delay is waited out with the line looked at by the caller.
PLAYER_STEP = Intent(
    'player step',
    reserve=LOW_CHARGES,
    may_swap=True,
    may_wait=True,
    distrust=WARP_RETRY,
    sparing=WARP_CHARGES,
    walks_under=1,
    waits_blind=True,
)
# A goal the character is to get to, however far (`Intent.routed`: rca/2026-10-13/kp4-findings.md §6), as
# the pursuit loop asks for it (macros/pursuit.py). The set answers by its own way there: no caller hops
# for it, so here the charges the key spends to the last are the set's to spend (`reserve` 1) and the
# staff is swapped in for a hop that needs it.
#
# The key's own goal: as PLAYER_STEP, the charges spent to the last.
PRESSED = Intent(
    'pressed goal',
    reserve=1,
    may_swap=True,
    may_wait=True,
    distrust=WARP_RETRY,
    sparing=WARP_CHARGES,
    walks_under=1,
    routed=True,
)
# The goal attack mode goes to by itself (a boss out of reach): as OWN_MOVE, no swap and the staff's
# last LOW_CHARGES kept, but a casting delay about to end is waited out: nothing is struck meanwhile.
STANDING = Intent(
    'standing goal',
    reserve=LOW_CHARGES,
    may_swap=False,
    may_wait=True,
    distrust=JUMP_DISTRUST,
    sparing=math.inf,
    routed=True,
)

# Why a stride or a way round has no move (`NoWay.reason`), one for each way there is none.
THERE = 'the character is as near the goal as the move was to end'  # the one that is an arrival
SHUNNED = 'the place a stride toward the goal ends at is shunned'
UNSEEN = 'the end of a walk toward the goal is not in view'
WALLED = 'no straight walk leads toward the goal: a wall in the line, or no footing at its end'
NO_SHOT = 'a few units up to a wall the goal stands behind: the firing spot is to find'
OPEN_GROUND = 'no wall or closed door is known: there is no way round to look for'
NO_WAY_ROUND = 'no walked way leads nearer the goal'
NO_SPOT_ON_WAY = 'no spot on the walked way is in view and reached by a jump over a clear line or one straight walk'
NO_SET = 'no movement set of the build is for the character as it is now'
WAY_UNKNOWN = 'no walked way to the goal is known (its ground is not read, or nothing leads there)'
NO_NEARER = 'the move found brings the goal no nearer by the way'
# The walked way to a far goal (`Walked`). A cell beside a barred one counts HUG times its length: a
# click's walk and a thrown jump end only where the cells around are free (`way`, `stride_of`), and the
# shortest way hugs every corner it turns, so without it the way's own cells are places no move may end at.
HUG = 2.0
GOAL_CELLS = 8  # cells round a goal a walkable one is looked for in: an object stands on cells nobody walks on


def navigator(sets: Sequence[MovementSet], facts: MoveFacts) -> MovementSet | None:
    """The movement set to ask now: the first of a build's that applies to the facts; None when none
    does. The one way to a set: `leg`, `eta`, `jumps` and `wait` are asked of no other."""
    return next((movement for movement in sets if movement.applies(facts)), None)


def spare_jump(sets: Sequence[MovementSet], slots: Sequence[int | None]) -> Jump | None:
    """The jump of a build's own that spares the staff: the first of its sets' jumps that is not
    Teleport and is on a key, whatever the facts otherwise (its casting delay, a failure). None: the
    build has none, or it is on no key. A jump that is not Teleport is taken to cost no charge."""
    return next(
        (
            source.jump
            for movement in sets
            for source in movement.sources
            if source.jump.skill != TELEPORT and source.jump.skill in slots
        ),
        None,
    )


def move_facts(
    run: Run,
    world: World,
    ground: Ground | None,
    aspect: float,
    travel: Travel,
    rooms: tuple[Room, ...] = (),
    *,
    lead: float = 0.0,
) -> MoveFacts:
    """What a move is chosen from, read once: where the character stands, the clock, the skills on
    keys, the worn staff, the level, and `travel`'s memory of the jumps made and failed. No staff
    reader (`run.teleport` None) and a staff that is not there or cannot be read are the same fact,
    `staff=None`: Teleport, if it is in a slot, is taken as a skill of the character's own. `lead`:
    seconds before a casting delay is over that its jump counts as ready (`ahead_of`)."""
    # The staff is read only with Teleport on a key, as before the facts were (a read of the worn
    # items on every stride would be a new cost in the game's loop): without it no jump asks for it.
    staff = run.teleport() if run.teleport is not None and TELEPORT in world.slots else None
    return facts_with(run, world, ground, aspect, travel, staff, rooms, lead=lead)


def ahead_of(intent: Intent) -> float:
    """Seconds before a casting delay is over that a jump counts as ready for a move within `intent`:
    PLAN_AHEAD where the intent may wait a delay out, else none (`Travel.jump` holds the key till then)."""
    return PLAN_AHEAD if intent.may_wait else 0.0


def facts_with(
    run: Run,
    world: World,
    ground: Ground | None,
    aspect: float,
    travel: Travel,
    staff: Teleport | None,
    rooms: tuple[Room, ...] = (),
    *,
    lead: float = 0.0,
) -> MoveFacts:
    """`move_facts` with the worn staff as the caller has it (read a moment ago, or None): the clock
    is read, the staff is not. A staff counts only with Teleport on a key, as in `move_facts`."""
    player = world.player
    assert player is not None
    now = run.clock()
    return MoveFacts(
        here=(player.x, player.y),
        now=now,
        slots=world.slots,
        staff=staff if TELEPORT in world.slots else None,
        ground=ground,
        doors=world.doors,
        aspect=aspect,
        last_used=travel.counted(now, player.cooldown, lead),
        failed=dict(travel.jump_failed),
        area=player.area,
        rooms=rooms,
        distrusted=dict(travel.distrusted),
        pad=run.pad is not None,
    )


def known(ground: Ground | None) -> Ground:
    """The level as a line is tested over it; not known, a level with no wall read: only a closed door bars."""
    return ground if ground is not None else Ground(())


def stride_of(
    facts: MoveFacts,
    goal: Point,
    short: float = 0.0,
    shot: bool = False,
    shuns: Callable[[Point], bool] = nowhere,
    *,
    jumps: Sequence[Jump] = (),
) -> Leg:
    """A stride straight toward `goal`, to end `short` of it: a jump of up to JUMP_REACH when the
    character can make one (the first of `jumps`, the ones it can make now: a movement set's answer),
    else a walk of STRIDE; onto footing, in view, and not to a place a step failed for. With `shot` a
    short walk has to end with a clear shot at the goal. With no such stride, the reason: THERE (an
    arrival; a goal nearer than `short` too), else what is in the way.

    One jump is asked for, the first, and the stride never falls to the next: with a wall in the line
    of a jump that needs a clear one the stride is walked, or has no way."""
    here = facts.here
    ground = known(facts.ground)
    view = Viewport(facts.aspect)
    away = math.dist(here, goal)
    barred = no_footing(ground, facts.doors)

    def at(stride: float) -> Point:
        return (here[0] + (goal[0] - here[0]) * stride / away, here[1] + (goal[1] - here[1]) * stride / away)

    def footed(spot: Point) -> bool:
        return in_view(view.ground(here, spot[0], spot[1])) and (
            barred is None or not any(barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        )

    if away - short < MOVED:
        return NoWay(THERE, arrived=True)
    if shuns(at(min(away - short, STRIDE))):
        return NoWay(SHUNNED)
    jump = next(iter(jumps), None)
    # The jump's own reach as well: a jump of one length in controller mode (macros/pad.py) has a least near it.
    least = max(JUMP_LEAST, jump.least) if jump is not None else JUMP_LEAST
    if jump is not None and away - short >= least:
        longest = min(away - short, JUMP_REACH, jump.reach)
        for stride in (longest, longest * 0.75, longest * 0.5):
            spot = at(stride)
            if stride < least or not footed(spot):
                continue
            if jump.line and not clear_shot(ground, here, spot, facts.doors):
                continue  # the blade flies there: no wall in its way
            return Step(spot, jump.skill)
    stride = min(away - short, STRIDE)
    spot = at(stride)
    if not in_view(view.ground(here, spot[0], spot[1])):
        return NoWay(UNSEEN)
    if not way(barred, here, spot):
        return NoWay(WALLED)
    if shot and stride < STRIDE / 2 and not clear_shot(ground, spot, goal, facts.doors):
        return NoWay(NO_SHOT)  # a few units up to a wall it stands behind: the firing spot's to find
    return Step(spot)


def around_of(facts: MoveFacts, goal: Point, *, jumps: Sequence[Jump] = ()) -> Leg:
    """A move along the walked way to `goal` when no straight stride leads there (a wall in the
    line): the shortest way over walkable ground, and on it the furthest spot a Blade Warp flies to
    over a clear line, else the furthest one click's straight walk reaches. With no such way, the reason.
    The jump is the first of `jumps` (the ones the character can make now) and only when that one
    flies a clear line: a first jump that needs none is not made along the way, which is then walked.
    Drifter Cavern, 09:43 on 2026-10-12 (user: "KP_1 got stuck when I'm out of tp charges, probably
    we should switch to walk/blade warp routes calculation"): the staff empty, the firing spot 26
    units off behind a wall, and thirteen presses each ended with "no Blade Warp or walk leads"."""
    here = facts.here
    ground = known(facts.ground)
    view = Viewport(facts.aspect)
    barred = no_footing(ground, facts.doors)
    if barred is None:
        return NoWay(OPEN_GROUND)
    path = walked_way(barred, here, goal)
    if not path:
        if (math.floor(here[0]), math.floor(here[1])) == (math.floor(goal[0]), math.floor(goal[1])):
            return NoWay(THERE, arrived=True)  # on the goal's cell: the way has no step
        return NoWay(NO_WAY_ROUND)
    jump = next(iter(jumps), None)
    if jump is not None and jump.line:
        for spot in reversed(path):
            away = math.dist(here, spot)
            if not max(JUMP_LEAST, jump.least) <= away <= min(JUMP_REACH, jump.reach):
                continue  # within the jump's own reach as well: one length in controller mode (macros/pad.py)
            if not in_view(view.ground(here, *spot)):
                continue
            if clear_shot(ground, here, spot, facts.doors) and not any(
                barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            ):
                return Step(spot, jump.skill)
    for spot in reversed(path):
        away = math.dist(here, spot)
        seen = in_view(view.ground(here, *spot))
        if AROUND_LEAST <= away <= STRIDE and seen and way(barred, here, spot):
            return Step(spot)
    return NoWay(NO_SPOT_ON_WAY)


class Walked:
    """The walked way to a goal from any cell of the level: Dijkstra outward from the goal's cell over
    cells that are not barred (eight neighbours, no corner cut, a cell beside a wall HUG times as long),
    grown only as far as it is asked for and kept for the next asking. `left` is the way left from a
    point; `descent` the cells of the way from it. What `walked_way` is for a place a move away, this is
    for a goal at any distance: the measure a character on foot gets nearer by (13:05 on 2026-10-13: the
    seal 286 units off in a straight line and 318 by the walked way, which led north out of the wing
    while every move went west into its pocket)."""

    def __init__(self, barred: Callable[[Point], bool], goal: Point) -> None:
        self.barred = barred
        self.bars: dict[tuple[int, int], bool] = {}
        self.hugs: dict[tuple[int, int], bool] = {}
        last = (math.floor(goal[0]), math.floor(goal[1]))
        around = [
            (last[0] + dx, last[1] + dy)
            for dx in range(-GOAL_CELLS, GOAL_CELLS + 1)
            for dy in range(-GOAL_CELLS, GOAL_CELLS + 1)
        ]
        free = [cell for cell in around if not self.bar(cell)]
        self.cost: dict[tuple[int, int], float] = {}
        self.settled: set[tuple[int, int]] = set()
        self.queue: list[tuple[float, tuple[int, int]]] = []
        if free:
            root = min(free, key=lambda cell: math.dist((cell[0] + 0.5, cell[1] + 0.5), goal))
            self.cost[root] = 0.0
            self.queue.append((0.0, root))

    def bar(self, cell: tuple[int, int]) -> bool:
        known = self.bars.get(cell)
        if known is None:
            known = self.bars[cell] = bool(self.barred((cell[0] + 0.5, cell[1] + 0.5)))
        return known

    def hug(self, cell: tuple[int, int]) -> bool:
        """Whether a barred cell is beside this one."""
        known = self.hugs.get(cell)
        if known is None:
            known = self.hugs[cell] = any(self.bar((cell[0] + dx, cell[1] + dy)) for dx, dy, _ in NEIGHBOURS)
        return known

    def grow(self, cell: tuple[int, int]) -> None:
        """Settle cells outward from the goal until `cell` is settled or nothing is left to reach."""
        cost, queue, settled = self.cost, self.queue, self.settled
        while queue and cell not in settled:
            gone, at = heapq.heappop(queue)
            if at in settled:
                continue
            settled.add(at)
            for dx, dy, step in NEIGHBOURS:
                near = (at[0] + dx, at[1] + dy)
                if near in settled or self.bar(near):
                    continue
                if dx and dy and (self.bar((at[0] + dx, at[1])) or self.bar((at[0], at[1] + dy))):
                    continue
                further = gone + step * (HUG if self.hug(near) else 1.0)
                if further < cost.get(near, math.inf):
                    cost[near] = further
                    heapq.heappush(queue, (further, near))

    def of(self, cell: tuple[int, int]) -> float:
        """The way left from a cell; inf: none leads from it."""
        self.grow(cell)
        return self.cost[cell] if cell in self.settled else math.inf

    def foot(self, point: Point) -> tuple[int, int] | None:
        """The cell the way from `point` begins on: its own, or (the character stands on cells the
        grids call unwalkable now and then) the neighbour with the shortest way left. None: no way."""
        cell = (math.floor(point[0]), math.floor(point[1]))
        if not self.bar(cell):
            return cell if self.of(cell) < math.inf else None
        beside = [(cell[0] + dx, cell[1] + dy) for dx, dy, _ in NEIGHBOURS]
        free = [near for near in beside if not self.bar(near) and self.of(near) < math.inf]
        return min(free, key=self.of) if free else None

    def left(self, point: Point) -> float:
        """Units of the walked way left from `point` (a cell beside a wall counted HUG times); inf: no way."""
        cell = self.foot(point)
        return math.inf if cell is None else self.of(cell)

    def descent(self, point: Point, reach: float) -> list[tuple[Point, float]]:
        """The way from `point` toward the goal as (cell centre, way left from it), from the first step on,
        as far as `reach` units from `point` in a straight line. Empty: no way, or already on the goal's cell."""
        cell = self.foot(point)
        found: list[tuple[Point, float]] = []
        while cell is not None and self.cost[cell] > 0.0:
            best = None
            for dx, dy, _ in NEIGHBOURS:
                near = (cell[0] + dx, cell[1] + dy)
                if near not in self.settled or self.cost[near] >= self.cost[cell]:
                    continue
                if dx and dy and (self.bar((cell[0] + dx, cell[1])) or self.bar((cell[0], cell[1] + dy))):
                    continue
                if best is None or self.cost[near] < self.cost[best]:
                    best = near
            if best is None:
                break
            cell = best
            centre = (cell[0] + 0.5, cell[1] + 0.5)
            if math.dist(point, centre) > reach:
                break
            found.append((centre, self.cost[cell]))
        return found


@lru_cache(maxsize=4)
def walked_over(grids: tuple[Walkable, ...], closed: tuple[Door, ...], goal: tuple[int, int]) -> Walked | None:
    """The walked way to the goal's cell over a level's ground, kept across looks: the ground and the
    goal rarely change between two of them. None on ground with no wall and no closed door."""
    barred = no_footing(Ground(grids), closed)
    return None if barred is None else Walked(barred, (goal[0] + 0.5, goal[1] + 0.5))


def walked_for(facts: MoveFacts, goal: Point) -> Walked | None:
    """`walked_over` for the facts' ground and closed doors; None: open ground, any straight line is a way."""
    grids = facts.ground.grids if facts.ground is not None else ()
    closed = tuple(door for door in facts.doors if door.closed)
    return walked_over(grids, closed, (math.floor(goal[0]), math.floor(goal[1])))


def way_left(facts: MoveFacts, goal: Point) -> float:
    """Units of the way left to `goal` on foot: by the walked way where the level has walls (inf: none
    is known), the straight line on open ground."""
    field = walked_for(facts, goal)
    return math.dist(facts.here, goal) if field is None else field.left(facts.here)


def way_leg(facts: MoveFacts, goal: Point, intent: Intent, *, jumps: Sequence[Jump] = ()) -> Leg:
    """The next move along the walked way to a goal at any distance (`Intent.routed`), to end
    `intent.short` of it: on the way's next cells the furthest one the first of `jumps` reaches (over a
    clear line, for one that needs it), else the furthest one click's straight walk reaches. Every spot
    of the way has less of it left than where the character stands, so a move given here always brings
    the goal nearer on foot. On open ground the way is the straight stride (`stride_of`)."""
    here = facts.here
    if math.dist(here, goal) - intent.short < MOVED:
        return NoWay(THERE, arrived=True)
    field = walked_for(facts, goal)
    if field is None:
        return stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=jumps)
    left = field.left(here)
    if left == math.inf:
        return NoWay(WAY_UNKNOWN)
    whole = field.descent(here, JUMP_REACH)
    path = [(spot, cost) for spot, cost in whole if cost >= intent.short]
    ends = bool(whole) and whole[-1][1] == 0.0  # the way's last cell is in a move's reach
    if not path or (ends and all(math.dist(here, spot) < AROUND_LEAST for spot, _ in path)):
        # The way's end is within `short`, or nearer than a move along the way can be made: there
        return NoWay(THERE, arrived=True)
    ground = known(facts.ground)
    view = Viewport(facts.aspect)
    barred = field.barred

    def shown(spot: Point) -> bool:
        return in_view(view.ground(here, *spot)) and not intent.shuns(spot)

    jump = next(iter(jumps), None)
    if jump is not None:
        for spot, _ in reversed(path):
            away = math.dist(here, spot)
            if not jump.least <= away <= jump.reach or not shown(spot):
                continue
            if any(barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            if not jump.line or clear_shot(ground, here, spot, facts.doors):
                return Step(spot, jump.skill)
    for spot, _ in reversed(path):
        away = math.dist(here, spot)
        if AROUND_LEAST <= away <= STRIDE and shown(spot) and way(barred, here, spot):
            return Step(spot)
    return NoWay(NO_SPOT_ON_WAY)


class Stale(Abort):
    """The character is not where a jump's leg was chosen from any more, found while the jump waited for its
    casting delay to end (`Travel.delay_over`): no key is pressed, and the next look chooses the leg again. Not
    a jump that failed: the way is not distrusted for it."""


class Untaken(Abort):
    """A jump's key the game took no cast for: the character did not move and its delay state was read after the
    key but never set (a cast sets it at its action frame). The key in the skill's cooldown is refused this way
    (run-0305-findings.md §5.1); it began no delay, and the way is not distrusted for it: the jump is made again
    when due. REFUSALS in a row are a failure like any other (a cast the game keeps refusing: no mana, say)."""


REFUSALS = 2


@dataclass
class Thrown:
    """What the looks after a jump's key read of the character's delay state (`Travel.jump`)."""

    read: bool = False  # some look read the state
    set: bool = False  # some look had it set: the game took a cast

    def note(self, world: World) -> bool:
        """Notes one look; True, so that it goes before a look's own test with `and`."""
        player = world.player
        if player is not None and player.cooldown is not None:
            self.read = True
            self.set = self.set or player.cooldown
        return True

    @property
    def untaken(self) -> bool:
        return self.read and not self.set


@dataclass
class Tally:
    """The moves of one level run (KP_1), for its pace: from its first leg (`since`), the units made (a jump
    landed, a walk's stride as clicked), the legs, and the key-to-key seconds of the delayed jumps made one
    after the other (`Travel.jump`'s "leg time" line). Told and begun again when the run ends (`Travel.paced`)."""

    since: float | None = None
    last: float = -math.inf  # the clock at the last leg's start
    units: float = 0.0
    jumps: int = 0
    walks: int = 0
    keys: list[float] = field(default_factory=list)

    def leg(self, now: float) -> None:
        if self.since is None:
            self.since = now
        self.last = now


class Travel:
    """What the character can jump by, and the moves made with it. The choice of a move is a movement
    set's (`sets`: a build's, the first that applies), asked here with the facts as they are now
    (`move_facts`) and within the caller's intent; this holds what a set cannot: the memory of the
    jumps made, and the making."""

    def __init__(self, sets: Sequence[MovementSet] = ()) -> None:
        self.sets = tuple(sets)  # the build's movement sets: the first that applies is the one asked
        # The skills with a casting delay and its seconds: the last jump by one of them is remembered
        self.delays = {
            source.jump.skill: source.delay for movement in self.sets for source in movement.sources if source.delay
        }
        self.delayed = frozenset(self.delays)
        # -> seconds from the key before which a clear delay state is not the delay over (`JumpSource.cleared`)
        self.cleared = {
            source.jump.skill: source.cleared for movement in self.sets for source in movement.sources if source.delay
        }
        self.refusals: dict[int, int] = {}  # skill -> keys in a row the game took no cast for (`jump`)
        self.jumped_at: dict[int, float] = {}  # skill with a casting delay -> clock time its last key went down
        self.released_at: dict[int, float] = {}  # -> the clock time that key came up (the clock's rule, `left`)
        self.jump_failed: dict[int, float] = {}  # skill -> clock time a jump by it last moved nothing
        # A way a set said leads nowhere (`NoWay.distrust`) -> the clock time it said so (`toward`)
        self.distrusted: dict[Hashable, float] = {}
        self.landed_at: dict[int, float] = {}  # skill -> the clock when its last jump was seen landed
        self.tally = Tally()  # the level run's moves (`paced`)

    @property
    def warped_at(self) -> float:
        """Clock time of the last jump by a skill that has a casting delay; -inf with none made."""
        return max(self.jumped_at.values(), default=-math.inf)

    @warped_at.setter
    def warped_at(self, at: float) -> None:
        """Every skill with a casting delay was last jumped by at `at` (a test's way to the state)."""
        self.jumped_at = dict.fromkeys(self.delayed, at)
        self.released_at = {}

    def left(self, skill: int, now: float, cooldown: bool | None) -> float:
        """Seconds of the skill's casting delay still to run; 0 or less (-inf: known over), none. By the
        character's delay state where the look read it (`cooldown`, world.py `Player.cooldown`): clear
        DELAY_SHOWN after the key and no sooner than the skill's `cleared` after it, over (the state clears a
        tick or so before the game takes the next cast: run-0305-findings.md §5.1); set, it ends no sooner
        than the delay from the key's down nor before the next tick. With the state unread, or set
        DELAY_STALE after the key (not this key's), by the clock from the key's release (or from the key,
        when no release was recorded)."""
        keyed, delay = self.jumped_at.get(skill), self.delays.get(skill, 0.0)
        if keyed is None or not delay:
            return -math.inf
        since = now - keyed
        if cooldown is None or since >= DELAY_STALE:
            return self.released_at.get(skill, keyed) + delay - now
        if cooldown:
            return max(delay - since, DELAY_TICK)
        if since < DELAY_SHOWN:
            return delay - since
        floor = self.cleared.get(skill, 0.0) - since
        return -math.inf if floor <= ROUNDING else floor

    def counted(self, now: float, cooldown: bool | None, lead: float = 0.0) -> dict[int, float]:
        """`MoveFacts.last_used` for a choice made now with the delay state `cooldown`: for each skill keyed, the
        clock time its delay counts from, so that a set reads it as over (`JumpSource.ready`) `lead` seconds
        before `left` does. A skill whose delay the state says is over is left out; one timed by the clock
        counts from its key's release (from its key as recorded where none was: a test's `warped_at`)."""
        found: dict[int, float] = {}
        for skill, keyed in self.jumped_at.items():
            delay = self.delays.get(skill, 0.0)
            if cooldown is None or not delay or now - keyed >= DELAY_STALE:
                found[skill] = self.released_at.get(skill, keyed) - lead
                continue
            left = self.left(skill, now, cooldown)
            if left > -math.inf:
                found[skill] = now - delay + left - lead
        return found

    def leg(self, run: Run, world: World, ground: Ground | None, aspect: float, goal: Point, intent: Intent) -> Leg:
        """The next move toward `goal` within `intent`, by the set that applies to the facts as they
        are now; with no such set, that reason."""
        facts = move_facts(run, world, ground, aspect, self, lead=ahead_of(intent))
        movement = navigator(self.sets, facts)
        return NoWay(NO_SET) if movement is None else movement.leg(facts, goal, intent)

    def options(
        self, run: Run, world: World, ground: Ground | None, aspect: float, goal: Point, intent: Intent
    ) -> tuple[Step, ...]:
        """Each usable jump and the walk, separately, for the safety arbiter to price.

        A preferred jump must not hide a faster escape by another means. A set
        on the back is offered only when a swap is allowed; no input is made.
        """
        facts = move_facts(run, world, ground, aspect, self, lead=ahead_of(intent))
        if intent.may_swap and facts.staff is not None:
            facts = replace(facts, staff=replace(facts.staff, in_hand=True))
        movement = navigator(self.sets, facts)
        jumps = () if movement is None else movement.jumps(facts, intent)
        found: dict[tuple, Step] = {}
        for offered in (*((jump,) for jump in jumps), ()):
            step = stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=offered)
            if isinstance(step, Step):
                found[step.spot, step.skill] = step
        return tuple(found.values())

    def asked(self, facts: MoveFacts, goal: Point, intent: Intent) -> tuple[MoveFacts, MovementSet | None, Leg]:
        """The set for `facts` and its `leg` toward `goal`, asked again while the set names a way of its
        own that gave nothing from here (`NoWay.distrust`): that is remembered, and the set then goes by
        its next. With the facts as they were asked last."""
        movement = navigator(self.sets, facts)
        if movement is None:
            return facts, None, NoWay(NO_SET)
        found = movement.leg(facts, goal, intent)
        while isinstance(found, NoWay) and found.distrust is not None and found.distrust not in facts.distrusted:
            self.distrusted[found.distrust] = facts.now
            facts = replace(facts, distrusted=dict(self.distrusted))
            found = movement.leg(facts, goal, intent)
        return facts, movement, found

    def toward(
        self,
        run: Run,
        world: World,
        ground: Ground | None,
        aspect: float,
        goal: Point,
        intent: Intent,
        rooms: tuple[Room, ...] = (),
    ) -> Leg:
        """The one way to a move toward a goal the character is to get to (`Intent.routed`): the next
        move by the means in hand now, as the set that applies gives it by its own way there, or the
        reason there is none. `goal` is the goal's own place, never a place worked out for one means;
        `rooms`: the level's, for a set that plans over them."""
        return self.asked(move_facts(run, world, ground, aspect, self, rooms, lead=ahead_of(intent)), goal, intent)[2]

    def eta(
        self,
        run: Run,
        world: World,
        ground: Ground | None,
        aspect: float,
        goal: Point,
        intent: Intent,
        rooms: tuple[Room, ...] = (),
    ) -> float:
        """Seconds to `goal` by the means in hand now (`MovementSet.eta`): what progress toward a goal
        is measured by. inf where `toward` has no way."""
        facts = move_facts(run, world, ground, aspect, self, rooms, lead=ahead_of(intent))
        facts, movement, found = self.asked(facts, goal, intent)
        if movement is None or (isinstance(found, NoWay) and not found.arrived):
            return math.inf
        return movement.eta(facts, goal, intent)

    def pause(
        self,
        run: Run,
        world: World,
        ground: Ground | None,
        aspect: float,
        goal: Point,
        intent: Intent,
        rooms: tuple[Room, ...] = (),
    ) -> float:
        """Seconds to let pass before `toward` is asked (`MovementSet.wait`: a casting delay about to
        end on the way the set would take); the game is read again after them. A delay that ends within
        PLAN_AHEAD is not waited out here: the jump waits for it with its key (`ahead_of`, `jump`)."""
        facts = move_facts(run, world, ground, aspect, self, rooms, lead=ahead_of(intent))
        movement = navigator(self.sets, facts)
        return 0.0 if movement is None else movement.wait(facts, goal, intent)

    def stride(
        self, run: Run, world: World, ground: Ground, aspect: float, goal: Point, intent: Intent = OWN_MOVE
    ) -> Step | None:
        """A stride straight toward `goal` within `intent`, which says how far short of it to end
        and what to shun (`stride_of`); None with none, whatever the reason."""
        found = self.leg(run, world, ground, aspect, goal, intent)
        return found if isinstance(found, Step) else None

    def around(
        self, run: Run, world: World, ground: Ground, aspect: float, goal: Point, intent: Intent = OWN_MOVE
    ) -> Step | None:
        """A move along the walked way to `goal` when no straight stride leads there (`around_of`).
        None with no such way."""
        found = self.leg(run, world, ground, aspect, goal, replace(intent, detour=True))
        return found if isinstance(found, Step) else None

    def wait(
        self,
        run: Run,
        world: World,
        ground: Ground | None,
        aspect: float,
        here: Point,
        goal: Point,
        intent: Intent,
        staff: Teleport | None,
    ) -> float:
        """Seconds to let pass before a move from `here` toward `goal` is asked for (`MovementSet.wait`:
        a casting delay about to end). The clock is read; the staff is the caller's (`facts_with`)."""
        facts = replace(facts_with(run, world, ground, aspect, self, staff, lead=ahead_of(intent)), here=here)
        movement = navigator(self.sets, facts)
        return 0.0 if movement is None else movement.wait(facts, goal, intent)

    def jumps(self, run: Run, world: World, intent: Intent = OWN_MOVE) -> tuple[Jump, ...]:
        """The skills a step can be jumped by now without a weapon swap, the preferred first (the
        set's `jumps`): asked without the level or the window, which a list of jumps reads neither of."""
        facts = move_facts(run, world, None, NO_ASPECT, self, lead=ahead_of(intent))
        movement = navigator(self.sets, facts)
        return () if movement is None else movement.jumps(facts, intent)

    def jump_by(self, run: Run, world: World, intent: Intent = OWN_MOVE) -> int | None:
        """The skill a stride can be jumped by now (the first of `jumps`). None: the stride is walked."""
        return next((jump.skill for jump in self.jumps(run, world, intent)), None)

    def jump(
        self,
        run: Run,
        found: Step,
        player,
        aspect: float,
        key_names,
        ahead: Callable[[Point], Point | None] | None = None,
    ) -> None:
        """One jump onto `found.spot` by the skill it names: the pointer on its ground, the skill's casting
        delay waited out with the pointer there (`delay_over`), the key, and the character seen somewhere
        else. `ahead`: the aim of the leg after it from where it lands, for the pointer during the flight
        (`aim_ahead`). What it was aimed at and where it landed goes to the log, and the leg's time (`timed`)."""
        skill = found.skill
        assert skill is not None
        began = run.clock()
        before, before_released = self.jumped_at.get(skill), self.released_at.get(skill)
        cast = Thrown()
        try:
            with run.lightly():  # the key's name needs the skills on keys alone
                run.keys.update(key_names(run.world(), (skill,)))
            # No wait of its own for the cast in flight: `press_skill` waits for the character (with one,
            # 0.39 s went by between the decision and the key at the median, 2026-10-11).
            if run.pad is not None:
                run.pad.aim_place((player.x, player.y), found.spot)  # controller mode: a heading (macros/pad.py)
            else:
                where = ground_fraction(player, found.spot[0], found.spot[1], aspect)
                run.actuator.aim(*where, scatter=(4, 3), near=NEAR_AIM)
            aimed = run.clock()
            # Where the character is at the key: still running from a walk's click, it is not where the leg was
            # chosen from. The aim is put again from there, so that the blade goes to the place chosen, and the
            # landing is told from there (held key's scenes, seed 11: a walk's 2.3 units taken for the landing).
            origin = self.delay_over(run, skill, player) or player
            if run.pad is None and math.dist((origin.x, origin.y), (player.x, player.y)) > REAIM:
                where = ground_fraction(origin, found.spot[0], found.spot[1], aspect)
                run.actuator.aim(*where, scatter=(4, 3), near=NEAR_AIM)
            waited = run.clock()
            keyed = press_skill(run, skill)
            released = run.clock()
            if skill in self.delayed:
                self.jumped_at[skill], self.released_at[skill] = keyed, released
            spot = found.spot
            if ahead is not None and run.pad is None:
                self.aim_ahead(run, keyed, origin, spot, aspect, ahead, cast.note)
            with run.lightly():  # the landing is the character's place: no monster or door is wanted
                landing = run.seen(
                    lambda w: cast.note(w) and w.player is not None and landed_from(w.player, origin, spot),
                    max(released + JUMP_SECONDS - run.clock(), KEY_POLL),
                )
            if landing is None:
                if skill in self.delayed and cast.untaken and self.refusals.get(skill, 0) + 1 < REFUSALS:
                    # The game took no cast for the key (its delay state never set): the key began no delay and
                    # the way is not to distrust; the jump is made again as soon as it is due.
                    self.refusals[skill] = self.refusals.get(skill, 0) + 1
                    self.jumped_at.pop(skill, None)
                    self.released_at.pop(skill, None)
                    if before is not None:
                        self.jumped_at[skill] = before
                    if before_released is not None:
                        self.released_at[skill] = before_released
                    gap = '' if before is None else f' {keyed - before:.3f}s after the key before'
                    LOG.info(
                        'Macro: %s: the game took no cast for the key%s (its delay state never set): '
                        'made again when due', skill_name(skill), gap,
                    )  # fmt: skip
                    raise Untaken(f'{skill_name(skill)}: the character did not move: the game took no cast')
                raise Abort(f'{skill_name(skill)}: the character did not move')
        except Stale, Untaken:
            raise
        except Abort:
            self.jump_failed[skill] = run.clock()
            self.refusals.pop(skill, None)
            raise
        self.refusals.pop(skill, None)
        landed_at = run.clock()
        landed = landing.player
        assert landed is not None
        LOG.info(
            'Macro: %s aimed at (%.1f, %.1f), %.1f from (%.1f, %.1f); landed at (%.1f, %.1f), off by %.1f, '
            '%.2fs after the key',
            skill_name(skill), *found.spot, math.dist((origin.x, origin.y), found.spot), origin.x, origin.y,
            landed.x, landed.y,
            math.dist((landed.x, landed.y), found.spot), landed_at - keyed,
        )  # fmt: skip
        self.tally.units += math.dist((origin.x, origin.y), (landed.x, landed.y))
        self.tally.jumps += 1
        if skill in self.delayed:
            self.timed(skill, before, (began, aimed, waited, keyed, released))
            self.landed_at[skill] = landed_at

    def timed(self, skill: int, before: float | None, marks: tuple[float, float, float, float, float]) -> None:
        """The log's line of a delayed jump made right after the one before ("leg time:", for the next game's
        reading): the seconds from that key's down to this one's and their parts, the flight before (its key
        to its landing seen), the look and the choice of this leg, the aim, the delay waited out with the
        pointer on the aim, and `press_skill`'s wait for the character; and this key's hold."""
        began, aimed, waited, keyed, released = marks
        landed = self.landed_at.get(skill)
        if before is None or landed is None or not before <= landed <= began or keyed - before > LEG_GAP:
            return
        self.tally.keys.append(keyed - before)
        LOG.info(
            'Macro: leg time: %s %.3fs key to key = flight %.3f + look and choice %.3f + aim %.3f + delay wait '
            '%.3f + ready %.3f; hold %.3f',
            skill_name(skill), keyed - before, landed - before, began - landed, aimed - began, waited - aimed,
            keyed - waited, released - keyed,
        )  # fmt: skip

    def delay_over(self, run: Run, skill: int, player: Player) -> Player | None:
        """Wait until the skill's casting delay is over (`left`), looking lightly every KEY_POLL with the
        pointer on the aim, so that the key goes down at the first look that allows it. A key in the delay
        is refused by the game and the jump then moves nobody (2026-10-11 to 13: 36 of 46 such keys). A
        character no longer where the leg was chosen from, or dead, ends the wait without a key: `Stale`.
        Returns the character as the last look saw it; None when no delay was waited for."""
        if skill not in self.delayed or skill not in self.jumped_at:
            return None
        with run.lightly():
            while True:
                seen = run.world().player
                left = self.left(skill, run.clock(), seen.cooldown if seen is not None else None)
                if left <= 0:
                    return seen
                if seen is None or seen.mode in DEAD or moved(seen, player):
                    raise Stale(f'{skill_name(skill)}: the character moved in its delay; the leg is chosen again')
                run.pace.sleep(min(left, KEY_POLL))

    def aim_ahead(
        self,
        run: Run,
        keyed: float,
        player: Player,
        spot: Point,
        aspect: float,
        ahead: Callable[[Point], Point | None],
        note: Callable[[World], bool] = lambda _: True,
    ) -> None:
        """During a jump's flight, the pointer put on the aim of the leg after it as the set would give it
        from the landing (`ahead`, the goal's next jump), once the cast has thrown: the delay state set, or
        DELAY_SHOWN after the key with none read (the place the jump goes to is the pointer's at the cast;
        12:33 on 2026-10-13: the state set 0.17 to 0.23 s after the key). The leg is chosen again from the
        landing; the pointer then has a step to go at most (`Actuator.aim` `near`). The player's hand on the
        mouse stops it: nothing else depends on it. `note`: each look made, to the caller (`Thrown.note`)."""

        def thrown(w: World) -> bool:
            p = w.player
            return note(w) and p is not None and (bool(p.cooldown) or landed_from(p, player, spot))

        with run.lightly():
            run.seen(thrown, max(keyed + DELAY_SHOWN - run.clock(), 0.0), KEY_POLL)
        then = ahead(spot)
        if then is None:
            return
        where = ground_fraction(replace(player, x=spot[0], y=spot[1]), then[0], then[1], aspect)
        if not in_view(where):
            return
        try:
            run.actuator.aim(*where, scatter=(4, 3))
        except Abort:
            if run.cancelled.is_set():
                raise

    def ahead(
        self, run: Run, world: World, ground: Ground | None, aspect: float, landing: Point, goal: Point, intent: Intent
    ) -> Point | None:
        """Where the leg after a jump that lands at `landing` aims, as the set that applies there gives it
        toward `goal` with every delay over, when that leg is a delayed jump again: a guess made during the
        flight, for the pointer alone. None: a walk, a hop or no leg."""
        player = world.player
        assert player is not None
        there = replace(world, player=replace(player, x=landing[0], y=landing[1], cooldown=None))
        facts = replace(move_facts(run, there, ground, aspect, self), last_used={})
        movement = navigator(self.sets, facts)
        found = None if movement is None else movement.leg(facts, goal, intent)
        return found.spot if isinstance(found, Step) and found.skill in self.delayed else None

    def paced(self, now: float | None, why: str) -> None:
        """The level run is over (`why`): its pace to the log ("leg time: level run"), and a new tally begun."""
        tally, self.tally = self.tally, Tally()
        if tally.since is None:
            return
        end = tally.last if now is None else now
        spent = max(end - tally.since, 1e-9)
        keys = f'p50 {statistics.median(tally.keys):.3f}s over {len(tally.keys)}' if tally.keys else 'none'
        LOG.info(
            'Macro: leg time: level run (%s): %.0f units in %.1fs since its first leg, %.1f units/s; %d jumps, '
            '%d walks; key to key %s',
            why, tally.units, spent, tally.units / spent, tally.jumps, tally.walks, keys,
        )  # fmt: skip

    def make(
        self,
        run: Run,
        found: Step,
        world: World,
        aspect: float,
        key_names,
        ground: Ground | None,
        name: str = '',
        intent: Intent = OWN_MOVE,
        goal: Point | None = None,
        hurry: bool = False,
    ) -> None:
        """Make one move of the mode's own, by the way it names: a jump by its skill, or one click's
        walk. A jump that cannot be made any more (the skill gone from `jumps` since the choice, a
        wall in a blade's line) is made by the next skill that can, else walked. `intent` is the one
        the step was chosen under: the jumps are asked for again within it. `goal`: the place the step
        leads toward, when it is not the step's own end (a routed move), for what is said of a hop and
        for the pointer during a jump's flight (`ahead`)."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        skill = found.skill
        self.tally.leg(run.clock())
        if intent.routed and skill == TELEPORT and key_names is not None:
            # A hop the set that teleports chose over the level's rooms: made as the teleport step makes
            # its own (teleport.py `hop_to`: the staff swapped in where a staff it is, the key during the
            # cast before, the landing watched for).
            rect = run.actuator.keys.focused_window_rect()
            if rect is None:
                raise Abort('no game window')
            tile = (found.spot[0] / TILE_UNITS, found.spot[1] / TILE_UNITS)
            end = found.spot if goal is None else goal  # the hop's line says how far the goal is after it
            mark = Target(
                player.area, (), (end[0] / TILE_UNITS, end[1] / TILE_UNITS), name or 'the goal', 'hunt', False,
                ground.grids if ground else (),
            )  # fmt: skip
            try:
                hop_to(run, mark, player, rect, tile, 0.0, key_names)
            except Abort:
                self.jump_failed[TELEPORT] = run.clock()
                raise
            return
        if skill is not None and key_names is not None:
            jumps = self.jumps(run, world, intent)
            if ground is not None and not clear_shot(ground, here, found.spot, world.doors):
                jumps = tuple(jump for jump in jumps if not jump.line)
            able = [jump.skill for jump in jumps]
            if found.needs is not None and skill not in able:
                raise Abort('priced movement is no longer available; a new safety decision is needed')
            skill = skill if skill in able else next(iter(able), None)
        if skill is not None and key_names is not None:
            ahead = None
            if goal is not None and intent.routed and skill in self.delayed:
                ahead = partial(self.ahead, run, world, ground, aspect, goal=goal, intent=intent)
            self.jump(run, replace(found, skill=skill), player, aspect, key_names, ahead)
        else:
            began = run.clock()
            settled = step_walk(
                run, found.spot, player, aspect, attackable(world), name=name or 'a better place', hurry=hurry
            )
            self.tally.units += math.dist(here, found.spot)
            self.tally.walks += 1
            LOG.info(
                'Macro: leg time: walk of %.0f, %.3fs to the character seen going (settle %.3f)',
                math.dist(here, found.spot), run.clock() - began, settled,
            )  # fmt: skip


def walked_way(barred: Callable[[Point], bool], start: Point, goal: Point) -> list[Point]:
    """The shortest walk from `start` toward `goal` over cells that are not barred, as the centres of
    its cells from the first step on; it ends on the goal's cell, or with that one out of reach on the
    reached cell nearest the goal when that is nearer than the start. Empty: no way. The cell the
    character stands on is taken as it is, and no corner is cut."""
    first = (math.floor(start[0]), math.floor(start[1]))
    last = (math.floor(goal[0]), math.floor(goal[1]))
    limit = min(math.dist(start, goal) * AROUND_DETOUR + 10, AROUND_REACH * 3)
    bars: dict[tuple[int, int], bool] = {}

    def bar(cell: tuple[int, int]) -> bool:
        known = bars.get(cell)
        if known is None:
            known = bars[cell] = barred((cell[0] + 0.5, cell[1] + 0.5))
        return known

    cost, before = {first: 0.0}, {}
    queue = [(0.0, first)]
    while queue:
        gone, cell = heapq.heappop(queue)
        if cell == last:
            break
        if gone > cost[cell]:
            continue
        for dx, dy, step in NEIGHBOURS:
            near = (cell[0] + dx, cell[1] + dy)
            further = gone + step
            if further > limit or max(abs(near[0] - first[0]), abs(near[1] - first[1])) > AROUND_REACH:
                continue
            if further >= cost.get(near, math.inf) or bar(near):
                continue
            if dx and dy and (bar((cell[0] + dx, cell[1])) or bar((cell[0], cell[1] + dy))):
                continue
            cost[near], before[near] = further, cell
            heapq.heappush(queue, (further, near))
    end = last
    if end not in cost:
        end = min(cost, key=lambda cell: math.dist((cell[0] + 0.5, cell[1] + 0.5), goal))
        if math.dist((end[0] + 0.5, end[1] + 0.5), goal) > math.dist(start, goal) - AROUND_LEAST:
            return []
    path = []
    while end != first:
        path.append((end[0] + 0.5, end[1] + 0.5))
        end = before[end]
    return path[::-1]


# Units: the walked way round a wall a click from afar is trusted to make. A drop round a wall corner 18.3 units off,
# 19.4 by walking, took four clicks the client never walked (Chaos Sanctuary, 15:18:31-35 on 2026-10-14,
# rca/2026-10-14/run-1214-findings.md §3.2; the 00:25 game's 13 unmoved clicks were 18.1 off): from further than
# this a drop is clicked only on a clear straight line, and gone to first otherwise. Inferred, from those two cases:
# the client's own pathing limit for a click was not read.
ROUND_CLICK = 5.0


def clear_line(ground: Ground | None, doors: Sequence[Door], here: Point, goal: Point) -> bool:
    """Whether the straight line from `here` to `goal` has no wall, lava or closed door on it over the read ground.
    The first and last unit are not looked at: the character stands, and a drop lies, on cells the grids call
    unwalkable now and then. With no walls read (open ground), or within 2 units, it is clear."""
    barred = no_footing(ground, doors)
    away = math.dist(here, goal)
    if barred is None or away <= 2.0:
        return True
    steps = max(1, math.ceil(away * 2))
    line = (
        (here[0] + (goal[0] - here[0]) * k / steps, here[1] + (goal[1] - here[1]) * k / steps) for k in range(steps)
    )
    return not any(barred(point) for point in line if min(math.dist(point, here), math.dist(point, goal)) > 1.0)


def walk_reaches(ground: Ground | None, doors: Sequence[Door], here: Point, goal: Point, reach: float) -> bool:
    """Whether a click on a drop at `goal` from `here` walks the character to it: within `reach` and on a clear
    straight line (`clear_line`), or else by a walked way round (`walked_way`) no longer than ROUND_CLICK. What
    "near enough to click" means for a drop (macros/hunt.py `judge`, macros/pickup.py `approach`); further, the
    drop is gone to first. A drop 17 units off across lava was 43 by walking (River of Flame, 00:26:36 on
    2026-10-14, rca/2026-10-14/run-0025-findings.md §2.2), and one 18.3 off round a wall corner, 19.4 by walking,
    was clicked four times and never walked to (run-1214-findings.md §3.2). With no walls read (open ground) the
    straight distance alone decides."""
    if math.dist(here, goal) > reach:
        return False
    if clear_line(ground, doors, here, goal):
        return True
    barred = no_footing(ground, doors)
    assert barred is not None  # a line is barred only by read ground or a closed door
    path = walked_way(barred, here, goal)
    if not path or math.dist(path[-1], goal) > 1.5:
        return False
    walked = sum(math.dist(one, other) for one, other in zip((here, *path), path, strict=False))
    return walked <= min(reach, ROUND_CLICK)


def step_line(step: Step | None, here: Point) -> str:
    """A step for the log: the place it goes to as it was chosen, or the stride and what it is made by."""
    if step is None or step.camp is not None:
        return stand_line(step.camp if step is not None else None)
    by = skill_name(step.skill) if step.skill is not None else 'a walk'
    return f'a stride of {math.dist(here, step.spot):.0f} toward the nearest, by {by}'


def stand_line(found: Camp | None) -> str:
    if found is None:
        return 'no better place'
    way_there = 'a walk' if found.skill is None else f'a jump by {skill_name(found.skill)}'
    return (
        f'a place at ({found.spot[0]:.1f}, {found.spot[1]:.1f}), {way_there} of {found.walk:.0f} '
        f'({found.seconds:.1f}s), worth {found.worth:.0f} against {found.here:.0f} here, '
        f'{found.casts or "more than the horizon's"} casts'
    )


def label(monster: Monster) -> str:
    return f'{"the elite" if monster.leader else "the monster"} {monster.txt_id} ({monster.unit_id})'


def life(monster: Monster | None) -> str:
    if monster is None:
        return 'gone'
    return f'{monster.life}/{monster.max_life}' if monster.max_life else 'life unknown'


def attackable(world: World) -> list[Monster]:
    """The live monsters a left click attacks: not the character's own and not an ally."""
    return [m for m in world.monsters if m.owner == NO_OWNER and not m.ally and (m.x or m.y)]


def step_walk(
    run: Run,
    goal,
    player,
    aspect: float,
    alive: list[Monster],
    *,
    name: str = 'a better place',
    clicks: int = 1,
    hurry: bool = False,
) -> float:
    """A click on the ground at `goal` and the character seen going within STEP_WALK_SECONDS, `clicks`
    times at most (a click made while a cast ends is swallowed). Not clicked with one of `alive` (the
    monsters a click attacks) under the pointer: the left button attacks it, where it stands or after
    a chase. The unit the game names as under the pointer counts only within HOVER_UNITS of the goal
    (the name of the last unit hovered seems to stay). The first click waits for the character to stand
    free for a while (`settle`) only when the look the walk was chosen by (`player`) or one now has it
    casting: free at both, no cast ends under the click (the fixed 0.2 s of every walk leg, 2026-10-13
    latency-findings.md §2.2); a click again, after one the game took no notice of, waits. `hurry`: a step out
    of an act under way (macros/pursuit.py `Move.dodge`): the first click waits for the cast's end alone, not for
    the settle after it, and one the game took no notice of within HURRY_SECONDS is said and made again, settled
    (rca/2026-10-14/diablo-handling.md fix 3: a step decided in a cast left 0.67 s after the decision at 15:19,
    with the missiles). Returns the seconds spent waiting so."""
    where = ground_fraction(player, goal[0], goal[1], aspect)
    if not in_view(where):
        raise Abort(f'the place near {name} is not in view')
    run.say(f'Walking {math.dist((player.x, player.y), goal):.0f} toward {name}')
    if run.pad is not None:
        # Controller mode: the stick held toward it until there (macros/pad.py); nothing is attacked on the way.
        run.pad.walk(goal, why=name)
        if not moved(run.world().player or player, player):
            raise Abort('the character did not move')
        return 0.0
    settled = 0.0
    for click in range(max(clicks, 2) if hurry else clicks):
        began = run.clock()
        hurried = hurry and not click
        if click or player.mode in ACTING or not free(run):
            settle(run, seconds=HURRY_FREE if hurried else SWAP_SETTLE, limit=0.5)
        settled += run.clock() - began
        run.actuator.aim(*where, scatter=(4, 3))
        if run.hovered is not None:
            run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            if over is not None and over[0] == MONSTER_UNIT_TYPE:
                under = [m for m in alive if m.unit_id == over[1] and math.dist((m.x, m.y), goal) <= HOVER_UNITS]
                if under:
                    raise Covered(f'{label(under[0])} is under the pointer there', (under[0].unit_id,))
        run.actuator.click()
        within = HURRY_SECONDS if hurried else STEP_WALK_SECONDS
        if run.seen(lambda w: w.player is not None and moved(w.player, player), within) is not None:
            return settled
        if hurried:
            LOG.info(
                'Macro: walk: the click toward %s, made %.3fs after the step was chosen with no settle, showed no '
                'move in %.2fs: clicked again, settled', name, settled, within,
            )  # fmt: skip
    raise Abort('the character did not move')


def free(run: Run) -> bool:
    """Whether a light look has the character free to act (no cast under way)."""
    with run.lightly():
        seen = run.world().player
    return seen is not None and seen.mode not in ACTING
