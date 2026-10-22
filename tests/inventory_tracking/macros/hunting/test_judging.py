"""The act loop's super chests in the Kurast camp huts, 02:32-02:40 on 2026-10-21 (rca/2026-10-21/super-chest-misses-
findings.md): clicked from 8.5-10 units outside the hut's wall, where the game moved nobody, three tries from the same
spot each (hunting/judging.py CHESTS_NOT_ACROSS_WALLS, hunting/choice.py NEARER_CLEARING)."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Thing
from inventory_tracking.levels.model import SEALS, SUPER_CHEST, UNIQUE_CHEST, Ground, Target, Walkable, pack_cells
from inventory_tracking.macros.agenda import COVER, Agenda
from inventory_tracking.macros.goals import PLACE_NEAR, USE_NEAR, Goal
from inventory_tracking.macros.hunting import choice, judging
from inventory_tracking.macros.pursuit import FULL, Move, Operate, Pursuit
from inventory_tracking.macros.runmode import AGENDA, Mode
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.routes.model import USE
from tests.inventory_tracking.macros.test_hunt import EAST, game, hunter


# A hut's wall: '#' a column 34 units long at x 5004 from y 4980, the way round it under its end (one char a unit,
# from (4980, 4980)); the character at (5000, 5000) west of it
HUT_ROWS = (*('........................#...............',) * 34, *('.' * 40,) * 6)
HUT_BITS = ''.join(row.replace('.', '1').replace('#', '0') for row in HUT_ROWS)
HUT = Walkable(996, 996, 8, 8, pack_cells(HUT_BITS), pack_cells(HUT_BITS))
FLOOR = tuple(Walkable(room.x, room.y, 8, 8, pack_cells('1' * 1600)) for room in EAST)
GROUND = (HUT, *FLOOR)
BEHIND = (5009.0, 5000.0)  # 9 east, across the wall: ~33 round its end (Upper Kurast 02:37:03: 9.9 straight, 104)
OPEN_SIDE = (4991.0, 5000.0)  # 9 west, on the character's side: a clear line
CHEST = 1820989529


def hut_run(place: tuple[float, float]):
    """The act loop's run (an agenda kind: rush off) in a hut level with one closed super chest at `place`."""
    play = game(area=117)
    hunt = hunter(play, ground=GROUND)
    hunt.agenda, hunt.agenda_policy = Agenda(), lambda area: COVER
    hunt.agenda.begin('g')
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    hunt.mode = Mode(True, AGENDA, agenda=True)
    run = play.run()
    run.things = lambda: (Thing(CHEST, SUPER_CHEST, 0, *place),)
    return play, hunt, run


def judged(play, hunt, run):
    return hunt.judge(run, play.world, [], Ground(GROUND), in_reach=False)


@pytest.mark.parametrize('switch', [True, False])
def test_an_agenda_chest_behind_a_hut_wall_is_gone_to_first_and_one_on_the_open_side_clicked(monkeypatch, switch):
    monkeypatch.setattr(judging, 'CHESTS_NOT_ACROSS_WALLS', switch)
    play, hunt, run = hut_run(BEHIND)
    found = judged(play, hunt, run)
    assert found.goal is not None
    assert (found.goal.do, found.goal.unit) == (USE, CHEST)
    if switch:
        assert isinstance(found.act, Move)  # the Teleport into the hut first
        assert found.place == BEHIND  # toward the chest's own place
    else:
        assert isinstance(found.act, Operate)  # clicked across the wall, as before
    play, hunt, run = hut_run(OPEN_SIDE)
    found = judged(play, hunt, run)
    assert isinstance(found.act, Operate)  # a clear line: clicked from where the character stands
    assert found.goal is not None
    assert found.goal.near == USE_NEAR  # the chest's own reach, not the LK kind's OPEN_NEAR


def chest_goal(use: int) -> Goal:
    mark = Target(117, (), (1001.8, 1000.0), 'Super chest', 'target', use=use)
    return Goal('agenda: Super chest', BEHIND, USE, USE_NEAR, PRESSED, unit=CHEST, mark=mark, clearing=True)


