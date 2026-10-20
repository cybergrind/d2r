"""Experience Shrines on a level run's way (the player, 2026-10-20 ~18:43: "i'd like you to take exp shrines along the
way"): a side goal beside the containers', on the shared path every level run takes (hunting/judging.py `judge`: the
KP_1 run and the KP_6 loop's kinds alike).

Found: the object units every SHRINE_LOOK (GameMemory.objects, loot/ground.py `shrines_in`); only Experience Shrines
(loot/shrines.py EXPERIENCE_SHRINE) unused (mode 0). Chosen: on the way as a valuable is (choice.py `on_the_way`: within
SHRINE_WALK walked, or on the loop within SHRINE_TELEPORT seconds of Teleport), in the quiet (no hostile within
SHRINE_GUARD of the shrine or the character, life at SHRINE_LIFE or more, not just hurt), the character alive, and only
while the run's own goal is no fight, pickup or stand-by (a valuable and a fight come first). Clicked from within
SHRINE_NEAR on a clear line, only with the game's hover record naming it; used when its mode leaves 0. Left after
SHRINE_TRIES clicks, SHRINE_SECONDS of looks gone for it, or no way to it.

Why only Experience Shrines: shrines.json gives every Booster a duration and the shrine states (states.json 128-137) no
group; one shrine effect at a time is the classic game's rule (a new shrine's effect replaces the one on), not in the
data and not yet seen on this build, so any other shrine could end an Experience Shrine's 144 s. A second Experience
Shrine while one is on gives the same state anew (no stacking: the bonus is Arg0 50 % either way), so it is worth what
it renews: taken unless the one on was used here less than REFRESH_AFTER ago (the loop never comes back for it).
"""

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import OBJECT_UNIT
from inventory_tracking.game.records import World
from inventory_tracking.game.view import UNIT_PIXELS
from inventory_tracking.levels.model import Ground
from inventory_tracking.loot.ground import Shrine, shrines_in
from inventory_tracking.loot.shrines import EXPERIENCE_SECONDS, EXPERIENCE_SHRINE
from inventory_tracking.macros.act import until
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import PICK_NEAR, PICK_UP, WAIT, Goal
from inventory_tracking.macros.hunting.base import FAR_JUDGED, HURT_SECONDS, LOOP_PICK_SECONDS, OPEN_NEAR, hostiles
from inventory_tracking.macros.movement import HOPS
from inventory_tracking.macros.routines import DEAD, settle
from inventory_tracking.macros.teleport import (
    HOVER_SECONDS,
    STILL_SECONDS,
    THING_SECONDS,
    ground_fraction,
    in_view,
)
from inventory_tracking.macros.travel import PRESSED, Point, open_reaches, walked_length
from inventory_tracking.routes.model import FIGHT, USE


if TYPE_CHECKING:
    from inventory_tracking.macros.hunt import Hunter
    from inventory_tracking.macros.pursuit import Pursuit


# The switch: False and no shrine is looked for (the player, 2026-10-20: "take exp shrines along the way")
EXP_SHRINES = True
SHRINE_LOOK = 1.0  # seconds between two reads of the objects for shrines (a read of every object unit)
SHRINE_SIGHT = 80.0  # units: a shrine further off is not judged (nor said)
SHRINE_WALK = PICK_NEAR  # units walked: on the way as a valuable is (40)
SHRINE_TELEPORT = LOOP_PICK_SECONDS  # seconds of Teleport hops on the loop: as a valuable (2.5)
SHRINE_SECONDS = 10.0  # seconds of the looks that went for it (not a fight's between them): left after this
SHRINE_GAP = 1.0  # seconds: a look this soon after the last that went for it adds its time to SHRINE_SECONDS
SHRINE_TRIES = 3  # uses tried (each a few aims) before it is left
SHRINE_GUARD = 15.0  # units: no hostile this near the shrine or the character
SHRINE_LIFE = 50.0  # % of the character's life at least (or the build's safety floor, if higher)
SHRINE_NEAR = OPEN_NEAR  # units on a clear line: clicked from here (12; the click walks the rest)
REFRESH_AFTER = 30.0  # seconds since this run used one: a second one renews no less than this
SHRINE_POLL = 0.1  # seconds between the reads of its mode after a click
# Classic pixels above its ground point: a shrine is drawn as a statue or an altar standing on it (objects.txt gives
# none a click box), so the aims go up its middle; each is clicked only with the shrine under the pointer by the
# game's own hover record. Not yet seen clicked on this build.
SHRINE_AIMS = ((0, -30), (0, -45), (0, -15), (0, -60), (12, -30), (-12, -30), (0, 0))


