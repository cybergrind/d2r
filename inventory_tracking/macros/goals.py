"""Goals: what the character is after, and nothing about how it gets there (rca/2026-10-13/kp4-findings.md §6).

The player's ruling of 2026-10-13: "We MUST have architecturally separated goals from navigational
system. Goal gives the current goal and navigational system decides what we actually do and how to reach
the goal." A `Goal` is the first half: a place in world units (and the unit there, when it is one), what
is done at it (`reach` it, `use` an object, `stand`, `fight`, `pick up`; `enter`, `loot` and `leave` name
the stages the route's own press still performs), how near is near enough, what may be spent on the way
(an `Intent`, handed in by whoever pursues it) and a label for the log. The second half is the movement
sets behind `macros/travel.py` `navigator`, which are given the goal's place and never a move worked out
here: this module knows of no wall and of no way to move.

`goal_of` is the goal a press of the teleport key means now, and the one attack mode stands by between
presses: pure, from the route's stage, the level card's mark, the hostiles in the world and what the
tracker remembers. Every stage has a place. A fight's is its boss: where it stands now, else where a boss
was last seen alive, else the stage's own mark, else whatever of the level is left to look for it in
(the label says which). A valuable beside the character comes before all of it, as a goal of its own
(`drop`: macros/pickup.py `worth_a_stop`); on a level run (the pickup key, macros/pursuit.py) so does a
drop the pickup rules take on the way (`side`). `first_fight` is the goal while hostiles bar what is to
be done at another: the fight with them first. `route_goal` is the route's part alone (no drop, no valuable
stood by): the level card's first row and arrow follow it too (macros/card_goal.py).

The numbers for "near enough" are the hands' own (the reach of a click on an object, the radius a stand
counts within); they are named here, in the goal's words, and a test holds them equal to the hands'.
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
# A level run stays by a valuable the inventory has no room for (the player, 2026-10-13: "when valuable doesn't
# fit: we need to stop near it"): what is done there is to wait for room.
WAIT = 'wait by'
# What the pursuit loop performs itself (macros/pursuit.py); a goal of another kind is the route's own press
PURSUED = frozenset((REACH, USE, STAND, FIGHT, PICK_UP, WAIT))
USE_NEAR = 25.0  # units: an object this near is clicked from where the character stands (teleport.py THING_REACH)
STAND_NEAR = 12.0  # units from a mark: the character has stood at it (route.py STAND_NEAR)
PLACE_NEAR = 5.0  # units, one tile: a place is arrived at (teleport.py SPOT_NEAR)
# Units from an open passage's far place (levels/exits.py `through`, a tile inside the next level) within which the
# level run walks across with one click, in view and under a stride (travel.py STRIDE 16): the way there is the
# navigator's over this level's ground, which ends at the level's edge (rca/2026-10-14/kp1-mode.md §8).
PASSAGE_NEAR = 12.0
# Units from where the character stands to click a door (macros/teleport.py `entry_stand`, its remembered entry on
# footing): a level run to the door ends on it, from where its click goes in with no walk; one ended at the mark's far
# side walked round the Catacombs stairs' block of walls, or hopped onto the entry first
# (rca/2026-10-18/stairs-walks-findings.md §5 B). The way there ends on the spot itself, not its intent's `short` of it:
# the loop's LOOP_SHORT 3 (travel.py, for a chest's own spot) took the last hop back toward the character, and the runs
# ended 2.2-3.0 units off the entry, east of the block, walking 1.3-7.6 units round it (13:00-13:10 on 2026-10-18)
ENTRY_GOAL_NEAR = 2.0
PICK_NEAR = 40.0  # units: a valuable this near is taken before the character leaves (pickup.py STOP_UNITS)
# Units: a drop this near is clicked from where the character stands (pickup.py PICK_UNITS); a level run's
# drop further off is gone to by the navigator with the movement in hand first (walk, Blade Warp or Teleport),
# not by the pickup's own Teleport hops (rca/2026-10-13/run-2110-findings.md §2.3, the Amn Rune).
PICK_REACH = 20.0
# Units: a potion with a hostile this near it or the character is not stopped for (hunt.py GATHER_CLEAR: Tower
# Cellar 5, 2026-10-11); on a level run those hostiles are its guards and the fight first (`in_the_way`).
GUARD_NEAR = 12.0
# Units from a fight's mark within which a boss is the one the mark is for (hunt.py BOSS_MARK_UNITS: the
# Countess stood 2 to 29 units from the place her map gives her over 56 visits)
BOSS_MARK_UNITS = 60.0
SAME_PLACE = 1.0  # units: two of the tracker's last-seen places this near are one monster's
# Units: on a level run the hostiles this near the character, with a clear line to them, are fought before the
# run goes on to its goal (`clear_way`; the player, 2026-10-14: "go to the level's goal clearing everything along
# the way"). Hunt.py SIGHT: hostiles further off are no part of a fight's decision either.
CLEAR_WAY = 30.0


@dataclass(frozen=True)
class Goal:
    """What the character is after. `place` is where, in world units; `unit` the monster or object there
    when the goal is one (a boss in sight); `do` what happens at it; `near` how near the place counts as
    reached (for a fight: the distance the build strikes from, with a shot at it); `spend` what the way
    there may cost; `known`: the place is where the thing is or was seen (False: only where to look for
    it). `mark` is the level card's mark the goal was made from, for the hands that operate it; `route`
    and `stage` the stage it performs, for the progress to be told. `guarded`: a pickup never begun with a
    hostile within GUARD_NEAR (a potion: `in_the_way` names them), and the fight first with them (`first_fight`):
    a level run's side goal, of no route stage. `clearing`: a level run's fight on its way or of the rest of the
    level (`clear_way`, `rest_of_level`): its own goal, on a level with a route or not (macros/runmode.py)."""

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
        """A way out that is an open passage (`Target.passage`: no warp joins the levels): its place is the far
        place inside the next level, a walk to it changes the level, and that change is the arrival (macros/pursuit.py
        `through`). A door, stairs or a portal is operated: its place is the mark, and going through is a press."""
        return self.do == ENTER and self.mark is not None and self.mark.passage is not None


def is_boss(monster: Monster) -> bool:
    """A boss or a super unique, as the tracker counts the kills a `fight` stage waits for
    (terror/tracker.py `killed`: the act bosses by their type, the rest by the super unique flag)."""
    return monster.txt_id in BOSSES or bool(monster.flags & SUPER_UNIQUE_FLAG)


def spot_of(mark: Target) -> Point:
    """A mark's place in world units (the card holds tiles)."""
    return (mark.point[0] * TILE_UNITS, mark.point[1] * TILE_UNITS)


