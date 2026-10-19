"""The goal agenda: a prioritized queue of goals, a stack of packages, and the choice of a level run's next target
(macros/goals-plan.md, the player's design of 2026-10-19 ~01:57).

The player: "if we have packaged goal (on stack in our case), we get goals from our stack from the top, one by one
until stack is empty. then we discard stack and continue with prioritized queue"; "we can have clearer signals for
save/restart - when we have no more goals". So `Agenda.next` gives the stack's top while there is one, else the
queue's best goal (the lowest tier, then the nearest), else LEAVE_GAME; out of a game NEW_GAME.

The player, 2026-10-19 ~02:12: "every loop has it's own metric, that it must optimize: boss kills/elites kill/opened
chest. the only thing that has more priority - proper interactions with drops (we cannot run without picking desired
items just with killing boss alone)". Every tier of a drop is above every tier of the metric's goals, in a level
(`in_level`: a side drop and its guards before any leader, room or boss) and at the game's level (PICKUP before
LEVEL, LOOT before NEXT_LEVEL, and no LEAVE_GAME with a valuable on the ground).

Two granularities (goals-plan.md §2): the game-level goals are one KP_6 leg each (macros/tzloop.py performs them);
the in-level ones are a level run's targets, asked at each look of attack mode (`in_level`, from macros/hunt.py
`Hunter.agenda_target`). Pure: nothing here reads the game or sends input. Safety is no goal here: the arbiter and the
drinking act inside every look of every leg.
"""

import math
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from inventory_tracking.common import LOG
from inventory_tracking.macros.goals import GUARD_NEAR


Point = tuple[float, float]

# Game-level goals: one leg of the loop each
NEW_GAME, WAYPOINT, TOWN_ROUTINE = 'new game', 'waypoint', 'town routine'
PORTAL_TO_TOWN, THROUGH_PORTAL, RESUME = 'portal to town', 'through the portal', 'resume'
LEVEL, LOOT, PICKUP, NEXT_LEVEL, LEAVE_GAME = 'level', 'loot', 'pickup', 'next level', 'leave game'
# In-level goals: a level run's targets (PICKUP is both: a side drop in a level, a remembered valuable at a leg)
KILL, EXPLORE, NAVIGATE = 'kill', 'explore', 'navigate'
# A closed super chest to open (2026-10-19, the player: "we don't open intermediate goals, like superchests. probably we
# should add superchests to intemediate goals and open them along the way")
OPEN = 'open'

# How a level run works an area (goals-plan.md §6). The player, 2026-10-19 ~02:12: "we're going to have separate
# mods: - full clear tz : for herald hunting - tz leveling: clear only elites/champs".
COVER = 'cover'  # TZ leveling: every leader found, nearest first, and the unexplored rooms
ON_THE_WAY = 'on the way'  # TZ leveling: the leaders in the read and remembered near, then the area's end goal
FULL_CLEAR = 'full clear'  # Full clear TZ: every hostile and every room (the Heralds come of the group's kills)

# The in-level tiers (goals-plan.md §3), lowest first. The drops' (DROP_GUARD, DROP) come before every goal of the
# metric (the ruling of 02:12); a Herald and its omen are the fight that comes to the character anyway. CHEST
# (2026-10-19, the player: "we should add superchests to intemediate goals and open them along the way"): a closed super
# chest within CHEST_NEAR comes after the leaders in the read (they are the metric, and they come at a character that
# stands at a chest) and before the leaders out of sight, the rooms and the area's end goal; its spill is then the drop
# tiers'.
HERALD, OMEN, DROP_GUARD, DROP, LEADER, CHEST, LEADER_NEAR, ROOM, LEADER_FAR = range(9)
# The game-level tiers: the stack (0) first; a valuable on the ground before the metric's legs
STACK, SIGHTED, ERRAND, WORK, LOOTING, ONWARD, EXCURSION = 0, 10, 20, 30, 40, 50, 60
# Units: on an ON_THE_WAY area a leader in the read further off than this is not gone for (about two screens' width
# of the way; open question 1 of goals-plan.md)
WAY_UNITS = 90.0
# A leader remembered alive this near is gone for before the next room; one further waits for the tour's end
# (hunt.py REMEMBERED_NEAR, the player 2026-10-18 00:10: "we starts to go from one side to another back and forward";
# a test holds them equal)
REMEMBERED_NEAR = 45.0
# Units (2026-10-19): a super chest (objects.txt 397 ConsolationChest, "sparklychest") seen this near the character is
# opened on the way; one further is not gone for, so no chest seen far off sends the run across the level (a side goal
# worth a short detour, not a reason to explore: the TZ leveling loop's metric is elite kills an hour). 60 is the full
# clear's own bound (hunt.py SUPER_NEAR; a test holds them equal): about three Teleport hops of 26, a second or so there
CHEST_NEAR = 60.0
TRIES = 3  # a goal whose leg stopped this often in a game is dropped, said (progress-or-back-off)

# levels.txt Act (third-parties/d2data/json/levels.json, read 2026-10-19): act 1 levels 0-39, act 2 40-74, act 3
# 75-102, act 4 103-108, act 5 109-137; each act's town is its first level
TOWNS = (1, 40, 75, 103, 109)
PANDEMONIUM_FORTRESS = 103


def town_of(area: int) -> int:
    """The town of level `area`'s act: where its Town Portal leads."""
    return next(town for town, end in zip(TOWNS, (40, 75, 103, 109, 10**6), strict=True) if area < end)