@dataclass
class ShrineWatch:
    """A Hunter's shrines of this game: the last read, what was said, tried and used."""

    game: str = ''
    read_at: float = -math.inf
    seen: tuple[Shrine, ...] = ()
    used_at: float | None = None  # the clock when this game's last Experience Shrine was used by the run
    since: dict[int, tuple[float, float]] = field(default_factory=dict)  # unit -> (seconds gone for, the last look)
    tries: dict[int, int] = field(default_factory=dict)
    left: set[int] = field(default_factory=set)  # units left for good
    said: dict[int, str] = field(default_factory=dict)  # unit -> the kind of the last thing said of it
    far: dict[int, tuple[float, bool]] = field(default_factory=dict)  # unit -> (clock, Teleport brings it)

    def begin(self, game: str) -> None:
        if game != self.game:
            self.__init__(game=game)  # a new game: nothing of the last one


def name_of(shrine: Shrine) -> str:
    return f'{shrine.label} at ({shrine.x:.0f}, {shrine.y:.0f})'


def say(watch: ShrineWatch, shrine: Shrine, text: str, kind: str | None = None) -> None:
    """`Macro: shrine: <name> <text>`, said when the kind of what is said of the shrine changes (`kind`, else the
    text: a distance in it changes every look)."""
    kind = text if kind is None else kind
    if watch.said.get(shrine.unit_id) == kind:
        return
    watch.said[shrine.unit_id] = kind
    LOG.info('Macro: shrine: %s %s', name_of(shrine), text)


def leave(watch: ShrineWatch, shrine: Shrine, why: str) -> None:
    watch.left.add(shrine.unit_id)
    say(watch, shrine, f'left: {why}')


def read(run: Run) -> tuple[Shrine, ...]:
    if run.objects is None:
        return ()
    return tuple(shrines_in(run.objects()))


def seen(self: Hunter, run: Run, now: float) -> tuple[Shrine, ...]:
    """The shrines of the last read, read again every SHRINE_LOOK (they stand still; only a use changes them)."""
    watch = self.shrines
    if now - watch.read_at >= SHRINE_LOOK:
        watch.read_at, watch.seen = now, read(run)
    return watch.seen


def on_the_way(
    self: Hunter, run: Run, world: World, ground: Ground | None, here: Point, place: Point, unit: int
) -> bool:
    """Within SHRINE_WALK walked, or (the KP_6 loop) Teleport hops within SHRINE_TELEPORT, judged once in FAR_JUDGED."""
    if math.dist(here, place) <= SHRINE_WALK and walked_length(ground, world.doors, here, place) <= SHRINE_WALK:
        return True
    posted = self.pursuit
    if posted is None or not posted.looped or ground is None:
        return False
    return teleport_reach(self, run, world, ground, place, unit)


def teleport_reach(self: Hunter, run: Run, world: World, ground: Ground, place: Point, unit: int) -> bool:
    watch, now = self.shrines, run.clock()
    judged = watch.far.get(unit)
    if judged is not None and 0.0 <= now - judged[0] < FAR_JUDGED:
        return judged[1]
    player, rect = world.player, run.actuator.keys.focused_window_rect()
    level = self.known_level(player) if player is not None else None
    found = False
    if level is not None and rect is not None:
        aspect, intent = rect[2] / rect[3], self.looped_now(now)
        if self.travel.means(run, world, ground, aspect, place, intent, level.rooms) == HOPS:
            found = self.travel.eta(run, world, ground, aspect, place, intent, level.rooms) <= SHRINE_TELEPORT
    watch.far[unit] = (now, found)
    return found


