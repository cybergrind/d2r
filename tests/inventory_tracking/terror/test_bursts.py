"""Burst events from the probe log: much life lost at once, with the packs that stood there."""

import json

from inventory_tracking.terror.bursts import bursts, log_paths, main, read


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


def test_monsters_are_taken_where_the_log_last_put_them_and_another_game_starts_empty():
    moved = [{'event': 'back', 'unit_id': n, 'x': 5020 + 2 * n, 'y': 5000} for n in range(8)]
    events = [*(archer(n, x=9000) for n in range(8)), *moved, life(1.0, 1000), life(1.5, 500)]
    assert [pack.count for pack in bursts(events)[0].packs] == [8]

    left = [*(archer(n) for n in range(8)), {'event': 'left_game', 't': 0.5}, life(1.0, 1000), life(1.5, 500)]
    assert bursts(left)[0].packs == ()


def test_the_script_lists_the_bursts_of_each_log_and_skips_a_line_cut_off(tmp_path, capsys):
    log = tmp_path / 'terror-probe.jsonl'
    events = [*(archer(n) for n in range(8)), life(1.0, 1000), life(1.5, 500)]
    log.write_text('\n'.join(json.dumps(event) for event in events) + '\n{"event": "li')

    assert len(list(read(log))) == 10
    assert main([str(log)]) == 0
    out = capsys.readouterr().out
    assert 'Dark Ranger x8 · Fanaticism [deadly 12.6]' in out
    assert out.endswith('1 burst event in 1 log\n')


def test_a_pattern_the_shell_left_alone_names_every_log_it_matches(tmp_path):
    logs = [tmp_path / run / 'terror-probe.jsonl' for run in ('a', 'b')]
    for log in logs:
        log.parent.mkdir()
        log.write_text('')

    assert log_paths([tmp_path / '*' / 'terror-probe.jsonl', logs[0]]) == [*logs, logs[0]]
    assert log_paths([tmp_path / 'none' / '*.jsonl']) == []