@dataclass(frozen=True)
class Objective:
    """One goal. `tier` orders it (lowest first; within a tier the nearest); `area` is the level it is of (None: any,
    a town's or the lobby's); `place` where, in world units; `unit` the monster or the item it is for; `to` the level
    it leads into (a waypoint, the way on); `exit` how a town routine ends (macros/town.py `Exit` values)."""

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
    """A champion, unique, super unique or boss (or, on a full clear, any hostile) the level run knows of: in sight
    (`live`) or remembered alive where it was last seen."""

    unit: int
    place: Point
    label: str
    herald: bool = False
    live: bool = True


@dataclass(frozen=True)
class LevelView:
    """What a level run's look hands the agenda (macros/hunting/choice.py `agenda_target`). `hostiles`: (unit, place) of
    every hostile in the read, a drop's guards among them; `omens`: (spot, stand) of a Herald coming; `side`: the drop
    the pickup rules take now (a PICKUP); `frontier()`: the next unexplored room (place, what), asked only when it is
    wanted; `passed(place, unit)`: a target the run passed for a while (no progress toward it); `chests`: (unit, place)
    of the closed super chests in the read; `spent`: the super chests seen open, or tried out (never targets again)."""

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
    """The trip to town for room from level `area` (the player's example: "we need to empty the inventory -> create
    teleport -> put on stack continue run -> put on stack go back through teleport in town act 1 -> put on stack do
    town routine (identify/store/etc) -> put on stack go through just create teleport"): Town Portal, the Fortress's
    visit (macros/visit.py: its Cain, stash, Jamella and Halbu), back to the portal's town, through it, and on. The
    portal's town in act 4 is the Fortress: no waypoint either way, the visit walks nowhere after (`leave`)."""
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
    """The game's goals (the module text). `game`: the game they are of (macros/loop.py `GameId`); a new one starts
    them afresh. `queue`: the game-level goals as the producers last derived them (`refresh`); `stack`: the
    packages, top last; `kills`: the KILL goals of the leaders the level runs saw, by unit; `chests`: the OPEN goals of
    the closed super chests seen, by unit, and `opened` those seen open or tried out (never again); `worked`: the level
    runs of each area that ended by themselves; `finished`: the areas left done; `failures`: stops by goal."""

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
        """The goals of `game`: another than the last one's starts afresh, the stack discarded. Whether it did."""
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
        """A package onto the stack: pushed in reverse, so `goals[0]` comes first and the last given last."""
        self.stack.extend(reversed(goals))
        LOG.info('Macro: agenda: package pushed: %s', ' -> '.join(goal.label for goal in goals))

    def refresh(self, goals: Iterable[Objective]) -> None:
        """The game-level goals the producers want now (macros/tzroutine.py `produce`), in place of the last: they are
        derived from the facts at every leg ("re-plan, never resume"). A goal dropped for its failures stays out."""
        self.queue = {goal.key: goal for goal in goals if goal.key not in self.dropped}

    def next(self, here: Point | None, *, in_game: bool = True, valuable: str | None = None) -> Objective:
        """The goal to work now: the stack's top (a RESUME on it ends its package: popped and said, the queue goes
        on), else the queue's lowest tier, the nearest of it; else, with a valuable known on the ground (`valuable`,
        the sightings'), its PICKUP; else LEAVE_GAME: no goals left. Out of a game, NEW_GAME."""
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
        """`goal`, said when it is another than the last one given (`Macro: agenda: next ...`)."""
        if goal.label != self.said:
            self.said = goal.label
            source = 'stack' if self.stack and self.stack[-1] is goal else 'queue'
            LOG.info('Macro: agenda: next %s: %s (%s, tier %d)', goal.kind, goal.label, source, goal.tier)
        return goal

    def done(self, goal: Objective) -> None:
        """`goal`'s leg ended without a stop: off the stack's top, out of the queue."""
        if self.stack and self.stack[-1] == goal:
            self.stack.pop()
        self.queue.pop(goal.key, None)
        self.failures.pop(goal.key, None)

    def failed(self, goal: Objective) -> bool:
        """`goal`'s leg stopped; whether it is dropped for it (TRIES in this game), said."""
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
        """A level run of `area` ended by itself (its route's end, nothing left to go for)."""
        if area is not None:
            self.worked[area] += 1

    def finish(self, area: int | None) -> None:
        """Level `area` is left done: its excursion goes on past it."""
        if area is not None and area not in self.finished:
            self.finished.add(area)
            LOG.info('Macro: agenda: level %d done', area)

    def observe(self, view: LevelView) -> None:
        """The KILL goals of the leaders in `view` (the TZ leveling routine: "creates KillGoal for every elite/champ
        that it discovers"): each one seen or remembered alive kept with its last place; one of this level that is
        neither any more is dead or gone where it was seen, and dropped. An OPEN goal for every closed super chest in
        `view` (kept while it is out of the read: "seen on this level and not yet opened"); one seen open or tried
        out is dropped for the game."""
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
        """The level run's next target (goals-plan.md §3), first match: a live Herald; a Herald's omen (the hostile
        nearest its spot, else the stand by it); the side drop's guards (hostiles within GUARD_NEAR of it or of the
        character) and then the drop; a leader in sight (ON_THE_WAY: within WAY_UNITS); a closed super chest within
        CHEST_NEAR (every policy); a leader remembered within REMEMBERED_NEAR; on COVER and FULL_CLEAR the next
        unexplored room, then the leaders remembered further. None: nothing of the agenda's, and the area's end goal
        (the route's boss, object or door) is the run's."""
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
        """The KILL goals of level `area` still open."""
        return sum(1 for goal in self.kills.values() if goal.area == area)


def cost(goal: Objective, here: Point | None) -> float:
    """Units from `here` to the goal's place; 0 for a goal with none (a leg's), or with the character unread."""
    if goal.place is None or here is None:
        return 0.0
    return math.dist(here, goal.place)