@pytest.mark.parametrize('switch', [True, False])
def test_the_wall_check_is_for_the_chests_of_every_level_run_and_seals_keep_theirs(monkeypatch, switch):
    monkeypatch.setattr(judging, 'CHESTS_NOT_ACROSS_WALLS', switch)
    agenda = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    rushed = replace(agenda, agenda=False, rush=True)
    for use in (SUPER_CHEST, UNIQUE_CHEST):
        assert judging.wall_checked(agenda, chest_goal(use)) is switch
        assert judging.wall_checked(rushed, chest_goal(use))  # the LK chests kind's, as before
    seal = chest_goal(SEALS[0])
    assert not judging.wall_checked(agenda, seal)  # a seal on a terror zone run: clicked from its reach, as before
    assert judging.wall_checked(rushed, seal)
    assert not judging.wall_checked(replace(agenda, paused=True), chest_goal(SUPER_CHEST))  # no level run working
    assert not judging.wall_checked(None, chest_goal(SUPER_CHEST))


@pytest.mark.parametrize('switch', [True, False])
def test_an_agenda_chest_whose_click_did_not_take_is_made_again_from_nearer(monkeypatch, switch):
    # 02:39:34-02:39:40: two tries from the same spot 9 units off, then the route's goal, made nearer, teleported onto
    # the chest and it opened in 0.28 s. Off: the miss goes under the route's goal (`Hunter.base`), as before.
    monkeypatch.setattr(judging, 'CHESTS_NOT_ACROSS_WALLS', False)  # the click across the wall, as on the night
    monkeypatch.setattr(choice, 'NEARER_CLEARING', switch)
    play, hunt, run = hut_run(BEHIND)
    first = judged(play, hunt, run)
    assert isinstance(first.act, Operate)
    hunt.missed = None
    route = Goal('Super chests', (5100.0, 5000.0), USE, USE_NEAR, PRESSED, route='Lower Kurast')
    hunt.base = route
    key = choice.missed_key(first.act.goal if switch else route)
    hunt.missed = (key, run.clock() + 15.0)  # as `pursue` notes an Operate that raised
    again = judged(play, hunt, run)
    assert again.goal is not None
    if switch:
        assert key == f'agenda: Super chest ({CHEST})'  # every agenda chest has that label: its unit tells them apart
        assert again.goal.near == PLACE_NEAR
        assert isinstance(again.act, Move)  # gone onto the chest first
    else:
        assert key == 'Super chests'
        assert again.goal.near == USE_NEAR
        assert isinstance(again.act, Operate)  # the same click from the same spot


def test_the_miss_key_of_a_route_goal_is_its_label_and_a_clearing_goals_holds_its_unit():
    route = Goal('Super chests', (5100.0, 5000.0), USE, USE_NEAR, PRESSED, route='Lower Kurast')
    assert choice.missed_key(route) == 'Super chests'
    assert choice.from_nearer(('Super chests', 20.0), route, 10.0) == replace(route, near=PLACE_NEAR)
    assert choice.from_nearer(('Super chests', 20.0), route, 21.0) == route  # the miss is over
    chest = chest_goal(SUPER_CHEST)
    other = replace(chest, unit=CHEST + 1, place=OPEN_SIDE)
    assert choice.from_nearer((choice.missed_key(chest), 20.0), other, 10.0) == other  # another chest: no nearer
    assert choice.from_nearer(None, chest, 10.0) == chest
    assert choice.from_nearer(('x', 20.0), None, 10.0) is None


# --- a fight goal no shot reaches from where the moves end: Kurast Sewers 1, 17:51:43-17:52:29 on 2026-10-21 ---
# "a super healing potion, on the way: the fight first (2 in the way): as near as a move ends, and nothing in reach",
# an Undead SoulKiller elite (215, a doll: the pickup's dolls are fought from 20) 22 away behind a wall; 45 s still and
# the game left (rca/2026-10-21/no-hits-findings.md §7). Here the hut's wall stands between, the elite 21 east.
ELITE = 2612433046
ELITE_AT = (5021.0, 5000.0)


def sewer_fight() -> Goal:
    from inventory_tracking.routes.model import FIGHT

    stand_off = replace(PRESSED, short=20.0)  # goals.py `first_fight` with live dolls: min(LAND_UNITS 20, reach - 2)
    return Goal(
        'a super healing potion, on the way: the fight first (2 in the way)',
        ELITE_AT,
        FIGHT,
        22.08,
        stand_off,
        unit=ELITE,
        route='Kurast Sewers Level 1',
    )


