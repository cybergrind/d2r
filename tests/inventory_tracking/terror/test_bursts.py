"""Burst events from the probe log: much life lost at once, with the packs that stood there."""

from inventory_tracking.terror.bursts import bursts


def life(t, value, most=1000, x=5000, y=5000):
    return {'event': 'life', 't': t, 'area': 7, 'life': value, 'max': most, 'x': x, 'y': y}


def archer(unit_id, x=5020, y=5000):
    stats = [[0, 350, 122], [0, 351, 9]]  # under Fanaticism
    seen = {'event': 'seen', 'unit_id': unit_id, 'txt_id': 160, 'mode': 1, 'area': 7, 'data_hex': '00' * 0x80}
    return seen | {'x': x + 2 * unit_id, 'y': y, 'stats': stats}


def test_a_third_of_the_life_lost_within_a_second_is_a_burst_with_the_packs_nearby():
    events = [*(archer(n) for n in range(8)), life(1.0, 1000), life(1.25, 900), life(1.75, 600), life(2.0, 590)]

    (burst,) = bursts(events)

    assert (burst.t, burst.lost, burst.died) == (1.75, 400, False)
    assert [(pack.label, pack.band) for pack in burst.packs] == [('Dark Ranger x8 · Fanaticism', 'deadly')]
    assert burst.line.endswith('-40%  Dark Ranger x8 · Fanaticism [deadly 12.6]')


def test_slow_losses_and_healing_are_no_burst_and_a_death_is_one():
    slow = [life(1.0, 1000), life(2.5, 800), life(4.0, 600), life(5.5, 400), life(6.0, 900)]
    assert bursts(slow) == []

    (death,) = bursts([life(1.0, 200), life(1.25, 0)])
    assert (death.died, death.packs) == (True, ())


def test_dead_and_far_monsters_are_not_part_of_the_burst():
    far = [archer(n, x=9000) for n in range(8)]
    killed = [{'event': 'died', 'unit_id': n, 'area': 7} for n in range(20, 28)]
    events = [*far, *(archer(n) for n in range(20, 28)), *killed, life(1.0, 1000), life(1.5, 500)]

    (burst,) = bursts(events)

    assert burst.packs == ()
