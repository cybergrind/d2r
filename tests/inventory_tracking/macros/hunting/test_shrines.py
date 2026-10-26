"""Experience Shrines on a level run's way (macros/hunting/shrines.py; the player, 2026-10-20 ~18:43: "i'd like you to
take exp shrines along the way"): one on the way is gone to and used; one off the way, guarded, of another type, or
after a death is left; the detour's bounds."""

import json
import logging
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.game.records import Thing
from inventory_tracking.levels.model import Ground
from inventory_tracking.loot.ground import shrines_in
from inventory_tracking.loot.shrines import EXPERIENCE_SECONDS, EXPERIENCE_SHRINE, EXPERIENCE_STATE, SHRINE_CLASSES
from inventory_tracking.macros.goals import PICK_NEAR, PICK_UP, PLACE_NEAR, Goal
from inventory_tracking.macros.hunting import shrines
from inventory_tracking.macros.pursuit import FULL, Operate, Pursuit
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.routes.model import ENTER, FIGHT
from tests.inventory_tracking.macros.test_hunt import attack_mode, foe, game, hunter, keys, me
from tests.inventory_tracking.macros.test_tz_leveling import FLOOR


DATA = Path(__file__).resolve().parents[4] / 'third-parties' / 'd2data' / 'json'
DEER_SHRINE = 2  # objects.txt DeerShrine (SubClass 1)
DOOR = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Infernal Pit')


def level_run(east: float = 8.0, kind: int = EXPERIENCE_SHRINE, looped: bool = False):
    """A KP_1 level run (no press) with a shrine `east` units east of the character."""
    play = game()
    hunt = hunter(play, ground=FLOOR)
    here = me(play.world)
    play.thing = Thing(700, DEER_SHRINE, 0, here.x + east, here.y)
    play.shrine_type = kind
    hunt.pursuit = Pursuit('pickup', 0.0, advance=False, leash=FULL, looped=looped)
    return play, hunt, play.run()


def side(play, hunt, run, goal: Goal | None = DOOR) -> Goal | None:
    return shrines.side_goal(hunt, run, play.world, goal, hunt.pursuit)


def test_the_data_cited_holds_in_the_d2data_dump():
    table = json.loads((DATA / 'shrines.json').read_text())[str(EXPERIENCE_SHRINE)]
    assert table['Name'] == 'Experience Shrine'
    assert table['Duration in frames'] * 0.04 == EXPERIENCE_SECONDS == 144.0
    assert 'reset time in minutes' not in table  # used once, never comes back
    states = json.loads((DATA / 'states.json').read_text())
    assert states['shrine_experience']['*ID'] == EXPERIENCE_STATE
    assert all('group' not in row for name, row in states.items() if name.startswith('shrine_'))
    objects = json.loads((DATA / 'objects.json').read_text())
    assert {int(k) for k, row in objects.items() if row.get('SubClass', 0) & 1} == SHRINE_CLASSES


def test_shrines_are_read_from_the_object_rows_by_class_type_byte_and_table_pointer():
    play, _, _ = level_run()
    rows = play.objects()
    [found] = shrines_in(rows)
    assert (found.shrine_type, found.unit_id, found.mode, found.label) == (15, 700, 0, 'Experience Shrine')
    assert shrines_in([rows[0] | {'txt_id': 181}]) == []  # a chest's class: no shrine, whatever its bytes
    no_table = bytearray(bytes.fromhex(rows[0]['data']))
    no_table[0x10:0x18] = bytes(8)
    assert shrines_in([rows[0] | {'data': no_table.hex()}]) == []
    assert shrines_in([{'unit_id': 1, 'txt_id': 2, 'mode': 0}]) == []  # its data unread


def test_an_experience_shrine_on_the_way_is_gone_to_and_used(caplog):
    play, hunt, _ = level_run(east=30.0)
    with caplog.at_level(logging.INFO):
        attack_mode(play, hunt, until=8.0)
    assert play.thing is not None
    assert play.thing.mode == 2
    assert 'Macro: shrine: Experience Shrine at (5030, 5000) is 30 away: going to it' in caplog.messages
    assert 'Macro: shrine: Experience Shrine at (5030, 5000) used' in caplog.messages


