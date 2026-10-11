"""The reading of the service logs' teleport lines (evidence.py), on lines copied from a probe.log."""

import pytest

from inventory_tracking.macros.view import Viewport
from tests.inventory_tracking.scenarios.navigation.evidence import free_hops, hops_of, journeys_of, reach_along


RECT = '(1920, 0, 2560, 1418)'
# The run of 21:35 on 2026-10-10 (alt-d/20261010T182945Z-ae2caac8): two hops toward the stairs of
# Catacombs 2, a seek step's hop with the player's hand on the mouse, and a hop that moved nobody
# (the last line is made up from the format of the others).
# fmt: off
LOG = f"""\
2026-10-10 21:35:17,262 INFO Macro: Teleport toward Next level: 357 left after this, 69 charges
2026-10-10 21:35:17,463 INFO Macro: door Next level marked at (22897.5, 6702.5), entry (22895.5, 6706.5); this hop aims 357.2 from the mark
2026-10-10 21:35:17,711 INFO Macro: teleport aimed at (22540.5, 6689.4), 23.9 from (22531.5, 6711.5), 25.7 off the way, footing True, 14 grids, pointer (4376, 456) in {RECT}; landed at (22540.5, 6689.5), off by 0.1 (-0.0, +0.1)
2026-10-10 21:35:17,856 INFO Macro: Teleport toward Next level: 352 left after this, 68 charges
2026-10-10 21:35:18,040 INFO Macro: door Next level marked at (22897.5, 6702.5), entry (22895.5, 6706.5); this hop aims 351.9 from the mark
2026-10-10 21:35:18,262 INFO Macro: teleport aimed at (22547.4, 6667.3), 23.3 from (22540.5, 6689.5), 16.8 off the way, footing True, 14 grids, pointer (4303, 414) in {RECT}; landed at (22547.5, 6667.5), off by 0.2 (+0.1, +0.2)
2026-10-10 21:35:32,567 INFO Macro: hunting the elite 122 (3820978991) at (22710.5, 6590.5), 77 away from (22703.5, 6667.5), firing spot (22710.5, 6607.5) of 54
2026-10-10 21:35:32,724 INFO Macro: Teleport toward the elite 122 (3820978991): 31 left after this, 60 charges
2026-10-10 21:35:33,325 INFO Macro: teleport aimed at (22702.5, 6637.4), 30.1 from (22703.5, 6667.5), 30.5 off the way, footing True, 14 grids, pointer (1927, 911) in {RECT}; landed at (22694.5, 6687.5), off by 50.7 (-8.0, +50.1)
2026-10-10 21:35:38,700 INFO Macro: Teleport toward the elite 122 (3820978991): 7 left after this, 59 charges
2026-10-10 21:35:39,074 INFO Macro: teleport aimed at (22697.2, 6608.0), 24.9 from (22692.5, 6632.5), 21.3 off the way, footing True, 14 grids, pointer (4297, 323) in {RECT}; the character did not move: key t, slots 379, staff None
""".splitlines()  # noqa: E501
# fmt: on


def test_every_hop_line_is_read_with_the_mark_of_its_step():
    hops = hops_of(LOG, 'probe.log')
    assert [hop.label for hop in hops] == ['Next level'] * 2 + ['the elite 122 (3820978991)'] * 2
    first = hops[0]
    assert (first.stamp, first.aim, first.start) == ('2026-10-10 21:35:17.711', (22540.5, 6689.4), (22531.5, 6711.5))
    assert (first.gain, first.grids, first.landed) == (25.7, 14, (22540.5, 6689.5))
    assert first.mark == (22897.5, 6702.5)  # the door
    assert first.off == pytest.approx(0.1)
    assert (hops[2].mark, hops[2].quarry) == ((22710.5, 6607.5), (22710.5, 6590.5))  # the firing spot, the monster
    assert (hops[3].landed, hops[3].end) == (None, hops[3].start)


def test_the_pointer_away_from_the_aim_is_the_players_hand():
    hops = hops_of(LOG, 'probe.log')
    assert [hop.hand for hop in hops] == [False, False, True, False]


def test_a_journey_is_hops_toward_one_mark_each_from_where_the_last_landed():
    journeys = journeys_of(hops_of(LOG, 'probe.log'))
    assert [len(journey.hops) for journey in journeys] == [2, 1, 1]  # the hand's hop landed 50 units off: a new start
    door = journeys[0]
    assert (door.kind, door.start, door.end) == ('door', (22531.5, 6711.5), (22547.5, 6667.5))
    assert (door.ideal, door.over) == (2, 0)
    assert journeys[1].kind == 'hunt'
    assert journeys[1].causes() == {"the player's hand on the mouse": 1}
    assert journeys[2].causes() == {'the character did not move': 1}


def test_the_fewest_hops_with_no_walls_follow_the_windows_shape():
    host = Viewport(2560 / 1418)
    # Straight up the screen (both world axes falling) a hop covers 23.5 units of each axis, down 18.3.
    assert free_hops(host, (0.0, 0.0), (-33.0, -33.0)) == 2
    assert free_hops(host, (0.0, 0.0), (33.0, 33.0)) == 3
    assert free_hops(host, (0.0, 0.0), (0.2, 0.2)) == 0
    assert reach_along(host, (0.0, 0.0), (-1.0, -1.0)) == pytest.approx(0.444 * 75 / 2**0.5, abs=0.05)
    assert free_hops(Viewport(4 / 3), (0.0, 0.0), (40.0, -40.0)) > free_hops(host, (0.0, 0.0), (40.0, -40.0))
