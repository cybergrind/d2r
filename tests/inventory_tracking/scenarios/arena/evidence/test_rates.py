"""rates.py on takes made by hand (synthetic.py): what a take is tallied into, and what tallies measure;
model.py's numbers against the model's own parameters; the split and the report end to end."""

import json
import math

import pytest

from inventory_tracking.combat.hurts import COLD
from inventory_tracking.combat.sim.monsters import REACH, STRIKE_FRAMES, Traits
from inventory_tracking.combat.timeline import GAME_RATE
from tests.inventory_tracking.scenarios.arena.evidence import blows, model, rates, report, scan
from tests.inventory_tracking.scenarios.arena.evidence.blows import (
    FRIEND,
    HERO,
    MONSTER_KIND,
    NONE,
    NOVA,
    SEVERAL,
    SOLE_MELEE,
    SOLE_RANGED,
    SWING,
)
from tests.inventory_tracking.scenarios.arena.evidence.synthetic import (
    DEAD,
    HERO_UNIT,
    MELEE_TXT,
    NOVA_MISSILE,
    RANGED_TXT,
    RATE,
    STRIKE,
    aims,
    at_hero,
    born,
    flying,
    frame,
    monster,
    take,
    write,
)


def tallied(found, mods=None):
    """(rows, tally) of a take, as scan.read makes them."""
    moments = list(blows.walk(found))
    rows = blows.blows(found, mods, moments)
    return rows, rates.tally(found.directory.name, moments, rows, blows.Roster(found, mods))


def melee_take(name='20261011T120000Z-25', hit=True):
    """A monster two units off that swings through frames 3 to 6 at the character and takes 100 points
    at frame 5 (`hit`), then stands; ten frames."""
    frames = []
    for index in range(10):
        foe = monster(7, mode=STRIKE if 3 <= index <= 6 else 1)
        frames.append(frame(index, 900 if hit and index >= 5 else 1000, [foe]))
    return take(frames, paths=[at_hero(0, 7)], name=name)


def test_time_near_is_binned_by_distance():
    rows, found = tallied(melee_take())
    bins = found['near'][f'{MELEE_TXT}|plain']
    assert bins[int(2.0 / rates.BIN)] == pytest.approx(9 / RATE)  # the last frame stands for no time
    assert sum(bins) == pytest.approx(9 / RATE)
    assert found['seconds'] == pytest.approx(9 / RATE)
    assert rates.within(bins, 3.5) == pytest.approx(9 / RATE)
    assert rates.within(bins, 2.0) == 0.0
    assert found['sight'] == {}  # no shooter in the take
    assert found['paths'] == 1
    assert len(rows) == 1


def test_a_run_in_an_attack_mode_is_one_swing_with_its_drop():
    _rows, found = tallied(melee_take())
    (swing,) = found['swings']
    assert (swing['txt'], swing['mode'], swing['frames'], swing['away'], swing['aim']) == (
        MELEE_TXT,
        STRIKE,
        4,
        2.0,
        HERO,
    )
    assert (swing['alone'], swing['any_n'], swing['sole_n'], swing['sole_points'], swing['shared_n']) == (
        1,
        1,
        1,
        100,
        0,
    )
    assert (swing['fired'], swing['moved'], swing['jumped']) == (0, 0.0, 0)
    _rows, missed = tallied(melee_take(hit=False))
    assert missed['swings'][0]['sole_n'] == 0


def test_a_swing_among_others_is_not_alone_and_shares_its_drop():
    frames = []
    for index in range(8):
        foes = [
            monster(7, mode=STRIKE if 2 <= index <= 5 else 1),
            monster(9, at=(100.0, 103.0), mode=STRIKE if 2 <= index <= 5 else 1),
        ]
        frames.append(frame(index, 900 if index >= 4 else 1000, foes))
    rows, found = tallied(take(frames))
    assert rows[0]['class'] == SEVERAL
    assert [(s['alone'], s['sole_n'], s['shared_n'], s['shared_points'], s['aim']) for s in found['swings']] == [
        (0, 0, 1, 50.0, None)
    ] * 2


