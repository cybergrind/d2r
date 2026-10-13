"""Golden net for the loop scenarios of test_reaction.py and test_handover.py: the fake-clock counts and timestamps
`Play` keeps (struck_at, pressed_at, released_at, moved_at, reads), per scenario, frozen in loop_counts.json.

Frozen: the fake clock's values, rounded to 3 places, and the lists in the order they happened. Not frozen: wall
time, which varies run to run (test_tick_cost.py measures it). A refactor of the loop must leave every number here
as it was; a change in behaviour shows as a diff in loop_counts.json. Regenerate with GOLDEN_REGEN=1.
"""

import json
import os
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock import mark as mark_module
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.levels.model import Level
from inventory_tracking.macros import teleport
from inventory_tracking.macros.hunt import TOUGH_POINTS
from inventory_tracking.macros.pickup import pick_up
from tests.inventory_tracking.scenarios.loop.helpers import (
    CHAMPION,
    NO_MARK_SLOTS,
    ROOMS,
    appear,
    attack_mode,
    foe,
    game,
    hunter,
    keys,
    left_click,
    vanish,
)
from tests.inventory_tracking.scenarios.loop.test_reaction import wall_at_5005


GOLDEN = Path(__file__).with_name('loop_counts.json')
REGEN = os.environ.get('GOLDEN_REGEN') == '1'


@pytest.fixture(autouse=True)
def no_door_entries_remembered(monkeypatch):
    """As loop/conftest.py: door entries live in memory only under test."""
    monkeypatch.setattr(teleport, 'ENTRIES', teleport.Entries(None))
    monkeypatch.setattr(teleport, 'AIMS', teleport.Entries(None))


# --- the scenarios: each plays the source test's scenario and returns its plays ---


def walking_into_reach():
    plays = []
    for arrives in (1.0, 1.013, 1.031, 1.052, 1.077, 1.094):  # every phase of the idle nap
        play = game(slots=NO_MARK_SLOTS)
        attack_mode(play, hunter(play), until=3.0, events=[(arrives, appear(play, foe(10, 5008.0, 5000.0)))])
        plays.append(play)
    return plays


def first_strike(flags):
    with pytest.MonkeyPatch.context() as patch:  # as the marks_all fixture of test_reaction.py
        patch.setattr(mark_module, 'why_not', lambda facts, monster: None)
        play = game(foe(10, 5008.0, 5000.0, flags))
        play.toughness[10] = 1000
        attack_mode(play, hunter(play), until=3.0)
    return [play]


def nothing_else_to_cast():
    play = game(foe(10, 5008.0, 5000.0), slots=NO_MARK_SLOTS)
    attack_mode(play, hunter(play), until=2.0)
    return [play]


def lined_monster_dies():
    play = game(foe(10, 5008.0, 5000.0), foe(11, 5000.0, 5009.0), slots=NO_MARK_SLOTS)
    play.toughness[10], play.toughness[11] = 3, 1000
    attack_mode(play, hunter(play), until=3.0)
    return [play]


def monster_out_of_reach_for_a_moment():
    monster = foe(10, 5008.0, 5000.0)
    play = game(monster, slots=NO_MARK_SLOTS)
    play.toughness[10] = 1000
    attack_mode(play, hunter(play), until=4.0, events=[(2.0, vanish(play, 10)), (2.2, appear(play, monster))])
    return [play]


def reachable_while_elite_behind_wall():
    play = game(foe(10, 5010.0, 5000.0, CHAMPION), foe(11, 5000.0, 5012.0), slots=NO_MARK_SLOTS)
    play.toughness[11] = 3
    attack_mode(play, hunter(play, ground=(wall_at_5005(),)), until=3.0)
    return [play]


def no_sigil_behind_wall():
    play = game(foe(10, 5010.0, 5000.0, CHAMPION), foe(11, 5003.5, 5000.0), slots=NO_MARK_SLOTS)
    play.toughness[11] = 3
    attack_mode(play, hunter(play, ground=(wall_at_5005(),)), until=3.0)
    return [play]


