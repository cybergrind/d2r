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
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.goals import GUARD_NEAR


# Game-level goals: one leg of the loop each
NEW_GAME, WAYPOINT, TOWN_ROUTINE = 'new game', 'waypoint', 'town routine'
PORTAL_TO_TOWN, THROUGH_PORTAL, RESUME = 'portal to town', 'through the portal', 'resume'
# Runs of a level done ending with nothing left to go to that are no way on (`Agenda.nothing_left`)
NOTHING_LEFT_ENDS = 5
LEVEL, LOOT, PICKUP, NEXT_LEVEL, LEAVE_GAME = 'level', 'loot', 'pickup', 'next level', 'leave game'
# A trip that starts in the town it leaves on foot: Blood Moor, Rocky Waste, Outer Steppes (macros/townexit.py)
WALK_OUT = 'walk out'
# The Gheed's swap (macros/charms.py; the player, 2026-10-18: "put our own gheed into SHARED tab; go back and pick new
# one; go to town, identify; check what is better"), as a package (`gheeds_package`, 2026-10-19)
SWAP_AWAY, SWAP_PARK, SWAP_PICK = "gheed's away", "gheed's park", "gheed's pick"
SWAP_HOME, SWAP_CHOOSE = "gheed's home", "gheed's choose"
SWAP_GOALS = frozenset((SWAP_AWAY, SWAP_PARK, SWAP_PICK, SWAP_HOME, SWAP_CHOOSE))
# A Worldstone Shard used in the Fortress at a game's start (macros/actloop.py, macros/terrorize.py; the player,
# 2026-10-20 ~18:50: "terrorize with worldstone shards whole act and go whole act, zone by zone")
TERRORIZE = 'terrorize act'
# In-level goals: a level run's targets (PICKUP is both: a side drop in a level, a remembered valuable at a leg)
KILL, EXPLORE, NAVIGATE = 'kill', 'explore', 'navigate'
# A closed super chest ("add superchests to intemediate goals and open them along the way", the player, 2026-10-19)
OPEN = 'open'

# How a level run works an area (goals-plan.md §6): "full clear tz: for herald hunting - tz leveling: clear only
# elites/champs" (the player, 2026-10-19).
COVER = 'cover'  # TZ leveling: every leader found, nearest first, and the unexplored rooms
ON_THE_WAY = 'on the way'  # TZ leveling: the leaders in the read and remembered near, then the area's end goal
FULL_CLEAR = 'full clear'  # Full clear TZ: every hostile and every room (the Heralds come of the group's kills)
# Both TZ kinds on a level not terrorized (crossed to reach one, or off the trip): the route's way on only, no leader,
# no room, no boss. The player, 2026-10-19 ~21:56: "when we're running tz leveling loop - it should run within terror
# zones"
TRANSIT = 'transit'
# A level of the zone the zone moved on from under its run (the tracker reads it not terrorized now): the run ends
# there, its drops picked up; the agenda then makes for the new zone (23:30 on 2026-10-19)
ZONE_LEFT = 'zone left'
# TZ+, the TZ leveling kind's default since 2026-10-20 (macros/tzroutine.py TZ_PLUS). The player, ~18:50: "add another
# mode TZ+: it tries to kill slightly more mobs on levels with not so many mobs to get herald spawn ... we don't want
# to clear very large levels with 300 mobs or so ... we just kill reasonable groups and if herald doesn't spawn - we're
# fine, we don't want to kill alone mobs in the corners"; ~18:58: "fore levels with 300+ mobs - we just clear big
# groups and elites/champions". PLUS: COVER's leaders and rooms, and the reasonable groups in the read (`groups`);
# PLUS_WAY: ON_THE_WAY's, and the groups (a big level on the way to a boss, a boss that comes to a stand).
PLUS = 'tz+'
PLUS_WAY = 'tz+ on the way'
GROUPS_TAKEN = frozenset((PLUS, PLUS_WAY))
WAYS_ON = frozenset((ON_THE_WAY, PLUS_WAY))  # the leaders near, then the area's end goal: no room is explored
# Hostiles: a level of this many (terror/zones.py `level_population`) and more is big: only its big groups and its
# leaders are gone for, never a clear. The player's own number ("300 mobs or so"). Exp an hour agrees (2026-10-20,
# 16:48-18:55, in-level time): Frozen Tundra (374), every room explored, 9.9M an hour, under the loop's 11-12M an hour
# over whole games; the small levels made 13-20M (Halls of the Dead 1-3 14-20M, Jail 1-3 13-16M, Outer Steppes 15.6M).
BIG_LEVEL = 300
# Hostiles within GROUP_LINK units of one another (one linked chain) are one group. 15 units is 3 tiles: a pack as
# it spawns and stands; under the strike's 20 (combat/policy.py STRIKE_REACH), so a group's first cast reaches more.
GROUP_LINK = 15.0
# A group of this many is gone for on a level under BIG_LEVEL; fewer (a pair, a lone monster in a corner) are left.
# A detour within GROUP_NEAR is ~1 s of hops each way and ~2 s of fight for 4 kills (1.75 kills a second in combat,
# ~2.7k exp a kill: 2026-10-20's sessions): ~11k exp in ~4 s, ~10M an hour plus the Herald's share, about the loop's
# own rate; three would be under it.
GROUP_MIN = 4
# On a big level only groups of this many: twice the exp for the same detour, as its own rate is under the loop's.
BIG_GROUP = 8
# Units: a group's nearest member further than this is no detour the metric pays (a screen, as CHEST_NEAR, USE_NEAR);
# the tour brings the rest near, and what is never near is left ("we don't want to hunt every mob").
GROUP_NEAR = 60.0

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
# The route's next object on the level (a seal, a chest: a `use` stage leading nowhere else) this near goes before a
# farther room of the tour or a leader remembered far: in game 30 (2026-10-19) Vizier seal 2 stood 40 units from seal 1
# and Infector seal 2 43 from seal 1, and the tour went 184 and 213 units away first (~29 s;
# rca/2026-10-19/game30-run-findings.md S3). About a screen. False: the tour first, as before.
USE_FIRST = True
USE_NEAR = 60.0
TRIES = 3  # a goal whose leg stopped this often in a game is dropped, said (progress-or-back-off)

