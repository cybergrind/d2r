"""The zone graph (routes/zone_graph.py; macros/zone-nav-plan.md §2): the acts' trees from their itineraries, the ways
in and back up and where their marks come from."""

import pytest

from inventory_tracking.macros.tzroutine import itinerary
from inventory_tracking.macros.zonenav import graph_of
from inventory_tracking.routes.tz_groups import manual_zone
from inventory_tracking.routes.zone_graph import (
    CATALOGUE,
    GENERIC,
    HANDLER,
    PORTAL,
    WALK,
    WARP,
    Chain,
    Way,
    way,
    zone_graph,
)


def act_graph(act: int):
    zone = manual_zone(act)
    assert zone is not None
    plan = itinerary(zone.core)
    assert plan is not None
    return graph_of(plan)


def test_act_3_is_eight_roots_with_their_dungeons_temples_and_the_causeway_under_upper_kurast():
    graph = act_graph(3)
    assert graph.said() == (
        '101 (102); 83 (100); 81 (82 (98, 99), 96, 97); 80 (92 (93), 94, 95); 79; 78 (88 (89 (91)), 86 (87 (90))); 77; '
        '76 (84, 85)'
    )
    assert graph.roots == (101, 83, 81, 80, 79, 78, 77, 76)
    assert graph.nodes[98].root == 81
    assert graph.ancestors(98) == (82, 81)
    assert graph.depth(81) == 3
    assert graph.depth(96) == 1
    assert graph.depth(88) == 3
    assert graph.subtree(80) == (80, 92, 93, 94, 95)


def test_act_3s_ways_in_and_back_up_name_the_marks_the_cards_show():
    graph = act_graph(3)
    temple = graph.nodes[96]
    assert temple.entry == Way(96, 'Forgotten Reliquary', WARP, CATALOGUE)
    # no handler in the temple: the generic way out levels/exits.py names after the level it leads into (the Ruined
    # Temple's card, 09:13:43 on 2026-10-21: "Kurast Bazaar: here")
    assert temple.back == Way(81, 'Upper Kurast', WARP, GENERIC)
    causeway = graph.nodes[82]
    assert causeway.entry == Way(82, 'Kurast Causeway', WALK, CATALOGUE)
    assert causeway.back == Way(81, 'Upper Kurast', WALK, GENERIC)
    assert graph.nodes[92].back == Way(80, 'Way up', WARP, HANDLER)  # Sewers 1's ladders up
    assert graph.nodes[88].back == Way(78, 'Flayer Jungle', WARP, HANDLER)
    assert graph.nodes[102].entry == Way(102, 'Next level', WARP, CATALOGUE)


def test_the_unconfirmed_ways_are_the_generic_marks_and_the_missing_ways_back():
    graph = act_graph(3)
    found = graph.unconfirmed()
    assert "96->81 'Upper Kurast'" in found
    assert "102->101 'Durance of Hate 2'" in found
    assert not any(line.startswith('92->') for line in found)  # the handler's 'Way up'


def test_act_4_crosses_the_river_to_the_chaos_sanctuary_its_boss():
    graph = act_graph(4)
    assert graph.roots[0] == 107
    assert graph.nodes[107].crossed
    assert graph.nodes[108].boss
    assert graph.nodes[108].entry is not None
    assert graph.nodes[108].entry.kind == WALK


def test_the_canyons_tombs_are_its_children_each_left_by_its_way_back():
    graph = act_graph(2)
    canyon = graph.nodes[46]
    # and Duriel's Lair, the tour's side level under the hub, entered by a tomb's Orifice (levels/handlers/tal_rasha.py
    # DURIEL, on since 2026-10-21)
    assert canyon.children == (66, 67, 68, 69, 70, 71, 72, 73)
    lair = graph.nodes[73]
    assert (lair.parent, lair.side, lair.sources, lair.back) == (46, True, (66, 67, 68, 69, 70, 71, 72), None)
    tomb = graph.nodes[68]
    assert tomb.parent == 46
    assert tomb.entry == Way(68, 'Tomb', WARP, CATALOGUE)
    assert tomb.back == Way(46, 'Canyon of the Magi', WARP, CATALOGUE)


def test_a_level_two_trips_name_keeps_the_first_trips_parent_and_a_portal_level_has_no_way_back():
    graph = zone_graph('test', (Chain(52, (52, 53, 54, 74)), Chain(74, (74,)), Chain(48, (48, 49))))
    assert graph.roots == (52, 48)  # 74 is already under 54
    sanctuary = graph.nodes[74]
    assert sanctuary.parent == 54
    assert sanctuary.entry is not None
    assert sanctuary.entry.kind == PORTAL
    assert sanctuary.back is None
    assert '74->54 none' in graph.unconfirmed()


@pytest.mark.parametrize(('area', 'to', 'mark'), [(81, 96, 'Forgotten Reliquary'), (78, 88, 'Flayer Dungeon 1')])
def test_a_way_in_named_by_the_catalogue(area, to, mark):
    assert way(area, to).mark == mark
    assert way(area, to).source == CATALOGUE