def swap_to_main_weapons():
    count = int(TOUGH_POINTS / points_of(19, 101)) + 1  # a pack worth the swap
    pack = [foe(100 + index, 5004.0 + index % 8, 4996.0 + index // 8) for index in range(count)]
    play = game(*pack, slots=NO_MARK_SLOTS)
    for monster in pack:
        play.toughness[monster.unit_id] = 1000
    play.sets.reverse()  # the staff's set in hand, as after a hop
    attack_mode(play, hunter(play), until=4.0)
    return [play]


def click_during_fight():
    play = game(foe(10, 5008.0, 5000.0), slots=NO_MARK_SLOTS)
    play.toughness[10] = 1000
    attack_mode(play, hunter(play), until=3.0, events=[left_click(play, 1.0)])
    return [play]


def one_elite_hopped_three_times():
    play = game(foe(10, 5080.0, 5000.0, CHAMPION))
    hunt = hunter(play)
    level = Level(101, ROOMS, ())
    for _ in range(3):  # three presses, a hop each; the source test counts the scans on the side
        run = play.run()
        pick_up(run, level, keys, lambda run=run: hunt.seek(run, keys))
    return [play]


def world_read_once_a_tick(place):
    play = game(foe(10, place, 5000.0), slots=NO_MARK_SLOTS)
    play.toughness[10] = 10**6
    attack_mode(play, hunter(play), until=3.0)
    return [play]


def left_button_looked_at(place):
    # The source test counts the looks of pointer_state on the side; the play is the same without the count.
    play = game(foe(10, place, 5000.0), slots=NO_MARK_SLOTS)
    play.toughness[10] = 10**6
    attack_mode(play, hunter(play), until=3.0)
    return [play]


SCENARIOS = {
    'test_a_monster_walking_into_reach_is_struck_within_three_ticks': walking_into_reach,
    'test_the_first_strike_does_not_wait_for_the_mark_or_the_sigil[a monster: Death Mark]': lambda: first_strike(0),
    'test_the_first_strike_does_not_wait_for_the_mark_or_the_sigil[an elite: the sigil and Death Mark]': lambda: first_strike(
        CHAMPION
    ),
    'test_with_nothing_else_to_cast_the_first_strike_is_held_within_three_ticks_of_the_mode_coming_on': nothing_else_to_cast,
    'test_the_lined_monster_dying_moves_the_pointer_to_the_next_line_within_a_tick': lined_monster_dies,
    'test_a_monster_out_of_reach_for_a_moment_does_not_end_the_hold': monster_out_of_reach_for_a_moment,
    'test_a_reachable_monster_is_struck_at_once_while_an_elite_stands_behind_a_wall': reachable_while_elite_behind_wall,
    'test_no_sigil_is_cast_under_an_elite_behind_a_wall_on_the_way_to_a_strike': no_sigil_behind_wall,
    'test_the_swap_to_the_main_weapons_keeps_the_strike_up_half_a_second_at_most': swap_to_main_weapons,
    'test_a_click_during_a_fight_lets_the_strike_go_within_a_tick': click_during_fight,
    'test_hunting_one_elite_does_not_scan_the_ground_again_on_every_hop': one_elite_hopped_three_times,
    'test_the_world_is_read_once_a_tick_at_most_idle_or_fighting[idle]': lambda: world_read_once_a_tick(5060.0),
    'test_the_world_is_read_once_a_tick_at_most_idle_or_fighting[fighting]': lambda: world_read_once_a_tick(5008.0),
    'test_the_left_button_is_looked_at_once_a_slice[idle]': lambda: left_button_looked_at(5060.0),
    'test_the_left_button_is_looked_at_once_a_slice[fighting]': lambda: left_button_looked_at(5008.0),
}


# --- the summary: fake-clock values only ---


def plain(value):
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def counts(plays) -> list[dict]:
    return [
        plain(
            {
                'struck_at': play.struck_at,
                'pressed_at': play.pressed_at,
                'released_at': play.released_at,
                'moved_at': play.moved_at,
                'reads': play.reads,
            }
        )
        for play in plays
    ]


def load() -> dict:
    return json.loads(GOLDEN.read_text(encoding='utf-8')) if GOLDEN.exists() else {}


def store(data: dict) -> None:
    GOLDEN.write_text(json.dumps(data, sort_keys=True, indent=1) + '\n', encoding='utf-8')


@pytest.mark.parametrize('name', list(SCENARIOS))
def test_a_loop_scenario_counts_as_recorded(name):
    summary = counts(SCENARIOS[name]())
    if REGEN:
        data = load()
        data[name] = summary
        store(data)
        return
    assert summary == load()[name]


def test_no_scenario_is_missing_or_stale():
    if REGEN:
        store({name: summary for name, summary in load().items() if name in SCENARIOS})
    assert sorted(load()) == sorted(SCENARIOS)
