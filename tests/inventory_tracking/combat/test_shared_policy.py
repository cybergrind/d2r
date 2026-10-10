"""The decision the simulator and the game share (combat/policy.py): observations, the line sweep,
the hunt's nearest-monster rule, the walls and the link."""

import math

from inventory_tracking.combat.mechanics.damage import link_table
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.combat.policy import (
    AIM_BEYOND,
    Foe,
    LinePolicy,
    NearestPolicy,
    Observation,
    clear_line,
    linked_set,
    observe,
    walls,
)
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.world import Monster, Player


HERE = (5000.0, 5000.0)


def flat(txt):
    return 1000.0


def seen(*foes, **changes):
    return Observation(HERE, {unit: Foe(310, at, 100_000.0, elite) for unit, at, elite in foes}, **changes)


def test_the_line_sweep_lays_its_line_through_the_most_monsters_and_names_the_one_it_went_through():
    choice = LinePolicy(damage_of=flat)(
        seen((1, (5012.0, 5000.0), False), (2, (5000.0, 5008.0), False), (3, (5000.0, 5016.0), False))
    )
    assert choice is not None
    assert choice.unit in (2, 3)
    assert abs(choice.focal[0] - 5000.0) < 1e-6
    assert choice.worth > 2000.0


def test_a_lone_monster_is_aimed_at_where_it_stands():
    # Every offset hits a lone monster the same: the tie goes to the focal point on it.
    choice = LinePolicy(damage_of=flat)(seen((1, (5008.0, 5000.0), False)))
    assert choice is not None
    assert choice.unit == 1
    assert math.dist(choice.focal, (5008.0, 5000.0)) < 1e-6


def test_the_line_sweep_yields_while_the_player_is_moving_unless_told_not_to():
    moving = seen((1, (5008.0, 5000.0), False), moving=True)
    assert LinePolicy(damage_of=flat)(moving) is None
    assert LinePolicy(yields=False, damage_of=flat)(moving) is not None


def test_nothing_within_the_blades_reach_is_no_cast():
    assert LinePolicy(damage_of=flat)(seen((1, (5030.0, 5000.0), False))) is None
    assert LinePolicy(damage_of=flat)(seen()) is None


def test_the_hunts_rule_takes_the_elite_first_then_the_nearest_one_unit_past_it():
    rule = NearestPolicy(damage_of=flat)
    choice = rule(seen((1, (5006.0, 5000.0), False), (2, (5000.0, 5012.0), True)))
    assert choice is not None
    assert choice.unit == 2
    assert math.dist(choice.focal, (5000.0, 5012.0 + AIM_BEYOND)) < 1e-6
    assert rule(seen((1, (5006.0, 5000.0), False), (3, (5000.0, 5012.0), False))).unit == 1
    assert rule(seen((1, (5021.0, 5000.0), False))) is None  # past the hunt's reach
    assert rule(seen((1, (5006.0, 5000.0), False), moving=True)) is not None  # the rule of 2026-10-09 never yielded


def test_the_hunts_rule_skips_a_monster_behind_a_wall():
    wall = lambda point: 5004.0 <= point[0] <= 5005.0  # noqa: E731
    rule = NearestPolicy(damage_of=flat)
    assert rule(seen((1, (5010.0, 5000.0), False), blocked=wall)) is None
    assert rule(seen((1, (5010.0, 5000.0), False), (2, (5000.0, 5015.0), False), blocked=wall)).unit == 2
    assert clear_line(wall, HERE, (5002.0, 5000.0))  # too short to look at
    assert not clear_line(wall, HERE, (5010.0, 5000.0))
    assert clear_line(None, HERE, (5010.0, 5000.0))


def test_the_line_sweep_finds_no_line_through_a_wall():
    wall = lambda point: 5004.0 <= point[0] <= 5005.0  # noqa: E731
    assert LinePolicy(damage_of=flat)(seen((1, (5010.0, 5000.0), False), blocked=wall)) is None


def test_walls_are_the_flight_layer_unread_cells_and_closed_doors():
    assert walls(None) is None
    assert walls(Ground(())) is None
    cells = pack_cells('1' * 200)
    flight = pack_cells('1' * 100 + '0' * 100)  # the lower half of the room stops a missile
    blocked = walls(Ground((Walkable(1000, 1000, 1, 8, cells, flight),)))
    assert blocked is not None
    assert not blocked((5001.0, 5001.0))
    assert blocked((5001.0, 5030.0))  # the flight layer
    assert blocked((4990.0, 5001.0))  # no grid there: a room not read
    door = walls(None, (Door(9, 15, 0, 5005.0, 5000.0),))
    assert door is not None
    assert door((5005.0, 5000.0))
    assert not door((5020.0, 5000.0))
    assert walls(None, (Door(9, 15, 2, 5005.0, 5000.0),)) is None  # open


def test_the_link_holds_the_monsters_nearest_a_defiler_within_its_range():
    foes = {1: (5005.0, 5000.0), 2: (5010.0, 5000.0), 3: (5020.0, 5000.0), 4: (5100.0, 5000.0)}
    assert linked_set([(5000.0, 5000.0)], foes, 25.0, 2) == {1, 2}
    assert linked_set([(5000.0, 5000.0)], foes, 25.0, 5) == {1, 2, 3}
    assert linked_set([], foes, 25.0, 5) == frozenset()


def test_the_games_records_become_an_observation():
    player = Player(1, 'CybergrindAA', 1, 108, 5000.0, 5000.0, None)
    fresh = Monster(10, 310, 1, 5008.0, 5000.0, 0xFFFFFFFF)  # the stats unread: taken as full
    hurt = Monster(11, 310, 1, 5000.0, 5010.0, 0xFFFFFFFF, 0x08, life=32, max_life=128)
    defiler = Monster(20, 744, 1, 5002.0, 5002.0, 1, ally=True)
    found = observe(player, [fresh, hurt], [defiler], moving=True)
    full = points_of(310, 108)
    assert found.origin == (5000.0, 5000.0)
    assert found.foes[10] == Foe(310, (5008.0, 5000.0), full)
    assert found.foes[11] == Foe(310, (5000.0, 5010.0), full / 4, True)
    assert found.linked == {10, 11}
    assert found.share == link_table()[2]
    assert found.moving
    assert found.blocked is None
    assert observe(player, [fresh], []).linked == frozenset()  # no Defiler, no link
