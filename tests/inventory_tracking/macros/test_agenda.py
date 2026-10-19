"""The goal agenda (macros/agenda.py, macros/goals-plan.md): the stack before the queue, the queue by tier and distance,
no goals = leave the game, never with a valuable on the ground, and a level run's targets in their order."""

from inventory_tracking.macros import agenda as agenda_module
from inventory_tracking.macros.agenda import (
    CHEST,
    CHEST_NEAR,
    COVER,
    DROP,
    DROP_GUARD,
    EXPLORE,
    FULL_CLEAR,
    KILL,
    LEADER,
    LEAVE_GAME,
    LEVEL,
    LOOT,
    NAVIGATE,
    NEW_GAME,
    NEXT_LEVEL,
    ON_THE_WAY,
    OPEN,
    PICKUP,
    PORTAL_TO_TOWN,
    SIGHTED,
    THROUGH_PORTAL,
    TOWN_ROUTINE,
    TRIES,
    WAYPOINT,
    WORK,
    Agenda,
    Leader,
    LevelView,
    Objective,
    room_package,
    town_of,
)


def aimed(agenda: Agenda, seen: LevelView) -> Objective:
    """The level run's target, which the test expects there to be."""
    found = agenda.in_level(seen)
    assert found is not None
    return found


CATACOMBS_3, ROGUE_ENCAMPMENT, FORTRESS, CITY_OF_THE_DAMNED = 36, 1, 103, 106
HERE = (5000.0, 5000.0)


def test_the_room_package_pops_portal_town_routine_back_and_continue_in_order_and_the_queue_resumes():
    # The player, 2026-10-19: "we need to empty the inventory -> create teleport -> put on stack continue run -> put on
    # stack go back through teleport in town act 1 -> put on stack do town routine (identify/store/etc) -> put on stack
    # go through just create teleport ... then we discard stack and continue with prioritized queue"
    agenda = Agenda()
    agenda.begin('cyber32')
    level = Objective(LEVEL, 'the Catacombs Level 3 run', WORK, CATACOMBS_3)
    agenda.refresh([level])
    agenda.push(*room_package(CATACOMBS_3))

    made = []
    for _ in range(10):
        goal = agenda.next(HERE)
        made.append((goal.kind, goal.to, goal.exit))
        if goal.kind == LEVEL:
            break
        agenda.done(goal)

    assert made == [
        (PORTAL_TO_TOWN, ROGUE_ENCAMPMENT, ''),
        (WAYPOINT, FORTRESS, ''),
        (TOWN_ROUTINE, None, 'portal'),
        (WAYPOINT, ROGUE_ENCAMPMENT, ''),
        (THROUGH_PORTAL, CATACOMBS_3, ''),
        (LEVEL, None, ''),  # RESUME is popped by itself: no leg for it, the queue goes on
    ]
    assert agenda.stack == []


def test_in_act_4_the_package_has_no_waypoints_and_the_visit_walks_nowhere():
    kinds = [(goal.kind, goal.exit) for goal in room_package(CITY_OF_THE_DAMNED)]
    assert [kind for kind, _ in kinds] == [PORTAL_TO_TOWN, TOWN_ROUTINE, THROUGH_PORTAL, 'resume']
    assert dict(kinds)[TOWN_ROUTINE] == 'leave'


def test_a_leg_that_stops_keeps_its_goal_on_top_until_its_tries_run_out():
    agenda = Agenda()
    agenda.begin('g')
    agenda.push(*room_package(CATACOMBS_3))
    top = agenda.next(HERE)
    for _ in range(TRIES - 1):
        assert not agenda.failed(top)
        assert agenda.next(HERE) == top
    assert agenda.failed(top)  # dropped, said: no goal is tried forever
    assert agenda.next(HERE).kind == WAYPOINT