def shot_take(target=(100.0, 100.0), hero_path=None, hit=True, name='20261011T121000Z-25'):
    """An archer 12 units off in an attack mode through frames 1 to 4; its missile appears at frame 2
    and flies three units a frame toward `target`, last seen one unit short of it at frame 5; the
    character (at `hero_path(index)`, default standing at 100, 100) loses 60 points at frame 6."""
    frames = []
    for index in range(9):
        archer = monster(8, RANGED_TXT, at=(112.0, 100.0), mode=STRIKE if 1 <= index <= 4 else 1)
        pet = monster(30, at=(100.0, 110.0), owner=HERO_UNIT)
        flights = []
        if 2 <= index <= 5:
            done = (index - 2) / 3 * (11 / 12)
            arrow = (112.0 + (target[0] - 112.0) * done, 100.0 + (target[1] - 100.0) * done)
            flights.append(flying(50, NOVA_MISSILE, (round(arrow[0]), round(arrow[1]))))
        here = hero_path(index) if hero_path else (100.0, 100.0)
        frames.append(frame(index, 940 if hit and index >= 6 else 1000, [archer, pet], flights, at=here))
    return take(frames, missiles=[born(2, 50, NOVA_MISSILE, 8)], name=name)


def test_a_shot_that_ends_on_the_character_and_takes_life():
    rows, found = tallied(shot_take())
    assert [row['class'] for row in rows] == [SOLE_RANGED]
    (shot,) = found['swings']
    assert (shot['txt'], shot['fired'], shot['at_hero'], shot['on_hero'], shot['on_friend']) == (RANGED_TXT, 1, 1, 1, 0)
    assert (shot['arrived'], shot['hit_sole'], shot['hit_any'], shot['hit_points']) == (1, 1, 1, 60)
    assert (shot['away'], shot['moved'], shot['jumped']) == (12.0, 0.0, 0)
    assert sum(found['sight'][f'{RANGED_TXT}|plain']) == pytest.approx(8 / RATE)  # no level file: every second
    assert found['owners'] == {'foe': 1}
    assert found['sighted'] == 0


def test_a_shot_at_a_companion_ends_on_it():
    rows, found = tallied(shot_take(target=(100.0, 110.0), hit=False))
    (shot,) = found['swings']
    assert rows == []
    assert (shot['fired'], shot['at_hero'], shot['on_hero'], shot['on_friend'], shot['hit_any']) == (1, 0, 0, 1, 0)


def test_a_shot_walked_out_of_or_teleported_out_of():
    walked = shot_take(hero_path=lambda index: (100.0, 100.0 + 1.5 * max(index - 1, 0)), hit=False)
    (shot,) = tallied(walked)[1]['swings']
    assert (shot['at_hero'], shot['on_hero'], shot['jumped'], rates.motion_of(shot)) == (1, 0, 0, 'moved')
    hopped = shot_take(hero_path=lambda index: (100.0, 100.0) if index < 4 else (100.0, 130.0), hit=False)
    (shot,) = tallied(hopped)[1]['swings']
    assert (shot['at_hero'], shot['on_hero'], shot['jumped'], rates.motion_of(shot)) == (1, 0, 1, 'jumped')
    (shot,) = tallied(shot_take())[1]['swings']
    assert rates.motion_of(shot) == 'stood'


def test_targets_are_tallied_by_who_is_nearer():
    pet = monster(30, at=(110.0, 100.0), owner=HERO_UNIT)
    foes = [monster(7, at=(103.0, 100.0)), monster(9, at=(108.0, 100.0)), monster(11, at=(100.0, 150.0))]
    frames = [frame(index, 1000, [pet, *foes]) for index in range(6)]
    paths = [aims(0, (7, MONSTER_KIND, 30)), at_hero(0, 9, 11)]
    _rows, found = tallied(take(frames, paths=paths))
    cells = found['targets'][f'{MELEE_TXT}|plain']
    assert cells == {
        f'{HERO}>{FRIEND}': pytest.approx(0.2),
        f'{FRIEND}>{HERO}': pytest.approx(0.2),
    }  # 11 is beyond AWARE
    assert found['target_units'][f'{MELEE_TXT}|plain'] == {f'{HERO}>{FRIEND}': 1, f'{FRIEND}>{HERO}': 1}
    measured = rates.targets([found])
    assert measured['pooled'][HERO]['hero_share'] == 0.0
    assert measured['pooled'][FRIEND]['hero_share'] == 1.0
    assert measured['types'][str(MELEE_TXT)][FRIEND]['units'][HERO] == 1


