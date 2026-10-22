"""One move of the hunt's own: a step to a place, by a jump or one click's walk.

The choice is pure, from `MoveFacts`: a straight stride (`stride_of`), the way round a wall (`around_of`) or along
the walked field to a far goal (`way_leg`), each with a `NoWay` reason when there is none. `Travel` asks the build's
first applicable movement set (`navigator`) within the caller's `Intent`, remembers jumps made and failed, and makes
the step (`make`). The intents live here, not in macros/movement.py, because movement.py imports this module.
"""

import base64
import binascii
import heapq
import math
import statistics
import threading
from collections import OrderedDict
from collections.abc import Callable, Generator, Hashable, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from functools import partial

from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.combat.stance import RUN_SPEED, WALK_LATENCY, Camp, Jump, no_footing, way
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import ITEM_UNIT, MONSTER_UNIT, NO_OWNER, OBJECT_UNIT
from inventory_tracking.game.records import GOLD, VALUABLE, Monster, Player, Teleport, World
from inventory_tracking.game.view import Viewport
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import SEALS, Ground, Room, Target, Walkable
from inventory_tracking.macros.actuator import Abort, Cancelled, Expired, Hand
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
from inventory_tracking.native.layout import TILE_UNITS


STRIDE = 16.0  # units of one walk stride (the click must be in view)
STEP_WALK_SECONDS = 0.7  # a walk's click must show the character moving within this
# A hurried walk's first click goes at the first look that reads the cast over; unseen going within HURRY_SECONDS,
# it is clicked again, settled (rca/2026-10-14/diablo-handling.md fix 3).
HURRY_FREE = 0.02
HURRY_SECONDS = 0.3
HOVER_UNITS = 12.0  # a monster named under the pointer counts only this near the aim (the name lingers)
# Walk clicks kept off item labels (the player, 2026-10-21 ~00:55: "not always clicking correct object (we often can
# pickup hp/rejuv potion) that we wanted"): with the labels shown, a walk's click on one takes that item instead of a
# step. All five potions the takes of 2026-10-20 show put into the inventory were taken so (4 of 84 town visits
# stashed one), each followed by "the character did not move" and its spot barred. With an item under the
# pointer that is no wanted valuable or gold of the read, the walk point is moved WALK_LABEL_SHIFTS world units
# (along the line, across it) until no label is under it; with none free it is clicked where aimed. False: clicked
# where aimed, as before
WALK_OFF_LABELS = True
# Walk clicks kept off a closed Chaos Sanctuary seal (2026-10-21, the arena's CS run, seed 3, as the code stood at
# 13:40): a walk's click on the seal's picture opens it, as `use_thing`'s does. A safety retreat and a firing spot
# toward the route's goal "Infector seal 2" walked onto it at 169.31 s (the arena's play) with the Infector still
# fought: the seal opened at 170.36 s, unasked and out of the route's order, the Infector died at 173.0 s, and
# Diablo is called by the fifth seal. With a closed seal under the pointer the walk point is moved off it as off an
# item label (WALK_LABEL_SHIFTS); a seal is opened only by `use_thing`. False: clicked where aimed, as before
WALK_OFF_SEALS = True
WALK_LABEL_SHIFTS = ((-1.5, 0.0), (0.0, 1.5), (0.0, -1.5), (1.5, 0.0), (-3.0, 0.0), (0.0, 3.0), (0.0, -3.0))
JUMP_REACH = 26.0  # units of a jump: in view, and within the blade's range
JUMP_LEAST = 8.0  # a stride shorter than this is walked
JUMP_SECONDS = 1.5  # for the character to be seen somewhere else after the key
# A casting delay shows as state 185 (`Player.cooldown`), set at the action frame and cleared when the delay is over;
# a key before the clear is refused. Measures: history/travel.md.
DELAY_SHOWN = ONE_CAST  # a clear state this long after the key is the delay over; before, the cast has not thrown
DELAY_STALE = 2.5  # seconds after its key a delay state still set is not that key's: the clock decides
DELAY_TICK = 0.04  # a delay state still set ends at the next game tick at the soonest
ROUNDING = 1e-6  # seconds of float rounding
# A waiting intent is offered the jump this long before its delay ends, so the look and choice overlap the delay
# (rca/2026-10-13/latency-findings.md §2.2); the key then waits (`Travel.delay_over`).
PLAN_AHEAD = 0.25
KEY_POLL = 0.02  # seconds between light looks waiting for a delay's end or a throw
NEAR_AIM = 120  # pixels: a pointer this near a jump's aim goes onto it in one step (`Actuator.aim` `near`)
REAIM = 0.5  # units moved during a delay wait that have the pointer put again
LEG_GAP = 2.5  # seconds: two moves further apart are not legs of one travel (`Tally`)
# Staff charges the mode's own moves leave alone (user, 2026-10-11: "track number of tp charges when using staff,
# and leverage warp more when low on charges"). The player's own teleport step spends them to the last.
LOW_CHARGES = 10
JUMP_DISTRUST = 30.0  # seconds a way of jumping that did not move the character is left alone
WARP_CHARGES = 15  # with fewer charges the teleport step hops by Blade Warp where it can
WARP_RETRY = 3.0  # seconds the teleport step leaves Blade Warp alone after one that moved nobody
# The walked way round a wall (`around_of`): Dijkstra within AROUND_REACH, AROUND_DETOUR times the line at most.
AROUND_REACH = 70
AROUND_DETOUR = 4.0
AROUND_LEAST = 3.0  # units a move along that way has to make
NEIGHBOURS = tuple((dx, dy, math.hypot(dx, dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
NO_ASPECT = 0.0  # window shape for facts asked only for the jumps: not read


# What each kind of caller allows (architecture.md 4.3).
#
# The sweep and the choice of a place to stand: no wait, no swap, a straight stride only.
OWN_MOVE = Intent(
    'own move', reserve=LOW_CHARGES, may_swap=False, may_wait=False, distrust=JUMP_DISTRUST, sparing=math.inf
)
# Safety's alternatives, a charged set on the back included; the caller prices the swap.
SAFE_MOVE = replace(OWN_MOVE, name='priced move', may_swap=True, reserve=1)
# The seek step (hunting/moves.py `afoot`): under LOW_CHARGES a walk comes before the hop.
SEEK = Intent(
    'seek',
    reserve=LOW_CHARGES,
    may_swap=True,
    may_wait=True,
    distrust=JUMP_DISTRUST,
    sparing=math.inf,
    walks_under=LOW_CHARGES,
)
# The player's own teleport step (hunting/moves.py `warp_hop`, `empty_hop`): under WARP_CHARGES a staff-sparing
# jump first; a walk only with the staff empty.
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
# A goal however far, routed by the set (macros/pursuit.py; rca/2026-10-13/kp4-findings.md §6).
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
# The KP_6 loop's goals: as PRESSED, but charges are dear (the player, 2026-10-16: "it actually can get too
# expensive (~100k+ for full recharge)"): Blade Warp first, the last LOW_CHARGES kept.
#
# Moves end LOOP_SHORT short: a Teleport aimed onto a chest's own spot was not cast (2026-10-16 19:56:40); the chest
# is clicked from beside it (hunt.py OPEN_NEAR).
LOOP_SHORT = 3.0
# No Teleport in the loop's moves: the player chose "No TP, high-value trade only" (2026-10-17 13:36; the charges
# bought no time, history/travel.md).
HOP_FROM = math.inf
LOOPED = replace(PRESSED, name='loop goal', reserve=LOW_CHARGES, sparing=math.inf, short=LOOP_SHORT, hop_from=HOP_FROM)
# Teleport wherever faster, while the gold carried is high (macros/loop.py `teleports`; the player, 2026-10-17: "if we
# make enough gold - we can use teleport staff more often to speed up things").
LOOPED_TELEPORT = replace(LOOPED, name='loop goal by Teleport', hop_from=0.0)
# Attack mode's own goal (a boss out of reach): as OWN_MOVE, but a delay about to end is waited out.
STANDING = Intent(
    'standing goal',
    reserve=LOW_CHARGES,
    may_swap=False,
    may_wait=True,
    distrust=JUMP_DISTRUST,
    sparing=math.inf,
    routed=True,
)

# A one-click walk whose end lies off the screen is made to the farthest point of its straight line in view
# (`in_view_toward`); the next look walks on. The player, 2026-10-20 ~23:15: "act 4: we couldn't find way to plains
# of despair in current game, I moved char through the gate manually" (the Outer Steppes passage 37 units south,
# below the view: "the place near Plains of Despair is not in view" x52 from 23:10:47). False: it aborts as before
WALK_PARTWAY = True
VIEW_STEPS = 12  # halvings of the line to its last point in view (37 units to under 0.01)

# `NoWay.reason`s.
THERE = 'the character is as near the goal as the move was to end'  # the arrival
SHUNNED = 'the place a stride toward the goal ends at is shunned'
UNSEEN = 'the end of a walk toward the goal is not in view'
WALLED = 'no straight walk leads toward the goal: a wall in the line, or no footing at its end'
NO_SHOT = 'a few units up to a wall the goal stands behind: the firing spot is to find'
OPEN_GROUND = 'no wall or closed door is known: there is no way round to look for'
NO_WAY_ROUND = 'no walked way leads nearer the goal'
NO_SPOT_ON_WAY = 'no spot on the walked way is in view and reached by a jump over a clear line or one straight walk'
NO_SET = 'no movement set of the build is for the character as it is now'
WAY_UNKNOWN = 'no walked way to the goal is known (its ground is not read, or nothing leads there)'
# Not a failed way (hunting/judging.py `judge` does not pass the goal by): the next look grows the field on.
GROWING = 'the walked way there is still being grown'
NO_NEARER = 'the move found brings the goal no nearer by the way'
HUG = 2.0  # cost factor beside a wall: moves end only on free surroundings, an unweighted way hugs corners
GOAL_CELLS = 8  # cells round a goal searched for a walkable root: objects stand on unwalkable cells
FIELDS_KEPT = 8  # walked fields kept (`Fields`)
GROW_CHECK = 256  # cells settled between clock reads (~1.5 ms of growth)


def navigator(sets: Sequence[MovementSet], facts: MoveFacts) -> MovementSet | None:
    """The first of a build's sets that applies to the facts; None when none does."""
    return next((movement for movement in sets if movement.applies(facts)), None)


def spare_jump(sets: Sequence[MovementSet], slots: Sequence[int | None]) -> Jump | None:
    """The first of the sets' jumps on a key that is not Teleport (taken to cost no charge), whatever its delay or
    failures; None without one."""
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
    """What a move is chosen from, read once. `staff=None` (no reader, or no staff read) makes a slotted Teleport
    the character's own. `lead`: seconds before a delay ends that its jump counts as ready (`ahead_of`)."""
    # The staff is read only with Teleport on a key: a worn-items read every stride would cost the loop.
    staff = run.teleport() if run.teleport is not None and TELEPORT in world.slots else None
    return facts_with(run, world, ground, aspect, travel, staff, rooms, lead=lead)


def ahead_of(intent: Intent) -> float:
    """PLAN_AHEAD where the intent may wait a delay out, else 0."""
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
    """`move_facts` with the caller's staff (not read again)."""
    player = world.player
    assert player is not None
    now = run.clock()
    failed = dict(travel.jump_failed)
    if run.pad is not None and run.pad.walk_owed(now):
        # Controller mode after an astray landing (macros/pad.py `astray`): the next leg is walked
        failed.update(dict.fromkeys(run.pad.reach, now))
    return MoveFacts(
        here=(player.x, player.y),
        now=now,
        slots=world.slots,
        staff=staff if TELEPORT in world.slots else None,
        ground=ground,
        doors=world.doors,
        aspect=aspect,
        last_used=travel.counted(now, player.cooldown, lead),
        failed=failed,
        area=player.area,
        rooms=rooms,
        distrusted=dict(travel.distrusted),
        pad=run.pad is not None,
    )


def known(ground: Ground | None) -> Ground:
    """The ground, or an empty one (only closed doors bar)."""
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
    """A stride straight toward `goal`, ending `short` of it: by the first of `jumps` (up to JUMP_REACH), else a
    walk of STRIDE, onto footing in view. With `shot` a short walk must end with a clear shot. Only the first jump
    is tried; it falls to the walk, never the next jump. Otherwise the `NoWay` reason (THERE: arrived)."""
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
    # The jump's own least too: controller mode jumps one length (macros/pad.py).
    least = max(JUMP_LEAST, jump.least) if jump is not None else JUMP_LEAST
    if jump is not None and away - short >= least:
        longest = min(away - short, JUMP_REACH, jump.reach)
        for stride in (longest, longest * 0.75, longest * 0.5):
            spot = at(stride)
            if stride < least or not footed(spot):
                continue
            if jump.line and not clear_shot(ground, here, spot, facts.doors):
                continue  # the blade flies: no wall in its way
            return Step(spot, jump.skill)
    stride = min(away - short, STRIDE)
    spot = at(stride)
    if not in_view(view.ground(here, spot[0], spot[1])):
        return NoWay(UNSEEN)
    if not way(barred, here, spot):
        return NoWay(WALLED)
    if shot and stride < STRIDE / 2 and not clear_shot(ground, spot, goal, facts.doors):
        return NoWay(NO_SHOT)
    return Step(spot)


def around_of(facts: MoveFacts, goal: Point, *, jumps: Sequence[Jump] = ()) -> Leg:
    """A move along the shortest walked way to `goal` when a wall blocks the line: the furthest spot on it the
    first of `jumps` reaches over a clear line (only a line jump), else the furthest one straight walk reaches;
    otherwise the reason. For an empty staff (user, 2026-10-12: "KP_1 got stuck when I'm out of tp charges")."""
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
                continue  # the jump's own reach too (controller mode, macros/pad.py)
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


class Unplanned(Exception):
    """A walked field ran out of the look's time (`planning`); what it settled is kept."""


@dataclass
class Planning:
    """A look's time for the walked fields: the clock, its end, and the fields that ran out (each the straight
    line for the rest of the look, so one look decides by one measure)."""

    timer: Callable[[], float]
    until: float
    short: set[int] = field(default_factory=set)  # id() of the fields that ran out

    def over(self) -> bool:
        return self.timer() >= self.until


PLANNING: ContextVar[Planning | None] = ContextVar('planning', default=None)


@contextmanager
def planning(timer: Callable[[], float] | None, until: float) -> Generator[None]:
    """Walked fields grow within the block until `timer` reads `until`; one short of the character is the straight
    line until the next block. No clock (the arena): no bound. rca/2026-10-14/run-2040-findings.md §1.2.2."""
    if timer is None:
        yield
        return
    outer = PLANNING.get()
    own = Planning(timer, until)
    token = PLANNING.set(own)
    try:
        yield
    finally:
        PLANNING.reset(token)
        if outer is not None:
            outer.short |= own.short


class Walked:
    """The walked way to a goal from any cell: Dijkstra outward from the goal's cell (eight neighbours, no corner
    cut, HUG beside walls), grown lazily and kept. `left`: the way left from a point; `descent`: its cells. The
    measure on-foot progress is judged by, where the straight line leads into pockets. Kept across ground growth
    (`extend`) and grown within a look's time (`planning`)."""

    def __init__(self, barred: Callable[[Point], bool], goal: Point) -> None:
        self.barred = barred
        self.bars: dict[tuple[int, int], bool] = {}
        self.hugs: dict[tuple[int, int], bool] = {}
        self.goal = goal
        self.cost: dict[tuple[int, int], float] = {}
        self.settled: set[tuple[int, int]] = set()
        self.queue: list[tuple[float, tuple[int, int]]] = []
        self.radius = 0.0  # cost of the last cell settled: every nearer cell is settled
        # Cells a room read shortened (`extend`), passed on before any other is settled
        self.lowered: list[tuple[float, tuple[int, int]]] = []
        self.said = False  # "still being grown" logged (`walked_for`)
        self.root = self.rooted()
        if self.root is not None:
            self.cost[self.root] = 0.0
            self.queue.append((0.0, self.root))

    def rooted(self) -> tuple[int, int] | None:
        """The walkable cell nearest the goal within GOAL_CELLS."""
        last = (math.floor(self.goal[0]), math.floor(self.goal[1]))
        around = [
            (last[0] + dx, last[1] + dy)
            for dx in range(-GOAL_CELLS, GOAL_CELLS + 1)
            for dy in range(-GOAL_CELLS, GOAL_CELLS + 1)
        ]
        free = [cell for cell in around if not self.bar(cell)]
        if not free:
            return None
        return min(free, key=lambda cell: math.dist((cell[0] + 0.5, cell[1] + 0.5), self.goal))

    def bar(self, cell: tuple[int, int]) -> bool:
        known = self.bars.get(cell)
        if known is None:
            known = self.bars[cell] = self.barred((cell[0] + 0.5, cell[1] + 0.5))
        return known

    def hug(self, cell: tuple[int, int]) -> bool:
        """Whether a barred cell is beside this one."""
        known = self.hugs.get(cell)
        if known is None:
            known = self.hugs[cell] = any(self.bar((cell[0] + dx, cell[1] + dy)) for dx, dy, _ in NEIGHBOURS)
        return known

    def step(self, at: tuple[int, int], dx: int, dy: int, length: float) -> float | None:
        """The cost of the step from `at` by (dx, dy); None onto a barred cell or across a corner."""
        near = (at[0] + dx, at[1] + dy)
        if self.bar(near):
            return None
        if dx and dy and (self.bar((at[0] + dx, at[1])) or self.bar((at[0], at[1] + dy))):
            return None
        return length * (HUG if self.hug(near) else 1.0)

    def grow(self, cell: tuple[int, int]) -> None:
        """Settle cells until `cell` is settled or none is left, `lowered` first. Past the look's time
        (checked every GROW_CHECK cells) raises `Unplanned`, keeping the work done."""
        cost, queue, settled, lowered = self.cost, self.queue, self.settled, self.lowered
        if not lowered and (cell in settled or not queue):
            return
        plan = PLANNING.get()
        if plan is not None and (id(self) in plan.short or plan.over()):
            plan.short.add(id(self))
            raise Unplanned
        count = 0
        while lowered:
            gone, at = heapq.heappop(lowered)
            if gone > cost[at]:
                continue
            if gone > self.radius:
                heapq.heappush(queue, (gone, at))  # beyond the settled radius: the growth's
                continue
            settled.add(at)
            for dx, dy, length in NEIGHBOURS:
                near = (at[0] + dx, at[1] + dy)
                step = self.step(at, dx, dy, length)
                if step is not None and gone + step < cost.get(near, math.inf):
                    cost[near] = gone + step
                    heapq.heappush(lowered, (gone + step, near))
            count += 1
            if plan is not None and count % GROW_CHECK == 0 and plan.over():
                plan.short.add(id(self))
                raise Unplanned
        while queue and cell not in settled:
            gone, at = heapq.heappop(queue)
            if at in settled:
                continue
            settled.add(at)
            self.radius = gone
            for dx, dy, length in NEIGHBOURS:  # `step` inlined: the hot loop
                near = (at[0] + dx, at[1] + dy)
                if near in settled or self.bar(near):
                    continue
                if dx and dy and (self.bar((at[0] + dx, at[1])) or self.bar((at[0], at[1] + dy))):
                    continue
                further = gone + length * (HUG if self.hug(near) else 1.0)
                if further < cost.get(near, math.inf):
                    cost[near] = further
                    heapq.heappush(queue, (further, near))
            count += 1
            if plan is not None and count % GROW_CHECK == 0 and plan.over():
                plan.short.add(id(self))
                raise Unplanned

    def extend(self, barred: Callable[[Point], bool], areas: Sequence[tuple[int, int, int, int]]) -> bool:
        """Take in ground that only gained footing within `areas` (x, y, width, height in units) without regrowing:
        cells there are read anew and every way they shorten is carried on from the settled cells (lowered within
        `radius`, queued beyond), so the answer equals a fresh field's. The next `grow` passes them on. False: the
        goal's root cell changed; grow afresh."""
        self.barred = barred
        for x, y, width, height in areas:
            for cx in range(x - 1, x + width + 1):
                for cy in range(y - 1, y + height + 1):
                    self.bars.pop((cx, cy), None)
            for cx in range(x - 2, x + width + 2):
                for cy in range(y - 2, y + height + 2):
                    self.hugs.pop((cx, cy), None)
        if self.rooted() != self.root:
            return False
        cost, settled, lowered = self.cost, self.settled, self.lowered
        for x, y, width, height in areas:
            # Every changed step ends in the area or one cell round it: retaken from the settled cells beside it
            for cx in range(x - 2, x + width + 2):
                for cy in range(y - 2, y + height + 2):
                    cell = (cx, cy)
                    if self.bar(cell):
                        continue
                    best = cost.get(cell, math.inf)
                    for dx, dy, length in NEIGHBOURS:
                        back = (cx - dx, cy - dy)
                        if back not in settled:
                            continue
                        step = self.step(back, dx, dy, length)
                        if step is not None and cost[back] + step < best:
                            best = cost[back] + step
                    if best < cost.get(cell, math.inf):
                        cost[cell] = best
                        heapq.heappush(lowered, (best, cell))
        return True

    def of(self, cell: tuple[int, int]) -> float:
        """The way left from a cell; inf: none leads from it."""
        self.grow(cell)
        return self.cost[cell] if cell in self.settled else math.inf

    def foot(self, point: Point) -> tuple[int, int] | None:
        """The cell the way from `point` begins on: its own, or (on an unwalkable cell, which happens) the
        neighbour with the shortest way left. None: no way."""
        cell = (math.floor(point[0]), math.floor(point[1]))
        if not self.bar(cell):
            return cell if self.of(cell) < math.inf else None
        beside = [(cell[0] + dx, cell[1] + dy) for dx, dy, _ in NEIGHBOURS]
        free = [near for near in beside if not self.bar(near) and self.of(near) < math.inf]
        return min(free, key=self.of) if free else None

    def left(self, point: Point) -> float:
        """Units of the walked way left from `point` (HUG-weighted); inf: no way."""
        cell = self.foot(point)
        return math.inf if cell is None else self.of(cell)

    def descent(self, point: Point, reach: float) -> list[tuple[Point, float]]:
        """The way's (cell centre, way left) from the first step on, within `reach` straight units of `point`.
        Empty: no way, or on the goal's cell."""
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


def grids_gained(known: Sequence[Walkable], grids: Sequence[Walkable]) -> list[tuple[int, int, int, int]] | None:
    """The areas (x, y, width, height in units) where `grids` only gained footing over `known`: same grids in the
    same order, none losing a walkable cell, then new grids over uncovered tiles. None for any other change."""
    if len(grids) < len(known):
        return None
    gained: list[tuple[int, int, int, int]] = []
    covered: set[tuple[int, int]] = set()
    for old, new in zip(known, grids, strict=False):  # new grids come after
        if (old.x, old.y, old.width, old.height) != (new.x, new.y, new.width, new.height):
            return None
        if old is not new and old.cells != new.cells:
            try:
                before = int.from_bytes(base64.b64decode(old.cells, validate=True), 'big')
                after = int.from_bytes(base64.b64decode(new.cells, validate=True), 'big')
            except binascii.Error, ValueError:
                return None
            if before & ~after:
                return None  # a cell barred now: a way may have grown longer
            gained.append(grid_area(new))
        covered.update(grid_tiles(old))
    for new in grids[len(known) :]:
        tiles = grid_tiles(new)
        if not covered.isdisjoint(tiles):
            return None  # over a tile already read: the winning grid may change
        covered.update(tiles)
        gained.append(grid_area(new))
    return gained


def grid_tiles(grid: Walkable) -> set[tuple[int, int]]:
    return {(x, y) for x in range(grid.x, grid.x + grid.width) for y in range(grid.y, grid.y + grid.height)}


def grid_area(grid: Walkable) -> tuple[int, int, int, int]:
    return (grid.x * TILE_UNITS, grid.y * TILE_UNITS, grid.width * TILE_UNITS, grid.height * TILE_UNITS)


class Fields:
    """An LRU of walked fields keyed by goal cell and closed doors, each with the grids it was grown over. Not
    keyed by grids: outdoor levels read rooms as the character nears, which regrew the field every room
    (rca/2026-10-14/run-2040-findings.md §1.2.2). The lock guards the table; only the macro's thread grows fields."""

    def __init__(self, most: int) -> None:
        self.most = most
        self.kept: OrderedDict[Hashable, tuple[tuple[Walkable, ...], Walked | None]] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: Hashable) -> tuple[tuple[Walkable, ...], Walked | None] | None:
        with self.lock:
            found = self.kept.get(key)
            if found is not None:
                self.kept.move_to_end(key)
            return found

    def put(self, key: Hashable, grids: tuple[Walkable, ...], walked: Walked | None) -> None:
        with self.lock:
            self.kept[key] = (grids, walked)
            self.kept.move_to_end(key)
            while len(self.kept) > self.most:
                self.kept.popitem(last=False)

    def clear(self) -> None:
        with self.lock:
            self.kept.clear()


FIELDS = Fields(FIELDS_KEPT)


def walked_over(grids: tuple[Walkable, ...], closed: tuple[Door, ...], goal: tuple[int, int]) -> Walked | None:
    """The kept walked field to the goal's cell, extended when the ground only gained rooms (`grids_gained`).
    None on ground with no wall and no closed door."""
    key = (closed, goal)
    kept = FIELDS.get(key)
    if kept is not None:
        known, walked = kept
        if known == grids:
            return walked
        gained = grids_gained(known, grids) if walked is not None else None
        if gained is not None:
            barred = no_footing(Ground(grids), closed)
            if barred is not None and walked is not None and walked.extend(barred, gained):
                FIELDS.put(key, grids, walked)
                return walked
    barred = no_footing(Ground(grids), closed)
    walked = None if barred is None else Walked(barred, (goal[0] + 0.5, goal[1] + 0.5))
    FIELDS.put(key, grids, walked)
    return walked


def walked_for(facts: MoveFacts, goal: Point) -> Walked | None:
    """`walked_over` for the facts, grown as far as the character. None: open ground, or a field that has not
    reached the character within the look's time (the straight line meanwhile; logged once per field)."""
    grids = facts.ground.grids if facts.ground is not None else ()
    closed = tuple(door for door in facts.doors if door.closed)
    walked = walked_over(grids, closed, (math.floor(goal[0]), math.floor(goal[1])))
    if walked is None:
        return None
    plan = PLANNING.get()
    if plan is not None and id(walked) in plan.short:
        return None
    try:
        walked.foot(facts.here)
    except Unplanned:
        if not walked.said:
            walked.said = True
            LOG.info(
                'Macro: way: the walked way to (%.0f, %.0f) is still being grown (%d cells settled, %.0f of the way '
                'out): the straight line meanwhile',
                *goal, len(walked.settled), walked.radius,
            )  # fmt: skip
        return None
    walked.said = False
    return walked


def growing(facts: MoveFacts, goal: Point) -> bool:
    """Whether the walked field to `goal` ran out of the look's time before reaching the character."""
    plan = PLANNING.get()
    if plan is None or not plan.short:
        return False
    grids = facts.ground.grids if facts.ground is not None else ()
    closed = tuple(door for door in facts.doors if door.closed)
    kept = FIELDS.get((closed, (math.floor(goal[0]), math.floor(goal[1]))))
    return kept is not None and kept[1] is not None and kept[0] == grids and id(kept[1]) in plan.short


def way_left(facts: MoveFacts, goal: Point) -> float:
    """Units left to `goal` on foot: the walked way (inf: none known), or the straight line on open ground."""
    field = walked_for(facts, goal)
    return math.dist(facts.here, goal) if field is None else field.left(facts.here)


# Seconds from one walk leg to the next in a leg loop, any length within STRIDE (measured 2026-10-14 22:32: 1.65 s
# median over 37 legs; history/travel.md).
WALK_LEG = 1.6


def walk_seconds(walked: float) -> float:
    """Seconds a walk leg of `walked` units takes in a leg loop."""
    return max(WALK_LEG, WALK_LATENCY + walked / RUN_SPEED)


def beats_walk(jump: Jump, delay: float, flown: float, gained: float, walked: float, walk_gained: float) -> bool:
    """Whether a jump leg gains more walked way per second than the walk leg (a jump takes at least its delay)."""
    if walk_gained <= 0.0:
        return gained > 0.0
    jumping = max(jump.takes(flown), delay)
    return gained / jumping >= walk_gained / walk_seconds(walked)


LANDING_TRIES = 48  # footed cells `landing_in_reach` line-tests at most; past them the descent is taken


def landing_in_reach(
    field: Walked,
    here: Point,
    jump: Jump,
    short: float,
    left: float,
    footed: Callable[[Point], bool],
    lands: Callable[[Point], bool],
) -> tuple[Point, float] | None:
    """The cell centre in the jump's reach with the least walked way left (at least `short`, under `left`) that is
    `footed` and `lands`, with that way; None with none. Beats the descent's furthest cell on winding ways
    (history/travel.md)."""
    cx, cy = math.floor(here[0]), math.floor(here[1])
    reach = math.ceil(jump.reach)
    least, most = jump.least**2, jump.reach**2
    found: list[tuple[float, float, Point]] = []
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            spot = (cx + dx + 0.5, cy + dy + 0.5)
            far = (spot[0] - here[0]) ** 2 + (spot[1] - here[1]) ** 2
            if not least <= far <= most:
                continue
            # Settled cells only, never grown (`Walked.of` could raise `Unplanned` every look, 2026-10-17 00:13):
            # every cell under `left` was settled before the character's own
            cell = (cx + dx, cy + dy)
            cost = field.cost[cell] if cell in field.settled else math.inf
            if short <= cost < left:
                found.append((cost, far, spot))
    found.sort()
    tried = 0
    for cost, _, spot in found:
        if not footed(spot):
            continue
        if lands(spot):
            return spot, cost
        tried += 1
        if tried >= LANDING_TRIES:
            break
    return None


def way_leg(
    facts: MoveFacts,
    goal: Point,
    intent: Intent,
    *,
    jumps: Sequence[Jump] = (),
    delays: Mapping[int, float] | None = None,
) -> Leg:
    """The next move along the walked way to a far goal (`Intent.routed`), ending `intent.short` of it: the first
    of `jumps` or one straight walk, whichever gains faster (`beats_walk` with `delays`; without, the jump). Every
    spot has less way left than here, so a move always brings the goal nearer. Open ground: `stride_of`."""
    here = facts.here
    if math.dist(here, goal) - intent.short < MOVED:
        return NoWay(THERE, arrived=True)
    field = walked_for(facts, goal)
    if field is None:
        found = stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=jumps)
        if isinstance(found, NoWay) and not found.arrived and growing(facts, goal):
            return NoWay(GROWING)
        return found
    left = field.left(here)
    if left == math.inf:
        return NoWay(WAY_UNKNOWN)
    whole = field.descent(here, JUMP_REACH)
    path = [(spot, cost) for spot, cost in whole if cost >= intent.short]
    # The descent's last cell is exactly 0 when the way's end is in reach.
    ends = bool(whole) and whole[-1][1] == 0.0  # ruff: ignore[float-equality-comparison]
    if not path or (ends and all(math.dist(here, spot) < AROUND_LEAST for spot, _ in path)):
        # The end is within `short`, or nearer than a move can be made
        return NoWay(THERE, arrived=True)
    ground = known(facts.ground)
    view = Viewport(facts.aspect)
    barred = field.barred

    def shown(spot: Point) -> bool:
        return in_view(view.ground(here, *spot)) and not intent.shuns(spot)

    jump = next(iter(jumps), None)
    line = jump is not None and jump.line

    def footed(spot: Point) -> bool:
        return shown(spot) and not any(barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def lands(spot: Point) -> bool:
        return not line or clear_shot(ground, here, spot, facts.doors)

    flown = None
    if jump is not None:
        # The end in reach: land on the way's own line (an off-line cell may lead nowhere)
        flown = None if ends else landing_in_reach(field, here, jump, intent.short, left, footed, lands)
        for spot, cost in reversed(path) if flown is None else ():
            # The descent's furthest reachable cell, when the best cells are walled off
            if jump.least <= math.dist(here, spot) <= jump.reach and footed(spot) and lands(spot):
                flown = (spot, cost)
                break
    walked = next(
        (
            (spot, cost)
            for spot, cost in reversed(path)
            if AROUND_LEAST <= math.dist(here, spot) <= STRIDE and shown(spot) and way(barred, here, spot)
        ),
        None,
    )
    if flown is not None and jump is not None:
        if walked is None or delays is None:
            return Step(flown[0], jump.skill)
        delay = delays.get(jump.skill, 0.0)
        if beats_walk(
            jump, delay, math.dist(here, flown[0]), left - flown[1], math.dist(here, walked[0]), left - walked[1]
        ):
            return Step(flown[0], jump.skill)
    if walked is not None:
        return Step(walked[0])
    return NoWay(NO_SPOT_ON_WAY)


def cut(run: Run, stop: Abort) -> bool:
    """Whether a jump was stopped by the player or the run (`Hand`, `Cancelled`, `Expired`, `Run.stops`), not
    failed by the game: such a jump is not distrusted (rca/2026-10-14/run-1932-findings.md §1.2.4)."""
    return isinstance(stop, (Hand, Cancelled, Expired)) or run.stops(stop)


class Stale(Abort):
    """The character moved while a jump waited for its delay: no key, the leg is chosen again, nothing distrusted."""


class Untaken(Abort):
    """A jump's key the game took no cast for: no move, and the delay state read but never set (a key in the
    cooldown, run-0305-findings.md §5.1). Not distrusted, made again when due; REFUSALS in a row are a failure."""


REFUSALS = 2


@dataclass
class Thrown:
    """The delay state seen by the looks after a jump's key."""

    read: bool = False  # some look read the state
    set: bool = False  # some look had it set: the game took a cast

    def note(self, world: World) -> bool:
        """Notes one look; True, to chain before a look's test with `and`."""
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
    """One level run's (KP_1) moves, for its pace: units, legs and delayed jumps' key-to-key seconds
    (`Travel.paced`)."""

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
    """Asks the build's movement sets for moves and makes them; holds what a set cannot: the memory of jumps made
    and failed."""

    def __init__(self, sets: Sequence[MovementSet] = ()) -> None:
        self.sets = tuple(sets)  # the first that applies is asked
        # skill with a casting delay -> its seconds
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
        self.released_at: dict[int, float] = {}  # -> the clock time that key came up
        self.jump_failed: dict[int, float] = {}  # skill -> clock time a jump by it last moved nothing
        self.distrusted: dict[Hashable, float] = {}  # `NoWay.distrust` -> clock time it was said
        self.landed_at: dict[int, float] = {}  # skill -> the clock when its last jump was seen landed
        self.tally = Tally()  # the level run's moves (`paced`)

    @property
    def warped_at(self) -> float:
        """Clock time of the last jump by a skill that has a casting delay; -inf with none made."""
        return max(self.jumped_at.values(), default=-math.inf)

    @warped_at.setter
    def warped_at(self, at: float) -> None:
        """Every delayed skill last jumped at `at` (for tests)."""
        self.jumped_at = dict.fromkeys(self.delayed, at)
        self.released_at = {}

    def left(self, skill: int, now: float, cooldown: bool | None) -> float:
        """Seconds of the skill's casting delay still to run; <= 0 none (-inf: known over). By the read delay state
        (`cooldown`): clear after DELAY_SHOWN and the skill's `cleared`, over (it clears a tick early,
        run-0305-findings.md §5.1); set, not before the delay from the key nor the next tick. Unread, or set past
        DELAY_STALE: by the clock from the key's release."""
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
        """`MoveFacts.last_used`: per keyed skill, the time its delay counts from, so a set reads it over `lead`
        seconds before `left` does. Skills whose state says over are left out."""
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
        """The next move toward `goal` within `intent` by the set that applies; else NO_SET."""
        facts = move_facts(run, world, ground, aspect, self, lead=ahead_of(intent))
        movement = navigator(self.sets, facts)
        return NoWay(NO_SET) if movement is None else movement.leg(facts, goal, intent)

    def options(
        self, run: Run, world: World, ground: Ground | None, aspect: float, goal: Point, intent: Intent
    ) -> tuple[Step, ...]:
        """Each usable jump and the walk, separately, for safety to price (a preferred jump must not hide a faster
        escape). A set on the back only when a swap is allowed; no input is made."""
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
        """The set and its `leg`, asked again while it names a way to distrust (`NoWay.distrust`, remembered);
        with the facts last asked."""
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
        """The next move toward a routed goal by the set that applies, or the reason there is none. `goal` is the
        goal's own place, never one worked out for one means; `rooms`: for sets that plan over them."""
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
        """Seconds to `goal` by the means in hand (`MovementSet.eta`); inf where `toward` has no way."""
        facts = move_facts(run, world, ground, aspect, self, rooms, lead=ahead_of(intent))
        facts, movement, found = self.asked(facts, goal, intent)
        if movement is None or (isinstance(found, NoWay) and not found.arrived):
            return math.inf
        return movement.eta(facts, goal, intent)

    def means(
        self,
        run: Run,
        world: World,
        ground: Ground | None,
        aspect: float,
        goal: Point,
        intent: Intent,
        rooms: tuple[Room, ...] = (),
    ) -> str | None:
        """The navigation class the way is planned by (macros/movement.py `Ways.means`); None: no set, or a set with
        no classes."""
        facts = move_facts(run, world, ground, aspect, self, rooms, lead=ahead_of(intent))
        movement = navigator(self.sets, facts)
        plan = getattr(movement, 'means', None)
        return None if plan is None else plan(facts, goal, intent)

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
        """Seconds to let pass before `toward` is asked (`MovementSet.wait`). A delay ending within PLAN_AHEAD is
        waited by the jump's key instead."""
        facts = move_facts(run, world, ground, aspect, self, rooms, lead=ahead_of(intent))
        movement = navigator(self.sets, facts)
        return 0.0 if movement is None else movement.wait(facts, goal, intent)

    def stride(
        self, run: Run, world: World, ground: Ground, aspect: float, goal: Point, intent: Intent = OWN_MOVE
    ) -> Step | None:
        """A stride straight toward `goal` within `intent` (`stride_of`); None with none."""
        found = self.leg(run, world, ground, aspect, goal, intent)
        return found if isinstance(found, Step) else None

    def around(
        self, run: Run, world: World, ground: Ground, aspect: float, goal: Point, intent: Intent = OWN_MOVE
    ) -> Step | None:
        """A move round a wall toward `goal` (`around_of`); None with none."""
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
        """`pause` from `here`, with the caller's staff (`facts_with`)."""
        facts = replace(facts_with(run, world, ground, aspect, self, staff, lead=ahead_of(intent)), here=here)
        movement = navigator(self.sets, facts)
        return 0.0 if movement is None else movement.wait(facts, goal, intent)

    def jumps(self, run: Run, world: World, intent: Intent = OWN_MOVE) -> tuple[Jump, ...]:
        """The jumps available now without a swap, preferred first (the set's `jumps`)."""
        facts = move_facts(run, world, None, NO_ASPECT, self, lead=ahead_of(intent))
        movement = navigator(self.sets, facts)
        return () if movement is None else movement.jumps(facts, intent)

    def jump_by(self, run: Run, world: World, intent: Intent = OWN_MOVE) -> int | None:
        """The first of `jumps`' skills; None: walked."""
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
        """One jump onto `found.spot`: aim, wait out the delay (`delay_over`), key, and see the landing. `ahead`:
        the next leg's aim, for the pointer during the flight (`aim_ahead`). Logs aim, landing and leg time."""
        skill = found.skill
        assert skill is not None
        began = run.clock()
        before, before_released = self.jumped_at.get(skill), self.released_at.get(skill)
        cast = Thrown()
        try:
            with run.lightly():  # the key's name needs the skills on keys alone
                run.keys.update(key_names(run.world(), (skill,)))
            # No wait for the cast in flight: `press_skill` waits for the character (one here cost 0.39 s).
            if run.pad is not None:
                run.pad.aim_place((player.x, player.y), found.spot)  # controller mode: a heading (macros/pad.py)
            else:
                where = ground_fraction(player, found.spot[0], found.spot[1], aspect)
                run.actuator.aim(*where, scatter=(4, 3), near=NEAR_AIM)
            aimed = run.clock()
            # Still running from a walk, the character is not where the leg was chosen: re-aim and judge the
            # landing from where it is at the key
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
            with run.lightly():  # only the character's place is wanted
                landing = run.seen(
                    lambda w: cast.note(w) and w.player is not None and landed_from(w.player, origin, spot),
                    max(released + JUMP_SECONDS - run.clock(), KEY_POLL),
                )
            if landing is None:
                if skill in self.delayed and cast.untaken and self.refusals.get(skill, 0) + 1 < REFUSALS:
                    # No cast taken: restore the delay clock, distrust nothing
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
        except Abort as stop:
            if not cut(run, stop):
                self.jump_failed[skill] = run.clock()
            self.refusals.pop(skill, None)
            raise
        self.refusals.pop(skill, None)
        self.jump_failed.pop(skill, None)
        landed_at = run.clock()
        landed = landing.player
        assert landed is not None
        if run.pad is not None:
            run.pad.landing((landed.x, landed.y))  # an astray landing has the next leg walked
        LOG.info(
            'Macro: %s aimed at (%.1f, %.1f), %.1f from (%.1f, %.1f); landed at (%.1f, %.1f), off by %.1f, '
            '%.2fs after the key',
            skill_name(skill), *found.spot, math.dist((origin.x, origin.y), found.spot), origin.x, origin.y,
            landed.x, landed.y,
            math.dist((landed.x, landed.y), found.spot), landed_at - keyed,
        )  # fmt: skip
        self.tally.units += math.dist((origin.x, origin.y), (landed.x, landed.y))
        self.tally.jumps += 1
        herald_pack.hopped(landed_at, math.dist((origin.x, origin.y), (landed.x, landed.y)))  # mark.py REMARK_AFTER_HOP
        if skill in self.delayed:
            self.timed(skill, before, (began, aimed, waited, keyed, released))
            self.landed_at[skill] = landed_at

    def timed(self, skill: int, before: float | None, marks: tuple[float, float, float, float, float]) -> None:
        """Logs a back-to-back delayed jump's key-to-key seconds split into flight, look and choice, aim, delay
        wait and ready, plus the key's hold ("leg time:")."""
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
        """Wait, pointer on the aim, until the skill's delay is over (`left`; a key in it is refused), looking
        every KEY_POLL. A character moved or dead raises `Stale`. Returns the last look's character; None when no
        delay was waited for."""
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
        """During a jump's flight, once the cast has thrown (delay state set, or DELAY_SHOWN with none read: the
        jump goes where the pointer was at the cast), the pointer onto the next leg's aim (`ahead`), so the real
        aim is a step away at most. Only a stop the run honours is raised. `note`: each look, to the caller."""

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
        except Abort as stop:
            if run.stops(stop):
                raise

    def ahead(
        self, run: Run, world: World, ground: Ground | None, aspect: float, landing: Point, goal: Point, intent: Intent
    ) -> Point | None:
        """The aim of the leg after a landing at `landing`, delays taken as over, when it is a delayed jump again: a
        guess for the pointer alone. None otherwise."""
        player = world.player
        assert player is not None
        there = replace(world, player=replace(player, x=landing[0], y=landing[1], cooldown=None))
        facts = replace(move_facts(run, there, ground, aspect, self), last_used={})
        movement = navigator(self.sets, facts)
        found = None if movement is None else movement.leg(facts, goal, intent)
        return found.spot if isinstance(found, Step) and found.skill in self.delayed else None

    def paced(self, now: float | None, why: str) -> None:
        """Logs the level run's pace and begins a new tally."""
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
        """Make one move: a jump by its skill, or one click's walk. A jump no longer possible (gone from `jumps`
        under `intent`, a wall in a line jump's way) falls to the next, else a walk; a priced one aborts. `goal`:
        a routed move's real goal, for the hop's line and the pointer in flight (`ahead`)."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        skill = found.skill
        self.tally.leg(run.clock())
        if intent.routed and skill == TELEPORT and key_names is not None:
            # A routed Teleport is made as the teleport step's own hop (teleport.py `hop_to`)
            rect = run.actuator.keys.focused_window_rect()
            if rect is None:
                raise Abort('no game window')
            tile = (found.spot[0] / TILE_UNITS, found.spot[1] / TILE_UNITS)
            end = found.spot if goal is None else goal  # the hop's log line names the goal's distance
            mark = Target(
                player.area, (), (end[0] / TILE_UNITS, end[1] / TILE_UNITS), name or 'the goal', 'hunt', False,
                ground.grids if ground else (),
            )  # fmt: skip
            try:
                hop_to(run, mark, player, rect, tile, 0.0, key_names)
            except Abort as stop:
                if not cut(run, stop):
                    self.jump_failed[TELEPORT] = run.clock()
                raise
            self.jump_failed.pop(TELEPORT, None)
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
            spot = in_view_toward(player, found.spot, aspect) if WALK_PARTWAY else found.spot
            if spot != found.spot:
                LOG.info('Macro: walk: (%.1f, %.1f) is %.0f away, off the screen: walked to (%.1f, %.1f) on its line',
                         *found.spot, math.dist(here, found.spot), *spot)  # fmt: skip
            settled = step_walk(
                run, spot, player, aspect, attackable(world), name=name or 'a better place', hurry=hurry
            )
            self.tally.units += math.dist(here, spot)
            self.tally.walks += 1
            LOG.info(
                'Macro: leg time: walk of %.0f, %.3fs to the character seen going (settle %.3f)',
                math.dist(here, spot), run.clock() - began, settled,
            )  # fmt: skip


def in_view_toward(player: Player, goal: Point, aspect: float) -> Point:
    """`goal` when its ground is in view from the character, else the farthest point of the straight line to it that is
    (halved VIEW_STEPS times); the character's own place when none is."""
    here = (player.x, player.y)
    if in_view(ground_fraction(player, goal[0], goal[1], aspect)):
        return goal
    low, high = 0.0, 1.0
    for _ in range(VIEW_STEPS):
        mid = (low + high) / 2
        point = (here[0] + (goal[0] - here[0]) * mid, here[1] + (goal[1] - here[1]) * mid)
        if in_view(ground_fraction(player, *point, aspect)):
            low = mid
        else:
            high = mid
    return (here[0] + (goal[0] - here[0]) * low, here[1] + (goal[1] - here[1]) * low)


def walked_way(barred: Callable[[Point], bool], start: Point, goal: Point) -> list[Point]:
    """The shortest walk from `start` toward `goal` as cell centres from the first step on, ending on the goal's
    cell, or else on the reached cell nearest the goal if nearer than the start. Empty: no way. No corner cut."""
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


# Units of walked way round a wall a click from afar is trusted to make; beyond, a drop is gone to first. Inferred
# from clicks the client never walked (rca/2026-10-14/run-1214-findings.md §3.2); its pathing limit was not read.
ROUND_CLICK = 5.0


def clear_line(ground: Ground | None, doors: Sequence[Door], here: Point, goal: Point) -> bool:
    """Whether the straight line has no wall, lava or closed door, its end units aside (characters and drops sit on
    unwalkable cells now and then). Open ground, or within 2 units: clear."""
    barred = no_footing(ground, doors)
    away = math.dist(here, goal)
    if barred is None or away <= 2.0:
        return True
    steps = max(1, math.ceil(away * 2))
    line = (
        (here[0] + (goal[0] - here[0]) * k / steps, here[1] + (goal[1] - here[1]) * k / steps) for k in range(steps)
    )
    return not any(barred(point) for point in line if min(math.dist(point, here), math.dist(point, goal)) > 1.0)


def walked_length(ground: Ground | None, doors: Sequence[Door], here: Point, goal: Point) -> float:
    """Units a walk from `here` to `goal` goes: the clear straight line, else the walked way round (`walked_way`);
    inf where none ends at the goal (rca/2026-10-14/run-1932-findings.md §1.2.3)."""
    if clear_line(ground, doors, here, goal):
        return math.dist(here, goal)
    barred = no_footing(ground, doors)
    assert barred is not None  # only read ground or a closed door bars a line
    path = walked_way(barred, here, goal)
    if not path or math.dist(path[-1], goal) > 1.5:
        return math.inf
    return sum(math.dist(one, other) for one, other in zip((here, *path), path, strict=False))


def walk_reaches(ground: Ground | None, doors: Sequence[Door], here: Point, goal: Point, reach: float) -> bool:
    """Whether a click on a drop walks the character to it: within `reach` on a clear line, or by a walked way no
    longer than ROUND_CLICK. "Near enough to click" for hunting/judging.py and pickup.py; further, the drop is gone
    to first (rca/2026-10-14/run-0025-findings.md §2.2, run-1214-findings.md §3.2)."""
    if math.dist(here, goal) > reach:
        return False
    if clear_line(ground, doors, here, goal):
        return True
    return walked_length(ground, doors, here, goal) <= min(reach, ROUND_CLICK)


ROUND_OPEN = 1.5  # an object off a clear line is opened only if the walk round is at most this times the line


def open_reaches(ground: Ground | None, doors: Sequence[Door], here: Point, goal: Point, reach: float) -> bool:
    """Whether a click on an object opens it soon: within `reach` on a clear line, or a walk round at most
    ROUND_OPEN times the line (a chest behind a shack wall was walked round 43-55 units;
    rca/2026-10-17/slow-legs-findings.md §5)."""
    away = math.dist(here, goal)
    if away > reach:
        return False
    if clear_line(ground, doors, here, goal):
        return True
    return walked_length(ground, doors, here, goal) <= ROUND_OPEN * away


def step_line(step: Step | None, here: Point) -> str:
    """A step for the log."""
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
    """Click the ground at `goal` and see the character going, `clicks` times at most. Raises `Covered` with one of
    `alive` under the pointer (the click would attack). Only a casting character is settled first; a repeat always
    is. `hurry` (pursuit.py `Move.dodge`): no settle, repeated settled if unseen. Returns the seconds settling."""
    where = ground_fraction(player, goal[0], goal[1], aspect)
    if not in_view(where):
        raise Abort(f'the place near {name} is not in view')
    run.say(f'Walking {math.dist((player.x, player.y), goal):.0f} toward {name}')
    if run.pad is not None:
        # Controller mode: the stick held toward it (macros/pad.py); nothing is attacked on the way.
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
            if over is not None and over[0] == MONSTER_UNIT:
                under = [m for m in alive if m.unit_id == over[1] and math.dist((m.x, m.y), goal) <= HOVER_UNITS]
                if under:
                    raise Covered(f'{label(under[0])} is under the pointer there', (under[0].unit_id,))
            if over is not None and (
                (WALK_OFF_LABELS and over[0] == ITEM_UNIT and not wanted_item(run, over[1])) or closed_seal(run, over)
            ):
                where = off_item_labels(run, player, goal, aspect, where, over, alive, name)
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


def closed_seal(run: Run, over: tuple[int, int] | None) -> bool:
    """Whether `over` (the unit under the pointer) is a Chaos Sanctuary seal not opened yet (WALK_OFF_SEALS): a walk's
    click on it would open it."""
    if not WALK_OFF_SEALS or over is None or over[0] != OBJECT_UNIT or run.things is None:
        return False
    return any(t.unit_id == over[1] and t.txt_id in SEALS and not t.mode for t in run.things())


def wanted_item(run: Run, unit: int) -> bool:
    """Whether item `unit` is a valuable or gold the read's pickup takes (a walk's click on it takes it, as wanted)."""
    if run.loot is None:
        return False
    return any(drop.unit_id == unit and drop.kind in (VALUABLE, GOLD) for drop in run.loot().drops)


def off_item_labels(
    run: Run,
    player: Player,
    goal: Point,
    aspect: float,
    where: tuple[float, float],
    over: tuple[int, int],
    alive: Sequence[Monster],
    name: str,
) -> tuple[float, float]:
    """Where a walk toward `goal` is clicked with item `over` (WALK_OFF_LABELS) or a closed seal (WALK_OFF_SEALS)
    under the pointer at `where`: the first WALK_LABEL_SHIFTS point in view with no item, closed seal or one of
    `alive` under it, the pointer left there; with none, `where` again (the pointer put back)."""
    here = (player.x, player.y)
    length = math.dist(here, goal)
    along = ((goal[0] - here[0]) / length, (goal[1] - here[1]) / length) if length > 0 else (1.0, 0.0)
    across = (-along[1], along[0])
    tried = [f'{over}']
    assert run.hovered is not None  # the caller read it
    for forth, side in WALK_LABEL_SHIFTS:
        point = (goal[0] + along[0] * forth + across[0] * side, goal[1] + along[1] * forth + across[1] * side)
        if length + forth <= 0:
            continue
        shifted = ground_fraction(player, *point, aspect)
        if not in_view(shifted):
            continue
        run.actuator.aim(*shifted, scatter=(2, 2))
        run.pace.sleep(HOVER_SECONDS)
        now = run.hovered()
        foe = now is not None and now[0] == MONSTER_UNIT and any(m.unit_id == now[1] for m in alive)
        if now is not None and (foe or (now[0] == ITEM_UNIT and not wanted_item(run, now[1])) or closed_seal(run, now)):
            tried.append(f'{forth:+.1f}/{side:+.1f}: {now}')
            continue
        LOG.info(
            'Macro: walk toward %s: %s %s under the click at (%.1f, %.1f): clicked at (%.1f, %.1f) instead (%s)',
            name, 'an item' if over[0] == ITEM_UNIT else 'a closed seal', over, *goal, *point, ', '.join(tried),
        )  # fmt: skip
        return shifted
    LOG.info(
        'Macro: walk toward %s: an item under every aim near (%.1f, %.1f) (%s): clicked where aimed',
        name, *goal, ', '.join(tried),
    )  # fmt: skip
    run.actuator.aim(*where, scatter=(2, 2))
    return where


def free(run: Run) -> bool:
    """Whether a light look has the character free to act (no cast under way)."""
    with run.lightly():
        seen = run.world().player
    return seen is not None and seen.mode not in ACTING