def test_with_no_goals_left_the_game_is_left_but_never_with_a_valuable_on_the_ground():
    # "we can have clearer signals for save/restart - when we have no more goals"; the hard rule of 2026-10-17
    agenda = Agenda()
    agenda.begin('g')
    assert agenda.next(HERE).kind == LEAVE_GAME
    kept = agenda.next(HERE, valuable='Ist Rune at (100, 200)')
    assert (kept.kind, kept.tier) == (PICKUP, SIGHTED)
    assert agenda.next(None, in_game=False).kind == NEW_GAME


def test_the_queue_gives_the_lowest_tier_then_the_nearest():
    agenda = Agenda()
    agenda.begin('g')
    far = Objective(KILL, 'far', LEADER, 1, (5100.0, 5000.0), 1)
    near = Objective(KILL, 'near', LEADER, 1, (5010.0, 5000.0), 2)
    onward = Objective(NEXT_LEVEL, 'on', 50, 1, to=2)
    agenda.refresh([onward, far, near])
    assert agenda.next(HERE) == near
    agenda.refresh([onward, far])
    assert agenda.next(HERE) == far
    agenda.refresh([onward])
    assert agenda.next(HERE) == onward


def test_drops_come_before_every_goal_of_the_metric_at_the_games_level():
    # The player, 2026-10-19 ~02:12: "the only thing that has more priority - proper interactions with drops (we cannot
    # run without picking desired items just with killing boss alone)"
    agenda = Agenda()
    agenda.begin('g')
    agenda.refresh(
        [
            Objective(LEVEL, 'the run', WORK, 37),
            Objective(LOOT, 'the loot', 40, 37),
            Objective(PICKUP, 'a Ring, still on the ground', SIGHTED, 37),
        ]
    )
    assert agenda.next(HERE).kind == PICKUP
    assert SIGHTED < WORK


def test_a_new_game_discards_the_package_and_the_leaders():
    agenda = Agenda()
    agenda.begin('g1')
    agenda.push(*room_package(CATACOMBS_3))
    agenda.in_level(LevelView(35, HERE, (Leader(7, (5010.0, 5000.0), 'champion'),)))
    assert agenda.kills
    assert agenda.begin('g2')
    assert (agenda.stack, agenda.kills) == ([], {})
    assert not agenda.begin('g2')


def view(**changes) -> LevelView:
    return LevelView(35, HERE, **changes)


def test_a_pickup_near_a_pack_comes_after_the_kill_near_it_then_the_distant_pack():
    # The player's example: "2 groups of mobs + pickup item: we may need some kill action near pickup item, then
    # pickup, then travel to distant group and kill it"
    agenda = Agenda()
    agenda.begin('g')
    drop = Objective(PICKUP, 'Ist Rune', DROP, 35, (5040.0, 5000.0), 900)
    by_the_drop = Leader(11, (5045.0, 5000.0), 'champion by the rune')
    distant = Leader(12, (5300.0, 5000.0), 'a distant champion')
    hostiles = ((11, (5045.0, 5000.0)), (13, (5038.0, 5004.0)), (12, (5300.0, 5000.0)))

    first = agenda.in_level(view(leaders=(by_the_drop, distant), hostiles=hostiles, side=drop))
    assert first is not None
    assert (first.kind, first.unit, first.tier) == (KILL, 13, DROP_GUARD)  # the nearest guard, a plain one too
    second = agenda.in_level(view(leaders=(by_the_drop, distant), hostiles=hostiles[:1] + hostiles[2:], side=drop))
    assert second is not None
    assert (second.kind, second.unit) == (KILL, 11)
    third = agenda.in_level(view(leaders=(distant,), hostiles=hostiles[2:], side=drop))
    assert third == drop  # the guards dead: the pickup, before any travel
    fourth = agenda.in_level(view(leaders=(distant,), hostiles=hostiles[2:]))
    assert fourth is not None
    assert (fourth.kind, fourth.unit, fourth.tier) == (KILL, 12, LEADER)


