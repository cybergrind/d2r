"""Goals: what the character is after, never how it gets there (rca/2026-10-13/kp4-findings.md §6; the player,
2026-10-13: "We MUST have architecturally separated goals from navigational system").

A `Goal` is a place in world units (and the unit there), what is done at it, how near is near enough, what the way
may spend, and a label. The movement sets behind travel.py `navigator` get its place; this module knows no wall and
no way to move.

`goal_of` (pure) is the goal a teleport-key press means now: a valuable beside the character first, then a level
run's side drop, then the route's stage (`route_goal`, which the level card follows too). A fight's place is its boss
where it stands, else where one was last seen alive, else the stage's mark, else somewhere left to look.
`first_fight` puts hostiles that bar a goal first. The "near enough" numbers mirror the hands' (a test holds them
equal).
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from inventory_tracking.game.records import HEALING, REJUVENATION, Drop, Monster
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.build import Intent
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT, STAND, USE, Stage
from inventory_tracking.terror.bosses import BOSSES, SUPER_UNIQUE_FLAG


REACH, PICK_UP = 'reach', 'pick up'  # with the routes' USE, STAND, FIGHT, ENTER, LOOT and LEAVE: what is done at a goal
# A level run stands by a valuable with no room ("when valuable doesn't fit: we need to stop near it", the player,
# 2026-10-13)
WAIT = 'wait by'
# What the pursuit loop performs itself (macros/pursuit.py); other kinds are the route's own press
PURSUED = frozenset((REACH, USE, STAND, FIGHT, PICK_UP, WAIT))
USE_NEAR = 25.0  # units: an object this near is clicked from where the character stands (teleport.py THING_REACH)
STAND_NEAR = 12.0  # units from a mark: the character has stood at it (route.py STAND_NEAR)
PLACE_NEAR = 5.0  # units, one tile: a place is arrived at (teleport.py SPOT_NEAR)
# Units from an open passage's far place within which one click walks across, under a stride
# (rca/2026-10-14/kp1-mode.md §8)
PASSAGE_NEAR = 12.0
# Units from a door's remembered click spot: the run ends on it, not `short` of it, so the click needs no walk
# (rca/2026-10-18/stairs-walks-findings.md §5 B)
ENTRY_GOAL_NEAR = 2.0
PICK_NEAR = 40.0  # units: a valuable this near is taken before the character leaves (pickup.py STOP_UNITS)
# Units: a drop this near is clicked from where the character stands (pickup.py PICK_UNITS); further off the
# navigator goes first (rca/2026-10-13/run-2110-findings.md §2.3)
PICK_REACH = 20.0
# Units: a potion with a hostile this near it or the character is not stopped for (hunt.py GATHER_CLEAR); on a level
# run those hostiles are fought first (`in_the_way`)
GUARD_NEAR = 12.0
# Units from a fight's mark within which a boss is the mark's (hunt.py BOSS_MARK_UNITS; the Countess stood 2-29 units
# off over 56 visits)
BOSS_MARK_UNITS = 60.0
SAME_PLACE = 1.0  # units: two of the tracker's last-seen places this near are one monster's
# Units: on a level run hostiles this near, in line of sight, are fought before going on ("go to the level's goal
# clearing everything along the way", the player, 2026-10-14)
CLEAR_WAY = 30.0


@dataclass(frozen=True)
class Goal:
    """What the character is after. `place` in world units; `unit` the monster or object there; `do` what happens
    at it; `near` how near counts as reached (a fight: the build's strike distance); `spend` what the way may cost;
    `known` False: only where to look. `mark` the card mark it was made from; `route`, `stage` the stage it performs.
    `guarded`: a pickup never begun with a hostile within GUARD_NEAR. `clearing`: a level run's fight on its way or
    of the rest of the level."""

    label: str
    place: Point
    do: str
    near: float
    spend: Intent
    unit: int | None = None
    known: bool = True
    mark: Target | None = None
    route: str = ''
    stage: Stage | None = None
    guarded: bool = False
    clearing: bool = False

    def gap(self, here: Point) -> float:
        """Units from `here` to the goal's place."""
        return math.dist(here, self.place)

    @property
    def crossed(self) -> bool:
        """A way out that is an open passage (no warp): its place is inside the next level and the level change is the
        arrival. A door, stairs or portal is operated instead: its place is the mark."""
        return self.do == ENTER and self.mark is not None and self.mark.passage is not None


def is_boss(monster: Monster) -> bool:
    """A boss or a super unique, as terror/tracker.py `killed` counts them."""
    return monster.txt_id in BOSSES or bool(monster.flags & SUPER_UNIQUE_FLAG)


def spot_of(mark: Target) -> Point:
    """A mark's place in world units (the card holds tiles)."""
    return (mark.point[0] * TILE_UNITS, mark.point[1] * TILE_UNITS)


def remembered_boss(
    here: Point, remembered: Sequence[tuple[int, float, float, bool]], supers: Sequence[Point], gone: frozenset[int]
) -> Point | None:
    """The nearest place a boss or super unique was last seen alive and is not in sight now: a leader remembered
    alive at a place `supers` holds (dead ones too; one tracker, so one place per monster). `gone`: units to skip."""
    found = [
        (x, y)
        for unit, x, y, leader in remembered
        if leader and unit not in gone and any(math.dist((x, y), place) <= SAME_PLACE for place in supers)
    ]
    return min(found, key=lambda place: math.dist(here, place)) if found else None


def fight_goal(
    stage: Stage,
    route: str,
    mark: Target | None,
    here: Point,
    foes: Sequence[Monster],
    remembered: Sequence[tuple[int, float, float, bool]],
    supers: Sequence[Point],
    gone: frozenset[int],
    elsewhere: Callable[[], tuple[Point, str] | None] | None,
    reach: float,
    spend: Intent,
) -> Goal | None:
    """The goal of a `fight` stage: the boss, by the first of its places that is known."""
    name = stage.boss
    at = spot_of(mark) if mark is not None else None
    bosses = [m for m in foes if is_boss(m)]
    if at is not None:  # the stage has a place: the boss is the one that place is for
        bosses = [m for m in bosses if math.dist(at, (m.x, m.y)) <= BOSS_MARK_UNITS]
    made = {'do': FIGHT, 'near': reach, 'spend': spend, 'mark': mark, 'route': route, 'stage': stage}
    if bosses:
        origin = at if at is not None else here
        boss = min(bosses, key=lambda m: math.dist(origin, (m.x, m.y)))
        return Goal(f'{name}', (boss.x, boss.y), unit=boss.unit_id, **made)
    seen = remembered_boss(here, remembered, supers, gone | {m.unit_id for m in foes})
    if seen is not None:
        return Goal(f'{name}, where a boss was last seen', seen, **made)
    if at is not None:
        return Goal(f'{name}, by its mark {stage.mark}', at, **made)
    looked = elsewhere() if elsewhere is not None else None
    if looked is not None:
        place, what = looked
        return Goal(f'seek {name}: toward {what}', place, known=False, **made)
    return None


def first_fight(goal: Goal, here: Point, blockers: Sequence[Monster], reach: float) -> Goal:
    """The goal while hostiles bar `goal` (a monster on a seal, ground covered: teleport.py `Covered`): the fight
    with the nearest, never a silent wait (architecture §2.6). The stage and mark stay the goal's."""
    nearest = min(blockers, key=lambda m: math.dist(here, (m.x, m.y)))
    return Goal(
        f'{goal.label}: the fight first ({len(blockers)} in the way)',
        (nearest.x, nearest.y),
        FIGHT,
        reach,
        goal.spend,
        unit=nearest.unit_id,
        mark=goal.mark,
        route=goal.route,
        stage=goal.stage,
        guarded=goal.guarded,
    )


def clear_way(goal: Goal, here: Point, near: Sequence[Monster], reach: float) -> Goal:
    """A level run's goal while hostiles are on its way (`near`, the caller's measure): the nearest fought first,
    then on to `goal`."""
    found = first_fight(goal, here, near, reach)
    return replace(found, label=f'{goal.label}: clearing the way ({len(near)} near)', clearing=True)


def rest_of_level(found: tuple[Point, str, int | None], base: Goal | None, reach: float, spend: Intent) -> Goal:
    """A full clear's goal: `found` (place, what, unit) is what is left of the level. A hostile (`unit`) is fought;
    an unexplored room (no unit) is gone to. `base`'s route is kept for the log."""
    place, what, unit = found
    route = base.route if base is not None else ''
    if unit is not None:
        return Goal(f'full clear: {what}', place, FIGHT, reach, spend, unit=unit, route=route, clearing=True)
    return Goal(f'full clear: {what}', place, REACH, PLACE_NEAR, spend, known=False, route=route, clearing=True)


def boss_ahead(stages: Sequence[Stage], stage: Stage) -> bool:
    """Whether `stage` brings a boss's fight: it is the fight, or the use right before it (the last seal of an
    arm)."""
    if stage.kind == FIGHT:
        return True
    if stage.kind != USE or stage not in stages:
        return False
    index = list(stages).index(stage)
    return index + 1 < len(stages) and stages[index + 1].kind == FIGHT


def nearer(goal: Goal) -> Goal:
    """`goal` after its click did not take: made again from within PLACE_NEAR (rca/2026-10-13/run-1233-findings.md
    §2)."""
    return replace(goal, near=min(goal.near, PLACE_NEAR)) if goal.do == USE else goal


def in_the_way(goal: Goal, foes: Sequence[Monster], here: Point | None = None) -> list[Monster]:
    """The hostiles a level run fights before `goal`'s act: within `goal.near` of an object to use (no object
    opened under threat), or for a guarded pickup within GUARD_NEAR of the drop or `here`. Empty for other kinds."""
    if goal.do == PICK_UP and goal.guarded:
        spots = (goal.place,) if here is None else (goal.place, here)
        return [m for m in foes if min(math.dist((m.x, m.y), spot) for spot in spots) <= GUARD_NEAR]
    if goal.do != USE:
        return []
    return [m for m in foes if math.dist((m.x, m.y), goal.place) <= goal.near]


def goal_of(
    here: Point,
    *,
    spend: Intent,
    reach: float,
    stage: Stage | None = None,
    route: str = '',
    card: Target | None = None,
    foes: Sequence[Monster] = (),
    remembered: Sequence[tuple[int, float, float, bool]] = (),
    supers: Sequence[Point] = (),
    gone: frozenset[int] = frozenset(),
    elsewhere: Callable[[], tuple[Point, str] | None] | None = None,
    drop: Drop | None = None,
    side: Drop | None = None,
    stay: Drop | None = None,
    entry: Point | None = None,
) -> Goal | None:
    """The goal a press of the teleport key means now. `stage`: the level's current stage; `card`: the level
    card's first mark; `foes`: hostiles in the world; `remembered`, `supers`, `gone`: the tracker's memory and units
    to skip; `elsewhere()`: (place, what) to look in when nothing is known of a boss, asked only then; `drop`: a
    valuable beside the character, taken first; `side`: a drop a level run takes on its way (guarded when a potion);
    `stay`: a valuable with no room, stood by; `reach`: the build's strike distance; `entry`: the card door's
    remembered click spot. None: nothing to go to."""
    if drop is not None:
        return Goal(f'{drop.label}, before leaving', (drop.x, drop.y), PICK_UP, PICK_NEAR, spend, unit=drop.unit_id)
    if side is not None:
        potion = side.kind in (HEALING, REJUVENATION)
        return Goal(
            f'{side.label}, on the way', (side.x, side.y), PICK_UP, PICK_REACH, spend, unit=side.unit_id, guarded=potion
        )
    if stay is not None:
        return Goal(stay.label, (stay.x, stay.y), WAIT, STAND_NEAR, spend, unit=stay.unit_id)
    return route_goal(
        here,
        spend=spend,
        reach=reach,
        stage=stage,
        route=route,
        card=card,
        foes=foes,
        remembered=remembered,
        supers=supers,
        gone=gone,
        elsewhere=elsewhere,
        entry=entry,
    )


def way_out(
    card: Target, label: str, spend: Intent, route: str, stage: Stage | None, entry: Point | None = None
) -> Goal:
    """The goal of a way to another level at the card's mark. A door, stairs, a cave: the mark within PLACE_NEAR, or
    `entry` (the door's click spot) within ENTRY_GOAL_NEAR. An open passage: a tile inside the next level, within
    PASSAGE_NEAR ("move our target slightly further so the map changes", the player, 2026-10-15)."""
    if card.passage is not None:
        place = (card.passage[0] * TILE_UNITS, card.passage[1] * TILE_UNITS)
        return Goal(label, place, ENTER, PASSAGE_NEAR, spend, mark=card, route=route, stage=stage)
    if entry is not None:  # the last hop lands on it, not short of it
        on = replace(spend, short=0.0)
        return Goal(label, entry, ENTER, ENTRY_GOAL_NEAR, on, mark=card, route=route, stage=stage)
    return Goal(label, spot_of(card), ENTER, PLACE_NEAR, spend, mark=card, route=route, stage=stage)


def route_goal(
    here: Point,
    *,
    spend: Intent,
    reach: float,
    stage: Stage | None = None,
    route: str = '',
    card: Target | None = None,
    foes: Sequence[Monster] = (),
    remembered: Sequence[tuple[int, float, float, bool]] = (),
    supers: Sequence[Point] = (),
    gone: frozenset[int] = frozenset(),
    elsewhere: Callable[[], tuple[Point, str] | None] | None = None,
    entry: Point | None = None,
) -> Goal | None:
    """The route's own goal, nothing on the side: `goal_of` with no drop and no valuable to stand by; the level
    card's first row points at it too (macros/card_goal.py). Arguments as `goal_of`'s. None: nothing to go to."""
    mark = card if card is not None and stage is not None and card.label == stage.mark else None
    if stage is not None and stage.kind in (LOOT, LEAVE):
        return Goal(stage.text(), here, stage.kind, math.inf, spend, route=route, stage=stage)
    if stage is not None and stage.kind == FIGHT:
        found = fight_goal(stage, route, mark, here, foes, remembered, supers, gone, elsewhere, reach, spend)
        if found is not None or not stage.mark:
            return found
    if card is None:
        return None
    place = spot_of(card)
    if mark is None:
        # No stage, or its mark not on the card yet: the card's first mark, as with no route
        label = card.label if stage is None or not stage.mark else f'{card.label} ({stage.mark} is not marked yet)'
        do = ENTER if card.warp or card.kind == 'previous' else USE if card.use else REACH
        if do == ENTER:
            return way_out(card, label, spend, route, None, entry)
        near = USE_NEAR if do == USE else PLACE_NEAR
        return Goal(label, place, do, near, spend, mark=card, route=route)
    assert stage is not None
    if stage.kind == ENTER or card.warp:
        return way_out(card, card.label, spend, route, stage, entry)
    if stage.kind == USE:
        return Goal(card.label, place, USE, USE_NEAR, spend, mark=card, route=route, stage=stage)
    if stage.kind == STAND:
        return Goal(card.label, place, STAND, STAND_NEAR, spend, mark=card, route=route, stage=stage)
    return Goal(card.label, place, REACH, PLACE_NEAR, spend, mark=card, route=route, stage=stage)