def remembered_boss(
    here: Point, remembered: Sequence[tuple[int, float, float, bool]], supers: Sequence[Point], gone: frozenset[int]
) -> Point | None:
    """Where a boss or super unique was last seen alive and is not in sight now: a leader the tracker
    remembers alive (`remembered`) at a place it holds for a super unique or a boss (`supers`, which
    holds the dead ones too: the two lists are of one tracker, so one monster has one place in both);
    the nearest. `gone`: units not to go to again (in sight now, or not where they were seen)."""
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
    """The goal of a `fight` stage: the boss, by the first of its places that is known (the module text)."""
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
    """The goal while hostiles bar what is to be done at `goal` (a seal with a monster standing on it, a
    walk whose ground a monster covers: the hands' own report, macros/teleport.py `Covered`): the fight
    with the nearest of them, from where the attack reaches it (architecture §2.6: what blocks is fought
    first, aimed through; Q3: the least-time act is normally to fight through, never a silent wait). The
    stage and its mark stay the goal's, for the progress and the card."""
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
    """A level run's goal while hostiles are on its way (`near`: those within CLEAR_WAY of the character with a
    clear line to them, the caller's measure): the fight with the nearest of them first, the stage and its mark
    kept (the player's ruling of 2026-10-14: the level's goal, clearing everything along the way). The run goes
    on to `goal` once none is left."""
    found = first_fight(goal, here, near, reach)
    return replace(found, label=f'{goal.label}: clearing the way ({len(near)} near)', clearing=True)


def rest_of_level(found: tuple[Point, str, int | None], base: Goal | None, reach: float, spend: Intent) -> Goal:
    """A full clear's goal (macros/runmode.py): what is left of the level, `found` as (place, what, unit). A
    hostile in sight or remembered alive (`unit`) is fought from where the attack reaches it; an unexplored room
    (no unit) is gone to. The route of `base`, the goal the route has after the clear, is kept for the log."""
    place, what, unit = found
    route = base.route if base is not None else ''
    if unit is not None:
        return Goal(f'full clear: {what}', place, FIGHT, reach, spend, unit=unit, route=route, clearing=True)
    return Goal(f'full clear: {what}', place, REACH, PLACE_NEAR, spend, known=False, route=route, clearing=True)


