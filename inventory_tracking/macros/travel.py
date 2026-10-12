"""One move of the hunt's own (macros/hunt.py): a step to a place, made by a jump or by one click's walk.

`Step` is the order: where to, and the skill it is jumped by (None: a walk). `Travel` knows which jumps
the character can make now without a weapon swap (`jumps`: Blade Warp over a clear line once its
casting delay is over, Teleport from the staff in hand), makes a step by the way it names (`make`),
and finds a straight stride toward a goal (`stride`). The place itself is chosen in combat/stance.py
(`camp`), priced by these jumps.
"""

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass, replace

from inventory_tracking.combat.stance import Camp, Jump, no_footing, way
from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import press_skill, settle
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.skills import BLADE_WARP, TELEPORT, skill_name
from inventory_tracking.macros.teleport import HOVER_SECONDS, MOVED, ground_fraction, in_view, landed_from, moved
from inventory_tracking.macros.world import NO_OWNER, Monster, World


MONSTER_UNIT_TYPE = 1  # the unit type of a monster, alive or dead, in the record of what is under the pointer
STRIDE = 16.0  # units of one stride: the click has to be in view
# A walk is a click; the character must be seen moving within STEP_WALK_SECONDS.
STEP_WALK_SECONDS = 0.7
HOVER_UNITS = 12.0  # a monster named as under the pointer stands this near the ground aimed at, or is not there
# A stride is a jump when a skill makes one without a weapon swap: Blade Warp first (skills.txt 390, a casting
# delay of 20 frames, spends no charges), else Teleport when in hand or a skill of the character's own (Enigma).
JUMP_REACH = 26.0  # units of a jump: in view, and within the blade's range
JUMP_LEAST = 8.0  # a stride shorter than this is walked
WARP_DELAY = 0.8  # seconds between two Blade Warps (the skill's casting delay)
JUMP_SECONDS = 1.5  # for the character to be seen somewhere else after the key
# What a jump takes from its key to standing there, for the choice of a place (combat/stance.py `Jump`).
WARP_SECONDS, WARP_SPEED = 0.35, 45.0  # Blade Warp: the cast, then the blade's flight in units a second
TELEPORT_SECONDS = 0.31  # Teleport with the staff in hand
# Charges of the Teleport staff the mode's own moves leave alone (user, 2026-10-11: "track number of tp
# charges when using staff, and leverage warp more when low on charges"): under it the sweep
# does not jump by Teleport, and the seek step goes by Blade Warp or a walk where one leads on. The
# player's own teleport step spends them to the last. A staff of 69 came to 2 clearing a level after
# Nihlathak (15:10 that day); some 20 are needed to reach him.
LOW_CHARGES = 10
JUMP_DISTRUST = 30.0  # seconds a way of jumping that did not move the character is left alone
# The walked way round a wall (`Travel.around`), for a staff with no charge left: Dijkstra over the
# walkable unit cells within AROUND_REACH of the character, AROUND_DETOUR times the straight line at most.
AROUND_REACH = 70
AROUND_DETOUR = 4.0
AROUND_LEAST = 3.0  # units a move along that way has to make
NEIGHBOURS = tuple((dx, dy, math.hypot(dx, dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
Point = tuple[float, float]


@dataclass(frozen=True)
class Step:
    """A move of the mode's own: where to, and by what (a skill the character jumps by; None: one
    click's walk). `camp` is the place decision it came from, when one was made."""

    spot: Point
    skill: int | None = None
    camp: Camp | None = None

    @classmethod
    def to(cls, place: Camp) -> Step:
        """The move to a place, by the way the place was chosen for."""
        return cls(place.spot, place.skill, place)


class Travel:
    """What the character can jump by, and the moves made with it."""

    def __init__(self) -> None:
        self.warped_at = -math.inf  # clock time of the last Blade Warp
        self.jump_failed: dict[int, float] = {}  # skill -> clock time a jump by it last moved nothing

    def stride(
        self,
        run: Run,
        world: World,
        ground: Ground,
        aspect: float,
        goal: Point,
        short: float = 0.0,
        shot: bool = False,
        shuns: Callable[[Point], bool] = lambda spot: False,
    ) -> Step | None:
        """A stride straight toward `goal`, to end `short` of it: a jump of up to JUMP_REACH when the
        character can make one (`jump_by`), else a walk of STRIDE; onto footing, in view, and not to a
        place a step failed for. With `shot` a short walk has to end with a clear shot at the goal."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        away = math.dist(here, goal)
        barred = no_footing(ground, world.doors)

        def at(stride: float) -> Point:
            return (here[0] + (goal[0] - here[0]) * stride / away, here[1] + (goal[1] - here[1]) * stride / away)

        def footed(spot: Point) -> bool:
            return in_view(ground_fraction(player, spot[0], spot[1], aspect)) and (
                barred is None
                or not any(barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            )

        if away - short < MOVED or shuns(at(min(away - short, STRIDE))):
            return None
        skill = self.jump_by(run, world)
        if skill is not None and away - short >= JUMP_LEAST:
            longest = min(away - short, JUMP_REACH)
            for stride in (longest, longest * 0.75, longest * 0.5):
                spot = at(stride)
                if stride < JUMP_LEAST or not footed(spot):
                    continue
                if skill == BLADE_WARP and not clear_shot(ground, here, spot, world.doors):
                    continue  # the blade flies there: no wall in its way
                return Step(spot, skill)
        stride = min(away - short, STRIDE)
        spot = at(stride)
        if not in_view(ground_fraction(player, spot[0], spot[1], aspect)) or not way(barred, here, spot):
            return None
        if shot and stride < STRIDE / 2 and not clear_shot(ground, spot, goal, world.doors):
            return None  # a few units up to a wall it stands behind: the firing spot's to find
        return Step(spot)

    def around(self, run: Run, world: World, ground: Ground, aspect: float, goal: Point) -> Step | None:
        """A move along the walked way to `goal` when no straight stride leads there (a wall in the
        line): the shortest way over walkable ground, and on it the furthest spot a Blade Warp flies to
        over a clear line, else the furthest one click's straight walk reaches. None with no such way.
        Drifter Cavern, 09:43 on 2026-10-12 (user: "KP_1 got stuck when I'm out of tp charges, probably
        we should switch to walk/blade warp routes calculation"): the staff empty, the firing spot 26
        units off behind a wall, and thirteen presses each ended with "no Blade Warp or walk leads"."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        barred = no_footing(ground, world.doors)
        if barred is None:
            return None
        path = walked_way(barred, here, goal)
        skill = self.jump_by(run, world)
        if skill == BLADE_WARP:
            for spot in reversed(path):
                away = math.dist(here, spot)
                if not JUMP_LEAST <= away <= JUMP_REACH or not in_view(ground_fraction(player, *spot, aspect)):
                    continue
                if clear_shot(ground, here, spot, world.doors) and not any(
                    barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                ):
                    return Step(spot, skill)
        for spot in reversed(path):
            away = math.dist(here, spot)
            seen = in_view(ground_fraction(player, *spot, aspect))
            if AROUND_LEAST <= away <= STRIDE and seen and way(barred, here, spot):
                return Step(spot)
        return None

    def jumps(self, run: Run, world: World) -> tuple[Jump, ...]:
        """The skills a step can be jumped by now without a weapon swap, the preferred first: Blade
        Warp when it is in a slot and its casting delay is over, Teleport from the staff in hand with
        LOW_CHARGES or more, or as the character's own skill. One that moved nothing is left out for JUMP_DISTRUST."""

        def trusted(skill: int) -> bool:
            return run.clock() - self.jump_failed.get(skill, -math.inf) > JUMP_DISTRUST

        found = []
        if BLADE_WARP in world.slots and trusted(BLADE_WARP) and run.clock() - self.warped_at >= WARP_DELAY:
            found.append(Jump(BLADE_WARP, WARP_SECONDS, WARP_SPEED, JUMP_REACH, JUMP_LEAST, line=True))
        if TELEPORT in world.slots and trusted(TELEPORT):
            staff = run.teleport() if run.teleport is not None else None
            if staff is None or (staff.in_hand and staff.charges >= LOW_CHARGES):
                found.append(Jump(TELEPORT, TELEPORT_SECONDS, math.inf, JUMP_REACH, JUMP_LEAST, line=False))
        return tuple(found)

    def jump_by(self, run: Run, world: World, *, warp: bool = True) -> int | None:
        """The skill a stride can be jumped by now (`jumps`), without Blade Warp when `warp` is off.
        None: the stride is walked."""
        return next((jump.skill for jump in self.jumps(run, world) if warp or jump.skill != BLADE_WARP), None)

    def jump(self, run: Run, found: Step, player, aspect: float, key_names) -> None:
        """One jump onto `found.spot` by the skill it names: the pointer on its ground, the key, and
        the character seen somewhere else. What it was aimed at and where it landed goes to the log."""
        skill = found.skill
        assert skill is not None
        try:
            run.keys.update(key_names(run.world(), (skill,)))
            # No wait of its own for the cast in flight: `press_skill` waits for the character (with one,
            # 0.39 s went by between the decision and the key at the median, 2026-10-11).
            run.actuator.aim(*ground_fraction(player, found.spot[0], found.spot[1], aspect), scatter=(4, 3))
            pressed = run.clock()
            press_skill(run, skill)
            if skill == BLADE_WARP:
                self.warped_at = run.clock()
            spot = found.spot
            if run.seen(lambda w: w.player is not None and landed_from(w.player, player, spot), JUMP_SECONDS) is None:
                raise Abort(f'{skill_name(skill)}: the character did not move')
        except Abort:
            self.jump_failed[skill] = run.clock()
            raise
        landed = run.world().player
        if landed is not None:
            LOG.info(
                'Macro: %s aimed at (%.1f, %.1f), %.1f from (%.1f, %.1f); landed at (%.1f, %.1f), off by %.1f, '
                '%.2fs after the key',
                skill_name(skill), *found.spot, math.dist((player.x, player.y), found.spot), player.x, player.y,
                landed.x, landed.y,
                math.dist((landed.x, landed.y), found.spot), run.clock() - pressed,
            )  # fmt: skip

    def make(
        self, run: Run, found: Step, world: World, aspect: float, key_names, ground: Ground | None, name: str = ''
    ) -> None:
        """Make one move of the mode's own, by the way it names: a jump by its skill, or one click's
        walk. A jump that cannot be made any more (the skill gone from `jumps` since the choice, a
        wall in a blade's line) is made by the next skill that can, else walked."""
        player = world.player
        assert player is not None
        here = (player.x, player.y)
        skill = found.skill
        if skill is not None and key_names is not None:
            able = [jump.skill for jump in self.jumps(run, world)]
            if ground is not None and not clear_shot(ground, here, found.spot, world.doors):
                able = [other for other in able if other != BLADE_WARP]
            skill = skill if skill in able else next(iter(able), None)
        if skill is not None and key_names is not None:
            self.jump(run, replace(found, skill=skill), player, aspect, key_names)
        else:
            step_walk(run, found.spot, player, aspect, attackable(world), name=name or 'a better place')


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
    run: Run, goal, player, aspect: float, alive: list[Monster], *, name: str = 'a better place', clicks: int = 1
) -> None:
    """A click on the ground at `goal` and the character seen going within STEP_WALK_SECONDS, `clicks`
    times at most (a click made while a cast ends is swallowed). Not clicked with one of `alive` (the
    monsters a click attacks) under the pointer: the left button attacks it, where it stands or after
    a chase. The unit the game names as under the pointer counts only within HOVER_UNITS of the goal
    (the name of the last unit hovered seems to stay)."""
    where = ground_fraction(player, goal[0], goal[1], aspect)
    if not in_view(where):
        raise Abort(f'the place near {name} is not in view')
    run.say(f'Walking {math.dist((player.x, player.y), goal):.0f} toward {name}')
    for _ in range(clicks):
        settle(run, limit=0.5)
        run.actuator.aim(*where, scatter=(4, 3))
        if run.hovered is not None:
            run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            if over is not None and over[0] == MONSTER_UNIT_TYPE:
                under = [m for m in alive if m.unit_id == over[1] and math.dist((m.x, m.y), goal) <= HOVER_UNITS]
                if under:
                    raise Abort(f'{label(under[0])} is under the pointer there')
        run.actuator.click()
        if run.seen(lambda w: w.player is not None and moved(w.player, player), STEP_WALK_SECONDS) is not None:
            return
    raise Abort('the character did not move')