# levels.txt Act (d2data levels.json, 2026-10-19): each act's town is its first level
TOWNS = (1, 40, 75, 103, 109)
PANDEMONIUM_FORTRESS = 103


def town_of(area: int) -> int:
    """The town of level `area`'s act: where its Town Portal leads."""
    return next(town for town, end in zip(TOWNS, (40, 75, 103, 109, 10**6), strict=True) if area < end)


# A game that would end in the act of a town here ends in the town it names: the next game starts there, by the waypoint
# (the player, 2026-10-19: "if we're doing save/exit in any act3 zone in loop, we must use the same routins as LK
# (teleport home -> pandemonium fortress -> save/exit)"). Lower Kurast's own legs make the same way (loop.py `lk_leg`)
KURAST_DOCKS = 75
LEFT_FROM = {KURAST_DOCKS: PANDEMONIUM_FORTRESS}
# A level left for that town by a way of its own once its boss is dead: (boss, way, town). The player, 2026-10-19
# ~22:11: "when we have killed mephisto -- we must go through red portal and do save/exit only when we're in fortress"
# (game 32 was left in Durance 3). Made by the level run, whose route's stage there is that way (catalog/act3.py)
WAYS_OUT = {102: ('Mephisto', 'Red portal', PANDEMONIUM_FORTRESS)}


@dataclass(frozen=True)
class Objective:
    """One goal. `tier` orders it (lowest first, then nearest); `area` None means any; `place` in world units; `unit`
    the monster or item; `to` the level it leads into; `exit` how a town routine ends (town.py `Exit`); `ends`: a step
    of the game's end (`game_end`)."""

    kind: str
    label: str
    tier: int
    area: int | None = None
    place: Point | None = None
    unit: int | None = None
    to: int | None = None
    exit: str = ''
    ends: bool = False

    @property
    def key(self) -> tuple:
        if self.unit is not None:
            return (self.kind, self.unit)
        return (self.kind, self.area, self.to, self.exit)