def boss_ahead(stages: Sequence[Stage], stage: Stage) -> bool:
    """Whether the route's stage `stage` (one of `stages`, its level's script) brings a boss's fight: it is that
    fight, or the use of the object that calls the boss (the last seal of an arm: the next stage is the fight)."""
    if stage.kind == FIGHT:
        return True
    if stage.kind != USE or stage not in stages:
        return False
    index = list(stages).index(stage)
    return index + 1 < len(stages) and stages[index + 1].kind == FIGHT


def nearer(goal: Goal) -> Goal:
    """`goal` after its act did not take from where the character stood (an object not under the pointer at
    any aim from 21 to 25 units: rca/2026-10-13/run-1233-findings.md §2; architecture §2.2, "then nearer when
    the click does not take"): the act is made from within PLACE_NEAR of its place."""
    return replace(goal, near=min(goal.near, PLACE_NEAR)) if goal.do == USE else goal


def in_the_way(goal: Goal, foes: Sequence[Monster], here: Point | None = None) -> list[Monster]:
    """The hostiles where `goal`'s act is to be made, which a level run fights before it (`first_fight`):
    those within `goal.near` of an object to use, the stand its click is made from (the player's ruling: an
    object is opened with no immediate threat by it; architecture §5 example 2, "the fight first (9 by the
    seal)"); for a guarded pickup (a potion) those within GUARD_NEAR of the drop or of the character `here`,
    the pickup key's own measure (no pickup is begun among a pack: Tower Cellar 5, 2026-10-11). None for a
    goal of another kind: a fight's pack is the fight, a place is gone through, a valuable is gone for."""
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
    """The goal a press of the teleport key means now. `stage`: the stage the level is at, when the
    press performs one (`Progress.step`); `card`: the level card's first mark, of this level; `foes`: the
    hostiles in the world; `remembered`, `supers`: the tracker's memory of the level; `gone`: remembered
    units not to go to; `elsewhere()`: (a place, what it is) to look in when nothing is known of a boss
    (the nearest remembered hostile, an unexplored room), asked only then; `drop`: a valuable beside the
    character that is taken first; `side`: a drop a level run takes on its way (macros/pickup.py
    `choose`, the pickup key's own rules), gone to until within PICK_REACH and guarded when a potion;
    `stay`: a valuable a level run has no room for, stood by (`WAIT`); `reach`: the distance the build strikes
    from; `spend`: what the way may cost; `entry`: the card's door's remembered entry (world units, `way_out`).
    None: there is nothing to go to (no stage, no mark, nothing known of the boss)."""
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
    """The goal of a way to another level at the card's mark. A door, stairs, a cave's mouth: the mark, within
    PLACE_NEAR, where going through is the route's press (U13); with `entry` (world units, where the character stands
    to click the door: macros/hunt.py `door_entry`), that spot, within ENTRY_GOAL_NEAR. An open passage
    (`Target.passage`: the River of Flame's bridge into the Chaos Sanctuary, a border; the player, 2026-10-15: "move
    our target slightly further so the map changes"): its far place a tile inside the next level, within PASSAGE_NEAR,
    from where a walk crosses."""
    if card.passage is not None:
        place = (card.passage[0] * TILE_UNITS, card.passage[1] * TILE_UNITS)
        return Goal(label, place, ENTER, PASSAGE_NEAR, spend, mark=card, route=route, stage=stage)
    if entry is not None:  # where the door's click goes in with no walk: the last hop lands on it, not short of it
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
    """The route's own goal, the stage's and nothing on the side: what `goal_of` means with no drop to take
    and no valuable to stand by, and what the level card's first row points at (macros/card_goal.py; the
    player, 2026-10-14: the arrow follows the next undone goal, the macro's own goal model). The arguments
    are `goal_of`'s. None: there is nothing to go to (no stage, no mark, nothing known of the boss)."""
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
        # No stage, or one whose mark the card does not hold yet: the card's own first mark, as the key
        # goes without a route. The label says when that is not the stage's.
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
