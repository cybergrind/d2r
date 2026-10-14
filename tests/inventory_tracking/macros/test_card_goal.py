"""The level card's goal is the route's, as the macro's (rca/2026-10-14/run-1916-hud-findings.md §1)."""

from inventory_tracking.levels.model import SEALS, Poi, Room, Target
from inventory_tracking.macros.card_goal import NOT_SEEN, CardGoals
from inventory_tracking.macros.goals import FIGHT, USE, goal_of, route_goal
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.travel import STANDING
from inventory_tracking.macros.world import Drop, Thing
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.bosses import SUPER_UNIQUE_FLAG


CS = 108
ROOM = Room(1, 0, 0, 200, 200)
STAR = Poi('Diablo', ROOM, 'target', (100.0, 100.0))
VIZIER_1 = Poi('Vizier seal 1', ROOM, 'target', (20.0, 100.0), use=SEALS[4])
VIZIER_2 = Poi('Vizier seal 2', ROOM, 'target', (30.0, 110.0), use=SEALS[3])
DE_SEIS = Poi('De Seis seal', ROOM, 'target', (100.0, 20.0), use=SEALS[2])
MARKS = (STAR, VIZIER_1, VIZIER_2, DE_SEIS)


def progress(dead=()):
    found = Progress(ROUTES, PERFORMED, lambda: frozenset(dead))
    found.note('game', CS)
    return found


def first(mark: Poi) -> Target:
    return Target(CS, (ROOM,), mark.spot, mark.label, mark.kind, False, (), mark.use)


def opened(found: Progress, *marks: Poi) -> None:
    for mark in marks:
        found.used(CS, mark.label, mark.spot, (mark.spot,))


def test_the_card_points_at_the_next_seal_and_drops_the_opened_one():
    found = progress()
    opened(found, VIZIER_1)
    goals = CardGoals(found)

    goal = goals.goal(CS, (0.0, 0.0), first(VIZIER_2))

    assert (goal.label, goal.do, goal.mark.label) == ('Vizier seal 2', USE, 'Vizier seal 2')
    labels, places = goals.done(CS)
    assert 'Vizier seal 1' in labels and ('Vizier seal 1', VIZIER_1.spot) in places
    assert 'Vizier seal 2' not in labels


def test_a_fight_without_a_mark_points_at_the_boss_where_the_tracker_has_him():
    found = progress(dead={'Grand Vizier of Chaos'})
    opened(found, VIZIER_1, VIZIER_2, DE_SEIS)
    held = [(312, 312, SUPER_UNIQUE_FLAG, 480.0, 90.0), (400, 310, 0, 470.0, 95.0)]
    goals = CardGoals(found, hostiles=lambda area: held if area == CS else [])

    goal = goals.goal(CS, (0.0, 0.0), first(STAR))  # the card's own order leads with the star

    assert (goal.label, goal.do, goal.unit, goal.place) == ('Lord De Seis', FIGHT, 312, (480.0, 90.0))
    assert goal.mark is None


def test_a_boss_nothing_is_known_of_is_a_goal_not_seen():
    found = progress(dead={'Grand Vizier of Chaos'})
    opened(found, VIZIER_1, VIZIER_2, DE_SEIS)

    goal = CardGoals(found).goal(CS, (5.0, 5.0), first(STAR))

    assert not goal.known and goal.stage.boss == 'Lord De Seis' and NOT_SEEN in goal.label


def test_no_goal_once_the_boss_is_dead_and_his_mark_is_done():
    dead = {'Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls', 'Diablo'}
    found = progress(dead=dead)
    opened(found, VIZIER_1, VIZIER_2, DE_SEIS)
    for label in ('Infector seal 1', 'Infector seal 2'):
        found.used(CS, label, (0.0, 0.0), ((0.0, 0.0),))
    goals = CardGoals(found)

    assert goals.goal(CS, (0.0, 0.0), first(STAR)) is None  # loot, then leave: nothing to point at
    assert 'Diablo' in goals.done(CS)[0]


def test_a_seal_opened_by_hand_is_done_at_the_guides_poll():
    found = progress()
    goals = CardGoals(found)
    assert goals.wanted(CS, MARKS) == frozenset(SEALS[2:5])
    x, y = (VIZIER_1.spot[0] * TILE_UNITS, VIZIER_1.spot[1] * TILE_UNITS)
    shut = Thing(9, SEALS[4], 0, x + 3, y)

    assert not goals.note(CS, (0.0, 0.0), MARKS, [shut])
    assert goals.note(CS, (0.0, 0.0), MARKS, [Thing(9, SEALS[4], 1, x + 3, y)])

    assert ('Vizier seal 1', VIZIER_1.spot) in goals.done(CS)[1]
    assert found.step(CS).stage.mark == 'Vizier seal 2'
    assert SEALS[4] not in goals.wanted(CS, MARKS)  # read no more


def test_a_stand_is_done_within_reach_of_its_mark_whoever_moved():
    found = Progress(ROUTES, PERFORMED, lambda: frozenset())
    found.note('game', 93)  # Kurast Sewers level 2: stand at Khalim's Heart
    heart = Poi("Khalim's Heart", ROOM, 'target', (40.0, 40.0))
    goals = CardGoals(found)
    far, near = (0.0, 0.0), (40.0 * TILE_UNITS + 5, 40.0 * TILE_UNITS)

    assert not goals.note(93, far, (heart,), ())
    assert goals.note(93, near, (heart,), ())
    assert not goals.note(93, near, (heart,), ())  # once
    assert "Khalim's Heart" in goals.done(93)[0]


def test_goal_of_without_a_drop_is_the_route_goal():
    found = progress()
    stage = found.step(CS).stage
    kwargs = {'spend': STANDING, 'reach': 20.0, 'stage': stage, 'route': 'Diablo', 'card': first(VIZIER_1)}

    assert goal_of((1.0, 2.0), **kwargs) == route_goal((1.0, 2.0), **kwargs)
    drop = Drop(5, 3.0, 4.0, 'Ber Rune', 'valuable')
    assert goal_of((1.0, 2.0), drop=drop, **kwargs).label == 'Ber Rune, before leaving'
