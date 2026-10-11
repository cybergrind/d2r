"""A walking monster's route from its path record, and where it puts the monster a while later
(combat/mechanics/movement.py); the line sweep that leads with it (combat/policy.py `lead`)."""

import struct

import pytest

from inventory_tracking.combat.mechanics.movement import CURRENT, RUN, WALK, WAYPOINTS, Route, route_of, speed_of
from inventory_tracking.combat.policy import Foe, LinePolicy, Observation, virtual_cast
from inventory_tracking.combat.sim.situation import routes_of
from inventory_tracking.combat.takes import Take


DOOM_KNIGHT = 310  # monstats Velocity 6, Run 7


def record(waypoints, current=0):
    data = bytearray(0x240)
    struct.pack_into('<II', data, CURRENT, current, len(waypoints))
    for index, cell in enumerate(waypoints):
        struct.pack_into('<HH', data, WAYPOINTS + 4 * index, *cell)
    return bytes(data)


def test_a_route_is_the_waypoints_still_ahead_at_the_types_speed():
    route = route_of(record([(5000, 5000), (5010, 5000), (5010, 5020)], current=1), DOOM_KNIGHT, WALK)
    assert route == Route(((5010.5, 5000.5), (5010.5, 5020.5)), 6 / 25)
    assert route_of(record([(5010, 5000)]), DOOM_KNIGHT, RUN).speed == 7 / 25
    assert speed_of(DOOM_KNIGHT, WALK) == 6 / 25


@pytest.mark.parametrize(
    ('data', 'txt', 'mode'),
    [
        (record([(5010, 5000)]), DOOM_KNIGHT, 1),  # standing: the waypoints are of a walk it ended
        (record([]), DOOM_KNIGHT, WALK),  # nothing to walk to
        (record([(5010, 5000)], current=1), DOOM_KNIGHT, WALK),  # past its last waypoint
        (record([(5010, 5000)]), 99_999, WALK),  # a type without a monstats row: no speed
        (b'\0' * 8, DOOM_KNIGHT, WALK),  # only the position was read
    ],
)
def test_no_route_when_the_monster_is_not_walking_one(data, txt, mode):
    assert route_of(data, txt, mode) is None


def test_a_monster_follows_its_waypoints_and_stands_at_the_last():
    route = Route(((5004.0, 5000.0), (5004.0, 5003.0)), 0.5)
    assert route.after((5000.0, 5000.0), 4) == (5002.0, 5000.0)
    assert route.after((5000.0, 5000.0), 10) == (5004.0, 5001.0)  # round the corner
    assert route.after((5000.0, 5000.0), 100) == (5004.0, 5003.0)
    assert Foe(DOOM_KNIGHT, (5000.0, 5000.0), 1.0).ahead(10) == (5000.0, 5000.0)  # no route: where it stands


def test_a_led_cast_counts_the_monster_where_the_blades_meet_it():
    origin = (5000.0, 5000.0)
    # Walking across the line of fire, 12 units out: by the time a blade is that far it has gone 6 units.
    walker = Foe(DOOM_KNIGHT, (5000.0, 5012.0), 10_000.0, route=Route(((5040.0, 5012.0),), 0.4))
    at_it = virtual_cast(origin, (5000.0, 5012.0), {1: walker}, frozenset(), 0.0, lambda txt: 1000.0, lead=5)
    ahead = virtual_cast(origin, (5006.0, 5012.0), {1: walker}, frozenset(), 0.0, lambda txt: 1000.0, lead=5)
    assert ahead > at_it
    assert virtual_cast(origin, (5000.0, 5012.0), {1: walker}, frozenset(), 0.0, lambda txt: 1000.0) > 0  # unled


def test_the_line_sweep_leads_a_walking_monster_only_when_asked():
    walker = Foe(DOOM_KNIGHT, (5000.0, 5012.0), 10_000.0, route=Route(((5040.0, 5012.0),), 0.4))
    seen = Observation((5000.0, 5000.0), {1: walker})
    still = LinePolicy(damage_of=lambda txt: 1000.0)(seen)
    led = LinePolicy(damage_of=lambda txt: 1000.0, lead=5)(seen)
    assert still is not None
    assert led is not None
    assert still.focal[0] == 5000.0  # straight at where it stands
    assert led.focal[0] > 5003.0  # toward where its route takes it


def test_a_takes_path_records_become_routes_from_the_frame_they_were_written():
    def frame(n, mode, x):
        return {'n': n, 'm': [[7, DOOM_KNIGHT, mode, x, 5000.5, 128, 128, 0, 0xFFFFFFFF, 0]]}

    frames = [frame(1, 1, 5000.5), frame(2, WALK, 5000.7), frame(3, WALK, 5000.9), frame(4, 1, 5001.0)]
    paths = [{'t': 0.0, 'n': 2, 'm': [[7, record([(5010, 5000)]).hex()]]}]
    routes = routes_of(Take(None, {}, frames, paths=paths), frames)
    assert routes == {7: {2: Route(((5010.5, 5000.5),), 6 / 25), 3: Route(((5010.5, 5000.5),), 6 / 25)}}
    assert routes_of(Take(None, {}, frames), frames) == {}