def game_end(area: int | None, dead: frozenset[str] = frozenset()) -> Objective:
    """The goal that ends the game from level `area`: LEAVE_GAME, or in an act whose games end in another town
    (LEFT_FROM) the next step there: the level's own way (WAYS_OUT) with its boss in `dead` (Durance 3's Red portal,
    a LEVEL run to it), else Town Portal home from a field level, the waypoint from the act's town."""
    town = town_of(area) if area is not None else None
    there = LEFT_FROM.get(town) if town is not None else None
    if there is None:
        return Objective(LEAVE_GAME, 'no goals left', EXCURSION)
    name = display_name(there)
    way = WAYS_OUT.get(area) if area is not None else None
    if way is not None and way[0] in dead and way[2] == there:
        return Objective(LEVEL, f'the {way[1]} to {name}: the game ends there', ERRAND, area, to=there, ends=True)
    if area != town:
        return Objective(PORTAL_TO_TOWN, f'Town Portal home: the game ends in {name}', ERRAND, area, to=town, ends=True)
    return Objective(WAYPOINT, f'to {name}: the game ends there', ERRAND, to=there, ends=True)


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
    use_at: Point | None = None  # the route's next object on this level (`Agenda.in_level` USE_FIRST)
    # TZ+ (GROUPS_TAKEN): the hostiles of this level in the read the groups are made of (`groups`), and the level's
    # population (terror/zones.py `level_population`; BIG_LEVEL), None unknown: a level under BIG_LEVEL
    crowd: tuple[tuple[int, Point], ...] = ()
    population: float | None = None

    @property
    def group_size(self) -> int:
        """The fewest hostiles a group gone for has here: BIG_GROUP on a big level, else GROUP_MIN."""
        return BIG_GROUP if self.population is not None and self.population >= BIG_LEVEL else GROUP_MIN


def kill(area: int, unit: int, place: Point, label: str, tier: int = LEADER) -> Objective:
    return Objective(KILL, label, tier, area, place, unit)


def groups(
    crowd: Iterable[tuple[int, Point]], smallest: int, link: float = GROUP_LINK
) -> list[tuple[tuple[int, Point], ...]]:
    """The groups among `crowd` (unit, place): hostiles linked by chains of steps of at most `link` units, `smallest`
    or more of them (TZ+, GROUP_MIN / BIG_GROUP); the rest are left."""
    members = list(crowd)
    parent = list(range(len(members)))

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for first, (_, at) in enumerate(members):
        for second in range(first + 1, len(members)):
            if math.dist(at, members[second][1]) <= link:
                parent[root(first)] = root(second)
    found: dict[int, list[tuple[int, Point]]] = {}
    for index, member in enumerate(members):
        found.setdefault(root(index), []).append(member)
    return [tuple(group) for group in found.values() if len(group) >= smallest]


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


def gheeds_package(area: int) -> tuple[Objective, ...]:
    """The Gheed's swap from level `area` (goals-plan.md §7): Town Portal, the Fortress, the player's onto a shared
    page, back through the portal, the new one picked up, then `gheeds_fetch`."""
    town = town_of(area)
    goals = [Objective(SWAP_AWAY, "Gheed's Fortune away", STACK, area, to=town)]
    if town != PANDEMONIUM_FORTRESS:
        goals.append(Objective(WAYPOINT, 'to the Fortress for the swap', STACK, to=PANDEMONIUM_FORTRESS))
    goals.append(Objective(SWAP_PARK, "Gheed's Fortune onto a shared page", STACK))
    if town != PANDEMONIUM_FORTRESS:
        goals.append(Objective(WAYPOINT, "back to the portal's town", STACK, to=town))
    goals.append(Objective(THROUGH_PORTAL, 'back through the portal', STACK, to=area))
    goals.append(Objective(SWAP_PICK, "the new Gheed's Fortune", STACK, area))
    return (*goals, *gheeds_fetch(area))