def nova_take(name='20261011T120500Z-25'):
    """An elite dies six units off at frame 2; its nova's missile is near the character at frame 3 and
    180 points are gone at frame 4."""
    alive, corpse = monster(9, at=(106.0, 100.0), flags=8), monster(9, at=(106.0, 100.0), mode=DEAD, flags=8)
    frames = [
        frame(0, 1000, [alive]),
        frame(1, 1000, [alive]),
        frame(2, 1000, [corpse]),
        frame(3, 1000, [corpse], [flying(50, NOVA_MISSILE, (102.0, 100.0))]),
        frame(4, 820, [corpse]),
        frame(5, 820, [corpse]),
    ]
    return take(frames, missiles=[born(3, 50, NOVA_MISSILE, 9)], name=name)


def test_a_death_is_tallied_with_what_followed_it():
    rows, found = tallied(nova_take(), {9: [COLD]})
    assert [row['class'] for row in rows] == [NOVA]
    (death,) = found['deaths']
    assert (death['txt'], death['rank'], death['mods'], death['away']) == (MELEE_TXT, blows.UNIQUE, [COLD], 6.0)
    assert (death['after_n'], death['after_points'], death['before_n'], death['nova_points']) == (1, 180, 0, 180)
    assert death['missiles'] == [NOVA_MISSILE]
    measured = rates.novas(rows, [found])
    assert measured['deaths']['cold|elite|4-8']['nova_n'] == 1
    assert measured['deaths']['cold|elite|4-8']['with_missile'] == 1
    assert measured['drops'][f'{NOVA_MISSILE}|cold']['drop']['p50'] == 180
    assert rates.enchantment(None) == 'not known'
    assert rates.enchantment([5]) == 'none'


def test_quantiles_and_ratios():
    assert rates.quantile([], 0.5) is None
    assert rates.quantile([5, 1, 3], 0.5) == 3
    assert rates.quantile(list(range(1, 101)), 0.9) == 90
    assert rates.spread([4, 2])['max'] == 4
    assert rates.ratio(1, 0) is None
    assert rates.ratio(1, 4) == 0.25


def swing(frames=20, **fields):
    found = {
        'txt': MELEE_TXT, 'rank': 'plain', 'mode': STRIKE, 'frames': frames, 'away': 2.0, 'aim': HERO, 'alone': 0,
        'clear': None, 'any_n': 0, 'sole_n': 0, 'sole_points': 0, 'shared_n': 0, 'shared_points': 0.0, 'fired': 0,
        'at_hero': 0, 'on_hero': 0, 'on_friend': 0, 'arrived': 0, 'hit_any': 0, 'hit_sole': 0, 'hit_points': 0,
        'moved': 0.0, 'jumped': 0, 'level': 80, 'tier': 0,
    }  # fmt: skip
    return {**found, **fields}


def test_a_run_is_as_many_swings_as_its_length_says():
    swings = [swing() for _ in range(12)] + [swing(40), swing(4), swing(7)]
    usual = rates.usual_frames(swings)
    assert usual == {(MELEE_TXT, STRIKE): 20}
    assert [rates.swing_count(s, usual) for s in swings[-3:]] == [2, 1, 1]
    assert rates.usual_frames([swing() for _ in range(9)]) == {}  # under ten runs: no usual length
    assert rates.swing_count(swing(40), {}) == 1


def test_swing_stats_count_whole_swings_at_the_character():
    swings = (
        [swing(sole_n=1, any_n=1, alone=1)] * 2
        + [swing(shared_n=1, any_n=1)] * 2
        + [swing()] * 6
        + [swing(4)] * 2  # cut short
        + [swing(aim=FRIEND)] * 3
        + [swing(aim=None)]
        + [swing(sole_n=1, any_n=1, jumped=1)]
    )
    found = rates.swing_stats(swings, rates.usual_frames(swings))
    assert (found['runs'], found['swings'], found['cut_short'], found['aim_known'], found['aimed']) == (
        17,
        17,
        2,
        16,
        13,
    )
    assert found['whole_aimed'] == 11
    assert (found['hits_sole'], found['hits_shared']) == (3, 2)
    assert (found['hit_low'], found['hit_high']) == (round(3 / 11, 3), round(5 / 11, 3))
    assert (found['alone'], found['alone_hit']) == (2, 1.0)
    assert (found['stood'], found['stood_hit_low'], found['left']) == (10, 0.2, 1)