def test_the_judge_clicks_it_from_its_reach_and_the_route_goes_on_after():
    play, hunt, run = level_run()
    found = hunt.judge(run, play.world, [], Ground(FLOOR), in_reach=False)
    assert isinstance(found.act, Operate)
    assert found.goal is not None
    assert found.goal.shrine
    hunt.operate(run, play.world, found.goal, keys)
    assert play.thing is not None
    assert play.thing.mode == 2
    assert side(play, hunt, run) == DOOR  # used: the route's own goal again


def test_a_shrine_off_the_way_is_not_gone_for(caplog):
    play, hunt, run = level_run(east=PICK_NEAR + 5.0)
    with caplog.at_level(logging.INFO):
        assert side(play, hunt, run) == DOOR
    assert any('not on the way' in line for line in caplog.messages)
    play, hunt, run = level_run(east=PICK_NEAR - 5.0)
    found = side(play, hunt, run)
    assert found is not None
    assert found.shrine


def test_the_loop_takes_one_teleport_brings_within_its_seconds(monkeypatch):
    play, hunt, run = level_run(east=60.0, looped=True)
    monkeypatch.setattr(hunt.travel, 'means', lambda *a: shrines.HOPS)
    monkeypatch.setattr(hunt.travel, 'eta', lambda *a: shrines.SHRINE_TELEPORT - 0.5)
    found = side(play, hunt, run)
    assert found is not None
    assert found.shrine
    play, hunt, run = level_run(east=60.0, looped=True)
    monkeypatch.setattr(hunt.travel, 'means', lambda *a: shrines.HOPS)
    monkeypatch.setattr(hunt.travel, 'eta', lambda *a: shrines.SHRINE_TELEPORT + 0.5)
    assert side(play, hunt, run) == DOOR


@pytest.mark.parametrize('kind', [18, 7, 12, 14])  # Gem, Combat, Skill, Stamina
def test_no_other_shrine_is_ever_taken(caplog, kind):
    play, hunt, run = level_run(kind=kind)
    with caplog.at_level(logging.INFO):
        assert side(play, hunt, run) == DOOR
    assert any('left: not an Experience Shrine' in line for line in caplog.messages)


def test_hostiles_by_the_shrine_or_low_life_make_it_wait_and_bring_no_fight():
    play, hunt, run = level_run()
    play.world = replace(play.world, monsters=(foe(5, 5008.0 + shrines.SHRINE_GUARD - 1.0, 5000.0),))
    assert side(play, hunt, run) == DOOR
    play.world = replace(play.world, monsters=())
    play.loot = replace(play.loot, life=300, max_life=1000)
    assert side(play, hunt, run) == DOOR
    play.loot = replace(play.loot, life=900, max_life=1000)
    found = side(play, hunt, run)
    assert found is not None
    assert found.shrine


def test_a_fight_a_valuable_and_a_stand_by_come_first():
    play, hunt, run = level_run()
    fight = Goal('Andariel', (5010.0, 5000.0), FIGHT, 20.0, PRESSED, unit=3, route='Andariel')
    rune = Goal('Ko Rune, on the way', (5003.0, 5000.0), PICK_UP, 20.0, PRESSED, unit=9)
    for goal in (fight, rune):
        assert side(play, hunt, run, goal) == goal
    found = side(play, hunt, run, None)  # no goal of the route's: the shrine still
    assert found is not None
    assert found.shrine


def test_nothing_after_a_death():
    play, hunt, run = level_run()
    found = side(play, hunt, run)
    assert found is not None
    dead = replace(play.world, player=replace(me(play.world), mode=17))
    play.world = dead
    assert shrines.side_goal(hunt, run, dead, DOOR, hunt.pursuit) == DOOR
    clicks = len([e for e in play.keys.events if e[0] == 'click'])
    hunt.operate(run, dead, found, keys)
    assert len([e for e in play.keys.events if e[0] == 'click']) == clicks
    assert play.thing is not None
    assert play.thing.mode == 0


def test_a_press_or_the_switch_off_takes_no_shrine(monkeypatch):
    play, hunt, run = level_run()
    assert shrines.side_goal(hunt, run, play.world, DOOR, None) == DOOR
    monkeypatch.setattr(shrines, 'EXP_SHRINES', False)
    assert side(play, hunt, run) == DOOR


