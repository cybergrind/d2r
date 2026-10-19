"""curses.py on takes made by hand (synthetic.py): what a take's resistance readings and cursers are
tallied into, what tallies measure, and the report from them."""

import json
from pathlib import Path
from typing import Any

import pytest

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.takes.hurts import ATTACK_MODES
from inventory_tracking.takes.record import RESIST_STATS
from inventory_tracking.takes.takes import Take
from tests.inventory_tracking.scenarios.arena.evidence import blows, curses
from tests.inventory_tracking.scenarios.arena.evidence.synthetic import IDLE, MELEE_TXT, RATE, START, frame, monster


KNIGHT = next(txt for txt, ai in sorted(curses.CURSERS.items()) if ai == 'OblivionKnight')
CURSER, OTHER, LEADER = 7, 8, 9
SET_A = [154, 108, 118, 124]  # the elemental four with one set of weapons
SET_B = [190, 179, 189, 195]  # with the other: not the same step for each of the four
FRAMES = 100
CAST = 30  # the frame the curser's cast begins at


def hurt(index, resists):
    """A `hurt` event at frame `index` as the recorder writes it, with the resistances read then."""
    return {'t': START + index / RATE, 'event': 'hurt', 'resists': [*resists], 'lost': 10, 'by': [], 'near': []}


def curse_take(readings, name='20261011T120000Z-25', away=6.0, casts=(CAST,), first=None, units=()):
    """The character standing still, a curser `away` units east of it that is in its casting mode for four
    frames from each of `casts`, a monster of another type beside the curser, and the `readings`
    (frame, resistances) as `hurt` events; `first`: the resistances the manifest holds."""
    frames = []
    for index in range(FRAMES):
        casting = any(start <= index < start + 4 for start in casts)
        foes = [
            monster(CURSER, KNIGHT, at=(100.0 + away, 100.0), mode=curses.CAST_MODE if casting else IDLE),
            monster(OTHER, MELEE_TXT, at=(100.0 + away, 102.0), mode=curses.CAST_MODE),
        ]
        frames.append(frame(index, 1000, foes))
    manifest: dict[str, Any] = {'schema': 2}
    if first is not None:
        manifest['character_stats'] = {str(stat): value for stat, value in zip(RESIST_STATS, first, strict=True)}
    events = [hurt(index, resists) for index, resists in readings]
    return Take(Path('/nowhere') / name, manifest, frames, events, [*units], [], [])


def tallied(found):
    return curses.tally(found.directory.name, list(blows.walk(found)), blows.Readings(found), blows.Roster(found))