def sewer_run(monkeypatch, *, firing_stand: bool):
    from inventory_tracking.combat.threats import dolls
    from tests.inventory_tracking.macros.test_hunt import foe

    monkeypatch.setattr(judging, 'FIRING_STAND', firing_stand)
    play, hunt, run = hut_run(OPEN_SIDE)
    run.things = lambda: ()
    elite = foe(ELITE, *ELITE_AT, flags=0x08, txt_id=215, life=128, max_life=128)
    play.world = replace(play.world, monsters=(elite,))
    assert dolls.runner(215)
    fight = sewer_fight()
    monkeypatch.setattr(hunt, 'goal', lambda *_: fight)
    monkeypatch.setattr(hunt, 'cleared', lambda run, world, foes, ground, goal: goal)
    return play, hunt, run, elite


@pytest.mark.parametrize('firing_stand', [True, False])
def test_a_fight_goal_behind_a_wall_goes_onto_its_firing_spot_whatever_its_stand_off(monkeypatch, firing_stand):
    from inventory_tracking.macros.build import NoWay

    play, hunt, run, elite = sewer_run(monkeypatch, firing_stand=firing_stand)
    found = hunt.judge(run, play.world, [elite], Ground(GROUND), in_reach=False)
    if firing_stand:
        assert isinstance(found.act, Move)  # toward a spot with a clear shot
        assert found.place is not None
        assert math.dist(found.place, ELITE_AT) >= 13.5  # on the stand-off's outer ring first (17), not into the doll
    else:  # the night's: the spot is within the stand-off, "as near as a move ends, and nothing in reach"
        assert isinstance(found.act, NoWay)
        assert 'as near as a move ends, and nothing in reach' in found.act.reason


def test_a_fight_goal_no_shot_reaches_is_left_alone_after_the_unshot_seconds(monkeypatch):
    from inventory_tracking.macros.hunting.base import UNSHOT_SECONDS

    assert UNSHOT_SECONDS is not None
    play, hunt, run, elite = sewer_run(monkeypatch, firing_stand=False)
    hunt.judge(run, play.world, [elite], Ground(GROUND), in_reach=False)
    assert ELITE not in hunt.untouchable
    play.clock.now += UNSHOT_SECONDS + 0.1
    hunt.judge(run, play.world, [elite], Ground(GROUND), in_reach=False)
    assert ELITE in hunt.untouchable  # the next look's goal goes on: the pickup, the next hostile, the route
    assert ELITE not in hunt.foes(play.world, play.clock.now)


def test_a_boss_no_shot_reaches_is_never_left_alone(monkeypatch):
    play, hunt, run, elite = sewer_run(monkeypatch, firing_stand=False)
    baal = replace(elite, txt_id=544)
    play.world = replace(play.world, monsters=(baal,))
    hunt.judge(run, play.world, [baal], Ground(GROUND), in_reach=False)
    play.clock.now += 10.0
    hunt.judge(run, play.world, [baal], Ground(GROUND), in_reach=False)
    assert hunt.untouchable == {}


def test_the_routes_own_fight_stage_monster_is_never_left_alone_unshot_or_recovering(monkeypatch):
    from inventory_tracking.routes.model import FIGHT, Stage

    play, hunt, run, elite = sewer_run(monkeypatch, firing_stand=False)
    staged = replace(sewer_fight(), label='Fangskin', stage=Stage(FIGHT, boss='Fangskin'))
    monkeypatch.setattr(hunt, 'goal', lambda *_: staged)
    hunt.judge(run, play.world, [elite], Ground(GROUND), in_reach=False)
    play.clock.now += 10.0
    hunt.judge(run, play.world, [elite], Ground(GROUND), in_reach=False)
    hunt.recover_asked = play.clock.now
    hunt.judge(run, play.world, [elite], Ground(GROUND), in_reach=False)
    assert hunt.untouchable == {}


def test_the_still_watchdogs_recovery_leaves_the_last_fight_goal_and_its_blockers_alone(monkeypatch):
    play, hunt, run, elite = sewer_run(monkeypatch, firing_stand=False)
    other = replace(elite, unit_id=1306208331, x=5025.0)
    play.world = replace(play.world, monsters=(elite, other))
    hunt.judge(run, play.world, [elite, other], Ground(GROUND), in_reach=False)
    hunt.blocking = ('a super healing potion, on the way', frozenset({other.unit_id}), play.clock.now + 5.0)
    hunt.recover_asked = play.clock.now
    hunt.judge(run, play.world, [elite, other], Ground(GROUND), in_reach=False)
    assert hunt.recover_asked is None
    assert {ELITE, other.unit_id} <= set(hunt.untouchable)
    assert hunt.blocking is None