def test_the_detour_is_bounded_in_seconds_and_tries(caplog):
    play, hunt, run = level_run()
    assert side(play, hunt, run) is not None
    play.clock.now += 30.0  # a fight between: its time is not the shrine's
    assert side(play, hunt, run) is not None
    with caplog.at_level(logging.INFO):
        for _ in range(int(shrines.SHRINE_SECONDS / 0.5) + 3):
            play.clock.now += 0.5
            found = side(play, hunt, run)
            if found == DOOR:
                break
    assert found == DOOR
    assert any('left: not used in 10 s gone for' in line for line in caplog.messages)
    play, hunt, run = level_run()
    hunt.shrines.begin(play.world.game_name)
    hunt.shrines.tries[700] = shrines.SHRINE_TRIES
    assert side(play, hunt, run) == DOOR
    assert (shrines.SHRINE_WALK, shrines.SHRINE_TELEPORT, shrines.SHRINE_SECONDS) == (40.0, 2.5, 10.0)


def test_a_second_one_soon_after_waits_and_later_renews_the_effect():
    play, hunt, run = level_run()
    hunt.shrines.begin(play.world.game_name)
    hunt.shrines.used_at = play.clock.now - 5.0
    assert side(play, hunt, run) == DOOR
    hunt.shrines.used_at = play.clock.now - shrines.REFRESH_AFTER - 1.0
    found = side(play, hunt, run)
    assert found is not None
    assert found.shrine


def test_no_way_to_it_leaves_it_and_the_level_is_not_explored_for_it():
    play, hunt, run = level_run()
    found = side(play, hunt, run)
    assert found is not None
    shrines.no_way(hunt, found, 'no way toward Experience Shrine, on the way: walled')
    assert 700 in hunt.shrines.left
    assert side(play, hunt, run) == DOOR


def leveled(play, level: int | None) -> None:
    stats = dict(play.loot.stats)
    stats.pop(12, None)
    if level is not None:
        stats[12], stats[13] = level, 1_000_000  # itemstatcost.txt level, experience
    play.loot = replace(play.loot, stats=tuple(stats.items()))


@pytest.mark.parametrize(('terror', 'level', 'taken'), [
    (True, 92, True), (True, 98, True), (True, 99, False), (True, None, False), (False, 92, False),
])  # fmt: skip
def test_in_a_terror_zone_under_99_every_experience_shrine_is_gone_for(monkeypatch, caplog, terror, level, taken):
    # the player, 2026-10-25 ~17:53: "in TZ if we're not 99 lvl already we should use all experience shrines"
    play, hunt, run = level_run(east=PICK_NEAR + 60.0)  # off the way, past SHRINE_SIGHT
    monkeypatch.setattr(hunt.bearings, 'terror', lambda area: terror)
    leveled(play, level)
    with caplog.at_level(logging.INFO):
        found = side(play, hunt, run)
    assert (found is not None and found.shrine) is taken, (terror, level)
    if taken:
        assert any('(terror zone: every one)' in line for line in caplog.messages)


def test_in_a_terror_zone_a_second_one_is_taken_at_once_and_the_quiet_still_holds(monkeypatch):
    play, hunt, run = level_run(east=PICK_NEAR + 20.0)
    monkeypatch.setattr(hunt.bearings, 'terror', lambda area: True)
    leveled(play, 95)
    hunt.shrines.begin(play.world.game_name)
    hunt.shrines.used_at = run.clock() - 1.0  # one used a second ago: no REFRESH_AFTER wait here
    found = side(play, hunt, run)
    assert found is not None
    assert found.shrine
    monkeypatch.setattr(shrines, 'TZ_EVERY_SHRINE', False)
    assert side(play, hunt, run) == DOOR  # the switch off: as before
    monkeypatch.setattr(shrines, 'TZ_EVERY_SHRINE', True)
    monkeypatch.setattr(shrines, 'quiet', lambda *a: ('hostiles', 'waits: hostiles'))
    assert side(play, hunt, run) == DOOR  # hostiles by it: it waits, as everywhere