def test_shot_stats():
    shots = [swing(fired=1, at_hero=1, on_hero=1, hit_sole=1, hit_any=1)] + [swing(fired=1, at_hero=1, on_hero=1)] * 3
    shots += [swing(fired=1, at_hero=1, on_friend=1)] * 2 + [swing(fired=1)] * 4
    found = rates.shot_stats(shots)
    assert (found['shots'], found['at_hero'], found['on_hero'], found['on_friend']) == (10, 6, 4, 2)
    assert (found['took_low'], found['took_high'], found['hit_per_shot_low']) == (0.25, 0.25, 0.1)
    assert found['at_hero_on_hero_share'] == round(4 / 6, 3)


def test_the_classes_of_a_set_of_rows():
    rows, _found = tallied(melee_take())
    more, _found = tallied(nova_take(), {9: [COLD]})
    ticks = [
        {'take': 'a', 't': 0.4 * index, 'lost': 10, 'class': NONE, 'by': [], 'missiles': [], 'gap': 0.04, 'share': 0.01,
         'foes_near': 0, 'nearest_striking': None, 'hero_mode': 1, 'dead': False}
        for index in range(3)
    ]  # fmt: skip
    found = rates.classes([*rows, *more, *ticks])
    assert (found['n'], found['points']) == (5, 310)
    assert (found[SOLE_MELEE]['n'], found[NOVA]['points'], found[NONE]['n']) == (1, 180, 3)
    assert found[SOLE_MELEE]['points_share'] == round(100 / 310, 3)
    assert found['parts']['unknown, one of a run of drops 0.3 to 0.5 s apart (damage over time)']['n'] == 3
    assert found['parts']['unknown, nothing hostile within 8 units']['n'] == 3
    assert found['unknown_sizes']['10 to 19']['n'] == 3
    assert rates.composition({'by': [{'via': SWING, 'txt': 1}, {'via': SWING, 'txt': 1}]}) == 'swings of one type'
    assert rates.composition({'by': [{'via': SWING, 'txt': 1}, {'via': 'missile', 'txt': 2}]}) == 'swings and missiles'


def test_measure_puts_it_together_and_counts_the_tail_by_the_reach_given():
    takes = [melee_take(f'2026101{day}T120000Z-25') for day in range(1, 4)]
    parts = [tallied(found) for found in takes]
    rows, tallies = [row for part in parts for row in part[0]], [part[1] for part in parts]
    found = rates.measure(rows, tallies)
    assert (found['takes'], found['classes']['n'], found['takes_with_paths']) == (3, 3, 3)
    assert found['reach']['pooled']['blows'] == {'n': 3, 'p50': 2.0, 'p90': 2.0, 'p99': 2.0, 'max': 2.0}
    entry = found['melee'][str(MELEE_TXT)]
    assert entry['seconds'] == pytest.approx(27 / RATE, abs=0.05)
    assert (entry['swings'], entry['whole_aimed'], entry['hits_sole'], entry['hit_low'], entry['alone_hit']) == (
        3,
        3,
        3,
        1.0,
        1.0,
    )
    assert (entry['blows'], entry['points_sole'], entry['reach'], entry['reach_from']) == (
        3,
        300,
        rates.MODEL_REACH,
        'pooled',
    )
    assert found['melee']['all']['swings'] == 3
    assert found['melee_by_rank'][f'{MELEE_TXT}|plain']['blows'] == 3
    assert found['coverage'][0]['txt'] == MELEE_TXT
    band = next(band for band in found['reach_curve'] if band['from'] == 2.0)
    assert (band['swings'], band['hit_low']) == (3, 1.0)
    wider = rates.measure(rows, tallies, {'pooled': {'blows': {'p90': 9.0}}, 'types': {}})
    assert wider['melee'][str(MELEE_TXT)]['reach'] == 9.0
    assert wider['reach'] == found['reach']  # its own reach is reported either way


def test_a_type_that_stands_and_never_swings_is_left_out_of_the_pool():
    frames = [frame(index, 1000, [monster(7)]) for index in range(int(40 * RATE))]
    _rows, found = tallied(take(frames))
    assert rates.idle_types([found]) == {MELEE_TXT}
    assert rates.measure([], [found])['melee']['all']['left_out'] == [MELEE_TXT]
    assert rates.idle_types([tallied(melee_take())[1]]) == set()


