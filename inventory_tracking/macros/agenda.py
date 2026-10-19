"""The goal agenda: a prioritized queue of goals, a stack of packages, and a level run's next target
(macros/goals-plan.md, the player's design of 2026-10-19).

`Agenda.next` gives the stack's top while there is one, else the queue's best goal (lowest tier, then nearest), else
LEAVE_GAME; out of a game NEW_GAME. "Every loop has it's own metric ... the only thing that has more priority - proper
interactions with drops" (the player, 2026-10-19): every drop tier is above every metric tier, in a level and at the
game's level (no LEAVE_GAME with a valuable on the ground).

Game-level goals are one KP_6 leg each (macros/tzloop.py); in-level goals are a level run's targets, asked at each
look (`in_level`, from `Hunter.agenda_target`). Pure. Safety is no goal: the arbiter and drinking act in every look.
"""

import math
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from inventory_tracking.common import LOG
from inventory_tracking.levels.geometry import Point
from inventory_tracking.macros.goals import GUARD_NEAR


# Game-level goals: one leg of the loop each
NEW_GAME, WAYPOINT, TOWN_ROUTINE = 'new game', 'waypoint', 'town routine'
PORTAL_TO_TOWN, THROUGH_PORTAL, RESUME = 'portal to town', 'through the portal', 'resume'
LEVEL, LOOT, PICKUP, NEXT_LEVEL, LEAVE_GAME = 'level', 'loot', 'pickup', 'next level', 'leave game'
# In-level goals: a level run's targets (PICKUP is both: a side drop in a level, a remembered valuable at a leg)
KILL, EXPLORE, NAVIGATE = 'kill', 'explore', 'navigate'
# A closed super chest ("add superchests to intemediate goals and open them along the way", the player, 2026-10-19)
OPEN = 'open'

# How a level run works an area (goals-plan.md §6): "full clear tz: for herald hunting - tz leveling: clear only
# elites/champs" (the player, 2026-10-19).
COVER = 'cover'  # TZ leveling: every leader found, nearest first, and the unexplored rooms
ON_THE_WAY = 'on the way'  # TZ leveling: the leaders in the read and remembered near, then the area's end goal
FULL_CLEAR = 'full clear'  # Full clear TZ: every hostile and every room (the Heralds come of the group's kills)

# In-level tiers (goals-plan.md §3), lowest first. Drops come before the metric; a Herald comes to the character
# anyway. CHEST after the leaders in the read (they come at a character standing at a chest), before the rest.
HERALD, OMEN, DROP_GUARD, DROP, LEADER, CHEST, LEADER_NEAR, ROOM, LEADER_FAR = range(9)
# The game-level tiers: the stack (0) first; a valuable on the ground before the metric's legs
STACK, SIGHTED, ERRAND, WORK, LOOTING, ONWARD, EXCURSION = 0, 10, 20, 30, 40, 50, 60
# Units: on an ON_THE_WAY area a leader in the read further off is not gone for (goals-plan.md open question 1)
WAY_UNITS = 90.0
# A remembered leader this near is gone for before the next room, one further after the tour ("we starts to go from
# one side to another back and forward", the player, 2026-10-18). A test holds it equal to hunt.py REMEMBERED_NEAR.
REMEMBERED_NEAR = 45.0
# Units: a super chest (objects.txt 397 ConsolationChest) this near is opened on the way; one further is a detour the
# metric does not pay for. A test holds it equal to hunt.py SUPER_NEAR.
CHEST_NEAR = 60.0
TRIES = 3  # a goal whose leg stopped this often in a game is dropped, said (progress-or-back-off)

# levels.txt Act (d2data levels.json, 2026-10-19): each act's town is its first level
TOWNS = (1, 40, 75, 103, 109)
PANDEMONIUM_FORTRESS = 103


def town_of(area: int) -> int:
    """The town of level `area`'s act: where its Town Portal leads."""
    return next(town for town, end in zip(TOWNS, (40, 75, 103, 109, 10**6), strict=True) if area < end)