def gheeds_fetch(area: int) -> tuple[Objective, ...]:
    """The swap's second half from `area`: Town Portal from a field level, the Fortress, Cain and the choice, back
    through the portal, on. From a town (a new game's, a restart's) the Fortress and the choice only."""
    town, field = town_of(area), area not in TOWNS
    goals = []
    if field:
        goals.append(Objective(SWAP_HOME, "Gheed's Fortunes to compare", STACK, area, to=town))
    if (town if field else area) != PANDEMONIUM_FORTRESS:  # where the portal or the game put the character
        goals.append(Objective(WAYPOINT, 'to the Fortress for the choice', STACK, to=PANDEMONIUM_FORTRESS))
    goals.append(Objective(SWAP_CHOOSE, "the better Gheed's Fortune", STACK))
    if field:
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
    # Levels a run found no way on from, explored (`no_way_on`): their NEXT_LEVEL goals stay out
    wayless: set[int] = field(default_factory=set)
    # Runs of a level done that ended with nothing left to go to (`nothing_left`), by area
    ended_empty: Counter[int] = field(default_factory=Counter)
    # Runs a level had when its boss's trip, which only crossed it, was over (macros/tzloop.py `reopen`): its own trip
    # counts its runs from there
    reopened: dict[int, int] = field(default_factory=dict)
    said: str | None = None
    plan: object | None = None  # the game's itinerary (macros/tzroutine.py `Itinerary`), set by macros/tzloop.py
    policies: dict[int, str] = field(default_factory=dict)  # how each level was last said to be worked (`worked_as`)
    # The act kind's shard this game (macros/actloop.py): None not tried yet, else how it went (actloop.USED ...);
    # `acts` the acts a shard terrorized in this game (planned whatever the client's list reads: tzloop.py `zone_of`)
    shard: str | None = None
    acts: frozenset[int] = frozenset()
    # Games in a row whose shard step failed (kept across games: actloop.py SHARD_FAILURES)
    shard_failures: int = 0

    def begin(self, game: object) -> bool:
        """Start afresh (stack discarded) when `game` is new; whether it was."""
        if game == self.game:
            return False
        if self.stack:
            LOG.info('Macro: agenda: a new game: the package %s discarded', [goal.label for goal in self.stack])
        self.game, self.queue, self.stack, self.kills = game, {}, [], {}
        self.chests, self.opened = {}, set()
        self.worked, self.finished, self.failures, self.dropped = Counter(), set(), Counter(), set()
        self.plan, self.wayless, self.ended_empty = None, set(), Counter()
        self.reopened = {}
        self.policies = {}
        self.shard, self.acts = None, frozenset()
        return True

    def push(self, *goals: Objective) -> None:
        """Push a package so `goals[0]` comes first."""
        self.stack.extend(reversed(goals))
        LOG.info('Macro: agenda: package pushed: %s', ' -> '.join(goal.label for goal in goals))

    def holds(self, kinds: frozenset[str]) -> bool:
        """Whether a package goal of `kinds` is on the stack."""
        return any(goal.kind in kinds for goal in self.stack)

    def cut(self) -> None:
        """The rest of the top goal's package dropped, its RESUME kept: the top's own leg ends it (`done`)."""
        ends = [index for index, goal in enumerate(self.stack[:-1]) if goal.kind == RESUME]
        if ends and ends[-1] + 1 < len(self.stack) - 1:
            dropped = self.stack[ends[-1] + 1 : -1]
            del self.stack[ends[-1] + 1 : -1]
            LOG.info('Macro: agenda: the rest of the package dropped: %s', [goal.label for goal in reversed(dropped)])

    def refresh(self, goals: Iterable[Objective]) -> None:
        """Replace the queue with the producers' goals ("re-plan, never resume"); dropped goals stay out."""
        self.queue = {
            goal.key: goal
            for goal in goals
            if goal.key not in self.dropped and not (goal.kind == NEXT_LEVEL and goal.area in self.wayless)
        }

    def nothing_left(self, area: int | None) -> None:
        """A run of `area`, a level done, ended with nothing left to go to: NOTHING_LEFT_ENDS of them in a game are no
        way on (`no_way_on`). One alone is not: a crossing's first look ends so (Inner Cloister to the Cathedral at
        08:22:37 on 2026-10-20, the game left on the first; Outer Cloister to Barracks had 1, the Throne 28)."""
        if area is None:
            return
        self.ended_empty[area] += 1
        if self.ended_empty[area] >= NOTHING_LEFT_ENDS:
            self.no_way_on(area)

    def no_way_on(self, area: int | None) -> None:
        """A run on `area` ended with no way on after exploring it: its NEXT_LEVEL goals are dropped for the game.
        Made again, the leg ended the same way every 8 s until the 45 s watchdog left the game (Lost City to Valley of
        Snakes, 01:13:16-01:13:54 on 2026-10-20)."""
        if area is not None and area not in self.wayless:
            self.wayless.add(area)
            for key in [key for key, goal in self.queue.items() if goal.kind == NEXT_LEVEL and goal.area == area]:
                del self.queue[key]
            LOG.info('Macro: agenda: no way on from level %d: its next level is dropped for the game', area)

    def next(
        self,
        here: Point | None,
        *,
        in_game: bool = True,
        valuable: str | None = None,
        area: int | None = None,
        dead: frozenset[str] = frozenset(),
    ) -> Objective:
        """The goal to work now: the stack's top (a RESUME ends its package), else the queue's best, else a PICKUP
        of `valuable` still on the ground, else the game's end from `area` (`game_end`: LEAVE_GAME, or the way to the
        town it ends in; `dead` the bosses killed, for a level's own way out, the Town Portal once that is dropped).
        Out of a game, NEW_GAME."""
        if not in_game:
            return Objective(NEW_GAME, 'the next game', STACK)
        top = self.package()
        if top is not None:
            return top
        if self.queue:
            return self.told(min(self.queue.values(), key=lambda goal: (goal.tier, cost(goal, here))))
        if valuable is not None:
            return self.told(Objective(PICKUP, f'{valuable}, before leaving', SIGHTED))
        end = game_end(area, dead)
        return self.told(end if end.key not in self.dropped else game_end(area))

    def package(self) -> Objective | None:
        """The stack's top goal, a RESUME ending its package; None with no package (the shared room trip:
        macros/tzloop.py `packaged`, `errand`)."""
        while self.stack and self.stack[-1].kind == RESUME:
            done = self.stack.pop()
            LOG.info('Macro: agenda: package done: %s', done.label)
        return self.told(self.stack[-1]) if self.stack else None

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
                # One goal a chest: the client names a chest anew when its room is loaded again, and the name before
                # is never seen spent (Sewers Level 1, 01:54:14 on 2026-10-20, rca/2026-10-20/super-chest-settle-*.md)
                at = (view.area, place)
                for old in [u for u, goal in self.chests.items() if u != unit and (goal.area, goal.place) == at]:
                    del self.chests[old]
                self.chests[unit] = Objective(OPEN, 'Super chest', CHEST, view.area, place, unit)

    def in_level(self, view: LevelView) -> Objective | None:
        """The level run's next target (goals-plan.md §3), first match: a live Herald; a Herald's omen; the side
        drop's guards, then the drop; a leader in sight (on TZ+ a reasonable group too, `groups_near`); a super chest
        within CHEST_NEAR; a leader remembered within REMEMBERED_NEAR; on COVER/PLUS/FULL_CLEAR the next room, then
        leaders further, unless the route's next object (`use_at`) is within USE_NEAR and no farther; on TRANSIT nothing
        after the drop. None: the area's end goal is next (on TZ+ its goals met: rooms explored, no group near)."""
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
        if view.policy == TRANSIT:
            return None  # the drops above, then the way on
        reach = WAY_UNITS if view.policy in WAYS_ON else math.inf
        seen = [goal for goal in known if goal.unit in live and away(where(goal)) <= reach]
        if view.policy in GROUPS_TAKEN:
            seen += self.groups_near(view)
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
        if view.policy in WAYS_ON:
            return None
        use = view.use_at if USE_FIRST else None
        near_use = use is not None and away(use) <= USE_NEAR
        room = view.frontier() if view.frontier is not None else None
        if room is not None and not view.passed(room[0], None):
            if near_use and use is not None and away(use) <= away(room[0]):
                return None  # the route's object beside the character before a farther room (USE_FIRST)
            return Objective(EXPLORE, room[1], ROOM, view.area, room[0])
        if near_use:
            return None
        if remembered:
            found = min(remembered, key=lambda goal: away(where(goal)))
            return Objective(KILL, found.label, LEADER_FAR, found.area, found.place, found.unit)
        return None

    def worked_as(self, area: int, policy: str, population: float | None) -> None:
        """Say how level `area` is worked when that changes (once a level a game, unless it changes): its policy, on
        TZ+ its population and the groups it takes (`LevelView.group_size`)."""
        if self.policies.get(area) == policy:
            return
        self.policies[area] = policy
        extra = ''
        if policy in GROUPS_TAKEN:
            size = LevelView(area, (0.0, 0.0), population=population).group_size
            known = f'{population:.0f} hostiles' if population is not None else 'its size unknown'
            extra = f' ({known}: groups of {size} and more)'
        LOG.info('Macro: agenda: %s is worked %s%s', display_name(area), policy, extra)

    def groups_near(self, view: LevelView) -> list[Objective]:
        """TZ+'s KILL goals for the reasonable groups of `view.crowd` (`groups`, `LevelView.group_size`): each group's
        nearest member, when within GROUP_NEAR and not passed (a group behind a wall is left whole, not member by
        member). A level under BIG_LEVEL takes groups of GROUP_MIN, a big one only of BIG_GROUP; a lone monster, a
        pair, a group further are left."""
        found = []
        for group in groups(view.crowd, view.group_size):
            unit, place = min(group, key=lambda member: math.dist(view.here, member[1]))
            if math.dist(view.here, place) <= GROUP_NEAR and not view.passed(place, unit):
                found.append(kill(view.area, unit, place, f'a group of {len(group)}'))
        return found

    def known(self, area: int) -> int:
        """The open KILL goals of `area`."""
        return sum(1 for goal in self.kills.values() if goal.area == area)


def cost(goal: Objective, here: Point | None) -> float:
    """Units from `here` to the goal's place; 0 without either."""
    if goal.place is None or here is None:
        return 0.0
    return math.dist(here, goal.place)