def test_a_herald_first_then_its_omen_then_the_nearest_leader():
    agenda = Agenda()
    agenda.begin('g')
    near = Leader(1, (5010.0, 5000.0), 'champion')
    herald = Leader(2, (5200.0, 5000.0), 'Herald', herald=True)
    assert aimed(agenda, view(leaders=(near, herald))).unit == 2
    omen = ((5100.0, 5000.0), (5080.0, 5000.0))
    coming = aimed(agenda, view(leaders=(near,), omens=(omen,)))
    assert (coming.kind, coming.place) == (NAVIGATE, (5080.0, 5000.0))  # nothing by its spot: the stand
    pack = aimed(agenda, view(leaders=(near,), omens=(omen,), hostiles=((3, (5110.0, 5000.0)),)))
    assert (pack.kind, pack.unit) == (KILL, 3)
    assert aimed(agenda, view(leaders=(near,))).unit == 1


def test_a_cover_area_tours_its_rooms_after_the_leaders_and_on_the_way_does_not():
    agenda = Agenda()
    agenda.begin('g')
    room = ((5500.0, 5500.0), 'an unexplored room')
    far = Leader(4, (5400.0, 5000.0), 'a far champion')  # 400 off: over WAY_UNITS

    covered = aimed(agenda, view(leaders=(far,), frontier=lambda: room, policy=COVER))
    assert covered.unit == 4  # COVER: every leader found, whatever the distance
    assert agenda.in_level(view(leaders=(far,), frontier=lambda: room, policy=ON_THE_WAY)) is None  # the route's goal
    rooms = aimed(agenda, view(frontier=lambda: room, policy=COVER))
    assert (rooms.kind, rooms.place) == (EXPLORE, room[0])
    remembered = Leader(5, (5600.0, 5000.0), 'the remembered monster', live=False)
    assert aimed(agenda, view(leaders=(remembered,), frontier=lambda: room)).kind == EXPLORE  # far: after the tour
    assert aimed(agenda, view(leaders=(remembered,), frontier=lambda: None)).unit == 5
    near = Leader(6, (5030.0, 5000.0), 'the remembered monster', live=False)
    assert aimed(agenda, view(leaders=(near,), frontier=lambda: room, policy=ON_THE_WAY)).unit == 6


def test_the_frontier_is_asked_only_when_the_rooms_are_wanted():
    asked = []
    agenda = Agenda()
    agenda.begin('g')

    def frontier():
        asked.append(1)
        return None

    agenda.in_level(view(leaders=(Leader(1, (5010.0, 5000.0), 'champion'),), frontier=frontier))
    agenda.in_level(view(frontier=frontier, policy=ON_THE_WAY))
    assert asked == []
    agenda.in_level(view(frontier=frontier, policy=FULL_CLEAR))
    assert asked == [1]


def test_a_leader_seen_is_a_kill_goal_until_it_is_neither_seen_nor_remembered():
    # "TZLevelingRoutine creates KillGoal for every elite/champ that it discovers"
    agenda = Agenda()
    agenda.begin('g')
    agenda.in_level(view(leaders=(Leader(1, (5010.0, 5000.0), 'champion'), Leader(2, (5090.0, 5000.0), 'unique'))))
    assert agenda.known(35) == 2
    agenda.in_level(view(leaders=(Leader(2, (5090.0, 5000.0), 'unique', live=False),)))
    assert agenda.known(35) == 1  # one dead (or gone where it was seen)
    assert agenda.kills[2].tier > LEADER  # remembered: after those in sight


def test_a_passed_target_gives_its_place_to_the_next():
    agenda = Agenda()
    agenda.begin('g')
    leaders = (Leader(1, (5010.0, 5000.0), 'near'), Leader(2, (5050.0, 5000.0), 'next'))
    assert aimed(agenda, view(leaders=leaders, passed=lambda place, unit: unit == 1)).unit == 2