@dataclass(frozen=True)
class Objective:
    """One goal. `tier` orders it (lowest first, then nearest); `area` None means any; `place` in world units; `unit`
    the monster or item; `to` the level it leads into; `exit` how a town routine ends (town.py `Exit`)."""

    kind: str
    label: str
    tier: int
    area: int | None = None
    place: Point | None = None
    unit: int | None = None
    to: int | None = None
    exit: str = ''

    @property
    def key(self) -> tuple:
        if self.unit is not None:
            return (self.kind, self.unit)
        return (self.kind, self.area, self.to, self.exit)


@dataclass(frozen=True)
class Leader:
    """A champion, unique or boss (any hostile on a full clear), in sight (`live`) or remembered alive."""

    unit: int
    place: Point
    label: str
    herald: bool = False
    live: bool = True


@dataclass(frozen=True)
class LevelView:
    """What a level run's look hands the agenda (hunting/choice.py `agenda_target`). `omens`: (spot, stand) of a
    Herald coming; `side`: the drop the pickup takes now; `frontier()`: the next unexplored room, asked lazily;
    `passed(place, unit)`: a target with no progress for a while; `chests`: closed super chests in the read; `spent`:
    super chests open or tried out."""

    area: int
    here: Point
    leaders: tuple[Leader, ...] = ()
    hostiles: tuple[tuple[int, Point], ...] = ()
    omens: tuple[tuple[Point, Point], ...] = ()
    side: Objective | None = None
    frontier: Callable[[], tuple[Point, str] | None] | None = None
    policy: str = COVER
    passed: Callable[[Point, int | None], bool] = lambda place, unit: False
    omen_near: float = 22.0  # hunt.py OMEN_NEAR, handed in
    chests: tuple[tuple[int, Point], ...] = ()
    spent: frozenset[int] = frozenset()


def kill(area: int, unit: int, place: Point, label: str, tier: int = LEADER) -> Objective:
    return Objective(KILL, label, tier, area, place, unit)


def room_package(area: int) -> tuple[Objective, ...]:
    """The trip to town for room from `area` (the player's example package, 2026-10-19): Town Portal, the Fortress
    visit (macros/visit.py), back to the portal's town, through the portal, on. In act 4 no waypoint either way."""
    town = town_of(area)
    goals = [Objective(PORTAL_TO_TOWN, 'Town Portal for room', STACK, area, to=town)]
    if town != PANDEMONIUM_FORTRESS:
        goals.append(Objective(WAYPOINT, 'to the Fortress for the visit', STACK, to=PANDEMONIUM_FORTRESS))
    goals.append(
        Objective(TOWN_ROUTINE, 'the town visit', STACK, exit='portal' if town != PANDEMONIUM_FORTRESS else 'leave')
    )
    if town != PANDEMONIUM_FORTRESS:
        goals.append(Objective(WAYPOINT, "back to the portal's town", STACK, to=town))
    goals.append(Objective(THROUGH_PORTAL, 'back through the portal', STACK, to=area))
    goals.append(Objective(RESUME, 'continue the run', STACK, area))
    return tuple(goals)