def write(found, root):
    """The take as a directory under `root`, with its events (synthetic.write leaves them out)."""
    directory = root / found.directory.name
    directory.mkdir(parents=True)
    (directory / 'manifest.json').write_text(json.dumps(found.manifest))
    parts = {'frames': found.frames, 'events': found.events, 'units': found.units, 'missiles': [], 'paths': []}
    for part, records in parts.items():
        (directory / f'{part}.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records))
    return directory


def test_the_cursers_are_the_types_of_the_two_cursing_ais_by_the_bundled_tables():
    assert curses.CAST_MODE in ATTACK_MODES
    assert curses.CURSERS
    for txt, ai in curses.CURSERS.items():
        assert tables()['monsters'][str(txt)]['AI'] == ai
        assert ai in curses.SKILLS


def test_the_skills_named_are_what_the_games_monstats_gives_the_ais():
    """Against the game's own tables where a checkout holds them (third-parties is not in the repo)."""
    if not curses.DUMP.exists():
        pytest.skip('no d2data checkout')
    assert curses.table_skills() == {ai: dict(skills) for ai, skills in curses.SKILLS.items()}


def test_a_take_is_tallied_into_its_readings_its_cursers_time_near_and_their_casts():
    found = tallied(curse_take([(10, [10, *SET_A]), (40, [-40, *SET_A])]))
    assert found['seconds'] == pytest.approx((FRAMES - 1) / RATE)
    assert found['samples'] == [[10, [10, *SET_A]], [40, [-40, *SET_A]]]
    assert found['casts'] == [[CAST, CURSER, KNIGHT, 6.0]]  # the other type in the same mode is no curser
    band = next(index for index, edge in enumerate(curses.BANDS[1:]) if edge >= 6.0)
    assert found['near']['OblivionKnight'][band] == pytest.approx((FRAMES - 1) / RATE)
    assert sum(found['near']['OblivionKnight']) == pytest.approx((FRAMES - 1) / RATE)
    assert found['stretches'] == [[0, FRAMES - 1]]
    (span,) = found['spans']
    assert (span['nearest'], span['txt'], span['casts']) == (6.0, KNIGHT, 1)


def test_the_manifests_resistances_are_the_first_reading():
    found = tallied(curse_take([(40, [-40, *SET_A])], first=[10, *SET_A]))
    assert found['samples'] == [[0, [10, *SET_A]], [40, [-40, *SET_A]]]


def test_a_curser_out_of_range_is_not_near_and_a_cursed_leader_is_noted():
    units = [{'unit': OTHER, 'txt': MELEE_TXT, 'mods': [curses.CURSED]}]
    found = tallied(curse_take([(10, [10, *SET_A]), (40, [-90, *SET_A])], away=35.0, units=units))
    assert found['stretches'] == []
    (span,) = found['spans']
    assert (span['nearest'], span['cursed']) == (35.0, 35.1)  # the leader stands two units beside the curser


def test_the_levels_are_the_highest_seen_of_the_physical_and_of_each_set_of_weapons():
    one = tallied(curse_take([(10, [10, *SET_A]), (20, [-40, *SET_B]), (30, [10, *(v - 55 for v in SET_B)])]))
    two = tallied(curse_take([(10, [10, *SET_B])], name='20261011T130000Z-25'))
    levels = curses.levels([one, two])
    assert levels['physical'] == 10
    assert levels['sets'] == {curses.shape([0, *SET_A]): SET_A[3], curses.shape([0, *SET_B]): SET_B[3]}
    assert curses.state([10, *SET_A], levels) == curses.NONE
    assert curses.state([-40, *SET_B], levels) == 'physical -50'
    assert curses.state([-90, *(v - 55 for v in SET_A)], levels) == 'physical -100 + elemental -55'


def test_a_step_down_between_two_readings_is_an_onset_with_who_was_near_and_a_swap_is_none():
    readings = [
        (10, [10, *SET_A]),
        (20, [10, *SET_B]),  # the other weapons: no curse
        (40, [-40, *SET_B]),  # the curser cast at 30
        (60, [-40, *SET_A]),  # the other weapons again, the curse still on
        (80, [10, *SET_A]),
    ]
    found = curses.measure([tallied(curse_take(readings))])
    assert (found['takes'], found['sampled_takes'], found['samples'], found['curser_takes']) == (1, 1, 5, 1)
    assert found['states'] == {curses.NONE: 3, 'physical -50': 2}
    (onset,) = found['onsets']
    assert (onset['to'], onset['from'], onset['gap']) == ('physical -50', curses.NONE, pytest.approx(20 / RATE))
    assert (onset['casts'], onset['nearest'], onset['txt'], onset['swap']) == (1, 6.0, KNIGHT, 0)
    # A curser was within range from the take's first frame: 20 to 40 frames before the curse was read.
    assert (onset['near_for'], onset['near_for_most']) == (pytest.approx(20 / RATE), pytest.approx(40 / RATE))
    assert found['sources']['physical -50'] == {'n': 1, 'cast': 1, 'curser': 0, 'cursed': 0, 'nobody': 0}
    (spell,) = found['spells']
    assert (spell['state'], spell['least'], spell['most']) == ('physical -50', 20 / RATE, 60 / RATE)
    assert [off['from'] for off in found['offsets']] == ['physical -50']


def test_a_curse_the_take_ends_in_has_no_longest_time():
    found = curses.measure([tallied(curse_take([(10, [10, *SET_A]), (40, [-40, *SET_A]), (90, [-40, *SET_A])]))])
    (spell,) = found['spells']
    assert (spell['least'], spell['most']) == (50 / RATE, None)


def test_the_four_elemental_ones_falling_alike_without_a_swap_is_a_curse():
    lowered = [value - 55 for value in SET_A]
    found = curses.measure([tallied(curse_take([(10, [10, *SET_A]), (40, [10, *lowered])]))])
    assert [onset['to'] for onset in found['onsets']] == ['elemental -55']


def test_casts_a_second_are_the_casts_over_the_time_cursers_stood_in_the_band():
    found = curses.measure([tallied(curse_take([], casts=(30, 60)))])
    assert found['samples'] == 0
    row = next(row for row in found['casting']['OblivionKnight'] if row['casts'])
    assert (row['casts'], row['seconds']) == (2, pytest.approx((FRAMES - 1) / RATE, abs=0.05))
    assert row['rate'] == pytest.approx(2 / ((FRAMES - 1) / RATE), abs=0.01)
    assert row['from'] < 6.0 <= row['to']


def test_a_cast_is_laid_against_the_readings_before_and_after_it():
    found = curses.measure([tallied(curse_take([(10, [10, *SET_A]), (40, [-40, *SET_A])], casts=(30, 90)))])
    (row,) = [row for row in found['landing'] if row['casts']]
    # The cast at 30 has a reading within AFTER of it, cursed; the one at 90 has none after it.
    assert (row['casts'], row['read'], row['cursed'], row['clean_before'], row['cursed_after_clean']) == (2, 1, 1, 1, 1)


def test_takes_are_gathered_from_disk_and_the_report_is_written_by_group(tmp_path):
    first = write(curse_take([(10, [10, *SET_A]), (40, [-40, *SET_A])], '20261011T120000Z-25'), tmp_path)
    second = write(curse_take([(10, [10, *SET_A])], '20261011T130000Z-25'), tmp_path)
    one, two = (curses.gather([path], cache=None, probes=(), jobs=1, progress=False) for path in (first, second))
    assert one[0]['casts'] == [[CAST, CURSER, KNIGHT, 6.0]]
    cached = curses.gather([first], cache=tmp_path / 'cache', probes=(), jobs=1, progress=False)
    assert curses.gather([first], cache=tmp_path / 'cache', probes=(), jobs=1, progress=False) == cached == one
    levels = curses.levels([*one, *two])
    groups = {'train': curses.measure(one, levels), 'check': curses.measure(two, levels)}
    text = curses.render({'levels': levels, 'groups': groups})
    assert '| takes with a reading of the resistances | 1 | 1 |' in text
    assert '| physical -50 | 1 | 0 |' in text


def test_the_command_writes_both_files_with_the_takes_since_the_split_by_its_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(curses.scan, 'PROBES', tmp_path / 'no-logs')  # never the host's probe logs
    out, root = tmp_path / 'out', tmp_path / 'takes'
    out.mkdir()
    write(curse_take([(10, [10, *SET_A])], '20261011T120000Z-25'), root)
    later = write(curse_take([(10, [10, *SET_A]), (40, [-40, *SET_A])], '20261013T120000Z-25'), root)
    split = out / 'split.json'
    split.write_text(json.dumps({'train': ['20261011T120000Z-25'], 'check': []}))
    args = ['--root', str(root), '--out', str(out), '--split', str(split), '--no-cache', '--jobs', '1']
    assert curses.main(args) == 0
    found = json.loads((out / 'curses.json').read_text())
    group = curses.SINCE + '_' + curses.scan.half(later.name)
    assert found['groups']['train']['takes'] == 1
    assert found['groups'][group]['takes'] == 1
    assert [onset['take'] for onset in found['groups'][group]['onsets']] == [later.name]
    assert (out / 'CURSES.md').read_text() == curses.render(found)