def quiet(self: Hunter, run: Run, world: World, here: Point, place: Point) -> tuple[str, str] | None:
    """Why the shrine waits now as (kind, text): hostiles near, just hurt, life low; None: in the quiet."""
    near = [
        m for m in hostiles(world) if min(math.dist((m.x, m.y), here), math.dist((m.x, m.y), place)) <= SHRINE_GUARD
    ]
    if near:
        return 'hostiles', f'waits: {len(near)} hostiles within {SHRINE_GUARD:.0f} of it or the character'
    if run.clock() - self.hurt_at <= HURT_SECONDS:
        return 'hurt', f'waits: the character was hurt within {HURT_SECONDS:.0f} s'
    if run.loot is not None:
        loot = run.loot()
        least = max(SHRINE_LIFE, self.build.settings.safety.floor)
        if loot.max_life > 0 and loot.life < loot.max_life * least / 100:
            return 'life', f'waits: life {loot.life}/{loot.max_life}, under {least:.0f} %'
    return None


def side_goal(self: Hunter, run: Run, world: World, goal: Goal | None, posted: Pursuit | None) -> Goal | None:
    """The level run's goal with an Experience Shrine on its way first (the module's rules); `goal` otherwise. Asked
    by `judge` on a run's own look (no advance press)."""
    player = world.player
    if not EXP_SHRINES or player is None or player.in_town or player.mode in DEAD or run.objects is None:
        return goal
    if posted is None or not posted.runs:
        return goal
    if goal is not None and goal.do in (FIGHT, PICK_UP, WAIT):
        return goal  # a fight, a valuable, a potion or the stand-by first
    watch, now, here = self.shrines, run.clock(), (player.x, player.y)
    watch.begin(world.game_name)
    level = self.known_level(player)
    ground = Ground(level.ground) if level is not None else None
    found: list[tuple[float, Shrine]] = []
    for shrine in seen(self, run, now):
        place = (float(shrine.x), float(shrine.y))
        away = math.dist(here, place)
        if shrine.unit_id in watch.left or shrine.mode != 0 or away > SHRINE_SIGHT:
            continue
        if shrine.shrine_type != EXPERIENCE_SHRINE:
            leave(watch, shrine, "not an Experience Shrine (another shrine's effect would end an Experience Shrine's)")
            continue
        if watch.tries.get(shrine.unit_id, 0) >= SHRINE_TRIES:
            leave(watch, shrine, f'not used in {SHRINE_TRIES} tries')
            continue
        since = watch.since.get(shrine.unit_id)
        if since is not None and since[0] > SHRINE_SECONDS:
            leave(watch, shrine, f'not used in {SHRINE_SECONDS:.0f} s gone for')
            continue
        if watch.used_at is not None and now - watch.used_at < REFRESH_AFTER:
            age = now - watch.used_at
            say(watch, shrine, f'waits: the last one was used {age:.0f} s ago (renewing it gains under '
                f'{REFRESH_AFTER:.0f} of {EXPERIENCE_SECONDS:.0f} s)', 'renews little')  # fmt: skip
            continue
        if since is None and not on_the_way(self, run, world, ground, here, place, shrine.unit_id):
            say(watch, shrine, f'not on the way from ({here[0]:.0f}, {here[1]:.0f}): {away:.0f} away', 'off the way')
            continue
        why = quiet(self, run, world, here, place)
        if why is not None:
            say(watch, shrine, why[1], why[0])
            continue
        found.append((away, shrine))
    if not found:
        return goal
    away, shrine = min(found, key=lambda pair: pair[0])
    spent, last = watch.since.get(shrine.unit_id, (0.0, now))
    watch.since[shrine.unit_id] = (spent + (now - last if 0.0 <= now - last <= SHRINE_GAP else 0.0), now)
    say(watch, shrine, f'is {away:.0f} away: going to it', 'going')
    spend = goal.spend if goal is not None else (self.looped_now(now) if posted.rush else PRESSED)
    route = goal.route if goal is not None else ''
    place = (float(shrine.x), float(shrine.y))
    # `guarded`: a side goal of the run's own (pursuit.py `run_level`), never begun with hostiles by it (`quiet`)
    return Goal(f'{shrine.label}, on the way', place, USE, SHRINE_NEAR, spend, unit=shrine.unit_id, route=route,
                guarded=True, shrine=True)  # fmt: skip