@dataclass
class Agenda:
    """The game's goals; a new `game` starts them afresh. `queue`: the game-level goals last derived; `stack`: the
    packages, top last; `kills`/`chests`: KILL/OPEN goals by unit; `opened`: chests never targeted again; `worked`:
    self-ended level runs per area; `finished`: areas done; `failures`: stops by goal."""

    game: object | None = None
    queue: dict[tuple, Objective] = field(default_factory=dict)
    stack: list[Objective] = field(default_factory=list)
    kills: dict[int, Objective] = field(default_factory=dict)
    chests: dict[int, Objective] = field(default_factory=dict)
    opened: set[int] = field(default_factory=set)
    worked: Counter[int] = field(default_factory=Counter)
    finished: set[int] = field(default_factory=set)
    failures: Counter[tuple] = field(default_factory=Counter)
    dropped: set[tuple] = field(default_factory=set)
    said: str | None = None
    plan: object | None = None  # the game's itinerary (macros/tzroutine.py `Itinerary`), set by macros/tzloop.py

    def begin(self, game: object) -> bool:
        """Start afresh (stack discarded) when `game` is new; whether it was."""
        if game == self.game:
            return False
        if self.stack:
            LOG.info('Macro: agenda: a new game: the package %s discarded', [goal.label for goal in self.stack])
        self.game, self.queue, self.stack, self.kills = game, {}, [], {}
        self.chests, self.opened = {}, set()
        self.worked, self.finished, self.failures, self.dropped = Counter(), set(), Counter(), set()
        self.plan = None
        return True

    def push(self, *goals: Objective) -> None:
        """Push a package so `goals[0]` comes first."""
        self.stack.extend(reversed(goals))
        LOG.info('Macro: agenda: package pushed: %s', ' -> '.join(goal.label for goal in goals))

    def refresh(self, goals: Iterable[Objective]) -> None:
        """Replace the queue with the producers' goals ("re-plan, never resume"); dropped goals stay out."""
        self.queue = {goal.key: goal for goal in goals if goal.key not in self.dropped}

    def next(self, here: Point | None, *, in_game: bool = True, valuable: str | None = None) -> Objective:
        """The goal to work now: the stack's top (a RESUME ends its package), else the queue's best, else a PICKUP
        of `valuable` still on the ground, else LEAVE_GAME. Out of a game, NEW_GAME."""
        if not in_game:
            return Objective(NEW_GAME, 'the next game', STACK)
        while self.stack and self.stack[-1].kind == RESUME:
            done = self.stack.pop()
            LOG.info('Macro: agenda: package done: %s', done.label)
        if self.stack:
            return self.told(self.stack[-1])
        if self.queue:
            return self.told(min(self.queue.values(), key=lambda goal: (goal.tier, cost(goal, here))))
        if valuable is not None:
            return self.told(Objective(PICKUP, f'{valuable}, before leaving', SIGHTED))
        return self.told(Objective(LEAVE_GAME, 'no goals left', EXCURSION))

    def told(self, goal: Objective) -> Objective:
        """`goal`, logged when it changes."""
        if goal.label != self.said:
            self.said = goal.label
            source = 'stack' if self.stack and self.stack[-1] is goal else 'queue'
            LOG.info('Macro: agenda: next %s: %s (%s, tier %d)', goal.kind, goal.label, source, goal.tier)
        return goal

    def done(self, goal: Objective) -> None:
        """`goal`'s leg ended without a stop: remove it."""
        if self.stack and self.stack[-1] == goal:
            self.stack.pop()
        self.queue.pop(goal.key, None)
        self.failures.pop(goal.key, None)

    def failed(self, goal: Objective) -> bool:
        """`goal`'s leg stopped; whether it is now dropped for the game (TRIES)."""
        self.failures[goal.key] += 1
        if self.failures[goal.key] < TRIES:
            return False
        LOG.info('Macro: agenda: %s dropped: its leg stopped %d times in this game', goal.label, TRIES)
        self.dropped.add(goal.key)
        self.queue.pop(goal.key, None)
        if self.stack and self.stack[-1] == goal:
            self.stack.pop()
        return True

    def ran(self, area: int | None) -> None:
        """A level run of `area` ended by itself."""
        if area is not None:
            self.worked[area] += 1

    def finish(self, area: int | None) -> None:
        """Level `area` is done."""
        if area is not None and area not in self.finished:
            self.finished.add(area)
            LOG.info('Macro: agenda: level %d done', area)

    def observe(self, view: LevelView) -> None:
        """Update the KILL goals from `view`'s leaders (one of this level no longer known is dropped) and the OPEN
        goals from its closed super chests (kept out of the read; dropped for the game once spent)."""
        present = {leader.unit for leader in view.leaders}
        for unit, goal in list(self.kills.items()):
            if goal.area == view.area and unit not in present:
                del self.kills[unit]
        for leader in view.leaders:
            tier = HERALD if leader.herald else LEADER if leader.live else LEADER_NEAR
            self.kills[leader.unit] = kill(view.area, leader.unit, leader.place, leader.label, tier)
        for unit in view.spent:
            self.chests.pop(unit, None)
            self.opened.add(unit)
        for unit, place in view.chests:
            if unit not in self.opened:
                self.chests[unit] = Objective(OPEN, 'Super chest', CHEST, view.area, place, unit)

    def in_level(self, view: LevelView) -> Objective | None:
        """The level run's next target (goals-plan.md §3), first match: a live Herald; a Herald's omen; the side
        drop's guards, then the drop; a leader in sight; a super chest within CHEST_NEAR; a leader remembered within
        REMEMBERED_NEAR; on COVER/FULL_CLEAR the next room, then leaders further. None: the area's end goal is next."""
        self.observe(view)
        here = view.here

        def away(place: Point) -> float:
            return math.dist(here, place)

        def where(goal: Objective) -> Point:
            return goal.place if goal.place is not None else here

        known = [
            goal for goal in self.kills.values() if goal.area == view.area and not view.passed(where(goal), goal.unit)
        ]
        live = {leader.unit for leader in view.leaders if leader.live}
        heralds = [goal for goal in known if goal.tier == HERALD and goal.unit in live]
        if heralds:
            return min(heralds, key=lambda goal: away(where(goal)))
        if view.omens:
            spot, stand = min(view.omens, key=lambda omen: away(omen[0]))
            near = [(unit, place) for unit, place in view.hostiles if math.dist(spot, place) <= view.omen_near]
            if near:
                unit, place = min(near, key=lambda found: away(found[1]))
                return kill(view.area, unit, place, 'the hostile by the Herald coming', OMEN)
            if not view.passed(stand, None):
                return Objective(NAVIGATE, 'the stand for the Herald coming', OMEN, view.area, stand)
        side = view.side
        if side is not None and side.place is not None:
            drop = side.place
            guards = [
                (unit, place)
                for unit, place in view.hostiles
                if min(math.dist(place, drop), away(place)) <= GUARD_NEAR and not view.passed(place, unit)
            ]
            if guards:
                unit, place = min(guards, key=lambda found: away(found[1]))
                return kill(view.area, unit, place, f'a guard of {side.label}', DROP_GUARD)
            return side
        reach = WAY_UNITS if view.policy == ON_THE_WAY else math.inf
        seen = [goal for goal in known if goal.unit in live and away(where(goal)) <= reach]
        if seen:
            return min(seen, key=lambda goal: away(where(goal)))
        chests = [
            goal
            for goal in self.chests.values()
            if goal.area == view.area and away(where(goal)) <= CHEST_NEAR and not view.passed(where(goal), goal.unit)
        ]
        if chests:
            return min(chests, key=lambda goal: away(where(goal)))
        remembered = [goal for goal in known if goal.unit not in live]
        near = [goal for goal in remembered if away(where(goal)) <= REMEMBERED_NEAR]
        if near:
            found = min(near, key=lambda goal: away(where(goal)))
            return Objective(KILL, found.label, LEADER_NEAR, found.area, found.place, found.unit)
        if view.policy == ON_THE_WAY:
            return None
        room = view.frontier() if view.frontier is not None else None
        if room is not None and not view.passed(room[0], None):
            return Objective(EXPLORE, room[1], ROOM, view.area, room[0])
        if remembered:
            found = min(remembered, key=lambda goal: away(where(goal)))
            return Objective(KILL, found.label, LEADER_FAR, found.area, found.place, found.unit)
        return None

    def known(self, area: int) -> int:
        """The open KILL goals of `area`."""
        return sum(1 for goal in self.kills.values() if goal.area == area)


def cost(goal: Objective, here: Point | None) -> float:
    """Units from `here` to the goal's place; 0 without either."""
    if goal.place is None or here is None:
        return 0.0
    return math.dist(here, goal.place)