def test_the_models_numbers_are_read_off_its_parameters():
    traits = Traits.of(MELEE_TXT)
    chance = min(traits.strikes, 100) / 100
    expected = GAME_RATE / (STRIKE_FRAMES + (1 - chance) / chance * max(traits.idles, 1))
    assert model.swings_per_second(traits) == pytest.approx(expected)
    found = model.blow(MELEE_TXT, None)
    assert found['most'] >= found['mean'] > 0
    assert found['points_per_second'] == pytest.approx(expected * found['mean'], rel=0.01)
    unique = model.blow(MELEE_TXT, None, model.flags_of(blows.UNIQUE), (COLD,))
    assert unique['most_raw'] > found['most_raw']
    assert unique['most'] < unique['most_raw']  # the main set stops three quarters of the cold part
    shot = model.shot(RANGED_TXT, None)
    assert shot['ranged'] is True
    assert shot['shots_per_second'] == model.CONSTANTS['shots_per_second']
    suspect = {'txt': MELEE_TXT, 'level': 0, 'flags': 0, 'mods': None, 'tier': 0}
    assert model.most(suspect) == found['most']
    # The bin that holds the model's reach ends at rates.MODEL_REACH.
    assert math.ceil(REACH / rates.BIN) * rates.BIN == rates.MODEL_REACH


def test_the_split_is_by_name_and_about_even():
    names = [f'20261011T{hour:02d}{minute:02d}00Z-25' for hour in range(24) for minute in range(0, 60, 5)]
    halves = [scan.half(name) for name in names]
    assert halves == [scan.half(name) for name in names]
    assert 0.4 < halves.count(scan.TRAIN) / len(names) < 0.6
    assert set(halves) == {scan.TRAIN, scan.CHECK}


def test_the_report_from_takes_on_disk(tmp_path, monkeypatch, capsys):
    root, out, cache = tmp_path / 'takes', tmp_path / 'out', tmp_path / 'cache'
    names = [f'2026101{day}T12{minute:02d}00Z-25' for day in (0, 1) for minute in range(8)]
    for index, name in enumerate(names):
        write(melee_take(name) if index % 2 else shot_take(name=name), root)
    write(take([frame(0, 1000)], name='20261009T120000Z-25', schema=1), root)
    monkeypatch.setattr(scan, 'PROBES', tmp_path / 'no-logs')
    assert [path.name for path in scan.takes_under(root, since='20261011')] == names[8:]
    assert len(scan.takes_under(root, limit=3)) == 3
    assert report.main(['--root', str(root), '--out', str(out), '--cache', str(cache), '--jobs', '1']) == 0
    split = json.loads((out / 'split.json').read_text())
    assert sorted(split[scan.TRAIN] + split[scan.CHECK]) == names
    assert split['left_out'] == {'20261009T120000Z-25': 'schema 1: no vitals'}
    assert all(scan.half(name) == scan.TRAIN for name in split[scan.TRAIN])
    evidence = json.loads((out / 'evidence.json').read_text())
    assert evidence['counts']['read'] == 16
    assert evidence[scan.TRAIN]['takes'] + evidence[scan.CHECK]['takes'] == 16
    assert evidence['all']['classes']['n'] == 16
    assert set(evidence['types']) == {str(MELEE_TXT), str(RANGED_TXT)}
    assert evidence['types'][str(MELEE_TXT)]['model']['blow']['swings_per_second'] > 0
    text = (out / 'EVIDENCE.md').read_text()
    for heading in ('## 2. Who took the life', '## 5. Melee', '## 6. Ranged', '## 7. Target choice', '## 8. Big blows',
                    '## 9. Death novas', '## 10. What the refit should change'):  # fmt: skip
        assert heading in text
    assert len(list(cache.glob('2026*.json'))) == 17
    assert len((cache / 'blows.jsonl').read_text().splitlines()) == 16
    first = (out / 'EVIDENCE.md').read_bytes(), (out / 'evidence.json').read_bytes()
    assert report.main(['--root', str(root), '--out', str(out), '--cache', str(cache), '--jobs', '1']) == 0  # cached
    assert first == ((out / 'EVIDENCE.md').read_bytes(), (out / 'evidence.json').read_bytes())
    assert 'takes read' in capsys.readouterr().err