def test_the_towns_of_the_acts_and_the_remembered_reach_held_to_the_hunts():
    from inventory_tracking.macros.hunt import REMEMBERED_NEAR

    assert [town_of(area) for area in (2, 37, 39, 40, 74, 75, 102, 103, 108, 109, 132)] == [
        1, 1, 1, 40, 40, 75, 75, 103, 103, 109, 109,
    ]  # fmt: skip
    assert agenda_module.REMEMBERED_NEAR == REMEMBERED_NEAR


# -- super chests (2026-10-19, the player: "we don't open intermediate goals, like superchests. probably we should add
# superchests to intemediate goals and open them along the way") ------------------------------------------------------


def test_a_super_chest_near_is_opened_after_the_drops_and_the_leaders_in_sight_before_the_rest():
    agenda = Agenda()
    agenda.begin('g')
    chest = ((70, (5040.0, 5000.0)),)
    champion = Leader(1, (5080.0, 5000.0), 'champion')  # in the read, within WAY_UNITS
    drop = Objective(PICKUP, 'Ist Rune', DROP, 35, (5010.0, 5000.0), 900)
    room = ((5030.0, 5000.0), 'an unexplored room')
    near = Leader(2, (5020.0, 5000.0), 'the remembered monster', live=False)  # within REMEMBERED_NEAR

    assert aimed(agenda, view(chests=chest, side=drop)) == drop  # the drops first
    assert aimed(agenda, view(chests=chest, leaders=(champion,), policy=ON_THE_WAY)).unit == 1  # the metric's next
    opened = aimed(agenda, view(chests=chest, leaders=(near,), frontier=lambda: room, policy=COVER))
    assert (opened.kind, opened.unit, opened.tier, opened.place) == (OPEN, 70, CHEST, (5040.0, 5000.0))
    # ON_THE_WAY too: before the route's own goal (no target of the agenda's otherwise)
    assert aimed(agenda, view(chests=chest, policy=ON_THE_WAY)).kind == OPEN
    assert aimed(agenda, view(chests=chest, policy=FULL_CLEAR, frontier=lambda: room)).kind == OPEN


def test_a_super_chest_far_off_is_no_detour_and_one_seen_is_kept_until_it_is_open():
    agenda = Agenda()
    agenda.begin('g')
    far = ((71, (5000.0 + CHEST_NEAR + 1.0, 5000.0)),)
    assert agenda.in_level(view(chests=far, policy=ON_THE_WAY)) is None  # the route's goal: no trip across the level
    rooms = aimed(agenda, view(chests=far, frontier=lambda: ((5300.0, 5000.0), 'a room'), policy=COVER))
    assert rooms.kind == EXPLORE
    # Seen once, out of the read now, still closed: a target once the character is near it ("seen on this level")
    assert aimed(agenda, LevelView(35, (5100.0, 5000.0), policy=ON_THE_WAY)).unit == 71
    assert agenda.in_level(LevelView(36, (5100.0, 5000.0), policy=ON_THE_WAY)) is None  # another level's: never
    # Opened (or tried out): never a target again in this game, whatever a later read says
    assert agenda.in_level(LevelView(35, (5100.0, 5000.0), policy=ON_THE_WAY, spent=frozenset((71,)))) is None
    assert agenda.in_level(LevelView(35, (5100.0, 5000.0), policy=ON_THE_WAY, chests=far)) is None
    assert agenda.begin('g2')
    assert (agenda.chests, agenda.opened) == ({}, set())


def test_a_super_chest_passed_gives_its_place_to_the_next():
    agenda = Agenda()
    agenda.begin('g')
    chests = ((70, (5040.0, 5000.0)), (72, (5050.0, 5000.0)))
    assert aimed(agenda, view(chests=chests, policy=ON_THE_WAY)).unit == 70  # the nearest
    assert aimed(agenda, view(chests=chests, policy=ON_THE_WAY, passed=lambda place, unit: unit == 70)).unit == 72


def test_the_chest_reach_is_held_to_the_full_clears():
    from inventory_tracking.macros.hunt import SUPER_NEAR

    assert CHEST_NEAR == SUPER_NEAR