def there(ground: Ground, world: World, here: Point, goal: Goal) -> bool:
    """Whether the shrine is clicked from here: within its `near` on a clear line (never across a wall)."""
    return open_reaches(ground, world.doors, here, goal.place, goal.near)


def no_way(self: Hunter, goal: Goal, reason: str) -> None:
    """No way to the shrine: left (it is a side goal: the level's own way is not explored for it)."""
    shrine = next((s for s in self.shrines.seen if s.unit_id == goal.unit), None)
    if shrine is not None:
        leave(self.shrines, shrine, reason)


def fresh(run: Run, unit: int | None) -> Shrine | None:
    return next((s for s in read(run) if s.unit_id == unit), None)


def use(self: Hunter, run: Run, world: World, goal: Goal) -> None:
    """Click the shrine `goal` names and see its mode leave 0. A click that does not take is a try (SHRINE_TRIES); the
    act's own stops (cancel, a flip of the input mode) go on up, any other is said and the next look decides."""
    watch, player = self.shrines, world.player
    if player is None or player.mode in DEAD:
        return  # nothing after a death
    unit = goal.unit
    assert unit is not None
    watch.tries[unit] = watch.tries.get(unit, 0) + 1
    shrine = fresh(run, unit)
    if shrine is None:
        watch.left.add(unit)
        LOG.info('Macro: shrine: %s left: no longer shown', goal.label)
        return
    if shrine.mode != 0:
        leave(watch, shrine, f'used already (mode {shrine.mode})')
        return
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')

    def took() -> bool:
        now = fresh(run, unit)
        return now is not None and now.mode != 0

    try:
        if run.pad is not None:  # controller mode: stand by it, target it, press (macros/pad.py)
            used = run.pad.interact(OBJECT_UNIT, unit, (float(shrine.x), float(shrine.y)), took, name_of(shrine))
        else:
            used = click(run, shrine, rect[2] / rect[3])
    except Abort as stop:
        if run.stops(stop):
            raise
        say(watch, shrine, f'not used (try {watch.tries[unit]} of {SHRINE_TRIES}): {stop}')
        return
    if used:
        watch.used_at = run.clock()
        watch.left.add(unit)
        say(watch, shrine, 'used')
        run.say(f'{shrine.label}: used')
    else:
        say(watch, shrine, f'not used (try {watch.tries[unit]} of {SHRINE_TRIES}): no click took')


def click(run: Run, shrine: Shrine, aspect: float) -> bool:
    """The aims up the shrine's picture (SHRINE_AIMS): one under the pointer by the hover record is clicked, then its
    mode is read until it leaves 0 (THING_SECONDS: the click walks the character to it). Whether it was used."""
    at = (float(shrine.x), float(shrine.y))

    def mode_left(seen: Shrine) -> bool:
        return seen.mode != 0

    def again() -> Shrine | None:
        return fresh(run, shrine.unit_id)

    for aim in SHRINE_AIMS:
        player = run.world().player
        if player is None or player.mode in DEAD:
            return False  # nothing after a death
        across, down = ground_fraction(player, *at, aspect)
        where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
        if not in_view(where):
            continue
        run.actuator.aim(*where, scatter=(4, 3))
        if run.hovered is not None:
            run.pace.sleep(HOVER_SECONDS)
            if run.hovered() != (OBJECT_UNIT, shrine.unit_id):
                continue
        settle(run, 0.0, STILL_SECONDS)
        run.actuator.click()
        if until(run, mode_left, THING_SECONDS, read=again, poll=SHRINE_POLL) is not None:
            return True
        LOG.info('Macro: shrine: %s did not take the click %s pixels from its ground', name_of(shrine), aim)
    return False
